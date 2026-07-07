"""DRF viewsets — the CRUD API mounted at ``/api/v1/``.

Catalogue resources (games, genres, alerts) are read-only for regular users
and writable by staff. Forum resources (topics, replies, comments) and the
personal library are writable by their owner, with the author/user set from
the request.
"""

from rest_framework import generics, viewsets

from .models import (
    Alert,
    Game,
    GameComment,
    Genre,
    LibraryEntry,
    Reply,
    Topic,
    UserProfile,
)
from .permissions import IsAdminOrReadOnly, IsAuthorOrReadOnly
from .serializers import (
    AlertSerializer,
    GameCommentSerializer,
    GameSerializer,
    GenreSerializer,
    LibraryEntrySerializer,
    ReplySerializer,
    TopicSerializer,
    UserProfileSerializer,
)


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.prefetch_related("genres").all()
    serializer_class = GameSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    filterset_fields = ["genres__slug"]
    search_fields = ["name", "developer", "publisher"]
    ordering_fields = ["bug_score", "name", "metacritic", "popularity"]


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = "slug"
    search_fields = ["name"]


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


class LibraryViewSet(viewsets.ModelViewSet):
    serializer_class = LibraryEntrySerializer
    # Owner-scoped queryset already limits access to the request user's rows.
    permission_classes = [IsAuthorOrReadOnly]

    def get_queryset(self):
        return (
            LibraryEntry.objects.filter(user=self.request.user)
            .select_related("game")
            .order_by("-added_at")
        )

    def perform_create(self, serializer):
        # Idempotent: adding a game already in the library updates the flag
        # instead of raising a unique-constraint error.
        entry, _ = LibraryEntry.objects.update_or_create(
            user=self.request.user,
            game=serializer.validated_data["game"],
            defaults={"favorite": serializer.validated_data.get("favorite", False)},
        )
        serializer.instance = entry


class MeView(generics.RetrieveUpdateAPIView):
    """The authenticated user's profile (GET / PATCH)."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
