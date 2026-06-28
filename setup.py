#!/usr/bin/env python
import os
from pathlib import Path

def create_file(path: Path, content: str = "") -> None:
    """Safely creates directories and writes absolute file content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")
    print(f"✅ Created: {path.relative_to(Path.cwd())}")

def bootstrap_entire_system():
    print("🎬 Bootstrapping Complete Production-Grade Ledger Monorepo Engine...")
    base_dir = Path.cwd()

    # ================================================
    # 1. CORE SYSTEM DEPLOYMENT & ECOSYSTEM CONTEXTS
    # ================================================
    
    pyproject_content = """
[tool.poetry]
name = "industrial-ledger-backend"
version = "1.0.0"
description = "High-concurrency, double-entry transactional ledger backend engine."
authors = ["Enterprise Engineering Team <dev@company.com>"]

[tool.poetry.dependencies]
python = "^3.11"
django = "^5.0"
djangorestframework = "^3.15"
celery = {extras = ["redis"], version = "^5.3"}
redis = "^5.0"
psycopg = {extras = ["binary"], version = "^3.1"}
django-prometheus = "^2.3"
requests = "^2.31"
gunicorn = "^21.2"
uvicorn = {extras = ["standard"], version = "^0.27"}

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
"""
    create_file(base_dir / "pyproject.toml", pyproject_content)

    docker_compose_content = """
version: '3.8'

services:
  postgres-primary:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ledger_prod
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secure_password_here
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d ledger_prod"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api-gateway:
    build:
      context: .
      dockerfile: ./deploy/docker/django/Dockerfile.prod
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.base
      - DB_HOST=postgres-primary
      - DB_NAME=ledger_prod
      - DB_USER=postgres
      - DB_PASSWORD=secure_password_here
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    ports:
      - "8000:8000"
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_healthy

  celery-worker:
    build:
      context: .
      dockerfile: ./deploy/docker/django/Dockerfile.prod
    command: celery -A config worker --loglevel=info -Q webhooks
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.base
      - DB_HOST=postgres-primary
      - DB_NAME=ledger_prod
      - DB_USER=postgres
      - DB_PASSWORD=secure_password_here
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      postgres-primary:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  postgres_primary_data:
  redis_data:
"""
    create_file(base_dir / "docker-compose.prod.yml", docker_compose_content)

    dockerfile_prod_content = """
FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir poetry
COPY pyproject.toml ./
RUN poetry export --without-hashes -f requirements.txt --output requirements.txt

FROM python:3.11-slim AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*
COPY --from=builder /build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./config ./config
COPY ./src ./src
EXPOSE 8000
RUN useradd -u 8888 appuser && chown -R appuser:appuser /app
USER appuser
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "config.asgi:application"]
"""
    create_file(base_dir / "deploy/docker/django/Dockerfile.prod", dockerfile_prod_content)


    # ================================================
    # 2. SYSTEM ORCHESTRATION CONFIG LAYER (DJANGO)
    # ================================================
    
    settings_base_content = """
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "prod-hardened-fallback-key")
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'rest_framework',
    'django_prometheus',
    'src.domains.ledger.apps.LedgerConfig',
    'src.domains.webhooks.apps.WebhooksConfig',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'src.api.middleware.idempotency.RedisIdempotencyMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
DATABASE_ROUTERS = ['config.db_routers.cqrs_router.PrimaryReplicaRouter']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv("DB_NAME", "ledger_prod"),
        'USER': os.getenv("DB_USER", "postgres"),
        'PASSWORD': os.getenv("DB_PASSWORD", "postgres"),
        'HOST': os.getenv("DB_HOST", "postgres-primary"),
        'PORT': os.getenv("DB_PORT", "5432"),
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv("REDIS_URL", "redis://redis:6379/0"),
    }
}

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_PARSER_CLASSES': ['rest_framework.parsers.JSONParser'],
}

TIME_ZONE = 'UTC'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
"""
    create_file(base_dir / "config/settings/base.py", settings_base_content)
    create_file(base_dir / "config/settings/__init__.py")

    cqrs_router_content = """
