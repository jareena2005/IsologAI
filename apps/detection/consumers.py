import logging
import time
import redis
from django.conf import settings
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly
from .feature_extraction import extract_features_dict
from .model_manager import ModelManager
from .metrics import (
    anomalies_detected_total,
    logs_scored_total,
    scoring_latency_seconds,
)

logger = logging.getLogger(__name__)

def process_stream_messages(limit=100):
    """
    Connects to Redis Stream, reads pending messages in the consumer group,
    scores them using the ModelManager, creates Anomaly instances, and acknowledges messages.
    """
    r = redis.Redis.from_url(settings.REDIS_URL)
    stream_name = settings.REDIS_STREAM_NAME
    group_name = settings.REDIS_STREAM_GROUP
    consumer_name = settings.REDIS_STREAM_CONSUMER

    # Create consumer group if not present
    try:
        r.xgroup_create(stream_name, group_name, id='0', mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise e

    # Read messages from group ('>' gets messages not yet acknowledged/delivered to other consumers)
    messages = r.xreadgroup(group_name, consumer_name, {stream_name: '>'}, count=limit)
    
    processed_count = 0
    if not messages:
        return processed_count

    manager = ModelManager()

    for stream, stream_msgs in messages:
        for msg_id, payload in stream_msgs:
            # Decode byte arrays to utf-8 strings
            data = {k.decode('utf-8'): v.decode('utf-8') for k, v in payload.items()}
            
            try:
                log_id = int(data['id'])
                log_entry = LogEntry.objects.get(id=log_id)
                
                # Check if the log entry was already evaluated
                if not hasattr(log_entry, 'anomaly'):
                    # Extract features and query singleton model manager
                    features = extract_features_dict(data)
                    start_time = time.perf_counter()
                    score, is_anomaly = manager.score_log(features)
                    scoring_latency_seconds.observe(time.perf_counter() - start_time)
                    logs_scored_total.inc()
                    if is_anomaly:
                        anomalies_detected_total.inc()
                    
                    Anomaly.objects.create(
                        log_entry=log_entry,
                        score=score,
                        is_anomaly=is_anomaly,
                        model_version=manager.version
                    )
                
                # Acknowledge stream message
                r.xack(stream_name, group_name, msg_id)
                processed_count += 1
            except LogEntry.DoesNotExist:
                logger.warning(f"LogEntry {data.get('id')} not found in DB. Acking and ignoring.")
                r.xack(stream_name, group_name, msg_id)
            except Exception as e:
                logger.error(f"Error processing stream message {msg_id}: {e}")
                
    return processed_count
