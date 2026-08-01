from django.test import Client
from apps.detection.metrics import (
    anomalies_detected_total,
    consumer_lag,
    logs_ingested_total,
    logs_scored_total,
    scoring_latency_seconds,
)


def test_metrics_endpoint_exposes_prometheus_output():
    logs_ingested_total.labels(service_name="payment-service").inc()
    anomalies_detected_total.inc()
    logs_scored_total.inc()
    scoring_latency_seconds.observe(0.42)
    consumer_lag.set(7)

    client = Client()
    response = client.get('/api/metrics/')

    assert response.status_code == 200
    body = response.content.decode()
    assert 'logs_ingested_total{' in body
    assert 'service_name="payment-service"' in body
    assert 'anomalies_detected_total' in body
    assert 'logs_scored_total' in body
    assert 'scoring_latency_seconds_bucket' in body
    assert 'consumer_lag' in body
