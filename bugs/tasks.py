"""Celery tasks for Fase 3b scraping+classification (see docs plan)."""
import requests
from celery import shared_task
from django.utils.text import Truncator

from bugs.classifier import get_classifier
from bugs.models import Bug, BugSignal
from bugs.scraping import fetch_steam_reviews
from catalog.models import Game


@shared_task(
    bind=True, rate_limit="30/m",
    autoretry_for=(requests.RequestException,), retry_backoff=True, max_retries=3,
)
def scrape_and_classify_game(self, appid: int) -> str:
    game = Game.objects.filter(steam_appid=appid).first()
    if not game:
        return "no-game"
    reviews = fetch_steam_reviews(appid)
    if not reviews:
        return "no-reviews"
    seen = set(
        BugSignal.objects.filter(
            source=Bug.Source.SCRAPED,
            external_id__in=[r["external_id"] for r in reviews],
        ).values_list("external_id", flat=True)
    )
    fresh = [r for r in reviews if r["external_id"] not in seen]
    if not fresh:
        return "nothing-new"
    results = get_classifier().classify([r["text"] for r in fresh])
    created = 0
    for r, c in zip(fresh, results, strict=True):
        if not c.is_bug:
            continue
        bug = (
            Bug.objects.filter(game=game, source=Bug.Source.SCRAPED, category=c.category)
            .order_by("-created_at")
            .first()
        )
        if bug is None:
            bug = Bug.objects.create(
                game=game, title=Truncator(r["text"]).chars(80), description=r["text"],
                category=c.category, source=Bug.Source.SCRAPED, status=Bug.Status.OPEN,
            )
            created += 1
        BugSignal.objects.get_or_create(
            source=Bug.Source.SCRAPED, external_id=r["external_id"],
            defaults={"bug": bug, "url": r.get("url", ""), "text": r["text"][:500], "score": c.score},
        )
    return f"created={created}"


@shared_task
def enqueue_scrape(limit: int | None = None) -> int:
    qs = Game.objects.exclude(steam_appid=None)
    if limit is not None:
        qs = qs[:limit]
    count = 0
    for g in qs:
        scrape_and_classify_game.delay(g.steam_appid)
        count += 1
    return count
