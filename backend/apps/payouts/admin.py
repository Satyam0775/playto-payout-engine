from django.contrib import admin
from .models import Payout

@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'merchant', 'amount_paise', 'status', 'retry_count', 'created_at')
    list_filter = ('status',)
    search_fields = ('merchant__name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
