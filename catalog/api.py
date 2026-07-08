"""Catalogue JSON endpoint consumed by the library screen via ``fetch()``."""

from django.http import JsonResponse

from core.api import api_login_required
from core.gating import require_module_api

from . import services


@api_login_required
@require_module_api("catalog")
def library(request):
    games = services.user_library_cards(request.user)
    return JsonResponse({"games": games, "total": len(games)})
