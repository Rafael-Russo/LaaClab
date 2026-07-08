from unittest import mock

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase, override_settings

from bugs.models import Bug, BugVote
from catalog.models import Game

User = get_user_model()


@override_settings(BUGS_CLASSIFIER="fake")
class FakeClassifierTests(TestCase):
    def test_flags_bug_keywords_by_category(self):
        from bugs.classifier import get_classifier
        c = get_classifier()
        res = c.classify(["o jogo trava ao abrir", "servidor não conecta", "amazing game i love it"])
        self.assertTrue(res[0].is_bug)
        self.assertEqual(res[0].category, "crash")
        self.assertTrue(res[1].is_bug)
        self.assertEqual(res[1].category, "online")
        self.assertFalse(res[2].is_bug)


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


class ScoringSourceTests(TestCase):
    def test_open_scraped_bug_does_not_score_until_confirmed(self):
        from bugs.models import Bug
        from bugs.scoring import compute_bug_score
        from catalog.models import Game
        g = Game.objects.create(name="SS", bug_score=0)
        b = Bug.objects.create(game=g, title="x", severity="critical", status="open", source="scraped")
        self.assertEqual(compute_bug_score(g), 0)  # open+scraped -> not counted
        b.status = "confirmed"
        b.save()
        self.assertGreater(compute_bug_score(g), 0)  # confirmed -> counts

    def test_community_open_bug_still_scores(self):
        from bugs.models import Bug
        from bugs.scoring import compute_bug_score
        from catalog.models import Game
        g = Game.objects.create(name="SC", bug_score=0)
        Bug.objects.create(game=g, title="y", severity="high", status="open", source="community")
        self.assertGreater(compute_bug_score(g), 0)


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

    def test_vote_cannot_be_patched(self):
        from bugs.models import Bug
        self.api.force_authenticate(self.user)
        bug = Bug.objects.create(game=self.game, title="v")
        r = self.api.post("/api/v1/bug-votes/", {"bug": bug.id}, format="json")
        vid = r.json()["id"]
        self.assertEqual(self.api.patch(f"/api/v1/bug-votes/{vid}/", {"bug": bug.id}, format="json").status_code, 405)

    def test_reject_drops_score(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command

        from bugs.models import Bug
        call_command("setup_permissions")
        g = self.game
        bug = Bug.objects.create(game=g, title="crash", severity="critical", status="confirmed", confirmations=5)
        g.refresh_from_db()
        self.assertGreater(g.bug_score, 0)
        self.mod.groups.add(Group.objects.get(name="Moderador de Jogos/Bugs"))
        self.api.force_authenticate(self.mod)
        self.assertEqual(self.api.post(f"/api/v1/bugs/{bug.id}/reject/").status_code, 200)
        g.refresh_from_db()
        self.assertEqual(g.bug_score, 0)


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


class ScrapeParseTests(TestCase):
    def test_parse_filters_and_extracts(self):
        from bugs.scraping import parse_reviews
        payload = {"reviews": [
            {"recommendationid": "111", "review": "o jogo [b]trava[/b] muito ao abrir, crash constante",
             "author": {"steamid": "76561198000000001"}},
            {"recommendationid": "222", "review": "gg"},  # curta demais -> filtrada
            {"recommendationid": "333", "review": "servidor nunca conecta, matchmaking quebrado sempre"},
        ]}
        rows = parse_reviews(payload)
        ids = {r["external_id"] for r in rows}
        self.assertEqual(ids, {"111", "333"})
        self.assertNotIn("[b]", rows[0]["text"])
        row_111 = next(r for r in rows if r["external_id"] == "111")
        row_333 = next(r for r in rows if r["external_id"] == "333")
        self.assertIn("76561198000000001", row_111["url"])
        self.assertEqual(row_333["url"], "")  # no author -> empty url


class ScrapeBugsCommandTests(TestCase):
    def test_appid_and_all_together_is_rejected(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("scrape_bugs", appid=999, all=True)

    def test_neither_appid_nor_all_is_rejected(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            call_command("scrape_bugs")


class BugSignalModelTests(TestCase):
    def test_unique_external_id_per_source(self):
        from django.db import IntegrityError

        from bugs.models import Bug, BugSignal
        g = Game.objects.create(name="S", bug_score=0)
        b = Bug.objects.create(game=g, title="x", source="scraped")
        BugSignal.objects.create(bug=b, source="scraped", external_id="r1")
        with self.assertRaises(IntegrityError):
            BugSignal.objects.create(bug=b, source="scraped", external_id="r1")


class SnapshotAndSeedTests(TestCase):
    def test_snapshot_creates_one_per_game(self):
        from django.core.management import call_command

        from bugs.models import GameScoreSnapshot
        from catalog.models import Game
        Game.objects.create(name="A", bug_score=5)
        Game.objects.create(name="B", bug_score=0)
        call_command("snapshot_scores")
        self.assertEqual(GameScoreSnapshot.objects.count(), 2)

    def test_seed_creates_bugs_and_scores(self):
        from django.core.management import call_command

        from bugs.models import Bug
        from catalog.models import Game
        call_command("seed")
        self.assertTrue(Bug.objects.exists())
        # at least one game with bugs has a recomputed non-zero score
        self.assertTrue(Game.objects.filter(bug_score__gt=0).exists())

    def test_seed_no_bug_games_score_zero(self):
        from django.core.management import call_command

        from catalog.models import Game
        call_command("seed")
        # games without any bug must be 0 (the fake fixture score is gone)
        zero_games = Game.objects.filter(bugs__isnull=True).distinct()
        self.assertTrue(zero_games.exists())
        for g in zero_games:
            self.assertEqual(g.bug_score, 0, f"{g.slug} kept a non-recomputed score")


@override_settings(BUGS_CLASSIFIER="fake", CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ScrapeTaskTests(TestCase):
    def setUp(self):
        from catalog.models import Game
        self.game = Game.objects.create(name="SG", bug_score=0, steam_appid=999)

    def _reviews(self):
        return [
            {"external_id": "a1", "text": "o jogo trava toda hora, crash feio", "url": "u1"},
            {"external_id": "a2", "text": "servidor nao conecta nunca, matchmaking quebrado", "url": "u2"},
            {"external_id": "a3", "text": "amazing game, love it, recommend", "url": "u3"},
        ]

    def test_creates_candidate_bugs_and_signals(self):
        from bugs import tasks
        from bugs.models import Bug, BugSignal
        with mock.patch("bugs.tasks.fetch_steam_reviews", return_value=self._reviews()):
            tasks.scrape_and_classify_game(999)
        # a3 is not a bug -> not created; a1(crash) + a2(online) created
        bugs = Bug.objects.filter(game=self.game, source="scraped")
        self.assertEqual(bugs.count(), 2)
        self.assertEqual(set(bugs.values_list("category", flat=True)), {"crash", "online"})
        self.assertTrue(all(b.status == "open" for b in bugs))
        self.assertEqual(BugSignal.objects.count(), 2)

    def test_idempotent_and_coarse_dedup(self):
        from bugs import tasks
        from bugs.models import Bug, BugSignal
        reviews = self._reviews() + [{"external_id": "a4", "text": "outro crash, jogo trava de novo", "url": "u4"}]
        with mock.patch("bugs.tasks.fetch_steam_reviews", return_value=reviews):
            tasks.scrape_and_classify_game(999)
            tasks.scrape_and_classify_game(999)  # re-run: same external_ids
        # a1 and a4 are both crash -> same game+category -> ONE bug, TWO signals
        crash_bugs = Bug.objects.filter(game=self.game, category="crash", source="scraped")
        self.assertEqual(crash_bugs.count(), 1)
        self.assertEqual(BugSignal.objects.filter(bug=crash_bugs.first()).count(), 2)
        # re-run created no duplicates
        self.assertEqual(BugSignal.objects.count(), 3)  # a1,a2,a4 (a3 not a bug)

    def test_moderated_category_not_duplicated(self):
        from bugs import tasks
        from bugs.models import Bug
        r1 = [{"external_id": "m1", "text": "o jogo trava, crash feio", "url": "u"}]
        with mock.patch("bugs.tasks.fetch_steam_reviews", return_value=r1):
            tasks.scrape_and_classify_game(999)
        bug = Bug.objects.get(game=self.game, category="crash", source="scraped")
        bug.status = "confirmed"
        bug.save()
        r2 = [{"external_id": "m2", "text": "outro crash, trava de novo", "url": "u2"}]
        with mock.patch("bugs.tasks.fetch_steam_reviews", return_value=r2):
            tasks.scrape_and_classify_game(999)
        self.assertEqual(Bug.objects.filter(game=self.game, category="crash", source="scraped").count(), 1)
