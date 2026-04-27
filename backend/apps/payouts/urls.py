from django.urls import path
from .views import PayoutCreateView, PayoutListView, PayoutDetailView
from apps.ledger.views import MerchantLedgerView

urlpatterns = [
    path('payouts/', PayoutCreateView.as_view(), name='payout-create'),
    path('payouts/<uuid:payout_id>/', PayoutDetailView.as_view(), name='payout-detail'),
    path('merchants/<uuid:merchant_id>/payouts/', PayoutListView.as_view(), name='merchant-payouts'),
    path('merchants/<uuid:merchant_id>/ledger/', MerchantLedgerView.as_view(), name='merchant-ledger'),
]
