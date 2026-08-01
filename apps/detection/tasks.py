import logging
from celery import shared_task
from django.conf import settings
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly
from .feature_extraction import extract_features_model
from .model_manager import ModelManager
from .metrics import consumer_lag
import numpy as np
import redis

logger = logging.getLogger(__name__)

@shared_task
def score_log(log_id):
    """
    Celery task to score a specific LogEntry by ID.
    """
    try:
        log_entry = LogEntry.objects.get(id=log_id)
        
        if hasattr(log_entry, 'anomaly'):
            return f"LogEntry {log_id} already evaluated."
            
        features = extract_features_model(log_entry)
        manager = ModelManager()
        score, is_anomaly = manager.score_log(features)
        
        Anomaly.objects.create(
            log_entry=log_entry,
            score=score,
            is_anomaly=is_anomaly,
            model_version=manager.version
        )
        return f"Scored Log {log_id}: score={score:.4f}, is_anomaly={is_anomaly}"
    except LogEntry.DoesNotExist:
        return f"LogEntry {log_id} not found."
    except Exception as e:
        logger.error(f"Error scoring log {log_id}: {e}")
        return f"Error scoring log {log_id}: {str(e)}"

@shared_task
def retrain_model(contamination=0.05):
    """
    Celery task to fit Isolation Forest on all available historical logs.
    """
    try:
        logs = LogEntry.objects.all()
        if logs.count() < 10:
            return "Insufficient logs to train (need at least 10 entries)."
            
        X_train = []
        for log in logs:
            features = extract_features_model(log)
            X_train.append(features)
            
        X_train = np.array(X_train)
        
        manager = ModelManager()
        manager.retrain(X_train, contamination=contamination)
        return f"Model trained on {len(X_train)} samples. New version: {manager.version}"
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return f"Error training model: {str(e)}"

def update_consumer_lag():
    """Refresh the consumer lag gauge from Redis stream pending messages."""
    client = redis.Redis.from_url(settings.REDIS_URL)
    stream_name = settings.REDIS_STREAM_NAME
    group_name = settings.REDIS_STREAM_GROUP

    try:
        pending_info = client.xpending(stream_name, group_name)
        pending_count = None

        if hasattr(pending_info, 'pending'):
            pending_count = pending_info.pending
        elif isinstance(pending_info, dict):
            pending_count = pending_info.get('pending')

        if pending_count is None:
            for group in client.xinfo_groups(stream_name):
                group_name_value = group.get('name') if isinstance(group, dict) else None
                if group_name_value in (group_name, group_name.encode('utf-8')):
                    pending_count = group.get('pending', 0)
                    break

        consumer_lag.set(int(pending_count or 0))
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.warning("Unable to refresh consumer lag: %s", exc)
        consumer_lag.set(0)


@shared_task
def consume_stream():
    """
    Task to execute stream processing as a periodic Celery worker execution.
    """
    from .consumers import process_stream_messages
    update_consumer_lag()
    count = process_stream_messages(limit=100)
    return f"Processed {count} messages from stream."
