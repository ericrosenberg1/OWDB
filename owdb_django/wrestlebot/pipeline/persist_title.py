"""
persist_title + persist_stable.

Both need a Promotion to attach to (Title.promotion is required FK).
Stables also auto-link members + leaders to Wrestler rows by name match.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import SourceFetch
from ..sources.base import StableFields, TitleFields, TrainingSchoolFields
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


TITLE_FIELD_MAP = {
    "name": "name",
    "debut_year": "debut_year",
    "retirement_year": "retirement_year",
    "title_type": "title_type",
}

STABLE_FIELD_MAP = {
    "name": "name",
    "formed_year": "formed_year",
    "disbanded_year": "disbanded_year",
}


@dataclass
class TitlePersistResult:
    title_id: int
    created: bool
    promotion_id: Optional[int]
    fields_written: list[str]
    provenance_rows_created: int


@dataclass
class StablePersistResult:
    stable_id: int
    created: bool
    promotion_id: Optional[int]
    fields_written: list[str]
    provenance_rows_created: int
    linked_members: int
    linked_leaders: int


# ----------------------------------------------------------------- titles


def _resolve_promotion(promo_wiki_link: Optional[str], promo_name: Optional[str]):
    """Resolve a promotion from KNOWN_PROMOTIONS — same logic as event persist."""
    from .linking import KNOWN_PROMOTIONS, _get_or_create_promotion_stub
    if promo_wiki_link and promo_wiki_link in KNOWN_PROMOTIONS:
        return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[promo_wiki_link], promo_wiki_link)
    if promo_name and promo_name in KNOWN_PROMOTIONS:
        return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[promo_name], promo_name)
    if promo_name:
        for key in (promo_name.split("(")[0].strip(), promo_name.split()[0]):
            if key in KNOWN_PROMOTIONS:
                return _get_or_create_promotion_stub(KNOWN_PROMOTIONS[key], key)
    return None


def persist_title(
    candidate_name: str,
    fields: TitleFields,
    source_fetch: SourceFetch,
) -> Optional[TitlePersistResult]:
    """Persist a Title. Requires a resolvable promotion (FK is non-null)."""
    from owdb_django.owdbapp.models import Title

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
        logger.info("persist_title: unresolved promotion for %r — skipping", canonical_name)
        return None

    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        title = None
        if source_fetch.entity_id:
            title = Title.objects.filter(id=source_fetch.entity_id).first()
        if title is None:
            title = Title.objects.filter(slug=slug).first()
        if title is None:
            title = Title.objects.filter(name=canonical_name, promotion=promotion).first()
        created = False
        if title is None:
            title = Title.objects.create(
                name=canonical_name, slug=slug, promotion=promotion,
            )
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in TITLE_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(title, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(title, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="title", entity_id=title.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        # Contract requires a `promotion` provenance row too. The
        # promotion-FK was resolved from `promotion_name` /
        # `promotion_wiki_link` snippets above; record a synthetic row
        # so the contract sees the required field as covered.
        promo_snip = fields.promotion_wiki_link or fields.promotion_name
        record_provenance(
            entity_type="title", entity_id=title.id,
            field_name="promotion", value=promotion.name,
            source_fetch=source_fetch,
            snippet=(getattr(promo_snip, "snippet", "") if promo_snip else "")
                    or f"resolved via KNOWN_PROMOTIONS[{promotion.abbreviation!r}]",
            confidence=getattr(promo_snip, "confidence", 90) if promo_snip else 90,
        )
        provenance_rows += 1

        if source_fetch.source == "wikipedia" and not title.wikipedia_url:
            title.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        title.last_enriched = timezone.now()
        _apply_contract("title", title, source_fetch)
        title.save()

        if source_fetch.entity_id != title.id:
            source_fetch.entity_type = "title"
            source_fetch.entity_id = title.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    # Mentions extraction
    try:
        from .mentions import persist_mentions_for_entity
        persist_mentions_for_entity("title", title.id, source_fetch)
    except Exception as e:
        logger.exception("Title mention extraction failed: %s", e)

    logger.info(
        "Persisted title %r (id=%d, created=%s, promotion=%s, wrote=%s)",
        canonical_name, title.id, created, promotion.name, fields_written,
    )
    return TitlePersistResult(
        title_id=title.id, created=created,
        promotion_id=promotion.id,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
    )


# ----------------------------------------------------------------- stables


def _link_wrestler_names(wiki_link_csv: Optional[str]) -> list:
    """Resolve a comma-separated list of wiki titles to Wrestler rows."""
    from owdb_django.owdbapp.models import Wrestler
    if not wiki_link_csv:
        return []
    names = [n.strip() for n in str(wiki_link_csv).split(",") if n.strip()]
    out = []
    for name in names:
        w = Wrestler.objects.filter(name=name).first() or Wrestler.objects.filter(name__iexact=name).first()
        if w is not None and w not in out:
            out.append(w)
    return out


def persist_stable(
    candidate_name: str,
    fields: StableFields,
    source_fetch: SourceFetch,
) -> Optional[StablePersistResult]:
    """Persist a Stable. Promotion is nullable; members + leaders linked from wiki titles."""
    from owdb_django.owdbapp.models import Stable

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None

    promotion = _resolve_promotion(
        fields.promotion_wiki_link.value if fields.promotion_wiki_link else None,
        fields.promotion_name.value if fields.promotion_name else None,
    )

    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        stable = None
        if source_fetch.entity_id:
            stable = Stable.objects.filter(id=source_fetch.entity_id).first()
        if stable is None:
            stable = Stable.objects.filter(slug=slug).first()
        created = False
        if stable is None:
            stable = Stable.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in STABLE_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(stable, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(stable, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="stable", entity_id=stable.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if promotion is not None and stable.promotion_id != promotion.id:
            stable.promotion = promotion
            fields_written.append("promotion")
            # Provenance row for the resolved promotion FK so Earl's
            # rules can see where this link came from.
            promo_snip = fields.promotion_wiki_link or fields.promotion_name
            record_provenance(
                entity_type="stable", entity_id=stable.id,
                field_name="promotion", value=promotion.name,
                source_fetch=source_fetch,
                snippet=(getattr(promo_snip, "snippet", "") if promo_snip else "")
                        or f"resolved via KNOWN_PROMOTIONS[{promotion.abbreviation!r}]",
                confidence=getattr(promo_snip, "confidence", 90) if promo_snip else 90,
            )
            provenance_rows += 1

        if source_fetch.source == "wikipedia" and not stable.wikipedia_url:
            stable.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        stable.last_enriched = timezone.now()
        _apply_contract("stable", stable, source_fetch)
        stable.save()

        if source_fetch.entity_id != stable.id:
            source_fetch.entity_type = "stable"
            source_fetch.entity_id = stable.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

        # Link members + leaders from infobox wiki titles
        linked_members = 0
        for w in _link_wrestler_names(
            fields.member_wiki_links.value if fields.member_wiki_links else None
        ):
            if not stable.members.filter(id=w.id).exists():
                stable.members.add(w)
                linked_members += 1
        linked_leaders = 0
        for w in _link_wrestler_names(
            fields.leader_wiki_links.value if fields.leader_wiki_links else None
        ):
            if not stable.leaders.filter(id=w.id).exists():
                stable.leaders.add(w)
                linked_leaders += 1
            # Leaders are also implicit members
            if not stable.members.filter(id=w.id).exists():
                stable.members.add(w)
                linked_members += 1

    # Mentions extraction (for cross-link graph), but DO NOT auto-add
    # prose-mentioned wrestlers as members — only the infobox "Members" /
    # "Leader(s)" cells are reliable source for stable membership. Prose
    # mentions a stable's enemies, allies, and bystanders alongside actual
    # members, so persisting them as members would fabricate relationships
    # (D-Generation X's article mentions Undertaker and Kane as opponents,
    # not as members).
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        persist_mentions_for_entity("stable", stable.id, source_fetch)
        # Resolve mentions for the wrestler↔stable mention graph (queryable
        # via EntityMention; not used to populate Stable.members).
        resolve_all_mentions_to_wrestlers()
    except Exception as e:
        logger.exception("Stable mention extraction failed: %s", e)

    logger.info(
        "Persisted stable %r (id=%d, created=%s, promotion=%s, members=%d, leaders=%d)",
        canonical_name, stable.id, created,
        promotion.name if promotion else None,
        linked_members, linked_leaders,
    )
    return StablePersistResult(
        stable_id=stable.id, created=created,
        promotion_id=promotion.id if promotion else None,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_members=linked_members,
        linked_leaders=linked_leaders,
    )


# --------------------------------------------------------- training schools


TRAINING_SCHOOL_FIELD_MAP = {
    "name": "name",
    "location": "location",
    "founded_year": "founded_year",
    "closed_year": "closed_year",
    "founder": "founder",
    "head_trainer": "head_trainer",
}


@dataclass
class TrainingSchoolPersistResult:
    training_school_id: int
    created: bool
    parent_promotion_id: Optional[int]
    fields_written: list[str]
    provenance_rows_created: int
    linked_trainees: int


def persist_training_school(
    candidate_name: str,
    fields: TrainingSchoolFields,
    source_fetch: SourceFetch,
) -> Optional[TrainingSchoolPersistResult]:
    """Persist a TrainingSchool and auto-link mentioned wrestlers as notable trainees."""
    from owdb_django.owdbapp.models import TrainingSchool

    canonical_name = (
        str(fields.name.value).strip() if fields.name is not None else candidate_name.strip()
    )
    if not canonical_name:
        return None

    parent_promotion = _resolve_promotion(
        fields.parent_promotion_wiki_link.value if fields.parent_promotion_wiki_link else None,
        None,
    )

    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        school = None
        if source_fetch.entity_id:
            school = TrainingSchool.objects.filter(id=source_fetch.entity_id).first()
        if school is None:
            school = TrainingSchool.objects.filter(slug=slug).first()
        created = False
        if school is None:
            school = TrainingSchool.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        provenance_rows = 0
        for src_attr, dst_attr in TRAINING_SCHOOL_FIELD_MAP.items():
            snip = getattr(fields, src_attr, None)
            if snip is None:
                continue
            current = getattr(school, dst_attr, None)
            is_empty = current in (None, "", b"")
            if is_empty:
                setattr(school, dst_attr, snip.value)
                fields_written.append(dst_attr)
            record_provenance(
                entity_type="training_school", entity_id=school.id,
                field_name=dst_attr, value=snip.value,
                source_fetch=source_fetch, confidence=snip.confidence,
                snippet=getattr(snip, "snippet", "") or "",
            )
            provenance_rows += 1

        if parent_promotion is not None and school.parent_promotion_id != parent_promotion.id:
            school.parent_promotion = parent_promotion
            fields_written.append("parent_promotion")

        if source_fetch.source == "wikipedia" and not school.wikipedia_url:
            school.wikipedia_url = source_fetch.url[:500]
            fields_written.append("wikipedia_url")

        # training_school has no formal contract entry; accuracy_contract
        # returns PROVISIONAL for unknown types (correct default here).
        school.last_enriched = timezone.now()
        _apply_contract("training_school", school, source_fetch)
        school.save()

        if source_fetch.entity_id != school.id:
            source_fetch.entity_type = "training_school"
            source_fetch.entity_id = school.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    # Cross-link mentioned wrestlers as notable trainees
    linked = 0
    try:
        from .mentions import persist_mentions_for_entity
        from .linking import resolve_all_mentions_to_wrestlers
        from ..models import EntityMention
        from owdb_django.owdbapp.models import Wrestler
        persist_mentions_for_entity("training_school", school.id, source_fetch)
        resolve_all_mentions_to_wrestlers()
        for m in EntityMention.objects.filter(
            source_fetch=source_fetch, resolved_entity_type="wrestler",
        ):
            try:
                w = Wrestler.objects.get(id=m.resolved_entity_id)
            except Wrestler.DoesNotExist:
                continue
            if not school.notable_trainees.filter(id=w.id).exists():
                school.notable_trainees.add(w)
                linked += 1
    except Exception as e:
        logger.exception("TrainingSchool wrestler-linking failed: %s", e)

    logger.info(
        "Persisted training_school %r (id=%d, created=%s, parent=%s, trainees=%d)",
        canonical_name, school.id, created,
        parent_promotion.name if parent_promotion else None, linked,
    )
    return TrainingSchoolPersistResult(
        training_school_id=school.id, created=created,
        parent_promotion_id=parent_promotion.id if parent_promotion else None,
        fields_written=fields_written,
        provenance_rows_created=provenance_rows,
        linked_trainees=linked,
    )
