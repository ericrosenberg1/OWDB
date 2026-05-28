"""
Persist stage — write extracted fields to entity tables + FieldProvenance.

Policy (v3.0):
- Entity is looked up by name (case-insensitive slug match). Created if absent.
- For each extracted field:
    - If the entity field is empty/null, write the new value.
    - If the entity field is already set, keep existing (first-write-wins).
      We still record a FieldProvenance row so we can see the candidate value
      from this newer source for later reconciliation.
- A SourceFetch row is linked to the entity (entity_id set) regardless.
- The entity's `verified=True` is set if any field write succeeded, with
  `verification_source` = the source name and `last_verified` = now.

Why first-write-wins for v3.0: it keeps the very first end-to-end test simple
and verifiable. Cross-source reconciliation comes in v3.1 once we have more
than one adapter wired up.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from ..models import FieldProvenance, SourceFetch
from ..sources.base import WrestlerFields
from ._provenance import record_provenance

logger = logging.getLogger(__name__)


# Map of WrestlerFields attribute name -> Wrestler model attribute name.
# Most map 1:1; we keep this explicit so we never accidentally write to a
# field we didn't extract.
WRESTLER_FIELD_MAP: dict[str, str] = {
    "name": "name",
    "real_name": "real_name",
    "aliases": "aliases",
    "birth_date": "birth_date",
    "death_date": "death_date",
    "debut_year": "debut_year",
    "retirement_year": "retirement_year",
    "nationality": "nationality",
    "hometown": "hometown",
    "height": "height",
    "weight": "weight",
    "finishers": "finishers",
    "signature_moves": "signature_moves",
    "trained_by": "trained_by",
    "roles": "roles",
}


@dataclass
class PersistResult:
    """Summary of what one persist call did."""

    wrestler_id: int
    created: bool
    fields_written: list[str]
    fields_skipped: list[str]
    provenance_rows_created: int


_DISAMBIG_SUFFIX_RE = re.compile(
    r"\s*\((?:wrestler|wrestling|professional\s+wrestler|"
    r"professional\s+wrestling|professional\s+wrestling\s+stable|"
    r"professional\s+wrestling\s+championship|"
    r"professional\s+wrestling\s+tag\s+team|"
    r"disambiguation|"
    r"American\s+wrestler|woman\s+wrestler|tag\s+team|stable|"
    r"championship)\)\s*$",
    re.IGNORECASE,
)


def _strip_disambig(name: str) -> str:
    """
    Remove Wikipedia disambiguation suffixes like '(wrestler)' or
    '(disambiguation)' from a name. These are page-title artifacts; the
    actual person's name doesn't include them.
    """
    cleaned = _DISAMBIG_SUFFIX_RE.sub("", name).strip()
    return cleaned or name  # never return empty


def persist_wrestler(
    candidate_name: str,
    fields: WrestlerFields,
    source_fetch: SourceFetch,
) -> Optional[PersistResult]:
    """
    Idempotent: writes the entity + provenance rows in one transaction.

    Returns None if the candidate is unusable (e.g., empty name).
    """
    # Late import to avoid Django app-loading issues.
    from owdb_django.owdbapp.models import Wrestler

    # Best name for the entity. Priority order:
    #   1. `best_known_as` (when the Wikipedia adapter detected a "better
    #      known as X" phrase in the article's lede, or stripped a disambig
    #      suffix). This is the display name fans actually use — e.g.
    #      "Mr. Perfect" rather than the article title "Curt Hennig".
    #   2. The infobox-extracted `name` field.
    #   3. The original candidate name that was queued for fetching.
    used_best_known = False
    if fields.best_known_as is not None:
        canonical_name = str(fields.best_known_as.value).strip()
        used_best_known = True
    elif fields.name is not None:
        canonical_name = str(fields.name.value).strip()
    else:
        canonical_name = candidate_name.strip()
    if not canonical_name:
        return None

    # Strip Wikipedia disambiguation suffixes — they aren't part of the
    # wrestler's actual name, and they break exact-match lookups (e.g.,
    # trained_by="Pat Patterson" failing to match Wrestler.name="Pat Patterson (wrestler)").
    canonical_name = _strip_disambig(canonical_name)

    slug = slugify(canonical_name)[:255]

    with transaction.atomic():
        wrestler = None
        created = False

        # First try: match by an existing entity already linked to this
        # exact SourceFetch (re-extracts of the same fetch should be idempotent).
        if source_fetch.entity_id:
            wrestler = Wrestler.objects.filter(id=source_fetch.entity_id).first()

        # Second try: match by Wikipedia URL if the fetch came from wikipedia
        # OR by the candidate_name's slug — covers cross-validation sources
        # that arrive after the canonical wikipedia persist.
        if wrestler is None and source_fetch.candidate_name:
            cand_slug = slugify(_strip_disambig(source_fetch.candidate_name))[:255]
            if cand_slug:
                wrestler = Wrestler.objects.filter(slug=cand_slug).first()

        # Third try: the standard slug-of-canonical-name path.
        if wrestler is None:
            wrestler = Wrestler.objects.filter(slug=slug).first()

        # Fall back to creating a new wrestler.
        if wrestler is None:
            wrestler = Wrestler.objects.create(name=canonical_name, slug=slug)
            created = True

        fields_written: list[str] = []
        fields_skipped: list[str] = []
        provenance_rows = 0

        # Always record FieldProvenance for `name` so the wrestler can
        # pass the accuracy contract (codex round-2 audit: contract was
        # checking name, persist never recorded it). When best_known_as
        # drove the canonical_name choice, attach the lede snippet that
        # supports it as evidence — much stronger than the degenerate
        # "snippet = the name itself" fallback we use otherwise.
        existing_name_prov = FieldProvenance.objects.filter(
            entity_type="wrestler",
            entity_id=wrestler.id,
            field_name="name",
        ).exists()
        if not existing_name_prov:
            if used_best_known and fields.best_known_as is not None:
                name_snippet = getattr(fields.best_known_as, "snippet", "") or wrestler.name
                name_confidence = fields.best_known_as.confidence
            else:
                name_snippet = wrestler.name
                name_confidence = 95  # name from a Wikipedia article title
            record_provenance(
                entity_type="wrestler",
                entity_id=wrestler.id,
                field_name="name",
                value=wrestler.name,
                source_fetch=source_fetch,
                snippet=name_snippet,
                confidence=name_confidence,
            )
            provenance_rows += 1

        for src_attr, dst_attr in WRESTLER_FIELD_MAP.items():
            snip = getattr(fields, src_attr)
            if snip is None:
                continue

            current = getattr(wrestler, dst_attr, None)
            new_value = snip.value
            # Treat empty string as unset for char/text fields.
            is_empty = current in (None, "", b"")

            if is_empty:
                setattr(wrestler, dst_attr, new_value)
                fields_written.append(dst_attr)
            else:
                fields_skipped.append(dst_attr)
                # Source-drift detection: source now disagrees with the value
                # we previously persisted. We don't auto-overwrite (accuracy-
                # first, no silent updates) but we DO log it for human review.
                if str(current).strip() != str(new_value).strip():
                    _log_source_drift(wrestler, dst_attr, current, new_value, source_fetch)

            # Always record provenance for the value we observed from this source.
            record_provenance(
                entity_type="wrestler",
                entity_id=wrestler.id,
                field_name=dst_attr,
                value=new_value,
                source_fetch=source_fetch,
                snippet=getattr(snip, "snippet", "") or "",
                confidence=snip.confidence,
            )
            provenance_rows += 1

        # Stamp source URL on the entity if not already set (helps the
        # in-app "source link" without joining FieldProvenance).
        if source_fetch.source == "wikipedia" and not wrestler.wikipedia_url:
            wrestler.wikipedia_url = source_fetch.url[:500]
        elif source_fetch.source == "cagematch" and not wrestler.cagematch_url:
            wrestler.cagematch_url = source_fetch.url[:500]
        elif source_fetch.source == "profightdb" and not wrestler.profightdb_url:
            wrestler.profightdb_url = source_fetch.url[:500]

        # Mark verified if any field write succeeded.
        if fields_written:
            wrestler.verified = True
            if not wrestler.verification_source:
                wrestler.verification_source = source_fetch.source
            wrestler.last_verified = timezone.now()

        wrestler.last_enriched = timezone.now()
        wrestler.save()

        # Set verification_state per the accuracy contract. The save above
        # must commit first so accuracy_contract.is_satisfied sees the
        # provenance rows we just wrote.
        from .accuracy_contract import enforce

        new_state, _ = enforce("wrestler", wrestler)
        if wrestler.verification_state != new_state:
            wrestler.verification_state = new_state
            wrestler.save(update_fields=["verification_state"])

        # Link the source fetch to the entity now that we know the id.
        if source_fetch.entity_id != wrestler.id:
            source_fetch.entity_type = "wrestler"
            source_fetch.entity_id = wrestler.id
            source_fetch.save(update_fields=["entity_type", "entity_id"])

    logger.info(
        "Persisted wrestler %r (id=%d, created=%s, wrote=%s, skipped=%s)",
        canonical_name,
        wrestler.id,
        created,
        fields_written,
        fields_skipped,
    )

    # Side effects beyond field writes — wired here so wb_extract runs them too.
    _post_persist_side_effects(wrestler, source_fetch)

    return PersistResult(
        wrestler_id=wrestler.id,
        created=created,
        fields_written=fields_written,
        fields_skipped=fields_skipped,
        provenance_rows_created=provenance_rows,
    )


def _log_source_drift(
    wrestler, field_name: str, current_value, new_value, source_fetch: SourceFetch
) -> None:
    """
    Wikipedia (or another source) now reports a different value than what
    we previously stored. We deliberately do NOT auto-update — instead log
    a 'source_drift' WrestleBotActivity so a human can review and reconcile.

    This is intentional: silently changing existing data violates the
    accuracy-first contract. The drift surfaces in wb_audit; a maintainer
    can then decide which value is correct.
    """
    try:
        from ..models import WrestleBotActivity

        WrestleBotActivity.objects.create(
            action_type="error",
            entity_type="wrestler",
            entity_id=wrestler.id,
            entity_name=wrestler.name,
            source="source_drift",
            details={
                "field": field_name,
                "stored_value": str(current_value)[:200],
                "new_source_value": str(new_value)[:200],
                "new_source": source_fetch.source,
                "new_source_url": source_fetch.url[:300],
            },
            ai_assisted=False,
            success=False,
            error_message=(
                f"Source drift on {field_name}: stored={current_value!r:.80} "
                f"new={new_value!r:.80} ({source_fetch.source})"
            )[:1000],
        )
        logger.warning(
            "Source drift on Wrestler#%d.%s: %r -> %r (%s)",
            wrestler.id,
            field_name,
            current_value,
            new_value,
            source_fetch.source,
        )
    except Exception as e:
        logger.debug("Couldn't log source drift: %s", e)


def _post_persist_side_effects(wrestler, source_fetch: SourceFetch) -> None:
    """
    Cheap post-persist work: clean fields, extract mentions, link promotions,
    run consistency checks. Each step is best-effort — failures are logged
    but don't unwind the persist transaction.
    """
    # 1. Field cleanup — strip artifacts from text fields BEFORE downstream
    # checks see them (consistency rules look at the cleaned values).
    try:
        from .cleanup import apply_wrestler_cleanup

        changes = apply_wrestler_cleanup(wrestler)
        if changes:
            logger.info("Cleaned wrestler#%d fields: %s", wrestler.id, list(changes.keys()))
    except Exception as e:
        logger.exception("Field cleanup failed for Wrestler#%d: %s", wrestler.id, e)

    # 1b. Extract external-source URLs (cagematch, profightdb) from the
    # Wikipedia source so the next pipeline cycle can cross-validate.
    if source_fetch.source == "wikipedia":
        try:
            from .external_links import apply_external_links_to_wrestler

            ext = apply_external_links_to_wrestler(wrestler, source_fetch.raw_content)
            if ext:
                logger.info(
                    "Picked up external links for wrestler#%d: %s", wrestler.id, list(ext.keys())
                )
        except Exception as e:
            logger.exception("External-link extraction failed for Wrestler#%d: %s", wrestler.id, e)

    # 2. EntityMention extraction
    try:
        from .mentions import persist_mentions_for_wrestler

        persist_mentions_for_wrestler(wrestler.id, source_fetch)
    except Exception as e:
        logger.exception("Mention extraction failed for Wrestler#%d: %s", wrestler.id, e)

    # 3. Resolve mentions -> Promotion stubs + WrestlerPromotionHistory
    try:
        from .linking import resolve_wrestler_mentions_to_promotions

        result = resolve_wrestler_mentions_to_promotions(wrestler.id)
        if result["linked"]:
            logger.info(
                "Linked Wrestler#%d to %d promotion(s)",
                wrestler.id,
                result["linked"],
            )
    except Exception as e:
        logger.exception("Promotion linking failed for Wrestler#%d: %s", wrestler.id, e)

    # 4. Resolve mentions to existing wrestlers (Round 4)
    try:
        from .linking import resolve_wrestler_mentions_to_wrestlers

        wresult = resolve_wrestler_mentions_to_wrestlers(wrestler.id)
        if wresult["resolved"]:
            logger.info(
                "Linked Wrestler#%d to %d other wrestler mention(s)",
                wrestler.id,
                wresult["resolved"],
            )
    except Exception as e:
        logger.exception("Wrestler-mention resolution failed for Wrestler#%d: %s", wrestler.id, e)

    # 5. Trained-by trainer links (Round 4)
    try:
        from .linking import link_trainers_for_wrestler

        tresult = link_trainers_for_wrestler(wrestler)
        if tresult["linked"]:
            logger.info(
                "Linked Wrestler#%d to %d trainer(s)",
                wrestler.id,
                tresult["linked"],
            )
    except Exception as e:
        logger.exception("Trainer linking failed for Wrestler#%d: %s", wrestler.id, e)

    # 6. Consistency checks
    try:
        from .consistency import check_wrestler, log_issues, lower_confidence_for_issues

        issues = check_wrestler(wrestler)
        if issues:
            log_issues("wrestler", wrestler.id, wrestler.name, issues)
            lower_confidence_for_issues("wrestler", wrestler.id, issues)
    except Exception as e:
        logger.exception("Consistency check failed for Wrestler#%d: %s", wrestler.id, e)

    # 7. Cross-source reconcile — only meaningful when 2+ sources have
    # contributed to this wrestler's FieldProvenance rows. Cheap to run.
    try:
        from .reconcile_sources import reconcile_field_provenance

        rec = reconcile_field_provenance("wrestler", wrestler.id)
        if rec["agreements"] or rec["disagreements"]:
            logger.info(
                "Cross-source reconcile for Wrestler#%d: %d agreement(s), %d disagreement(s)",
                wrestler.id,
                len(rec["agreements"]),
                len(rec["disagreements"]),
            )
    except Exception as e:
        logger.exception("Cross-source reconcile failed for Wrestler#%d: %s", wrestler.id, e)
