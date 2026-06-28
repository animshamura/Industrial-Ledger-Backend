import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from src.domains.ledger.models.journal import Account, LedgerEntry
from src.domains.webhooks.models.outbox import WebhookOutbox
from src.domains.ledger.services.transfer import LedgerTransferService


class LedgerTransferServiceTests(TestCase):
    def setUp(self):
        self.source_account = Account.objects.create(
            user_id=uuid.uuid4(),
            balance=1000,
            currency="USD",
        )
        self.destination_account = Account.objects.create(
            user_id=uuid.uuid4(),
            balance=500,
            currency="USD",
        )

    def test_execute_transfer_creates_ledger_entry_and_outbox(self):
        ledger_entry = LedgerTransferService.execute_transfer(
            debit_account_id=self.source_account.id,
            credit_account_id=self.destination_account.id,
            amount=250,
            idempotency_key="test-key-123",
        )

        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, 750)
        self.assertEqual(self.destination_account.balance, 750)
        self.assertEqual(LedgerEntry.objects.count(), 1)
        self.assertEqual(WebhookOutbox.objects.count(), 1)
        self.assertEqual(ledger_entry.idempotency_key, "test-key-123")
        self.assertEqual(ledger_entry.amount, 250)
        self.assertEqual(str(ledger_entry.debit_account_id), str(self.source_account.id))
        self.assertEqual(str(ledger_entry.credit_account_id), str(self.destination_account.id))

    def test_execute_transfer_fails_when_insufficient_funds(self):
        with self.assertRaises(ValidationError):
            LedgerTransferService.execute_transfer(
                debit_account_id=self.source_account.id,
                credit_account_id=self.destination_account.id,
                amount=1500,
                idempotency_key="insufficient-key",
            )

        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, 1000)
        self.assertEqual(self.destination_account.balance, 500)
        self.assertEqual(LedgerEntry.objects.count(), 0)
        self.assertEqual(WebhookOutbox.objects.count(), 0)
