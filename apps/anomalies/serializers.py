from rest_framework import serializers
from .models import Anomaly
from apps.logs.serializers import LogEntrySerializer

class AnomalySerializer(serializers.ModelSerializer):
    log_entry = LogEntrySerializer(read_only=True)
    log_entry_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Anomaly
        fields = ['id', 'log_entry', 'log_entry_id', 'score', 'is_anomaly', 'model_version', 'created_at']
        read_only_fields = ['id', 'created_at']
