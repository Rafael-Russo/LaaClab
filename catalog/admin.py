from django.contrib import admin

from .models import Game, Genre, IngestCandidate, LibraryEntry


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "bug_score", "metacritic", "steam_appid")
    list_filter = ("genres",)
    search_fields = ("name", "slug", "developer", "publisher")
    filter_horizontal = ("genres",)
    ordering = ("name",)


@admin.register(LibraryEntry)
class LibraryEntryAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "favorite", "added_at")
    list_filter = ("favorite",)
    search_fields = ("user__username", "game__name")


@admin.register(IngestCandidate)
class IngestCandidateAdmin(admin.ModelAdmin):
    list_display = ("appid", "name", "owners", "rank", "status", "attempts")
    list_filter = ("status",)
    search_fields = ("appid", "name")
