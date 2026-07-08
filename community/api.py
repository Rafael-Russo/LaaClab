"""Community JSON endpoint consumed by the community screen via ``fetch()``."""

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.http import JsonResponse
from django.utils.text import Truncator

from catalog.models import Game
from core import services
from core.api import api_login_required
from core.gating import require_module_api

from .models import Reply, Topic

User = get_user_model()

COMMUNITY_RULES = [
    "Respeite todos os membros.",
    "Não faça spam ou autopromoção.",
    "Evite conteúdos ofensivos.",
    "Ajude outros jogadores!",
]


def _fmt_thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


@api_login_required
@require_module_api("community")
def community(request):
    games = list(Game.objects.annotate(n_topics=Count("topics")))
    slug = request.GET.get("game")

    selected = None
    if slug:
        selected = next((g for g in games if g.slug == slug), None)
    if selected is None:
        # Prefer a game that actually has topics, else the first game.
        selected = next(
            (g for g in games if g.n_topics > 0), games[0] if games else None
        )

    def card(game):
        data = services.game_card(game)
        data["topic_count"] = game.n_topics
        return data

    topics = []
    if selected is not None:
        qs = selected.topics.select_related("author")
        if not (
            request.user.has_perm("community.can_moderate_forum") or request.user.is_staff
        ):
            qs = qs.filter(is_hidden=False)
        for t in qs[:20]:
            topics.append(
                {
                    "title": t.title,
                    "author": t.author.username,
                    "when": services.humanize_when(t.created_at),
                    "type": t.get_type_display(),
                    "level": t.level,
                    "excerpt": Truncator(t.body).chars(160),
                }
            )

    stats = {
        "members": _fmt_thousands(User.objects.count()),
        "topics": _fmt_thousands(Topic.objects.count()),
        "messages": _fmt_thousands(Topic.objects.count() + Reply.objects.count()),
        "active_games": sum(1 for g in games if g.n_topics > 0),
    }

    return JsonResponse(
        {
            "games": [card(g) for g in games],
            "selected": card(selected) if selected else None,
            "topics": topics,
            "stats": stats,
            "rules": COMMUNITY_RULES,
        }
    )
