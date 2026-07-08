from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Gamer profile shown on the sidebar widget and the profile screen."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    handle = models.CharField(max_length=50, blank=True)
    level = models.PositiveIntegerField(default=1)
    xp = models.PositiveIntegerField(default=0)
    xp_max = models.PositiveIntegerField(default=2000)
    bio = models.CharField(max_length=280, blank=True)
    avatar_color = models.CharField(max_length=9, default="#6b7cff")
    achievements = models.PositiveIntegerField(default=0)
    friends = models.PositiveIntegerField(default=0)
    days_active = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"Profile({self.user})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_profile(sender, instance, created, **kwargs):
    """Every user gets a profile the moment the account is created."""
    if created:
        UserProfile.objects.create(user=instance, handle=instance.username)
