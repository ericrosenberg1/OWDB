"""
TMDB (The Movie Database) source adapter for WrestleBot.

Wraps the existing `owdbapp.scrapers.tmdb.TMDBClient` and exposes a few
agent-friendly entry points:

    search_show(name)          — TV series search (returns top hits)
    search_movie(name)         — Movie/film search
    search_wrestling(query)    — TMDB's combined wrestling search
    get_show_details(tmdb_id)  — full series detail
    get_movie_details(tmdb_id) — full movie detail

API-key resolution lives in the underlying TMDBClient (env / settings).
If no key is configured, every function returns an empty list / None and
logs once.

Accuracy contract:
    TMDB image URLs and ratings can be cited directly (they're TMDB's
    own primary data). For dates, casts, and synopses, the agent should
    prefer Wikipedia when both have it and flag disagreements for Earl.
"""

from __future__ import annotations

import logging
from typing import Optional

from ...owdbapp.scrapers.tmdb import TMDBClient

logger = logging.getLogger(__name__)

_client_singleton: Optional[TMDBClient] = None
_warned_no_key = False


TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


def _client() -> Optional[TMDBClient]:
    """Lazy singleton; returns None if no API key is configured."""
    global _client_singleton, _warned_no_key
    if _client_singleton is None:
        try:
            _client_singleton = TMDBClient()
        except Exception as e:
            if not _warned_no_key:
                logger.info("TMDB disabled: %s", e)
                _warned_no_key = True
            return None
    if not getattr(_client_singleton, "_is_configured", lambda: False)():
        if not _warned_no_key:
            logger.info(
                "TMDB disabled: set TMDB_API_KEY env var or settings.TMDB_API_KEY"
            )
            _warned_no_key = True
        return None
    return _client_singleton


def available() -> bool:
    return _client() is not None


def _poster_url(path: Optional[str], size: str = "w500") -> str:
    if not path:
        return ""
    return f"{TMDB_IMAGE_BASE}/{size}{path}"


def _slim_show(row: dict) -> dict:
    return {
        "tmdb_id": row.get("id"),
        "name": row.get("name") or row.get("original_name") or "",
        "first_air_date": row.get("first_air_date") or "",
        "overview": (row.get("overview") or "")[:500],
        "vote_average": float(row.get("vote_average") or 0.0),
        "vote_count": int(row.get("vote_count") or 0),
        "poster_url": _poster_url(row.get("poster_path")),
        "tmdb_url": f"https://www.themoviedb.org/tv/{row.get('id')}" if row.get("id") else "",
    }


def _slim_movie(row: dict) -> dict:
    return {
        "tmdb_id": row.get("id"),
        "title": row.get("title") or row.get("original_title") or "",
        "release_date": row.get("release_date") or "",
        "overview": (row.get("overview") or "")[:500],
        "vote_average": float(row.get("vote_average") or 0.0),
        "vote_count": int(row.get("vote_count") or 0),
        "poster_url": _poster_url(row.get("poster_path")),
        "tmdb_url": f"https://www.themoviedb.org/movie/{row.get('id')}" if row.get("id") else "",
    }


def search_show(name: str, limit: int = 10) -> list[dict]:
    c = _client()
    if c is None:
        return []
    rows = c.search_tv(name, page=1) or []
    return [_slim_show(r) for r in rows[:max(1, min(limit, 20))]]


def search_movie(name: str, limit: int = 10) -> list[dict]:
    c = _client()
    if c is None:
        return []
    rows = c.search_movies(name, page=1) or []
    return [_slim_movie(r) for r in rows[:max(1, min(limit, 20))]]


def search_wrestling(query: str, limit: int = 10) -> dict:
    """
    TMDB's combined wrestling-aware search. Returns {tv: [...], movies: [...]}.
    """
    c = _client()
    if c is None:
        return {"tv": [], "movies": []}
    if hasattr(c, "search_wrestling_content"):
        try:
            result = c.search_wrestling_content(query) or {}
        except Exception as e:
            logger.warning("TMDB search_wrestling_content failed: %s", e)
            result = {}
        tv = [_slim_show(r) for r in (result.get("tv_shows") or [])[:limit]]
        movies = [_slim_movie(r) for r in (result.get("movies") or [])[:limit]]
        return {"tv": tv, "movies": movies}
    # Fallback if the upstream lacks that method.
    return {"tv": search_show(query, limit), "movies": search_movie(query, limit)}


def get_show_details(tmdb_id: int) -> Optional[dict]:
    c = _client()
    if c is None:
        return None
    return c.get_tv_details(int(tmdb_id))


def get_movie_details(tmdb_id: int) -> Optional[dict]:
    c = _client()
    if c is None:
        return None
    return c.get_movie_details(int(tmdb_id))


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    q = " ".join(sys.argv[1:]) or "WWE Raw"
    print(json.dumps(search_wrestling(q, limit=3), indent=2, default=str))
