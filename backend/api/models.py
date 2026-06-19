from django.db import models
from django.utils import timezone

from utils.models import BaseModel


class MetricSnapshot(BaseModel):
    """Point-in-time metric value used by public overview dashboards."""

    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'
    STATUS_CHOICES = [
        (STATUS_OK, 'OK'),
        (STATUS_ERROR, 'Error'),
    ]

    metric_key = models.CharField(max_length=120, db_index=True)
    source = models.CharField(max_length=80, db_index=True)
    label = models.CharField(max_length=160, blank=True)
    value = models.DecimalField(max_digits=40, decimal_places=8, null=True, blank=True)
    unit = models.CharField(max_length=40, blank=True)
    observed_at = models.DateTimeField(default=timezone.now, db_index=True)
    dimensions = models.JSONField(default=dict, blank=True)
    raw_payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OK, db_index=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-observed_at', '-created_at']
        indexes = [
            models.Index(fields=['metric_key', '-observed_at'], name='api_metric_observed_idx'),
            models.Index(fields=['source', '-observed_at'], name='api_source_observed_idx'),
        ]

    def __str__(self):
        return f'{self.metric_key}={self.value} ({self.source})'
