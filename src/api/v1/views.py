from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from src.domains.ledger.services.transfer import LedgerTransferService
from django.core.exceptions import ValidationError

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
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Critical system exception: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
