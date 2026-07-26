import numpy as np
from datetime import datetime

SEVERITY_MAPPING = {
    'DEBUG': 0.0,
    'INFO': 1.0,
    'WARN': 2.0,
    'WARNING': 2.0,
    'ERROR': 3.0,
    'CRITICAL': 4.0,
}

def extract_features_dict(log_data):
    """
    Extract numeric features from log data dictionary (e.g. from Redis Stream payload).
    """
    severity = str(log_data.get('severity', 'INFO')).upper()
    severity_val = SEVERITY_MAPPING.get(severity, 1.0)

    message = str(log_data.get('message', ''))
    msg_len = float(len(message))
    num_digits = float(sum(c.isdigit() for c in message))
    num_uppercase = float(sum(c.isupper() for c in message))

    service = str(log_data.get('service_name', ''))
    service_len = float(len(service))

    timestamp_str = log_data.get('timestamp', '')
    hour_val = 0.0
    if timestamp_str:
        try:
            # Parse ISO formats safely (replacing Z with UTC timezone)
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            hour_val = float(dt.hour)
        except ValueError:
            pass

    return [severity_val, msg_len, num_digits, num_uppercase, service_len, hour_val]

def extract_features_model(log_entry):
    """
    Extract numeric features from a LogEntry Django model instance.
    """
    log_data = {
        'severity': log_entry.severity,
        'message': log_entry.message,
        'service_name': log_entry.service_name,
        'timestamp': log_entry.timestamp.isoformat()
    }
    return extract_features_dict(log_data)
