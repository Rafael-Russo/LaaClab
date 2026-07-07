"""DRF serializers for the CRUD API (``/api/v1/``).

Related games are referenced by ``slug`` and authors are read-only (set from
the request user), so the browsable API is pleasant to use by hand.
"""

from rest_framework import serializers

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


class TopicSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    game = serializers.SlugRelatedField(
        slug_field="slug", queryset=Game.objects.all(), allow_null=True, required=False
    )
    type_display = serializers.CharField(source="get_type_display", read_only=True)
    level = serializers.ReadOnlyField()
    replies_count = serializers.IntegerField(source="replies.count", read_only=True)

    class Meta:
        model = Topic
        fields = [
            "id", "game", "author", "title", "body", "type", "type_display",
            "level", "replies_count", "created_at",
        ]
        read_only_fields = ["author", "created_at"]


class ReplySerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")

    class Meta:
        model = Reply
        fields = ["id", "topic", "author", "body", "created_at"]
        read_only_fields = ["author", "created_at"]


class GameCommentSerializer(serializers.ModelSerializer):
    author = serializers.ReadOnlyField(source="author.username")
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())

    class Meta:
        model = GameComment
        fields = ["id", "game", "author", "text", "created_at"]
        read_only_fields = ["author", "created_at"]


class AlertSerializer(serializers.ModelSerializer):
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())
    severity_display = serializers.CharField(source="get_severity_display", read_only=True)
    level = serializers.ReadOnlyField()
    icon = serializers.ReadOnlyField()

    class Meta:
        model = Alert
        fields = [
            "id", "game", "severity", "severity_display", "level", "icon",
            "text", "created_at",
        ]
        read_only_fields = ["created_at"]


class LibraryEntrySerializer(serializers.ModelSerializer):
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())
    game_name = serializers.ReadOnlyField(source="game.name")

    class Meta:
        model = LibraryEntry
        fields = ["id", "game", "game_name", "favorite", "added_at"]
        read_only_fields = ["added_at"]


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.ReadOnlyField(source="user.username")
    email = serializers.ReadOnlyField(source="user.email")

    class Meta:
        model = UserProfile
        fields = [
            "username", "email", "handle", "level", "xp", "xp_max", "bio",
            "avatar_color", "achievements", "friends", "days_active",
        ]
        # Progression stats are server-owned; users may edit their handle/bio/colour.
        read_only_fields = [
            "username", "email", "level", "xp", "xp_max",
            "achievements", "friends", "days_active",
        ]
