"""Central helper to create notifications (skips self-notification)."""

from .models import Notification


def notify(*, recipient, kind, text, url="", actor=None):
    if actor is not None and actor == recipient:
        return None
    return Notification.objects.create(
        recipient=recipient, actor=actor, kind=kind, text=text, url=url
    )
