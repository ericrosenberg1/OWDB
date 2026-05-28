"""
Source adapters for the accuracy-first WrestleBot v3 pipeline.

Each adapter wraps one external source (Wikipedia, Cagematch, ProFightDB, etc.)
and provides a uniform interface:

    adapter.fetch_wrestler_by_name(name)  -> FetchResult or None  (does I/O)
    adapter.extract_wrestler(source_fetch) -> WrestlerFields or None  (pure)

Fetch and extract are deliberately separated so we can re-run extraction on
stored raw_content without re-fetching, which matters a lot when the
extractor evolves.
"""

from .base import (
    SourceAdapter,
    FetchResult,
    WrestlerFields,
    PromotionFields,
    EventFields,
    VenueFields,
    BookFields,
    VideoGameFields,
    PodcastFields,
    ActionFigureFields,
    ThemeSongFields,
    TitleFields,
    StableFields,
    TVShowFields,
    SpecialFields,
    TrainingSchoolFields,
    FieldSnippet,
)
from .wikipedia import WikipediaAdapter
from .cagematch import CagematchAdapter
from .wikidata import WikidataAdapter

__all__ = [
    "SourceAdapter",
    "FetchResult",
    "WrestlerFields",
    "PromotionFields",
    "EventFields",
    "FieldSnippet",
    "WikipediaAdapter",
    "CagematchAdapter",
    "WikidataAdapter",
]
