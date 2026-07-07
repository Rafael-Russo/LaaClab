from django.contrib import admin

from .models import (
    Alert,
    UserProfile,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "handle", "level", "xp", "days_active")
    search_fields = ("user__username", "handle")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("game", "severity", "created_at")
    list_filter = ("severity",)
    search_fields = ("text", "game__name")
