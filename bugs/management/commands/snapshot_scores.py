"""Record a point-in-time GameScoreSnapshot for every game (feeds P4 Históricos).

Not idempotent by design: each run adds a new data point to the time series.

    python manage.py snapshot_scores
"""

from django.core.management.base import BaseCommand

from bugs.models import GameScoreSnapshot
from catalog.models import Game


class Command(BaseCommand):
    help = "Create a GameScoreSnapshot for every game's current bug_score."

    def handle(self, *args, **options):
        snapshots = [
            GameScoreSnapshot(game=game, bug_score=game.bug_score)
            for game in Game.objects.all()
        ]
        GameScoreSnapshot.objects.bulk_create(snapshots)
        self.stdout.write(self.style.SUCCESS(f"snapshots: {len(snapshots)} created"))
