"""
Brave Search API wrapper.

A thin client around https://api.search.brave.com/res/v1/web/search that
returns clean, structured search hits. Used by the JR and Earl agents when
they need to discover candidate URLs that aren't already on Wikipedia.

API key resolution (first hit wins):
    1. settings.BRAVE_SEARCH_API_KEY (Django setting)
    2. $BRAVE_SEARCH_API_KEY (environment variable)
    3. macOS Keychain entry "wrestlebot-brave-search"

If no key is configured, `search()` returns an empty list and logs once
at INFO. The agents are written to handle that gracefully — Brave Search
is an enrichment tool, not a hard dependency.

Accuracy contract:
    Brave returns URLs and snippets but never structured facts. Agents
    treat search hits as candidates only — anything they decide to use as
    a fact MUST be re-fetched through one of the SourceAdapters (Wikipedia,
    Wikidata, Cagematch) so the FieldProvenance trail stays intact.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)

BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
KEYCHAIN_SERVICE = "wrestlebot-brave-search"

# Brave free tier is 1 req/sec. Cap a hair under to leave clock-skew headroom.
RATE_LIMIT_PER_SEC = 1.0 / 1.05

_warned_no_key = False


@dataclass
class BraveSearchHit:
    """One result row from Brave Search."""
    title: str
    url: str
    description: str
    age: str = ""  # e.g. "2 days ago" — Brave returns this when available
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "description": self.description,
            "age": self.age,
        }


# ---------------------------------------------------------------- API key


def _read_key_from_keychain() -> Optional[str]:
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


def get_api_key() -> Optional[str]:
    """Resolve a Brave Search API key from settings, env, or Keychain."""
    # 1. Django settings
    try:
        from django.conf import settings
        key = getattr(settings, "BRAVE_SEARCH_API_KEY", None)
        if key:
            return key
    except Exception:
        pass

    # 2. Environment variable
    key = os.environ.get("BRAVE_SEARCH_API_KEY")
    if key:
        return key

    # 3. macOS Keychain
    return _read_key_from_keychain()


def available() -> bool:
    return get_api_key() is not None


# ---------------------------------------------------------------- search


def search(
    query: str,
    count: int = 10,
    offset: int = 0,
    country: str = "us",
    safesearch: str = "moderate",
    freshness: Optional[str] = None,  # e.g. "pw" (past week), "py" (past year)
    timeout_seconds: int = 15,
) -> list[BraveSearchHit]:
    """
    Run one Brave Web Search query.

    Returns a list of `BraveSearchHit` (possibly empty). Never raises on
    network/HTTP failure — logs the issue and returns an empty list so the
    agent loop can move on.
    """
    global _warned_no_key

    if not query or not query.strip():
        return []

    key = get_api_key()
    if not key:
        if not _warned_no_key:
            logger.info(
                "Brave Search disabled: set BRAVE_SEARCH_API_KEY env var "
                "(or 'wrestlebot-brave-search' Keychain entry) to enable."
            )
            _warned_no_key = True
        return []

    params = {
        "q": query.strip(),
        "count": str(min(max(count, 1), 20)),
        "offset": str(max(offset, 0)),
        "country": country,
        "safesearch": safesearch,
    }
    if freshness:
        params["freshness"] = freshness
    url = BRAVE_SEARCH_ENDPOINT + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "X-Subscription-Token": key,
            "User-Agent": "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org)",
        },
        method="GET",
    )

    with rate_limited("brave_search", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning("Brave Search HTTP %s for %r: %s", e.code, query, e.reason)
            return []
        except Exception as e:
            logger.warning("Brave Search request failed for %r: %s", query, e)
            return []

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.warning("Brave Search returned non-JSON for %r: %s", query, e)
        return []

    web = payload.get("web") or {}
    results = web.get("results") or []
    hits: list[BraveSearchHit] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        title = (row.get("title") or "").strip()
        link = (row.get("url") or "").strip()
        desc = (row.get("description") or "").strip()
        if not link:
            continue
        hits.append(BraveSearchHit(
            title=title,
            url=link,
            description=desc,
            age=row.get("age", "") or "",
            extra={
                k: row.get(k) for k in ("language", "family_friendly", "page_age")
                if row.get(k) is not None
            },
        ))
    return hits


# Convenience for shell debugging.
if __name__ == "__main__":  # pragma: no cover
    import sys
    q = " ".join(sys.argv[1:]) or "Hulk Hogan wrestler"
    for h in search(q, count=5):
        print(f"- {h.title}\n  {h.url}\n  {h.description}\n")
