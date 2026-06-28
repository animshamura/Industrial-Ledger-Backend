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
