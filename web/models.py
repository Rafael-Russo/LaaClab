"""Domain models for LaaCLab.

The catalogue (``Game``/``Genre``) is seeded from a real dataset (Steam store
API). The remaining models capture what the screens show: a per-user library,
the community forum (``Topic``/``Reply``), per-game comments, and stability
alerts. Derived, presentation-only data (the 24h chart, metric buckets) lives
in ``services.py`` instead of the database.
"""

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify


def status_for(score: int) -> dict:
    """Map a 0-100 bug score to a stability level (drives the UI colour)."""
    if score >= 65:
        return {"label": "Crítico", "level": "critical"}
    if score >= 40:
        return {"label": "Instável", "level": "warning"}
    return {"label": "Estável", "level": "stable"}


class Genre(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Game(models.Model):
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    name = models.CharField(max_length=200)
    steam_appid = models.PositiveIntegerField(null=True, blank=True, unique=True)

    short_description = models.TextField(blank=True)
    about = models.TextField(blank=True)
    merch = models.TextField(blank=True)

    # Real cover art URL (Steam header image) with a two-colour gradient
    # fallback ([light, dark]) used when no image is available.
    cover_image = models.URLField(blank=True, max_length=500)
    cover = models.JSONField(default=list, blank=True)
    cover_file = models.ImageField(upload_to="covers/", blank=True)
    popularity = models.PositiveIntegerField(default=0)
    initials = models.CharField(max_length=4, blank=True)

    # 0-100 stability score; higher = more bugs reported.
    bug_score = models.PositiveSmallIntegerField(default=0)

    release_date = models.CharField(max_length=60, blank=True)
    developer = models.CharField(max_length=200, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    metacritic = models.PositiveSmallIntegerField(null=True, blank=True)
    genres = models.ManyToManyField(Genre, related_name="games", blank=True)

    last_update = models.DateField(null=True, blank=True)
    achievements = models.PositiveIntegerField(default=0)
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    time_to_beat_main = models.CharField(max_length=40, blank=True)
    time_to_beat_speedrun = models.CharField(max_length=40, blank=True)
    time_to_beat_platinum = models.CharField(max_length=40, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["bug_score"])]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:140]
        if not self.initials:
            parts = [p for p in self.name.split() if p]
            self.initials = ("".join(p[0] for p in parts[:2]) or self.name[:2]).upper()
        super().save(*args, **kwargs)

    @property
    def status(self) -> dict:
        return status_for(self.bug_score)


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


class LibraryEntry(models.Model):
    """A game a user added to their personal library."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="library"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="library_entries"
    )
    favorite = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "game")
        ordering = ["-added_at"]
        verbose_name_plural = "library entries"

    def __str__(self) -> str:
        return f"{self.user} → {self.game}"


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
        Game, null=True, blank=True, on_delete=models.CASCADE, related_name="topics"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="topics"
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    type = models.CharField(max_length=20, choices=Type.choices, default=Type.DISCUSSION)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

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

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "replies"

    def __str__(self) -> str:
        return f"Reply({self.author} @ {self.topic_id})"


class GameComment(models.Model):
    """A short comment on a game's detail page."""

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_comments"
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Comment({self.author} @ {self.game_id})"


class Alert(models.Model):
    """A stability alert raised for a game."""

    class Severity(models.TextChoices):
        CRITICAL = "critical", "CRÍTICO"
        WARNING = "warning", "INSTÁVEL"
        UPDATE = "update", "Atualização"

    # Presentation hints per severity: (UI level, icon name used by the JS).
    PRESENTATION = {
        "critical": ("critical", "wifi"),
        "warning": ("warning", "alert"),
        "update": ("stable", "check"),
    }

    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="alerts")
    severity = models.CharField(max_length=20, choices=Severity.choices)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.get_severity_display()} · {self.game}"

    @property
    def level(self) -> str:
        return self.PRESENTATION.get(self.severity, ("critical", "wifi"))[0]

    @property
    def icon(self) -> str:
        return self.PRESENTATION.get(self.severity, ("critical", "wifi"))[1]


class IngestCandidate(models.Model):
    """A Steam app queued for ingestion; makes the pipeline resumable."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        FETCHING = "fetching", "Buscando"
        DONE = "done", "Concluído"
        FAILED = "failed", "Falhou"

    appid = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    owners = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "appid"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.appid} ({self.status})"
