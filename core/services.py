"""Cross-cutting presentation-layer helpers.

The home, bugômetro and game-detail screens fetch curated JSON. These
functions turn ORM objects into those exact shapes and compute derived,
non-persisted data (the 24h chart, the metric buckets, the recent-activity
feed). Catalogue-specific card builders (``game_card``, ``user_library_cards``,
``user_favorite_cards``) live in ``catalog.services`` and are re-exported here
so ``core.services.game_card`` keeps working for the endpoints in this app.
"""

import math

from django.utils.text import Truncator
from django.utils.timesince import timesince

from bugs.models import Bug
from catalog.models import Game, status_for
from catalog.services import game_card, user_favorite_cards, user_library_cards

# --- Bugômetro derived data -------------------------------------------------

# (key, label, icon) for each of the 4 cards the front-end renders. The shape
# of ``bugometro_metrics``'s return value must stay exactly this — the JS only
# reads data.metrics[i].{key,label,value,level,icon}.
_METRIC_DEFS = [
    ("crash", "Crash", "shield"),
    ("bugs", "Bugs", "bug"),
    ("stutter", "Stutter", "activity"),
    ("fps", "FPS Drop", "gauge"),
]

# Which card each Bug.Category feeds into.
_CATEGORY_TO_CARD = {
    Bug.Category.CRASH: "crash",
    Bug.Category.GRAPHICS: "bugs",
    Bug.Category.PROGRESSION: "bugs",
    Bug.Category.OTHER: "bugs",
    Bug.Category.PERFORMANCE: "stutter",
    Bug.Category.ONLINE: "fps",
}

_SEVERITY_RANK = {
    Bug.Severity.LOW: 0,
    Bug.Severity.MEDIUM: 1,
    Bug.Severity.HIGH: 2,
    Bug.Severity.CRITICAL: 3,
}


def _card_value_level(bugs: list) -> tuple[str, str]:
    """value/level for one card from its bucket of active bugs."""
    if not bugs:
        return "Baixo", "stable"
    max_rank = max(_SEVERITY_RANK.get(b.severity, 0) for b in bugs)
    if max_rank >= _SEVERITY_RANK[Bug.Severity.HIGH] or len(bugs) >= 5:
        return "Alto", "critical"
    return "Médio", "warning"


def bugometro_metrics(game: Game) -> list[dict]:
    """4 cards (crash/bugs/stutter/fps) derived from the game's active bugs."""
    buckets: dict[str, list] = {key: [] for key, _, _ in _METRIC_DEFS}
    active = game.bugs.filter(status__in=[Bug.Status.OPEN, Bug.Status.CONFIRMED])
    for bug in active:
        card = _CATEGORY_TO_CARD.get(bug.category, "bugs")
        buckets[card].append(bug)

    metrics = []
    for key, label, icon in _METRIC_DEFS:
        value, level = _card_value_level(buckets[key])
        metrics.append(
            {"key": key, "label": label, "value": value, "level": level, "icon": icon}
        )
    return metrics


_CHART_LABELS = [
    "06h", "07h", "08h", "09h", "10h", "11h", "12h", "13h",
    "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h",
    "22h", "23h", "00h", "01h", "02h", "03h", "04h", "05h",
]


def _series(amplitude: float, phase: float, base: float) -> list[int]:
    return [
        round(max(0, base + amplitude * math.sin((i / 24) * math.pi * 2 + phase)))
        for i in range(24)
    ]


def bugometro_chart() -> dict:
    return {
        "labels": _CHART_LABELS,
        "series": [
            {"key": "crash", "label": "Crash", "color": "#ef4444", "data": _series(35, 0.4, 55)},
            {"key": "bug", "label": "Bug", "color": "#f59e0b", "data": _series(28, 1.6, 45)},
            {"key": "stutter", "label": "Stutter", "color": "#a855f7", "data": _series(22, 2.7, 35)},
            {"key": "fps", "label": "FPS Drop", "color": "#ec4899", "data": _series(30, 3.9, 48)},
        ],
    }


def top_unstable(limit: int = 4) -> list[dict]:
    return [
        {"name": g.name, "score": g.bug_score, "status": g.status}
        for g in Game.objects.order_by("-bug_score")[:limit]
    ]


def humanize_when(dt) -> str:
    """'há 3 minutos' style relative time."""
    return "há " + timesince(dt).split(",")[0].strip()


def game_activity(game: Game, limit: int = 4) -> list[dict]:
    """Recent-activity feed for the bugômetro, derived from the game's alerts."""
    items = []
    for alert in game.alerts.all()[:limit]:
        items.append(
            {
                "title": alert.get_severity_display(),
                "subtitle": Truncator(alert.text).chars(48),
                "when": humanize_when(alert.created_at),
                "level": alert.level,
            }
        )
    return items


__all__ = [
    "game_card",
    "user_library_cards",
    "user_favorite_cards",
    "bugometro_metrics",
    "bugometro_chart",
    "top_unstable",
    "game_activity",
    "humanize_when",
    "status_for",
]
