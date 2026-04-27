from django.urls import path
from .views import MerchantListView, MerchantBalanceView

urlpatterns = [
    path('merchants/', MerchantListView.as_view(), name='merchant-list'),
    path('merchants/<uuid:merchant_id>/balance/', MerchantBalanceView.as_view(), name='merchant-balance'),
]
