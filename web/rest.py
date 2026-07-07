"""DRF viewsets — the CRUD API mounted at ``/api/v1/``.

Alerts are read-only for regular users and writable by staff. Catalogue
(games/genres) and library viewsets live in ``catalog/rest.py``; forum
(topics/replies/comments) viewsets live in ``community/rest.py``.
"""

from rest_framework import generics, viewsets

from .models import (
    Alert,
    UserProfile,
)
from .permissions import IsAdminOrReadOnly
from .serializers import (
    AlertSerializer,
    UserProfileSerializer,
)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("game").all()
    serializer_class = AlertSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["game__slug", "severity"]
    ordering_fields = ["created_at"]


class MeView(generics.RetrieveUpdateAPIView):
    """The authenticated user's profile (GET / PATCH)."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
