"""Catalogue presentation helpers (game cards, library/favourites listings).

Turns ``Game``/``LibraryEntry`` ORM objects into the exact JSON shapes the
screens expect. Bugômetro/chart/cross-cutting helpers live in
``core/services.py``.
"""

from catalog.models import Game, LibraryEntry

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
    cards = []
    for e in LibraryEntry.objects.filter(user=user).select_related("game"):
        card = game_card(e.game, e.favorite)
        card["entry_id"] = e.id
        cards.append(card)
    return cards


def user_favorite_cards(user) -> list[dict]:
    """The user's favourites (empty when they have none)."""
    entries = list(
        LibraryEntry.objects.filter(user=user, favorite=True).select_related("game")
    )
    return [game_card(e.game, True) for e in entries]


__all__ = [
    "game_card",
    "user_library_cards",
    "user_favorite_cards",
]
