
# Create your tests here.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings

from catalog.models import Game, LibraryEntry

User = get_user_model()

# Non-manifest static storage so the page-shell template renders in tests
# without requiring `collectstatic` (mirrors catalog.tests.TEST_STORAGES).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class MePayloadRoleFlagsTests(TestCase):
    def setUp(self):
        call_command("setup_permissions")
        self.user = User.objects.create_user("u", password="pw")
        self.fmod = User.objects.create_user("fm", password="pw")
        self.fmod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.gmod = User.objects.create_user("gm", password="pw")
        self.gmod.groups.add(Group.objects.get(name="Moderador de Jogos/Bugs"))

    def test_regular_user_has_no_role_flags(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/me/").json()
        self.assertFalse(data["is_forum_moderator"])
        self.assertFalse(data["is_games_moderator"])

    def test_forum_and_games_moderators_flagged(self):
        self.client.force_login(self.fmod)
        self.assertTrue(self.client.get("/api/me/").json()["is_forum_moderator"])
        self.client.force_login(self.gmod)
        self.assertTrue(self.client.get("/api/me/").json()["is_games_moderator"])


@override_settings(STORAGES=TEST_STORAGES)
class ProfileScreenRendersTests(TestCase):
    """The /perfil/ page shell (with the new "Jogos recentes" container and
    the "Ver todos" -> /biblioteca/ link) still renders."""

    def test_profile_page_renders_with_recent_game(self):
        user = User.objects.create_user("pfscreen", password="pw")
        game = Game.objects.create(name="Recent", bug_score=15)
        LibraryEntry.objects.create(user=user, game=game)
        self.client.force_login(user)
        response = self.client.get("/perfil/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'href="/biblioteca/"', response.content)


class MeUnreadCountTests(TestCase):
    def test_me_includes_unread_count(self):
        from notifications.services import notify

        u = User.objects.create_user("mu", password="pw")
        o = User.objects.create_user("mo", password="pw")
        notify(recipient=u, actor=o, kind="reply", text="x", url="/x/")
        self.client.force_login(u)
        self.assertEqual(self.client.get("/api/me/").json()["unread_count"], 1)


class ConfigThemeTests(TestCase):
    def test_me_includes_theme_and_patch_updates(self):
        from rest_framework.test import APIClient

        u = User.objects.create_user("cfg", password="pw")
        self.client.force_login(u)
        self.assertIn("theme", self.client.get("/api/me/").json())
        api = APIClient()
        api.force_authenticate(u)
        r = api.patch("/api/v1/me/", {"theme": "light"}, format="json")
        self.assertEqual(r.status_code, 200)
        u.profile.refresh_from_db()
        self.assertEqual(u.profile.theme, "light")

    def test_theme_rejects_invalid(self):
        from rest_framework.test import APIClient

        u = User.objects.create_user("cfg2", password="pw")
        api = APIClient()
        api.force_authenticate(u)
        r = api.patch("/api/v1/me/", {"theme": "neon"}, format="json")
        self.assertEqual(r.status_code, 400)


@override_settings(STORAGES=TEST_STORAGES)
class ConfigPageTests(TestCase):
    def test_config_page_renders(self):
        u = User.objects.create_user("cp", password="pw")
        self.client.force_login(u)
        self.assertEqual(self.client.get("/configuracao/").status_code, 200)
