from django.db.models import Sum, Q
from .models import LedgerEntry
from apps.payouts.models import Payout


def get_merchant_balance(merchant_id):
    """
    Compute merchant balance entirely at the database level using aggregation.
    Never loads individual rows into Python - single SQL query.

    Balance model:
      - DEBIT entry is created immediately when a payout is requested (funds held)
      - CREDIT entry is created when a payout FAILS (funds returned)
      - CREDIT entry is created for incoming customer payments
    
    Therefore:
      available_balance = SUM(credits) - SUM(debits)
      held_balance      = SUM of DEBIT entries whose linked payout is still
                          pending or processing (informational only)
    """
    result = LedgerEntry.objects.filter(merchant_id=merchant_id).aggregate(
        total_credits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
        total_debits=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
    )

    total_credits = result['total_credits'] or 0
    total_debits = result['total_debits'] or 0
    available = total_credits - total_debits

    # Held = debits whose payout is still pending/processing (not yet settled)
    held_result = LedgerEntry.objects.filter(
        merchant_id=merchant_id,
        entry_type=LedgerEntry.DEBIT,
        payout__status__in=[Payout.PENDING, Payout.PROCESSING],
    ).aggregate(held=Sum('amount_paise'))
    held = held_result['held'] or 0

    return {
        'available': available,
        'held': held,
        'total_credits': total_credits,
        'total_debits': total_debits,
    }
