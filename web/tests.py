"""Tests for models, the per-screen endpoints and the DRF CRUD API."""

from io import StringIO
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from web.models import Alert, Game, Topic, UserProfile, status_for

User = get_user_model()

# Non-manifest static storage so page-shell templates render in tests without
# requiring `collectstatic` (the manifest is git-ignored and CI skips collect).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


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


class ScreenEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("gamer", password="pw")
        self.game = Game.objects.create(name="Warzone", bug_score=72)

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/home/").status_code, 401)

    def test_all_screens_return_200(self):
        self.client.force_login(self.user)
        urls = [
            "/api/me/", "/api/home/", "/api/bugometro/", "/api/biblioteca/",
            "/api/comunidade/", "/api/alertas/", "/api/perfil/",
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertEqual(self.client.get(f"/api/jogo/{self.game.slug}/").status_code, 200)
        self.assertEqual(self.client.get("/api/jogo/does-not-exist/").status_code, 404)


@override_settings(STORAGES=TEST_STORAGES)
class ExploreScreenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("exp", password="pw")

    def test_explore_page_renders(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/explorar/").status_code, 200)

    def test_explore_requires_login(self):
        self.assertEqual(self.client.get("/explorar/").status_code, 302)


class CrudApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u1", password="pw")
        self.other = User.objects.create_user("u2", password="pw")
        self.staff = User.objects.create_user("boss", password="pw", is_staff=True)
        self.game = Game.objects.create(name="Warzone", bug_score=72)
        self.client = APIClient()

    def test_anonymous_forbidden(self):
        self.assertEqual(self.client.get("/api/v1/games/").status_code, 403)

    def test_catalogue_read_only_for_regular_user(self):
        self.client.force_authenticate(self.user)
        self.assertEqual(self.client.get("/api/v1/games/").status_code, 200)
        r = self.client.post("/api/v1/games/", {"name": "Hackzor"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_staff_can_create_game(self):
        self.client.force_authenticate(self.staff)
        r = self.client.post(
            "/api/v1/games/", {"name": "New Game", "bug_score": 10}, format="json"
        )
        self.assertEqual(r.status_code, 201, r.content)

    def test_topic_author_set_and_owner_only_delete(self):
        self.client.force_authenticate(self.user)
        r = self.client.post(
            "/api/v1/topics/",
            {"title": "t", "type": "bug", "game": self.game.slug},
            format="json",
        )
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["author"], "u1")
        topic_id = r.data["id"]

        # A different, non-staff user may not delete it.
        self.client.force_authenticate(self.other)
        self.assertEqual(
            self.client.delete(f"/api/v1/topics/{topic_id}/").status_code, 403
        )
        # The author may.
        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.delete(f"/api/v1/topics/{topic_id}/").status_code, 204
        )

    def test_library_scoped_and_idempotent(self):
        self.client.force_authenticate(self.user)
        r1 = self.client.post(
            "/api/v1/library/", {"game": self.game.slug, "favorite": True}, format="json"
        )
        self.assertIn(r1.status_code, (200, 201))
        r2 = self.client.post(
            "/api/v1/library/", {"game": self.game.slug, "favorite": False}, format="json"
        )
        self.assertIn(r2.status_code, (200, 201))  # no unique-constraint crash
        self.assertEqual(self.client.get("/api/v1/library/").data["count"], 1)

        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get("/api/v1/library/").data["count"], 0)

    def test_profile_patch_respects_read_only_fields(self):
        self.client.force_authenticate(self.user)
        r = self.client.patch(
            "/api/v1/me/", {"bio": "hello", "level": 999}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["bio"], "hello")
        self.assertNotEqual(r.data["level"], 999)


class InfraTests(TestCase):
    def test_celery_app_importable(self):
        from config.celery import app
        self.assertEqual(app.main, "laaclab")

    def test_media_settings_present(self):
        from django.conf import settings
        self.assertTrue(str(settings.MEDIA_ROOT).endswith("media"))
        self.assertEqual(settings.MEDIA_URL, "/media/")


class IngestCandidateModelTests(TestCase):
    def test_defaults(self):
        from web.models import IngestCandidate
        c = IngestCandidate.objects.create(appid=730, name="CS2")
        self.assertEqual(c.status, "pending")
        self.assertEqual(c.attempts, 0)
        self.assertEqual(c.owners, 0)

    def test_game_new_fields(self):
        from web.models import Game
        g = Game.objects.create(name="X", bug_score=10, popularity=5000)
        self.assertEqual(g.popularity, 5000)
        self.assertFalse(g.cover_file)


class IngestionHelperTests(TestCase):
    def test_parse_owners(self):
        from web.ingestion import parse_owners
        self.assertEqual(parse_owners("10,000,000 .. 20,000,000"), 10000000)
        self.assertEqual(parse_owners(""), 0)
        self.assertEqual(parse_owners("1.234"), 1234)

    def test_steamspy_candidates(self):
        from web.ingestion import steamspy_candidates
        payload = {
            "730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"},
            "570": {"appid": 570, "name": "Dota 2", "owners": "100,000,000 .. 200,000,000"},
        }
        items = steamspy_candidates(payload)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["appid"], 730)
        self.assertEqual(items[0]["owners"], 50000000)

    def test_game_defaults_from_appdetails_maps_fields(self):
        from web.ingestion import game_defaults_from_appdetails
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
        self.assertGreaterEqual(d["bug_score"], 10)

    def test_game_defaults_returns_none_for_non_game(self):
        from web.ingestion import game_defaults_from_appdetails
        self.assertIsNone(game_defaults_from_appdetails(1, {"type": "dlc", "name": "X"}))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class IngestTaskTests(TestCase):
    def test_ingest_game_creates_game_and_marks_done(self):
        from web import tasks
        from web.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=1091500, name="Cyberpunk 2077")
        appdata = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG", "detailed_description": "jogo",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["CDPR"], "publishers": ["CDPR"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("web.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("web.tasks.download_cover", return_value="covers/cyberpunk-2077.jpg"):
            result = tasks.ingest_game(1091500)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=1091500)
        self.assertEqual(game.metacritic, 86)
        self.assertEqual(game.cover_file.name, "covers/cyberpunk-2077.jpg")
        self.assertEqual(game.genres.count(), 1)
        self.assertEqual(IngestCandidate.objects.get(appid=1091500).status, "done")

    def test_ingest_game_marks_failed_on_missing_data(self):
        from web import tasks
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=999, name="Ghost")
        with mock.patch("web.tasks.fetch_appdetails", return_value=None):
            result = tasks.ingest_game(999)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=999)
        self.assertEqual(c.status, "failed")
        self.assertEqual(c.attempts, 1)

    def test_refresh_applist_creates_candidates(self):
        from web import tasks
        from web.models import IngestCandidate
        page = {"730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"}}
        with mock.patch("web.tasks.fetch_steamspy_page", return_value=page):
            n = tasks.refresh_applist(pages=1)
        self.assertEqual(n, 1)
        self.assertTrue(IngestCandidate.objects.filter(appid=730).exists())

    def test_enqueue_pending_only_non_done(self):
        from web import tasks
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="pending")
        IngestCandidate.objects.create(appid=2, status="done")
        with mock.patch("web.tasks.ingest_game.delay") as delayed:
            n = tasks.enqueue_pending()
        self.assertEqual(n, 1)
        delayed.assert_called_once_with(1)

    def test_ingest_game_slug_unique_for_duplicate_names(self):
        from web import tasks
        from web.models import Game, IngestCandidate
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
        with mock.patch("web.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("web.tasks.download_cover", return_value=""):
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
        from web import tasks
        from web.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=333, name="日本語ゲーム")
        appdata = {
            "type": "game", "name": "日本語ゲーム",
            "short_description": "d", "detailed_description": "d",
            "header_image": "", "release_date": {"date": "2020"},
            "developers": [], "publishers": [],
            "metacritic": None, "achievements": {"total": 0},
            "genres": [],
        }
        with mock.patch("web.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("web.tasks.download_cover", return_value=""):
            result = tasks.ingest_game(333)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=333)
        self.assertTrue(game.slug)
        self.assertEqual(IngestCandidate.objects.get(appid=333).status, "done")

    def test_ingest_game_marks_failed_on_network_error(self):
        import requests

        from web import tasks
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=444, name="Boom")
        with mock.patch(
            "web.tasks.fetch_appdetails", side_effect=requests.RequestException("boom")
        ):
            result = tasks.ingest_game(444)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=444)
        self.assertEqual(c.status, "failed")
        self.assertIn("boom", c.last_error)
        self.assertEqual(c.attempts, 1)


