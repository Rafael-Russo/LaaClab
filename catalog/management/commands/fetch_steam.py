"""Fetch a real games catalogue from the (keyless) Steam store API.

This talks to the internet and writes a versioned fixture
(``catalog/fixtures/games_seed.json``) so that seeding the database stays
reproducible and offline-friendly (CI/Docker never need network access).

Usage::

    python manage.py fetch_steam            # refresh the committed fixture
    python manage.py fetch_steam --sleep 1  # be gentler on the API

A few catalogue staples that are not sold on Steam (Fortnite, Valorant) are
appended from a small manual list so the mockup games all exist.
"""

import html
import json
import re
import time
from pathlib import Path

import requests
from django.core.management.base import BaseCommand

from catalog.ingestion import provisional_bug_score

# Curated list of popular Steam appids (the catalogue we seed from).
STEAM_APPIDS = [
    1938090,  # Call of Duty (Warzone / MWII hub)
    730,      # Counter-Strike 2
    271590,   # Grand Theft Auto V
    1091500,  # Cyberpunk 2077
    1172470,  # Apex Legends
    1174180,  # Red Dead Redemption 2
    1245620,  # ELDEN RING
    1971870,  # Mortal Kombat 1
    1888930,  # The Last of Us Part I
    1086940,  # Baldur's Gate 3
    292030,   # The Witcher 3: Wild Hunt
    578080,   # PUBG: BATTLEGROUNDS
    570,      # Dota 2
    252490,   # Rust
    413150,   # Stardew Valley
    1145360,  # Hades
    367520,   # Hollow Knight
    814380,   # Sekiro: Shadows Die Twice
    582010,   # Monster Hunter: World
    2050650,  # Resident Evil 4
    1623730,  # Palworld
    553850,   # HELLDIVERS 2
    1716740,  # Starfield
    892970,   # Valheim
    1174180,  # (dup guard handled below)
]

# Games not on Steam — added by hand so the mockup catalogue is complete.
MANUAL_GAMES = [
    {
        "slug": "fortnite", "name": "Fortnite", "steam_appid": None,
        "short_description": "Battle royale gratuito da Epic Games.",
        "about": "Fortnite é um jogo battle royale gratuito onde até 100 jogadores "
                 "disputam para ser o último de pé, construindo estruturas e usando um "
                 "arsenal variado. Recebe atualizações sazonais frequentes.",
        "cover_image": "", "cover": ["#3aa0d8", "#1a5a8f"],
        "release_date": "2017", "developer": "Epic Games", "publisher": "Epic Games",
        "metacritic": 78, "achievements": 0, "genres": ["Battle Royale", "Ação"],
    },
    {
        "slug": "valorant", "name": "Valorant", "steam_appid": None,
        "short_description": "FPS tático 5v5 baseado em agentes, da Riot Games.",
        "about": "Valorant é um shooter tático 5v5 baseado em personagens, onde a "
                 "precisão da mira encontra habilidades únicas de cada agente. "
                 "Gratuito para jogar.",
        "cover_image": "", "cover": ["#bd3b4a", "#2b3a3f"],
        "release_date": "2020", "developer": "Riot Games", "publisher": "Riot Games",
        "metacritic": 80, "achievements": 0, "genres": ["FPS", "Tático"],
    },
]

STORE_URL = "https://store.steampowered.com/api/appdetails"
_TAG_RE = re.compile(r"<[^>]+>")

# Deterministic gradient palette (picked by appid so covers stay stable).
_PALETTE = [
    ["#3a4a3f", "#1b241f"], ["#2b6cb0", "#1a365d"], ["#b7950b", "#4a3f0b"],
    ["#2f7d5b", "#14352a"], ["#bd3b4a", "#2b3a3f"], ["#a1421f", "#3a1a10"],
    ["#c07f2a", "#241608"], ["#3f4a55", "#161c22"], ["#8a3a2a", "#2a140d"],
    ["#7a2a2a", "#1c0d0d"], ["#4a3f6b", "#1c1830"], ["#2a6b6b", "#0f2626"],
]


def _strip_html(raw: str, limit: int = 600) -> str:
    text = html.unescape(_TAG_RE.sub(" ", raw or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit].rstrip()


class Command(BaseCommand):
    help = "Fetch a games catalogue from Steam into catalog/fixtures/games_seed.json"

    def add_arguments(self, parser):
        parser.add_argument("--sleep", type=float, default=0.6,
                            help="Seconds to wait between requests (rate limiting).")
        parser.add_argument("--output", type=str, default="",
                            help="Override the fixture output path.")

    def handle(self, *args, **options):
        out_path = Path(options["output"]) if options["output"] else (
            Path(__file__).resolve().parents[2] / "fixtures" / "games_seed.json"
        )
        session = requests.Session()
        session.headers.update({"User-Agent": "LaaCLab-seed/1.0"})

        records: list[dict] = []
        seen_appids: set[int] = set()

        for appid in STEAM_APPIDS:
            if appid in seen_appids:
                continue
            seen_appids.add(appid)
            record = self._fetch_one(session, appid)
            if record:
                records.append(record)
                self.stdout.write(self.style.SUCCESS(f"  [ok] {record['name']}"))
            else:
                self.stdout.write(self.style.WARNING(f"  [--] appid {appid} skipped"))
            time.sleep(options["sleep"])

        for game in MANUAL_GAMES:
            game = {**game, "bug_score": provisional_bug_score(0, game["name"])}
            game.setdefault("likes", 20000 + len(game["name"]) * 137)
            game.setdefault("dislikes", game["likes"] // 18)
            records.append(game)
            self.stdout.write(self.style.SUCCESS(f"  + {game['name']} (manual)"))

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.stdout.write(
            self.style.SUCCESS(f"\nWrote {len(records)} games to {out_path}")
        )

    def _fetch_one(self, session, appid: int) -> dict | None:
        try:
            resp = session.get(
                STORE_URL,
                params={"appids": appid, "l": "portuguese", "cc": "br"},
                timeout=20,
            )
            resp.raise_for_status()
            payload = resp.json().get(str(appid), {})
        except (requests.RequestException, ValueError) as exc:
            self.stderr.write(f"  ! appid {appid}: {exc}")
            return None

        if not payload.get("success"):
            return None
        data = payload["data"]
        if data.get("type") != "game":
            return None

        name = data.get("name", "").strip()
        if not name:
            return None

        palette = _PALETTE[appid % len(_PALETTE)]
        score = provisional_bug_score(appid, name)
        return {
            "slug": "",  # let the model derive it from the name
            "name": name,
            "steam_appid": appid,
            "short_description": _strip_html(data.get("short_description", ""), 300),
            "about": _strip_html(data.get("detailed_description", ""), 700),
            "cover_image": data.get("header_image", "") or "",
            "cover": palette,
            "bug_score": score,
            "release_date": (data.get("release_date") or {}).get("date", ""),
            "developer": ", ".join(data.get("developers", []) or [])[:200],
            "publisher": ", ".join(data.get("publishers", []) or [])[:200],
            "metacritic": (data.get("metacritic") or {}).get("score"),
            "achievements": (data.get("achievements") or {}).get("total", 0),
            "genres": [g["description"] for g in data.get("genres", []) or []],
            "likes": 20000 + (appid % 900) * 137,
            "dislikes": (20000 + (appid % 900) * 137) // 18,
        }
