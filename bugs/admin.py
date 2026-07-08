from django.contrib import admin

from .models import Bug, BugReport, BugSignal, BugVote, GameScoreSnapshot


@admin.register(Bug)
class BugAdmin(admin.ModelAdmin):
    list_display = ("game", "title", "category", "severity", "status", "confirmations")
    list_filter = ("category", "severity", "status")
    search_fields = ("title", "game__name")


@admin.register(BugReport)
class BugReportAdmin(admin.ModelAdmin):
    list_display = ("game", "bug", "author", "category", "created_at")
    list_filter = ("category",)
    search_fields = ("text", "game__name", "author__username")


@admin.register(BugVote)
class BugVoteAdmin(admin.ModelAdmin):
    list_display = ("bug", "user", "created_at")
    search_fields = ("bug__title", "user__username")


@admin.register(GameScoreSnapshot)
class GameScoreSnapshotAdmin(admin.ModelAdmin):
    list_display = ("game", "bug_score", "captured_at")
    search_fields = ("game__name",)


@admin.register(BugSignal)
class BugSignalAdmin(admin.ModelAdmin):
    list_display = ("bug", "source", "external_id", "score", "created_at")
    list_filter = ("source",)
    search_fields = ("external_id", "bug__title")
