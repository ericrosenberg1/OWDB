"""
PWI 500 + PWI Female 50/100/150 yearly ranking extractor.

The PWI 500 has no consolidated Wikipedia article per year — Wikipedia only
mentions PWI ranks inside individual wrestler bios. ProFightDB, however,
mirrors the official PWI lists at:

    http://www.profightdb.com/pwi-500/YYYY.html
    http://www.profightdb.com/pwi-female-50/YYYY.html

Each table has columns: position | born | wrestler | previous year position
| difference | notes. We extract them into ExternalRanking + Entry rows.

Accuracy contract:
    Position + wrestler name come directly from the table cells. If a row
    is missing the position or wrestler, it is skipped (better empty than
    wrong). Wrestler matching to existing DB rows is done by case-insensitive
    name equality and aliases; unmatched rows are still persisted with the
    name as published.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional

from bs4 import BeautifulSoup

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)


USER_AGENT = "Mozilla/5.0 (compatible; wrestlingdb-wrestlebot/1.0; +https://wrestlingdb.org)"
# ProFightDB is a small site; cap at 1 req per 2 seconds to be polite.
RATE_LIMIT_PER_SEC = 0.5

PFDB_PWI_URLS = {
    "pwi_500": "http://www.profightdb.com/pwi-500/{year}.html",
    "pwi_female_50": "http://www.profightdb.com/pwi-female-50/{year}.html",
    "pwi_female_100": "http://www.profightdb.com/pwi-female-100/{year}.html",
    "pwi_female_150": "http://www.profightdb.com/pwi-female-150/{year}.html",
}


@dataclass
class PWIEntry:
    position: int
    wrestler_name: str
    previous_year_position: Optional[int] = None
    difference: Optional[int] = None
    notes: str = ""


def _http_get(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with rate_limited("profightdb_pwi", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning("PWI HTTP %s for %s: %s", e.code, url, e.reason)
            return None
        except Exception as e:
            logger.warning("PWI request failed for %s: %s", url, e)
            return None


def _to_int(s: str) -> Optional[int]:
    if not s or s.upper() == "N/A":
        return None
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group(0)) if m else None


def fetch_pwi_list(list_kind: str, year: int) -> list[PWIEntry]:
    """
    Fetch and parse one PWI ranking list for a given year. Returns a
    sequential list of PWIEntry rows. Empty list on fetch/parse failure.
    """
    if list_kind not in PFDB_PWI_URLS:
        raise ValueError(f"Unknown list_kind={list_kind!r}; valid: {sorted(PFDB_PWI_URLS)}")
    url = PFDB_PWI_URLS[list_kind].format(year=year)
    html = _http_get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")

    # The page paginates rankings across multiple tables (top 100, 101-200,
    # 201-300, etc.). Each shares the same header structure.
    out: list[PWIEntry] = []
    seen_positions: set[int] = set()
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        # First row is header — confirm it looks like a PWI ranking table.
        header_cells = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        if not header_cells or "position" not in header_cells[0]:
            continue
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            position = _to_int(cells[0].get_text(" ", strip=True))
            if not position or position in seen_positions:
                continue
            wrestler_name = cells[2].get_text(" ", strip=True)
            if not wrestler_name:
                continue
            prev = _to_int(cells[3].get_text(" ", strip=True)) if len(cells) > 3 else None
            diff = _to_int(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else None
            notes = cells[5].get_text(" ", strip=True) if len(cells) > 5 else ""
            out.append(
                PWIEntry(
                    position=position,
                    wrestler_name=wrestler_name,
                    previous_year_position=prev,
                    difference=diff,
                    notes=notes[:500],
                )
            )
            seen_positions.add(position)
    out.sort(key=lambda e: e.position)
    return out


def ingest_pwi_list(list_kind: str, year: int) -> dict:
    """
    Fetch one PWI list, upsert the ExternalRanking + entries.
    Returns stats dict: {ranking_id, entries_created, entries_total, matched_wrestlers}.
    """
    import hashlib
    from owdb_django.owdbapp.models import (
        ExternalRanking,
        ExternalRankingEntry,
        Wrestler,
    )
    from ..models import SourceFetch

    entries = fetch_pwi_list(list_kind, year)
    if not entries:
        return {
            "ranking_id": None,
            "entries_created": 0,
            "entries_total": 0,
            "matched_wrestlers": 0,
            "error": "fetch returned no entries",
        }

    url = PFDB_PWI_URLS[list_kind].format(year=year)
    label = dict(ExternalRanking.LIST_CHOICES).get(list_kind, list_kind)

    # ------------------------------------------------------------------
    # 1. Persist the source page as a SourceFetch so every entry below
    #    has a real auditable provenance trail.
    # ------------------------------------------------------------------
    # The source string makes it clear we got this via ProFightDB's mirror,
    # not the PWI publication itself (codex P2-3).
    source_label = "profightdb_pwi_mirror"
    payload = "\n".join(
        f"{e.position}\t{e.wrestler_name}\tprev={e.previous_year_position}\tdiff={e.difference}\tnotes={e.notes}"
        for e in entries
    )
    h = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    source_fetch, _ = SourceFetch.objects.update_or_create(
        source=source_label,
        content_hash=h,
        defaults=dict(
            url=url[:500],
            entity_type="external_ranking",
            entity_id=0,
            candidate_name=f"{label} ({year})"[:255],
            http_status=200,
            raw_content=payload[:65_000],  # truncated; full data is on the upstream URL
        ),
    )

    ranking, _ = ExternalRanking.objects.update_or_create(
        list_kind=list_kind,
        year=year,
        defaults=dict(
            title=f"{label} ({year})",
            source_url=url,
            notes=f"Source: ProFightDB's PWI mirror — {url}",
        ),
    )

    # Name lookup over existing wrestlers (case-insensitive, aliases).
    wrestler_by_name: dict[str, Wrestler] = {}
    for w in Wrestler.objects.only("id", "name", "aliases"):
        wrestler_by_name[w.name.strip().lower()] = w
        for a in (getattr(w, "aliases", "") or "").split(","):
            a = a.strip().lower()
            if a:
                wrestler_by_name.setdefault(a, w)

    # ------------------------------------------------------------------
    # 2. Upsert entries by (ranking, position). Codex P1-8: do NOT wipe
    #    all entries on rerun — that destroys any human links / review
    #    state. Update in place; only delete rows that are no longer
    #    present in the new fetch.
    # ------------------------------------------------------------------
    new_positions = {e.position for e in entries}
    ExternalRankingEntry.objects.filter(ranking=ranking).exclude(
        position__in=new_positions,
    ).delete()

    matched = 0
    created = 0
    updated = 0
    for e in entries:
        w = wrestler_by_name.get(e.wrestler_name.strip().lower())
        if w:
            matched += 1
        # Preserve a manually-linked wrestler if the auto-lookup didn't find
        # one: only write the FK when we have a match. Passing wrestler=None
        # in defaults would clobber a human's manual correction back to NULL
        # on the next rerun — a 100%-accuracy violation.
        defaults = {
            "wrestler_name_as_published": e.wrestler_name,
            "blurb": e.notes,
        }
        if w is not None:
            defaults["wrestler"] = w
        obj, was_created = ExternalRankingEntry.objects.update_or_create(
            ranking=ranking,
            position=e.position,
            defaults=defaults,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "ranking_id": ranking.id,
        "source_fetch_id": source_fetch.id,
        "source": source_label,
        "entries_created": created,
        "entries_updated": updated,
        "entries_total": len(entries),
        "matched_wrestlers": matched,
    }


if __name__ == "__main__":  # pragma: no cover
    import sys

    args = sys.argv[1:] or ["pwi_500", "2024"]
    list_kind = args[0]
    year = int(args[1])
    entries = fetch_pwi_list(list_kind, year)
    print(f"{len(entries)} entries in {list_kind} {year}")
    for e in entries[:10]:
        print(
            f"  #{e.position:>3}  {e.wrestler_name:<30} prev={e.previous_year_position} diff={e.difference}"
        )
