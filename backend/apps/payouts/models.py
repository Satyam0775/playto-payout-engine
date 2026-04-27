import uuid
from django.db import models
from django.core.exceptions import ValidationError


class Payout(models.Model):
    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (COMPLETED, 'Completed'),
        (FAILED, 'Failed'),
    ]

    # Legal state transitions - enforced at model level
    VALID_TRANSITIONS = {
        PENDING: [PROCESSING],
        PROCESSING: [COMPLETED, FAILED],
        COMPLETED: [],   # Terminal state
        FAILED: [],      # Terminal state
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.PROTECT,
        related_name='payouts',
    )
    # Amount in paise - BigIntegerField, NEVER float/decimal
    amount_paise = models.BigIntegerField()
    bank_account_id = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_index=True,
    )
    # Retry tracking for stuck payouts
    retry_count = models.IntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payouts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['merchant', 'status']),
            models.Index(fields=['status', 'processing_started_at']),
        ]

    def __str__(self):
        return f'Payout {self.id} [{self.status}] {self.amount_paise} paise'

    def transition_to(self, new_status):
        """
        Enforce state machine. Raises ValidationError on illegal transitions.
        This is the single gatekeeper - all status changes go through here.
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValidationError(
                f'Illegal state transition: {self.status} -> {new_status}. '
                f'Allowed from {self.status}: {allowed}'
            )
        self.status = new_status
