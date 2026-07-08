
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


class ModerationActionTests(TestCase):
    def setUp(self):
        call_command("setup_permissions")
        self.author = User.objects.create_user("a", password="pw")
        self.mod = User.objects.create_user("mod", password="pw")
        self.mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.game = Game.objects.create(name="G", bug_score=10)
        self.topic = Topic.objects.create(game=self.game, author=self.author, title="t")
        self.client = APIClient()

    def test_non_moderator_cannot_hide(self):
        self.client.force_authenticate(self.author)  # author, but not a moderator
        r = self.client.post(f"/api/v1/topics/{self.topic.id}/hide/")
        self.assertEqual(r.status_code, 403)

    def test_moderator_can_hide_and_sets_fields(self):
        self.client.force_authenticate(self.mod)
        r = self.client.post(f"/api/v1/topics/{self.topic.id}/hide/")
        self.assertEqual(r.status_code, 200)
        self.topic.refresh_from_db()
        self.assertTrue(self.topic.is_hidden)
        self.assertEqual(self.topic.moderated_by, self.mod)

    def test_hidden_topic_absent_for_regular_user(self):
        self.topic.is_hidden = True
        self.topic.save()
        # /api/comunidade/ is a plain Django view (not a DRF one), so it reads
        # request.user from the session — force_authenticate() only patches
        # the request object DRF views build, so it has no effect here.
        self.client.force_login(self.author)
        data = self.client.get(f"/api/comunidade/?game={self.game.slug}").json()
        titles = [t["title"] for t in data["topics"]]
        self.assertNotIn("t", titles)


class RestHiddenAndLockTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        from rest_framework.test import APIClient

        from catalog.models import Game
        from community.models import Topic
        call_command("setup_permissions")
        U = get_user_model()
        self.author = U.objects.create_user("au", password="pw")
        self.mod = U.objects.create_user("mo", password="pw")
        self.mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.game = Game.objects.create(name="G", bug_score=10)
        self.topic = Topic.objects.create(game=self.game, author=self.author, title="visible")
        self.hidden = Topic.objects.create(game=self.game, author=self.author, title="secret", is_hidden=True)
        self.client = APIClient()

    def test_regular_user_list_excludes_hidden(self):
        self.client.force_authenticate(self.author)
        titles = [t["title"] for t in self.client.get("/api/v1/topics/").json()["results"]]
        self.assertIn("visible", titles)
        self.assertNotIn("secret", titles)

    def test_moderator_list_includes_hidden(self):
        self.client.force_authenticate(self.mod)
        titles = [t["title"] for t in self.client.get("/api/v1/topics/").json()["results"]]
        self.assertIn("secret", titles)

    def test_reply_to_locked_topic_rejected_for_regular_user(self):
        self.topic.is_locked = True
        self.topic.save()
        self.client.force_authenticate(self.author)
        r = self.client.post("/api/v1/replies/", {"topic": self.topic.id, "body": "hi"}, format="json")
        self.assertEqual(r.status_code, 403)

    def test_moderator_can_reply_to_locked_topic(self):
        self.topic.is_locked = True
        self.topic.save()
        self.client.force_authenticate(self.mod)
        r = self.client.post("/api/v1/replies/", {"topic": self.topic.id, "body": "hi"}, format="json")
        self.assertEqual(r.status_code, 201)
