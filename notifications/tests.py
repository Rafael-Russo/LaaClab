from django.contrib.auth import get_user_model
from django.test import TestCase

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
