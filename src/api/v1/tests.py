import uuid
from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from src.domains.ledger.models.journal import Account, LedgerEntry
from src.domains.ledger.services.transfer import LedgerTransferService


class LedgerTransferAPITests(TestCase):
    def setUp(self):
        self.client = Client()
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

    def test_transfer_endpoint_requires_idempotency_key(self):
        response = self.client.post(
            "/api/v1/transfers",
            {
                "source_account_id": str(self.source_account.id),
                "destination_account_id": str(self.destination_account.id),
                "amount": 100,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_transfer_endpoint_creates_transaction(self):
        response = self.client.post(
            "/api/v1/transfers",
            {
                "source_account_id": str(self.source_account.id),
                "destination_account_id": str(self.destination_account.id),
                "amount": 100,
            },
            content_type="application/json",
            HTTP_X_IDEMPOTENCY_KEY="api-test-key",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "AUTHORIZED")

        self.source_account.refresh_from_db()
        self.destination_account.refresh_from_db()

        self.assertEqual(self.source_account.balance, 900)
        self.assertEqual(self.destination_account.balance, 600)

    def test_transfer_endpoint_rejects_invalid_amount(self):
        response = self.client.post(
            "/api/v1/transfers",
            {
                "source_account_id": str(self.source_account.id),
                "destination_account_id": str(self.destination_account.id),
                "amount": -50,
            },
            content_type="application/json",
            HTTP_X_IDEMPOTENCY_KEY="api-test-key-2",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())


class AccountEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.account = Account.objects.create(
            user_id=uuid.uuid4(),
            balance=1200,
            currency="USD",
        )

    def test_account_list_returns_accounts(self):
        response = self.client.get("/api/v1/accounts/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_account_detail_returns_account(self):
        response = self.client.get(f"/api/v1/accounts/{self.account.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.account.id))

    def test_health_endpoint_returns_ok(self):
        response = self.client.get("/api/v1/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


class LedgerEntryEndpointsTests(TestCase):
    def setUp(self):
        self.client = Client()
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
        self.entry = LedgerEntry.objects.create(
            idempotency_key="entry-test-key",
            debit_account=self.source_account,
            credit_account=self.destination_account,
            amount=100,
            description="Test ledger entry",
        )

    def test_ledger_entry_list_returns_entries(self):
        response = self.client.get("/api/v1/ledger-entries/")
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_ledger_entry_detail_returns_entry(self):
        response = self.client.get(f"/api/v1/ledger-entries/{self.entry.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.entry.id))
