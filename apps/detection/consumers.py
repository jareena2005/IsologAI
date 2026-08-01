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
    consumer_dlq_size,
    logs_scored_total,
    messages_dead_lettered_total,
    scoring_latency_seconds,
)

logger = logging.getLogger(__name__)


def _get_pending_delivery_count(r, stream_name, group_name, msg_id):
    """Return the delivery count for a message from pending-entry metadata."""
    try:
        pending_entries = r.xpending_range(stream_name, group_name, min='-', max='+', count=1000)
    except Exception:
        return 0

    msg_id_value = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else str(msg_id)

    for entry in pending_entries:
        if isinstance(entry, dict):
            candidate_id = entry.get('message_id') or entry.get('id')
            delivery_count = entry.get('times_delivered') or entry.get('delivery_count')
        elif isinstance(entry, (tuple, list)) and len(entry) >= 4:
            candidate_id = entry[0]
            delivery_count = entry[3]
        else:
            continue

        if isinstance(candidate_id, bytes):
            candidate_id = candidate_id.decode('utf-8')

        if str(candidate_id) == msg_id_value:
            return int(delivery_count or 0)

    return 0


def _move_to_dlq(r, stream_name, group_name, msg_id, payload, failure_reason, delivery_count):
    """Move a failed message to the dead-letter stream and acknowledge it in the source stream."""
    dlq_stream_name = settings.REDIS_DLQ_STREAM_NAME
    original_fields = {k.decode('utf-8'): v.decode('utf-8') for k, v in payload.items()}
    dlq_payload = {
        **original_fields,
        'original_message_id': original_fields.get('id', msg_id.decode('utf-8')),
        'failure_reason': f'{failure_reason.__class__.__name__}: {failure_reason}',
        'delivery_count': str(delivery_count),
    }
    r.xadd(dlq_stream_name, dlq_payload)
    r.xack(stream_name, group_name, msg_id)
    consumer_dlq_size.set(r.xlen(dlq_stream_name))
    messages_dead_lettered_total.inc()


def process_stream_messages(limit=100):
    """
    Connects to Redis Stream, reads pending messages in the consumer group,
    scores them using the ModelManager, creates Anomaly instances, and acknowledges messages.
    """
    r = redis.Redis.from_url(settings.REDIS_URL)
    stream_name = settings.REDIS_STREAM_NAME
    group_name = settings.REDIS_STREAM_GROUP
    consumer_name = settings.REDIS_STREAM_CONSUMER

    try:
        r.xgroup_create(stream_name, group_name, id='0', mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise e

    message_batches = []
    for message_id in ('>', '0'):
        try:
            stream_messages = r.xreadgroup(group_name, consumer_name, {stream_name: message_id}, count=limit)
        except redis.exceptions.ResponseError:
            stream_messages = []
        if stream_messages:
            message_batches.extend(stream_messages)

    processed_count = 0
    if not message_batches:
        return processed_count

    manager = ModelManager()
    processed_ids = set()

    for stream, stream_msgs in message_batches:
        for msg_id, payload in stream_msgs:
            msg_key = msg_id.decode('utf-8') if isinstance(msg_id, bytes) else str(msg_id)
            if msg_key in processed_ids:
                continue
            processed_ids.add(msg_key)

            data = {k.decode('utf-8'): v.decode('utf-8') for k, v in payload.items()}
            delivery_count = _get_pending_delivery_count(r, stream_name, group_name, msg_id)
            if not data.get('id'):
                data['id'] = '0'

            try:
                log_id = int(data['id'])
                log_entry = LogEntry.objects.get(id=log_id)

                if not hasattr(log_entry, 'anomaly'):
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

                r.xack(stream_name, group_name, msg_id)
                processed_count += 1
            except LogEntry.DoesNotExist:
                logger.warning(f"LogEntry {data.get('id')} not found in DB. Acking and ignoring.")
                r.xack(stream_name, group_name, msg_id)
            except Exception as e:
                logger.error(f"Error processing stream message {msg_id}: {e}")
                if delivery_count > settings.CONSUMER_MAX_RETRIES:
                    _move_to_dlq(r, stream_name, group_name, msg_id, payload, e, delivery_count)
                else:
                    logger.info("Message %s failed with delivery_count=%s; leaving pending for retry", msg_id, delivery_count)

    return processed_count
