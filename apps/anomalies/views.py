from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg
from .models import Anomaly
from .serializers import AnomalySerializer

class AnomalyViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Anomaly.
    Supports GET (list, retrieve) with filtering, and custom /stats/ action.
    """
    queryset = Anomaly.objects.all()
    serializer_class = AnomalySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        is_anomaly = self.request.query_params.get('is_anomaly')
        model_version = self.request.query_params.get('model_version')
        service_name = self.request.query_params.get('service_name')

        if is_anomaly is not None:
            queryset = queryset.filter(is_anomaly=is_anomaly.lower() in ['true', '1'])
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if service_name:
            queryset = queryset.filter(log_entry__service_name__iexact=service_name)
            
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Returns statistical analysis of anomalies.
        """
        total_logs = Anomaly.objects.count()
        anomaly_count = Anomaly.objects.filter(is_anomaly=True).count()
        avg_score = Anomaly.objects.aggregate(Avg('score'))['score__avg'] or 0.0

        service_breakdown = Anomaly.objects.filter(is_anomaly=True).values('log_entry__service_name').annotate(
            count=Count('id')
        ).order_by('-count')

        return Response({
            'total_scored_logs': total_logs,
            'anomaly_count': anomaly_count,
            'anomaly_rate': anomaly_count / total_logs if total_logs > 0 else 0.0,
            'avg_anomaly_score': avg_score,
            'service_breakdown': service_breakdown
        }, status=status.HTTP_200_OK)
