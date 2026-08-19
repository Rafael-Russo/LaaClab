
# Create your tests here.

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from catalog.models import Game
from community.models import Reply, Topic

User = get_user_model()

# Non-manifest static storage so page-shell templates render in tests without
# requiring `collectstatic` (mirrors core/tests.py's TEST_STORAGES).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


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


class CommunityTopicPayloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cu", password="pw")
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        self.topic = Topic.objects.create(
            game=self.game, author=self.user, title="t", is_locked=True
        )

    def test_topic_payload_has_id_and_moderation_state(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/comunidade/?game=g").json()
        t = data["topics"][0]
        self.assertEqual(t["id"], self.topic.id)
        self.assertTrue(t["is_locked"])
        self.assertFalse(t["is_hidden"])
        self.assertFalse(t["is_pinned"])


class CommunityFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("cf", password="pw")
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        bug_topic = Topic.objects.create(
            game=self.game, author=self.user, title="Bug do save", type="bug", body="trava"
        )
        tip_topic = Topic.objects.create(
            game=self.game, author=self.user, title="Dica de build", type="tip", body="use isso"
        )
        # auto_now_add timestamps for two rows created back-to-back can tie at
        # whatever resolution the DB stores; force a real, unambiguous gap so
        # ordering assertions below aren't flaky.
        now = timezone.now()
        Topic.objects.filter(pk=bug_topic.pk).update(created_at=now - timedelta(minutes=10))
        Topic.objects.filter(pk=tip_topic.pk).update(created_at=now)
        self.client.force_login(self.user)

    def test_filter_by_type(self):
        data = self.client.get("/api/comunidade/?game=g&type=bug").json()
        titles = [t["title"] for t in data["topics"]]
        self.assertIn("Bug do save", titles)
        self.assertNotIn("Dica de build", titles)

    def test_search_by_term(self):
        data = self.client.get("/api/comunidade/?game=g&q=build").json()
        self.assertEqual([t["title"] for t in data["topics"]], ["Dica de build"])

    def test_ordering_ascending(self):
        data = self.client.get("/api/comunidade/?game=g&ordering=created_at").json()
        titles = [t["title"] for t in data["topics"]]
        self.assertEqual(titles, ["Bug do save", "Dica de build"])

    def test_unknown_ordering_falls_back_to_default(self):
        data = self.client.get("/api/comunidade/?game=g&ordering=title").json()
        titles = [t["title"] for t in data["topics"]]
        self.assertEqual(titles, ["Dica de build", "Bug do save"])


class TopicModerationNotifyTests(TestCase):
    def setUp(self):
        call_command("setup_permissions")
        self.author = User.objects.create_user("au", password="pw")
        self.mod = User.objects.create_user("fm", password="pw")
        self.mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        self.topic = Topic.objects.create(game=self.game, author=self.author, title="T")
        self.api = APIClient()
        self.api.force_authenticate(self.mod)

    def test_hide_notifies_author(self):
        from notifications.models import Notification
        self.api.post(f"/api/v1/topics/{self.topic.id}/hide/")
        self.assertEqual(
            Notification.objects.filter(recipient=self.author, kind="topic_hidden").count(), 1
        )

    def test_lock_notifies_author(self):
        from notifications.models import Notification
        self.api.post(f"/api/v1/topics/{self.topic.id}/lock/")
        self.assertEqual(
            Notification.objects.filter(recipient=self.author, kind="topic_locked").count(), 1
        )

    def test_notification_url_includes_game_slug(self):
        from notifications.models import Notification
        self.api.post(f"/api/v1/topics/{self.topic.id}/hide/")
        n = Notification.objects.get(recipient=self.author, kind="topic_hidden")
        self.assertIn(self.game.slug, n.url)

    def test_author_moderating_own_topic_does_not_self_notify(self):
        from notifications.models import Notification
        self.author.groups.add(Group.objects.get(name="Moderador de Fórum"))
        api = APIClient()
        api.force_authenticate(self.author)
        api.post(f"/api/v1/topics/{self.topic.id}/hide/")
        self.assertEqual(Notification.objects.filter(recipient=self.author).count(), 0)


class ThreadEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("t", password="pw")
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        self.topic = Topic.objects.create(game=self.game, author=self.user, title="T", body="corpo")
        Reply.objects.create(topic=self.topic, author=self.user, body="r1")

    def test_thread_returns_topic_and_replies(self):
        self.client.force_login(self.user)
        data = self.client.get(f"/api/topico/{self.topic.id}/").json()
        self.assertEqual(data["topic"]["title"], "T")
        self.assertFalse(data["topic"]["is_locked"])
        self.assertEqual(len(data["replies"]), 1)

    def test_hidden_topic_404_for_non_moderator(self):
        self.topic.is_hidden = True
        self.topic.save()
        self.client.force_login(self.user)
        resp = self.client.get(f"/api/topico/{self.topic.id}/")
        self.assertEqual(resp.status_code, 404)

    def test_hidden_topic_visible_to_moderator(self):
        call_command("setup_permissions")
        mod = User.objects.create_user("modu", password="pw")
        mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        self.topic.is_hidden = True
        self.topic.save()
        self.client.force_login(mod)
        resp = self.client.get(f"/api/topico/{self.topic.id}/")
        self.assertEqual(resp.status_code, 200)

    def test_hidden_reply_filtered_for_non_moderator(self):
        Reply.objects.create(topic=self.topic, author=self.user, body="secret", is_hidden=True)
        self.client.force_login(self.user)
        data = self.client.get(f"/api/topico/{self.topic.id}/").json()
        bodies = [r["body"] for r in data["replies"]]
        self.assertNotIn("secret", bodies)

    def test_hidden_reply_visible_to_moderator(self):
        call_command("setup_permissions")
        mod = User.objects.create_user("modv", password="pw")
        mod.groups.add(Group.objects.get(name="Moderador de Fórum"))
        Reply.objects.create(topic=self.topic, author=self.user, body="secret", is_hidden=True)
        self.client.force_login(mod)
        data = self.client.get(f"/api/topico/{self.topic.id}/").json()
        bodies = [r["body"] for r in data["replies"]]
        self.assertIn("secret", bodies)


@override_settings(STORAGES=TEST_STORAGES)
class ThreadPageTests(TestCase):
    def test_thread_page_renders(self):
        u = User.objects.create_user("tp", password="pw")
        g = Game.objects.create(name="G", slug="g", bug_score=1)
        t = Topic.objects.create(game=g, author=u, title="T")
        self.client.force_login(u)
        self.assertEqual(self.client.get(f"/comunidade/topico/{t.id}/").status_code, 200)
