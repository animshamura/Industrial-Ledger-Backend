# Industrial Ledger Backend

A high-concurrency, double-entry transactional ledger backend engine built with Django, Django REST Framework, Celery, PostgreSQL, and Redis.

## Overview

Industrial Ledger Backend is a ledger service designed for financial systems that need auditability, idempotent operations, and reliable webhook delivery.

It enforces double-entry accounting through explicit debit and credit ledger entries, uses database transactions to protect balance changes, and publishes webhook events via an outbox pattern.

Key capabilities:
- REST API for ledger transfers with explicit debit/credit accounting
- Account list/detail and ledger entry list/detail endpoints
- Idempotent transfer requests using `X-Idempotency-Key`
- Database locking with `select_for_update()` for concurrent balance updates
- Webhook outbox persistence and retry-safe Celery delivery
- Prometheus metrics via `django-prometheus`
- OpenAPI schema and Swagger UI documentation

## Architecture and system design

The service is designed as a modular Django monolith with clearly separated domain and API layers.

- `src/domains/ledger/` holds accounting models and transactional business logic.
- `src/domains/webhooks/` stores outbox events and handles webhook delivery asynchronously.
- `src/api/v1/` exposes REST resources and serialization for accounts, ledger entries, and transfers.
- `config/` contains environment-specific Django settings, URL routing, and deployment integration.

The core transfer workflow is:

1. Client submits `POST /api/v1/transfers` with source and destination account IDs, amount, and `X-Idempotency-Key`.
2. The API validates the request and forwards it to `LedgerTransferService`.
3. The service loads both accounts using `select_for_update()` inside a transaction to prevent concurrent balance corruption.
4. It debits one account and credits the other, then creates a `LedgerEntry` record.
5. A webhook outbox record is created in the same transaction to guarantee delivery intent.
6. Celery workers later consume outbox records and deliver webhook payloads, retrying failed deliveries.

Design goals:

- **Durability and consistency:** account balance updates and ledger entry creation occur inside a single atomic transaction.
- **Idempotency:** ledger transfers are protected by a unique idempotency key recorded in the ledger entry.
- **Observability:** Prometheus metrics and API schema documentation are exposed for monitoring and API discovery.
- **Separation of concerns:** API, domain logic, and webhook delivery are separated into discrete packages.

## Repository structure

- `config/` - Django settings, URLs, WSGI/ASGI entrypoints
- `src/api/v1/` - API views, serializers, and tests
- `src/domains/ledger/` - ledger models, services, and business logic
- `src/domains/webhooks/` - webhook outbox models and Celery tasks
- `deploy/docker/django/Dockerfile.prod` - production Docker image build
- `docker-compose.prod.yml` - sample deployment stack for PostgreSQL, Redis, Django, and Celery

## Requirements

- Python 3.11
- Poetry (recommended) or equivalent Python dependency manager
- PostgreSQL and Redis for production deployment
- SQLite is used by local development settings

## Local development

This repository includes local Django settings in `config/settings/local.py` that use SQLite and in-memory cache.

1. Install dependencies:

```bash
poetry install
```

2. Set the local settings module:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
```

3. Apply database migrations:

```bash
poetry run python -m django migrate
```

4. Start the development server:

```bash
poetry run python -m django runserver 0.0.0.0:8000
```

> Note: This project does not include `manage.py`. Use `python -m django` and set `DJANGO_SETTINGS_MODULE` explicitly.

## Docker deployment

To run the full stack using Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up --build
```

This starts:
- `postgres-primary` (PostgreSQL)
- `redis` (Redis cache and Celery broker)
- `api-gateway` (Django app)
- `celery-worker` (Celery worker)

The API will be available at `http://localhost:8000/`.

## Environment variables

Production settings use these variables:

- `DJANGO_SETTINGS_MODULE=config.settings.base`
- `DB_HOST` (default: `postgres-primary`)
- `DB_NAME` (default: `ledger_prod`)
- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (default: `postgres`)
- `DB_PORT` (default: `5432`)
- `REDIS_URL` (default: `redis://redis:6379/0`)
- `CELERY_BROKER_URL` (default: `redis://redis:6379/1`)
- `CELERY_RESULT_BACKEND` (recommended: `redis://redis:6379/2`)

## API Endpoints

### Transfer

`POST /api/v1/transfers`

Headers:
- `Content-Type: application/json`
- `X-Idempotency-Key: <unique-key>`

Body:

```json
{
  "source_account_id": "<uuid>",
  "destination_account_id": "<uuid>",
  "amount": 100
}
```

Success response:

```json
{
  "transaction_id": "<uuid>",
  "status": "AUTHORIZED",
  "message": "Funds successfully captured and settled globally."
}
```

### Account endpoints

- `GET /api/v1/accounts/` — list all accounts
- `GET /api/v1/accounts/<uuid:id>/` — retrieve one account by ID

### Ledger entry endpoints

- `GET /api/v1/ledger-entries/` — list all ledger entries
- `GET /api/v1/ledger-entries/<uuid:id>/` — retrieve one ledger entry by ID

## Example requests

List accounts:

```bash
curl http://localhost:8000/api/v1/accounts/
```

Get a single account:

```bash
curl http://localhost:8000/api/v1/accounts/<uuid>/
```

List ledger entries:

```bash
curl http://localhost:8000/api/v1/ledger-entries/
```

Get a single ledger entry:

```bash
curl http://localhost:8000/api/v1/ledger-entries/<uuid>/
```

## Swagger / API documentation

- `http://localhost:8000/api/schema/` — raw OpenAPI schema
- `http://localhost:8000/api/schema/swagger-ui/` — interactive Swagger UI

## Tests

Run the Django test suite with local settings:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
poetry run python -m django test
```

The project currently includes 9 tests covering transfer behavior, account endpoints, and ledger entry endpoints.

## Webhooks

Successful ledger transfers create records in `src.domains.webhooks.models.outbox.WebhookOutbox`.

Webhook delivery is processed asynchronously by Celery.

Example worker command:

```bash
celery -A config worker --loglevel=info -Q webhooks
```

## Metrics

`django-prometheus` is integrated for application metrics. Prometheus-compatible endpoints are exposed by the Django URL configuration.

## Notes

- There is no `manage.py` script in this repository.
- Local development uses SQLite via `config.settings.local`.
- Production deployment expects PostgreSQL and Redis.
