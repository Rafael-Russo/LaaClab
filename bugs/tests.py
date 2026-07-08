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
