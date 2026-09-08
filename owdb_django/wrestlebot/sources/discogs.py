"""
Discogs adapter — music release database.

Discogs is a community-curated music database with deep release-level
detail (label, catalog number, country, format). For WrestleBot, it
complements MusicBrainz when researching theme songs and wrestler-
related records (e.g. "WWE: The Music Vol. 1").

API: https://api.discogs.com/

Auth: requires a personal access token (free, create at
https://www.discogs.com/settings/developers). Resolution order:
    1. settings.DISCOGS_TOKEN
    2. $DISCOGS_TOKEN
    3. macOS Keychain entry "wrestlebot-discogs"

If no token is configured, returns empty results gracefully.

Rate limits:
    Authenticated: 60 req/min. Unauthenticated: 25 req/min. We cap to
    1 req/sec to be a good citizen.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)

DISCOGS_BASE = "https://api.discogs.com"
KEYCHAIN_SERVICE = "wrestlebot-discogs"
USER_AGENT = "wrestlingdb-wrestlebot/1.0 +https://wrestlingdb.org"
# Authenticated tier is 60/min but we cap at ~1/sec to be a good citizen.
RATE_LIMIT_PER_SEC = 1.0 / 1.05

_warned_no_token = False


@dataclass
class DiscogsHit:
    """One Discogs search hit (release/master/artist)."""
    discogs_id: int
    type: str         # 'release' | 'master' | 'artist'
    title: str
    year: str = ""
    label: str = ""
    catno: str = ""
    country: str = ""
    formats: list[str] = field(default_factory=list)
    genre: list[str] = field(default_factory=list)
    style: list[str] = field(default_factory=list)
    thumb_url: str = ""
    discogs_url: str = ""

    def to_dict(self) -> dict:
        return {
            "discogs_id": self.discogs_id,
            "type": self.type,
            "title": self.title,
            "year": self.year,
            "label": self.label,
            "catno": self.catno,
            "country": self.country,
            "formats": self.formats,
            "genre": self.genre,
            "style": self.style,
            "thumb_url": self.thumb_url,
            "discogs_url": self.discogs_url,
        }


# ---------------------------------------------------------------- token


def _read_token_from_keychain() -> Optional[str]:
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password",
             "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip()


def get_token() -> Optional[str]:
    try:
        from django.conf import settings
        token = getattr(settings, "DISCOGS_TOKEN", None)
        if token:
            return token
    except Exception:
        pass
    t = os.environ.get("DISCOGS_TOKEN")
    if t:
        return t
    return _read_token_from_keychain()


def available() -> bool:
    return get_token() is not None


# ---------------------------------------------------------------- HTTP


def _http_get_json(path: str, params: Optional[dict] = None,
                  timeout: float = 15.0) -> Optional[dict]:
    global _warned_no_token
    token = get_token()
    if not token:
        if not _warned_no_token:
            logger.info(
                "Discogs disabled: set DISCOGS_TOKEN env var "
                "(or 'wrestlebot-discogs' Keychain entry). "
                "Get a token at https://www.discogs.com/settings/developers"
            )
            _warned_no_token = True
        return None
    qs = dict(params or {})
    qs["token"] = token
    url = f"{DISCOGS_BASE}{path}?{urllib.parse.urlencode(qs)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    with rate_limited("discogs", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                logger.warning("Discogs rate limit hit; backing off 30s")
                time.sleep(30)
            else:
                logger.warning("Discogs HTTP %s for %s: %s", e.code, path, e.reason)
            return None
        except Exception as e:
            logger.warning("Discogs request failed for %s: %s", path, e)
            return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning("Discogs returned non-JSON for %s: %s", path, e)
        return None


# ---------------------------------------------------------------- search


def search(
    query: str,
    type: str = "release",   # 'release' | 'master' | 'artist' | 'label'
    artist: Optional[str] = None,
    year: Optional[str] = None,
    limit: int = 10,
) -> list[DiscogsHit]:
    """Discogs /database/search."""
    if not query or not query.strip():
        return []
    params: dict = {
        "q": query.strip(),
        "type": type if type in ("release", "master", "artist", "label") else "release",
        "per_page": max(1, min(limit, 50)),
    }
    if artist:
        params["artist"] = artist
    if year:
        params["year"] = year
    data = _http_get_json("/database/search", params=params)
    if not data:
        return []
    out: list[DiscogsHit] = []
    for r in data.get("results", []) or []:
        if not isinstance(r, dict):
            continue
        out.append(DiscogsHit(
            discogs_id=int(r.get("id") or 0),
            type=r.get("type", "") or "",
            title=r.get("title", "") or "",
            year=str(r.get("year") or ""),
            label=", ".join(r.get("label") or []) if isinstance(r.get("label"), list) else (r.get("label") or ""),
            catno=r.get("catno", "") or "",
            country=r.get("country", "") or "",
            formats=list(r.get("format") or []),
            genre=list(r.get("genre") or []),
            style=list(r.get("style") or []),
            thumb_url=r.get("thumb", "") or "",
            discogs_url=f"https://www.discogs.com{r.get('uri','')}" if r.get("uri") else "",
        ))
    return out


def get_release(release_id: int) -> Optional[dict]:
    """Fetch a full release detail by Discogs release ID."""
    if not release_id:
        return None
    return _http_get_json(f"/releases/{int(release_id)}")


if __name__ == "__main__":  # pragma: no cover
    import sys
    q = " ".join(sys.argv[1:]) or "WWE The Music Vol 1"
    hits = search(q, limit=5)
    print(f"{len(hits)} hits for {q!r}:")
    for h in hits:
        print(json.dumps(h.to_dict(), indent=2))
