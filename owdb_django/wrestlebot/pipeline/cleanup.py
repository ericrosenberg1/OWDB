"""
Post-extraction field cleanup.

Fixes a few common Wikipedia-extraction artifacts that survived the initial
parse: stray quote tokens, empty list items from double commas, footnote
markers that escaped the <sup> stripper, leading/trailing punctuation.

These transformations are intentionally conservative — only clear junk gets
dropped. Anything ambiguous is kept verbatim.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Tokens that are pure punctuation / quote chars / lone bracket markers.
# Wikipedia's quoted ring-names ('"Stone Cold" Steve Austin') get split into
# separate text nodes, so the lone `"` ends up as its own comma-delimited item.
_JUNK_TOKEN_RE = re.compile(
    r"""^(
        ["“”'`]                # lone quote chars (straight or curly)
        | \[[a-z0-9]+\]        # footnote refs like [a], [1], [12]
        | [(){}\[\]]+          # lone bracket characters
        | \.+                  # lone dots
        | ,+                   # lone commas
        | -+                   # lone dashes
        | \s*                  # empty / whitespace
    )$""",
    re.VERBOSE,
)


def _split_commas(value: str) -> list[str]:
    """Split a comma-separated string into trimmed parts."""
    return [p.strip() for p in value.split(",")]


def clean_list_field(value: Optional[str]) -> Optional[str]:
    """
    Clean a comma-separated multi-value field (aliases, trained_by, finishers, etc).

    - Drops junk tokens (lone quotes, brackets, empty after split-on-comma).
    - Strips bracket markers like [a], [1] that escaped <sup> stripping.
    - Dedupes while preserving order.
    - Re-joins with ", ".

    Returns None if value is None; "" if everything got cleaned away.
    """
    if value is None:
        return None
    if not value.strip():
        return ""

    parts = _split_commas(value)
    cleaned: list[str] = []
    seen: set[str] = set()

    for part in parts:
        # Trim repeated spaces; drop trailing/leading bracket markers
        p = re.sub(r"\s{2,}", " ", part).strip()
        # Remove inline footnote markers that escaped <sup> stripping
        p = re.sub(r"\[[a-z0-9]+\]", "", p, flags=re.IGNORECASE).strip()
        # Drop trailing junk punctuation but preserve internal punctuation
        p = p.rstrip(",;:")

        if not p:
            continue
        if _JUNK_TOKEN_RE.match(p):
            continue
        # Skip tokens that became too short to be a real value after cleaning
        if len(p) < 2:
            continue

        key = p.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(p)

    return ", ".join(cleaned)


def clean_single_value(value: Optional[str]) -> Optional[str]:
    """
    Clean a single-value text field (real_name, hometown, height, weight).

    - Strip footnote markers.
    - Strip leading/trailing whitespace + comma/quote/dash junk.
    - Collapse internal whitespace runs.
    - Preserves trailing periods (e.g., "U.S." stays "U.S.") — these are
      valid abbreviations, not sentence terminators.
    """
    if value is None:
        return None
    if not value.strip():
        return ""

    v = value
    v = re.sub(r"\[[a-z0-9]+\]", "", v, flags=re.IGNORECASE)
    v = re.sub(r"\s{2,}", " ", v)
    # Strip junk from the ends, but NOT trailing periods (those are abbrev
    # terminators in things like "U.S." / "Jr.").
    v = v.strip("\"'`“”,;:- \t\n")
    return v.strip()


# Map field_name -> cleaner function. Used by the post-extract sweep.
WRESTLER_FIELD_CLEANERS = {
    "aliases": clean_list_field,
    "trained_by": clean_list_field,
    "finishers": clean_list_field,
    "signature_moves": clean_list_field,
    "real_name": clean_single_value,
    "hometown": clean_single_value,
    "height": clean_single_value,
    "weight": clean_single_value,
    "nationality": clean_single_value,
}


def clean_wrestler_fields(wrestler) -> dict[str, str]:
    """
    Apply field cleaners to a Wrestler. Returns dict of {field: new_value} for
    every field that actually changed. Does NOT save the wrestler.
    """
    changes: dict[str, str] = {}
    for field, cleaner in WRESTLER_FIELD_CLEANERS.items():
        old = getattr(wrestler, field, None)
        new = cleaner(old)
        if new != old:
            changes[field] = new or ""
    return changes


def apply_wrestler_cleanup(wrestler) -> dict[str, str]:
    """Clean a wrestler's fields in place and save. Returns the change set."""
    changes = clean_wrestler_fields(wrestler)
    if not changes:
        return {}

    for field, value in changes.items():
        setattr(wrestler, field, value)
    update_fields = list(changes.keys()) + ["updated_at"]
    wrestler.save(update_fields=update_fields)
    return changes
