"""JSON endpoints consumed by the static screens via ``fetch()``.

Each screen loads its HTML/CSS/JS shell from a view in ``views.py`` and then
fetches its data from one of these endpoints. Responses are built from
``mock_data`` for now. Auth is required: an unauthenticated request gets a
JSON ``401`` (instead of an HTML login redirect) so the front-end can react.
"""

from functools import wraps

from django.http import JsonResponse

from . import mock_data


def api_login_required(view):
    """Like ``login_required`` but returns JSON 401 instead of redirecting."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Autenticação necessária."}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


@api_login_required
def me(request):
    """Current user summary used by the sidebar widget and top bar."""
    return JsonResponse(mock_data.CURRENT_USER)


@api_login_required
def home(request):
    return JsonResponse({
        "banners": mock_data.HOME_BANNERS,
        "updates": mock_data.HOME_UPDATES,
        "trending": mock_data.HOME_TRENDING,
        "favorites": mock_data.favorite_games(),
        "alert": mock_data.HOME_ALERT,
    })


@api_login_required
def bugometro(request):
    slug = request.GET.get("game", "warzone")
    game = mock_data.get_game(slug) or mock_data.get_game("warzone")
    return JsonResponse({
        "game": game,
        "updated_ago": "Atualizado há 2 min",
        "metrics": mock_data.BUGOMETRO_METRICS,
        "chart": mock_data.bugometro_chart(),
        "activity": mock_data.BUGOMETRO_ACTIVITY,
        "top_unstable": mock_data.TOP_UNSTABLE,
    })


@api_login_required
def library(request):
    games = mock_data.all_games()
    return JsonResponse({"games": games, "total": len(games)})


@api_login_required
def community(request):
    slug = request.GET.get("game", "cs2")
    selected = mock_data.get_game(slug) or mock_data.get_game("cs2")
    games = mock_data.all_games()
    return JsonResponse({
        "games": games,
        "selected": selected,
        "topics": mock_data.COMMUNITY_TOPICS,
        "stats": mock_data.COMMUNITY_STATS,
        "rules": mock_data.COMMUNITY_RULES,
    })


@api_login_required
def alerts(request):
    return JsonResponse({
        "alerts": mock_data.ALERTS,
        "summary": mock_data.ALERTS_SUMMARY,
        "favorites": mock_data.favorite_games(),
    })


@api_login_required
def game_detail(request, slug):
    detail = mock_data.game_detail(slug)
    if detail is None:
        return JsonResponse({"detail": "Jogo não encontrado."}, status=404)
    return JsonResponse(detail)


@api_login_required
def profile(request):
    return JsonResponse({
        "user": mock_data.CURRENT_USER,
        "recent_games": mock_data.PROFILE_RECENT,
    })
