"""Notifications JSON endpoints consumed by the topbar bell."""

import json

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from core.api import api_login_required
from core.services import humanize_when

from .models import Notification, PushSubscription


@api_login_required
def notifications(request):
    qs = Notification.objects.filter(recipient=request.user)
    rows = [
        {
            "id": n.id,
            "kind": n.kind,
            "text": n.text,
            "url": n.url,
            "is_read": n.is_read,
            "when": humanize_when(n.created_at),
        }
        for n in qs[:20]
    ]
    return JsonResponse(
        {"notifications": rows, "unread_count": qs.filter(is_read=False).count()}
    )


@api_login_required
def mark_read(request, pk):
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido."}, status=405)
    n = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not n.is_read:
        n.is_read = True
        n.save(update_fields=["is_read"])
    return HttpResponse(status=204)


@api_login_required
def mark_all_read(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido."}, status=405)
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return HttpResponse(status=204)


@api_login_required
def vapid_key(request):
    return JsonResponse({"public_key": settings.VAPID_PUBLIC_KEY})


@api_login_required
def subscribe(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido."}, status=405)
    try:
        data = json.loads(request.body)
        endpoint = data["endpoint"]
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return JsonResponse({"detail": "Requisição inválida."}, status=400)
    keys = data.get("keys") or {}
    if not isinstance(keys, dict):
        return JsonResponse({"detail": "Requisição inválida."}, status=400)
    PushSubscription.objects.update_or_create(
        endpoint=endpoint,
        defaults={
            "user": request.user,
            "p256dh": keys.get("p256dh", ""),
            "auth": keys.get("auth", ""),
        },
    )
    return JsonResponse({"detail": "Inscrito."}, status=201)


@api_login_required
def unsubscribe(request):
    if request.method != "POST":
        return JsonResponse({"detail": "Método não permitido."}, status=405)
    try:
        data = json.loads(request.body)
        endpoint = data["endpoint"]
    except (json.JSONDecodeError, KeyError, TypeError, AttributeError):
        return JsonResponse({"detail": "Requisição inválida."}, status=400)
    PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
    return HttpResponse(status=204)
