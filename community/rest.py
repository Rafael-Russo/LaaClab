"""DRF viewsets for the forum resources of the CRUD API (mounted at
``/api/v1/`` — see ``community/urls.py``).

Topics, replies and comments are writable by their owner, with the author
set from the request.
"""

from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.gating import ModuleEnabled
from core.permissions import IsForumModerator, IsForumModeratorOrAuthor

from .models import GameComment, Reply, Topic
from .serializers import GameCommentSerializer, ReplySerializer, TopicSerializer


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.select_related("game", "author").all()
    serializer_class = TopicSerializer
    permission_classes = [ModuleEnabled("community"), IsForumModeratorOrAuthor]
    filterset_fields = ["game__slug", "type"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_perm("community.can_moderate_forum") or user.is_staff:
            return qs
        return qs.filter(is_hidden=False)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _moderate(self, request, **fields):
        topic = self.get_object()
        for key, value in fields.items():
            setattr(topic, key, value)
        topic.moderated_by = request.user
        topic.moderated_at = timezone.now()
        topic.save()
        return Response({"status": "ok", **fields})

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def hide(self, request, pk=None):
        return self._moderate(request, is_hidden=True)

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def unhide(self, request, pk=None):
        return self._moderate(request, is_hidden=False)

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def lock(self, request, pk=None):
        return self._moderate(request, is_locked=True)

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def unlock(self, request, pk=None):
        return self._moderate(request, is_locked=False)

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def pin(self, request, pk=None):
        return self._moderate(request, is_pinned=True)

    @action(detail=True, methods=["post"], permission_classes=[IsForumModerator])
    def unpin(self, request, pk=None):
        return self._moderate(request, is_pinned=False)


class ReplyViewSet(viewsets.ModelViewSet):
    queryset = Reply.objects.select_related("author", "topic").all()
    serializer_class = ReplySerializer
    permission_classes = [ModuleEnabled("community"), IsForumModeratorOrAuthor]
    filterset_fields = ["topic"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_perm("community.can_moderate_forum") or user.is_staff:
            return qs
        return qs.filter(is_hidden=False)

    def perform_create(self, serializer):
        topic = serializer.validated_data["topic"]
        user = self.request.user
        if topic.is_locked and not (user.has_perm("community.can_moderate_forum") or user.is_staff):
            raise PermissionDenied("tópico travado")
        serializer.save(author=user)


class GameCommentViewSet(viewsets.ModelViewSet):
    queryset = GameComment.objects.select_related("author", "game").all()
    serializer_class = GameCommentSerializer
    permission_classes = [ModuleEnabled("community"), IsForumModeratorOrAuthor]
    filterset_fields = ["game__slug"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if user.has_perm("community.can_moderate_forum") or user.is_staff:
            return qs
        return qs.filter(is_hidden=False)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
