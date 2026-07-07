"""DRF viewsets for the forum resources of the CRUD API (mounted at
``/api/v1/`` — see ``community/urls.py``).

Topics, replies and comments are writable by their owner, with the author
set from the request.
"""

from rest_framework import viewsets

from core.permissions import IsForumModeratorOrAuthor

from .models import GameComment, Reply, Topic
from .serializers import GameCommentSerializer, ReplySerializer, TopicSerializer


class TopicViewSet(viewsets.ModelViewSet):
    queryset = Topic.objects.select_related("game", "author").all()
    serializer_class = TopicSerializer
    permission_classes = [IsForumModeratorOrAuthor]
    filterset_fields = ["game__slug", "type"]
    search_fields = ["title", "body"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ReplyViewSet(viewsets.ModelViewSet):
    queryset = Reply.objects.select_related("author", "topic").all()
    serializer_class = ReplySerializer
    permission_classes = [IsForumModeratorOrAuthor]
    filterset_fields = ["topic"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class GameCommentViewSet(viewsets.ModelViewSet):
    queryset = GameComment.objects.select_related("author", "game").all()
    serializer_class = GameCommentSerializer
    permission_classes = [IsForumModeratorOrAuthor]
    filterset_fields = ["game__slug"]
    ordering_fields = ["created_at"]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
