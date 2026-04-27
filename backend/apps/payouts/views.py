import uuid
import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.merchants.models import Merchant
from apps.idempotency.models import IdempotencyKey
from .models import Payout
from .serializers import PayoutSerializer, CreatePayoutSerializer
from .services import create_payout, InsufficientFundsError
from .tasks import process_payout

logger = logging.getLogger(__name__)


def _serializer_data_to_json_safe(data):
    """
    Recursively convert any UUID objects inside a serializer ReturnDict
    (or any nested dict/list) to strings so Django's JSONField can
    call json.dumps on them without raising TypeError.

    DRF's .data property returns a ReturnDict whose values can still be
    uuid.UUID instances if the model field is a UUIDField.
    """
    if isinstance(data, dict):
        return {key: _serializer_data_to_json_safe(val) for key, val in data.items()}
    if isinstance(data, list):
        return [_serializer_data_to_json_safe(item) for item in data]
    if isinstance(data, uuid.UUID):          # FIX: UUID → str
        return str(data)
    return data


class PayoutCreateView(APIView):
    """
    POST /api/v1/payouts/
    Header: Idempotency-Key: <uuid>
    Body: { merchant_id, amount_paise, bank_account_id }
    """

    def post(self, request):
        merchant_id = request.data.get('merchant_id')
        if not merchant_id:
            return Response({'error': 'merchant_id is required'}, status=400)

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        # ── Idempotency check ──────────────────────────────────────────────
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required'},
                status=400,
            )

        try:
            uuid.UUID(idempotency_key)           # validate format
        except ValueError:
            return Response(
                {'error': 'Idempotency-Key must be a valid UUID'},
                status=400,
            )

        expiry_cutoff = timezone.now() - timezone.timedelta(hours=24)
        existing_key = IdempotencyKey.objects.filter(
            merchant=merchant,
            key=idempotency_key,              # FIX: key is already a str from header
            created_at__gt=expiry_cutoff,
        ).first()

        if existing_key:
            if existing_key.is_in_flight:
                return Response(
                    {'error': 'Request with this Idempotency-Key is already in progress'},
                    status=409,
                )
            # Return the exact same response stored the first time
            return Response(
                existing_key.response_body,   # already JSON-safe (stored as dict)
                status=existing_key.response_status,
            )

        # ── Validate body ──────────────────────────────────────────────────
        serializer = CreatePayoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # ── Mark key as in-flight ──────────────────────────────────────────
        idem_key, created = IdempotencyKey.objects.get_or_create(
            merchant=merchant,
            key=idempotency_key,              # FIX: plain str, not uuid.UUID object
            defaults={
                'is_in_flight': True,
                'response_status': 0,
                'response_body': {},
            },
        )
        if not created:
            return Response({'error': 'Duplicate request in flight'}, status=409)

        # ── Process payout ─────────────────────────────────────────────────
        try:
            payout = create_payout(
                merchant_id=merchant.id,
                amount_paise=serializer.validated_data['amount_paise'],
                bank_account_id=serializer.validated_data['bank_account_id'],
            )

            # FIX: convert ReturnDict → plain dict with all UUIDs as strings
            # PayoutSerializer.data is a ReturnDict; UUIDField values inside it
            # are uuid.UUID objects which json.dumps cannot handle.
            response_data = _serializer_data_to_json_safe(
                dict(PayoutSerializer(payout).data)
            )
            response_status_code = 201

        except InsufficientFundsError as e:
            response_data = {'error': str(e)}
            response_status_code = 422

        except Exception as e:
            logger.exception(f'Unexpected error creating payout: {e}')
            idem_key.delete()
            return Response({'error': 'Internal server error'}, status=500)

        # ── Persist idempotency response ───────────────────────────────────
        # FIX: response_data is now a plain dict of JSON-safe primitives,
        # so JSONField.save() can call json.dumps on it without TypeError.
        idem_key.response_status = response_status_code
        idem_key.response_body = response_data   # safe: no UUID objects remain
        idem_key.is_in_flight = False
        idem_key.save()

        # ── Dispatch background worker ─────────────────────────────────────
        if response_status_code == 201:
            # FIX: pass payout.id as str — Celery serialises task args via JSON
            process_payout.delay(str(payout.id))

        return Response(response_data, status=response_status_code)


class PayoutListView(APIView):
    """GET /api/v1/merchants/{merchant_id}/payouts/"""

    def get(self, request, merchant_id):
        try:
            Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        payouts = Payout.objects.filter(merchant_id=merchant_id).order_by('-created_at')
        serializer = PayoutSerializer(payouts, many=True)
        return Response(serializer.data)


class PayoutDetailView(APIView):
    """GET /api/v1/payouts/{payout_id}/"""

    def get(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except Payout.DoesNotExist:
            return Response({'error': 'Payout not found'}, status=404)

        serializer = PayoutSerializer(payout)
        return Response(serializer.data)