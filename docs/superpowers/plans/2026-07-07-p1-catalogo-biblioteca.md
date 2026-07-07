# P1 — Catálogo em massa + biblioteca por usuário — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Popular o catálogo com milhares de jogos reais da Steam via Celery (resumível), com capas self-hosted, e tornar "Meus Jogos" estritamente do usuário com uma tela "Explorar" para descoberta/adição.

**Architecture:** Ingestão assíncrona (Celery + Redis): SteamSpy dá o ranking (appids + owners), a Steam appdetails enriquece, e as capas são baixadas para `media/`. Um modelo `IngestCandidate` torna o processo resumível. As telas consomem a API DRF existente (`/api/v1/games/` paginado + `/api/v1/library/`).

**Tech Stack:** Django 5.2, DRF, Celery, Redis, Pillow, MySQL/SQLite, requests.

## Global Constraints

- Python 3.12; venv em `.venv` (no Windows: `.venv/Scripts/python.exe`).
- Rodar testes: `python manage.py test web` (usa SQLite de teste; `testserver` já em ALLOWED_HOSTS sob o test runner).
- Lint: `ruff check .` deve passar (config em `pyproject.toml`, `line-length=100`, ignora `E501`).
- Testes **offline**: nenhuma chamada de rede real — `requests` sempre mockado; Celery em modo eager nos testes.
- Commits em **Conventional Commits**, mensagens enxutas, incrementais. Terminar cada mensagem com:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- Não commitar fixture gigante: a massa vai só para o banco; o seed pequeno (`web/fixtures/games_seed.json`, ~26) permanece para CI/`seed`.
- `bug_score` continua **provisório** (função determinística) até P3 — não é objetivo do P1 torná-lo real.

## File Structure

**Criar:**
- `web/ingestion.py` — helpers puros + fetch de rede (SteamSpy/appdetails) + download de capa.
- `web/tasks.py` — tasks Celery (`refresh_applist`, `enqueue_pending`, `ingest_game`).
- `config/celery.py` — app Celery.
- `web/management/commands/ingest.py` — comando orquestrador.
- `web/management/commands/ingest_status.py` — contagem por status.
- `web/templates/web/explore.html` — tela Explorar.
- `web/static/web/js/explore.js` — JS da tela Explorar.

**Modificar:**
- `requirements.txt` — `celery`, `redis`, `Pillow`.
- `config/settings.py` — Celery + MEDIA.
- `config/__init__.py` — importar o app Celery.
- `web/models.py` — `Game.cover_file`/`popularity` + `IngestCandidate`.
- `web/management/commands/fetch_steam.py` — usar `provisional_bug_score` de `ingestion`.
- `web/serializers.py` — `GameSerializer` com `cover_file`/`popularity`.
- `web/rest.py` — `GameViewSet` ordena por `popularity`.
- `web/services.py` — remover fallbacks; `game_card` inclui `cover_file`.
- `web/views.py`, `web/urls.py` — view/rota da tela Explorar.
- `web/templates/web/base.html` — link "Explorar" na sidebar + `<img>` no helper.
- `web/static/web/js/app.js` — helper de capa com `<img>` + fallback.
- `web/static/web/js/library.js` — estado vazio + remover/favoritar.
- `web/static/web/js/community.js` — remover `TOPIC_COUNTS` sintético.
- `docker-compose.yml`, `deploy/nginx.conf` — redis/worker/beat + volume media + `/media/`.
- `web/tests.py` — novos testes.
- `docs/CONTROLE-EXECUCAO.md` — status.

---

### Task 1: Dependências + app Celery + settings (Celery/MEDIA)

**Files:**
- Modify: `requirements.txt`
- Create: `config/celery.py`
- Modify: `config/__init__.py`
- Modify: `config/settings.py`
- Test: `web/tests.py`

**Interfaces:**
- Produces: `config.celery.app` (Celery instance); `settings.MEDIA_ROOT`/`MEDIA_URL`; `settings.CELERY_BROKER_URL`.

- [ ] **Step 1: Add dependencies**

Edit `requirements.txt`, adicionar após a linha `requests>=2.32,<3`:

```
celery>=5.4,<6
redis>=5.0,<6
Pillow>=10.4,<12
```

- [ ] **Step 2: Install**

Run: `./.venv/Scripts/python.exe -m pip install -r requirements.txt`
Expected: instala celery, redis, Pillow (e kombu/billiard/vine).

- [ ] **Step 3: Create the Celery app**

Create `config/celery.py`:

```python
"""Celery application for LaaCLab.

Reads its config from Django settings (keys prefixed with ``CELERY_``) and
auto-discovers tasks in the installed apps (``web/tasks.py``).
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("laaclab")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

- [ ] **Step 4: Wire the app on Django startup**

Replace the contents of `config/__init__.py` with:

```python
from .celery import app as celery_app

__all__ = ("celery_app",)
```

- [ ] **Step 5: Add Celery + MEDIA settings**

In `config/settings.py`, after the `REST_FRAMEWORK = { ... }` block, add:

```python
# --- Celery -----------------------------------------------------------------
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", False)
CELERY_TASK_EAGER_PROPAGATES = True
```

The `MEDIA_URL`/`MEDIA_ROOT` already exist in settings (Static & media section). No change needed there.

- [ ] **Step 6: Write the failing test**

In `web/tests.py`, add at the end:

```python
class InfraTests(TestCase):
    def test_celery_app_importable(self):
        from config.celery import app
        self.assertEqual(app.main, "laaclab")

    def test_media_settings_present(self):
        from django.conf import settings
        self.assertTrue(str(settings.MEDIA_ROOT).endswith("media"))
        self.assertEqual(settings.MEDIA_URL, "media/")
