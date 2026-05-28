"""
Persist functions for media-adjacent entity types: Book, VideoGame, Podcast.

Same accuracy-first pattern as persist_wrestler/event/venue: every extracted
field gets a FieldProvenance row, the entity is found-or-created by slug,
first-write-wins on field updates, no fabrication path.

Cross-linking:
  * Books: author -> Wrestler if exists (via author_wiki_link or author name)
           via Book.related_wrestlers M2M
  * VideoGames: any wrestler mentioned in source paragraphs -> VideoGame.wrestlers M2M
  * Podcasts: host_wiki_links -> Podcast.host_wrestlers M2M
              other mentioned wrestlers -> Podcast.related_wrestlers M2M
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import FieldProvenance, SourceFetch
from ..sources.base import (
    ActionFigureFields, BookFields, PodcastFields,
    ThemeSongFields, VideoGameFields,
)
from . import accuracy_contract
from ._provenance import record_provenance

logger = logging.getLogger(__name__)


def _apply_contract(entity_type: str, entity, source_fetch: SourceFetch):
    """Shared executable-contract gate. See persist_event._apply_contract."""
    state, reasons = accuracy_contract.enforce(entity_type, entity)
    entity.verification_state = state
    entity.verified = (state == accuracy_contract.VERIFIED)
    if state == accuracy_contract.VERIFIED:
        if not entity.verification_source:
            entity.verification_source = source_fetch.source
        entity.last_verified = timezone.now()
    if reasons:
        logger.info(
            "Contract: %s#%s → %s (%s)",
            entity_type, entity.id, state, "; ".join(reasons)[:240],
        )
    return state, reasons


BOOK_FIELD_MAP = {
    "title": "title",
    "author": "author",
    "publication_year": "publication_year",
    "publisher": "publisher",
    "isbn": "isbn",
}

VIDEO_GAME_FIELD_MAP = {
    "name": "name",
    "release_year": "release_year",
    "developer": "developer",
    "publisher": "publisher",
    "systems": "systems",
}

PODCAST_FIELD_MAP = {
    "name": "name",
    "hosts": "hosts",
    "launch_year": "launch_year",
    "end_year": "end_year",
}


@dataclass
class BookPersistResult:
    book_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_wrestlers: int


@dataclass
class VideoGamePersistResult:
    video_game_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_wrestlers: int


@dataclass
class PodcastPersistResult:
    podcast_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_hosts: int
    linked_guests: int


# ---------------------------------------------------------------------- books


def persist_book(
    candidate_name: str,
    fields: BookFields,
    source_fetch: SourceFetch,
) -> Optional[BookPersistResult]:
    """Persist a Book; resolve mentioned wrestlers to related_wrestlers."""
    from owdb_django.owdbapp.models import Book

    canonical_title = (
        str(fields.title.value).strip() if fields.title is not None else candidate_name.strip()
    )
    if not canonical_title:
        return None
    slug = slugify(canonical_title)[:255]

    with transaction.atomic():
        book = None
        if source_fetch.entity_id:
            book = Book.objects.filter(id=source_fetch.entity_id).first()
        if book is None:
            book = Book.objects.filter(slug=slug).first()
        created = False
        if book is None:
            book = Book.objects.create(title=canonical_title, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0

        # IDENTITY-FIELD PROVENANCE (round-2 codex fix). The book's
        # `title` is grounded by the Wikipedia article we fetched —
        # always write that provenance, even if the typed extractor
        # didn't pull a separate title field. Without this row the
        # `book` accuracy contract can't mark the row verified.
        record_provenance(
            entity_type="book", entity_id=book.id,
            field_name="title", value=canonical_title,
            source_fetch=source_fetch, confidence=90,
            snippet=f"Wikipedia article title: {canonical_title}"[:200],
        )
        provenance_rows += 1

        for src_attr, dst_attr in BOOK_FIELD_MAP.items():
            # Title is now handled above as the identity field.
            if dst_attr == "title":
                continue
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(book, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(book, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="book", entity_id=book.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not book.wikipedia_url:
            book.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        book.last_enriched = timezone.now()
        _apply_contract("book", book, source_fetch)
        book.save()

        if source_fetch.entity_id != book.id:
            source_fetch.entity_type = "book"
            source_fetch.entity_id = book.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

        # Link author to Wrestler if the author has a /wiki/ link that
        # matches a Wrestler in the DB.
        linked = _link_book_author_to_wrestler(book, fields)

    # Side effects (outside the transaction so a side-effect failure doesn't
    # roll back the persist).
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("book", book.id, source_fetch)
        # Resolve immediately so the cross-link step below finds them.
        resolve_all_mentions_to_wrestlers()
    except Exception as e:
        logger.exception("Book mention extraction failed: %s", e)

    # Additional wrestler links from paragraph mentions.
    try:
        linked += _link_book_to_mentioned_wrestlers(book, source_fetch)
    except Exception as e:
        logger.exception("Book wrestler-linking failed: %s", e)

    logger.info(
        "Persisted book %r (id=%d, created=%s, wrote=%s, linked_wrestlers=%d)",
        canonical_title, book.id, created, fields_written, linked,
    )
    return BookPersistResult(
        book_id=book.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_wrestlers=linked,
    )


def _link_book_author_to_wrestler(book, fields: BookFields) -> int:
    """If the book's author resolves to a Wrestler in our DB, link it."""
    from owdb_django.owdbapp.models import Wrestler

    candidate_names: list[str] = []
    if fields.author_wiki_link is not None:
        candidate_names.append(str(fields.author_wiki_link.value).strip())
    if fields.author is not None:
        # Author cells can contain "John Doe and Jane Smith"; split on commas/and
        import re as _re
        for part in _re.split(r",|\band\b", str(fields.author.value)):
            part = part.strip()
            if part and part not in candidate_names:
                candidate_names.append(part)

    linked = 0
    for name in candidate_names:
        if not name:
            continue
        w = (
            Wrestler.objects.filter(name=name).first()
            or Wrestler.objects.filter(name__iexact=name).first()
        )
        if w is not None and not book.related_wrestlers.filter(id=w.id).exists():
            book.related_wrestlers.add(w)
            linked += 1
    return linked


