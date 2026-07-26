import pytest
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly

@pytest.mark.django_db
def test_anomaly_model():
    log = LogEntry.objects.create(
        service_name="auth-service",
        severity="INFO",
        message="User authentication successful"
    )
    anomaly = Anomaly.objects.create(
        log_entry=log,
        score=-0.123,
        is_anomaly=True,
        model_version="v1"
    )
    assert anomaly.id is not None
    assert anomaly.score == -0.123
    assert anomaly.is_anomaly is True
    assert "v1" in str(anomaly)