```

- [ ] **Step 7: Run tests**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.InfraTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 8: Commit**

```bash
git add requirements.txt config/celery.py config/__init__.py config/settings.py web/tests.py
git commit -m "build(celery): add celery/redis/pillow and celery app"
```

---

### Task 2: Modelo — `Game.cover_file`/`popularity` + `IngestCandidate`

**Files:**
- Modify: `web/models.py`
- Create: `web/migrations/0002_ingest_and_cover.py` (via makemigrations)
- Test: `web/tests.py`

**Interfaces:**
- Produces: `Game.cover_file` (ImageField), `Game.popularity` (int); `IngestCandidate` with `appid`, `name`, `owners`, `rank`, `status` (`pending|fetching|done|failed`), `attempts`, `last_error`, `updated_at`, and `IngestCandidate.Status` choices.

- [ ] **Step 1: Add fields to `Game`**

In `web/models.py`, inside `class Game`, add after the `cover = models.JSONField(...)` line:

```python
    cover_file = models.ImageField(upload_to="covers/", blank=True)
    popularity = models.PositiveIntegerField(default=0)
```

- [ ] **Step 2: Add the `IngestCandidate` model**

At the end of `web/models.py`, add:

```python
class IngestCandidate(models.Model):
    """A Steam app queued for ingestion; makes the pipeline resumable."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        FETCHING = "fetching", "Buscando"
        DONE = "done", "Concluído"
        FAILED = "failed", "Falhou"

    appid = models.PositiveIntegerField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    owners = models.PositiveIntegerField(default=0)
    rank = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["rank", "appid"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.appid} ({self.status})"
```

- [ ] **Step 3: Make migrations**

Run: `./.venv/Scripts/python.exe manage.py makemigrations web`
Expected: cria `web/migrations/0002_*.py` com os 2 campos de Game + model IngestCandidate.

- [ ] **Step 4: Write the failing test**

In `web/tests.py`, add:

```python
class IngestCandidateModelTests(TestCase):
    def test_defaults(self):
        from web.models import IngestCandidate
        c = IngestCandidate.objects.create(appid=730, name="CS2")
        self.assertEqual(c.status, "pending")
        self.assertEqual(c.attempts, 0)
        self.assertEqual(c.owners, 0)

    def test_game_new_fields(self):
        from web.models import Game
        g = Game.objects.create(name="X", bug_score=10, popularity=5000)
        self.assertEqual(g.popularity, 5000)
        self.assertFalse(g.cover_file)
```

- [ ] **Step 5: Run tests**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestCandidateModelTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add web/models.py web/migrations/0002_*.py web/tests.py
git commit -m "feat(catalog): add game cover_file/popularity and IngestCandidate"
```

---

### Task 3: Helpers puros de ingestão (`web/ingestion.py`)

**Files:**
- Create: `web/ingestion.py`
- Modify: `web/management/commands/fetch_steam.py`
- Test: `web/tests.py`

**Interfaces:**
- Produces:
  - `parse_owners(owners: str) -> int`
  - `provisional_bug_score(appid: int, name: str) -> int`
  - `steamspy_candidates(payload: dict) -> list[dict]` → itens `{"appid": int, "name": str, "owners": int}`
  - `game_defaults_from_appdetails(appid: int, data: dict) -> dict | None`

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, add:

```python
class IngestionHelperTests(TestCase):
    def test_parse_owners(self):
        from web.ingestion import parse_owners
        self.assertEqual(parse_owners("10,000,000 .. 20,000,000"), 10000000)
        self.assertEqual(parse_owners(""), 0)
        self.assertEqual(parse_owners("1.234"), 1234)

    def test_steamspy_candidates(self):
        from web.ingestion import steamspy_candidates
        payload = {
            "730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"},
            "570": {"appid": 570, "name": "Dota 2", "owners": "100,000,000 .. 200,000,000"},
        }
        items = steamspy_candidates(payload)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["appid"], 730)
        self.assertEqual(items[0]["owners"], 50000000)

    def test_game_defaults_from_appdetails_maps_fields(self):
        from web.ingestion import game_defaults_from_appdetails
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
        from web.ingestion import game_defaults_from_appdetails
        self.assertIsNone(game_defaults_from_appdetails(1, {"type": "dlc", "name": "X"}))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestionHelperTests -v2`
Expected: FAIL (`ModuleNotFoundError: web.ingestion`).

- [ ] **Step 3: Create `web/ingestion.py`**

```python
"""Steam ingestion helpers.

