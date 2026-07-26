from django.db import models
from django.utils import timezone
from apps.logs.models import LogEntry

class Anomaly(models.Model):
    log_entry = models.OneToOneField(
        LogEntry, 
        on_delete=models.CASCADE, 
        related_name='anomaly',
        db_index=True
    )
    score = models.FloatField()
    is_anomaly = models.BooleanField(default=True)
    model_version = models.CharField(max_length=50, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name_plural = 'Anomalies'
        ordering = ['-created_at']

    def __str__(self):
        return f"Anomaly(log_id={self.log_entry.id}, score={self.score:.4f}, version={self.model_version})"
