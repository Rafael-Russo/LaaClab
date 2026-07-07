"""Cross-cutting tests: the per-screen JSON endpoints, the DRF CRUD API
(spanning multiple resources) and basic infrastructure (Celery app, media
settings)."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from catalog.models import Game
from core.models import Module

User = get_user_model()

# Non-manifest static storage so page-shell templates render in tests without
# requiring `collectstatic` (mirrors catalog/tests.py's TEST_STORAGES).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=TEST_STORAGES)
class ModuleGatingTests(TestCase):
    def test_disabled_module_blocks_route(self):
        Module.objects.create(key="community", name="Comunidade", enabled=False)
        u = User.objects.create_user("m", password="pw")
        self.client.force_login(u)
        self.assertEqual(self.client.get("/comunidade/").status_code, 404)

    def test_enabled_module_allows_route(self):
        Module.objects.create(key="community", name="Comunidade", enabled=True)
        u = User.objects.create_user("m2", password="pw")
        self.client.force_login(u)
        self.assertEqual(self.client.get("/comunidade/").status_code, 200)


class ModuleApiGatingTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from rest_framework.test import APIClient
        self.user = get_user_model().objects.create_user("mg", password="pw")
        self.api = APIClient()
        self.api.force_authenticate(self.user)

    def test_disabled_module_blocks_drf_list(self):
        from core.models import Module
        Module.objects.create(key="community", name="C", enabled=False)
        self.assertEqual(self.api.get("/api/v1/topics/").status_code, 403)

    def test_disabled_module_blocks_screen_endpoint(self):
        from core.models import Module
        Module.objects.create(key="community", name="C", enabled=False)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/comunidade/").status_code, 404)

    def test_enabled_module_allows_drf_list(self):
        from core.models import Module
        Module.objects.create(key="community", name="C", enabled=True)
        self.assertEqual(self.api.get("/api/v1/topics/").status_code, 200)


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


class PermissionsSetupTests(TestCase):
    def test_setup_permissions_creates_groups_with_right_perms(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command

        call_command("setup_permissions")
        forum = Group.objects.get(name="Moderador de Fórum")
        self.assertTrue(forum.permissions.filter(codename="can_moderate_forum").exists())
        self.assertFalse(forum.permissions.filter(codename="can_moderate_games").exists())
        games = Group.objects.get(name="Moderador de Jogos/Bugs")
        self.assertTrue(games.permissions.filter(codename="can_moderate_games").exists())
        self.assertFalse(games.permissions.filter(codename="can_moderate_forum").exists())
        # idempotent
        call_command("setup_permissions")
        self.assertEqual(Group.objects.filter(name="Moderador de Fórum").count(), 1)


class InfraTests(TestCase):
    def test_celery_app_importable(self):
        from config.celery import app
        self.assertEqual(app.main, "laaclab")

    def test_media_settings_present(self):
        from django.conf import settings
        self.assertTrue(str(settings.MEDIA_ROOT).endswith("media"))
        self.assertEqual(settings.MEDIA_URL, "/media/")