Pure mappers (testable without network) plus thin network fetchers for the
SteamSpy ranking and the Steam store appdetails endpoint. Celery tasks in
``web/tasks.py`` orchestrate these.
"""

import html
import re
from pathlib import Path

import requests

STEAMSPY_URL = "https://steamspy.com/api.php"
STORE_URL = "https://store.steampowered.com/api/appdetails"
COVER_DIR = "covers"

_TAG_RE = re.compile(r"<[^>]+>")
_PALETTE = [
    ["#3a4a3f", "#1b241f"], ["#2b6cb0", "#1a365d"], ["#b7950b", "#4a3f0b"],
    ["#2f7d5b", "#14352a"], ["#bd3b4a", "#2b3a3f"], ["#a1421f", "#3a1a10"],
    ["#c07f2a", "#241608"], ["#3f4a55", "#161c22"], ["#8a3a2a", "#2a140d"],
    ["#7a2a2a", "#1c0d0d"], ["#4a3f6b", "#1c1830"], ["#2a6b6b", "#0f2626"],
]


def parse_owners(owners: str) -> int:
    """Lower bound of a SteamSpy owners range ('10,000,000 .. 20,000,000')."""
    if not owners:
        return 0
    first = owners.split("..")[0]
    digits = re.sub(r"[^0-9]", "", first)
    return int(digits) if digits else 0


def provisional_bug_score(appid: int, name: str) -> int:
    """Stable placeholder score in [10, 89] until P3 computes a real one."""
    base = appid or sum(ord(c) for c in name)
    return 10 + (base * 73 + 17) % 80


def _strip_html(raw: str, limit: int) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit].rstrip()


def steamspy_candidates(payload: dict) -> list[dict]:
    """Map a SteamSpy 'all' page payload to candidate dicts."""
    out = []
    for entry in payload.values():
        appid = entry.get("appid")
        if not appid:
            continue
        out.append({
            "appid": int(appid),
            "name": entry.get("name", "") or "",
            "owners": parse_owners(entry.get("owners", "")),
        })
    return out


def game_defaults_from_appdetails(appid: int, data: dict) -> dict | None:
    """Map a Steam appdetails 'data' object to Game field defaults.

    Returns None when the app is not a playable game or has no name. The
    returned dict includes a ``genres_names`` list handled by the caller.
    """
    if data.get("type") != "game":
        return None
    name = (data.get("name") or "").strip()
    if not name:
        return None
    palette = _PALETTE[appid % len(_PALETTE)]
    return {
        "name": name,
        "short_description": _strip_html(data.get("short_description", ""), 300),
        "about": _strip_html(data.get("detailed_description", ""), 700),
        "cover_image": data.get("header_image", "") or "",
        "cover": palette,
        "bug_score": provisional_bug_score(appid, name),
        "release_date": (data.get("release_date") or {}).get("date", ""),
        "developer": ", ".join(data.get("developers", []) or [])[:200],
        "publisher": ", ".join(data.get("publishers", []) or [])[:200],
        "metacritic": (data.get("metacritic") or {}).get("score"),
        "achievements": (data.get("achievements") or {}).get("total", 0),
        "genres_names": [g["description"] for g in data.get("genres", []) or []],
    }


def fetch_steamspy_page(page: int, session: requests.Session | None = None) -> dict:
    """Fetch one SteamSpy 'all' page (network)."""
    s = session or requests
    resp = s.get(STEAMSPY_URL, params={"request": "all", "page": page}, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_appdetails(appid: int, session: requests.Session | None = None) -> dict | None:
    """Fetch one Steam appdetails 'data' object (network) or None."""
    s = session or requests
    resp = s.get(
        STORE_URL, params={"appids": appid, "l": "portuguese", "cc": "br"}, timeout=20
    )
    resp.raise_for_status()
    payload = resp.json().get(str(appid), {})
    return payload["data"] if payload.get("success") else None


def download_cover(url: str, slug: str, media_root, session: requests.Session | None = None) -> str:
    """Download a cover image to MEDIA_ROOT/covers/<slug>.jpg.

    Returns the media-relative path ('covers/<slug>.jpg') or '' on failure.
    """
    if not url:
        return ""
    s = session or requests
    try:
        resp = s.get(url, timeout=20)
        resp.raise_for_status()
        rel = f"{COVER_DIR}/{slug}.jpg"
        dest = Path(media_root) / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(resp.content)
        return rel
    except (requests.RequestException, OSError):
        return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestionHelperTests -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: DRY — reuse `provisional_bug_score` in `fetch_steam`**

In `web/management/commands/fetch_steam.py`, replace the local `_bug_score` function definition with an import. At the top imports add:

```python
from web.ingestion import provisional_bug_score
```

Delete the `def _bug_score(appid, name): ...` block and replace its call sites `_bug_score(` with `provisional_bug_score(`.

- [ ] **Step 6: Verify fetch_steam still imports**

Run: `./.venv/Scripts/python.exe -c "import django,os; os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings'); django.setup(); import web.management.commands.fetch_steam"`
Expected: sem erro.

- [ ] **Step 7: Commit**

```bash
git add web/ingestion.py web/management/commands/fetch_steam.py web/tests.py
git commit -m "feat(catalog): add steam ingestion helpers"
```

---

### Task 4: Celery tasks de ingestão (`web/tasks.py`)

**Files:**
- Create: `web/tasks.py`
- Test: `web/tests.py`

**Interfaces:**
- Consumes: `web.ingestion.fetch_steamspy_page/fetch_appdetails/steamspy_candidates/game_defaults_from_appdetails/download_cover`; models `Game`, `Genre`, `IngestCandidate`.
- Produces:
  - `refresh_applist(pages: int = 1) -> int`
  - `enqueue_pending(limit: int | None = None) -> int`
  - `ingest_game(appid: int) -> str` (retorna `"done"`/`"failed"`/`"skipped"`)

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, add:

```python
from unittest import mock
from django.test import override_settings


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class IngestTaskTests(TestCase):
    def test_ingest_game_creates_game_and_marks_done(self):
        from web.models import Game, IngestCandidate
        from web import tasks
        IngestCandidate.objects.create(appid=1091500, name="Cyberpunk 2077")
        appdata = {
            "type": "game", "name": "Cyberpunk 2077",
            "short_description": "RPG", "detailed_description": "jogo",
            "header_image": "https://x/y.jpg", "release_date": {"date": "2020"},
            "developers": ["CDPR"], "publishers": ["CDPR"],
            "metacritic": {"score": 86}, "achievements": {"total": 44},
            "genres": [{"description": "RPG"}],
        }
        with mock.patch("web.tasks.fetch_appdetails", return_value=appdata), \
             mock.patch("web.tasks.download_cover", return_value="covers/cyberpunk-2077.jpg"):
            result = tasks.ingest_game(1091500)
        self.assertEqual(result, "done")
        game = Game.objects.get(steam_appid=1091500)
        self.assertEqual(game.metacritic, 86)
        self.assertEqual(game.cover_file.name, "covers/cyberpunk-2077.jpg")
        self.assertEqual(game.genres.count(), 1)
        self.assertEqual(IngestCandidate.objects.get(appid=1091500).status, "done")

    def test_ingest_game_marks_failed_on_missing_data(self):
        from web.models import IngestCandidate
        from web import tasks
        IngestCandidate.objects.create(appid=999, name="Ghost")
        with mock.patch("web.tasks.fetch_appdetails", return_value=None):
            result = tasks.ingest_game(999)
        self.assertEqual(result, "failed")
        c = IngestCandidate.objects.get(appid=999)
        self.assertEqual(c.status, "failed")
        self.assertEqual(c.attempts, 1)

    def test_refresh_applist_creates_candidates(self):
        from web.models import IngestCandidate
        from web import tasks
        page = {"730": {"appid": 730, "name": "CS2", "owners": "50,000,000 .. 100,000,000"}}
        with mock.patch("web.tasks.fetch_steamspy_page", return_value=page):
            n = tasks.refresh_applist(pages=1)
        self.assertEqual(n, 1)
        self.assertTrue(IngestCandidate.objects.filter(appid=730).exists())

    def test_enqueue_pending_only_non_done(self):
        from web.models import IngestCandidate
        from web import tasks
        IngestCandidate.objects.create(appid=1, status="pending")
        IngestCandidate.objects.create(appid=2, status="done")
        with mock.patch("web.tasks.ingest_game.delay") as delayed:
            n = tasks.enqueue_pending()
        self.assertEqual(n, 1)
        delayed.assert_called_once_with(1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestTaskTests -v2`
Expected: FAIL (`ModuleNotFoundError: web.tasks`).

- [ ] **Step 3: Create `web/tasks.py`**

```python
"""Celery tasks for bulk catalogue ingestion (see docs/runbooks/popular-catalogo.md)."""

from celery import shared_task
from django.conf import settings
from django.utils.text import slugify

from .ingestion import (
    download_cover,
    fetch_appdetails,
    fetch_steamspy_page,
    game_defaults_from_appdetails,
    steamspy_candidates,
)
from .models import Game, Genre, IngestCandidate


@shared_task
def refresh_applist(pages: int = 1) -> int:
    """Pull ranked appids from SteamSpy into IngestCandidate. Returns upserts."""
    count = 0
    for page in range(pages):
        payload = fetch_steamspy_page(page)
        for rank, item in enumerate(steamspy_candidates(payload)):
            IngestCandidate.objects.update_or_create(
                appid=item["appid"],
                defaults={
                    "name": item["name"],
                    "owners": item["owners"],
                    "rank": page * 1000 + rank,
                },
            )
            count += 1
    return count


@shared_task
def enqueue_pending(limit: int | None = None) -> int:
    """Dispatch ingest_game for every candidate not yet done. Returns count."""
    qs = IngestCandidate.objects.exclude(status=IngestCandidate.Status.DONE)
    if limit:
        qs = qs[:limit]
    count = 0
    for candidate in qs:
        ingest_game.delay(candidate.appid)
        count += 1
    return count


@shared_task(bind=True, rate_limit="40/m", max_retries=3, default_retry_delay=30)
def ingest_game(self, appid: int) -> str:
    """Fetch appdetails, upsert the Game, download its cover. Idempotent."""
    candidate, _ = IngestCandidate.objects.get_or_create(appid=appid)
    candidate.status = IngestCandidate.Status.FETCHING
    candidate.attempts += 1
    candidate.save(update_fields=["status", "attempts", "updated_at"])

    data = fetch_appdetails(appid)
    defaults = game_defaults_from_appdetails(appid, data) if data else None
    if not defaults:
        candidate.status = IngestCandidate.Status.FAILED
        candidate.last_error = "sem dados de jogo (appdetails)"
        candidate.save(update_fields=["status", "last_error", "updated_at"])
        return "failed"

    genre_names = defaults.pop("genres_names", [])
    slug = slugify(defaults["name"])[:140]
    defaults["popularity"] = candidate.owners
    game, _ = Game.objects.update_or_create(steam_appid=appid, defaults={**defaults, "slug": slug})

    if game.cover_image:
        rel = download_cover(game.cover_image, game.slug, settings.MEDIA_ROOT)
        if rel:
            game.cover_file.name = rel
            game.save(update_fields=["cover_file"])

    if genre_names:
        genres = [
            Genre.objects.get_or_create(slug=slugify(n), defaults={"name": n})[0]
            for n in genre_names
        ]
        game.genres.set(genres)

    candidate.status = IngestCandidate.Status.DONE
    candidate.last_error = ""
    candidate.save(update_fields=["status", "last_error", "updated_at"])
    return "done"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestTaskTests -v2`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add web/tasks.py web/tests.py
git commit -m "feat(catalog): add celery ingestion tasks"
```

---

### Task 5: Comandos `ingest` e `ingest_status`

**Files:**
- Create: `web/management/commands/ingest.py`
- Create: `web/management/commands/ingest_status.py`
- Test: `web/tests.py`

**Interfaces:**
- Consumes: `web.tasks.refresh_applist/enqueue_pending/ingest_game`.
- Produces: comandos `ingest` (`--pages`, `--limit`, `--resume`, `--sync`) e `ingest_status`.

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, add:

```python
from io import StringIO
from django.core.management import call_command


class IngestCommandTests(TestCase):
    def test_ingest_status_counts(self):
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=1, status="done")
        IngestCandidate.objects.create(appid=2, status="pending")
        out = StringIO()
        call_command("ingest_status", stdout=out)
        text = out.getvalue()
        self.assertIn("done=1", text)
        self.assertIn("pending=1", text)

    def test_ingest_sync_resume_processes_pending(self):
        from web.models import IngestCandidate
        IngestCandidate.objects.create(appid=730, name="CS2", status="pending")
        with mock.patch("web.tasks.ingest_game") as ig:
            ig.return_value = "done"
            call_command("ingest", "--resume", "--sync", stdout=StringIO())
        ig.assert_called_once_with(730)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestCommandTests -v2`
Expected: FAIL (`Unknown command: 'ingest_status'`).

- [ ] **Step 3: Create `web/management/commands/ingest_status.py`**

```python
"""Print IngestCandidate counts per status."""

from django.core.management.base import BaseCommand

from web.models import IngestCandidate


class Command(BaseCommand):
    help = "Show catalogue ingestion progress (counts per status)."

    def handle(self, *args, **options):
        parts = []
        for status, _ in IngestCandidate.Status.choices:
            parts.append(f"{status}={IngestCandidate.objects.filter(status=status).count()}")
        self.stdout.write(" ".join(parts))
```

- [ ] **Step 4: Create `web/management/commands/ingest.py`**

```python
"""Kick off (or resume) the bulk catalogue ingestion.

    python manage.py ingest --pages 5           # refresh ranking + enqueue
    python manage.py ingest --resume            # only enqueue pending/failed
    python manage.py ingest --pages 1 --sync    # run inline (no worker)
