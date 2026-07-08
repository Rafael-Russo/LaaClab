
# Create your tests here.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase

User = get_user_model()


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
