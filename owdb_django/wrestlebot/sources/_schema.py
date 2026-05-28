"""
Schema-driven extractor framework.

Roughly half the code in `wrestlebot/sources/*.py` and a big chunk of
`pipeline/event_lists.py` and `pipeline/title_history.py` is copy-pasted
table-walking boilerplate: find the right `<table>`, parse headers, look
up column indexes, iterate rows, skip junk rows, clean cell values into
typed fields, package the result.

That boilerplate is the dominant source of "small refactor silently
drops a guard" bugs. Every new extractor reaches for the existing
`event_lists.py` template and adapts ~300 lines line-by-line; when
someone trims it down to ~250 they invariably remove the gate that
filtered out continuation rows, and the next ingest sweep produces a
hundred "Rosemont, Illinois" Venue rows.

This module replaces the boilerplate with a single declarative
`TableExtractorSpec` dataclass. Each new extractor becomes ~20 lines of
spec + cleaner functions instead of ~300 lines of imperative code.

Crucially, the framework automatically attaches a `FieldSnippet` (the
unit our accuracy contract checks) to every extracted value — bypassing
the contract becomes structurally impossible, because the only way to
get a value out is through `extract_tables()`, which always wraps it
in a FieldSnippet pointing at the actual `<td>` text.

# Spec shape

    spec = TableExtractorSpec(
        result_dataclass=ExtractedEvent,
        table_filter=is_ppv_table,         # callable: BeautifulSoup table → bool
        columns={
            # canonical_field_name: list of header keywords (case-insensitive)
            "date":         ["date"],
            "name":         ["event", "name"],
            "venue_name":   ["venue"],
            "location":     ["location", "city"],
            "attendance":   ["attendance"],
        },
        cleaners={                          # per-field cell → value
            "date":         clean_date,
            "attendance":   clean_attendance,
        },
        row_filter=skip_location_only_rows,  # callable: dict → bool (True = keep)
        context_resolvers={                  # for fields that come from heading context
            "year_context": resolve_year_from_preceding_heading,
        },
        required_fields=("date", "name"),    # rows missing these are dropped
    )
    rows = extract_tables(html, spec)

# Why the cleaner design

Each cleaner takes the raw cell text + the row's full context (so it
can refer to sibling columns or to `context_resolvers` output) and
returns a `FieldSnippet` (or None to drop the field). Cleaners that
return None do NOT block the row — they just omit that one field.

# Why this still leaves room for the imperative extractors

A spec handles the common 90% (tabular Wikipedia lists). The remaining
10% — Cagematch's free-form HTML, MusicBrainz JSON, Commons metadata —
stays as bespoke code because there's no shared shape to abstract.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from bs4 import BeautifulSoup

from .base import FieldSnippet

logger = logging.getLogger(__name__)


# Type aliases — these are just for readability. The functions themselves
# are duck-typed; nothing enforces these signatures statically.
TableFilter = Callable[[Any], bool]  # bs4.Tag → bool
RowFilter = Callable[[dict], bool]  # row-context dict → bool
CellCleaner = Callable[[str, dict], Optional[FieldSnippet]]
ContextResolver = Callable[[Any], Any]  # bs4.Tag → resolved value


# -----------------------------------------------------------------------------
# Spec dataclass
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class TableExtractorSpec:
    """
    Declarative spec for one tabular Wikipedia-style extractor.

    Pass to `extract_tables(html, spec)` → list of (result_dataclass, snippets)
    tuples where each tuple is one row's typed result + the FieldSnippet
    map that proves the accuracy contract.
    """

    # The dataclass instances we'll return one of per row. MUST have an
    # `__init__` that accepts keyword args matching the keys of `columns`.
    result_dataclass: type

    # Predicate: does this `<table>` element belong to this extractor?
    table_filter: TableFilter

    # canonical_field_name → list of lowercase header substrings to match.
    # First column whose header contains any of the substrings wins.
    columns: dict[str, tuple[str, ...]]

    # canonical_field_name → cleaner. If a cleaner is absent, the raw
    # `cell.get_text(" ", strip=True)` becomes the FieldSnippet value.
    cleaners: dict[str, CellCleaner] = field(default_factory=dict)

    # Predicate evaluated on each row's intermediate context dict (the raw
    # cell text per column). Return False to drop the row.
    row_filter: Optional[RowFilter] = None

    # Names of fields the row MUST have populated (after cleaners). Missing
    # any → row is dropped. Use this to enforce "every event has a date."
    required_fields: tuple[str, ...] = ()

    # Optional fields whose value comes from heading context (year, season
    # number, etc.), not from a cell. Keys here ARE valid `columns` keys.
    context_resolvers: dict[str, ContextResolver] = field(default_factory=dict)


# -----------------------------------------------------------------------------
# Engine
# -----------------------------------------------------------------------------


def _header_cells(table) -> list[str]:
    rows = table.find_all("tr")
    if not rows:
        return []
    return [(c.get_text(" ", strip=True) or "").lower() for c in rows[0].find_all(["th", "td"])]


def _column_index(headers: list[str], needles: tuple[str, ...]) -> Optional[int]:
    """Find the first column whose header contains any of `needles`."""
    for i, h in enumerate(headers):
        for n in needles:
            if n in h:
                return i
    return None


def _default_cleaner(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """Fallback cleaner: return the raw text as-is, never None for empty."""
    text = (text or "").strip()
    if not text:
        return None
    return FieldSnippet(value=text, snippet=text, confidence=85)


def extract_tables(
    html: str,
    spec: TableExtractorSpec,
) -> list[tuple[Any, dict[str, FieldSnippet]]]:
    """
    Apply `spec` to `html`. Returns list of (instance, snippets) tuples
    where `instance` is the spec.result_dataclass populated with values
    and `snippets` is the {field_name: FieldSnippet} map matching it.

    The pipeline persist layer can then write one FieldProvenance row
    per snippet without doing any extraction logic of its own.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[tuple[Any, dict[str, FieldSnippet]]] = []

    for table in soup.find_all("table"):
        try:
            if not spec.table_filter(table):
                continue
        except Exception as e:
            logger.debug("schema: table_filter raised on %s: %s", spec, e)
            continue

        headers = _header_cells(table)
        if not headers:
            continue

        # Resolve column index for each requested field once per table.
        col_index: dict[str, int] = {}
        for fname, needles in spec.columns.items():
            if fname in spec.context_resolvers:
                continue  # comes from heading context, not a column
            idx = _column_index(headers, needles)
            if idx is not None:
                col_index[fname] = idx

        if not col_index:
            logger.debug("schema: no columns matched for this table; skipping")
            continue

        # Heading-context fields: resolved once per table.
        ctx_values: dict[str, Any] = {}
        for fname, resolver in spec.context_resolvers.items():
            try:
                ctx_values[fname] = resolver(table)
            except Exception as e:
                logger.debug("schema: context_resolver(%s) raised: %s", fname, e)
                ctx_values[fname] = None

        rows = table.find_all("tr")[1:]  # skip header row
        for tr in rows:
            cells = tr.find_all(["td", "th"])
            if not cells:
                continue

            # Build raw-text context dict — passed to cleaners and row_filter.
            # Reserved keys (all leading `__`):
            #   `__cell_texts__`  full per-row tuple of cell text strings
            #   `__cells__`       full per-row tuple of bs4 cell Tags
            #   `__col_index__`   {field_name: cell_index} for configured columns
            # Cleaners that need DOM-level info — e.g. the `<a href>` inside a
            # cell, to disambiguate "Mr. Perfect" → /wiki/Curt_Hennig — use
            # `__cells__` + `__col_index__` to grab their own cell tag.
            raw_ctx: dict = {
                "__cell_texts__": tuple(c.get_text(" ", strip=True) or "" for c in cells),
                "__cells__": tuple(cells),
                "__col_index__": dict(col_index),
            }
            for fname, idx in col_index.items():
                if idx >= len(cells):
                    continue
                raw_ctx[fname] = cells[idx].get_text(" ", strip=True) or ""

            # Pass heading-context values through the context dict too, so
            # cleaners + row_filter can use them.
            for fname, val in ctx_values.items():
                raw_ctx[fname] = val

            # Drop the row if the spec's row_filter says so.
            if spec.row_filter is not None:
                try:
                    if not spec.row_filter(raw_ctx):
                        continue
                except Exception as e:
                    logger.debug("schema: row_filter raised: %s", e)
                    continue

            # Run cleaners. Each returns a FieldSnippet OR None.
            snippets: dict[str, FieldSnippet] = {}
            for fname in spec.columns:
                cleaner = spec.cleaners.get(fname, _default_cleaner)
                raw_value = raw_ctx.get(fname, "")
                # Heading-context fields don't go through default_cleaner —
                # their value is already typed.
                if fname in spec.context_resolvers and fname not in spec.cleaners:
                    if raw_value not in (None, ""):
                        snippets[fname] = FieldSnippet(
                            value=raw_value,
                            snippet=f"(heading context: {raw_value})",
                            confidence=80,
                        )
                    continue
                try:
                    snip = cleaner(
                        raw_value if isinstance(raw_value, str) else str(raw_value), raw_ctx
                    )
                except Exception as e:
                    logger.debug("schema: cleaner(%s) raised on %r: %s", fname, raw_value, e)
                    snip = None
                if snip is not None:
                    snippets[fname] = snip

            # Enforce required fields.
            missing = [f for f in spec.required_fields if f not in snippets]
            if missing:
                continue

            # Instantiate the spec's result dataclass. Each field can
            # accept either the raw value or the FieldSnippet —
            # by convention we pass the raw value (matches the legacy
            # ExtractedEvent / ExtractedEpisode shape).
            try:
                instance = spec.result_dataclass(**{k: v.value for k, v in snippets.items()})
            except TypeError as e:
                logger.warning(
                    "schema: %s rejected fields %s: %s",
                    spec.result_dataclass.__name__,
                    sorted(snippets),
                    e,
                )
                continue
            out.append((instance, snippets))

    return out


