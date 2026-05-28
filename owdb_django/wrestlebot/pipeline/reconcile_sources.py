"""
Cross-source reconciliation: when an entity has FieldProvenance entries from
more than one source, compare them. Agreement boosts confidence; disagreement
gets surfaced as a consistency issue.

The Wikipedia-only first-write-wins logic in persist.py never overrides a
value once it's set, so this module's job is purely about *measuring*
agreement, not picking a winner. We track:

  - Agreements: distinct sources reported the same value -> mark the
    primary FieldProvenance's confidence as 100 (already is), and log a
    'cross_source_verify' WrestleBotActivity for visibility.
  - Disagreements: distinct sources reported different values -> log a
    'cross_source_disagreement' issue. The wb_audit command will flag
    these for human review.

For v3.0 we treat field types like so:
  - Exact-equality (after normalisation): birth_date, death_date,
    debut_year, retirement_year, height, weight.
  - Fuzzy-equality (substring/word-set match): real_name, hometown,
    nationality.
  - Set-equality (treating comma-separated lists as sets): aliases,
    finishers, trained_by, signature_moves.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# Field-type buckets dictate the comparator used.
EXACT_FIELDS = {
    "birth_date",
    "death_date",
    "debut_year",
    "retirement_year",
    "height",
    "weight",
}
FUZZY_FIELDS = {"real_name", "hometown", "nationality"}
SET_FIELDS = {"aliases", "finishers", "trained_by", "signature_moves"}


@dataclass
class FieldReconcile:
    field_name: str
    sources: list[str]
    values: list[str]
    status: str  # "agree" | "disagree" | "single_source"


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _exact_eq(a: str, b: str) -> bool:
    return _normalize(a) == _normalize(b)


def _fuzzy_eq(a: str, b: str) -> bool:
    """Token-subset match: every token in the shorter value appears in the longer."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    tokens_a = set(re.findall(r"\w+", na))
    tokens_b = set(re.findall(r"\w+", nb))
    if not tokens_a or not tokens_b:
        return False
    smaller, larger = (
        (tokens_a, tokens_b) if len(tokens_a) <= len(tokens_b) else (tokens_b, tokens_a)
    )
    return smaller.issubset(larger)


def _set_eq(a: str, b: str) -> bool:
    """Treat each value as a comma-separated set; check for non-empty intersection."""
    items_a = {_normalize(x) for x in (a or "").split(",") if x.strip()}
    items_b = {_normalize(x) for x in (b or "").split(",") if x.strip()}
    if not items_a or not items_b:
        return False
    return bool(items_a & items_b)


def _comparator_for(field: str):
    if field in EXACT_FIELDS:
        return _exact_eq
    if field in FUZZY_FIELDS:
        return _fuzzy_eq
    if field in SET_FIELDS:
        return _set_eq
    # Unknown field type: fall back to exact (safest).
    return _exact_eq


def reconcile_field_provenance(entity_type: str, entity_id: int) -> dict:
    """
    Compare FieldProvenance rows across sources for one entity.

    Returns {
        "fields_checked": N,
        "agreements": [FieldReconcile, ...],
        "disagreements": [FieldReconcile, ...],
        "single_source": M,
    }.

    Side effects:
      - Logs each disagreement as a WrestleBotActivity (action=error,
        source=cross_source_disagreement).
      - Logs each agreement (action=verify, source=cross_source_verify).
    """
    from ..models import FieldProvenance, WrestleBotActivity

    by_field: dict[str, list[FieldProvenance]] = defaultdict(list)
    qs = (
        FieldProvenance.objects.filter(entity_type=entity_type, entity_id=entity_id)
        .select_related("source_fetch")
        .order_by("field_name", "extracted_at")
    )
    for p in qs:
        by_field[p.field_name].append(p)

    agreements: list[FieldReconcile] = []
    disagreements: list[FieldReconcile] = []
    single_source = 0

    entity_name = _entity_name(entity_type, entity_id)

    for field_name, provs in by_field.items():
        # Latest value per source. Reconcile across distinct sources only.
        latest_per_source: dict[str, FieldProvenance] = {}
        for p in provs:
            src = p.source_fetch.source
            # Keep the latest (extracted_at descending was reversed by the
            # ascending order_by above, so the *last* iteration is the newest).
            latest_per_source[src] = p

        if len(latest_per_source) < 2:
            single_source += 1
            continue

        sources = sorted(latest_per_source.keys())
        values = [latest_per_source[s].value for s in sources]

        comparator = _comparator_for(field_name)
        # All pairs must agree for the field to be "agree".
        all_pairs_agree = True
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                if not comparator(values[i], values[j]):
                    all_pairs_agree = False
                    break
            if not all_pairs_agree:
                break

        record = FieldReconcile(
            field_name=field_name,
            sources=sources,
            values=values,
            status=("agree" if all_pairs_agree else "disagree"),
        )

        if all_pairs_agree:
            agreements.append(record)
            # Side effect: confidence stays 100; log a verify event.
            WrestleBotActivity.objects.create(
                action_type="verify",
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name or f"{entity_type}#{entity_id}",
                source="cross_source_verify",
                details={
                    "field": field_name,
                    "sources": sources,
                    "value": values[0],
                },
                ai_assisted=False,
                success=True,
            )
        else:
            disagreements.append(record)
            WrestleBotActivity.objects.create(
                action_type="error",
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name or f"{entity_type}#{entity_id}",
                source="cross_source_disagreement",
                details={
                    "field": field_name,
                    "sources": sources,
                    "values": dict(zip(sources, values)),
                },
                ai_assisted=False,
                success=False,
                error_message=(
                    f"Cross-source disagreement on {field_name}: "
                    + ", ".join(f"{s}={v!r}" for s, v in zip(sources, values))
                )[:1000],
            )

    return {
        "fields_checked": len(by_field),
        "agreements": agreements,
        "disagreements": disagreements,
        "single_source": single_source,
    }


def _entity_name(entity_type: str, entity_id: int) -> Optional[str]:
    """Look up the entity's display name for activity log readability."""
    if entity_type == "wrestler":
        from owdb_django.owdbapp.models import Wrestler

        w = Wrestler.objects.filter(id=entity_id).only("name").first()
        return w.name if w else None
    if entity_type == "promotion":
        from owdb_django.owdbapp.models import Promotion

        p = Promotion.objects.filter(id=entity_id).only("name").first()
        return p.name if p else None
    return None
