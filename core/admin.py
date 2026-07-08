from django.contrib import admin

from core.models import Module


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "enabled")
    list_editable = ("enabled",)
    search_fields = ("key", "name")
