from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


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


class BugSignal(models.Model):
    """Provenance for an automatically-sourced bug candidate (Fase 3b)."""
    bug = models.ForeignKey(Bug, on_delete=models.CASCADE, related_name="signals")
    source = models.CharField(max_length=20, choices=Bug.Source.choices, default=Bug.Source.SCRAPED)
    external_id = models.CharField(max_length=100)
    url = models.URLField(blank=True, max_length=500)
    text = models.TextField(blank=True)
    score = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("source", "external_id")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"signal {self.source}:{self.external_id} -> bug {self.bug_id}"


@receiver([post_save, post_delete], sender=Bug)
def _bug_changed(sender, instance, **kwargs):
    from bugs.scoring import recompute_and_store
    recompute_and_store(instance.game)


@receiver([post_save, post_delete], sender=BugVote)
def _vote_changed(sender, instance, **kwargs):
    # keep confirmations in sync then rescore
    bug = instance.bug
    bug.confirmations = bug.votes.count()
    bug.save(update_fields=["confirmations", "updated_at"])  # triggers _bug_changed → rescore
