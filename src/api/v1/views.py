from rest_framework.views import APIView
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from src.domains.ledger.services.transfer import LedgerTransferService
from src.domains.ledger.models.journal import Account, LedgerEntry
from .serializers import AccountSerializer, LedgerEntrySerializer


class LedgerTransferView(APIView):
    def post(self, request, *args, **kwargs):
        idempotency_key = request.headers.get("X-Idempotency-Key")
        debit_id = request.data.get("source_account_id")
        credit_id = request.data.get("destination_account_id")
        amount = request.data.get("amount")

        if not idempotency_key:
            return Response({"error": "Header missing: X-Idempotency-Key"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ledger_entry = LedgerTransferService.execute_transfer(
                debit_account_id=debit_id,
                credit_account_id=credit_id,
                amount=int(amount),
                idempotency_key=idempotency_key
            )
            return Response({
                "transaction_id": str(ledger_entry.id),
                "status": "AUTHORIZED",
                "message": "Funds successfully captured and settled globally."
            }, status=status.HTTP_201_CREATED)
        except (ValidationError, DjangoValidationError) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Critical system exception: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AccountListView(generics.ListAPIView):
    queryset = Account.objects.all().order_by('created_at')
    serializer_class = AccountSerializer


class AccountDetailView(generics.RetrieveAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    lookup_field = 'id'


class LedgerEntryListView(generics.ListAPIView):
    queryset = LedgerEntry.objects.select_related('debit_account', 'credit_account').all().order_by('-created_at')
    serializer_class = LedgerEntrySerializer


class LedgerEntryDetailView(generics.RetrieveAPIView):
    queryset = LedgerEntry.objects.select_related('debit_account', 'credit_account').all()
    serializer_class = LedgerEntrySerializer
    lookup_field = 'id'
