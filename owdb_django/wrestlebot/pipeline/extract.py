"""
Extract stage — parse stored SourceFetch.raw_content into typed field structs.

Pure function over SourceFetch rows. No I/O. No DB writes (except optionally
marking the fetch as used). Re-runnable: extracting a SourceFetch twice
returns the same WrestlerFields.
"""

from __future__ import annotations

import logging
from typing import Optional

from django.utils import timezone

from ..models import SourceFetch
from ..sources.base import (
    ActionFigureFields, BookFields, EventFields, PodcastFields,
    PromotionFields, SourceAdapter, SpecialFields, StableFields,
    ThemeSongFields, TitleFields, TVShowFields,
    VenueFields, VideoGameFields, WrestlerFields,
)
from ..sources.wikipedia import WikipediaAdapter

logger = logging.getLogger(__name__)


def _adapter_for_source(source: str) -> Optional[SourceAdapter]:
    if source == "wikipedia":
        return WikipediaAdapter()
    if source == "cagematch":
        from ..sources.cagematch import CagematchAdapter
        return CagematchAdapter()
    if source == "wikidata":
        from ..sources.wikidata import WikidataAdapter
        return WikidataAdapter()
    # Future: profightdb, tmdb, etc.
    return None


def extract_wrestler(fetch: SourceFetch) -> Optional[WrestlerFields]:
    return _run_extract(fetch, "wrestler")


def extract_event(fetch: SourceFetch) -> Optional[EventFields]:
    return _run_extract(fetch, "event")


def extract_venue(fetch: SourceFetch) -> Optional[VenueFields]:
    return _run_extract(fetch, "venue")


def extract_promotion(fetch: SourceFetch) -> Optional[PromotionFields]:
    return _run_extract(fetch, "promotion")


def extract_book(fetch: SourceFetch) -> Optional[BookFields]:
    return _run_extract(fetch, "book")


def extract_video_game(fetch: SourceFetch) -> Optional[VideoGameFields]:
    return _run_extract(fetch, "video_game")


def extract_podcast(fetch: SourceFetch) -> Optional[PodcastFields]:
    return _run_extract(fetch, "podcast")


def extract_action_figure(fetch: SourceFetch) -> Optional[ActionFigureFields]:
    return _run_extract(fetch, "action_figure")


def extract_theme_song(fetch: SourceFetch) -> Optional[ThemeSongFields]:
    return _run_extract(fetch, "theme_song")


def extract_title(fetch: SourceFetch) -> Optional[TitleFields]:
    return _run_extract(fetch, "title")


def extract_stable(fetch: SourceFetch) -> Optional[StableFields]:
    return _run_extract(fetch, "stable")


def extract_tv_show(fetch: SourceFetch) -> Optional[TVShowFields]:
    return _run_extract(fetch, "tv_show")


def extract_special(fetch: SourceFetch) -> Optional[SpecialFields]:
    return _run_extract(fetch, "special")


def _run_extract(fetch: SourceFetch, entity_type: str):
    """
    Dispatch the typed extractor by entity_type and source.

    Returns None on failure. Stamps fetch.used_at on success.
    """
    if fetch.http_status != 200 or not fetch.raw_content:
        return None

    adapter = _adapter_for_source(fetch.source)
    if adapter is None:
        logger.warning("No adapter registered for source %r", fetch.source)
        return None

    try:
        if entity_type == "wrestler":
            fields = adapter.extract_wrestler(fetch.raw_content)
        elif entity_type == "event":
            fields = adapter.extract_event(fetch.raw_content)
        elif entity_type == "venue":
            fields = adapter.extract_venue(fetch.raw_content)
        elif entity_type == "promotion":
            fields = adapter.extract_promotion(fetch.raw_content)
        elif entity_type == "book":
            fields = adapter.extract_book(fetch.raw_content)
        elif entity_type == "video_game":
            fields = adapter.extract_video_game(fetch.raw_content)
        elif entity_type == "podcast":
            fields = adapter.extract_podcast(fetch.raw_content)
        elif entity_type == "action_figure":
            fields = adapter.extract_action_figure(fetch.raw_content)
        elif entity_type == "theme_song":
            fields = adapter.extract_theme_song(fetch.raw_content)
        elif entity_type == "title":
            fields = adapter.extract_title(fetch.raw_content)
        elif entity_type == "stable":
            fields = adapter.extract_stable(fetch.raw_content)
        elif entity_type == "tv_show":
            fields = adapter.extract_tv_show(fetch.raw_content)
        elif entity_type == "special":
            fields = adapter.extract_special(fetch.raw_content)
        else:
            raise ValueError(f"Unsupported entity_type: {entity_type!r}")
    except NotImplementedError:
        logger.debug("Adapter %s doesn't implement %s", fetch.source, entity_type)
        return None
    except Exception as e:
        logger.exception("Extraction crashed for SourceFetch#%d: %s", fetch.id, e)
        return None

    if fields is None:
        logger.info(
            "Extraction yielded no fields for SourceFetch#%d (%s, %s)",
            fetch.id, fetch.candidate_name, entity_type,
        )
        return None

    fetch.used_at = timezone.now()
    fetch.save(update_fields=["used_at"])
    return fields
