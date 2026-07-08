"""DRF serializers for the catalogue CRUD API (``/api/v1/``).

Related games are referenced by ``slug``; the browsable API stays pleasant
to use by hand.
"""

from rest_framework import serializers

from catalog.models import Game, Genre, LibraryEntry


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "slug"]
        read_only_fields = ["slug"]


class GameSerializer(serializers.ModelSerializer):
    genres = serializers.SlugRelatedField(
        slug_field="name", many=True, queryset=Genre.objects.all(), required=False
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = [
            "id", "slug", "name", "steam_appid", "short_description", "about", "merch",
            "cover_image", "cover", "cover_file", "popularity", "initials", "bug_score",
            "status", "release_date", "developer", "publisher", "metacritic", "genres",
            "last_update",
            "achievements", "likes", "dislikes", "time_to_beat_main",
            "time_to_beat_speedrun", "time_to_beat_platinum", "created_at", "updated_at",
        ]
        read_only_fields = ["slug", "initials", "status", "created_at", "updated_at"]

    def get_status(self, obj) -> dict:
        return obj.status


class LibraryEntrySerializer(serializers.ModelSerializer):
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())
    game_name = serializers.ReadOnlyField(source="game.name")

    class Meta:
        model = LibraryEntry
        fields = ["id", "game", "game_name", "favorite", "added_at"]
        read_only_fields = ["added_at"]
