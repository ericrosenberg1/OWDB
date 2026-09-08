"""
Title-history extractor — uses Wikipedia's "List of X Champions" articles
to discover wrestlers we don't yet have and to verify championship lineage.

Each "List of ... Champions" article on Wikipedia contains one or more
wikitables with a `Champion` column. We:
  1. Pull every distinct wrestler name from every Champion column.
  2. Queue names not already in the DB for JR's ingest pipeline.
  3. Persist FieldProvenance citing the title-history page so each
     discovered wrestler has an auditable source trail from the moment
     they enter the system.

Accuracy contract:
  - We only ADD candidate wrestler names — we never write fields like
    debut_year / birth_date / etc. from these tables. Those come from
    each wrestler's own Wikipedia page once JR fetches it.
  - The discovery is just a notability signal: "this person held a major
    championship, therefore worth ingesting."
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from ..sources._schema import TableExtractorSpec, extract_tables
from ..sources.base import FieldSnippet

logger = logging.getLogger(__name__)


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org; admin@wrestlingdb.org)"


# Title-history pages by title slug. Earlier entries get priority.
# These are the most-notable championships — long lineages, marquee names.
TITLE_HISTORY_PAGES: dict[str, tuple[str, ...]] = {
    "wwe_championship":         ("List of WWE Champions",),
    "wwe_universal":            ("List of WWE Universal Champions",),
    "wwe_intercontinental":     ("List of WWE Intercontinental Champions",),
    "wwe_united_states":        ("List of WWE United States Champions",),
    "wwe_womens":               ("List of WWE Women's Champions",
                                 "List of WWE Women's Champions (1956-2010)"),
    "wwe_raw_womens":           ("List of WWE Raw Women's Champions",),
    "wwe_smackdown_womens":     ("List of WWE SmackDown Women's Champions",),
    "wwe_tag_team":             ("List of WWE Tag Team Champions",),
    "wwe_world_tag_team":       ("List of WWE World Tag Team Champions",),
    "wcw_world_heavyweight":    ("List of WCW World Heavyweight Champions",),
    "wcw_united_states":        ("List of WCW United States Heavyweight Champions",),
    "wcw_world_television":     ("List of WCW World Television Champions",),
    "nwa_world_heavyweight":    ("List of NWA World Heavyweight Champions",),
    "aew_world":                ("List of AEW World Champions",
                                 "AEW World Championship"),
    "aew_womens_world":         ("List of AEW Women's World Champions",
                                 "AEW Women's World Championship"),
    "aew_tnt":                  ("List of AEW TNT Champions",
                                 "AEW TNT Championship"),
    "aew_tbs":                  ("List of AEW TBS Champions",
                                 "AEW TBS Championship"),
    "tna_world":                ("List of TNA World Heavyweight Champions",
                                 "TNA World Championship",
                                 "TNA World Heavyweight Championship"),
    "tna_knockouts":            ("List of TNA Knockouts Champions",
                                 "TNA Knockouts Championship"),
    "ecw_world":                ("List of ECW World Heavyweight Champions",),
    "iwgp_heavyweight":         ("List of IWGP Heavyweight Champions",
                                 "List of IWGP World Heavyweight Champions",
                                 "IWGP World Heavyweight Championship"),
    "iwgp_intercontinental":   ("List of IWGP Intercontinental Champions",),
    "iwgp_jr_heavyweight":     ("List of IWGP Junior Heavyweight Champions",),
    "ajpw_triple_crown":       ("List of Triple Crown Heavyweight Champions",
                                "Triple Crown Heavyweight Championship"),
    "noah_ghc_heavyweight":    ("List of GHC Heavyweight Champions",
                                "GHC Heavyweight Championship"),
    "roh_world":               ("List of ROH World Champions",
                                "ROH World Championship"),
    "cmll_world_heavyweight":  ("List of CMLL World Heavyweight Champions",),
    "wwe_hall_of_fame":        ("List of WWE Hall of Fame inductees",),
    "pwhof":                    ("Professional Wrestling Hall of Fame and Museum",),
}


# ------------------------------------------------------------------ HTTP


def _wiki_parse_page(title: str) -> Optional[dict]:
    params = {
        "action": "parse", "page": title, "prop": "text",
        "format": "json", "formatversion": "2",
        "redirects": "1", "disableeditsection": "true",
    }
    url = WIKIPEDIA_API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                import gzip
                data = gzip.decompress(data)
            return json.loads(data.decode("utf-8", errors="replace"))
    except Exception as e:
        logger.warning("Wikipedia fetch failed for %r: %s", title, e)
        return None


def _first_existing(titles: tuple[str, ...]) -> Optional[tuple[str, str]]:
    for t in titles:
        d = _wiki_parse_page(t)
        if not d or "parse" not in d:
            continue
        resolved = d["parse"].get("title", t)
        text = d["parse"].get("text")
        html = text if isinstance(text, str) else (text.get("*") if isinstance(text, dict) else None)
        if html:
            return resolved, html
    return None


# ------------------------------------------------------ extraction
#
# Title-history articles use a wikitable with a `Champion` (or `Wrestler` /
# `Name` / `Inductee`) column. We declare a TableExtractorSpec that:
#   - Detects those tables by header (`_is_champion_table`).
#   - Drops header sub-rows that aren't real reign rows
#     (`_keep_real_reign_row`) — the same heuristic the legacy code used.
#   - Cleans the champion-cell text via `_clean_champion_name`, stripping
#     parentheticals ('Bret Hart (4)'), footnotes ('Hulk Hogan [b]'), and
#     quotes; rejects entries that look like venue/promotion/event rows.
#
# The framework gives us a list of `_ChampionRow` instances; we dedupe by
# name and count raw rows seen — preserving the public
# `extract_champions_from_html(html) -> (unique_names, raw_count)` shape.


_NON_WRESTLER_NAMES = {
    "vacated", "vacant", "deactivated", "held up", "retired", "abandoned",
    "tournament", "abeyance", "n/a", "event", "champion", "champions",
    "wrestler", "wrestlers", "name", "inductee", "date", "location",
    "reign", "days", "result",
}
_NON_WRESTLER_TOKENS = (
    "championship", "title", "tournament", "promotion",
    "association", "federation",
)
_PAREN_RE = re.compile(r"\s*[\(\[][^)\]]*[\)\]]")
_CHAMPION_HEADERS = (
    "champion", "champions", "wrestler", "wrestlers", "name", "inductee",
)

_WIKI_LINK_PREFIX = "/wiki/"
# Wikipedia namespaces that are never wrestler articles. The action=parse
# fetcher would still resolve them, but they're never what we want to queue.
_WIKI_NAMESPACES_TO_SKIP = (
    "Category:", "File:", "Help:", "Wikipedia:",
    "Special:", "Template:", "Talk:", "Portal:",
)


def _link_target_for_name_cell(ctx: dict) -> Optional[str]:
    """
    Return the Wikipedia article title pointed to by the `<a>` in the
    Champion cell, or None if there's no usable link.

    The display text of the Champion cell is often a ring name that
    collides with a disambiguation page on Wikipedia ("Mr. Perfect",
    "The Texas Tornado", "Rikishi"). The `href` on the anchor points
    at the actual wrestler article (`/wiki/Curt_Hennig`,
    `/wiki/Kerry_Von_Erich`, `/wiki/Rikishi_(wrestler)`), so we prefer
    it whenever it's present and non-red.
    """
    cells = ctx.get("__cells__") or ()
    idx = (ctx.get("__col_index__") or {}).get("name")
    if idx is None or idx >= len(cells):
        return None
    a = cells[idx].find("a", href=True)
    if a is None:
        return None
    # Red links point at `?action=edit&redlink=1` — the article doesn't
    # exist yet, so the href is unusable; fall back to display text.
    if "new" in (a.get("class") or []):
        return None
    href = a["href"]
    if not href.startswith(_WIKI_LINK_PREFIX):
        return None
    target = href[len(_WIKI_LINK_PREFIX):].split("#", 1)[0].split("?", 1)[0]
    if not target:
        return None
    if any(target.startswith(ns) for ns in _WIKI_NAMESPACES_TO_SKIP):
        return None
    return urllib.parse.unquote(target).replace("_", " ")


def _clean_champion_name(text: str, ctx: dict) -> Optional[FieldSnippet]:
    if not text:
        return None
    s = text.strip()
    s = re.sub(r"\[[0-9a-z]+\]", "", s)
    s = _PAREN_RE.sub("", s)
    s = re.sub(r"[\"“”'‘’]", "", s)
    s = re.sub(r"\s+", " ", s).strip().strip(",.;:")
    if not s or len(s) < 3 or len(s) > 60:
        return None
    low = s.lower()
    if low in _NON_WRESTLER_NAMES:
        return None
    if any(t in low for t in _NON_WRESTLER_TOKENS):
        return None
    if ":" in s:
        return None
    if not re.search(r"[A-Za-z]{2,}", s):
        return None
    if re.match(r"^[\d\s\-]+$", s):
        return None
    # Display text passed sanity checks. If the cell links to a real
    # Wikipedia article, use the link target instead — it's the canonical
    # title and avoids the disambig-page problem (e.g. queue "Curt Hennig"
    # not "Mr. Perfect"). Display-text sanity checks above already gate
    # out junk rows ("ECW Championship", "WWE : SmackDown"), so we only
    # apply minimal validation to the link target itself.
    link_target = _link_target_for_name_cell(ctx)
    if link_target and 3 <= len(link_target) <= 80:
        lt_low = link_target.lower()
        if (
            lt_low not in _NON_WRESTLER_NAMES
            and not any(t in lt_low for t in _NON_WRESTLER_TOKENS)
        ):
            return FieldSnippet(value=link_target, snippet=text[:200], confidence=95)
    return FieldSnippet(value=s, snippet=text[:200], confidence=85)


def _is_champion_table(table) -> bool:
    """A wikitable whose header row has a Champion / Wrestler / Inductee column."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return False
    headers = [
        (c.get_text(" ", strip=True) or "").strip().lower().rstrip(":")
        for c in rows[0].find_all(["th", "td"])
    ]
    return any(h in _CHAMPION_HEADERS for h in headers)


