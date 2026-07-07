
# Create your tests here.

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from catalog.models import Game
from community.models import Topic

User = get_user_model()


class ForumModerationPermTests(TestCase):
    def setUp(self):
        call_command("setup_permissions")
        self.author = User.objects.create_user("author", password="pw")
        self.mod = User.objects.create_user("mod", password="pw")
        self.mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.other = User.objects.create_user("other", password="pw")
        self.game = Game.objects.create(name="G", bug_score=10)
        self.topic = Topic.objects.create(game=self.game, author=self.author, title="t")
        self.client = APIClient()

    def test_non_author_non_mod_cannot_delete(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.delete(f"/api/v1/topics/{self.topic.id}/").status_code, 403)

    def test_forum_moderator_can_delete(self):
        self.client.force_authenticate(self.mod)
        self.assertEqual(self.client.delete(f"/api/v1/topics/{self.topic.id}/").status_code, 204)


class AnonymousWriteBlockedTests(TestCase):
    def test_anon_cannot_post_topic(self):
        c = APIClient()
        r = c.post("/api/v1/topics/", {"title": "x", "type": "bug"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_anon_cannot_post_library(self):
        c = APIClient()
        r = c.post("/api/v1/library/", {"game": "nope"}, format="json")
        self.assertEqual(r.status_code, 403)
