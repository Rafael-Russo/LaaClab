"""Tests for the alerts domain: the /api/alertas/ level+search filters and
the /alertas/ page-shell render."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from catalog.models import Game

from .models import Alert

User = get_user_model()

# Non-manifest static storage so the page-shell template renders in tests
# without requiring `collectstatic` (mirrors catalog.tests.TEST_STORAGES).
TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


class AlertsFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("af", password="pw")
        self.g1 = Game.objects.create(name="Alpha", slug="alpha", bug_score=90)
        self.g2 = Game.objects.create(name="Beta", slug="beta", bug_score=10)
        # Alert.level is a derived property (from `severity`), not a stored
        # field — see alerts/models.py PRESENTATION. severity="update" maps
        # to level="stable".
        Alert.objects.create(game=self.g1, severity=Alert.Severity.CRITICAL, text="crash")
        Alert.objects.create(game=self.g2, severity=Alert.Severity.UPDATE, text="update")
        self.client.force_login(self.user)

    def test_filter_by_level(self):
        data = self.client.get("/api/alertas/?level=critical").json()
        self.assertEqual([a["game"] for a in data["alerts"]], ["Alpha"])

    def test_search_by_game(self):
        data = self.client.get("/api/alertas/?q=beta").json()
        self.assertEqual([a["game"] for a in data["alerts"]], ["Beta"])

    def test_level_and_search_compose(self):
        # Matches g1 on both filters: composing narrows, it doesn't OR.
        data = self.client.get("/api/alertas/?level=critical&q=alpha").json()
        self.assertEqual([a["game"] for a in data["alerts"]], ["Alpha"])
        # g2 matches the search term but not the level -> excluded.
        data = self.client.get("/api/alertas/?level=critical&q=beta").json()
        self.assertEqual(data["alerts"], [])


@override_settings(STORAGES=TEST_STORAGES)
class AlertsScreenRendersTests(TestCase):
    """The /alertas/ page shell (search input + filter button + rail) still
    renders after wiring the search/filter/detail controls in alerts.js."""

    def test_alerts_page_renders(self):
        user = User.objects.create_user("alscreen", password="pw")
        self.client.force_login(user)
        self.assertEqual(self.client.get("/alertas/").status_code, 200)
