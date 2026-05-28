"""
Mention-driven auto-discovery — the engine that makes the graph build itself.

When any entity is persisted, we capture every `/wiki/X` link in its source
paragraphs as an EntityMention. Most mentions are unresolved at first (the
linked entity doesn't yet exist in our DB). This module turns the top
unresolved mentions into discovery candidates, fetches each one, classifies
it (wrestler / event / venue / promotion), and routes to the right typed
persist pipeline.

Accuracy-first contract: if a fetched page can't be confidently classified
(see classifier.py), the page is skipped, not stored under a wrong type.

Strict skip list: GENERIC_WIKI_TITLES in classifier.py — generic concept
pages ("Pay-per-view", "Professional wrestling") are dropped before fetch.
"""

from __future__ import annotations

import hashlib
import logging
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AutoDiscoveryStats:
    candidates_considered: int = 0
    fetched: int = 0
    wrestler_persisted: int = 0
    event_persisted: int = 0
    venue_persisted: int = 0
    promotion_persisted: int = 0
    skipped_generic: int = 0
    skipped_unclassified: int = 0
    skipped_no_content: int = 0
    skipped_extract_failed: int = 0
    candidates: list[tuple[str, int, str]] = None  # (wiki_link, count, classification)


def _existing_entity_wiki_titles() -> set[str]:
    """
    Build the set of Wikipedia titles we already have entities for. Joins
    wikipedia_url across Wrestler / Promotion / Venue plus the SourceFetch
    history (for Events, which don't have a wikipedia_url column).
    """
    from urllib.parse import unquote as _unquote
    from owdb_django.owdbapp.models import Promotion, Venue, Wrestler
    from ..models import SourceFetch

    titles: set[str] = set()

    def _add(url: str):
        if not url or "/wiki/" not in url:
            return
        t = url.split("/wiki/", 1)[1].split("#", 1)[0]
        t = _unquote(t).replace("_", " ")
        if t:
            titles.add(t)

    for w in (
        Wrestler.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .only("wikipedia_url")
    ):
        _add(w.wikipedia_url)
    for p in (
        Promotion.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .only("wikipedia_url")
    ):
        _add(p.wikipedia_url)
    for v in (
        Venue.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .only("wikipedia_url")
    ):
        _add(v.wikipedia_url)
    for f in SourceFetch.objects.filter(
        source="wikipedia",
        entity_type="event",
        entity_id__isnull=False,
    ).only("url"):
        _add(f.url)
    return titles


def top_unresolved_mentions(limit: int = 50) -> list[tuple[str, int]]:
    """
    Return the top wiki_link targets that:
      - have NO entity already in the DB (matched by Wikipedia title)
      - are NOT a generic concept page
      - we have NOT already attempted to fetch (any prior SourceFetch with
        this candidate_name)

    Ordered by descending mention-count, then alphabetically for ties.
    """
    from ..models import EntityMention, SourceFetch
    from .classifier import is_generic_wiki_title

    # Already-fetched candidate names (string match).
    fetched_names = set(
        SourceFetch.objects.filter(source="wikipedia")
        .values_list("candidate_name", flat=True)
        .distinct()
    )
    # Already-persisted entities, identified by Wikipedia title (catches
    # accent / ASCII variation between candidate_name and the canonical
    # wikipedia_url title).
    existing_titles = _existing_entity_wiki_titles()

    counts = Counter()
    qs = EntityMention.objects.filter(resolved_entity_id__isnull=True).values_list(
        "wiki_link", flat=True
    )
    for link in qs:
        if not link:
            continue
        if is_generic_wiki_title(link):
            continue
        if link in fetched_names:
            continue
        if link in existing_titles:
            continue
        counts[link] += 1

    return counts.most_common(limit)


def auto_discover_step(limit: int = 5) -> AutoDiscoveryStats:
    """
    Run one round of mention-driven discovery: fetch + classify + persist
    up to `limit` candidates.

    Returns AutoDiscoveryStats with per-type counts and the list of
    candidates actually attempted (for visibility/logging).
    """
    from ..models import SourceFetch
    from ..sources.wikipedia import WikipediaAdapter
    from .classifier import classify_html, is_generic_wiki_title
    from .extract import extract_event, extract_venue, extract_wrestler
    from .persist import persist_wrestler
    from .persist_event import persist_event, persist_venue

    adapter = WikipediaAdapter()
    stats = AutoDiscoveryStats(candidates=[])

    candidates = top_unresolved_mentions(limit=limit * 5)
    stats.candidates_considered = len(candidates)

    for wiki_link, mention_count in candidates:
        if stats.fetched >= limit:
            break

        if is_generic_wiki_title(wiki_link):
            stats.skipped_generic += 1
            continue

        # Fetch the page (wrestler-by-name path works for any title — it
        # just resolves redirects and returns the HTML).
        try:
            result = adapter.fetch_wrestler_by_name(wiki_link)
        except Exception as e:
            logger.warning("auto-discovery: fetch failed for %s: %s", wiki_link, e)
            stats.skipped_no_content += 1
            continue
        if result is None:
            stats.skipped_no_content += 1
            stats.candidates.append((wiki_link, mention_count, "no-content"))
            continue

        # Classify before committing to a SourceFetch type. Pass the
        # candidate (Wikipedia page title) so the classifier can detect
        # sub-topic articles ("WWE action figures" etc.).
        entity_type = classify_html(result.raw_content, article_title=wiki_link)
        if entity_type is None:
            stats.skipped_unclassified += 1
            stats.candidates.append((wiki_link, mention_count, "unclassified"))
            logger.info("auto-discovery: %s -> unclassified, skipping", wiki_link)
            continue

        # Stamp a SourceFetch row with the classified entity_type.
        fetch = SourceFetch.objects.create(
            source="wikipedia",
            url=result.url,
            entity_type=entity_type,
            candidate_name=wiki_link,
            http_status=result.http_status,
            content_hash=hashlib.sha256(result.raw_content.encode("utf-8")).hexdigest(),
            raw_content=result.raw_content,
        )
        stats.fetched += 1
        stats.candidates.append((wiki_link, mention_count, entity_type))

        # Type-specific extract + persist.
        if entity_type == "wrestler":
            fields = extract_wrestler(fetch)
            if fields is None:
                stats.skipped_extract_failed += 1
                continue
            res = persist_wrestler(wiki_link, fields, fetch)
            if res is not None:
                stats.wrestler_persisted += 1
        elif entity_type == "event":
            fields = extract_event(fetch)
            if fields is None:
                stats.skipped_extract_failed += 1
                continue
            res = persist_event(wiki_link, fields, fetch)
            if res is not None:
                stats.event_persisted += 1
        elif entity_type == "venue":
            fields = extract_venue(fetch)
            if fields is None:
                stats.skipped_extract_failed += 1
                continue
            res = persist_venue(wiki_link, fields, fetch)
            if res is not None:
                stats.venue_persisted += 1
        elif entity_type == "promotion":
            from .extract import extract_promotion
            from .persist_event import persist_promotion

            fields = extract_promotion(fetch)
            if fields is None:
                stats.skipped_extract_failed += 1
                continue
            res = persist_promotion(wiki_link, fields, fetch)
            if res is not None:
                stats.promotion_persisted += 1

    # After persisting new entities, sweep mentions so newly-created targets
    # get resolved to entities they newly match — across all entity types.
    try:
        from .linking import resolve_all_mentions

        resolve_all_mentions()
    except Exception as e:
        logger.exception("Post-discovery mention sweep failed: %s", e)

    return stats
