# Industrial Ledger Backend

Industrial Ledger Backend is a transactional, double-entry ledger service built with Django, Django REST Framework, Celery, PostgreSQL, and Redis.

## Overview

This service is designed for systems that demand strong consistency, auditability, idempotent payments, and reliable webhook delivery.

Key features:
- Transactional debit/credit ledger transfers
- Account listing and retrieval APIs
- Ledger entry listing and retrieval APIs
- Idempotent transfer requests using `X-Idempotency-Key`
- Database row locking with `select_for_update()` to prevent concurrent balance corruption
- Webhook outbox persistence for deferred event delivery
- Prometheus metrics via `django-prometheus`
- OpenAPI schema and Swagger UI documentation
- Kubernetes and Docker Compose deployment examples

## Architecture

The project follows a modular service structure with a clear separation of concerns.

- `src/domains/ledger/`: ledger models, validation, and transfer business logic
- `src/domains/webhooks/`: webhook outbox persistence and Celery delivery processing
- `src/api/v1/`: REST API views, serializers, and tests
- `config/`: Django settings, URL routing, and environment configuration

### Transfer workflow

1. Client submits `POST /api/v1/transfers` with source account, destination account, amount, and `X-Idempotency-Key`.
2. The API validates the payload and forwards it to `LedgerTransferService`.
3. The service loads accounts using `select_for_update()` inside a transaction.
4. The source account is debited and the destination account is credited.
5. A `LedgerEntry` and webhook outbox record are created in the same transaction.
6. Celery workers later process outbox records and deliver webhook events.

### Design principles

- **Consistency:** transfers execute in one transactional boundary.
- **Idempotency:** repeated transfer requests with the same key are safe.
- **Observability:** API schema and Prometheus metrics are exposed.
- **Modularity:** API, domain logic, and webhook delivery are separated.

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

- `config/` — settings, URL routing, and deployment configuration
- `src/api/v1/` — API views, serializers, and tests
- `src/domains/ledger/` — ledger domain models and services
- `src/domains/webhooks/` — webhook outbox persistence and Celery integration
- `deploy/docker/django/Dockerfile.prod` — production Docker image build
- `docker-compose.prod.yml` — production-style Docker Compose stack
- `deploy/k8/` — Kubernetes manifests and `kustomization.yaml`

## Requirements

- Python 3.11
- Poetry (recommended)
- PostgreSQL and Redis for production
- SQLite for local development

## Local development

Local development uses `config.settings.local` with SQLite and in-memory caching.

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

> This repository does not include `manage.py`; use `python -m django` with `DJANGO_SETTINGS_MODULE`.

## Docker Compose deployment

Start the production-style local stack:

```bash
docker compose -f docker-compose.prod.yml up --build
```

Services started:
- `postgres-primary` — PostgreSQL
- `redis` — Redis broker/cache
- `api-gateway` — Django API
- `celery-worker` — Celery task worker

The API is available at `http://localhost:8000/`.

## Kubernetes deployment

A Kubernetes example is provided in `deploy/k8/`.

Build the application image:

```bash
docker build -t ledger-api:latest -f deploy/docker/django/Dockerfile.prod .
```

Apply the manifests with Kustomize:

```bash
kubectl apply -k deploy/k8/
```

## Environment variables

Production settings use:

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

### Health

`GET /api/v1/health/`

Response:

```json
{
  "status": "ok"
}
```

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
- `GET /api/v1/accounts/<uuid:id>/` — account details

### Ledger entry endpoints

- `GET /api/v1/ledger-entries/` — list ledger entries
- `GET /api/v1/ledger-entries/<uuid:id>/` — ledger entry details

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

Run tests with local settings:

```powershell
$env:DJANGO_SETTINGS_MODULE='config.settings.local'
poetry run python -m django test
```

Sample test output includes response debug output for request status and JSON body:

```text
RESPONSE [transfer-success]: status=201 body={'transaction_id': '...', 'status': 'AUTHORIZED', 'message': 'Funds successfully captured and settled globally.'}
RESPONSE [account-list]: status=200 body=[{...}]
RESPONSE [health-check]: status=200 body={'status': 'ok'}
...
```

The suite includes tests for transfer behavior, account endpoints, ledger entries, and health checks.

## Webhooks

Transfer completion creates webhook outbox records in `src/domains/webhooks/models/outbox.py`.

Webhook delivery is processed asynchronously by Celery.

Example worker command:

```bash
celery -A config worker --loglevel=info -Q webhooks
```

## Metrics

Prometheus metrics are exposed through `django-prometheus` and can be scraped by an observability stack.


`django-prometheus` provides application monitoring endpoints exposed by Django.

## Notes

- No `manage.py` file is present; use `python -m django` with `DJANGO_SETTINGS_MODULE`.
- Local development uses SQLite through `config.settings.local`.
- Production deployment expects PostgreSQL and Redis.
