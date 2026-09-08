"""
Reconcile stage — merge fields across multiple sources for the same entity.

v3.0 is single-source-per-entity (Wikipedia only), so reconcile is a thin
pass-through to persist. The interface is here so v3.1+ can plug in
cross-source merging without rewiring the pipeline.

Future cross-source policy (placeholder spec, not implemented):
- For each field, pick the value most sources agree on.
- On disagreement, prefer the source with higher confidence ranking
  (Cagematch > Wikipedia > ProFightDB for match-specific fields;
   Wikipedia > Cagematch > ProFightDB for biographical fields).
- Record all candidate values via FieldProvenance regardless of which wins.
"""

from __future__ import annotations

from typing import Optional

from ..models import SourceFetch
from ..sources.base import WrestlerFields
from .persist import PersistResult, persist_wrestler


def reconcile_and_persist_wrestler(
    candidate_name: str,
    fields_by_source: dict[str, tuple[WrestlerFields, SourceFetch]],
) -> Optional[PersistResult]:
    """
    Merge fields across sources for a wrestler and persist.

    v3.0: pick the first source (Wikipedia) and ignore the rest.

    Args:
        candidate_name: The name the pipeline was searching for.
        fields_by_source: {source_name: (WrestlerFields, SourceFetch)}.

    Returns the PersistResult from persist_wrestler, or None.
    """
    if not fields_by_source:
        return None

    # v3.0: single-source. Pick wikipedia if present, else the first available.
    if "wikipedia" in fields_by_source:
        fields, fetch = fields_by_source["wikipedia"]
    else:
        source_name, (fields, fetch) = next(iter(fields_by_source.items()))

    return persist_wrestler(candidate_name, fields, fetch)
