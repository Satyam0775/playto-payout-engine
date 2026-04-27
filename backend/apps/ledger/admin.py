from django.contrib import admin
from .models import LedgerEntry

@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'entry_type', 'amount_paise', 'description', 'created_at')
    list_filter = ('entry_type',)
    search_fields = ('merchant__name',)
    raw_id_fields = ('payout',)
