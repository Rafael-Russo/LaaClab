"""Catalogue JSON endpoint consumed by the library screen via ``fetch()``."""

from django.http import JsonResponse

from core.api import api_login_required

from . import services


@api_login_required
def library(request):
    games = services.user_library_cards(request.user)
    return JsonResponse({"games": games, "total": len(games)})
