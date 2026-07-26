from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.logs.urls')),
    path('api/anomalies/', include('apps.anomalies.urls')),
]