"""

from django.core.management.base import BaseCommand

from web import tasks
from web.models import IngestCandidate


class Command(BaseCommand):
    help = "Populate the catalogue from Steam via Celery (resumable)."

    def add_arguments(self, parser):
        parser.add_argument("--pages", type=int, default=1,
                            help="SteamSpy pages to pull (~1000 games each).")
        parser.add_argument("--limit", type=int, default=None,
                            help="Max candidates to enqueue this run.")
        parser.add_argument("--resume", action="store_true",
                            help="Skip the ranking refresh; only enqueue pending/failed.")
        parser.add_argument("--sync", action="store_true",
                            help="Run inline without a worker (small/testing).")

    def handle(self, *args, **options):
        if not options["resume"]:
            n = tasks.refresh_applist(pages=options["pages"])
            self.stdout.write(f"candidatos atualizados: {n}")

        if options["sync"]:
            qs = IngestCandidate.objects.exclude(status=IngestCandidate.Status.DONE)
            if options["limit"]:
                qs = qs[: options["limit"]]
            for candidate in list(qs):
                tasks.ingest_game(candidate.appid)
            self.stdout.write("ingestão síncrona concluída")
        else:
            n = tasks.enqueue_pending(limit=options["limit"])
            self.stdout.write(f"tarefas enfileiradas: {n}")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.IngestCommandTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add web/management/commands/ingest.py web/management/commands/ingest_status.py web/tests.py
git commit -m "feat(catalog): add ingest and ingest_status commands"
```

---

### Task 6: Serializer/API do catálogo (Explorar) — `cover_file`, `popularity`, ordenação

**Files:**
- Modify: `web/serializers.py`
- Modify: `web/rest.py:34-40` (GameViewSet)
- Test: `web/tests.py`

**Interfaces:**
- Produces: `GameSerializer` inclui `cover_file` (URL) e `popularity`; `GameViewSet` aceita `ordering=popularity`.

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, extend the CRUD tests — add a new class:

```python
from rest_framework.test import APIClient


class CatalogApiTests(TestCase):
    def setUp(self):
        from web.models import Game
        self.user = User.objects.create_user("cat", password="pw")
        Game.objects.create(name="Alpha", bug_score=10, popularity=100)
        Game.objects.create(name="Beta", bug_score=20, popularity=900)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_serializer_exposes_cover_file_and_popularity(self):
        r = self.client.get("/api/v1/games/")
        row = r.json()["results"][0]
        self.assertIn("cover_file", row)
        self.assertIn("popularity", row)

    def test_order_by_popularity_desc(self):
        r = self.client.get("/api/v1/games/?ordering=-popularity")
        names = [g["name"] for g in r.json()["results"]]
        self.assertEqual(names[0], "Beta")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.CatalogApiTests -v2`
Expected: FAIL (`cover_file`/`popularity` ausentes ou ordenação inválida).

- [ ] **Step 3: Update `GameSerializer`**

In `web/serializers.py`, in `class GameSerializer.Meta.fields`, add `"cover_file"` and `"popularity"` to the list (after `"cover"`). No other change needed — `ImageField` serializes to a URL/None automatically.

- [ ] **Step 4: Update `GameViewSet` ordering**

In `web/rest.py`, in `class GameViewSet`, change the `ordering_fields` line to:

```python
    ordering_fields = ["bug_score", "name", "metacritic", "popularity"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.CatalogApiTests -v2`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add web/serializers.py web/rest.py web/tests.py
git commit -m "feat(api): expose cover_file/popularity and order games by popularity"
```

---

### Task 7: Biblioteca por usuário — remover fallbacks + `game_card` com capa

**Files:**
- Modify: `web/services.py`
- Test: `web/tests.py`

**Interfaces:**
- Produces: `services.user_library_cards(user)` e `user_favorite_cards(user)` retornam só dados do usuário (vazio se não houver); `game_card` inclui `cover_file` (URL ou "").

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, add:

```python
class LibraryScopeTests(TestCase):
    def setUp(self):
        from web.models import Game
        self.user = User.objects.create_user("lib", password="pw")
        self.game = Game.objects.create(name="Solo", bug_score=10)

    def test_library_empty_when_user_has_none(self):
        from web import services
        self.assertEqual(services.user_library_cards(self.user), [])
        self.assertEqual(services.user_favorite_cards(self.user), [])

    def test_biblioteca_endpoint_empty_for_new_user(self):
        self.client.force_login(self.user)
        data = self.client.get("/api/biblioteca/").json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["games"], [])

    def test_game_card_includes_cover_file_key(self):
        from web import services
        card = services.game_card(self.game)
        self.assertIn("cover_file", card)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.LibraryScopeTests -v2`
Expected: FAIL (fallback devolve o catálogo; `cover_file` ausente).

- [ ] **Step 3: Update `services.py`**

In `web/services.py`, replace `user_library_cards` and `user_favorite_cards` with:

```python
def user_library_cards(user) -> list[dict]:
    """The user's library (empty when they have none)."""
    entries = list(LibraryEntry.objects.filter(user=user).select_related("game"))
    return [game_card(e.game, e.favorite) for e in entries]


