"""
Concurrency test: two simultaneous 60 rupee payout requests for a merchant
with 100 rupees. Exactly one must succeed, the other must be rejected.
"""
import threading
import uuid
from django.test import TestCase, TransactionTestCase
from apps.merchants.models import Merchant
from apps.ledger.models import LedgerEntry
from apps.payouts.models import Payout
from apps.payouts.services import create_payout, InsufficientFundsError


class ConcurrencyTest(TransactionTestCase):
    """
    Use TransactionTestCase (not TestCase) so that each thread gets its
    own DB connection and transactions actually commit/rollback.
    TestCase wraps everything in a rolled-back transaction, which would
    prevent select_for_update from working across threads.
    """

    def setUp(self):
        self.merchant = Merchant.objects.create(
            name='Test Merchant',
            email='test@concurrent.com',
        )
        # Credit 100 rupees = 10,000 paise
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.CREDIT,
            amount_paise=10000,
            description='Initial credit',
        )

    def test_concurrent_overdraft_prevention(self):
        """
        Two threads simultaneously try to withdraw 6,000 paise each
        (total 12,000 > available 10,000). Exactly one must succeed.
        """
        results = []
        errors = []

        def attempt_payout():
            try:
                payout = create_payout(
                    merchant_id=self.merchant.id,
                    amount_paise=6000,
                    bank_account_id='ACC123456',
                )
                results.append(('success', payout.id))
            except InsufficientFundsError as e:
                results.append(('rejected', str(e)))
            except Exception as e:
                errors.append(str(e))

        t1 = threading.Thread(target=attempt_payout)
        t2 = threading.Thread(target=attempt_payout)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(len(errors), 0, f'Unexpected errors: {errors}')
        self.assertEqual(len(results), 2)

        successes = [r for r in results if r[0] == 'success']
        rejections = [r for r in results if r[0] == 'rejected']

        self.assertEqual(len(successes), 1, 'Exactly one payout should succeed')
        self.assertEqual(len(rejections), 1, 'Exactly one payout should be rejected')

        # Verify only one payout exists in DB
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 1)

        # Verify balance integrity: available should be 4000 paise
        from apps.ledger.services import get_merchant_balance
        bal = get_merchant_balance(self.merchant.id)
        self.assertEqual(bal['available'], 4000)

    def test_balance_invariant_after_concurrent_operations(self):
        """
        After any sequence of operations, credits - debits == displayed balance.
        """
        create_payout(
            merchant_id=self.merchant.id,
            amount_paise=3000,
            bank_account_id='ACC123456',
        )

        from apps.ledger.services import get_merchant_balance
        from django.db.models import Sum, Q

        bal = get_merchant_balance(self.merchant.id)

        # Manually compute invariant
        totals = LedgerEntry.objects.filter(merchant=self.merchant).aggregate(
            c=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.CREDIT)),
            d=Sum('amount_paise', filter=Q(entry_type=LedgerEntry.DEBIT)),
        )
        expected = (totals['c'] or 0) - (totals['d'] or 0)

        self.assertEqual(
            bal['available'], expected,
            'Balance invariant violated: available != credits - debits'
        )
