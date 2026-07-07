from django.db import models


class Module(models.Model):
    """A togglable feature module (community, catalog, alerts, ...)."""

    key = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} ({'on' if self.enabled else 'off'})"


def module_enabled(key: str) -> bool:
    """True if the module is enabled (or unknown -> treated as enabled)."""
    row = Module.objects.filter(key=key).first()
    return row.enabled if row else True
