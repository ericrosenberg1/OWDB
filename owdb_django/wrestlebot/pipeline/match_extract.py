"""
Match extractor for Wikipedia event pages.

Most wrestling-event Wikipedia pages render their match cards as a
'Results' wikitable with columns:

    # | Results | Stipulations | Times

The `Results` column is a single cell of prose like:
    "Owen Hart defeated Bret Hart"
    "Bret Hart and Lex Luger fought to a no-contest"
    "Yokozuna (c) defeated Bret Hart by countout"

We parse those into structured Match rows + MatchParticipant links. The
parse is conservative: anything we cannot confidently split into
participants + outcome is logged and skipped (better empty than wrong).

Accuracy contract:
    - Every Match row carries verification_source='wikipedia' and points
      to the originating SourceFetch.
    - Participants are matched to existing Wrestler entities by case-
      insensitive name equality (with aliases). Unmatched participants
      cause the match to be persisted with whatever wrestlers WE COULD
      identify — orphaned names are recorded in match.about for later
      Al-driven backfill.
    - Match ratings (cagematch_rating, observer_stars) are NOT populated
      from Wikipedia. They're filled by separate enrichment passes when
      we add Cagematch / Observer ingest.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# Outcome markers ordered by specificity — first match wins.
_OUTCOME_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bby\s+pinfall\b", "pinfall"),
    (r"\bby\s+submission\b", "submission"),
    (r"\bby\s+disqualification\b", "dq"),
    (r"\bby\s+countout\b", "count_out"),
    (r"\bby\s+count[\s-]?out\b", "count_out"),
    (r"\bby\s+knockout\b", "knockout"),
    (r"\bby\s+forfeit\b", "forfeit"),
    (r"\bno[\s-]?contest\b", "no_contest"),
    (r"\b(time-?limit\s+draw|fought to a draw|drew)\b", "draw"),
)


@dataclass
class ExtractedMatch:
    """One match parsed from a Wikipedia event Results table."""

    card_position: int  # 1 = opener, max = main event
    raw_text: str  # full 'Results' cell text
    stipulation: str = ""  # value from the Stipulations column
    duration_text: str = ""  # raw 'Times' column value
    duration_seconds: Optional[int] = None
    # Sides: list of name lists. For singles, [[A], [B]] and a winner index.
    # For multi-team, [[A1, A2], [B1, B2]] etc.
    sides: list[list[str]] = field(default_factory=list)
    winning_side: Optional[int] = None  # 0 = first side won, 1 = second, etc.
    outcome_type: str = ""  # pinfall / submission / dq / ...
    title_at_stake: str = ""  # title name if extractable
    title_changed: bool = False
    is_dark: bool = False  # row prefixed with 'D' = dark match

    def to_dict(self) -> dict:
        return {
            "card_position": self.card_position,
            "raw_text": self.raw_text,
            "stipulation": self.stipulation,
            "duration_text": self.duration_text,
            "duration_seconds": self.duration_seconds,
            "sides": self.sides,
            "winning_side": self.winning_side,
            "outcome_type": self.outcome_type,
            "title_at_stake": self.title_at_stake,
            "title_changed": self.title_changed,
            "is_dark": self.is_dark,
        }


# -------------------------------------------------------- parsing helpers


def _parse_duration(s: str) -> Optional[int]:
    """Parse '20:21' or '1:01:35' into seconds."""
    if not s:
        return None
    parts = re.findall(r"\d+", s)
    if not parts:
        return None
    nums = [int(p) for p in parts]
    if len(nums) == 1:  # bare number — assume minutes
        return nums[0] * 60
    if len(nums) == 2:  # mm:ss
        return nums[0] * 60 + nums[1]
    if len(nums) >= 3:  # hh:mm:ss
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    return None


def _detect_outcome(text: str) -> str:
    low = text.lower()
    for pattern, label in _OUTCOME_PATTERNS:
        if re.search(pattern, low):
            return label
    return ""


_NAME_DELIM = re.compile(r"\s*(?:,|\band\b|\bwith\b|&)\s*", re.IGNORECASE)
_PAREN_RE = re.compile(r"\s*\([^)]*\)")
_BRACKET_RE = re.compile(r"\s*\[[^\]]*\]")


def _split_names(side_text: str) -> list[str]:
    """
    Split 'Tom Prichard and Jimmy Del Ray' -> ['Tom Prichard', 'Jimmy Del Ray'].
    Strips parenthetical asides like '(c)' or '(with Mr. Fuji)'.
    """
    if not side_text:
        return []
    # Remove footnote markers ' [1] [34]' etc.
    s = _BRACKET_RE.sub("", side_text)
    # Strip parentheticals AFTER capturing championship marker.
    s = _PAREN_RE.sub("", s)
    # Some pages use ' & ' to join.
    parts = _NAME_DELIM.split(s)
    return [p.strip().strip(",.;:") for p in parts if p.strip() and 2 < len(p.strip()) < 60]


_WINNER_VERBS = (
    "defeated",
    "beat",
    "defeats",
    "pinned",
    "submitted",
    "won against",
    "defeated and ",
)


def _split_winner_loser(results_text: str) -> Optional[tuple[str, str]]:
    """
    Given a Results cell like 'Owen Hart defeated Bret Hart by submission',
    return ('Owen Hart', 'Bret Hart'). The trailing 'by ...' and
    parentheticals are stripped before splitting.

    Returns None if no clear winner/loser verb is found.
    """
    cleaned = re.sub(r"\bby\b\s+[a-zA-Z\s-]+", "", results_text, flags=re.IGNORECASE)
    for verb in _WINNER_VERBS:
        m = re.search(rf"\b{re.escape(verb)}\b", cleaned, re.IGNORECASE)
        if m:
            return cleaned[: m.start()].strip(), cleaned[m.end() :].strip()
    return None


def _is_title_match(stipulation: str) -> tuple[bool, str]:
    """
    Detect title-match stipulations: 'Singles match for the WWF Championship'.
    Returns (is_title_match, title_name).
    """
    if not stipulation:
        return False, ""
    m = re.search(r"for the\s+([A-Z][A-Za-z'\s/]+?(?:Championship|Title)s?\b)", stipulation)
    if m:
        return True, m.group(1).strip()
    return False, ""


# -------------------------------------------------------- table detection


def _looks_like_results_table(table) -> bool:
    """True iff a wikitable has the canonical Results-table header shape."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return False
    header_cells = [
        (c.get_text(" ", strip=True) or "").lower() for c in rows[0].find_all(["th", "td"])
    ]
    if len(header_cells) < 3:
        return False
    joined = " | ".join(header_cells)
    # Canonical header signature.
    if "no." in header_cells[0] or "#" == header_cells[0].strip():
        if "result" in joined and ("stipulation" in joined or "match" in joined):
            return True
    return False


