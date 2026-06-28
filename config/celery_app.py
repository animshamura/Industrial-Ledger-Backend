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
