from django.conf import settings
from django.db import models


class Topic(models.Model):
    """A community/forum thread, optionally attached to a game."""

    class Type(models.TextChoices):
        DISCUSSION = "discussion", "Discussão"
        BUG = "bug", "Bug"
        TIP = "tip", "Dica"
        NEWS = "news", "Notícia"

    # UI colour bucket per type (matches the badge--* CSS classes).
    LEVELS = {"discussion": "discussion", "bug": "warning", "tip": "stable", "news": "info"}

    game = models.ForeignKey(
        "catalog.Game", null=True, blank=True, on_delete=models.CASCADE, related_name="topics"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topics"
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.DISCUSSION)
    created_at = models.DateTimeField(auto_now_add=True)

    is_hidden = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        permissions = [("can_moderate_forum", "Pode moderar o fórum")]

    def __str__(self) -> str:
        return self.title

    @property
    def level(self) -> str:
        return self.LEVELS.get(self.type, "discussion")


class Reply(models.Model):
    """A message posted in a topic."""

    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="replies")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="replies"
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    is_hidden = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "replies"

    def __str__(self) -> str:
        return f"Reply({self.author} @ {self.topic_id})"


class GameComment(models.Model):
    """A short comment on a game's detail page."""

    game = models.ForeignKey("catalog.Game", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_comments"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    is_hidden = models.BooleanField(default=False)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Comment({self.author} @ {self.game_id})"
