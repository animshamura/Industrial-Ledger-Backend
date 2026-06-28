from django.urls import path, include
from src.api.v1.views import LedgerTransferView

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('api/v1/transfers', LedgerTransferView.as_view(), name='ledger-transfer'),
]
