"""
persist_event + persist_venue — extends the WrestleBot v3 pipeline to handle
events and venues with the same provenance + cross-linking semantics as
wrestlers.

When an event is persisted:
  * The venue is found-or-created from `venue_wiki_link` (preferred) or
    `venue_name`. Stubs get a `wikipedia_url` so a future cycle can do a
    full fetch+extract+bio on the venue itself.
  * The promotion is resolved via the linking.py KNOWN_PROMOTIONS registry
    if `promotion_wiki_link` is a recognised wrestling org. Events that
    can't resolve their promotion are skipped (promotion is FK-required).
  * Provenance rows are written for every populated field.

When a venue is persisted, it's the same first-write-wins model as wrestlers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import SourceFetch
from ..sources.base import EventFields, VenueFields
from . import accuracy_contract
from ._provenance import record_provenance

logger = logging.getLogger(__name__)


def _apply_contract(entity_type: str, entity, source_fetch: SourceFetch):
    """
    Resolve verification_state from the executable contract and persist it.

    Keeps the legacy `verified=True` boolean for back-compat with templates
    that haven't been migrated, but the *truth* is the verification_state
    enum — only entities the contract says are eligible get True.
    """
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


# Event fields we write straight through to the Event model (post-resolution).
EVENT_DIRECT_FIELDS = {
    "name": "name",
    "date": "date",
    "attendance": "attendance",
}

VENUE_FIELD_MAP = {
    "name": "name",
    "location": "location",
    "city": "city",
    "country": "country",
    "capacity": "capacity",
    "opened_year": "opened_year",
}


@dataclass
class EventPersistResult:
    event_id: int
    created: bool
    venue_id: Optional[int]
    promotion_id: Optional[int]
    fields_written: list[str]
    provenance_rows_created: int


@dataclass
class VenuePersistResult:
    venue_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int


@dataclass
class PromotionPersistResult:
    promotion_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int


PROMOTION_FIELD_MAP = {
    "name": "name",
    "abbreviation": "abbreviation",
    "founded_year": "founded_year",
    "closed_year": "closed_year",
    "website": "website",
    "headquarters": "headquarters",
    "founder": "founder",
}


def persist_promotion(
    candidate_name: str,
    fields,
    source_fetch: SourceFetch,
) -> Optional[PromotionPersistResult]:
    """Persist a Promotion with provenance rows. Idempotent."""
    from owdb_django.owdbapp.models import Promotion
    from .linking import KNOWN_PROMOTIONS

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None
    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        # Locate existing promotion. Priority: source_fetch.entity_id, then
        # KNOWN_PROMOTIONS canonical name lookup (handles "World Wrestling
        # Federation" -> existing WWF stub), then slug, then abbreviation.
        promo = None
        if source_fetch.entity_id:
            promo = Promotion.objects.filter(id=source_fetch.entity_id).first()
        if promo is None:
            # Check if the candidate_name matches a KNOWN_PROMOTIONS canonical key
            spec = KNOWN_PROMOTIONS.get(candidate_name) or KNOWN_PROMOTIONS.get(canonical_name)
            if spec:
                promo = (
                    Promotion.objects.filter(abbreviation=spec["abbreviation"]).first()
                    or Promotion.objects.filter(slug=slugify(spec["name"])[:255]).first()
                )
        if promo is None:
            promo = Promotion.objects.filter(slug=slug).first()
        if promo is None and fields.abbreviation:
            promo = Promotion.objects.filter(abbreviation=str(fields.abbreviation.value)[:50]).first()
        created = False
        if promo is None:
            promo = Promotion.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in PROMOTION_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(promo, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(promo, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="promotion", entity_id=promo.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not promo.wikipedia_url:
            promo.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        # Resolve verification state via the executable contract instead
        # of the legacy "we wrote something therefore verified=True" rule.
        promo.last_enriched = timezone.now()
        _apply_contract("promotion", promo, source_fetch)
        promo.save()

        if source_fetch.entity_id != promo.id:
            source_fetch.entity_type = "promotion"
            source_fetch.entity_id = promo.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    logger.info(
        "Persisted promotion %r (id=%d, created=%s, wrote=%s)",
        canonical_name, promo.id, created, fields_written,
    )

    # Mentions
    try:
        from .mentions import persist_mentions_for_entity
        persist_mentions_for_entity("promotion", promo.id, source_fetch)
    except Exception as e:
        logger.exception("Promotion mention extraction failed: %s", e)

    return PromotionPersistResult(
        promotion_id=promo.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
    )


# --------------------------------------------------------------------- venue


def persist_venue(
    candidate_name: str,
    fields: VenueFields,
    source_fetch: SourceFetch,
) -> Optional[VenuePersistResult]:
    """Persist a Venue with provenance rows. Idempotent."""
    from owdb_django.owdbapp.models import Venue

    name_snip = fields.name
    canonical_name = (
        str(name_snip.value).strip() if name_snip is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None
    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        # Reuse existing entity if the source_fetch already points at one.
        venue = None
        if source_fetch.entity_id:
            venue = Venue.objects.filter(id=source_fetch.entity_id).first()
        if venue is None and source_fetch.candidate_name:
            cand_slug = slugify(source_fetch.candidate_name)[:255]
            if cand_slug:
                venue = Venue.objects.filter(slug=cand_slug).first()
        if venue is None:
            venue = Venue.objects.filter(slug=slug).first()
        created = False
        if venue is None:
            venue = Venue.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0

        for src_attr, dst_attr in VENUE_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(venue, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(venue, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="venue", entity_id=venue.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not venue.wikipedia_url:
            venue.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        venue.last_enriched = timezone.now()
        _apply_contract("venue", venue, source_fetch)
        venue.save()

        if source_fetch.entity_id != venue.id:
            source_fetch.entity_type = "venue"
            source_fetch.entity_id = venue.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    logger.info(
        "Persisted venue %r (id=%d, created=%s, wrote=%s)",
        canonical_name, venue.id, created, fields_written,
    )

    # Mentions in venue prose — usually link to teams that play there but may
    # link to notable events hosted at the venue, useful for auto-discovery.
    try:
        from .mentions import persist_mentions_for_entity
        persist_mentions_for_entity("venue", venue.id, source_fetch)
    except Exception as e:
        logger.exception("Venue mention extraction failed: %s", e)

    return VenuePersistResult(
        venue_id=venue.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
    )


# --------------------------------------------------------------------- event


def _looks_like_multi_venue_mash(name: str) -> bool:
    """
    Detect concatenated venue cells where Wikipedia listed multiple venues
    in a single infobox cell separated by <br> (which our get_text drops).

    Heuristic: anomalously long names AND containing multiple "venue-like"
    head nouns ("Arena", "Coliseum", "Center", "Stadium", "Dome", "Garden",
    "Memorial"). Real venues rarely exceed ~50 chars and contain at most
    one of these head nouns.
    """
    if not name:
        return False
    if len(name) > 80:
        return True
    venue_heads = ("Arena", "Coliseum", "Center", "Centre", "Stadium",
                   "Dome", "Garden", "Memorial", "Pavilion", "Hall")
    head_count = sum(1 for h in venue_heads if h in name)
    return head_count >= 3


def _ensure_venue_stub_from_wiki(
    wiki_link: Optional[str],
    display_name: Optional[str],
    source_fetch: Optional[SourceFetch] = None,
):
    """
    Find-or-create a Venue stub from a wiki-link target + display name.

    Returns the Venue, or None if:
      * neither wiki_link nor display_name is usable, or
      * the display_name looks like a multi-venue concatenation (we skip
        rather than persist obviously-bad data).

    When source_fetch is provided, writes FieldProvenance(name) so the
    stub's `name` is traceable back to the event that created it.
    """
    from owdb_django.owdbapp.models import Venue

    name = (display_name or wiki_link or "").strip()
    if not name:
        return None

    # Accuracy guard: skip obviously-concatenated names. The infobox cell
    # had multiple venues and our text extractor mashed them together.
    if _looks_like_multi_venue_mash(name):
        logger.warning(
            "Skipping multi-venue concatenation %r (probable mash-up)", name[:120],
        )
        return None

    slug = slugify(name)[:255]
    if not slug:
        return None

    venue = Venue.objects.filter(slug=slug).first()
    if venue is not None:
        # Backfill wikipedia_url if we just learned one.
        if wiki_link and not venue.wikipedia_url:
            venue.wikipedia_url = f"https://en.wikipedia.org/wiki/{wiki_link.replace(' ', '_')}"[:500]
            venue.save(update_fields=["wikipedia_url"])
        return venue

    wikipedia_url = (
        f"https://en.wikipedia.org/wiki/{wiki_link.replace(' ', '_')}"[:500]
        if wiki_link else ""
    )
    venue = Venue.objects.create(
        name=name, slug=slug, wikipedia_url=wikipedia_url or None,
    )

    # Provenance: record that this stub's name came from the calling
    # event's infobox cell. Without this, the venue page's verification
    # stamp under-reports its sources.
    if source_fetch is not None:
        try:
            record_provenance(
                entity_type="venue",
                entity_id=venue.id,
                field_name="name",
                value=name,
                source_fetch=source_fetch,
                snippet=name,  # the venue name itself is the snippet
                confidence=80,  # 80 — name came from an event's infobox,
                                # not the venue's own Wikipedia page
            )
        except Exception as e:
            logger.warning("Couldn't record provenance for venue stub %s: %s", name, e)

    logger.info("Created Venue stub: %s", name)
    return venue


def _resolve_promotion_for_event(promo_wiki_link: Optional[str], promo_name: Optional[str]):
    """
    Resolve an event's promotion via the KNOWN_PROMOTIONS registry.
    Returns the Promotion or None.
    """
    from .linking import KNOWN_PROMOTIONS, _get_or_create_promotion_stub

    if promo_wiki_link and promo_wiki_link in KNOWN_PROMOTIONS:
        return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[promo_wiki_link], promo_wiki_link)
    if promo_name and promo_name in KNOWN_PROMOTIONS:
        return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[promo_name], promo_name)
    # Also try acronyms inside the display string (e.g., "World Wrestling Entertainment (WWE)")
    if promo_name:
        for key in (promo_name.split("(")[0].strip(), promo_name.split()[0]):
            if key in KNOWN_PROMOTIONS:
                return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[key], key)
    return None


def persist_event(
    candidate_name: str,
    fields: EventFields,
    source_fetch: SourceFetch,
) -> Optional[EventPersistResult]:
    """
    Persist an Event with provenance. Skips if the promotion can't be
    resolved (Event.promotion is a required FK).
    """
    from owdb_django.owdbapp.models import Event

    name_snip = fields.name
    canonical_name = (
        str(name_snip.value).strip() if name_snip is not None else candidate_name.strip()
    )
    if not canonical_name or fields.date is None:
        logger.info("persist_event: missing name or date for %r — skipping", candidate_name)
        return None

    promotion = _resolve_promotion_for_event(
        fields.promotion_wiki_link.value if fields.promotion_wiki_link else None,
        fields.promotion_name.value if fields.promotion_name else None,
    )
    if promotion is None:
        logger.info("persist_event: unresolved promotion for %r — skipping", canonical_name)
        return None

    event_date = fields.date.value
    slug_base = f"{canonical_name}-{event_date.year}"
    slug = slugify(slug_base)[:255]

    with transaction.atomic():
        # Lookup priority: source_fetch.entity_id, slug, (promotion+name+date).
        event = None
        if source_fetch.entity_id:
            event = Event.objects.filter(id=source_fetch.entity_id).first()
        if event is None:
            event = Event.objects.filter(slug=slug).first()
        if event is None:
            event = Event.objects.filter(
                promotion=promotion, name=canonical_name, date=event_date,
            ).first()
        created = False
        if event is None:
            event = Event.objects.create(
                name=canonical_name, slug=slug, promotion=promotion, date=event_date,
            )
            created = True

        fields_written: list[str] = []
        provenance_rows = 0

        # Venue resolution (best-effort)
        venue = _ensure_venue_stub_from_wiki(
            fields.venue_wiki_link.value if fields.venue_wiki_link else None,
            fields.venue_name.value if fields.venue_name else None,
            source_fetch=source_fetch,
        )
        if venue and event.venue_id != venue.id:
            event.venue = venue
            fields_written.append("venue")

        # Attendance
        if fields.attendance and not event.attendance:
            event.attendance = fields.attendance.value
            fields_written.append("attendance")

        # Provenance entries for every captured field.
        for src_attr in ("name", "date", "venue_name", "venue_wiki_link",
                         "promotion_name", "promotion_wiki_link", "attendance"):
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            record_provenance(
                entity_type="event", entity_id=event.id,
                field_name=src_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not getattr(event, "wikipedia_url", None):
            # Event model doesn't have wikipedia_url; we link via source_fetch.url
            pass

        _apply_contract("event", event, source_fetch)
        event.save()

        if source_fetch.entity_id != event.id:
            source_fetch.entity_type = "event"
            source_fetch.entity_id = event.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    logger.info(
        "Persisted event %r (id=%d, created=%s, promotion=%s, venue=%s)",
        canonical_name, event.id, created,
        promotion.name if promotion else None,
        venue.name if venue else None,
    )

    # Extract mentions so the auto-discovery cycle can pull in linked
    # entities (other wrestlers, related events, other venues).
    try:
        from .mentions import persist_mentions_for_entity
        persist_mentions_for_entity("event", event.id, source_fetch)
    except Exception as e:
        logger.exception("Event mention extraction failed: %s", e)

    return EventPersistResult(
        event_id=event.id, created=created,
        venue_id=venue.id if venue else None,
        promotion_id=promotion.id if promotion else None,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
    )
