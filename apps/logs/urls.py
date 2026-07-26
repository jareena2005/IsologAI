from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LogEntryViewSet, health_check

router = DefaultRouter()
router.register(r'', LogEntryViewSet, basename='logentry')

urlpatterns = [
    path('health/', health_check, name='health-check'),
    path('logs/', include(router.urls)),
]
