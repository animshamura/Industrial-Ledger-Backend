import logging
from django.db import transaction
from django.core.exceptions import ValidationError
from src.domains.ledger.models.journal import Account, LedgerEntry
from src.domains.webhooks.models.outbox import WebhookOutbox

logger = logging.getLogger("ledger.services")

class LedgerTransferService:
    @staticmethod
    def execute_transfer(debit_account_id: str, credit_account_id: str, amount: int, idempotency_key: str) -> LedgerEntry:
        if amount <= 0:
            raise ValidationError("Transfer amount must be greater than zero.")
        account_ids = sorted([str(debit_account_id), str(credit_account_id)])
        
        with transaction.atomic():
            locked_accounts = {
                str(acc.id): acc for acc in Account.objects.select_for_update().filter(id__in=account_ids)
            }
            source_acc = locked_accounts.get(str(debit_account_id))
            destination_acc = locked_accounts.get(str(credit_account_id))
            
            if not source_acc or not destination_acc:
                raise ValidationError("One or both specified accounts do not exist.")
            if source_acc.balance < amount:
                raise ValidationError("Insufficient funds.")
                
            source_acc.balance -= amount
            destination_acc.balance += amount
            source_acc.save(update_fields=['balance', 'updated_at'])
            destination_acc.save(update_fields=['balance', 'updated_at'])
            
            ledger_entry = LedgerEntry.objects.create(
                idempotency_key=idempotency_key,
                debit_account=source_acc,
                credit_account=destination_acc,
                amount=amount,
                description=f"Transfer {amount} from {source_acc.id} to {destination_acc.id}"
            )
            
            WebhookOutbox.objects.create(
                event_type="ledger.transfer.completed",
                payload={
                    "ledger_entry_id": str(ledger_entry.id),
                    "amount": amount,
                    "timestamp": ledger_entry.created_at.isoformat()
                }
            )
            return ledger_entry
