"""Celery tasks for bulk catalogue ingestion (see docs/runbooks/popular-catalogo.md)."""

from celery import shared_task
from django.conf import settings
from django.utils.text import slugify

from .ingestion import (
    download_cover,
    fetch_appdetails,
    fetch_steamspy_page,
    game_defaults_from_appdetails,
    steamspy_candidates,
)
from .models import Game, Genre, IngestCandidate


@shared_task
def refresh_applist(pages: int = 1) -> int:
    """Pull ranked appids from SteamSpy into IngestCandidate. Returns upserts."""
    count = 0
    for page in range(pages):
        payload = fetch_steamspy_page(page)
        for rank, item in enumerate(steamspy_candidates(payload)):
            IngestCandidate.objects.update_or_create(
                appid=item["appid"],
                defaults={
                    "name": item["name"],
                    "owners": item["owners"],
                    "rank": page * 1000 + rank,
                },
            )
            count += 1
    return count


@shared_task
def enqueue_pending(limit: int | None = None) -> int:
    """Dispatch ingest_game for every candidate not yet done. Returns count."""
    qs = IngestCandidate.objects.exclude(status=IngestCandidate.Status.DONE)
    if limit is not None:
        qs = qs[:limit]
    count = 0
    for candidate in qs:
        ingest_game.delay(candidate.appid)
        count += 1
    return count


@shared_task(bind=True, rate_limit="40/m")
def ingest_game(self, appid: int) -> str:
    """Fetch appdetails, upsert the Game, download its cover. Idempotent."""
    candidate, _ = IngestCandidate.objects.get_or_create(appid=appid)
    candidate.status = IngestCandidate.Status.FETCHING
    candidate.attempts += 1
    candidate.save(update_fields=["status", "attempts", "updated_at"])

    try:
        data = fetch_appdetails(appid)
        defaults = game_defaults_from_appdetails(appid, data) if data else None
        if not defaults:
            candidate.status = IngestCandidate.Status.FAILED
            candidate.last_error = "sem dados de jogo (appdetails)"
            candidate.save(update_fields=["status", "last_error", "updated_at"])
            return "failed"

        genre_names = defaults.pop("genres_names", [])
        slug = (slugify(defaults["name"])[:130] or "game") + f"-{appid}"
        defaults["popularity"] = candidate.owners
        game, _ = Game.objects.update_or_create(
            steam_appid=appid, defaults={**defaults, "slug": slug}
        )

        if game.cover_image:
            rel = download_cover(game.cover_image, game.slug, settings.MEDIA_ROOT)
            if rel:
                game.cover_file.name = rel
                game.save(update_fields=["cover_file"])

        if genre_names:
            genres = [
                Genre.objects.get_or_create(slug=slugify(n), defaults={"name": n})[0]
                for n in genre_names
            ]
            game.genres.set(genres)

        candidate.status = IngestCandidate.Status.DONE
        candidate.last_error = ""
        candidate.save(update_fields=["status", "last_error", "updated_at"])
        return "done"
    except Exception as exc:  # network/DB/etc — mark failed, don't crash the run
        candidate.status = IngestCandidate.Status.FAILED
        candidate.last_error = str(exc)[:500]
        candidate.save(update_fields=["status", "last_error", "updated_at"])
        return "failed"
