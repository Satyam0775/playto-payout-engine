from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from apps.merchants.models import Merchant
from apps.ledger.models import LedgerEntry
from apps.idempotency.models import IdempotencyKey
from .models import Payout


class InsufficientFundsError(Exception):
    pass


class DuplicatePayoutError(Exception):
    def __init__(self, message, existing_payout):
        super().__init__(message)
        self.existing_payout = existing_payout


@transaction.atomic
def create_payout(merchant_id, amount_paise, bank_account_id):
    """
    Create a payout with proper fund reservation.

    Critical section:
      1. Lock the merchant row with SELECT FOR UPDATE
         This serialises concurrent requests at the DB level.
         Two simultaneous requests queue here; the second sees the
         updated balance after the first has committed.
      2. Compute spendable balance using pure DB aggregation - no
         Python arithmetic on individual fetched rows.
      3. If sufficient, create Payout + DEBIT LedgerEntry atomically.

    The SELECT FOR UPDATE on the Merchant row is the database primitive
    that prevents overdraft - not application-level locking.
    """
    # Step 1: Acquire row-level exclusive lock on the merchant
    merchant = Merchant.objects.select_for_update().get(id=merchant_id)

    # Step 2: Compute available balance at DB level (single aggregation query)
    result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        total_credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
        total_debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
    )
    total_credits = result['total_credits'] or 0
    total_debits = result['total_debits'] or 0
    available = total_credits - total_debits

    # Step 3: Enforce sufficient funds
    if available < amount_paise:
        raise InsufficientFundsError(
            f'Insufficient balance. Available: {available} paise, '
            f'Requested: {amount_paise} paise'
        )

    # Step 4: Create the payout record
    payout = Payout.objects.create(
        merchant=merchant,
        amount_paise=amount_paise,
        bank_account_id=bank_account_id,
        status=Payout.PENDING,
    )

    # Step 5: Create DEBIT ledger entry immediately - funds are now "held"
    # The debit is what makes the balance drop; it is created atomically
    # with the payout so the two are always consistent.
    LedgerEntry.objects.create(
        merchant=merchant,
        entry_type=LedgerEntry.DEBIT,
        amount_paise=amount_paise,
        description=f'Payout initiated: {payout.id}',
        payout=payout,
    )

    return payout


@transaction.atomic
def complete_payout(payout_id):
    """Mark payout as completed. No new ledger entry needed - DEBIT was
    already created at initiation. Atomic state transition with row lock."""
    payout = Payout.objects.select_for_update().get(id=payout_id)
    payout.transition_to(Payout.COMPLETED)   # raises on illegal transition
    payout.save(update_fields=['status', 'updated_at'])
    return payout


@transaction.atomic
def fail_payout(payout_id):
    """
    Mark payout as failed AND create a CREDIT refund entry in the SAME
    transaction. These two operations are atomic - you can never have a
    failed payout without the refund credit, or vice versa.
    """
    payout = Payout.objects.select_for_update().get(id=payout_id)
    payout.transition_to(Payout.FAILED)      # raises on illegal transition
    payout.save(update_fields=['status', 'updated_at'])

    # Refund: credit back the held amount
    LedgerEntry.objects.create(
        merchant_id=payout.merchant_id,
        entry_type=LedgerEntry.CREDIT,
        amount_paise=payout.amount_paise,
        description=f'Refund for failed payout: {payout.id}',
        payout=payout,
    )
    return payout
