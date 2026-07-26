import time
import random
import urllib.request
import json
from datetime import datetime

SERVICES = ['auth-service', 'payment-service', 'database-service', 'frontend-service', 'notification-service']
LEVELS = ['INFO', 'DEBUG', 'WARN', 'ERROR', 'CRITICAL']

NORMAL_MESSAGES = [
    "Database connection established successfully",
    "User login successful for email user@example.com",
    "GET /api/v1/items request received",
    "Sent verification email successfully",
    "Cache lookup hit for user profile",
    "Processing worker queue item #{}",
    "API call responded with 200 OK in {}ms",
]

ANOMALY_MESSAGES = [
    "OUT OF MEMORY ERROR: Kernel killed process 94812",
    "DATABASE CORRUPTION: Block #2841 corrupt in tablespace indexes",
    "SUSPICIOUS LOGIN ATTEMPT: 50 failures from IP 198.51.100.42 within 10 seconds",
    "SECURITY WARNING: Unauthorized API call detected to internal admin route",
    "FATAL ERROR: NullPointerException in PaymentGateway.process()",
]

def generate_log():
    is_anomaly = random.random() < 0.1  # 10% anomaly rate
    service = random.choice(SERVICES)
    
    if is_anomaly:
        severity = random.choice(['WARN', 'ERROR', 'CRITICAL'])
        message = random.choice(ANOMALY_MESSAGES).format(random.randint(100, 999))
    else:
        severity = random.choices(LEVELS, weights=[70, 15, 10, 4, 1])[0]
        message = random.choice(NORMAL_MESSAGES).format(random.randint(1, 100))

    return {
        "service_name": service,
        "severity": severity,
        "message": message,
        "raw_payload": {
            "environment": "production",
            "process_id": random.randint(1000, 9999),
            "synthetic": True
        }
    }

def main():
    url = "http://127.0.0.1:8000/api/logs/"
    print(f"Starting synthetic log generator. Posting logs to {url}...")
    print("Press Ctrl+C to stop.")
    
    count = 0
    while True:
        log_data = generate_log()
        req = urllib.request.Request(
            url, 
            data=json.dumps(log_data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 201:
                    print(f"[{datetime.now().isoformat()}] Log posted: {log_data['severity']} - {log_data['message']}")
                    count += 1
        except Exception as e:
            print(f"Error posting log (is Django running?): {e}")
            
        time.sleep(random.uniform(0.5, 2.0))

if __name__ == '__main__':
    main()
