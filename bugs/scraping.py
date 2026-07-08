"""Steam reviews scraper (keyless public API). Compliance: public reviews,
rate-limited, provenance kept in BugSignal (external_id + url)."""
import re

import requests

REVIEWS_URL = "https://store.steampowered.com/appreviews/{appid}"
_TAG = re.compile(r"\[/?[a-z]+\]")


def parse_reviews(payload: dict) -> list[dict]:
    out = []
    for rev in payload.get("reviews", []) or []:
        txt = re.sub(r"\s+", " ", _TAG.sub(" ", rev.get("review", "") or "")).strip()
        rid = str(rev.get("recommendationid", "") or "")
        if rid and 25 <= len(txt) <= 600:
            steamid = str((rev.get("author") or {}).get("steamid", ""))
            out.append({
                "external_id": rid,
                "text": txt,
                "url": f"https://steamcommunity.com/profiles/{steamid}/recommended/" if steamid else "",
            })
    return out


def fetch_steam_reviews(appid: int, n: int = 40, session=None) -> list[dict]:
    s = session or requests
    r = s.get(
        REVIEWS_URL.format(appid=appid),
        params={"json": 1, "language": "all", "num_per_page": n, "filter": "recent",
                "purchase_type": "all", "review_type": "all"},
        headers={"User-Agent": "LaaCLab-bugscan/1.0"}, timeout=25,
    )
    r.raise_for_status()
    return parse_reviews(r.json())
