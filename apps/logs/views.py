from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.conf import settings
from django.db import connection
from celery import current_app
import redis
from .models import LogEntry
from .serializers import LogEntrySerializer


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    def check_database():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            return "ok"
        except Exception as exc:
            return f"error: {exc}"

    def check_redis():
        try:
            client = redis.Redis.from_url(settings.REDIS_URL)
            client.ping()
            return "ok"
        except Exception as exc:
            return f"error: {exc}"

    def check_celery():
        try:
            result = current_app.control.inspect().ping()
            if not result:
                return "error: no workers responding"
            return "ok"
        except Exception as exc:
            return f"error: {exc}"

    database_status = check_database()
    redis_status = check_redis()
    celery_status = check_celery()

    overall_status = "ok" if all(
        status == "ok" for status in [database_status, redis_status, celery_status]
    ) else "error"

    payload = {
        "status": overall_status,
        "database": database_status,
        "redis": redis_status,
        "celery": celery_status,
    }

    return Response(payload, status=status.HTTP_200_OK if overall_status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE)


class LogEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LogEntry.
    Supports GET (list, retrieve) and POST (create log and push to stream).
    """
    queryset = LogEntry.objects.all()
    serializer_class = LogEntrySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def get_queryset(self):
        queryset = super().get_queryset()
        service_name = self.request.query_params.get('service_name')
        severity = self.request.query_params.get('severity')
        search = self.request.query_params.get('search')

        if service_name:
            queryset = queryset.filter(service_name__iexact=service_name)
        if severity:
            queryset = queryset.filter(severity__iexact=severity)
        if search:
            queryset = queryset.filter(message__icontains=search)
            
        return queryset
