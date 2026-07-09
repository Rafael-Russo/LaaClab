from django.contrib.auth import get_user_model
from django.test import TestCase

from alerts.models import Alert
from catalog.models import Game, LibraryEntry
from community.models import Reply, Topic
from notifications.models import Notification
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
