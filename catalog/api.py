"""Catalogue JSON endpoint consumed by the library screen via ``fetch()``.

``api_login_required`` (JSON 401 instead of an HTML login redirect) still
lives in ``web/api.py`` for now — it moves to ``core`` in Task 7.
"""

from django.http import JsonResponse

from web.api import api_login_required

from . import services


@api_login_required
def library(request):
    games = services.user_library_cards(request.user)
    return JsonResponse({"games": games, "total": len(games)})
