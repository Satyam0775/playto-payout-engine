from django.contrib import admin
from .models import Merchant

@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'created_at')
    search_fields = ('name', 'email')
