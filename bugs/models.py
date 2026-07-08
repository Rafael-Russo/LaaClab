from django.conf import settings
from django.db import models


class Bug(models.Model):
    class Category(models.TextChoices):
        CRASH = "crash", "Crash"
        GRAPHICS = "graphics", "Gráficos"
        PERFORMANCE = "performance", "Desempenho"
        PROGRESSION = "progression", "Progressão"
        ONLINE = "online", "Online"
        OTHER = "other", "Outro"

    class Severity(models.TextChoices):
        LOW = "low", "Baixa"
        MEDIUM = "medium", "Média"
        HIGH = "high", "Alta"
        CRITICAL = "critical", "Crítica"

    class Status(models.TextChoices):
        OPEN = "open", "Aberto"
        CONFIRMED = "confirmed", "Confirmado"
        RESOLVED = "resolved", "Resolvido"
        REJECTED = "rejected", "Rejeitado"

    class Source(models.TextChoices):
        COMMUNITY = "community", "Comunidade"
        SCRAPED = "scraped", "Coletado"
        AGENT = "agent", "Agente"

    game = models.ForeignKey("catalog.Game", on_delete=models.CASCADE, related_name="bugs")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.OTHER)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.COMMUNITY)
    confirmations = models.PositiveIntegerField(default=0)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["game", "status"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.game_id})"

    @property
    def is_active(self) -> bool:
        return self.status in {self.Status.OPEN, self.Status.CONFIRMED}


class BugReport(models.Model):
    """A user's raw report; may attach to an existing Bug or spawn one."""
    bug = models.ForeignKey(Bug, null=True, blank=True, on_delete=models.CASCADE, related_name="reports")
    game = models.ForeignKey("catalog.Game", on_delete=models.CASCADE, related_name="bug_reports")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bug_reports")
    text = models.TextField()
    category = models.CharField(max_length=20, choices=Bug.Category.choices, default=Bug.Category.OTHER)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BugVote(models.Model):
    """A user's confirmation vote on a Bug (one per user per bug)."""
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bug_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("bug", "user")


class GameScoreSnapshot(models.Model):
    """Point-in-time bug_score per game (feeds P4 Históricos)."""
    game = models.ForeignKey("catalog.Game", on_delete=models.CASCADE, related_name="score_snapshots")
    bug_score = models.PositiveSmallIntegerField()
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-captured_at"]
        indexes = [models.Index(fields=["game", "captured_at"])]
