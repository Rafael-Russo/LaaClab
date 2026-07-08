"""Alerts JSON endpoint consumed by the alerts screen via ``fetch()``."""

from django.http import JsonResponse

from core import services
from core.api import api_login_required
from core.gating import require_module_api

from .models import Alert

# Alert.level is a derived property (not a DB column, see alerts/models.py
# PRESENTATION); filtering by level maps it back to the stored severity.
_LEVEL_TO_SEVERITY = {level: severity for severity, (level, _icon) in Alert.PRESENTATION.items()}


@api_login_required
@require_module_api("alerts")
def alerts(request):
    qs = Alert.objects.select_related("game")
    level = request.GET.get("level") or ""
    if level:
        qs = qs.filter(severity=_LEVEL_TO_SEVERITY.get(level, level))
    term = request.GET.get("q") or ""
    if term:
        qs = qs.filter(game__name__icontains=term)
    rows = list(qs[:10])
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
