"""DRF serializers for the forum CRUD API (``/api/v1/``).

Related games are referenced by ``slug`` and authors are read-only (set from
the request user), so the browsable API stays pleasant to use by hand.
"""

from rest_framework import serializers

from catalog.models import Game

from .models import GameComment, Reply, Topic


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
