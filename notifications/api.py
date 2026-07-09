"""Notifications JSON endpoints consumed by the topbar bell."""

from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404

from core.api import api_login_required
from core.services import humanize_when

from .models import Notification


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
