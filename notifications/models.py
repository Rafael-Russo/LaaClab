from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Kind(models.TextChoices):
        REPLY = "reply", "Resposta"
        ALERT = "alert", "Alerta"
        BUG_CONFIRMED = "bug_confirmed", "Bug confirmado"
        BUG_RESOLVED = "bug_resolved", "Bug resolvido"
        BUG_REJECTED = "bug_rejected", "Bug rejeitado"
        TOPIC_HIDDEN = "topic_hidden", "Tópico ocultado"
        TOPIC_LOCKED = "topic_locked", "Tópico travado"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self) -> str:
        return f"{self.kind} -> {self.recipient_id}"