# -----------------------------------------------------------------------------
# Reusable cleaners — drop these into a spec's `cleaners=` dict.
# -----------------------------------------------------------------------------


_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def clean_iso_or_natural_date(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """
    Parse an ISO date ('2024-04-06') OR a 'natural' Wikipedia date
    ('April 6, 2024'). Returns a `datetime.date` value.
    """
    from datetime import date as _date

    if not text:
        return None
    text = text.strip()

    m = _ISO_DATE_RE.search(text)
    if m:
        try:
            return FieldSnippet(
                value=_date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
                snippet=text[:200],
                confidence=98,
            )
        except ValueError:
            return None

    # 'April 6, 2024' or 'April 6 2024'
    m = re.search(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
        text,
        re.I,
    )
    if m:
        try:
            return FieldSnippet(
                value=_date(
                    int(m.group(3)),
                    _MONTH_NAMES[m.group(1).lower()],
                    int(m.group(2)),
                ),
                snippet=text[:200],
                confidence=92,
            )
        except ValueError:
            return None
    return None


def clean_attendance(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """Parse a comma-grouped attendance figure with sanity bounds."""
    if not text:
        return None
    m = re.search(r"\d[\d,]*", text)
    if not m:
        return None
    n = int(m.group(0).replace(",", ""))
    if n <= 0 or n > 250_000:
        return None
    return FieldSnippet(value=n, snippet=text[:120], confidence=95)


def clean_int(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """Generic positive-integer cleaner (episode numbers, ring counts, etc.)."""
    if not text:
        return None
    m = re.search(r"-?\d+", text.replace(",", ""))
    if not m:
        return None
    return FieldSnippet(value=int(m.group(0)), snippet=text[:80], confidence=98)


def clean_text(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """Trim + return as text. Empty → None (drops the field)."""
    text = (text or "").strip()
    if not text:
        return None
    return FieldSnippet(value=text, snippet=text[:200], confidence=85)


def clean_text_required_non_empty(text: str, ctx: dict) -> Optional[FieldSnippet]:
    """Like `clean_text` but with a higher confidence floor."""
    text = (text or "").strip()
    if not text or len(text) < 2:
        return None
    return FieldSnippet(value=text, snippet=text[:200], confidence=95)


# -----------------------------------------------------------------------------
# Reusable context resolvers
# -----------------------------------------------------------------------------


def resolve_year_from_preceding_heading(table) -> Optional[int]:
    """
    Walk the document in source order; return the most recent
    h2/h3/h4 heading containing a 4-digit year, or None.

    Used by Wikipedia year-segmented lists where the table itself
    doesn't carry a year column.
    """
    soup = table.find_parent("html") or table.find_parent("body") or table.parent
    if soup is None:
        return None
    current_year: Optional[int] = None
    for el in soup.find_all(["h2", "h3", "h4", "table"]):
        if el is table:
            return current_year
        if el.name in ("h2", "h3", "h4"):
            text = el.get_text(" ", strip=True)
            m = re.search(r"\b(19|20)\d{2}\b", text)
            if m:
                current_year = int(m.group(0))
    return None


# -----------------------------------------------------------------------------
# Reusable table filters
# -----------------------------------------------------------------------------


def wikitable_with_headers(*required_substrings: str) -> TableFilter:
    """
    Return a `table_filter` that matches any wikitable whose joined header
    text contains every one of `required_substrings` (case-insensitive).

    Usage:
        spec = TableExtractorSpec(
            table_filter=wikitable_with_headers("date", "event", "venue"),
            ...
        )
    """
    required = tuple(s.lower() for s in required_substrings)

    def _f(table) -> bool:
        cls = table.get("class") or []
        if not any("wikitable" in c for c in cls):
            return False
        headers = _header_cells(table)
        if not headers:
            return False
        joined = " | ".join(headers)
        return all(s in joined for s in required)

    return _f
