"""
Idempotency test: same Idempotency-Key sent twice must return
the same response with no duplicate payout created.
"""
import uuid
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from apps.merchants.models import Merchant
from apps.ledger.models import LedgerEntry
from apps.payouts.models import Payout


class IdempotencyTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.merchant = Merchant.objects.create(
            name='Idem Test Merchant',
            email='idem@test.com',
        )
        LedgerEntry.objects.create(
            merchant=self.merchant,
            entry_type=LedgerEntry.CREDIT,
            amount_paise=100000,
            description='Initial credit for idempotency test',
        )

    def _make_request(self, key, amount=5000):
        return self.client.post(
            '/api/v1/payouts/',
            data={
                'merchant_id': str(self.merchant.id),
                'amount_paise': amount,
                'bank_account_id': 'HDFC0001234',
            },
            format='json',
            HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_same_key_returns_same_response(self):
        key = str(uuid.uuid4())

        response1 = self._make_request(key)
        response2 = self._make_request(key)

        self.assertEqual(response1.status_code, 201)
        self.assertEqual(response2.status_code, 201)

        # Responses must be identical
        self.assertEqual(response1.data['id'], response2.data['id'])
        self.assertEqual(response1.data['amount_paise'], response2.data['amount_paise'])

        # Only one payout must exist in the database
        payouts = Payout.objects.filter(merchant=self.merchant)
        self.assertEqual(payouts.count(), 1, 'Duplicate payout was created!')

    def test_different_keys_create_separate_payouts(self):
        key1 = str(uuid.uuid4())
        key2 = str(uuid.uuid4())

        r1 = self._make_request(key1, amount=3000)
        r2 = self._make_request(key2, amount=3000)

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.data['id'], r2.data['id'])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 2)

    def test_missing_idempotency_key_returns_400(self):
        response = self.client.post(
            '/api/v1/payouts/',
            data={
                'merchant_id': str(self.merchant.id),
                'amount_paise': 5000,
                'bank_account_id': 'HDFC0001234',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('Idempotency-Key', response.data['error'])

    def test_insufficient_funds_idempotent(self):
        """A failed request (insufficient funds) is also idempotent."""
        key = str(uuid.uuid4())

        r1 = self._make_request(key, amount=99999999)  # way more than balance
        r2 = self._make_request(key, amount=99999999)

        self.assertEqual(r1.status_code, 422)
        self.assertEqual(r2.status_code, 422)
        self.assertEqual(r1.data['error'], r2.data['error'])
        self.assertEqual(Payout.objects.filter(merchant=self.merchant).count(), 0)

    def test_state_machine_blocks_illegal_transitions(self):
        """Completed -> pending must raise, completed -> failed must raise."""
        from apps.payouts.models import Payout
        from django.core.exceptions import ValidationError

        payout = Payout(status=Payout.COMPLETED)

        with self.assertRaises(ValidationError):
            payout.transition_to(Payout.PENDING)

        with self.assertRaises(ValidationError):
            payout.transition_to(Payout.FAILED)

        payout2 = Payout(status=Payout.FAILED)
        with self.assertRaises(ValidationError):
            payout2.transition_to(Payout.COMPLETED)