class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return 'default'
    def db_for_write(self, model, **hints):
        return 'default'
    def allow_relation(self, obj1, obj2, **hints):
        return True
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'
"""
    create_file(base_dir / "config/db_routers/cqrs_router.py", cqrs_router_content)
    create_file(base_dir / "config/db_routers/__init__.py")

    celery_content = """
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
app = Celery('industrial_ledger')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.conf.update(
    broker_url=os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1"),
    result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2"),
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
app.autodiscover_tasks()
"""
    create_file(base_dir / "config/celery_app.py", celery_content)
    create_file(base_dir / "config/__init__.py", "from .celery_app import app as celery_app\n\n__all__ = ('celery_app',)")

    urls_content = """
from django.urls import path, include
from src.api.v1.views import LedgerTransferView

urlpatterns = [
    path('', include('django_prometheus.urls')),
    path('api/v1/transfers', LedgerTransferView.as_view(), name='ledger-transfer'),
]
"""
    create_file(base_dir / "config/urls.py", urls_content)
    create_file(base_dir / "config/wsgi.py", "from django.core.wsgi import get_wsgi_application\napplication = get_wsgi_application()")
    create_file(base_dir / "config/asgi.py", "from django.core.asgi import get_asgi_application\napplication = get_asgi_application()")


    # ================================================
    # 3. DOMAIN INTERFACES & TRANSPORT LAYER (API)
    # ================================================
    
    middleware_content = """
import json
from django.http import JsonResponse
from django.core.cache import caches

class RedisIdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.cache = caches['default']

    def __call__(self, request):
        if request.method not in ["POST", "PATCH", "PUT"]:
            return self.get_response(request)

        idempotency_key = request.headers.get("X-Idempotency-Key")
        if not idempotency_key:
            return self.get_response(request)

        cache_key = f"idempotency:{idempotency_key}"
        cached_data = self.cache.get(cache_key)
        
        if cached_data:
            if cached_data == "LOCK":
                return JsonResponse({"error": "Concurrent request flight in progress. Retry shortly."}, status=409)
            response_payload = json.loads(cached_data)
            return JsonResponse(response_payload['data'], status=response_payload['status'])

        self.cache.set(cache_key, "LOCK", timeout=120)
        response = self.get_response(request)

        if 200 <= response.status_code < 300:
            payload_to_cache = {
                "status": response.status_code,
                "data": json.loads(response.content.decode('utf-8')) if response.content else {}
            }
            self.cache.set(cache_key, json.dumps(payload_to_cache), timeout=86400)
        else:
            self.cache.delete(cache_key)

        return response
"""
    create_file(base_dir / "src/api/middleware/idempotency.py", middleware_content)
    create_file(base_dir / "src/api/middleware/__init__.py")

    views_content = """
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
"""
    create_file(base_dir / "src/api/v1/views.py", views_content)
    create_file(base_dir / "src/api/v1/__init__.py")
    create_file(base_dir / "src/api/__init__.py")


    # ================================================
    # 4. BUSINESS DOMAINS LAYER (BOUNDED CONTEXTS)
    # ================================================
    
    # --- DOMAIN: LEDGER ---
    ledger_apps_content = """
from django.apps import AppConfig
class LedgerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.domains.ledger'
"""
    create_file(base_dir / "src/domains/ledger/apps.py", ledger_apps_content)

    ledger_models_content = """
import uuid
from django.db import models
from django.core.exceptions import ValidationError

class Account(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.UUIDField(db_index=True, unique=True)
    balance = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LedgerEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    idempotency_key = models.CharField(max_length=255, unique=True, db_index=True)
    debit_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="debits")
    credit_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="credits")
    amount = models.BigIntegerField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def clean(self):
        if self.amount <= 0:
            raise ValidationError("Amount must be strictly positive.")
        if self.debit_account_id == self.credit_account_id:
            raise ValidationError("Debit and Credit accounts cannot be identical.")
"""
    create_file(base_dir / "src/domains/ledger/models/journal.py", ledger_models_content)
    create_file(base_dir / "src/domains/ledger/models/__init__.py", "from .journal import Account, LedgerEntry")

    ledger_service_content = """
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
"""
    create_file(base_dir / "src/domains/ledger/services/transfer.py", ledger_service_content)
    create_file(base_dir / "src/domains/ledger/services/__init__.py")
    create_file(base_dir / "src/domains/ledger/__init__.py")

    # --- DOMAIN: WEBHOOKS ---
    webhooks_apps_content = """
from django.apps import AppConfig
class WebhooksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src.domains.webhooks'
"""
    create_file(base_dir / "src/domains/webhooks/apps.py", webhooks_apps_content)

    webhooks_models_content = """
import uuid
from django.db import models

class WebhookOutbox(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default='PENDING', db_index=True)
    retry_count = models.IntegerField(default=0)
    last_attempt = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
"""
    create_file(base_dir / "src/domains/webhooks/models/outbox.py", webhooks_models_content)
    create_file(base_dir / "src/domains/webhooks/models/__init__.py", "from .outbox import WebhookOutbox")

    webhooks_tasks_content = """
import requests
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from src.domains.webhooks.models.outbox import WebhookOutbox

@shared_task(bind=True, max_retries=5, queue='webhooks')
def process_outbox_queue(self):
    with transaction.atomic():
        pending_events = WebhookOutbox.objects.select_for_update(skip_locked=True).filter(
            status__in=['PENDING', 'FAILED'],
            retry_count__lt=5
        )[:50]
        event_ids = [event.id for event in pending_events]
        WebhookOutbox.objects.filter(id__in=event_ids).update(status='PROCESSING', last_attempt=timezone.now())

    for event in pending_events:
        try:
            response = requests.post("https://api.externalpartner.com/v1/webhooks", json=event.payload, timeout=5)
            event.status = 'COMPLETED' if response.status_code == 200 else 'FAILED'
            if event.status == 'FAILED': event.retry_count += 1
        except requests.RequestException:
            event.status = 'FAILED'
            event.retry_count += 1
        event.save(update_fields=['status', 'retry_count', 'last_attempt'])
"""
    create_file(base_dir / "src/domains/webhooks/tasks.py", webhooks_tasks_content)
    create_file(base_dir / "src/domains/webhooks/__init__.py")
    create_file(base_dir / "src/domains/__init__.py")
    create_file(base_dir / "src/__init__.py")

    print("\n👑 Absolute Bootstrap Execution Successful! Run the stack using:")
    print("👉 docker-compose -f docker-compose.prod.yml up --build -d")

if __name__ == "__main__":
    bootstrap_entire_system()