from django.db import models
from django.utils import timezone

class LogEntry(models.Model):
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    service_name = models.CharField(max_length=100, db_index=True)
    severity = models.CharField(max_length=20, default='INFO', db_index=True)
    message = models.TextField()
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = 'Log Entries'
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.service_name} {self.severity}: {self.message[:50]}"
