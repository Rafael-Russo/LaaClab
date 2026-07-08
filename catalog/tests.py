"""Tests for the catalogue domain: models, Steam ingestion helpers, Celery
ingest tasks, the ``ingest``/``ingest_status`` management commands, the
explore/library page shells and the games/library CRUD API."""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import UserProfile
from alerts.models import Alert
from catalog.models import Game, IngestCandidate, LibraryEntry, status_for
from community.models import Topic

User = get_user_model()

# Non-manifest static storage so page-shell templates render in tests without
# requiring `collectstatic` (the manifest is git-ignored and CI skips collect).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class IngestionHelperTests(TestCase):
    def test_parse_owners(self):
        from catalog.ingestion import parse_owners
        self.assertEqual(parse_owners("10,000,000 .. 20,000,000"), 10000000)
        self.assertEqual(parse_owners(""), 0)
        self.assertEqual(parse_owners("1.234"), 1234)

    def test_steamspy_candidates(self):
        from catalog.ingestion import steamspy_candidates
        payload = {
            "730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"},
            "570": {"appid": 570, "name": "Dota 2", "owners": "100,000,000 .. 200,000,000"},
        }
        items = steamspy_candidates(payload)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["appid"], 730)
        self.assertEqual(items[0]["owners"], 50000000)

    def test_game_defaults_from_appdetails_maps_fields(self):
        from catalog.ingestion import game_defaults_from_appdetails
        data = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG.", "detailed_description": "<h1>Sobre</h1> jogo",
            "header_image": "https://x/y.jpg",
            "release_date": {"date": "10 dez. 2020"},
            "developers": ["CD PROJEKT RED"], "publishers": ["CD PROJEKT RED"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        d = game_defaults_from_appdetails(1091500, data)
        self.assertEqual(d["name"], "Cyberpunk 2077")
        self.assertEqual(d["metacritic"], 86)
        self.assertEqual(d["genres_names"], ["RPG"])
        self.assertNotIn("<h1>", d["about"])
        self.assertEqual(d["bug_score"], 0)

    def test_game_defaults_returns_none_for_non_game(self):
        from catalog.ingestion import game_defaults_from_appdetails
        self.assertIsNone(game_defaults_from_appdetails(1, {"type": "dlc", "name": "X"}))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class IngestTaskTests(TestCase):
    def test_ingest_game_creates_game_and_marks_done(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=1091500, name="Cyberpunk 2077")
        appdata = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG", "detailed_description": "jogo",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["CDPR"], "publishers": ["CDPR"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value="covers/cyberpunk-2077.jpg"):
            result = tasks.ingest_game(1091500)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=1091500)
        self.assertEqual(game.metacritic, 86)
        self.assertEqual(game.cover_file.name, "covers/cyberpunk-2077.jpg")
        self.assertEqual(game.genres.count(), 1)
        self.assertEqual(IngestCandidate.objects.get(appid=1091500).status, "done")

    def test_ingest_game_marks_failed_on_missing_data(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=999, name="Ghost")
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=None):
            result = tasks.ingest_game(999)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=999)
        self.assertEqual(c.status, "failed")
        self.assertEqual(c.attempts, 1)

    def test_refresh_applist_creates_candidates(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        page = {"730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"}}
        with mock.patch("catalog.tasks.fetch_steamspy_page", return_value=page):
            n = tasks.refresh_applist(pages=1)
        self.assertEqual(n, 1)
        self.assertTrue(IngestCandidate.objects.filter(appid=730).exists())

    def test_enqueue_pending_only_non_done(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="pending")
        IngestCandidate.objects.create(appid=2, status="done")
        with mock.patch("catalog.tasks.ingest_game.delay") as delayed:
            n = tasks.enqueue_pending()
        self.assertEqual(n, 1)
        delayed.assert_called_once_with(1)

    def test_ingest_game_slug_unique_for_duplicate_names(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=111, name="Same Name")
        IngestCandidate.objects.create(appid=222, name="Same Name")
        appdata = {
            "type": "game", "name": "Same Name",
            "short_description": "d", "detailed_description": "d",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["X"], "publishers": ["X"],
            "metacritic": {"score": 80}, "achievements": {"total": 1},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value=""):
            r1 = tasks.ingest_game(111)
            r2 = tasks.ingest_game(222)
        self.assertEqual(r1, "done")
        self.assertEqual(r2, "done")
        games = Game.objects.filter(name="Same Name")
        self.assertEqual(games.count(), 2)
        slugs = set(games.values_list("slug", flat=True))
        self.assertEqual(len(slugs), 2)
        statuses = set(
            IngestCandidate.objects.filter(appid__in=[111, 222]).values_list(
                "status", flat=True
            )
        )
        self.assertEqual(statuses, {"done"})

    def test_ingest_game_empty_slug_name(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=333, name="日本語ゲーム")
        appdata = {
            "type": "game", "name": "日本語ゲーム",
            "short_description": "d", "detailed_description": "d",
            "header_image": "", "release_date": {"date": "2020"},
            "developers": [], "publishers": [],
            "metacritic": None, "achievements": {"total": 0},
            "genres": [],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value=""):
            result = tasks.ingest_game(333)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=333)
        self.assertTrue(game.slug)
        self.assertEqual(IngestCandidate.objects.get(appid=333).status, "done")

    def test_ingest_game_marks_failed_on_network_error(self):
        import requests

        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=444, name="Boom")
        with mock.patch(
            "catalog.tasks.fetch_appdetails", side_effect=requests.RequestException("boom")
        ):
            result = tasks.ingest_game(444)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=444)
        self.assertEqual(c.status, "failed")
        self.assertIn("boom", c.last_error)
        self.assertEqual(c.attempts, 1)


