"""DRF serializers for the CRUD API (``/api/v1/``).

Related games are referenced by ``slug`` and authors are read-only (set from
the request user), so the browsable API is pleasant to use by hand.
"""

from rest_framework import serializers

from .models import (
    Alert,
    Game,
    GameComment,
    Reply,
    Topic,
    UserProfile,
)


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
