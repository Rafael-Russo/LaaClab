from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from alerts.models import Alert
from catalog.models import Game, LibraryEntry
from community.models import Reply, Topic
from notifications.models import Notification, PushSubscription
from notifications.services import notify

User = get_user_model()


class NotifyHelperTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", password="pw")
        self.b = User.objects.create_user("b", password="pw")

    def test_notify_creates_notification(self):
        n = notify(recipient=self.a, actor=self.b, kind="reply", text="oi", url="/x/")
        self.assertIsNotNone(n)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(n.recipient, self.a)
        self.assertFalse(n.is_read)

    def test_notify_skips_self(self):
        n = notify(recipient=self.a, actor=self.a, kind="reply", text="oi")
        self.assertIsNone(n)
        self.assertEqual(Notification.objects.count(), 0)


class ReplyNotificationTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user("author", password="pw")
        self.replier = User.objects.create_user("replier", password="pw")
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        self.topic = Topic.objects.create(game=self.game, author=self.author, title="T")

    def test_reply_notifies_topic_author(self):
        Reply.objects.create(topic=self.topic, author=self.replier, body="oi")
        n = Notification.objects.get(recipient=self.author)
        self.assertEqual(n.kind, "reply")
        self.assertIn(self.game.slug, n.url)

    def test_reply_by_author_does_not_self_notify(self):
        Reply.objects.create(topic=self.topic, author=self.author, body="meu")
        self.assertEqual(Notification.objects.filter(recipient=self.author).count(), 0)


class AlertNotificationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="pw")
        self.other = User.objects.create_user("other", password="pw")
        self.game = Game.objects.create(name="G", slug="g", bug_score=1)
        LibraryEntry.objects.create(user=self.owner, game=self.game)

    def test_alert_notifies_only_library_owners(self):
        Alert.objects.create(game=self.game, severity="critical", text="crash")
        self.assertEqual(Notification.objects.filter(recipient=self.owner).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.other).count(), 0)


class NotificationsApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="pw")
        self.other = User.objects.create_user("o", password="pw")
        for i in range(3):
            notify(recipient=self.user, actor=self.other, kind="reply", text=f"n{i}", url="/x/")
        notify(recipient=self.other, actor=self.user, kind="reply", text="alheia", url="/y/")

    def test_list_and_unread_count_scoped_to_user(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/notifications/").json()
        self.assertEqual(len(data["notifications"]), 3)
        self.assertEqual(data["unread_count"], 3)

    def test_mark_one_read(self):
        self.client.force_login(self.user)
        nid = Notification.objects.filter(recipient=self.user).first().id
        self.assertEqual(self.client.post(f"/api/notifications/{nid}/read/").status_code, 204)
        self.assertEqual(self.client.get("/api/notifications/").json()["unread_count"], 2)

    def test_mark_all_read(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.post("/api/notifications/read-all/").status_code, 204)
        self.assertEqual(self.client.get("/api/notifications/").json()["unread_count"], 0)

    def test_cannot_read_others_notification(self):
        self.client.force_login(self.user)
        alheia = Notification.objects.get(recipient=self.other)
        self.assertEqual(self.client.post(f"/api/notifications/{alheia.id}/read/").status_code, 404)

    def test_anonymous_blocked(self):
        self.assertEqual(self.client.get("/api/notifications/").status_code, 401)


class PushSubscriptionModelTests(TestCase):
    def test_unique_endpoint_per_row(self):
        u = User.objects.create_user("p", password="pw")
        PushSubscription.objects.create(user=u, endpoint="https://x/1", p256dh="a", auth="b")
        with self.assertRaises(IntegrityError):
            PushSubscription.objects.create(user=u, endpoint="https://x/1", p256dh="c", auth="d")


class PushEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("pe", password="pw")

    def test_vapid_key(self):
        self.client.force_login(self.user)
        self.assertIn("public_key", self.client.get("/api/push/vapid-key/").json())

    def test_subscribe_then_unsubscribe(self):
        self.client.force_login(self.user)
        body = {"endpoint": "https://x/1", "keys": {"p256dh": "a", "auth": "b"}}
        self.assertEqual(
            self.client.post(
                "/api/push/subscribe/", body, content_type="application/json"
            ).status_code,
            201,
        )
        self.assertEqual(PushSubscription.objects.filter(user=self.user).count(), 1)
        # idempotente
        self.client.post("/api/push/subscribe/", body, content_type="application/json")
        self.assertEqual(PushSubscription.objects.count(), 1)
        self.assertEqual(
            self.client.post(
                "/api/push/unsubscribe/", {"endpoint": "https://x/1"}, content_type="application/json"
            ).status_code,
            204,
        )
        self.assertEqual(PushSubscription.objects.count(), 0)

    def test_anon_blocked(self):
        self.assertEqual(self.client.get("/api/push/vapid-key/").status_code, 401)
