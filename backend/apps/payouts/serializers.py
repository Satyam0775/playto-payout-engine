from rest_framework import serializers
from .models import Payout


class PayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payout
        fields = (
            'id', 'merchant', 'amount_paise', 'bank_account_id',
            'status', 'retry_count', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'status', 'retry_count', 'created_at', 'updated_at')


class CreatePayoutSerializer(serializers.Serializer):
    amount_paise = serializers.IntegerField(min_value=1)
    bank_account_id = serializers.CharField(max_length=255)