class IngestCommandTests(TestCase):
    def test_ingest_status_counts(self):
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="done")
        IngestCandidate.objects.create(appid=2, status="pending")
        out = StringIO()
        call_command("ingest_status", stdout=out)
        text = out.getvalue()
        self.assertIn("done=1", text)
        self.assertIn("pending=1", text)

    def test_ingest_sync_resume_processes_pending(self):
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=730, name="CS2", status="pending")
        with mock.patch("catalog.tasks.ingest_game") as ig:
            ig.return_value = "done"
            call_command("ingest", "--resume", "--sync", stdout=StringIO())
        ig.assert_called_once_with(730)


class ModelTests(TestCase):
    def test_status_thresholds(self):
        self.assertEqual(status_for(80)["level"], "critical")
        self.assertEqual(status_for(50)["level"], "warning")
        self.assertEqual(status_for(10)["level"], "stable")

    def test_game_derives_slug_initials_and_status(self):
        g = Game.objects.create(name="Call of Duty", bug_score=72)
        self.assertEqual(g.slug, "call-of-duty")
        self.assertEqual(g.initials, "CO")
        self.assertEqual(g.status["level"], "critical")

    def test_profile_created_with_user(self):
        u = User.objects.create_user("newbie", password="x")
        self.assertTrue(UserProfile.objects.filter(user=u).exists())

    def test_topic_level_and_alert_presentation(self):
        u = User.objects.create_user("a", password="x")
        g = Game.objects.create(name="X Game", bug_score=10)
        topic = Topic.objects.create(game=g, author=u, title="t", type=Topic.Type.BUG)
        self.assertEqual(topic.level, "warning")
        alert = Alert.objects.create(game=g, severity=Alert.Severity.UPDATE, text="hi")
        self.assertEqual(alert.level, "stable")
        self.assertEqual(alert.icon, "check")


@override_settings(STORAGES=TEST_STORAGES)
class ExploreScreenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("exp", password="pw")

    def test_explore_page_renders(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/explorar/").status_code, 200)

    def test_explore_requires_login(self):
        self.assertEqual(self.client.get("/explorar/").status_code, 302)


class IngestCandidateModelTests(TestCase):
    def test_defaults(self):
        c = IngestCandidate.objects.create(appid=730, name="CS2")
        self.assertEqual(c.status, "pending")
        self.assertEqual(c.attempts, 0)
        self.assertEqual(c.owners, 0)

    def test_game_new_fields(self):
        g = Game.objects.create(name="X", bug_score=10, popularity=5000)
        self.assertEqual(g.popularity, 5000)
        self.assertFalse(g.cover_file)


class CatalogApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cat", password="pw")
        Game.objects.create(name="Alpha", bug_score=10, popularity=100)
        Game.objects.create(name="Beta", bug_score=20, popularity=900)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_serializer_exposes_cover_file_and_popularity(self):
        r = self.client.get("/api/v1/games/")
        row = r.json()["results"][0]
        self.assertIn("cover_file", row)
        self.assertIn("popularity", row)

    def test_order_by_popularity_desc(self):
        r = self.client.get("/api/v1/games/?ordering=-popularity")
        names = [g["name"] for g in r.json()["results"]]
        self.assertEqual(names[0], "Beta")


class LibraryScopeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("lib", password="pw")
        self.game = Game.objects.create(name="Solo", bug_score=10)

    def test_library_empty_when_user_has_none(self):
        from core import services
        self.assertEqual(services.user_library_cards(self.user), [])
        self.assertEqual(services.user_favorite_cards(self.user), [])

    def test_biblioteca_endpoint_empty_for_new_user(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["games"], [])

    def test_game_card_includes_cover_file_key(self):
        from core import services
        card = services.game_card(self.game)
        self.assertIn("cover_file", card)

    def test_biblioteca_card_includes_entry_id(self):
        entry = LibraryEntry.objects.create(user=self.user, game=self.game, favorite=True)
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(len(data["games"]), 1)
        card = data["games"][0]
        self.assertEqual(card["entry_id"], entry.id)
        self.assertTrue(card["favorite"])
