from django.contrib import admin
from .models import Anomaly

@admin.register(Anomaly)
class AnomalyAdmin(admin.ModelAdmin):
    list_display = ('id', 'log_entry', 'score', 'is_anomaly', 'model_version', 'created_at')
    list_filter = ('is_anomaly', 'model_version', 'created_at')
    search_fields = ('log_entry__service_name', 'log_entry__message')
