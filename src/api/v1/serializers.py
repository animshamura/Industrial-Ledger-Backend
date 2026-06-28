from rest_framework import serializers
from src.domains.ledger.models.journal import Account, LedgerEntry


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            'id',
            'user_id',
            'balance',
            'currency',
            'created_at',
            'updated_at',
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    debit_account_id = serializers.UUIDField(source='debit_account.id', read_only=True)
    credit_account_id = serializers.UUIDField(source='credit_account.id', read_only=True)

    class Meta:
        model = LedgerEntry
        fields = [
            'id',
            'idempotency_key',
            'debit_account_id',
            'credit_account_id',
            'amount',
            'description',
            'created_at',
        ]
