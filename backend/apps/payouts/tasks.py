import time
import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .models import Payout
from .services import complete_payout, fail_payout

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='apps.payouts.tasks.process_payout')
def process_payout(self, payout_id: str):
    """
    Background worker: picks up a PENDING payout and simulates bank processing.
    Always completes successfully after a 3-second simulated bank delay.
    """
    try:
        # Transition PENDING -> PROCESSING atomically with row lock
        with transaction.atomic():
            try:
                payout = Payout.objects.select_for_update().get(
                    id=payout_id, status=Payout.PENDING
                )
            except Payout.DoesNotExist:
                logger.info(f'Payout {payout_id} not in PENDING state, skipping.')
                return

            payout.transition_to(Payout.PROCESSING)
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=['status', 'processing_started_at', 'updated_at'])

        # ── CHANGED: simulate bank network latency, then always succeed ──
        logger.info(f'Payout {payout_id} sent to bank, awaiting settlement...')
        time.sleep(3)
        complete_payout(payout_id)
        logger.info(f'Payout {payout_id} completed successfully.')
        # ── END CHANGED SECTION ──────────────────────────────────────────

    except Exception as exc:
        logger.exception(f'Error processing payout {payout_id}: {exc}')
        raise


@shared_task(name='apps.payouts.tasks.check_stuck_payouts')
def check_stuck_payouts():
    """
    Periodic task (runs every 30s via Celery beat):
    Find payouts stuck in PROCESSING for >30s and queue retries.
    """
    stuck_threshold = timezone.now() - timedelta(seconds=30)

    stuck_ids = list(Payout.objects.filter(
        status=Payout.PROCESSING,
        processing_started_at__lt=stuck_threshold,
    ).values_list('id', flat=True))

    for payout_id in stuck_ids:
        retry_stuck_payout.delay(str(payout_id))

    if stuck_ids:
        logger.info(f'Queued retry for {len(stuck_ids)} stuck payouts')


@shared_task(name='apps.payouts.tasks.retry_stuck_payout')
def retry_stuck_payout(payout_id: str):
    """
    Retry a stuck payout with exponential backoff.
    Max 3 retries; after that, fail and refund.

    Note: We directly set status=PENDING here rather than going through
    transition_to() because PROCESSING->PENDING is an internal system
    operation (retry), not a merchant-driven transition. We document this
    explicitly rather than hiding it in the state machine.
    """
    with transaction.atomic():
        try:
            payout = Payout.objects.select_for_update().get(
                id=payout_id, status=Payout.PROCESSING
            )
        except Payout.DoesNotExist:
            return  # Already resolved by another worker

        if payout.retry_count >= 3:
            logger.warning(f'Payout {payout_id} exceeded max retries, marking failed')
            # Manually transition + refund inside this transaction
            from django.core.exceptions import ValidationError
            from apps.ledger.models import LedgerEntry

            payout.status = Payout.FAILED
            payout.save(update_fields=['status', 'updated_at'])

            LedgerEntry.objects.create(
                merchant_id=payout.merchant_id,
                entry_type=LedgerEntry.CREDIT,
                amount_paise=payout.amount_paise,
                description=f'Refund for max-retry payout: {payout.id}',
                payout=payout,
            )
            return

        backoff_seconds = 2 ** payout.retry_count  # 1s, 2s, 4s
        payout.retry_count += 1
        payout.status = Payout.PENDING  # Reset for re-processing (internal retry)
        payout.processing_started_at = None
        payout.save(update_fields=['retry_count', 'status', 'processing_started_at', 'updated_at'])
        logger.info(
            f'Payout {payout_id} reset to PENDING for retry #{payout.retry_count}, backoff={backoff_seconds}s'
        )

    # Schedule re-processing after backoff (outside atomic block)
    process_payout.apply_async(args=[payout_id], countdown=backoff_seconds)