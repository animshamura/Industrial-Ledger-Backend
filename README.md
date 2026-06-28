# Industrial Ledger Backend

Industrial Ledger Backend is a high-throughput, double-entry ledger service implemented with Django, Django REST Framework, Celery, PostgreSQL, and Redis.

## Overview

This project provides a transactional ledger backend suitable for financial systems that require strong consistency, auditability, and reliable webhook delivery.

The core system supports:
- REST-based ledger transfers with explicit debit and credit posting
- Account listing and retrieval
- Ledger entry listing and retrieval
- Idempotent transfer requests via `X-Idempotency-Key`
- Database locking via `select_for_update()` to prevent concurrent balance corruption
- Webhook outbox persistence for deferred event delivery
- Prometheus observability through `django-prometheus`
- OpenAPI schema and Swagger UI documentation

## Architecture and system design

The application is structured as a modular Django service with clean separation between API, domain logic, and integration components.

- `src/domains/ledger/` contains ledger models and transactional business logic.
- `src/domains/webhooks/` contains the webhook outbox model and asynchronous delivery behavior.
- `src/api/v1/` exposes the REST API and serialization layer.
- `config/` houses environment-specific settings, URL routing, and deployment configuration.

### Transfer workflow

1. Client submits `POST /api/v1/transfers` with source account, destination account, amount, and `X-Idempotency-Key`.
2. The API layer validates the request and hands it off to `LedgerTransferService`.
3. The service loads the account records with `select_for_update()` inside a transaction.
4. It debits the source account, credits the destination account, and creates a `LedgerEntry`.
5. A webhook outbox record is created in the same transaction to ensure delivery intent is persisted atomically.
6. Celery workers later process outbox records and deliver webhook payloads, retrying failures as needed.

### Design principles

- **Consistency:** ledger transfers are executed in a single transactional boundary.
- **Idempotency:** transfer requests are protected by a unique idempotency key.
- **Observability:** API schema and Prometheus metrics are exposed for monitoring.
- **Modularity:** API, ledger domain, and webhook delivery are separated into distinct components.

## Architecture diagram

```text
            +-----------------------------+
            |         API Client          |
            |   (web, mobile, integration) |
            +-------------+---------------+
                          |
                          v
            +-------------+---------------+
            |  Django REST API / Views    |
            |         src/api/v1/         |
            +------+------+---------------+
                   |      |
                   |      |
          +--------v--+  +v----------+
          | Transfer   |  | Read      |
          | service    |  | endpoints |
          | src/domains|  | (accounts,|
          | /ledger/   |  | ledger    |
          +-----+------+  | entries)  |
                |         +-----------+
                v
    +-----------+---------------------------+
    | PostgreSQL database                 |
    | - Account                           |
    | - LedgerEntry                       |
    | - idempotency key / indexes         |
    +-----------+---------------------------+
                |
                v
    +-------------------------------+
    | Webhook outbox                |
    | src/domains/webhooks/         |
    | - deferred delivery queue     |
    | - retry / status tracking     |
    +-------------------------------+
                |
                v
    +-------------------------------+
    | Celery worker                 |
    | - process outbox records      |
    | - send webhook events         |
    +-------------------------------+
```

## Repository structure

- `config/` — Django settings, URL definitions, and environment configuration
- `src/api/v1/` — API views, serializers, and tests
- `src/domains/ledger/` — ledger models, services, and transaction logic
- `src/domains/webhooks/` — webhook outbox persistence and Celery delivery
- `deploy/docker/django/Dockerfile.prod` — production Docker image build
- `docker-compose.prod.yml` — sample deployment stack for PostgreSQL, Redis, Django, and Celery

## Requirements

- Python 3.11
- Poetry (recommended) or equivalent dependency manager
- PostgreSQL and Redis for production deployments
- SQLite for local development

## Local development

Local development uses `config/settings/local.py` with SQLite and in-memory caching.

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

> Note: This repository does not include `manage.py`; use `python -m django` with `DJANGO_SETTINGS_MODULE`.

## Docker deployment

To start the full production-style stack:

```bash
docker compose -f docker-compose.prod.yml up --build
```

This starts:
- `postgres-primary` — PostgreSQL
- `redis` — Redis cache and Celery broker
- `api-gateway` — Django application
- `celery-worker` — Celery worker

The API is available at `http://localhost:8000/`.

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

Request body:

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

- `GET /api/v1/accounts/` — list accounts
- `GET /api/v1/accounts/<uuid:id>/` — retrieve account details

### Ledger entry endpoints

- `GET /api/v1/ledger-entries/` — list ledger entries
- `GET /api/v1/ledger-entries/<uuid:id>/` — retrieve ledger entry details

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

- `http://localhost:8000/api/schema/` — OpenAPI schema
- `http://localhost:8000/api/schema/swagger-ui/` — Swagger UI

## Tests

Run the Django test suite using local settings:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
poetry run python -m django test
```

This project includes tests for transfer behavior, account endpoints, and ledger entry endpoints.

## Webhooks

Transfer completion creates records in `src.domains.webhooks.models.outbox.WebhookOutbox`.

Webhook delivery is processed asynchronously by Celery.

Example worker command:

```bash
celery -A config worker --loglevel=info -Q webhooks
```

## Metrics

`django-prometheus` provides application monitoring endpoints exposed by Django.

## Notes

- No `manage.py` file is present; use `python -m django` with `DJANGO_SETTINGS_MODULE`.
- Local development uses SQLite through `config.settings.local`.
- Production deployment expects PostgreSQL and Redis.
