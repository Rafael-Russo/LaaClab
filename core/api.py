"""Per-screen JSON endpoints consumed by the static screens via ``fetch()``.

Each screen loads its HTML/CSS/JS shell from a view in ``views.py`` and then
fetches its data from one of these endpoints. Responses are built from the
database (via the ORM and ``services``) but keep the exact JSON shapes the
front-end already expects. Auth is required: an unauthenticated request gets a
JSON ``401`` (instead of an HTML login redirect) so the front-end can react.

``api_login_required`` is reused by the ``catalog``, ``community``, ``alerts``
and ``accounts`` apps.
"""

from functools import wraps

from django.http import JsonResponse
from django.utils.text import Truncator

from alerts.models import Alert
from catalog.models import Game
from community.models import Topic

from . import services


def api_login_required(view):
    """Like ``login_required`` but returns JSON 401 instead of redirecting."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Autenticação necessária."}, status=401)
        return view(request, *args, **kwargs)

    return wrapper


def _fmt_thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _active_bugs(game: Game) -> list[dict]:
    """Real, active bugs for a game — used by bugômetro and game_detail."""
    qs = game.bugs.filter(status__in=["open", "confirmed"]).order_by(
        "-confirmations", "-created_at"
    )[:20]
    return [
        {
            "id": b.id,
            "title": b.title,
            "category": b.get_category_display(),
            "severity": b.severity,
            "severity_display": b.get_severity_display(),
            "status": b.status,
            "confirmations": b.confirmations,
        }
        for b in qs
    ]


@api_login_required
def home(request):
    featured = list(Game.objects.exclude(metacritic=None).order_by("-metacritic")[:3])
    if not featured:
        featured = list(Game.objects.all()[:3])
    banners = [
        {
            "title": f"Novidades e atualizações em {g.name}",
            "game": g.name,
            "cover": g.cover or ["#2b2d47", "#14152b"],
        }
        for g in featured
    ]

    updates = []
    for alert in Alert.objects.select_related("game")[:4]:
        updates.append(
            {
                "game": alert.game.name,
                "tag": alert.get_severity_display(),
                "level": alert.level,
                "title": alert.game.name.upper(),
                "text": alert.text,
                "when": services.humanize_when(alert.created_at),
                "cover": alert.game.cover or ["#2b2d47", "#14152b"],
            }
        )

    trending = [
        {"title": t.title, "group": "Últimos assuntos"}
        for t in Topic.objects.all()[:8]
    ]

    latest_alert = Alert.objects.select_related("game").first()
    if latest_alert:
        alert_payload = {"message": latest_alert.text, "game": latest_alert.game.slug}
    else:
        alert_payload = {"message": "Nenhum alerta recente.", "game": ""}

    return JsonResponse(
        {
            "banners": banners,
            "updates": updates,
            "trending": trending,
            "favorites": services.user_favorite_cards(request.user),
            "alert": alert_payload,
        }
    )


@api_login_required
def bugometro(request):
    slug = request.GET.get("game")
    game = None
    if slug:
        game = Game.objects.filter(slug=slug).first()
    if game is None:
        game = Game.objects.order_by("-bug_score").first()
    if game is None:
        return JsonResponse({"detail": "Sem jogos cadastrados."}, status=404)

    activity = services.game_activity(game)
    if not activity:
        activity = [
            {
                "title": a.get_severity_display(),
                "subtitle": Truncator(a.text).chars(48),
                "when": services.humanize_when(a.created_at),
                "level": a.level,
            }
            for a in Alert.objects.select_related("game")[:4]
        ]

    return JsonResponse(
        {
            "game": services.game_card(game),
            "updated_ago": "Atualizado há 2 min",
            "metrics": services.bugometro_metrics(game),
            "chart": services.bugometro_chart(),
            "activity": activity,
            "top_unstable": services.top_unstable(),
            "bugs": _active_bugs(game),
        }
    )


@api_login_required
def game_detail(request, slug):
    game = Game.objects.filter(slug=slug).first()
    if game is None:
        return JsonResponse({"detail": "Jogo não encontrado."}, status=404)

    comments = [
        {"author": c.author.username, "text": c.text}
        for c in game.comments.select_related("author")[:10]
    ]
    last_update = game.last_update.strftime("%d/%m/%Y") if game.last_update else (
        game.release_date or "—"
    )
    return JsonResponse(
        {
            **services.game_card(game),
            "last_update": last_update,
            "about": game.about or game.short_description,
            "merch": game.merch or "Sem informações de merch para este jogo.",
            "likes": _fmt_thousands(game.likes),
            "dislikes": _fmt_thousands(game.dislikes),
            "time_to_beat": {
                "medio": game.time_to_beat_main or "—",
                "speedrun": game.time_to_beat_speedrun or "—",
                "platina": game.time_to_beat_platinum or "—",
            },
            "achievements": game.achievements,
            "comments": comments,
            "bugs": _active_bugs(game),
        }
    )