def _keep_real_reign_row(ctx: dict) -> bool:
    """
    Drop header sub-rows that creep into multi-section tables. A real
    reign row has either a rank-style number in cell 0 ('1', '12a') OR
    a 4-digit year *somewhere* in the row.
    """
    cells = ctx.get("__cell_texts__") or ()
    if not cells:
        return False
    if re.match(r"^\d+[a-z]?\s*$", cells[0]):
        return True
    if any(re.search(r"\b(19|20)\d{2}\b", c) for c in cells):
        return True
    return False


@dataclass
class _ChampionRow:
    name: str


# ------------------------------------------------------ public API


@dataclass
class TitleHistoryFinding:
    title_slug: str
    resolved_wikipedia_title: str
    source_url: str
    unique_champions: list[str] = field(default_factory=list)
    raw_count_seen: int = 0

    def to_dict(self) -> dict:
        return {
            "title_slug": self.title_slug,
            "resolved_wikipedia_title": self.resolved_wikipedia_title,
            "source_url": self.source_url,
            "unique_champions_count": len(self.unique_champions),
            "raw_count_seen": self.raw_count_seen,
            "sample_champions": self.unique_champions[:10],
        }


_CHAMPION_SPEC = TableExtractorSpec(
    result_dataclass=_ChampionRow,
    table_filter=_is_champion_table,
    columns={"name": _CHAMPION_HEADERS},
    cleaners={"name": _clean_champion_name},
    row_filter=_keep_real_reign_row,
    required_fields=("name",),
)


