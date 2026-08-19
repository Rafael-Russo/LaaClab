"""Community JSON endpoint consumed by the community screen via ``fetch()``."""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
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
    games = list(Game.objects.annotate(n_topics=Count("topics")).prefetch_related("genres"))
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

        type_key = request.GET.get("type") or ""
        if type_key:
            qs = qs.filter(type=type_key)
        term = request.GET.get("q") or ""
        if term:
            qs = qs.filter(Q(title__icontains=term) | Q(body__icontains=term))
        ordering = request.GET.get("ordering") or "-created_at"
        if ordering in ("created_at", "-created_at"):
            qs = qs.order_by(ordering)

        for t in qs[:20]:
            topics.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "author": t.author.username,
                    "when": services.humanize_when(t.created_at),
                    "type": t.get_type_display(),
                    "level": t.level,
                    "excerpt": Truncator(t.body).chars(160),
                    "is_hidden": t.is_hidden,
                    "is_locked": t.is_locked,
                    "is_pinned": t.is_pinned,
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


@api_login_required
@require_module_api("community")
def thread(request, pk):
    topic = get_object_or_404(Topic.objects.select_related("author", "game"), pk=pk)
    is_mod = request.user.has_perm("community.can_moderate_forum") or request.user.is_staff
    if topic.is_hidden and not is_mod:
        return JsonResponse({"detail": "Tópico indisponível."}, status=404)
    replies_qs = topic.replies.select_related("author")
    if not is_mod:
        replies_qs = replies_qs.filter(is_hidden=False)
    return JsonResponse(
        {
            "topic": {
                "id": topic.id,
                "title": topic.title,
                "body": topic.body,
                "author": topic.author.username,
                "type_display": topic.get_type_display(),
                "level": topic.level,
                "is_locked": topic.is_locked,
                "is_hidden": topic.is_hidden,
                "is_pinned": topic.is_pinned,
                "when": services.humanize_when(topic.created_at),
                "game": topic.game.slug if topic.game_id else "",
            },
            "replies": [
                {
                    "id": r.id,
                    "author": r.author.username,
                    "body": r.body,
                    "when": services.humanize_when(r.created_at),
                }
                for r in replies_qs
            ],
        }
    )
