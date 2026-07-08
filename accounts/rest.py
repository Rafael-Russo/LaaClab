"""DRF view for the authenticated user's profile (mounted at ``/api/v1/`` —
see ``accounts/urls.py``).
"""

from rest_framework import generics

from .models import UserProfile
from .serializers import UserProfileSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """The authenticated user's profile (GET / PATCH)."""

    serializer_class = UserProfileSerializer

    def get_object(self):
        profile, _ = UserProfile.objects.get_or_create(user=self.request.user)
        return profile
