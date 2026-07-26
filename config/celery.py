import os
from celery import Celery

# Set default settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('IsoLogAI')

# Configure celery prefix parameters in Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically load tasks.py from all installed apps
app.autodiscover_tasks()
