"""
Fetch stage — hit the network for each candidate, persist as SourceFetch.

Idempotency policy:
- If a SourceFetch already exists for (source, candidate_name) within
  FRESH_TTL_DAYS, skip re-fetching. Override with force=True.
- Each successful fetch creates a new SourceFetch row (append-only).
"""

from __future__ import annotations

import hashlib
import logging
from datetime import timedelta
from typing import Iterable, Optional

from django.utils import timezone

from ..models import SourceFetch
from ..sources.base import FetchResult, SourceAdapter
from ..sources.cagematch import CagematchAdapter
from ..sources.wikipedia import WikipediaAdapter

logger = logging.getLogger(__name__)


# How long a fetched page is considered "fresh enough" before we refetch.
FRESH_TTL_DAYS = 30


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _is_redirect_to_different_subject(url: str, candidate_name: str) -> bool:
    """
    Detect Wikipedia redirects that landed on a different subject than what
    we searched for. Example: "Real American" -> /wiki/The_Wrestling_Album
    means our query was treated as a song but Wikipedia treats it as an album.

    Returns True if the URL-derived article title differs from candidate_name
    in a way that suggests a different subject (not just a disambiguation
    suffix or accent normalization).
    """
    if "/wiki/" not in url:
        return False
    from urllib.parse import unquote

    title_in_url = url.split("/wiki/", 1)[1].split("#", 1)[0]
    title_in_url = unquote(title_in_url).replace("_", " ").strip()
    if not title_in_url or not candidate_name:
        return False

    # Normalise both for comparison
    a = candidate_name.strip().lower()
    b = title_in_url.strip().lower()

    if a == b:
        return False

    # Strip common disambiguation suffixes from both — those are not subject changes.
    import re as _re

    disambig_re = _re.compile(
        r"\s*\((?:wrestler|wrestling|professional\s+wrestler|disambiguation|"
        r"film|song|album|book|video\s+game|tv\s+series|tag\s+team|"
        r"american\s+wrestler|woman\s+wrestler)\)\s*$",
        _re.IGNORECASE,
    )
    a_stripped = disambig_re.sub("", a).strip()
    b_stripped = disambig_re.sub("", b).strip()
    if a_stripped == b_stripped:
        return False

    # Substring relationship suggests it's NOT a subject change (e.g.
    # "Bret Hart" vs "Bret Hart (wrestler)", or accent normalization).
    if a_stripped in b_stripped or b_stripped in a_stripped:
        # But check it's not a tiny substring of a much larger title.
        if abs(len(a_stripped) - len(b_stripped)) < 8:
            return False

    # Compute trivial token overlap. If <50% of tokens match, treat as different
    # subject. This catches "Real American" (2 tokens) vs "The Wrestling Album"
    # (3 tokens) — 0 token overlap.
    a_tokens = set(a_stripped.split())
    b_tokens = set(b_stripped.split())
    if not a_tokens or not b_tokens:
        return True
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens), len(b_tokens))
    return overlap < 0.5


def fetch_cagematch_for_wrestlers(
    wrestler_ids: Iterable[int],
    force: bool = False,
) -> list[SourceFetch]:
    """
    For each wrestler with a cagematch_url, fetch their Cagematch profile.

    Cagematch enforces a 527s crawl-delay per robots.txt; calling with more
    than 1-2 wrestlers will block on the rate limiter. Use sparingly,
    typically 1 per autonomous cycle.

    Returns the list of SourceFetch rows created (or reused).
    """
    from owdb_django.owdbapp.models import Wrestler

    adapter = CagematchAdapter()
    out: list[SourceFetch] = []
    cutoff = timezone.now() - timedelta(days=FRESH_TTL_DAYS)

    for wid in wrestler_ids:
        try:
            wrestler = Wrestler.objects.get(id=wid)
        except Wrestler.DoesNotExist:
            continue
        if not wrestler.cagematch_url:
            continue

        # Skip if a recent successful cagematch fetch already exists for this entity.
        if not force:
            recent = (
                SourceFetch.objects.filter(
                    source="cagematch",
                    entity_type="wrestler",
                    entity_id=wid,
                    fetched_at__gte=cutoff,
                    http_status=200,
                )
                .order_by("-fetched_at")
                .first()
            )
            if recent is not None:
                logger.debug(
                    "Reusing recent cagematch SourceFetch#%d for Wrestler#%d", recent.id, wid
                )
                out.append(recent)
                continue

        try:
            result = adapter.fetch_wrestler_by_url(wrestler.cagematch_url)
        except Exception as e:
            logger.warning("Cagematch fetch failed for Wrestler#%d: %s", wid, e)
            continue

        if result is None:
            logger.info("No cagematch content fetched for Wrestler#%d (%s)", wid, wrestler.name)
            continue

        fetch_row = SourceFetch.objects.create(
            source="cagematch",
            url=result.url,
            entity_type="wrestler",
            entity_id=wid,
            candidate_name=wrestler.name,
            http_status=result.http_status,
            content_hash=_content_hash(result.raw_content),
            raw_content=result.raw_content,
        )
        out.append(fetch_row)
        logger.info(
            "Fetched cagematch profile for Wrestler#%d (%s) -> SourceFetch#%d",
            wid,
            wrestler.name,
            fetch_row.id,
        )

    return out


