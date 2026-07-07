from django.contrib import admin

from .models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("game", "severity", "created_at")
    list_filter = ("severity",)
    search_fields = ("text", "game__name")
