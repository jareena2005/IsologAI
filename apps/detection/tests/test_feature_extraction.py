import pytest
from datetime import datetime
from apps.detection.feature_extraction import extract_features_dict, extract_features_model
from apps.logs.models import LogEntry

def test_extract_features_dict():
    log_data = {
        'severity': 'ERROR',
        'message': 'Failed login attempt 123 from IP',
        'service_name': 'auth-service',
        'timestamp': '2026-07-12T14:30:00Z'
    }
    
    features = extract_features_dict(log_data)
    
    # severity_val: ERROR -> 3.0
    assert features[0] == 3.0
    # msg_len: len('Failed login attempt 123 from IP') -> 32.0
    assert features[1] == 32.0
    # num_digits: 123 -> 3.0
    assert features[2] == 3.0
    # num_uppercase: F, I, P -> 3.0
    assert features[3] == 3.0
    # service_len: len('auth-service') -> 12.0
    assert features[4] == 12.0
    # hour_val: 14:30 -> 14.0
    assert features[5] == 14.0

@pytest.mark.django_db
def test_extract_features_model():
    log = LogEntry.objects.create(
        severity='WARN',
        message='High CPU limit threshold warning',
        service_name='monitor'
    )
    features = extract_features_model(log)
    
    # WARN -> 2.0
    assert features[0] == 2.0
    assert features[1] == len(log.message)
    assert features[4] == len(log.service_name)
