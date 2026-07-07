"""DRF viewsets — the CRUD API mounted at ``/api/v1/``.

Alerts are read-only for regular users and writable by staff. Forum
resources (topics, replies, comments) are writable by their owner, with the
author set from the request. Catalogue (games/genres) and library viewsets
live in ``catalog/rest.py``.
"""

from rest_framework import generics, viewsets

from .models import (
    Alert,
    GameComment,
    Reply,
    Topic,
    UserProfile,
)
from .permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from .serializers import (
    AlertSerializer,
    GameCommentSerializer,
    ReplySerializer,
    TopicSerializer,
    UserProfileSerializer,
)


class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.select_related("game").all()
    serializer_class = AlertSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ["game__slug", "severity"]
    ordering_fields = ["created_at"]


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.select_related("game", "author").all()
    serializer_class = TopicSerializer
    permission_classes = [IsAuthorOrReadOnly]
    filterset_fields = ["game__slug", "type"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ReplyViewSet(viewsets.ModelViewSet):
    queryset = Reply.objects.select_related("author", "topic").all()
    serializer_class = ReplySerializer
    permission_classes = [IsAuthorOrReadOnly]
    filterset_fields = ["topic"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class GameCommentViewSet(viewsets.ModelViewSet):
    queryset = GameComment.objects.select_related("author", "game").all()
    serializer_class = GameCommentSerializer
    permission_classes = [IsAuthorOrReadOnly]
    filterset_fields = ["game__slug"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class MeView(generics.RetrieveUpdateAPIView):
    """The authenticated user's profile (GET / PATCH)."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
