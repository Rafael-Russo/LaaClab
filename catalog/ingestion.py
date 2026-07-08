"""Steam ingestion helpers.

Pure mappers (testable without network) plus thin network fetchers for the
SteamSpy ranking and the Steam store appdetails endpoint. Celery tasks in
``catalog/tasks.py`` orchestrate these.
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
        "name": name[:200],
        "short_description": _strip_html(data.get("short_description", ""), 300),
        "about": _strip_html(data.get("detailed_description", ""), 700),
        "cover_image": data.get("header_image", "") or "",
        "cover": palette,
        "bug_score": 0,
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
