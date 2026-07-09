"""Celery task that delivers a Notification as a Web Push message."""

import json

from celery import shared_task
from django.conf import settings
from pywebpush import WebPushException, webpush


@shared_task
def send_push(notification_id):
    from accounts.models import UserProfile

    from .models import Notification, PushSubscription

    if not (settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY):
        return  # push desligado
    try:
        n = Notification.objects.select_related("recipient").get(pk=notification_id)
    except Notification.DoesNotExist:
        return
    profile, _ = UserProfile.objects.get_or_create(user=n.recipient)
    kinds = profile.push_kinds or []
    if kinds and n.kind not in kinds:  # lista vazia = todos
        return
    payload = json.dumps({"title": "LaaCLab", "body": n.text, "url": n.url})
    for sub in PushSubscription.objects.filter(user=n.recipient):
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_ADMIN_EMAIL}"},
            )
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                sub.delete()
