"""
Tavily Search API wrapper.

A thin client around https://api.tavily.com/search. Used by the JR, Earl,
and Al agents as a second web-search backend alongside Brave Search.

Why two backends:
    - **Brave Search** is general-purpose web search. Best for current
      news, discovery, and broad "what's out there" queries.
    - **Tavily** is specifically tuned for LLM use. Returns cleaner
      snippets and an optional LLM-synthesized `answer` field. Best for
      focused factual lookups ("when did X happen", "who founded Y").

API key resolution (first hit wins):
    1. settings.TAVILY_API_KEY (Django setting)
    2. $TAVILY_API_KEY (environment variable)
    3. macOS Keychain entry "wrestlebot-tavily-search"

Accuracy contract:
    Tavily's `answer` field is LLM-synthesized — it is NOT a fact source.
    The agents must treat it as a hint to investigate further, never as
    ground truth. Any fact ingested into the DB must come through a
    structured source adapter (Wikipedia, Wikidata, Cagematch) so the
    FieldProvenance trail stays intact.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)

TAVILY_SEARCH_ENDPOINT = "https://api.tavily.com/search"
KEYCHAIN_SERVICE = "wrestlebot-tavily-search"

# Tavily free tier is 1k req/month at modest per-second rates. Cap at
# 2 req/sec to stay a good citizen across concurrent agents.
RATE_LIMIT_PER_SEC = 2.0

_warned_no_key = False


@dataclass
class TavilySearchHit:
    """One result row from Tavily."""

    title: str
    url: str
    content: str  # snippet — Tavily's `content` is similar to Brave's `description`
    score: float = 0.0  # 0..1 relevance score from Tavily
    raw_content: str = ""  # Set only if include_raw_content=True

    def to_dict(self) -> dict:
        out = {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "score": round(self.score, 3),
        }
        if self.raw_content:
            out["raw_content"] = self.raw_content[:2000]
        return out


@dataclass
class TavilyResponse:
    """Full result of a Tavily query (search results + optional answer)."""

    query: str
    answer: str = ""  # LLM-synthesized summary; HINT only, not ground truth
    hits: list[TavilySearchHit] = field(default_factory=list)
    response_time_seconds: float = 0.0


# ---------------------------------------------------------------- API key


def _read_key_from_keychain() -> Optional[str]:
    if platform.system() != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.strip()


def get_api_key() -> Optional[str]:
    """Resolve a Tavily API key from settings, env, or Keychain."""
    try:
        from django.conf import settings

        key = getattr(settings, "TAVILY_API_KEY", None)
        if key:
            return key
    except Exception:
        pass

    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return key

    return _read_key_from_keychain()


def available() -> bool:
    return get_api_key() is not None


# ---------------------------------------------------------------- search


def search(
    query: str,
    *,
    max_results: int = 8,
    search_depth: str = "basic",  # "basic" or "advanced"
    topic: str = "general",  # "general" or "news"
    include_answer: bool = True,
    include_raw_content: bool = False,
    include_domains: Optional[list[str]] = None,
    exclude_domains: Optional[list[str]] = None,
    timeout_seconds: int = 20,
) -> Optional[TavilyResponse]:
    """
    Run one Tavily search. Returns a TavilyResponse, or None if the key
    is unset (so callers can choose to fall back to another backend).

    On HTTP/network failure, returns an empty TavilyResponse with the
    query echoed back (so the agent sees "no results" rather than crashing).
    """
    global _warned_no_key

    if not query or not query.strip():
        return TavilyResponse(query="")

    key = get_api_key()
    if not key:
        if not _warned_no_key:
            logger.info(
                "Tavily disabled: set TAVILY_API_KEY env var "
                "(or 'wrestlebot-tavily-search' Keychain entry) to enable."
            )
            _warned_no_key = True
        return None

    body: dict = {
        "api_key": key,
        "query": query.strip(),
        "max_results": max(1, min(max_results, 20)),
        "search_depth": search_depth if search_depth in ("basic", "advanced") else "basic",
        "topic": topic if topic in ("general", "news") else "general",
        "include_answer": bool(include_answer),
        "include_raw_content": bool(include_raw_content),
    }
    if include_domains:
        body["include_domains"] = list(include_domains)
    if exclude_domains:
        body["exclude_domains"] = list(exclude_domains)

    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_SEARCH_ENDPOINT,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org)",
        },
        method="POST",
    )

    with rate_limited("tavily_search", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                payload_bytes = resp.read()
        except urllib.error.HTTPError as e:
            logger.warning("Tavily HTTP %s for %r: %s", e.code, query, e.reason)
            return TavilyResponse(query=query)
        except Exception as e:
            logger.warning("Tavily request failed for %r: %s", query, e)
            return TavilyResponse(query=query)

    try:
        payload = json.loads(payload_bytes.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as e:
        logger.warning("Tavily returned non-JSON for %r: %s", query, e)
        return TavilyResponse(query=query)

    hits: list[TavilySearchHit] = []
    for row in payload.get("results", []) or []:
        if not isinstance(row, dict):
            continue
        url = (row.get("url") or "").strip()
        if not url:
            continue
        hits.append(
            TavilySearchHit(
                title=(row.get("title") or "").strip(),
                url=url,
                content=(row.get("content") or "").strip(),
                score=float(row.get("score") or 0.0),
                raw_content=(row.get("raw_content") or "") or "",
            )
        )

    return TavilyResponse(
        query=payload.get("query") or query,
        answer=(payload.get("answer") or "").strip(),
        hits=hits,
        response_time_seconds=float(payload.get("response_time") or 0.0),
    )


# Convenience for shell debugging.
if __name__ == "__main__":  # pragma: no cover
    import sys

    q = " ".join(sys.argv[1:]) or "Bret Hart wrestler"
    r = search(q, max_results=5)
    if r is None:
        print("Tavily not configured.")
    else:
        if r.answer:
            print(f"ANSWER (hint, not ground truth):\n  {r.answer}\n")
        print(f"{len(r.hits)} results:")
        for h in r.hits:
            print(f"- [{h.score:.2f}] {h.title}\n  {h.url}\n  {h.content[:200]}\n")