def _fetch_candidates_for_type(
    candidate_names: Iterable[str],
    entity_type: str,
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    """
    Shared candidate fetch loop. `entity_type` determines which adapter method
    we call (fetch_wrestler_by_name / fetch_event_by_name / fetch_venue_by_name)
    and what gets stamped on the SourceFetch row.
    """
    if adapter is None:
        adapter = WikipediaAdapter()

    if entity_type == "wrestler":
        fetch_method = adapter.fetch_wrestler_by_name
    elif entity_type == "event":
        fetch_method = adapter.fetch_event_by_name
    elif entity_type == "venue":
        fetch_method = adapter.fetch_venue_by_name
    elif entity_type == "promotion":
        fetch_method = adapter.fetch_promotion_by_name
    elif entity_type == "book":
        fetch_method = adapter.fetch_book_by_name
    elif entity_type == "video_game":
        fetch_method = adapter.fetch_video_game_by_name
    elif entity_type == "podcast":
        fetch_method = adapter.fetch_podcast_by_name
    elif entity_type == "action_figure":
        fetch_method = adapter.fetch_action_figure_by_name
    elif entity_type == "theme_song":
        fetch_method = adapter.fetch_theme_song_by_name
    elif entity_type == "title":
        fetch_method = adapter.fetch_title_by_name
    elif entity_type == "stable":
        fetch_method = adapter.fetch_stable_by_name
    elif entity_type == "tv_show":
        fetch_method = adapter.fetch_tv_show_by_name
    elif entity_type == "special":
        fetch_method = adapter.fetch_special_by_name
    else:
        raise ValueError(f"Unsupported entity_type for fetch: {entity_type!r}")

    out: list[SourceFetch] = []
    cutoff = timezone.now() - timedelta(days=FRESH_TTL_DAYS)

    for name in candidate_names:
        if not force:
            recent = (
                SourceFetch.objects.filter(
                    source=adapter.source_name,
                    entity_type=entity_type,
                    candidate_name=name,
                    fetched_at__gte=cutoff,
                    http_status=200,
                )
                .order_by("-fetched_at")
                .first()
            )
            if recent is not None:
                logger.debug("Reusing recent SourceFetch for %s (%s)", name, recent.fetched_at)
                out.append(recent)
                continue

        try:
            result: Optional[FetchResult] = fetch_method(name)
        except Exception as e:
            logger.warning("Fetch failed for %s on %s: %s", name, adapter.source_name, e)
            continue

        if result is None:
            logger.info("No content fetched for %s on %s", name, adapter.source_name)
            continue

        content_hash = _content_hash(result.raw_content)

        # Redirect detection: if an existing SourceFetch has the same source
        # + content_hash, Wikipedia redirected our candidate to an existing
        # article. We refuse to create a duplicate row with a fabricated
        # name — instead reuse the existing fetch.
        existing_with_same_content = (
            SourceFetch.objects.filter(
                source=adapter.source_name, content_hash=content_hash, http_status=200
            )
            .order_by("fetched_at")
            .first()
        )
        if existing_with_same_content is not None:
            logger.warning(
                "Skipping %r [%s]: content identical to SourceFetch#%d (%r) — "
                "Wikipedia redirected to an existing article",
                name,
                entity_type,
                existing_with_same_content.id,
                existing_with_same_content.candidate_name,
            )
            out.append(existing_with_same_content)
            continue

        # Redirect-target-mismatch detection: when Wikipedia redirects our
        # search to a different subject (e.g. "Real American" -> "The Wrestling
        # Album"), creating an entity for the original query is wrong — the
        # data describes the redirect target, not what we asked for.
        # We detect this by comparing URL-derived title against candidate_name.
        if _is_redirect_to_different_subject(result.url, name):
            logger.warning(
                "Skipping %r [%s]: Wikipedia redirected to a different subject (%s) — "
                "refusing to persist as %r",
                name,
                entity_type,
                result.url,
                name,
            )
            continue

        fetch_row = SourceFetch.objects.create(
            source=adapter.source_name,
            url=result.url,
            entity_type=entity_type,
            candidate_name=name,
            http_status=result.http_status,
            content_hash=content_hash,
            raw_content=result.raw_content,
        )
        out.append(fetch_row)
        logger.info(
            "Fetched %s [%s] on %s -> SourceFetch#%d",
            name,
            entity_type,
            adapter.source_name,
            fetch_row.id,
        )

    return out


def fetch_wrestler_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    """Fetch and persist source content for wrestler candidates."""
    return _fetch_candidates_for_type(candidate_names, "wrestler", adapter, force)


def fetch_event_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    """Fetch and persist source content for event candidates."""
    return _fetch_candidates_for_type(candidate_names, "event", adapter, force)


def fetch_venue_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    """Fetch and persist source content for venue candidates."""
    return _fetch_candidates_for_type(candidate_names, "venue", adapter, force)


def fetch_promotion_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    """Fetch and persist source content for promotion candidates."""
    return _fetch_candidates_for_type(candidate_names, "promotion", adapter, force)


def fetch_book_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "book", adapter, force)


def fetch_video_game_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "video_game", adapter, force)


def fetch_podcast_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "podcast", adapter, force)


def fetch_action_figure_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "action_figure", adapter, force)


def fetch_theme_song_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "theme_song", adapter, force)


def fetch_title_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "title", adapter, force)


def fetch_stable_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "stable", adapter, force)


def fetch_tv_show_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "tv_show", adapter, force)


def fetch_special_candidates(
    candidate_names: Iterable[str],
    adapter: Optional[SourceAdapter] = None,
    force: bool = False,
) -> list[SourceFetch]:
    return _fetch_candidates_for_type(candidate_names, "special", adapter, force)
