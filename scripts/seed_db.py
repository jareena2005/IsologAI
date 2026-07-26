import os
import sys
import django
from datetime import datetime, timedelta

# Add root folder and apps to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'apps'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

import random
from apps.logs.models import LogEntry
from apps.anomalies.models import Anomaly

SERVICES = ['auth-service', 'payment-service', 'database-service', 'frontend-service', 'notification-service']
NORMAL_MESSAGES = [
    "Database connection established successfully",
    "User login successful for email user@example.com",
    "GET /api/v1/items request received",
    "Sent verification email successfully",
    "Cache lookup hit for user profile",
    "Processing worker queue item #{}",
    "API call responded with 200 OK in {}ms",
]

def seed():
    print("Clearing database log and anomaly records...")
    Anomaly.objects.all().delete()
    LogEntry.objects.all().delete()

    print("Generating 100 synthetic logs to simulate history...")
    logs = []
    base_time = datetime.now() - timedelta(days=2)

    for i in range(100):
        service = random.choice(SERVICES)
        severity = random.choices(['INFO', 'DEBUG', 'WARN', 'ERROR'], weights=[75, 15, 8, 2])[0]
        message = random.choice(NORMAL_MESSAGES).format(random.randint(1, 100))
        timestamp = base_time + timedelta(minutes=15 * i)

        log = LogEntry(
            service_name=service,
            severity=severity,
            message=message,
            timestamp=timestamp,
            raw_payload={"seed": True, "index": i}
        )
        logs.append(log)

    LogEntry.objects.bulk_create(logs)
    print(f"Created {LogEntry.objects.count()} log records.")

    print("Retraining the initial model on seeded data...")
    try:
        from apps.detection.tasks import retrain_model
        result = retrain_model()
        print(f"Retraining result: {result}")
    except Exception as e:
        print(f"Model retraining skipped (ensure django dependencies are installed in your virtual env): {e}")

if __name__ == '__main__':
    seed()
