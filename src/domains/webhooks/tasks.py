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
