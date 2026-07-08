"""Kick off (or resume) the bulk catalogue ingestion.

    python manage.py ingest --pages 5           # refresh ranking + enqueue
    python manage.py ingest --resume            # only enqueue pending/failed
    python manage.py ingest --pages 1 --sync    # run inline (no worker)
"""

from django.core.management.base import BaseCommand

from catalog import tasks
from catalog.models import IngestCandidate


class Command(BaseCommand):
    help = "Populate the catalogue from Steam via Celery (resumable)."

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=1,
                            help="SteamSpy pages to pull (~1000 games each).")
        parser.add_argument("--limit", type=int, default=None,
                            help="Max candidates to enqueue this run.")
        parser.add_argument("--resume", action="store_true",
                            help="Skip the ranking refresh; only enqueue pending/failed.")
        parser.add_argument("--sync", action="store_true",
                            help="Run inline without a worker (small/testing).")

    def handle(self, *args, **options):
        if not options["resume"]:
            n = tasks.refresh_applist(pages=options["pages"])
            self.stdout.write(f"candidatos atualizados: {n}")

        if options["sync"]:
            qs = IngestCandidate.objects.exclude(status=IngestCandidate.Status.DONE)
            if options["limit"] is not None:
                qs = qs[: options["limit"]]
            for candidate in list(qs):
                tasks.ingest_game(candidate.appid)
            self.stdout.write("ingestão síncrona concluída")
        else:
            n = tasks.enqueue_pending(limit=options["limit"])
            self.stdout.write(f"tarefas enfileiradas: {n}")
