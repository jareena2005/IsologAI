from django.contrib import admin
from django.urls import path, include

from apps.detection.views import metrics_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.logs.urls')),
    path('api/anomalies/', include('apps.anomalies.urls')),
    path('api/metrics/', metrics_view, name='metrics'),
]
