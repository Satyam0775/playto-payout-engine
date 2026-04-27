from rest_framework.views import APIView
from rest_framework.response import Response
from apps.merchants.models import Merchant
from .models import LedgerEntry
from .serializers import LedgerEntrySerializer


class MerchantLedgerView(APIView):
    def get(self, request, merchant_id):
        try:
            Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        entries = LedgerEntry.objects.filter(
            merchant_id=merchant_id
        ).select_related('payout').order_by('-created_at')[:50]

        serializer = LedgerEntrySerializer(entries, many=True)
        return Response(serializer.data)
