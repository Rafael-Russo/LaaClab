"""Tests for the catalogue domain: Steam ingestion helpers, Celery ingest
tasks and the ``ingest``/``ingest_status`` management commands."""

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings


class IngestionHelperTests(TestCase):
    def test_parse_owners(self):
        from catalog.ingestion import parse_owners
        self.assertEqual(parse_owners("10,000,000 .. 20,000,000"), 10000000)
        self.assertEqual(parse_owners(""), 0)
        self.assertEqual(parse_owners("1.234"), 1234)

    def test_steamspy_candidates(self):
        from catalog.ingestion import steamspy_candidates
        payload = {
            "730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"},
            "570": {"appid": 570, "name": "Dota 2", "owners": "100,000,000 .. 200,000,000"},
        }
        items = steamspy_candidates(payload)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["appid"], 730)
        self.assertEqual(items[0]["owners"], 50000000)

    def test_game_defaults_from_appdetails_maps_fields(self):
        from catalog.ingestion import game_defaults_from_appdetails
        data = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG.", "detailed_description": "<h1>Sobre</h1> jogo",
            "header_image": "https://x/y.jpg",
            "release_date": {"date": "10 dez. 2020"},
            "developers": ["CD PROJEKT RED"], "publishers": ["CD PROJEKT RED"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        d = game_defaults_from_appdetails(1091500, data)
        self.assertEqual(d["name"], "Cyberpunk 2077")
        self.assertEqual(d["metacritic"], 86)
        self.assertEqual(d["genres_names"], ["RPG"])
        self.assertNotIn("<h1>", d["about"])
        self.assertGreaterEqual(d["bug_score"], 10)

    def test_game_defaults_returns_none_for_non_game(self):
        from catalog.ingestion import game_defaults_from_appdetails
        self.assertIsNone(game_defaults_from_appdetails(1, {"type": "dlc", "name": "X"}))


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class IngestTaskTests(TestCase):
    def test_ingest_game_creates_game_and_marks_done(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=1091500, name="Cyberpunk 2077")
        appdata = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG", "detailed_description": "jogo",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["CDPR"], "publishers": ["CDPR"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value="covers/cyberpunk-2077.jpg"):
            result = tasks.ingest_game(1091500)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=1091500)
        self.assertEqual(game.metacritic, 86)
        self.assertEqual(game.cover_file.name, "covers/cyberpunk-2077.jpg")
        self.assertEqual(game.genres.count(), 1)
        self.assertEqual(IngestCandidate.objects.get(appid=1091500).status, "done")

    def test_ingest_game_marks_failed_on_missing_data(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=999, name="Ghost")
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=None):
            result = tasks.ingest_game(999)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=999)
        self.assertEqual(c.status, "failed")
        self.assertEqual(c.attempts, 1)

    def test_refresh_applist_creates_candidates(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        page = {"730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"}}
        with mock.patch("catalog.tasks.fetch_steamspy_page", return_value=page):
            n = tasks.refresh_applist(pages=1)
        self.assertEqual(n, 1)
        self.assertTrue(IngestCandidate.objects.filter(appid=730).exists())

    def test_enqueue_pending_only_non_done(self):
        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="pending")
        IngestCandidate.objects.create(appid=2, status="done")
        with mock.patch("catalog.tasks.ingest_game.delay") as delayed:
            n = tasks.enqueue_pending()
        self.assertEqual(n, 1)
        delayed.assert_called_once_with(1)

    def test_ingest_game_slug_unique_for_duplicate_names(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=111, name="Same Name")
        IngestCandidate.objects.create(appid=222, name="Same Name")
        appdata = {
            "type": "game", "name": "Same Name",
            "short_description": "d", "detailed_description": "d",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["X"], "publishers": ["X"],
            "metacritic": {"score": 80}, "achievements": {"total": 1},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value=""):
            r1 = tasks.ingest_game(111)
            r2 = tasks.ingest_game(222)
        self.assertEqual(r1, "done")
        self.assertEqual(r2, "done")
        games = Game.objects.filter(name="Same Name")
        self.assertEqual(games.count(), 2)
        slugs = set(games.values_list("slug", flat=True))
        self.assertEqual(len(slugs), 2)
        statuses = set(
            IngestCandidate.objects.filter(appid__in=[111, 222]).values_list(
                "status", flat=True
            )
        )
        self.assertEqual(statuses, {"done"})

    def test_ingest_game_empty_slug_name(self):
        from catalog import tasks
        from catalog.models import Game, IngestCandidate
        IngestCandidate.objects.create(appid=333, name="日本語ゲーム")
        appdata = {
            "type": "game", "name": "日本語ゲーム",
            "short_description": "d", "detailed_description": "d",
            "header_image": "", "release_date": {"date": "2020"},
            "developers": [], "publishers": [],
            "metacritic": None, "achievements": {"total": 0},
            "genres": [],
        }
        with mock.patch("catalog.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("catalog.tasks.download_cover", return_value=""):
            result = tasks.ingest_game(333)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=333)
        self.assertTrue(game.slug)
        self.assertEqual(IngestCandidate.objects.get(appid=333).status, "done")

    def test_ingest_game_marks_failed_on_network_error(self):
        import requests

        from catalog import tasks
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=444, name="Boom")
        with mock.patch(
            "catalog.tasks.fetch_appdetails", side_effect=requests.RequestException("boom")
        ):
            result = tasks.ingest_game(444)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=444)
        self.assertEqual(c.status, "failed")
        self.assertIn("boom", c.last_error)
        self.assertEqual(c.attempts, 1)


class IngestCommandTests(TestCase):
    def test_ingest_status_counts(self):
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="done")
        IngestCandidate.objects.create(appid=2, status="pending")
        out = StringIO()
        call_command("ingest_status", stdout=out)
        text = out.getvalue()
        self.assertIn("done=1", text)
        self.assertIn("pending=1", text)

    def test_ingest_sync_resume_processes_pending(self):
        from catalog.models import IngestCandidate
        IngestCandidate.objects.create(appid=730, name="CS2", status="pending")
        with mock.patch("catalog.tasks.ingest_game") as ig:
            ig.return_value = "done"
            call_command("ingest", "--resume", "--sync", stdout=StringIO())
        ig.assert_called_once_with(730)
