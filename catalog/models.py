from django.conf import settings
from django.db import models
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

    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["bug_score"])]
        permissions = [("can_moderate_games", "Pode moderar jogos/bugs")]

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