class CatalogApiTests(TestCase):
    def setUp(self):
        from web.models import Game
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
        from web.models import Game
        self.user = User.objects.create_user("lib", password="pw")
        self.game = Game.objects.create(name="Solo", bug_score=10)

    def test_library_empty_when_user_has_none(self):
        from web import services
        self.assertEqual(services.user_library_cards(self.user), [])
        self.assertEqual(services.user_favorite_cards(self.user), [])

    def test_biblioteca_endpoint_empty_for_new_user(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["games"], [])

    def test_game_card_includes_cover_file_key(self):
        from web import services
        card = services.game_card(self.game)
        self.assertIn("cover_file", card)

    def test_biblioteca_card_includes_entry_id(self):
        from web.models import LibraryEntry
        entry = LibraryEntry.objects.create(user=self.user, game=self.game, favorite=True)
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(len(data["games"]), 1)
        card = data["games"][0]
        self.assertEqual(card["entry_id"], entry.id)
        self.assertTrue(card["favorite"])


class IngestCommandTests(TestCase):
    def test_ingest_status_counts(self):
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="done")
        IngestCandidate.objects.create(appid=2, status="pending")
        out = StringIO()
        call_command("ingest_status", stdout=out)
        text = out.getvalue()
        self.assertIn("done=1", text)
        self.assertIn("pending=1", text)

    def test_ingest_sync_resume_processes_pending(self):
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=730, name="CS2", status="pending")
        with mock.patch("web.tasks.ingest_game") as ig:
            ig.return_value = "done"
            call_command("ingest", "--resume", "--sync", stdout=StringIO())
        ig.assert_called_once_with(730)
