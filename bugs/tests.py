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


class BugApiTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        from rest_framework.test import APIClient
        call_command("setup_permissions")
        self.game = Game.objects.create(name="AG", bug_score=0, slug="ag")
        self.user = User.objects.create_user("u", password="pw")
        self.mod = User.objects.create_user("m", password="pw")
        self.mod.groups.add(Group.objects.get(name="Moderador de Jogos/Bugs"))
        self.api = APIClient()

    def test_report_creates_bug(self):
        self.api.force_authenticate(self.user)
        r = self.api.post("/api/v1/bug-reports/",
                          {"game": "ag", "text": "trava ao abrir", "category": "crash"}, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(Bug.objects.filter(game=self.game).count(), 1)

    def test_vote_is_unique_and_updates_confirmations(self):
        self.api.force_authenticate(self.user)
        bug = Bug.objects.create(game=self.game, title="b")
        r = self.api.post("/api/v1/bug-votes/", {"bug": bug.id}, format="json")
        self.assertIn(r.status_code, (200, 201))
        r2 = self.api.post("/api/v1/bug-votes/", {"bug": bug.id}, format="json")
        self.assertIn(r2.status_code, (200, 201))  # idempotent, no crash
        bug.refresh_from_db()
        self.assertEqual(bug.confirmations, 1)

    def test_only_moderator_can_confirm(self):
        bug = Bug.objects.create(game=self.game, title="b")
        self.api.force_authenticate(self.user)
        self.assertEqual(self.api.post(f"/api/v1/bugs/{bug.id}/confirm/").status_code, 403)
        self.api.force_authenticate(self.mod)
        self.assertEqual(self.api.post(f"/api/v1/bugs/{bug.id}/confirm/").status_code, 200)
        bug.refresh_from_db()
        self.assertEqual(bug.status, "confirmed")

    def test_anon_cannot_report(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().post("/api/v1/bug-reports/", {"game": "ag", "text": "x"}, format="json").status_code, 403)

    def test_bug_report_is_create_only(self):
        from bugs.models import BugReport
        self.api.force_authenticate(self.user)
        self.api.post("/api/v1/bug-reports/",
                      {"game": "ag", "text": "t", "category": "crash"}, format="json")
        rid = BugReport.objects.first().id
        # update/delete are not allowed (create-only viewset)
        self.assertEqual(self.api.patch(f"/api/v1/bug-reports/{rid}/", {"text": "x"}, format="json").status_code, 405)
        self.assertEqual(self.api.delete(f"/api/v1/bug-reports/{rid}/").status_code, 405)


class BugometroRealDataTests(TestCase):
    """P3 Task 4: bugômetro cards + payload derive from real, active bugs."""

    def test_critical_crash_bug_makes_crash_card_critical(self):
        from core.services import bugometro_metrics

        game = Game.objects.create(name="Real Bugs Game", bug_score=0)
        Bug.objects.create(
            game=game, title="Trava ao carregar save",
            category="crash", severity="critical", status="confirmed",
        )
        metrics = {m["key"]: m for m in bugometro_metrics(game)}
        self.assertEqual(metrics["crash"]["level"], "critical")
        # Shape stays exactly what the front-end expects.
        self.assertEqual(
            {m["key"] for m in metrics.values()}, {"crash", "bugs", "stutter", "fps"}
        )

    def test_bugometro_endpoint_returns_real_bugs(self):
        game = Game.objects.create(name="Real Bugs Game 2", bug_score=0)
        bug = Bug.objects.create(
            game=game, title="Trava ao carregar save",
            category="crash", severity="critical", status="confirmed",
        )
        user = User.objects.create_user("bm", password="pw")
        self.client.force_login(user)
        r = self.client.get(f"/api/bugometro/?game={game.slug}")
        self.assertEqual(r.status_code, 200)
        titles = [b["title"] for b in r.json()["bugs"]]
        self.assertIn(bug.title, titles)
