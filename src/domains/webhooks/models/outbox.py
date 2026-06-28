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
