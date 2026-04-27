from rest_framework import serializers
from .models import LedgerEntry


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ('id', 'entry_type', 'amount_paise', 'description', 'payout', 'created_at')
