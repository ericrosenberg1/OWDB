"""
Shared FieldProvenance writer.

Every persist path must use `record_provenance(...)` (or its bulk variant)
to write FieldProvenance rows. Centralising this means:

  1. The schema lie is fixed in one place — every row carries `snippet`.
  2. Future required-field checks live here (accuracy_contract.py).
  3. Bulk paths that don't have a per-field source snippet pass a
     `synthetic_snippet=` and a `confidence` below 100 so Earl can see
     they are reconstructed rather than directly extracted.

Anyone bypassing this and calling `FieldProvenance.objects.create(...)`
directly is a bug — accuracy_contract.audit_persistence() catches it.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def record_provenance(
    *,
    entity_type: str,
    entity_id: int,
    field_name: str,
    value,
    source_fetch,
    snippet: str = "",
    confidence: int = 100,
):
    """
    Insert one FieldProvenance row. Always supply `snippet` — empty string
    only if the source genuinely had no quotable substring (synthetic /
    back-fill paths).

    Returns the created FieldProvenance instance.
    """
    from ..models import FieldProvenance

    return FieldProvenance.objects.create(
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        value=("" if value is None else str(value))[:8000],
        source_fetch=source_fetch,
        snippet=snippet[:8000] if snippet else "",
        confidence=max(0, min(100, int(confidence))),
    )


def record_provenance_from_snippet(
    *,
    entity_type: str,
    entity_id: int,
    field_name: str,
    snip,
    source_fetch,
):
    """
    Convenience helper: derives value/snippet/confidence from a
    FieldSnippet dataclass (see sources/base.py).
    """
    return record_provenance(
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        value=getattr(snip, "value", ""),
        snippet=getattr(snip, "snippet", "") or "",
        confidence=getattr(snip, "confidence", 100),
        source_fetch=source_fetch,
    )


def bulk_synthetic_provenance(
    *,
    entity_type: str,
    entity_id: int,
    field_values: dict,
    source_fetch,
    snippet_hint: str = "",
    confidence: int = 75,
):
    """
    Bulk-import / back-fill helper. Creates one FieldProvenance row per
    (field_name, value) pair, all citing the same source_fetch.

    `snippet_hint` is the same source-derived text used for every field —
    typically the raw row from a Wikipedia list table. Set `confidence`
    low (default 75) so Earl can distinguish synthetic from direct provenance.
    """
    from ..models import FieldProvenance

    objs = [
        FieldProvenance(
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=k,
            value=("" if v is None else str(v))[:8000],
            source_fetch=source_fetch,
            snippet=snippet_hint[:8000] if snippet_hint else "",
            confidence=max(0, min(100, int(confidence))),
        )
        for k, v in field_values.items()
        if v is not None and v != ""
    ]
    FieldProvenance.objects.bulk_create(objs, batch_size=200)
    return len(objs)


def entity_has_full_provenance(
    entity_type: str,
    entity_id: int,
    required_fields: tuple[str, ...],
) -> bool:
    """
    Return True iff `entity_id` has at least one FieldProvenance row for
    every required field. Used by accuracy_contract to gate `verified=True`.
    """
    from ..models import FieldProvenance

    if not required_fields:
        return True
    covered = set(
        FieldProvenance.objects.filter(
            entity_type=entity_type, entity_id=entity_id, field_name__in=required_fields
        )
        .values_list("field_name", flat=True)
        .distinct()
    )
    return all(f in covered for f in required_fields)
