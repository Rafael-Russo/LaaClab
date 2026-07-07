"""DRF serializer for the UserProfile CRUD API (mounted at ``/api/v1/`` —
see ``accounts/urls.py``).
"""

from rest_framework import serializers

from .models import UserProfile


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
