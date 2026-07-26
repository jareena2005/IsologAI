import pytest
import redis
from django.conf import settings
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly
from apps.detection.consumers import process_stream_messages


@pytest.fixture
def redis_client(settings):
    return redis.Redis.from_url(settings.REDIS_URL)


@pytest.fixture(autouse=True)
def clean_stream_and_group(redis_client, settings):
    """Ensure a clean stream + consumer group before each test."""
    stream_name = settings.REDIS_STREAM_NAME
    group_name = settings.REDIS_STREAM_GROUP
    try:
        redis_client.delete(stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.xgroup_destroy(stream_name, group_name)
    except redis.exceptions.ResponseError:
        pass
    yield
    try:
        redis_client.delete(stream_name)
    except redis.exceptions.ResponseError:
        pass
    try:
        redis_client.xgroup_destroy(stream_name, group_name)
    except redis.exceptions.ResponseError:
        pass


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
