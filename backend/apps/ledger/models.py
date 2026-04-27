import uuid
from django.db import models


class LedgerEntry(models.Model):
    CREDIT = 'credit'
    DEBIT = 'debit'
    ENTRY_TYPE_CHOICES = [
        (CREDIT, 'Credit'),
        (DEBIT, 'Debit'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.PROTECT,
        related_name='ledger_entries',
    )
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPE_CHOICES, db_index=True)
    # All monetary values stored in paise (integer) - NEVER floats
    amount_paise = models.BigIntegerField()
    description = models.CharField(max_length=500)
    # Optional FK to the payout that triggered this entry
    payout = models.ForeignKey(
        'payouts.Payout',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='ledger_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'ledger_entries'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'entry_type']),
            models.Index(fields=['merchant', 'created_at']),
        ]

    def __str__(self):
        return f'{self.entry_type.upper()} {self.amount_paise} paise for {self.merchant}'
