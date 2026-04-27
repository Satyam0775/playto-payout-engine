from celery import shared_task
from django.utils import timezone


@shared_task(name='apps.idempotency.tasks.cleanup_expired_keys')
def cleanup_expired_keys():
    from .models import IdempotencyKey
    expiry = timezone.now() - timezone.timedelta(hours=24)
    deleted, _ = IdempotencyKey.objects.filter(created_at__lt=expiry).delete()
    return f'Deleted {deleted} expired idempotency keys'
