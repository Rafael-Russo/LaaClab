from django.db import models


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

    game = models.ForeignKey("catalog.Game", on_delete=models.CASCADE, related_name="alerts")
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
