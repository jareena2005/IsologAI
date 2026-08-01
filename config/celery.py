import os
from celery import Celery

# Set default settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('IsoLogAI')

# Configure celery prefix parameters in Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically load tasks.py from all installed apps
app.autodiscover_tasks()


from celery.signals import worker_ready

@worker_ready.connect
def start_prometheus_server(sender, **kwargs):
    from prometheus_client import start_http_server
    try:
        start_http_server(8001)
        print("Prometheus metrics server started on port 8001")
    except Exception as e:
        print(f"Failed to start Prometheus metrics server: {e}")