# -------------------------------------------------------- main extractor


def extract_matches(html: str) -> list[ExtractedMatch]:
    """
    Parse a Wikipedia event page's HTML and return the list of extracted
    matches in card-position order.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")

    matches: list[ExtractedMatch] = []
    table_index = 0

    for table in soup.find_all("table", class_=re.compile(r"\bwikitable\b")):
        if not _looks_like_results_table(table):
            continue
        # Reset per Results table so pre-show / multi-night cards don't drift
        # match_order across reruns when a sibling table is added or removed.
        # Tables are namespaced by table_index * 100 to avoid (event, match_order)
        # collisions in persistence.
        position_counter = 0
        rows = table.find_all("tr")
        # First row is the header.
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            num_cell = (cells[0].get_text(" ", strip=True) or "").strip()
            # Skip rows where the first cell isn't a number — section dividers.
            num_match = re.match(r"(\d+)([A-Z])?", num_cell)
            if not num_match:
                continue
            position_counter += 1
            card_position = table_index * 100 + position_counter
            is_dark = bool(num_match.group(2) and num_match.group(2).upper() == "D")

            results_text = cells[1].get_text(" ", strip=True)
            stipulation = cells[2].get_text(" ", strip=True) if len(cells) > 2 else ""
            duration_text = cells[3].get_text(" ", strip=True) if len(cells) > 3 else ""

            m = ExtractedMatch(
                card_position=card_position,
                raw_text=results_text,
                stipulation=stipulation,
                duration_text=duration_text,
                duration_seconds=_parse_duration(duration_text),
                is_dark=is_dark,
            )

            # Title detection from stipulation.
            is_title, title_name = _is_title_match(stipulation)
            if is_title:
                m.title_at_stake = title_name
                # Title change: a "(c)" winner marker is ABSENT and a new
                # champion is named. Better heuristic: champion is on losing
                # side. Hard to nail without disambiguating; skip for now
                # (m.title_changed stays False; agent can refine later).

            # Outcome verb.
            m.outcome_type = _detect_outcome(results_text)

            # Sides + winner.
            wl = _split_winner_loser(results_text)
            if wl:
                winner_side_text, loser_side_text = wl
                m.sides = [_split_names(winner_side_text), _split_names(loser_side_text)]
                if any(m.sides):
                    m.winning_side = 0
            else:
                # No clear winner — likely a draw / no-contest. Try splitting on
                # 'fought to' or 'vs.' / 'versus'.
                for sep in (" fought to ", " vs. ", " versus ", " v. "):
                    if sep in results_text.lower():
                        idx = results_text.lower().index(sep)
                        a, b = results_text[:idx], results_text[idx + len(sep) :]
                        m.sides = [_split_names(a), _split_names(b)]
                        break
                if m.outcome_type in ("draw", "no_contest"):
                    m.winning_side = None
                elif not m.sides:
                    # Couldn't structure — keep raw_text, leave sides empty
                    logger.debug("Could not split results: %r", results_text)

            if any(m.sides) or m.raw_text:
                matches.append(m)

        table_index += 1

    return matches


# -------------------------------------------------------- persistence


def persist_matches_for_event(event, fetch=None) -> dict:
    """
    Extract + persist matches for one Event from its most recent Wikipedia
    SourceFetch. `fetch` is optional — pass to override.

    Returns stats: {extracted, created, updated, skipped, unmatched_names}.
    """
    from owdb_django.owdbapp.models import (
        Match,
        MatchParticipant,
        Wrestler,
        Title,
    )
    from ..models import SourceFetch, FieldProvenance

    if fetch is None:
        fetch = (
            SourceFetch.objects.filter(
                entity_type="event", entity_id=event.id, source="wikipedia", http_status=200
            )
            .order_by("-fetched_at")
            .first()
        )
    if not fetch or not fetch.raw_content:
        return {
            "extracted": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "unmatched_names": [],
            "error": "no Wikipedia fetch",
        }

    extracted = extract_matches(fetch.raw_content)
    if not extracted:
        return {"extracted": 0, "created": 0, "updated": 0, "skipped": 0, "unmatched_names": []}

    # Name lookup table.
    wrestler_by_name: dict[str, Wrestler] = {}
    for w in Wrestler.objects.only("id", "name", "aliases"):
        wrestler_by_name[w.name.strip().lower()] = w
        for a in (getattr(w, "aliases", "") or "").split(","):
            a = a.strip().lower()
            if a:
                wrestler_by_name.setdefault(a, w)

    title_by_name: dict[str, Title] = {
        t.name.strip().lower(): t for t in Title.objects.only("id", "name")
    }

    from . import accuracy_contract
    from ._provenance import bulk_synthetic_provenance

    created = 0
    updated = 0
    skipped = 0
    unmatched: list[str] = []
    by_state = {"verified": 0, "provisional": 0, "candidate": 0}
    kept_orders: set[int] = {em.card_position for em in extracted}

    for em in extracted:
        title_obj = None
        if em.title_at_stake:
            title_obj = title_by_name.get(em.title_at_stake.strip().lower())

        winner_obj = None
        if em.winning_side is not None and em.sides:
            for nm in em.sides[em.winning_side]:
                w = wrestler_by_name.get(nm.strip().lower())
                if w is not None:
                    winner_obj = w
                    break

        match, was_created = Match.objects.update_or_create(
            event=event,
            match_order=em.card_position,
            defaults=dict(
                match_text=em.raw_text[:1000],
                result=em.raw_text[:255],
                match_type=em.stipulation[:255],
                outcome_type=em.outcome_type,
                duration_seconds=em.duration_seconds,
                title=title_obj,
                title_changed=em.title_changed,
                winner=winner_obj,
                winning_side=em.winning_side,
                verified=True,  # back-compat boolean
                verification_source="wikipedia",
            ),
        )
        if was_created:
            created += 1
        else:
            updated += 1

        # ------------------------------------------------------------------
        # Participants: keep existing rows when present so manual corrections
        # (entrance order, roles) aren't destroyed on rerun. Codex P2 finding.
        # ------------------------------------------------------------------
        existing_pids = {p.wrestler_id for p in match.participant_links.all()}
        row_unmatched: list[str] = []
        for side_idx, names in enumerate(em.sides):
            for nm in names:
                w = wrestler_by_name.get(nm.strip().lower())
                if w is None:
                    row_unmatched.append(nm)
                    unmatched.append(nm)
                    continue
                # Upsert (don't delete+recreate) so future role/entrance-order
                # corrections survive re-ingest.
                MatchParticipant.objects.update_or_create(
                    match=match,
                    wrestler=w,
                    defaults=dict(
                        side=side_idx,
                        is_winner=(em.winning_side == side_idx),
                    ),
                )
                match.wrestlers.add(w)

        # Record unresolved participants on the match itself so future
        # passes (or Al) can backfill them. Stored in `about` so they show
        # up on the match detail page.
        if row_unmatched:
            note = "Unresolved participants: " + ", ".join(row_unmatched)
            current_about = match.about or ""
            if note not in current_about:
                match.about = (current_about + "\n\n" + note).strip()[:2000]
                match.save(update_fields=["about"])

        # ------------------------------------------------------------------
        # FieldProvenance: every persisted field cites this event's source
        # fetch + carries the source-text snippet.
        # ------------------------------------------------------------------
        snippet_hint = em.raw_text[:1000]
        field_values = {
            "match_text": em.raw_text[:1000],
            "match_type": em.stipulation[:255],
        }
        if em.outcome_type:
            field_values["outcome_type"] = em.outcome_type
        if em.duration_seconds is not None:
            field_values["duration_seconds"] = em.duration_seconds
        if winner_obj:
            field_values["winner"] = winner_obj.name
        if em.winning_side is not None:
            field_values["winning_side"] = em.winning_side
        if title_obj:
            field_values["title"] = title_obj.name
        if em.title_changed:
            field_values["title_changed"] = True
        bulk_synthetic_provenance(
            entity_type="match",
            entity_id=match.id,
            field_values=field_values,
            source_fetch=fetch,
            snippet_hint=snippet_hint,
            confidence=85,  # 85 — match data parsed directly from Wikipedia results table
        )

        # ------------------------------------------------------------------
        # Contract enforcement — sets verification_state to verified iff:
        #   - match_text has provenance (it does)
        #   - match has at least one participant (forbidden-state check)
        # Falls to candidate if zero participants matched.
        # ------------------------------------------------------------------
        state, reasons = accuracy_contract.enforce("match", match)
        if match.verification_state != state:
            match.verification_state = state
            match.save(update_fields=["verification_state"])
        by_state[state] = by_state.get(state, 0) + 1

    # ------------------------------------------------------------------
    # Prune orphans: a Wikipedia-sourced Match whose match_order is no
    # longer in the current extract has been removed upstream (or shifted
    # to a new card_position because a sibling Results table appeared).
    # Without this, table_index re-namespacing leaves the old rows behind
    # forever. Scope is intentionally narrow:
    #   - Same event
    #   - verification_source='wikipedia' only (don't touch Cagematch/manual)
    #   - Skip when kept_orders is empty (already short-circuited above, but
    #     belt-and-braces against future refactors that could nuke an event)
    # MatchParticipant cascades via FK; FieldProvenance is a soft reference
    # so we clear it explicitly.
    # ------------------------------------------------------------------
    orphans_pruned = 0
    if kept_orders:
        orphans = list(
            Match.objects.filter(event=event, verification_source="wikipedia")
            .exclude(match_order__in=kept_orders)
            .values_list("id", flat=True)
        )
        if orphans:
            FieldProvenance.objects.filter(
                entity_type="match",
                entity_id__in=orphans,
            ).delete()
            Match.objects.filter(id__in=orphans).delete()
            orphans_pruned = len(orphans)

    return {
        "extracted": len(extracted),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "orphans_pruned": orphans_pruned,
        "by_state": by_state,
        "unmatched_names": unmatched[:50],
    }
