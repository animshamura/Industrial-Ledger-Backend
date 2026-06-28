from django.urls import path, include
from src.api.v1.views import (
    LedgerTransferView,
    HealthCheckView,
    AccountListView,
    AccountDetailView,
    LedgerEntryListView,
    LedgerEntryDetailView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/transfers', LedgerTransferView.as_view(), name='ledger-transfer'),
    path('api/v1/health/', HealthCheckView.as_view(), name='health-check'),
    path('api/v1/accounts/', AccountListView.as_view(), name='account-list'),
    path('api/v1/accounts/<uuid:id>/', AccountDetailView.as_view(), name='account-detail'),
    path('api/v1/ledger-entries/', LedgerEntryListView.as_view(), name='ledger-entry-list'),
    path('api/v1/ledger-entries/<uuid:id>/', LedgerEntryDetailView.as_view(), name='ledger-entry-detail'),
]
