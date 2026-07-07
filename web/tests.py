"""Tests for models, the per-screen endpoints and the DRF CRUD API."""

from django.contrib.auth import get_user_model
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
        from web.models import LibraryEntry
        entry = LibraryEntry.objects.create(user=self.user, game=self.game, favorite=True)
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(len(data["games"]), 1)
        card = data["games"][0]
        self.assertEqual(card["entry_id"], entry.id)
        self.assertTrue(card["favorite"])