def _link_book_to_mentioned_wrestlers(book, source_fetch: SourceFetch) -> int:
    """
    Walk EntityMentions for this book; link any wrestlers mentioned 2+ times.

    Round-2 accuracy fix (same shape as _link_video_game_to_roster). Books
    often mention dozens of wrestlers in passing; only ones referenced
    multiple times are likely subjects vs background. The single-mention
    case was producing books that claimed to be "about" a wrestler whose
    name appeared once in a back-cover blurb.
    """
    from collections import Counter
    from ..models import EntityMention
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_fetch=source_fetch, resolved_entity_type="wrestler",
    )
    counts = Counter(m.resolved_entity_id for m in mentions if m.resolved_entity_id)
    MIN_MENTIONS_FOR_BOOK_LINK = 2

    linked = 0
    for wrestler_id, hit_count in counts.items():
        if hit_count < MIN_MENTIONS_FOR_BOOK_LINK:
            continue
        try:
            w = Wrestler.objects.get(id=wrestler_id)
        except Wrestler.DoesNotExist:
            continue
        if not book.related_wrestlers.filter(id=w.id).exists():
            book.related_wrestlers.add(w)
            linked += 1
    return linked


# --------------------------------------------------------------- video games


def persist_video_game(
    candidate_name: str,
    fields: VideoGameFields,
    source_fetch: SourceFetch,
) -> Optional[VideoGamePersistResult]:
    """Persist a VideoGame; link any mentioned wrestlers to its roster M2M."""
    from owdb_django.owdbapp.models import VideoGame

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None
    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        game = None
        if source_fetch.entity_id:
            game = VideoGame.objects.filter(id=source_fetch.entity_id).first()
        if game is None:
            game = VideoGame.objects.filter(slug=slug).first()
        created = False
        if game is None:
            game = VideoGame.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0

        # IDENTITY-FIELD PROVENANCE (round-2 codex fix). Always write
        # provenance for the game's `name` from the Wikipedia article
        # we fetched. Without this row the `video_game` accuracy
        # contract leaves the entity provisional forever.
        record_provenance(
            entity_type="video_game", entity_id=game.id,
            field_name="name", value=canonical_name,
            source_fetch=source_fetch, confidence=90,
            snippet=f"Wikipedia article title: {canonical_name}"[:200],
        )
        provenance_rows += 1

        for src_attr, dst_attr in VIDEO_GAME_FIELD_MAP.items():
            # Name is now handled above as the identity field.
            if dst_attr == "name":
                continue
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(game, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(game, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="video_game", entity_id=game.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not game.wikipedia_url:
            game.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        game.last_enriched = timezone.now()
        _apply_contract("video_game", game, source_fetch)
        game.save()

        if source_fetch.entity_id != game.id:
            source_fetch.entity_type = "video_game"
            source_fetch.entity_id = game.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("video_game", game.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
    except Exception as e:
        logger.exception("VideoGame mention extraction failed: %s", e)

    linked = _link_video_game_to_roster(game, source_fetch)
    logger.info(
        "Persisted video_game %r (id=%d, created=%s, wrote=%s, roster=%d)",
        canonical_name, game.id, created, fields_written, linked,
    )
    return VideoGamePersistResult(
        video_game_id=game.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_wrestlers=linked,
    )


def _link_video_game_to_roster(game, source_fetch: SourceFetch) -> int:
    """
    Link wrestlers mentioned in the game's source paragraphs to game.wrestlers.

    Round-2 accuracy fix: BOTH codex AND Claude flagged that the previous
    "any single lead-paragraph mention adds the wrestler to the roster"
    behavior overreaches. Example: WWE 2K22's lead mentions Vince McMahon
    in passing as the exec who greenlit the title — Vince was not on the
    playable roster, but the old code attached him to game.wrestlers.

    The tightened rule requires MULTIPLE mentions per resolved wrestler.
    Real roster wrestlers are mentioned repeatedly in a game article
    (cover star, playable character, signature move list). One-off
    mentions are too easily false positives.

    Future tightening (tracked in consistency.py Earl rule
    video_game_roster_lead_only): only count mentions that appear inside
    a Roster / Playable Characters section, not the lead. Today's
    EntityMention rows don't carry section labels, so we use mention
    count as a proxy.
    """
    from collections import Counter
    from ..models import EntityMention
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_fetch=source_fetch, resolved_entity_type="wrestler",
    )
    # Count mentions per resolved wrestler. The same wrestler often gets
    # several EntityMention rows from a single article when their name
    # appears repeatedly.
    counts = Counter(m.resolved_entity_id for m in mentions if m.resolved_entity_id)

    # Roster threshold — at least 2 mentions before we attach. Tunable;
    # tighter values would reduce the chance of leaked execs but also
    # drop real roster members who happen to be named only twice.
    MIN_MENTIONS_FOR_ROSTER = 2

    linked = 0
    for wrestler_id, hit_count in counts.items():
        if hit_count < MIN_MENTIONS_FOR_ROSTER:
            continue
        try:
            w = Wrestler.objects.get(id=wrestler_id)
        except Wrestler.DoesNotExist:
            continue
        if not game.wrestlers.filter(id=w.id).exists():
            game.wrestlers.add(w)
            linked += 1
    return linked


# ------------------------------------------------------------------- podcasts


def persist_podcast(
    candidate_name: str,
    fields: PodcastFields,
    source_fetch: SourceFetch,
) -> Optional[PodcastPersistResult]:
    """Persist a Podcast; link hosts and discussed wrestlers."""
    from owdb_django.owdbapp.models import Podcast

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None
    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        podcast = None
        if source_fetch.entity_id:
            podcast = Podcast.objects.filter(id=source_fetch.entity_id).first()
        if podcast is None:
            podcast = Podcast.objects.filter(slug=slug).first()
        created = False
        if podcast is None:
            podcast = Podcast.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in PODCAST_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(podcast, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(podcast, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="podcast", entity_id=podcast.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not podcast.wikipedia_url:
            podcast.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        podcast.last_enriched = timezone.now()
        _apply_contract("podcast", podcast, source_fetch)
        podcast.save()

        if source_fetch.entity_id != podcast.id:
            source_fetch.entity_type = "podcast"
            source_fetch.entity_id = podcast.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("podcast", podcast.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
    except Exception as e:
        logger.exception("Podcast mention extraction failed: %s", e)

    linked_hosts = _link_podcast_hosts(podcast, fields)
    linked_guests = _link_podcast_guests(podcast, source_fetch)

    logger.info(
        "Persisted podcast %r (id=%d, created=%s, wrote=%s, hosts=%d, guests=%d)",
        canonical_name, podcast.id, created, fields_written, linked_hosts, linked_guests,
    )
    return PodcastPersistResult(
        podcast_id=podcast.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_hosts=linked_hosts,
        linked_guests=linked_guests,
    )


def _link_podcast_hosts(podcast, fields: PodcastFields) -> int:
    """Resolve host names (and host_wiki_links) to Wrestler -> podcast.host_wrestlers."""
    from owdb_django.owdbapp.models import Wrestler
    candidates: list[str] = []
    if fields.host_wiki_links is not None:
        candidates.extend(
            n.strip() for n in str(fields.host_wiki_links.value).split(",") if n.strip()
        )
    if fields.hosts is not None:
        candidates.extend(
            n.strip() for n in str(fields.hosts.value).split(",") if n.strip()
        )

    linked = 0
    for name in candidates:
        if not name:
            continue
        w = (
            Wrestler.objects.filter(name=name).first()
            or Wrestler.objects.filter(name__iexact=name).first()
        )
        if w is not None and not podcast.host_wrestlers.filter(id=w.id).exists():
            podcast.host_wrestlers.add(w)
            linked += 1
    return linked


def _link_podcast_guests(podcast, source_fetch: SourceFetch) -> int:
    """Link wrestlers mentioned anywhere in the podcast's lead to related_wrestlers."""
    from ..models import EntityMention
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_fetch=source_fetch, resolved_entity_type="wrestler",
    )
    linked = 0
    hosted_ids = set(podcast.host_wrestlers.values_list("id", flat=True))
    for m in mentions:
        try:
            w = Wrestler.objects.get(id=m.resolved_entity_id)
        except Wrestler.DoesNotExist:
            continue
        if w.id in hosted_ids:
            continue  # hosts aren't also guests
        if not podcast.related_wrestlers.filter(id=w.id).exists():
            podcast.related_wrestlers.add(w)
            linked += 1
    return linked


# ----------------------------------------------------------- action figures


ACTION_FIGURE_FIELD_MAP = {
    "name": "name",
    "manufacturer": "manufacturer",
    "start_year": "start_year",
    "end_year": "end_year",
}


@dataclass
class ActionFigurePersistResult:
    action_figure_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_wrestlers: int
    linked_promotion: bool


def persist_action_figure(
    candidate_name: str,
    fields: ActionFigureFields,
    source_fetch: SourceFetch,
) -> Optional[ActionFigurePersistResult]:
    """Persist an ActionFigure; resolve promotion + featured wrestlers."""
    from owdb_django.owdbapp.models import ActionFigure
    from .linking import KNOWN_PROMOTIONS, _get_or_create_promotion_stub

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None
    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        af = None
        if source_fetch.entity_id:
            af = ActionFigure.objects.filter(id=source_fetch.entity_id).first()
        if af is None:
            af = ActionFigure.objects.filter(slug=slug).first()
        created = False
        if af is None:
            af = ActionFigure.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in ACTION_FIGURE_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(af, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(af, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="action_figure", entity_id=af.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        # Promotion resolution (Jakks Pacific WWE figures -> WWE Promotion)
        linked_promotion = False
        if fields.promotion_wiki_link is not None:
            promo_link = str(fields.promotion_wiki_link.value)
            spec = KNOWN_PROMOTIONS.get(promo_link)
            if spec is not None:
                promo = _get_or_create_promotion_stub(spec, promo_link)
                if af.promotion_id != promo.id:
                    af.promotion = promo
                    fields_written.append("promotion")
                    linked_promotion = True
                    record_provenance(
                        entity_type="action_figure", entity_id=af.id,
                        field_name="promotion", value=promo.name,
                        source_fetch=source_fetch,
                        snippet=getattr(fields.promotion_wiki_link, "snippet", "") or
                                f"resolved via KNOWN_PROMOTIONS[{promo_link!r}]",
                        confidence=fields.promotion_wiki_link.confidence,
                    )
                    provenance_rows += 1

        if source_fetch.source == "wikipedia" and not af.wikipedia_url:
            af.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        af.last_enriched = timezone.now()
        _apply_contract("action_figure", af, source_fetch)
        af.save()

        if source_fetch.entity_id != af.id:
            source_fetch.entity_type = "action_figure"
            source_fetch.entity_id = af.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    # Mentions + cross-linking to wrestlers
    linked = 0
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("action_figure", af.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
        linked = _link_action_figure_to_wrestlers(af, source_fetch)
    except Exception as e:
        logger.exception("ActionFigure linking failed: %s", e)

    logger.info(
        "Persisted action_figure %r (id=%d, created=%s, wrote=%s, wrestlers=%d, promo=%s)",
        canonical_name, af.id, created, fields_written, linked, linked_promotion,
    )
    return ActionFigurePersistResult(
        action_figure_id=af.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_wrestlers=linked,
        linked_promotion=linked_promotion,
    )


def _link_action_figure_to_wrestlers(af, source_fetch: SourceFetch) -> int:
    """Link any wrestler mentions to featured_wrestlers M2M."""
    from ..models import EntityMention
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_fetch=source_fetch, resolved_entity_type="wrestler",
    )
    linked = 0
    for m in mentions:
        try:
            w = Wrestler.objects.get(id=m.resolved_entity_id)
        except Wrestler.DoesNotExist:
            continue
        if not af.featured_wrestlers.filter(id=w.id).exists():
            af.featured_wrestlers.add(w)
            linked += 1
    return linked


# --------------------------------------------------------------- theme songs


THEME_SONG_FIELD_MAP = {
    "title": "title",
    "artist": "artist",
    "release_year": "release_year",
    "album": "album",
}


@dataclass
class ThemeSongPersistResult:
    theme_song_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_wrestlers: int


def persist_theme_song(
    candidate_name: str,
    fields: ThemeSongFields,
    source_fetch: SourceFetch,
) -> Optional[ThemeSongPersistResult]:
    """Persist a ThemeSong; resolve artist + wrestlers who used it."""
    from owdb_django.owdbapp.models import ThemeSong

    canonical_title = (
        str(fields.title.value).strip() if fields.title is not None else candidate_name.strip()
    )
    if not canonical_title:
        return None
    slug = slugify(canonical_title)[:255]

    with transaction.atomic():
        ts = None
        if source_fetch.entity_id:
            ts = ThemeSong.objects.filter(id=source_fetch.entity_id).first()
        if ts is None:
            ts = ThemeSong.objects.filter(slug=slug).first()
        created = False
        if ts is None:
            ts = ThemeSong.objects.create(title=canonical_title, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in THEME_SONG_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(ts, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(ts, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="theme_song", entity_id=ts.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        # Artist Wikipedia URL (stored as plain string — artist may not be a Wrestler)
        if fields.artist_wiki_link is not None and not ts.artist_wikipedia_url:
            target = str(fields.artist_wiki_link.value).replace(" ", "_")
            ts.artist_wikipedia_url = f"https://en.wikipedia.org/wiki/{target}"[:500]
            fields_written.append("artist_wikipedia_url")

        if source_fetch.source == "wikipedia" and not ts.wikipedia_url:
            ts.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        ts.last_enriched = timezone.now()
        _apply_contract("theme_song", ts, source_fetch)
        ts.save()

        if source_fetch.entity_id != ts.id:
            source_fetch.entity_type = "theme_song"
            source_fetch.entity_id = ts.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    # Mentions + cross-linking to wrestlers who used it as entrance music
    linked = 0
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("theme_song", ts.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
        linked = _link_theme_song_to_users(ts, source_fetch)
    except Exception as e:
        logger.exception("ThemeSong linking failed: %s", e)

    logger.info(
        "Persisted theme_song %r (id=%d, created=%s, wrote=%s, wrestlers=%d)",
        canonical_title, ts.id, created, fields_written, linked,
    )
    return ThemeSongPersistResult(
        theme_song_id=ts.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_wrestlers=linked,
    )


def _link_theme_song_to_users(ts, source_fetch: SourceFetch) -> int:
    """Link any wrestler mentioned in the lead paragraphs as a user of this theme."""
    from ..models import EntityMention
    from owdb_django.owdbapp.models import Wrestler

    mentions = EntityMention.objects.filter(
        source_fetch=source_fetch, resolved_entity_type="wrestler",
    )
    linked = 0
    for m in mentions:
        try:
            w = Wrestler.objects.get(id=m.resolved_entity_id)
        except Wrestler.DoesNotExist:
            continue
        if not ts.used_by_wrestlers.filter(id=w.id).exists():
            ts.used_by_wrestlers.add(w)
            linked += 1
    return linked
