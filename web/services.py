"""Presentation-layer helpers.

The screens fetch curated JSON per view. These functions turn ORM objects into
those exact shapes and compute derived, non-persisted data (the 24h chart, the
metric buckets, the recent-activity feed). Keeping this out of the models and
out of the REST serializers lets the CRUD API stay clean while the screen
endpoints keep their stable contract.
"""

import math

from django.utils.text import Truncator
from django.utils.timesince import timesince

from .models import Game, LibraryEntry, status_for

# --- Game cards -------------------------------------------------------------

_DEFAULT_COVER = ["#2b2d47", "#14152b"]


def game_card(game: Game, favorite: bool = False) -> dict:
    """A game as the grids/cards expect it."""
    return {
        "slug": game.slug,
        "name": game.name,
        "score": game.bug_score,
        "initials": game.initials,
        "cover": game.cover or _DEFAULT_COVER,
        "cover_image": game.cover_image,
        "cover_file": game.cover_file.url if game.cover_file else "",
        "favorite": favorite,
        "status": game.status,
    }


def user_library_cards(user) -> list[dict]:
    """The user's library (empty when they have none)."""
    entries = list(LibraryEntry.objects.filter(user=user).select_related("game"))
    return [game_card(e.game, e.favorite) for e in entries]


def user_favorite_cards(user) -> list[dict]:
    """The user's favourites (empty when they have none)."""
    entries = list(
        LibraryEntry.objects.filter(user=user, favorite=True).select_related("game")
    )
    return [game_card(e.game, True) for e in entries]


# --- Bugômetro derived data -------------------------------------------------


def _value_level(score: int) -> tuple[str, str]:
    if score >= 65:
        return "Alto", "critical"
    if score >= 40:
        return "Médio", "warning"
    return "Baixo", "stable"


# (key, label, icon, score offset) — offsets spread the four sub-metrics around
# the game's overall bug score so they read distinctly.
_METRIC_DEFS = [
    ("crash", "Crash", "shield", 6),
    ("bugs", "Bugs", "bug", -18),
    ("stutter", "Stutter", "activity", -34),
    ("fps", "FPS Drop", "gauge", 2),
]


def bugometro_metrics(game: Game) -> list[dict]:
    metrics = []
    for key, label, icon, offset in _METRIC_DEFS:
        score = max(0, min(100, game.bug_score + offset))
        value, level = _value_level(score)
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
