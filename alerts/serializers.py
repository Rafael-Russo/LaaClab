"""DRF serializer for the Alert CRUD API (mounted at ``/api/v1/`` — see
``alerts/urls.py``).
"""

from rest_framework import serializers

from catalog.models import Game

from .models import Alert


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
