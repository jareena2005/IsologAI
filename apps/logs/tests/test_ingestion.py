import pytest
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APIClient
from apps.logs.models import LogEntry

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db(transaction=True)
@patch('apps.logs.signals.push_log_to_stream')
def test_log_ingestion_api(mock_push, api_client):
    url = '/api/logs/'
    data = {
        "service_name": "payment-service",
        "severity": "ERROR",
        "message": "Connection to payment gateway timed out",
        "raw_payload": {"retries": 3}
    }
    
    response = api_client.post(url, data, format='json')
    
    assert response.status_code == status.HTTP_201_CREATED
    
    log = LogEntry.objects.first()
    assert log.service_name == "payment-service"
    assert log.severity == "ERROR"
    assert log.raw_payload == {"retries": 3}
    
    # Verify that the helper was triggered to publish the event to Redis Stream
    mock_push.assert_called_once_with(log)


@pytest.mark.django_db(transaction=True)
def test_log_ingestion_pushes_to_real_redis(api_client, settings):
    import redis
    r = redis.Redis.from_url(settings.REDIS_URL)
    stream_name = settings.REDIS_STREAM_NAME
    initial_len = r.xlen(stream_name)

    url = '/api/logs/'
    data = {
        "service_name": "payment-service",
        "severity": "ERROR",
        "message": "Connection to payment gateway timed out",
        "raw_payload": {"retries": 3}
    }
    response = api_client.post(url, data, format='json')

    assert response.status_code == status.HTTP_201_CREATED

    final_len = r.xlen(stream_name)
    assert final_len == initial_len + 1

    entries = r.xrange(stream_name, count=final_len)
    last_entry_id, last_entry_data = entries[-1]
    decoded = {k.decode(): v.decode() for k, v in last_entry_data.items()}
    log = LogEntry.objects.first()
    assert decoded['id'] == str(log.id)
    assert decoded['service_name'] == "payment-service"

