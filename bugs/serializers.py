"""DRF serializers for the bugs CRUD API (``/api/v1/``).

Related games are referenced by ``slug``; authorship, moderation and
scoring-adjacent fields are read-only — they're set by the server, not the
client (author from the request user; status/moderation from the
moderation actions; confirmations from votes).
"""

from rest_framework import serializers

from catalog.models import Game

from .models import Bug, BugReport, BugVote


class BugSerializer(serializers.ModelSerializer):
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Bug
        fields = [
            "id", "game", "title", "description", "category", "category_display",
            "severity", "status", "source", "confirmations", "moderated_by", "moderated_at",
            "created_at",
        ]
        read_only_fields = ["status", "source", "confirmations", "moderated_by", "moderated_at", "created_at"]


class BugReportSerializer(serializers.ModelSerializer):
    game = serializers.SlugRelatedField(slug_field="slug", queryset=Game.objects.all())
    author = serializers.ReadOnlyField(source="author.username")

    class Meta:
        model = BugReport
        fields = ["id", "game", "author", "text", "category", "created_at", "bug"]
        read_only_fields = ["author", "created_at", "bug"]


class BugVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugVote
        fields = ["id", "bug", "created_at"]
        read_only_fields = ["created_at"]
