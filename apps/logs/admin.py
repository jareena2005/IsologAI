from django.contrib import admin
from .models import LogEntry

@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'timestamp', 'service_name', 'severity', 'message_snippet')
    list_filter = ('service_name', 'severity', 'timestamp')
    search_fields = ('service_name', 'message')

    def message_snippet(self, obj):
        return obj.message[:50]
    message_snippet.short_description = 'Message snippet'
