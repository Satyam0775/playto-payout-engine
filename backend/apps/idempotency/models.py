import uuid
from django.db import models


class IdempotencyKey(models.Model):
    """
    Stores seen idempotency keys and their responses.
    
    Scoped per (merchant, key) pair. Keys expire after 24 hours
    (enforced at query time in the view, not here).
    
    is_in_flight: True while the first request is still being processed.
    If a second identical request arrives while is_in_flight=True,
    we return 409 Conflict rather than processing it again.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(
        'merchants.Merchant',
        on_delete=models.CASCADE,
        related_name='idempotency_keys',
    )
    key = models.CharField(max_length=255, db_index=True)
    is_in_flight = models.BooleanField(default=False)
    response_status = models.IntegerField(default=0)
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'idempotency_keys'
        # A key is unique per merchant - same key from different merchants is OK
        unique_together = [['merchant', 'key']]
        indexes = [
            models.Index(fields=['merchant', 'key', 'created_at']),
        ]

    def __str__(self):
        return f'IdempKey {self.key} for {self.merchant_id}'
