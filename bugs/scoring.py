"""Real bug_score aggregation (replaces the P1 placeholder)."""

from django.db.models import Q

from bugs.models import Bug

_SEVERITY_WEIGHT = {"low": 4, "medium": 10, "high": 20, "critical": 35}


def compute_bug_score(game) -> int:
    """0-100 from a game's ACTIVE bugs, weighting severity + confirmations.

    Scraped bugs only count once a moderator confirms them; community reports
    still count while open.
    """
    total = 0.0
    active = game.bugs.filter(status__in=[Bug.Status.OPEN, Bug.Status.CONFIRMED]).exclude(
        Q(source=Bug.Source.SCRAPED) & Q(status=Bug.Status.OPEN)
    )
    for bug in active:
        base = _SEVERITY_WEIGHT.get(bug.severity, 10)
        confirmed = 1.5 if bug.status == Bug.Status.CONFIRMED else 1.0
        # diminishing returns on confirmations
        conf_boost = 1.0 + min(bug.confirmations, 20) / 20.0
        total += base * confirmed * conf_boost
    return int(min(100, round(total)))


def recompute_and_store(game) -> int:
    """Recompute and persist game.bug_score. Returns the new score."""
    score = compute_bug_score(game)
    if game.bug_score != score:
        game.bug_score = score
        game.save(update_fields=["bug_score", "updated_at"])
    return score
