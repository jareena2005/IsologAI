import logging
import json
from django.conf import settings
import redis

logger = logging.getLogger(__name__)

def push_log_to_stream(log_entry):
    """
    Pushes a validated LogEntry instance to the Redis Stream using XADD.
    """
    logger.info("push_log_to_stream called for log id=%s", getattr(log_entry, 'id', None))
    try:
        redis_client = redis.Redis.from_url(settings.REDIS_URL)

        payload = {
            'id': str(log_entry.id),
            'timestamp': log_entry.timestamp.isoformat(),
            'service_name': log_entry.service_name,
            'severity': log_entry.severity,
            'message': log_entry.message,
            'raw_payload': json.dumps(log_entry.raw_payload)
        }

        stream_name = settings.REDIS_STREAM_NAME
        entry_id = redis_client.xadd(stream_name, payload)
        logger.info("Pushed LogEntry %s to stream %s (ID: %s)", log_entry.id, stream_name, entry_id)
        return entry_id
    except Exception:
        logger.exception("Error pushing LogEntry %s to Redis stream", getattr(log_entry, 'id', None))
        return None