def user_favorite_cards(user) -> list[dict]:
    """The user's favourites (empty when they have none)."""
    entries = list(
        LibraryEntry.objects.filter(user=user, favorite=True).select_related("game")
    )
    return [game_card(e.game, True) for e in entries]
```

And in `game_card`, add a `cover_file` key. Replace the `return {` block with:

```python
    return {
        "slug": game.slug,
        "name": game.name,
        "score": game.bug_score,
        "initials": game.initials,
        "cover": game.cover or _DEFAULT_COVER,
        "cover_image": game.cover_image,
        "cover_file": game.cover_file.url if game.cover_file else "",
        "favorite": favorite,
        "status": game.status,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.LibraryScopeTests -v2`
Expected: PASS (3 tests).

- [ ] **Step 5: Adjust the existing favourites-fallback expectation**

Run the whole suite: `./.venv/Scripts/python.exe manage.py test web -v1`
Expected: PASS. If any prior test assumed the library fallback (it should not), update it to seed a `LibraryEntry` explicitly.

- [ ] **Step 6: Commit**

```bash
git add web/services.py web/tests.py
git commit -m "refactor(catalog): scope library strictly to the user"
```

---

### Task 8: Front — helper de capa com `<img>` + fallback (`app.js`)

**Files:**
- Modify: `web/static/web/js/app.js`
- Test: verificação por `node --check` + validação manual.

**Interfaces:**
- Produces: `LaaC.cover(game, cls)` renderiza `<img>` quando há `cover_file`/`cover_image`, caindo para o gradiente com iniciais.

- [ ] **Step 1: Update the cover helper**

In `web/static/web/js/app.js`, replace the `cover(game, cls = "")` method with:

```javascript
  /* Build a cover tile: real image when available, else gradient + initials. */
  cover(game, cls = "") {
    const src = game.cover_file || game.cover_image || "";
    const tile = LaaC.el("div", { class: "cover " + cls, style: LaaC.coverStyle(game.cover) },
      game.initials || game.name || "");
    if (src) {
      const img = LaaC.el("img", {
        src, alt: game.name || "", loading: "lazy",
        style: "width:100%;height:100%;object-fit:cover;position:absolute;inset:0",
        onerror: () => img.remove(),
      });
      tile.style.position = "relative";
      tile.style.overflow = "hidden";
      tile.append(img);
    }
    return tile;
  },
```

- [ ] **Step 2: Syntax check**

Run: `node --check web/static/web/js/app.js`
Expected: sem saída (ok).

- [ ] **Step 3: Manual validation note**

Registrar no controle de execução (Task 14) que a exibição de capas exige validação manual (abrir Biblioteca/Explorar com jogos que tenham `cover_file`).

- [ ] **Step 4: Commit**

```bash
git add web/static/web/js/app.js
git commit -m "feat(web): render real cover images with gradient fallback"
```

---

### Task 9: Tela "Explorar" (view + rota + template + JS + sidebar)

**Files:**
- Modify: `web/views.py`, `web/urls.py`, `web/templates/web/base.html`
- Create: `web/templates/web/explore.html`, `web/static/web/js/explore.js`
- Test: `web/tests.py` (render 200) + `node --check` + manual.

**Interfaces:**
- Consumes: `/api/v1/games/` (paginado, `search`/`genres__slug`/`ordering`), `/api/v1/library/` (POST).
- Produces: rota nomeada `explore` em `/explorar/`.

- [ ] **Step 1: Write the failing test**

In `web/tests.py`, in `ScreenEndpointTests.test_all_screens_return_200`, after the existing asserts add a check for the new page — or add a focused test:

```python
class ExploreScreenTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("exp", password="pw")

    def test_explore_page_renders(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/explorar/").status_code, 200)

    def test_explore_requires_login(self):
        self.assertEqual(self.client.get("/explorar/").status_code, 302)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.ExploreScreenTests -v2`
Expected: FAIL (404 em `/explorar/`).

- [ ] **Step 3: Add the view**

In `web/views.py`, add (following the existing view pattern that renders a shell with an `active` context var):

```python
@login_required
def explore(request):
    return render(request, "web/explore.html", {"active": "explore"})
```

- [ ] **Step 4: Add the route**

In `web/urls.py`, in `urlpatterns`, after the `path("biblioteca/", ...)` line add:

```python
    path("explorar/", views.explore, name="explore"),
```

- [ ] **Step 5: Create the template**

Create `web/templates/web/explore.html`:

```html
{% extends "web/base.html" %}
{% load static %}
{% block title %}Explorar · LaaCLab{% endblock %}

{% block content %}
<div class="page-head">
  <div class="icon-badge">
    <svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
  </div>
  <div>
    <h1>Explorar</h1>
    <p>Descubra jogos e adicione à sua biblioteca</p>
  </div>
</div>

<div class="row between" style="margin-bottom:16px;gap:12px;flex-wrap:wrap">
  <div class="search" style="max-width:420px">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" style="width:18px;height:18px"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
    <input id="ex-search" type="search" placeholder="Buscar jogos..." aria-label="Buscar jogos">
  </div>
  <select id="ex-genre" style="background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text)"></select>
  <select id="ex-order" style="background:var(--surface-2);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text)">
    <option value="-popularity">Mais populares</option>
    <option value="-bug_score">Mais instáveis</option>
    <option value="name">Nome (A–Z)</option>
  </select>
</div>

<div class="games-grid" id="ex-grid"><div class="skeleton">Carregando…</div></div>
<div style="text-align:center;margin-top:18px">
  <button id="ex-more" class="btn btn--outline" style="display:none">Carregar mais</button>
</div>
{% endblock %}

{% block extra_js %}<script src="{% static 'web/js/explore.js' %}"></script>{% endblock %}
```

- [ ] **Step 6: Create the JS**

Create `web/static/web/js/explore.js`:

```javascript
/* Explorar: catálogo paginado (busca/gênero/ordenação) + adicionar/favoritar. */

let page = 1;
let nextUrl = null;

function gameCard(g) {
  const cover = LaaC.cover(g, "");
  cover.style.height = "150px";
  const add = LaaC.el("button", {
    class: "btn btn--primary", style: "margin-top:8px;width:100%;justify-content:center",
    onclick: async () => {
      add.disabled = true;
      try {
        await LaaC.sendJSON("/api/v1/library/", { game: g.slug, favorite: false });
        add.textContent = "Na biblioteca ✓";
      } catch (e) { add.textContent = "Erro"; add.disabled = false; }
    },
  }, "Adicionar");
  return LaaC.el("div", { class: "game-card" }, cover,
    LaaC.el("div", { class: "g-name" }, g.name),
    LaaC.el("div", { class: "row", style: "gap:8px" },
      LaaC.scoreChip(g.score, g.status), add));
}

function buildQuery() {
  const p = new URLSearchParams();
  const s = document.getElementById("ex-search").value.trim();
  const genre = document.getElementById("ex-genre").value;
  const order = document.getElementById("ex-order").value;
  if (s) p.set("search", s);
  if (genre) p.set("genres__slug", genre);
  p.set("ordering", order);
  p.set("page", String(page));
  return p.toString();
}

async function load(reset) {
  const grid = document.getElementById("ex-grid");
  if (reset) { page = 1; grid.innerHTML = ""; }
  const data = await LaaC.getJSON("/api/v1/games/?" + buildQuery());
  if (reset && data.results.length === 0) {
    grid.innerHTML = "<div class='muted' style='padding:10px'>Nenhum jogo encontrado.</div>";
  }
  // /api/v1/games/ cards use REST field names; map to the shape LaaC.cover expects.
  data.results.forEach((g) => grid.append(gameCard({
    slug: g.slug, name: g.name, initials: g.initials, cover: g.cover,
    cover_file: g.cover_file, cover_image: g.cover_image,
    score: g.bug_score, status: g.status,
  })));
  nextUrl = data.next;
  document.getElementById("ex-more").style.display = nextUrl ? "" : "none";
}

async function initExplore() {
  // Genre filter options from the genres endpoint.
  const genres = await LaaC.getJSON("/api/v1/genres/?page=1");
  const sel = document.getElementById("ex-genre");
  sel.append(LaaC.el("option", { value: "" }, "Todos os gêneros"));
  (genres.results || []).forEach((g) => sel.append(LaaC.el("option", { value: g.slug }, g.name)));

  document.getElementById("ex-search").addEventListener("input", () => load(true));
  sel.addEventListener("change", () => load(true));
  document.getElementById("ex-order").addEventListener("change", () => load(true));
  document.getElementById("ex-more").addEventListener("click", () => { page += 1; load(false); });
  await load(true);
}

document.addEventListener("DOMContentLoaded", () => initExplore().catch((e) => {
  if (e.message !== "unauthenticated") console.error(e);
}));
```

- [ ] **Step 7: Add the sidebar link**

In `web/templates/web/base.html`, after the "Meus jogos" `<a class="nav-item ...">` block (the `library` one), add:

```html
      <a class="nav-item {% if active == 'explore' %}is-active{% endif %}" href="{% url 'explore' %}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></svg>
        Explorar
      </a>
```

- [ ] **Step 8: Run tests + syntax check**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.ExploreScreenTests -v2`
Expected: PASS (2 tests).
Run: `node --check web/static/web/js/explore.js`
Expected: ok.

- [ ] **Step 9: Commit**

```bash
git add web/views.py web/urls.py web/templates/web/explore.html web/static/web/js/explore.js web/templates/web/base.html web/tests.py
git commit -m "feat(web): add explore (catalogue) screen"
```

---

### Task 10: "Meus Jogos" — estado vazio + remover/favoritar (`library.js`)

**Files:**
- Modify: `web/static/web/js/library.js`
- Test: `node --check` + validação manual.

**Interfaces:**
- Consumes: `/api/biblioteca/` (lista do usuário) e `/api/v1/library/` (PATCH favorite / DELETE).

- [ ] **Step 1: Read the current file**

Run: `./.venv/Scripts/python.exe -c "print(open('web/static/web/js/library.js', encoding='utf-8').read())"`
(Entender a estrutura atual de render antes de editar.)

- [ ] **Step 2: Add empty state + actions**

In `web/static/web/js/library.js`, after fetching `/api/biblioteca/` and before rendering the grid, add an empty-state branch, and give each card remove/favourite buttons. Insert this block where the grid is populated (replace the grid-fill loop):

```javascript
  const grid = document.getElementById("lib-grid");
  grid.innerHTML = "";
  if (data.games.length === 0) {
    grid.innerHTML =
      "<div class='muted' style='padding:16px'>Sua biblioteca está vazia. " +
      "<a href='/explorar/' style='color:var(--brand)'>Explorar jogos →</a></div>";
    return;
  }
  data.games.forEach((g) => {
    const cover = LaaC.cover(g, "");
    cover.style.height = "150px";
    const fav = LaaC.el("button", {
      class: "btn btn--outline", style: "margin-top:8px",
      onclick: async () => {
        // toggle favourite for this game's library entry
        const lib = await LaaC.getJSON("/api/v1/library/?page=1");
        const entry = (lib.results || []).find((e) => e.game === g.slug);
        if (entry) await LaaC.sendJSON(`/api/v1/library/${entry.id}/`,
          { favorite: !entry.favorite }, "PATCH");
        location.reload();
      },
    }, g.favorite ? "★ Favorito" : "☆ Favoritar");
    grid.append(LaaC.el("div", { class: "game-card" }, cover,
      LaaC.el("div", { class: "g-name" }, g.name),
      LaaC.el("div", { class: "row", style: "gap:8px" },
        LaaC.scoreChip(g.score, g.status), fav)));
  });
```

Note: `#lib-grid` é o id do grid no template `library.html`; se o id atual diferir, ajuste para o existente (conferido no Step 1).

- [ ] **Step 3: Syntax check**

Run: `node --check web/static/web/js/library.js`
Expected: ok.

- [ ] **Step 4: Server-side render still 200**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.ScreenEndpointTests -v2`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add web/static/web/js/library.js
git commit -m "feat(web): library empty state and favourite/remove actions"
```

---

### Task 11: Remover contagem sintética de tópicos (`community.js`)

**Files:**
- Modify: `web/static/web/js/community.js`
- Test: `node --check` + teste existente da comunidade.

- [ ] **Step 1: Remove the synthetic fallback**

In `web/static/web/js/community.js`, replace the `topicCount(game)` function with one that trusts the real field only:

```javascript
/* Real topic count from the endpoint. */
function topicCount(game) {
  return typeof game.topic_count === "number" ? game.topic_count : 0;
}
```

Delete any remaining `TOPIC_COUNTS = {...}` constant if present.

- [ ] **Step 2: Syntax check**

Run: `node --check web/static/web/js/community.js`
Expected: ok.

- [ ] **Step 3: Community endpoint test still green**

Run: `./.venv/Scripts/python.exe manage.py test web.tests.ScreenEndpointTests -v2`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add web/static/web/js/community.js
git commit -m "refactor(web): drop synthetic topic counts"
```

---

### Task 12: Infra Docker — redis + worker + beat + volume media + nginx `/media/`

**Files:**
- Modify: `docker-compose.yml`, `deploy/nginx.conf`, `.env.example`
- Test: `docker compose config` + validação manual (runbook).

- [ ] **Step 1: Add services and media volume to compose**

In `docker-compose.yml`, add a `redis` service, a `worker` service and a `beat` service, mount a `media` volume on `web`/`worker`, and point `web` at Redis. Insert the `redis` service before `web`, add `media` mounts, and append the new services. The `services:` block becomes:

```yaml
  redis:
    image: redis:7
    ports:
      - "6379:6379"

  web:
    build: .
    command: python manage.py runserver 0.0.0.0:8000
    environment:
      DATABASE_URL: "mysql://laaclab:laaclab@db:3306/laaclab"
      DJANGO_DEBUG: "1"
      DJANGO_SECRET_KEY: "dev-compose-secret-change-me"
      DJANGO_ALLOWED_HOSTS: "localhost,127.0.0.1,web"
      PYTHONUNBUFFERED: "1"
      COLLECTSTATIC: "0"
      CELERY_BROKER_URL: "redis://redis:6379/0"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - media:/app/media

  worker:
    build: .
    command: celery -A config worker -l info
    environment:
      DATABASE_URL: "mysql://laaclab:laaclab@db:3306/laaclab"
      DJANGO_DEBUG: "1"
      DJANGO_SECRET_KEY: "dev-compose-secret-change-me"
      CELERY_BROKER_URL: "redis://redis:6379/0"
      PYTHONUNBUFFERED: "1"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    volumes:
      - .:/app
      - media:/app/media

  beat:
    build: .
    command: celery -A config beat -l info
    profiles: ["beat"]
    environment:
      DATABASE_URL: "mysql://laaclab:laaclab@db:3306/laaclab"
      DJANGO_SECRET_KEY: "dev-compose-secret-change-me"
      CELERY_BROKER_URL: "redis://redis:6379/0"
    depends_on:
      redis:
        condition: service_started
```

Keep the existing `db` service as-is. Update the trailing `volumes:` block to:

```yaml
volumes:
  mysql_data:
  media:
```

Note: the `worker`/`beat` `ENTRYPOINT` is the image's `deploy/entrypoint.sh`, which waits for the DB, migrates, then execs the given command — fine for a worker. Set `SEED_ON_START: "0"` on `worker` and `beat` env to avoid double-seeding:

Add `SEED_ON_START: "0"` to both `worker` and `beat` `environment` maps.

- [ ] **Step 2: Serve media in nginx**

In `deploy/nginx.conf`, inside the `server { ... }` block, add next to the existing `location /static/` block:

```nginx
    location /media/ {
        alias /app/media/;
        expires 7d;
        access_log off;
    }
```

(Match the `alias`/root path to how the project mounts media in your nginx container; `/app/media/` matches the compose volume.)

- [ ] **Step 3: Document env**

In `.env.example`, after the `SEED_ON_START=1` line, add:

```
# Celery broker/result backend (Redis).
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
```

- [ ] **Step 4: Validate compose config**

Run: `docker compose config`
Expected: parseia sem erro e lista `redis`, `worker`, `beat`, `media`.

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml deploy/nginx.conf .env.example
git commit -m "build(docker): add redis, celery worker/beat and media volume"
```

---

### Task 13: Verificação final + atualização do controle de execução

**Files:**
- Modify: `docs/CONTROLE-EXECUCAO.md`
- Test: suíte completa + ruff.

- [ ] **Step 1: Run the whole suite**

Run: `./.venv/Scripts/python.exe manage.py test web -v1`
Expected: PASS (todos, incluindo os novos).

- [ ] **Step 2: Lint**

Run: `./.venv/Scripts/python.exe -m ruff check .`
Expected: `All checks passed!` (corrija o que aparecer com `ruff check --fix .`).

- [ ] **Step 3: Migrations check**

Run: `./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run`
Expected: `No changes detected`.

- [ ] **Step 4: Update the control doc**

In `docs/CONTROLE-EXECUCAO.md`, set the P1 rows' **Status** to `Implementado` and **Testes auto** to `passou` for items 1–12; set item 5/6/7/8/9/11/13 **Testes manuais** to `aguardando usuário`. Add a "Pendências de validação manual" list with the concrete manual checks:

```markdown
- P1: rodar `python manage.py ingest --pages 1 --sync` (com Redis/worker) e ver jogos no catálogo.
- P1: abrir /explorar/ — busca/filtro/ordenação/"Carregar mais" e "Adicionar".
- P1: abrir /biblioteca/ — estado vazio quando sem jogos; favoritar/remover.
- P1: capas reais aparecem (cover_file) com fallback de gradiente.
- P1: `docker compose up --build` sobe redis+worker; runbook popular-catalogo.md.
```

Add a Log entry: `| 2026-07-07 | P1 implementado (código); testes auto verdes; testes manuais pendentes do usuário. |`

- [ ] **Step 5: Commit**

```bash
git add docs/CONTROLE-EXECUCAO.md
git commit -m "docs: mark p1 implemented, pending manual validation"
```

---

## Self-Review

**1. Spec coverage** (P1 spec → tasks):
- 2k–5k via API + resumível → Tasks 3–5 (helpers, tasks, comandos) + `IngestCandidate` (Task 2). ✔
- Imagens self-hosted → Task 3 (`download_cover`) + Task 4 (`ingest_game` salva `cover_file`) + Task 8 (front). ✔
- Meus Jogos por usuário + estado vazio → Task 7 (services) + Task 10 (UI). ✔
- Explorar (busca/filtro/ordenação/paginação/adicionar) → Tasks 6 + 9. ✔
- Mocks de catálogo removidos → Task 7 (fallbacks) + Task 11 (TOPIC_COUNTS). ✔
- CI offline com seed pequeno → todos os testes mockam rede/eager (Tasks 4–5). ✔
- Infra (redis/worker/beat/media/nginx) → Task 12. ✔
- Runbook → já existe; validação manual registrada na Task 13. ✔

**2. Placeholder scan:** nenhum "TBD/TODO"; todo passo tem código/comando reais.

**3. Type consistency:** nomes conferidos entre tasks — `refresh_applist/enqueue_pending/ingest_game`, `game_defaults_from_appdetails` (com `genres_names`), `IngestCandidate.Status`, `game_card` com `cover_file`, `LaaC.cover`. Consistentes.

> **Nota de dependência entre tasks:** as Tasks 8–11 (JS) não têm test runner de JS no projeto — a verificação é `node --check` + validação manual (registrada no controle). As demais são TDD com `manage.py test`.
