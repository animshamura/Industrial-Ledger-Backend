# Industrial Ledger Backend

A high-concurrency, double-entry transactional ledger backend engine built with Django, Django REST Framework, Celery, PostgreSQL, and Redis.

## Overview

Industrial Ledger Backend is a transaction-safe ledger backend service designed for financial systems that require auditability, idempotent API behavior, and low-latency transfer processing.

The system enforces double-entry accounting through explicit debit/credit ledger entries and protects balance updates with Django database transactions. It also decouples external webhook delivery with an outbox pattern and asynchronous Celery processing, minimizing the risk of lost events during transfer handling.

Key capabilities:
- REST API for ledger transfers with explicit debit/credit accounting
- Idempotent request handling both at the API layer and by ledger entry uniqueness
- Database-level locking with `select_for_update()` for concurrent balance updates
- Webhook outbox persistence with retry-safe Celery delivery
- Redis-backed response caching and concurrent-flight protection for idempotent requests
- Prometheus-ready metrics via `django-prometheus`

## Architecture

- `config/` - Django project configuration and deployment settings
- `src/api/v1/` - REST API view(s) for ledger operations
- `src/domains/ledger/` - ledger domain models and transfer service logic
- `src/domains/webhooks/` - webhook outbox models and Celery task processing
- `deploy/docker/django/Dockerfile.prod` - production Docker image build
- `docker-compose.prod.yml` - example deployment stack for PostgreSQL, Redis, Django, and Celery

## Requirements

- Python 3.11
- PostgreSQL
- Redis
- Poetry (project uses `pyproject.toml`)

## Environment

The application relies on these environment variables:

- `DJANGO_SETTINGS_MODULE=config.settings.base`
- `DB_HOST` (default: `postgres-primary`)
- `DB_NAME` (default: `ledger_prod`)
- `DB_USER` (default: `postgres`)
- `DB_PASSWORD` (default: `postgres`)
- `DB_PORT` (default: `5432`)
- `REDIS_URL` (default: `redis://redis:6379/0`)
- `CELERY_BROKER_URL` (default: `redis://redis:6379/1`)
- `CELERY_RESULT_BACKEND` (recommended: `redis://redis:6379/2`)

## Local Deployment with Docker Compose

Start the service stack using Docker Compose:

```bash
docker compose -f docker-compose.prod.yml up --build
```

This brings up:
- `postgres-primary` - PostgreSQL database
- `redis` - Redis cache and Celery broker
- `api-gateway` - Django app serving the ledger API
- `celery-worker` - Celery worker processing webhook events

## API Usage

### Transfer Endpoint

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

Error responses include validation issues, missing headers, or system exceptions.

## Webhooks

Successful ledger transfers create outbox records in `src.domains.webhooks.models.outbox.WebhookOutbox`.

A Celery task named `process_outbox_queue` retries failed delivery attempts and sends event payloads to the configured external webhook endpoint.

## Running Celery

The repository includes a Celery app factory in `config/celery_app.py`.

Example command:

```bash
celery -A config worker --loglevel=info -Q webhooks
```

## Metrics

`django-prometheus` is integrated for application observability.

Prometheus endpoints are mounted through the project URL configuration and can be scraped by a monitoring system.

## Notes

- There is no `manage.py` script in this repository; Django should be executed with the configured `DJANGO_SETTINGS_MODULE`.
- The service is designed for deployment via Docker and a production-style container workflow.

## License

Specify your license here.
