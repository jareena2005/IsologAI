from rest_framework import serializers
from .models import LogEntry

class LogEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LogEntry
        fields = ['id', 'timestamp', 'service_name', 'severity', 'message', 'raw_payload']
        read_only_fields = ['id']
