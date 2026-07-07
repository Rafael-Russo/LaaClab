"""DRF viewset for the Alert CRUD API (mounted at ``/api/v1/`` — see
``alerts/urls.py``).

Alerts are read-only for regular users and writable by staff.
"""

from rest_framework import viewsets

from web.permissions import IsAdminOrReadOnly

from .models import Alert
from .serializers import AlertSerializer


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("game").all()
    serializer_class = AlertSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["game__slug", "severity"]
    ordering_fields = ["created_at"]
