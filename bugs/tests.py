from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from bugs.models import Bug, BugVote
from catalog.models import Game

User = get_user_model()


class BugModelTests(TestCase):
    def test_defaults_and_is_active(self):
        g = Game.objects.create(name="G", bug_score=0)
        b = Bug.objects.create(game=g, title="crashes on boot")
        self.assertEqual(b.status, "open")
        self.assertEqual(b.source, "community")
        self.assertTrue(b.is_active)

    def test_vote_unique_per_user(self):
        g = Game.objects.create(name="G2", bug_score=0)
        b = Bug.objects.create(game=g, title="x")
        u = User.objects.create_user("v", password="pw")
        BugVote.objects.create(bug=b, user=u)
        with self.assertRaises(IntegrityError):
            BugVote.objects.create(bug=b, user=u)


class ScoringTests(TestCase):
    def test_no_bugs_is_zero(self):
        from bugs.scoring import compute_bug_score
        g = Game.objects.create(name="S0", bug_score=42)
        self.assertEqual(compute_bug_score(g), 0)

    def test_severity_and_confirmations_raise_score(self):
        from bugs.scoring import compute_bug_score
        g = Game.objects.create(name="S1", bug_score=0)
        Bug.objects.create(game=g, title="a", severity="critical", status="confirmed", confirmations=10)
        high = compute_bug_score(g)
        self.assertGreater(high, 0)
        self.assertLessEqual(high, 100)
        g2 = Game.objects.create(name="S2", bug_score=0)
        Bug.objects.create(game=g2, title="b", severity="low", status="open", confirmations=0)
        self.assertLess(compute_bug_score(g2), high)

    def test_recompute_updates_game(self):
        from bugs.scoring import recompute_and_store
        g = Game.objects.create(name="S3", bug_score=0)
        Bug.objects.create(game=g, title="c", severity="high", status="confirmed", confirmations=3)
        recompute_and_store(g)
        g.refresh_from_db()
        self.assertGreater(g.bug_score, 0)
