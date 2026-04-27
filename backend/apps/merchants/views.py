from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Merchant
from .serializers import MerchantSerializer
from apps.ledger.services import get_merchant_balance


class MerchantListView(generics.ListAPIView):
    queryset = Merchant.objects.all().order_by('created_at')
    serializer_class = MerchantSerializer


class MerchantBalanceView(APIView):
    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        balance = get_merchant_balance(merchant_id)
        return Response({
            'merchant_id': str(merchant.id),
            'merchant_name': merchant.name,
            'available_balance_paise': balance['available'],
            'held_balance_paise': balance['held'],
            'total_credits_paise': balance['total_credits'],
            'total_debits_paise': balance['total_debits'],
        })
