"""Scrape Steam reviews and classify candidate bugs (Fase 3b).

    python manage.py scrape_bugs --appid 999           # enqueue via Celery
    python manage.py scrape_bugs --appid 999 --sync    # run inline (no worker)
    python manage.py scrape_bugs --all --limit 10      # enqueue for all games
    python manage.py scrape_bugs --all --sync          # run inline for all games
"""

from django.core.management.base import BaseCommand, CommandError

from bugs import tasks
from catalog.models import Game


class Command(BaseCommand):
    help = "Scrape Steam reviews and create candidate bugs via classification."

    def add_arguments(self, parser):
        parser.add_argument("--appid", type=int, default=None,
                            help="Steam appid of a single game to scrape.")
        parser.add_argument("--all", action="store_true",
                            help="Scrape every game that has a steam_appid.")
        parser.add_argument("--limit", type=int, default=None,
                            help="Max games to process (with --all).")
        parser.add_argument("--sync", action="store_true",
                            help="Run inline without a worker (small/testing).")

    def handle(self, *args, **options):
        if options["all"] and options["appid"] is not None:
            raise CommandError("use --appid OR --all, not both")
        if not options["all"] and options["appid"] is None:
            raise CommandError("provide --appid or --all")

        if options["sync"]:
            appids = self._sync_appids(options)
            for appid in appids:
                result = tasks.scrape_and_classify_game(appid)
                self.stdout.write(f"appid {appid}: {result}")
            self.stdout.write(self.style.SUCCESS(f"scraping síncrono concluído ({len(appids)})"))
        elif options["all"]:
            n = tasks.enqueue_scrape(limit=options["limit"])
            self.stdout.write(f"tarefas enfileiradas: {n}")
        else:
            tasks.scrape_and_classify_game.delay(options["appid"])
            self.stdout.write("tarefa enfileirada: 1")

    def _sync_appids(self, options) -> list[int]:
        if options["appid"] is not None:
            return [options["appid"]]
        qs = Game.objects.exclude(steam_appid=None)
        if options["limit"] is not None:
            qs = qs[: options["limit"]]
        return list(qs.values_list("steam_appid", flat=True))
