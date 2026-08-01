import pytest
import redis
from django.conf import settings
from apps.logs import signals as log_signals
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly
from apps.detection import metrics as detection_metrics
from apps.detection.consumers import process_stream_messages


@pytest.fixture
def redis_client(settings):
    return redis.Redis.from_url(settings.REDIS_URL)


@pytest.fixture(autouse=True)
def clean_stream_and_group(redis_client, settings, monkeypatch):
    """Ensure a clean stream + consumer group before each test."""
    monkeypatch.setattr(log_signals, "push_log_to_stream", lambda instance: None)
    stream_name = settings.REDIS_STREAM_NAME
    group_name = settings.REDIS_STREAM_GROUP
    dlq_stream_name = settings.REDIS_DLQ_STREAM_NAME
    try:
        redis_client.delete(stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.delete(dlq_stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.xgroup_destroy(stream_name, group_name)
    except redis.exceptions.ResponseError:
        pass
    detection_metrics.consumer_dlq_size.set(0)
    detection_metrics.messages_dead_lettered_total._value.set(0)
    yield
    try:
        redis_client.delete(stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.delete(dlq_stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.xgroup_destroy(stream_name, group_name)
    except redis.exceptions.ResponseError:
        pass
    detection_metrics.consumer_dlq_size.set(0)
    detection_metrics.messages_dead_lettered_total._value.set(0)


@pytest.mark.django_db(transaction=True)
def test_process_stream_messages_creates_anomaly(redis_client, settings):
    log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Timeout calling downstream",
        raw_payload={"retries": 3},
    )

    stream_name = settings.REDIS_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "service_name": log.service_name,
        "severity": log.severity,
        "message": log.message,
        "raw_payload": "{}",
    })

    processed = process_stream_messages(limit=10)

    assert processed >= 1
    anomaly = Anomaly.objects.get(log_entry=log)
    assert isinstance(anomaly.score, float)
    assert isinstance(anomaly.is_anomaly, bool)


@pytest.mark.django_db(transaction=True)
def test_process_stream_messages_skips_already_scored(redis_client, settings):
    log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Timeout calling downstream",
        raw_payload={"retries": 3},
    )
    Anomaly.objects.create(log_entry=log, score=0.1, is_anomaly=False, model_version="test")

    stream_name = settings.REDIS_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "service_name": log.service_name,
        "severity": log.severity,
        "message": log.message,
        "raw_payload": "{}",
    })

    process_stream_messages(limit=10)

    assert Anomaly.objects.filter(log_entry=log).count() == 1


@pytest.mark.django_db(transaction=True)
def test_process_stream_messages_handles_missing_log_entry(redis_client, settings):
    stream_name = settings.REDIS_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": "999999",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "service_name": "ghost-service",
        "severity": "ERROR",
        "message": "no matching log entry",
        "raw_payload": "{}",
    })

    processed = process_stream_messages(limit=10)

    assert processed == 0
    assert Anomaly.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_message_exceeding_retry_limit_is_dead_lettered_and_xacked(redis_client, settings, monkeypatch):
    log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Failed handler",
        raw_payload={"retries": 4},
    )

    stream_name = settings.REDIS_STREAM_NAME
    dlq_stream_name = settings.REDIS_DLQ_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "service_name": log.service_name,
        "severity": log.severity,
        "message": log.message,
        "raw_payload": "{}",
    })

    class FailingModelManager:
        version = "test"

        def score_log(self, features):
            raise RuntimeError("simulated failure")

    monkeypatch.setattr("apps.detection.consumers.ModelManager", FailingModelManager)

    for _ in range(settings.CONSUMER_MAX_RETRIES + 1):
        process_stream_messages(limit=10)

    pending = redis_client.xpending(stream_name, settings.REDIS_STREAM_GROUP)
    assert pending['pending'] == 0
    assert redis_client.xlen(dlq_stream_name) == 1

    dlq_messages = redis_client.xrange(dlq_stream_name)
    assert len(dlq_messages) == 1
    payload = dlq_messages[0][1]
    assert payload[b"original_message_id"] == str(log.id).encode("utf-8")
    assert payload[b"failure_reason"].startswith(b"RuntimeError")
    assert payload[b"delivery_count"].decode("utf-8") == str(settings.CONSUMER_MAX_RETRIES + 1)


@pytest.mark.django_db(transaction=True)
def test_message_below_retry_limit_is_retried_not_dead_lettered(redis_client, settings, monkeypatch):
    log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Retryable failure",
        raw_payload={"retries": 2},
    )

    stream_name = settings.REDIS_STREAM_NAME
    dlq_stream_name = settings.REDIS_DLQ_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "service_name": log.service_name,
        "severity": log.severity,
        "message": log.message,
        "raw_payload": "{}",
    })

    class FailingModelManager:
        version = "test"

        def score_log(self, features):
            raise RuntimeError("retryable")

    monkeypatch.setattr("apps.detection.consumers.ModelManager", FailingModelManager)

    for _ in range(settings.CONSUMER_MAX_RETRIES - 1):
        process_stream_messages(limit=10)

    assert redis_client.xlen(dlq_stream_name) == 0
    pending = redis_client.xpending(stream_name, settings.REDIS_STREAM_GROUP)
    assert pending['pending'] == 1


@pytest.mark.django_db(transaction=True)
def test_metrics_update_after_dead_letter_event(redis_client, settings, monkeypatch):
    log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Metric failure",
        raw_payload={"retries": 1},
    )

    stream_name = settings.REDIS_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(log.id),
        "timestamp": log.timestamp.isoformat(),
        "service_name": log.service_name,
        "severity": log.severity,
        "message": log.message,
        "raw_payload": "{}",
    })

    class FailingModelManager:
        version = "test"

        def score_log(self, features):
            raise RuntimeError("metrics")

    monkeypatch.setattr("apps.detection.consumers.ModelManager", FailingModelManager)

    for _ in range(settings.CONSUMER_MAX_RETRIES + 1):
        process_stream_messages(limit=10)

    assert detection_metrics.consumer_dlq_size._value.get() == 1
    assert detection_metrics.messages_dead_lettered_total._value.get() == 1


@pytest.mark.django_db(transaction=True)
def test_one_bad_message_does_not_block_other_messages_in_batch(redis_client, settings, monkeypatch):
    good_log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Good message",
        raw_payload={"retries": 1},
    )
    bad_log = LogEntry.objects.create(
        service_name="payment-service",
        severity="ERROR",
        message="Bad message",
        raw_payload={"retries": 1},
    )

    stream_name = settings.REDIS_STREAM_NAME
    redis_client.xadd(stream_name, {
        "id": str(bad_log.id),
        "timestamp": bad_log.timestamp.isoformat(),
        "service_name": bad_log.service_name,
        "severity": bad_log.severity,
        "message": bad_log.message,
        "raw_payload": "{}",
    })
    redis_client.xadd(stream_name, {
        "id": str(good_log.id),
        "timestamp": good_log.timestamp.isoformat(),
        "service_name": good_log.service_name,
        "severity": good_log.severity,
        "message": good_log.message,
        "raw_payload": "{}",
    })

    class MixedModelManager:
        version = "test"

        def score_log(self, features):
            if features[1] < 10:
                raise RuntimeError("should not stop batch")
            return 0.1, False

    monkeypatch.setattr("apps.detection.consumers.ModelManager", MixedModelManager)

    processed = process_stream_messages(limit=10)

    assert processed >= 1
    assert Anomaly.objects.filter(log_entry=good_log).count() == 1
