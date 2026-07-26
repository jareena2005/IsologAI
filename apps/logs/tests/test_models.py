import pytest
from apps.logs.models import LogEntry

@pytest.mark.django_db
def test_create_log_entry():
    log = LogEntry.objects.create(
        service_name="auth-service",
        severity="INFO",
        message="User authentication successful",
        raw_payload={"user_id": 42}
    )
    assert log.id is not None
    assert log.severity == "INFO"
    assert log.raw_payload == {"user_id": 42}
    assert "auth-service" in str(log)
