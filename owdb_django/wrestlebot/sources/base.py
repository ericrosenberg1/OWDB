"""
SourceAdapter base class and field dataclasses.

A SourceAdapter wraps one external source (Wikipedia, Cagematch, etc.) and
provides two operations:

    fetch_*  — performs I/O, returns FetchResult with raw_content + url
    extract_* — pure function over a stored SourceFetch row, returns typed fields

Every extracted field carries a snippet (the substring of raw_content the field
was parsed from). The pipeline writes one FieldProvenance row per (entity,
field), pointing back to the SourceFetch and storing the snippet for later
audit. This is the structural backbone of the accuracy-first guarantee.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class FetchResult:
    """Outcome of an I/O fetch. Caller writes this into a SourceFetch row."""

    url: str
    http_status: int
    raw_content: str
    # Free-form source-specific id (e.g., Wikipedia page title, Cagematch numeric id).
    # Useful for later refetching the same logical resource.
    source_id: Optional[str] = None


@dataclass
class FieldSnippet:
    """One extracted field plus the source-text snippet it was parsed from."""

    value: object  # int, str, date, list, etc. — type depends on field
    snippet: str   # The raw text fragment that supports `value`
    confidence: int = 100  # 0-100. Lower for inferred/derived values.


def _snippets_dict() -> dict:
    return {}


@dataclass
class WrestlerFields:
    """
    Typed extraction result for a wrestler.

    Each populated attribute also has a corresponding entry in `snippets`
    mapping field_name -> FieldSnippet. Unset attributes are omitted from
    `snippets`.
    """

    name: Optional[FieldSnippet] = None
    real_name: Optional[FieldSnippet] = None
    aliases: Optional[FieldSnippet] = None
    birth_date: Optional[FieldSnippet] = None
    death_date: Optional[FieldSnippet] = None
    debut_year: Optional[FieldSnippet] = None
    retirement_year: Optional[FieldSnippet] = None
    nationality: Optional[FieldSnippet] = None
    hometown: Optional[FieldSnippet] = None
    height: Optional[FieldSnippet] = None
    weight: Optional[FieldSnippet] = None
    finishers: Optional[FieldSnippet] = None
    signature_moves: Optional[FieldSnippet] = None
    trained_by: Optional[FieldSnippet] = None
    roles: Optional[FieldSnippet] = None  # comma-separated role tags

    def populated_fields(self) -> dict[str, FieldSnippet]:
        """Return {field_name: FieldSnippet} for all set fields."""
        out: dict[str, FieldSnippet] = {}
        for attr in (
            "name", "real_name", "aliases", "birth_date", "death_date",
            "debut_year", "retirement_year", "nationality", "hometown",
            "height", "weight", "finishers", "signature_moves", "trained_by",
            "roles",
        ):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class PromotionFields:
    """Typed extraction result for a promotion."""

    name: Optional[FieldSnippet] = None
    abbreviation: Optional[FieldSnippet] = None
    founded_year: Optional[FieldSnippet] = None
    closed_year: Optional[FieldSnippet] = None
    website: Optional[FieldSnippet] = None
    headquarters: Optional[FieldSnippet] = None
    founder: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in (
            "name", "abbreviation", "founded_year", "closed_year",
            "website", "headquarters", "founder",
        ):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class EventFields:
    """Typed extraction result for an event."""

    name: Optional[FieldSnippet] = None
    date: Optional[FieldSnippet] = None  # value is date
    promotion_name: Optional[FieldSnippet] = None
    venue_name: Optional[FieldSnippet] = None
    venue_location: Optional[FieldSnippet] = None
    venue_wiki_link: Optional[FieldSnippet] = None  # /wiki/X target for venue stub
    promotion_wiki_link: Optional[FieldSnippet] = None
    attendance: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in (
            "name", "date", "promotion_name", "promotion_wiki_link",
            "venue_name", "venue_wiki_link", "venue_location", "attendance",
        ):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class TrainingSchoolFields:
    """Typed extraction result for a pro wrestling training school."""
    name: Optional[FieldSnippet] = None
    location: Optional[FieldSnippet] = None
    founded_year: Optional[FieldSnippet] = None
    closed_year: Optional[FieldSnippet] = None
    founder: Optional[FieldSnippet] = None
    head_trainer: Optional[FieldSnippet] = None
    parent_promotion_wiki_link: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "location", "founded_year", "closed_year",
                     "founder", "head_trainer", "parent_promotion_wiki_link"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class TVShowFields:
    """Typed extraction result for a TV show."""
    name: Optional[FieldSnippet] = None
    promotion_wiki_link: Optional[FieldSnippet] = None
    promotion_name: Optional[FieldSnippet] = None
    network: Optional[FieldSnippet] = None
    premiere_year: Optional[FieldSnippet] = None  # int
    finale_year: Optional[FieldSnippet] = None    # int (null = still running)

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "promotion_wiki_link", "promotion_name",
                     "network", "premiere_year", "finale_year"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class SpecialFields:
    """Typed extraction result for a documentary, film, or TV special."""
    title: Optional[FieldSnippet] = None
    release_year: Optional[FieldSnippet] = None
    type: Optional[FieldSnippet] = None  # 'documentary' / 'movie' / 'tv_special'
    director: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("title", "release_year", "type", "director"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class TitleFields:
    """Typed extraction result for a championship/title."""
    name: Optional[FieldSnippet] = None
    promotion_wiki_link: Optional[FieldSnippet] = None
    promotion_name: Optional[FieldSnippet] = None
    debut_year: Optional[FieldSnippet] = None
    retirement_year: Optional[FieldSnippet] = None
    title_type: Optional[FieldSnippet] = None  # "singles", "tag team", "women's", etc.

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "promotion_wiki_link", "promotion_name",
                     "debut_year", "retirement_year", "title_type"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class StableFields:
    """Typed extraction result for a stable/faction."""
    name: Optional[FieldSnippet] = None
    promotion_wiki_link: Optional[FieldSnippet] = None
    promotion_name: Optional[FieldSnippet] = None
    formed_year: Optional[FieldSnippet] = None
    disbanded_year: Optional[FieldSnippet] = None
    leader_wiki_links: Optional[FieldSnippet] = None  # comma-separated wiki titles
    member_wiki_links: Optional[FieldSnippet] = None  # comma-separated wiki titles

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "promotion_wiki_link", "promotion_name",
                     "formed_year", "disbanded_year",
                     "leader_wiki_links", "member_wiki_links"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class ActionFigureFields:
    """Typed extraction result for an action figure line or series."""
    name: Optional[FieldSnippet] = None
    manufacturer: Optional[FieldSnippet] = None
    start_year: Optional[FieldSnippet] = None
    end_year: Optional[FieldSnippet] = None
    promotion_wiki_link: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "manufacturer", "start_year", "end_year", "promotion_wiki_link"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class ThemeSongFields:
    """Typed extraction result for a theme/entrance song."""
    title: Optional[FieldSnippet] = None
    artist: Optional[FieldSnippet] = None
    artist_wiki_link: Optional[FieldSnippet] = None
    release_year: Optional[FieldSnippet] = None
    album: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("title", "artist", "artist_wiki_link", "release_year", "album"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class BookFields:
    """Typed extraction result for a book."""
    title: Optional[FieldSnippet] = None
    author: Optional[FieldSnippet] = None
    author_wiki_link: Optional[FieldSnippet] = None
    publication_year: Optional[FieldSnippet] = None
    publisher: Optional[FieldSnippet] = None
    isbn: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("title", "author", "author_wiki_link", "publication_year", "publisher", "isbn"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class VideoGameFields:
    """Typed extraction result for a video game."""
    name: Optional[FieldSnippet] = None
    release_year: Optional[FieldSnippet] = None
    developer: Optional[FieldSnippet] = None
    publisher: Optional[FieldSnippet] = None
    systems: Optional[FieldSnippet] = None  # comma-separated platforms

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "release_year", "developer", "publisher", "systems"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class PodcastFields:
    """Typed extraction result for a podcast."""
    name: Optional[FieldSnippet] = None
    hosts: Optional[FieldSnippet] = None  # comma-separated
    host_wiki_links: Optional[FieldSnippet] = None  # comma-separated /wiki/X targets
    launch_year: Optional[FieldSnippet] = None
    end_year: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "hosts", "host_wiki_links", "launch_year", "end_year"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


@dataclass
class VenueFields:
    """Typed extraction result for a venue."""

    name: Optional[FieldSnippet] = None
    location: Optional[FieldSnippet] = None  # full address / locality
    city: Optional[FieldSnippet] = None
    country: Optional[FieldSnippet] = None
    capacity: Optional[FieldSnippet] = None  # int
    opened_year: Optional[FieldSnippet] = None

    def populated_fields(self) -> dict[str, FieldSnippet]:
        out: dict[str, FieldSnippet] = {}
        for attr in ("name", "location", "city", "country", "capacity", "opened_year"):
            v = getattr(self, attr)
            if v is not None:
                out[attr] = v
        return out


class SourceAdapter(ABC):
    """
    Abstract base for all source adapters.

    Subclasses MUST set `source_name` to a value in
    `wrestlebot.models.SOURCE_CHOICES`.
    """

    source_name: str = ""

    @abstractmethod
    def fetch_wrestler_by_name(self, name: str) -> Optional[FetchResult]:
        """Fetch a wrestler's page. Returns None if not found / not allowed."""

    @abstractmethod
    def extract_wrestler(self, raw_content: str) -> Optional[WrestlerFields]:
        """
        Parse raw fetched content into a WrestlerFields struct.

        Pure function. Should never do I/O. Should return None if the content
        is not a valid wrestler page (e.g., disambiguation, redirect, error).
        """

    # Optional: subclasses may implement the same fetch/extract pair for
    # other entity types (promotion, event, match, etc.). Not abstract because
    # not every source covers every entity type.

    def fetch_promotion_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support promotion fetch")

    def extract_promotion(self, raw_content: str) -> Optional[PromotionFields]:
        raise NotImplementedError(f"{self.source_name} does not support promotion extract")

    def fetch_event_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support event fetch")

    def extract_event(self, raw_content: str) -> Optional[EventFields]:
        raise NotImplementedError(f"{self.source_name} does not support event extract")

    def fetch_venue_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support venue fetch")

    def extract_venue(self, raw_content: str) -> Optional[VenueFields]:
        raise NotImplementedError(f"{self.source_name} does not support venue extract")

    def fetch_book_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support book fetch")

    def extract_book(self, raw_content: str) -> Optional[BookFields]:
        raise NotImplementedError(f"{self.source_name} does not support book extract")

    def fetch_video_game_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support video game fetch")

    def extract_video_game(self, raw_content: str) -> Optional[VideoGameFields]:
        raise NotImplementedError(f"{self.source_name} does not support video game extract")

    def fetch_podcast_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support podcast fetch")

    def extract_podcast(self, raw_content: str) -> Optional[PodcastFields]:
        raise NotImplementedError(f"{self.source_name} does not support podcast extract")

    def fetch_tv_show_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support TV show fetch")

    def extract_tv_show(self, raw_content: str) -> Optional[TVShowFields]:
        raise NotImplementedError(f"{self.source_name} does not support TV show extract")

    def fetch_training_school_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support training school fetch")

    def extract_training_school(self, raw_content: str) -> Optional[TrainingSchoolFields]:
        raise NotImplementedError(f"{self.source_name} does not support training school extract")

    def fetch_special_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support special fetch")

    def extract_special(self, raw_content: str) -> Optional[SpecialFields]:
        raise NotImplementedError(f"{self.source_name} does not support special extract")

    def fetch_title_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support title fetch")

    def extract_title(self, raw_content: str) -> Optional[TitleFields]:
        raise NotImplementedError(f"{self.source_name} does not support title extract")

    def fetch_stable_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support stable fetch")

    def extract_stable(self, raw_content: str) -> Optional[StableFields]:
        raise NotImplementedError(f"{self.source_name} does not support stable extract")

    def fetch_action_figure_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support action figure fetch")

    def extract_action_figure(self, raw_content: str) -> Optional[ActionFigureFields]:
        raise NotImplementedError(f"{self.source_name} does not support action figure extract")

    def fetch_theme_song_by_name(self, name: str) -> Optional[FetchResult]:
        raise NotImplementedError(f"{self.source_name} does not support theme song fetch")

    def extract_theme_song(self, raw_content: str) -> Optional[ThemeSongFields]:
        raise NotImplementedError(f"{self.source_name} does not support theme song extract")
