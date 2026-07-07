"""Alerts JSON endpoint consumed by the alerts screen via ``fetch()``.

``api_login_required`` (JSON 401 instead of an HTML login redirect) still
lives in ``web/api.py`` for now — it moves to ``core`` in Task 7. ``services``
(``user_favorite_cards``) still lives in ``web`` for now too.
"""

from django.http import JsonResponse

from web import services
from web.api import api_login_required

from .models import Alert


@api_login_required
def alerts(request):
    rows = list(Alert.objects.select_related("game")[:10])
    counts = {"critical": 0, "warning": 0, "stable": 0}
    payload = []
    for a in rows:
        counts[a.level] = counts.get(a.level, 0) + 1
        payload.append(
            {
                "game": a.game.name,
                "slug": a.game.slug,
                "severity": a.get_severity_display(),
                "level": a.level,
                "icon": a.icon,
                "text": a.text,
            }
        )
    summary = [
        {"label": "Críticos", "count": counts["critical"], "level": "critical"},
        {"label": "Instável", "count": counts["warning"], "level": "warning"},
        {"label": "Atualização", "count": counts["stable"], "level": "stable"},
    ]
    return JsonResponse(
        {
            "alerts": payload,
            "summary": summary,
            "favorites": services.user_favorite_cards(request.user),
        }
    )