def _count_pre_filter_rows(html: str) -> int:
    """
    Count rows in every champion-bearing table BEFORE `_keep_real_reign_row`
    drops sub-headers — i.e. the legacy `raw_count_seen` denominator.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "lxml")
    count = 0
    for table in soup.find_all("table"):
        if not _is_champion_table(table):
            continue
        rows = table.find_all("tr")
        headers = [
            (c.get_text(" ", strip=True) or "").strip().lower().rstrip(":")
            for c in rows[0].find_all(["th", "td"])
        ]
        col_idx = next(
            (i for i, h in enumerate(headers) if h in _CHAMPION_HEADERS), None,
        )
        if col_idx is None:
            continue
        for tr in rows[1:]:
            if col_idx < len(tr.find_all(["td", "th"])):
                count += 1
    return count


def extract_champions_from_html(html: str) -> tuple[list[str], int]:
    """
    Extract every unique champion / inductee name from a Wikipedia
    title-history HTML page.

    Returns (ordered_unique_names, total_rows_seen).
    """
    seen: dict[str, None] = {}  # ordered set
    for row, _snippets in extract_tables(html, _CHAMPION_SPEC):
        seen.setdefault(row.name, None)
    return list(seen.keys()), _count_pre_filter_rows(html)


def discover_from_title_history(title_slug: str) -> Optional[TitleHistoryFinding]:
    """Pull one title-history page and return the unique-champions finding."""
    pages = TITLE_HISTORY_PAGES.get(title_slug)
    if not pages:
        return None
    result = _first_existing(pages)
    if not result:
        return None
    resolved_title, html = result
    champions, raw_count = extract_champions_from_html(html)
    url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(resolved_title.replace(' ', '_'))}"
    return TitleHistoryFinding(
        title_slug=title_slug,
        resolved_wikipedia_title=resolved_title,
        source_url=url,
        unique_champions=champions,
        raw_count_seen=raw_count,
    )


def discover_from_all_titles(limit_per_title: int = 200) -> dict:
    """
    Pull every title-history page in TITLE_HISTORY_PAGES, return a dict
    mapping title_slug -> finding, plus a flat set of all unique names.
    """
    out: dict[str, TitleHistoryFinding] = {}
    all_names: dict[str, list[str]] = {}  # name -> [title_slugs that mention them]
    for slug in TITLE_HISTORY_PAGES:
        f = discover_from_title_history(slug)
        if f is None:
            continue
        out[slug] = f
        for nm in f.unique_champions[:limit_per_title]:
            all_names.setdefault(nm, []).append(slug)
    return {"by_title": out, "by_name": all_names}


# ------------------------------------------------------ ingest entry point


def ingest_title_history_discovery(
    title_slug: Optional[str] = None,
    max_unknown_to_queue: int = 20,
) -> dict:
    """
    For one title (or all if title_slug=None), extract champions and
    queue unknown ones via the existing fetch_wrestler_candidates path.

    Returns {title_slug -> {found, already_in_db, queued, source_url}}.
    Each queued wrestler gets a SourceFetch citing the title-history page.
    """
    from owdb_django.owdbapp.models import Wrestler
    from .fetch import fetch_wrestler_candidates

    title_slugs = [title_slug] if title_slug else list(TITLE_HISTORY_PAGES)
    report: dict[str, dict] = {}
    total_queued = 0

    # One DB-side lookup for the existing wrestler name set, used across
    # all titles to avoid repeated full-table queries.
    existing_names = {
        w.name.strip().lower() for w in Wrestler.objects.only("name")
    }
    existing_aliases = set()
    for w in Wrestler.objects.only("name", "aliases"):
        for a in (getattr(w, "aliases", "") or "").split(","):
            a = a.strip().lower()
            if a:
                existing_aliases.add(a)

    for slug in title_slugs:
        if total_queued >= max_unknown_to_queue:
            break
        finding = discover_from_title_history(slug)
        if finding is None:
            report[slug] = {"error": "no Wikipedia page found"}
            continue

        known = 0
        unknown: list[str] = []
        for name in finding.unique_champions:
            lower = name.lower()
            if lower in existing_names or lower in existing_aliases:
                known += 1
            else:
                unknown.append(name)

        # Cap how many we queue this run — keep within rate limits.
        budget = max(0, max_unknown_to_queue - total_queued)
        to_queue = unknown[:budget]
        if to_queue:
            fetch_wrestler_candidates(to_queue, force=False)
            total_queued += len(to_queue)

        report[slug] = {
            "resolved_wikipedia_title": finding.resolved_wikipedia_title,
            "source_url": finding.source_url,
            "champions_found": len(finding.unique_champions),
            "already_in_db": known,
            "queued_for_ingest": len(to_queue),
            "remaining_unknown": max(0, len(unknown) - len(to_queue)),
            "sample_queued": to_queue[:5],
        }
    report["__totals__"] = {
        "titles_processed": len([s for s in title_slugs if s in report]),
        "total_queued": total_queued,
    }
    return report


if __name__ == "__main__":  # pragma: no cover
    import sys
    args = sys.argv[1:]
    if args:
        f = discover_from_title_history(args[0])
        print(json.dumps(f.to_dict() if f else {"error": "not found"}, indent=2))
    else:
        result = discover_from_all_titles()
        for slug, f in result["by_title"].items():
            print(f"{slug:<30} {f.resolved_wikipedia_title:<55} {len(f.unique_champions)} champions")
        print(f"\nTotal unique names across all titles: {len(result['by_name'])}")
