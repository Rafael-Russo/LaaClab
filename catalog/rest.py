"""DRF viewsets for the catalogue and library resources of the CRUD API
(mounted at ``/api/v1/`` — see ``catalog/urls.py``).

Games/genres are read-only for regular users and writable by staff; the
personal library is writable by its owner, with the user set from the
request.
"""

from rest_framework import viewsets

from core.permissions import IsAuthorOrReadOnly, IsGamesModeratorOrReadOnly

from .models import Game, Genre, LibraryEntry
from .serializers import GameSerializer, GenreSerializer, LibraryEntrySerializer


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.prefetch_related("genres").all()
    serializer_class = GameSerializer
    permission_classes = [IsGamesModeratorOrReadOnly]
    lookup_field = "slug"
    filterset_fields = ["genres__slug"]
    search_fields = ["name", "developer", "publisher"]
    ordering_fields = ["bug_score", "name", "metacritic", "popularity"]


class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsGamesModeratorOrReadOnly]
    lookup_field = "slug"
    search_fields = ["name"]


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
