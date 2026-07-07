from django.contrib import admin

from .models import GameComment, Reply, Topic


class ReplyInline(admin.TabularInline):
    model = Reply
    extra = 0


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "type", "game", "author", "created_at")
    list_filter = ("type",)
    search_fields = ("title", "body", "author__username")
    inlines = [ReplyInline]


@admin.register(GameComment)
class GameCommentAdmin(admin.ModelAdmin):
    list_display = ("game", "author", "created_at")
    search_fields = ("text", "author__username", "game__name")
