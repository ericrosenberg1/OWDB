"""
persist_tv_show + persist_special.

TVShow requires a Promotion (FK). Specials don't (no promotion-tied requirement).
Both auto-link mentioned wrestlers via EntityMention resolution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import FieldProvenance, SourceFetch
from ..sources.base import SpecialFields, TVShowFields
from . import accuracy_contract
from ._provenance import record_provenance

logger = logging.getLogger(__name__)


def _apply_contract(entity_type: str, entity, source_fetch: SourceFetch):
    """Same helper as persist_event._apply_contract — keep them in sync."""
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


TV_SHOW_FIELD_MAP = {
    "name": "name",
    "network": "network",
}

SPECIAL_FIELD_MAP = {
    "title": "title",
    "release_year": "release_year",
    "type": "type",
    "director": "director",
}


@dataclass
class TVShowPersistResult:
    tv_show_id: int
    created: bool
    promotion_id: Optional[int]
    fields_written: list[str]
    provenance_rows_created: int


@dataclass
class SpecialPersistResult:
    special_id: int
    created: bool
    fields_written: list[str]
    provenance_rows_created: int
    linked_wrestlers: int


def persist_tv_show(
    candidate_name: str,
    fields: TVShowFields,
    source_fetch: SourceFetch,
) -> Optional[TVShowPersistResult]:
    from owdb_django.owdbapp.models import TVShow
    from .persist_title import _resolve_promotion

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None

    promotion = _resolve_promotion(
        fields.promotion_wiki_link.value if fields.promotion_wiki_link else None,
        fields.promotion_name.value if fields.promotion_name else None,
    )
    if promotion is None:
        logger.info("persist_tv_show: unresolved promotion for %r — skipping", canonical_name)
        return None

    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        tv = None
        if source_fetch.entity_id:
            tv = TVShow.objects.filter(id=source_fetch.entity_id).first()
        if tv is None:
            tv = TVShow.objects.filter(slug=slug).first()
        created = False
        if tv is None:
            tv = TVShow.objects.create(
                name=canonical_name, slug=slug, promotion=promotion,
            )
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in TV_SHOW_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(tv, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(tv, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="tv_show", entity_id=tv.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if fields.premiere_year is not None and tv.premiere_date is None:
            from datetime import date as _date
            tv.premiere_date = _date(fields.premiere_year.value, 1, 1)
            fields_written.append("premiere_date")
            record_provenance(
                entity_type="tv_show", entity_id=tv.id,
                field_name="premiere_year", value=fields.premiere_year.value,
                source_fetch=source_fetch, confidence=fields.premiere_year.confidence,
                snippet=getattr(fields.premiere_year, "snippet", "") or "",
            )
            provenance_rows += 1
        if fields.finale_year is not None and tv.finale_date is None:
            from datetime import date as _date
            tv.finale_date = _date(fields.finale_year.value, 12, 31)
            fields_written.append("finale_date")
            record_provenance(
                entity_type="tv_show", entity_id=tv.id,
                field_name="finale_year", value=fields.finale_year.value,
                source_fetch=source_fetch, confidence=fields.finale_year.confidence,
                snippet=getattr(fields.finale_year, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not tv.wikipedia_url:
            tv.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        tv.last_enriched = timezone.now()
        _apply_contract("tv_show", tv, source_fetch)
        tv.save()

        if source_fetch.entity_id != tv.id:
            source_fetch.entity_type = "tv_show"
            source_fetch.entity_id = tv.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    try:
        from .mentions import persist_mentions_for_entity
        persist_mentions_for_entity("tv_show", tv.id, source_fetch)
    except Exception as e:
        logger.exception("TVShow mention extraction failed: %s", e)

    logger.info(
        "Persisted tv_show %r (id=%d, created=%s, promotion=%s, wrote=%s)",
        canonical_name, tv.id, created, promotion.name, fields_written,
    )
    return TVShowPersistResult(
        tv_show_id=tv.id, created=created, promotion_id=promotion.id,
        fields_written=fields_written, provenance_rows_created=provenance_rows,
    )


def persist_special(
    candidate_name: str,
    fields: SpecialFields,
    source_fetch: SourceFetch,
) -> Optional[SpecialPersistResult]:
    from owdb_django.owdbapp.models import Special

    canonical_title = (
        str(fields.title.value).strip() if fields.title is not None else candidate_name.strip()
    )
    if not canonical_title:
        return None
    slug = slugify(canonical_title)[:255]

    with transaction.atomic():
        sp = None
        if source_fetch.entity_id:
            sp = Special.objects.filter(id=source_fetch.entity_id).first()
        if sp is None:
            sp = Special.objects.filter(slug=slug).first()
        created = False
        if sp is None:
            sp = Special.objects.create(title=canonical_title, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in SPECIAL_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(sp, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(sp, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="special", entity_id=sp.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not sp.wikipedia_url:
            sp.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        # `special` has no formal entry in CONTRACTS yet; accuracy_contract
        # returns PROVISIONAL for unknown types, which is correct here —
        # better than an unconditional `verified=True`.
        sp.last_enriched = timezone.now()
        _apply_contract("special", sp, source_fetch)
        sp.save()

        if source_fetch.entity_id != sp.id:
            source_fetch.entity_type = "special"
            source_fetch.entity_id = sp.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    # Cross-link mentioned wrestlers to related_wrestlers M2M
    linked = 0
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        from ..models import EntityMention
        from owdb_django.owdbapp.models import Wrestler
        persist_mentions_for_entity("special", sp.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
        for m in EntityMention.objects.filter(
            source_fetch=source_fetch, resolved_entity_type="wrestler",
        ):
            try:
                w = Wrestler.objects.get(id=m.resolved_entity_id)
            except Wrestler.DoesNotExist:
                continue
            if not sp.related_wrestlers.filter(id=w.id).exists():
                sp.related_wrestlers.add(w)
                linked += 1
    except Exception as e:
        logger.exception("Special wrestler linking failed: %s", e)

    logger.info(
        "Persisted special %r (id=%d, created=%s, wrote=%s, wrestlers=%d)",
        canonical_title, sp.id, created, fields_written, linked,
    )
    return SpecialPersistResult(
        special_id=sp.id, created=created,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_wrestlers=linked,
    )
