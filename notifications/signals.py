"""Notification sources fired on model creation."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from alerts.models import Alert
from catalog.models import LibraryEntry
from community.models import Reply

from .services import notify

User = get_user_model()


@receiver(post_save, sender=Reply)
def _reply_created(sender, instance, created, **kwargs):
    if not created:
        return
    topic = instance.topic
    url = f"/comunidade/?game={topic.game.slug}" if topic.game_id else "/comunidade/"
    notify(
        recipient=topic.author,
        actor=instance.author,
        kind="reply",
        text=f'{instance.author.username} respondeu ao seu tópico "{topic.title}"',
        url=url,
    )


@receiver(post_save, sender=Alert)
def _alert_created(sender, instance, created, **kwargs):
    if not created:
        return
    game = instance.game
    owner_ids = LibraryEntry.objects.filter(game=game).values_list("user_id", flat=True)
    for user in User.objects.filter(id__in=owner_ids):
        notify(
            recipient=user,
            actor=None,
            kind="alert",
            text=f"Novo alerta em {game.name}: {instance.get_severity_display()}",
            url=f"/jogo/{game.slug}/",
        )
