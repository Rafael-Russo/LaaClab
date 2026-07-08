"""Print IngestCandidate counts per status."""

from django.core.management.base import BaseCommand

from catalog.models import IngestCandidate


class Command(BaseCommand):
    help = "Show catalogue ingestion progress (counts per status)."

    def handle(self, *args, **options):
        parts = []
        for status, _ in IngestCandidate.Status.choices:
            parts.append(f"{status}={IngestCandidate.objects.filter(status=status).count()}")
        self.stdout.write(" ".join(parts))
