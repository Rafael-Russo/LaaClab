from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "handle", "level", "xp", "days_active")
    search_fields = ("user__username", "handle")
