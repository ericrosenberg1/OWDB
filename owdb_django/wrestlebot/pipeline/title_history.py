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
#
# Coverage philosophy:
#   * Cover the major promotion lineages (WWE / WCW / ECW / AEW / TNA /
#     NWA / AWA / NJPW / AJPW / NOAH / ROH / CMLL / AAA / Stardom) end-
#     to-end: every long-running men's, women's, tag-team, and secondary
#     championship that has its own "List of X Champions" Wikipedia
#     article. Each is a notability-validated seed of dozens of wrestlers.
#   * Include defunct historical lineages (WCCW, Mid-South, Stampede,
#     UWF) that fed today's stars — the trainers of the 80s/90s came
#     from these territories.
#   * Each entry can list multiple title fallbacks — Wikipedia
#     occasionally renames pages (e.g. "IWGP Heavyweight" → "IWGP
#     World Heavyweight"). The ingester tries each in order.
#
# Skipping a belt is harmless: if no fallback resolves to a real page,
# `_first_existing` returns None and we move on. Adding speculative
# slugs is therefore safe.
TITLE_HISTORY_PAGES: dict[str, tuple[str, ...]] = {
    # =======================================================================
    # WWE / WWF — flagship + secondaries + brand-split women's + tag
    # =======================================================================
    "wwe_championship":             ("List of WWE Champions",),
    "wwe_universal":                ("List of WWE Universal Champions",),
    "wwe_intercontinental":         ("List of WWE Intercontinental Champions",),
    "wwe_united_states":            ("List of WWE United States Champions",),
    "wwe_womens":                   ("List of WWE Women's Champions",
                                     "List of WWE Women's Champions (1956-2010)"),
    "wwe_raw_womens":               ("List of WWE Raw Women's Champions",),
    "wwe_smackdown_womens":         ("List of WWE SmackDown Women's Champions",),
    "wwe_womens_tag_team":          ("List of WWE Women's Tag Team Champions",),
    "wwe_tag_team":                 ("List of WWE Tag Team Champions",),
    "wwe_world_tag_team":           ("List of WWE World Tag Team Champions",),
    "wwe_speed":                    ("List of WWE Speed Champions",
                                     "WWE Speed Championship"),
    # ---- WWE defunct / classic belts -------------------------------------
    "wwe_european":                 ("List of WWE European Champions",
                                     "WWE European Championship"),
    "wwe_hardcore":                 ("List of WWE Hardcore Champions",
                                     "WWE Hardcore Championship"),
    "wwe_light_heavyweight":        ("List of WWE Light Heavyweight Champions",
                                     "WWE Light Heavyweight Championship"),
    "wwe_cruiserweight":            ("List of WWE Cruiserweight Champions",
                                     "WWE Cruiserweight Championship"),
    "wwe_24_7":                     ("List of WWE 24/7 Champions",
                                     "WWE 24/7 Championship"),
    "wwe_million_dollar":           ("List of Million Dollar Champions",
                                     "Million Dollar Championship"),

    # =======================================================================
    # NXT — WWE's developmental brand has its own deep lineage
    # =======================================================================
    "nxt_championship":             ("List of NXT Champions",
                                     "NXT Championship"),
    "nxt_north_american":           ("List of NXT North American Champions",
                                     "NXT North American Championship"),
    "nxt_womens":                   ("List of NXT Women's Champions",
                                     "NXT Women's Championship"),
    "nxt_womens_north_american":    ("List of NXT Women's North American Champions",
                                     "NXT Women's North American Championship"),
    "nxt_tag_team":                 ("List of NXT Tag Team Champions",
                                     "NXT Tag Team Championship"),
    "nxt_uk":                       ("List of NXT UK Champions",
                                     "NXT United Kingdom Championship",
                                     "NXT UK Championship"),
    "nxt_uk_womens":                ("List of NXT UK Women's Champions",
                                     "NXT UK Women's Championship"),
    "nxt_uk_tag_team":              ("List of NXT UK Tag Team Champions",
                                     "NXT UK Tag Team Championship"),

    # =======================================================================
    # WCW — historic Atlanta lineage that fed the Monday Night Wars
    # =======================================================================
    "wcw_world_heavyweight":        ("List of WCW World Heavyweight Champions",),
    "wcw_united_states":            ("List of WCW United States Heavyweight Champions",),
    "wcw_world_television":         ("List of WCW World Television Champions",),
    "wcw_tag_team":                 ("List of WCW World Tag Team Champions",
                                     "WCW World Tag Team Championship"),
    "wcw_cruiserweight":            ("List of WCW Cruiserweight Champions",
                                     "WCW Cruiserweight Championship"),
    "wcw_hardcore":                 ("List of WCW Hardcore Champions",
                                     "WCW Hardcore Championship"),
    "wcw_international":            ("List of WCW International World Heavyweight Champions",
                                     "WCW International World Heavyweight Championship"),
    "wcw_light_heavyweight":        ("List of WCW Light Heavyweight Champions",
                                     "WCW Light Heavyweight Championship"),
    "wcw_womens":                   ("List of WCW Women's Champions",
                                     "WCW Women's Championship"),

    # =======================================================================
    # ECW — Philadelphia hardcore lineage
    # =======================================================================
    "ecw_world":                    ("List of ECW World Heavyweight Champions",),
    "ecw_world_television":         ("List of ECW World Television Champions",
                                     "ECW World Television Championship"),
    "ecw_world_tag_team":           ("List of ECW World Tag Team Champions",
                                     "ECW World Tag Team Championship"),
    "ecw_ftw":                      ("List of FTW Champions",
                                     "FTW Championship"),

    # =======================================================================
    # AEW — full active singles + tag + trios + ROH belts (AEW owns ROH)
    # =======================================================================
    "aew_world":                    ("List of AEW World Champions",
                                     "AEW World Championship"),
    "aew_womens_world":             ("List of AEW Women's World Champions",
                                     "AEW Women's World Championship"),
    "aew_tnt":                      ("List of AEW TNT Champions",
                                     "AEW TNT Championship"),
    "aew_tbs":                      ("List of AEW TBS Champions",
                                     "AEW TBS Championship"),
    "aew_international":            ("List of AEW International Champions",
                                     "AEW International Championship",
                                     "AEW All-Atlantic Championship"),
    "aew_continental":              ("List of AEW Continental Champions",
                                     "AEW Continental Championship",
                                     "AEW Continental Classic"),
    "aew_world_tag_team":           ("List of AEW World Tag Team Champions",
                                     "AEW World Tag Team Championship"),
    "aew_world_trios":              ("List of AEW World Trios Champions",
                                     "AEW World Trios Championship"),

    # =======================================================================
    # TNA / Impact — Nashville + Orlando + Impact era
    # =======================================================================
    "tna_world":                    ("List of TNA World Heavyweight Champions",
                                     "TNA World Championship",
                                     "TNA World Heavyweight Championship"),
    "tna_knockouts":                ("List of TNA Knockouts Champions",
                                     "TNA Knockouts Championship"),
    "tna_x_division":               ("List of TNA X Division Champions",
                                     "TNA X Division Championship",
                                     "Impact X Division Championship"),
    "tna_tag_team":                 ("List of TNA World Tag Team Champions",
                                     "TNA World Tag Team Championship"),
    "tna_knockouts_tag":            ("List of TNA Knockouts Tag Team Champions",
                                     "TNA Knockouts Tag Team Championship"),
    "tna_digital_media":            ("List of Impact Digital Media Champions",
                                     "Impact Digital Media Championship"),

    # =======================================================================
    # NWA — historic + current lineage; ~100 champions across the decades
    # =======================================================================
    "nwa_world_heavyweight":        ("List of NWA World Heavyweight Champions",),
    "nwa_world_tag_team":           ("List of NWA World Tag Team Champions",
                                     "NWA World Tag Team Championship"),
    "nwa_world_television":         ("List of NWA World Television Champions",
                                     "NWA World Television Championship"),
    "nwa_world_junior":             ("List of NWA World Junior Heavyweight Champions",
                                     "NWA World Junior Heavyweight Championship"),
    "nwa_worlds_womens":            ("List of NWA Worlds Women's Champions",
                                     "NWA World Women's Championship"),
    "nwa_united_states":            ("List of NWA United States Heavyweight Champions",
                                     "NWA United States Heavyweight Championship"),

    # =======================================================================
    # AWA — Minneapolis-based; Verne Gagne's promotion (1960-1991)
    # =======================================================================
    "awa_world_heavyweight":        ("List of AWA World Heavyweight Champions",
                                     "AWA World Heavyweight Championship"),
    "awa_world_tag_team":           ("List of AWA World Tag Team Champions",
                                     "AWA World Tag Team Championship"),
    "awa_world_womens":             ("List of AWA World Women's Champions",
                                     "AWA World Women's Championship"),

    # =======================================================================
    # World Class / WCCW — Dallas territory; the Von Erichs
    # =======================================================================
    "wccw_world_heavyweight":       ("List of WCCW World Heavyweight Champions",
                                     "WCCW World Heavyweight Championship",
                                     "NWA American Heavyweight Championship"),
    "wccw_world_tag_team":          ("List of WCCW World Tag Team Champions",
                                     "WCCW World Tag Team Championship"),
    "wccw_world_six_man":           ("WCCW World Six-Man Tag Team Championship",),

    # =======================================================================
    # Mid-South / UWF — Bill Watts' territory
    # =======================================================================
    "mid_south_north_american":     ("Mid-South North American Heavyweight Championship",
                                     "List of Mid-South North American Heavyweight Champions"),
    "uwf_heavyweight":              ("UWF Heavyweight Championship",
                                     "UWF World Heavyweight Championship"),

    # =======================================================================
    # Stampede Wrestling — Calgary; the Hart Family's home territory
    # =======================================================================
    "stampede_north_american":      ("Stampede Wrestling North American Heavyweight Championship",
                                     "Stampede North American Heavyweight Championship"),
    "stampede_international_tag":   ("Stampede Wrestling International Tag Team Championship",),

    # =======================================================================
    # NJPW — New Japan; the marquee Japanese lineage
    # =======================================================================
    "iwgp_heavyweight":             ("List of IWGP Heavyweight Champions",
                                     "List of IWGP World Heavyweight Champions",
                                     "IWGP World Heavyweight Championship"),
    "iwgp_intercontinental":        ("List of IWGP Intercontinental Champions",
                                     "IWGP Intercontinental Championship"),
    "iwgp_jr_heavyweight":          ("List of IWGP Junior Heavyweight Champions",
                                     "IWGP Junior Heavyweight Championship"),
    "iwgp_tag_team":                ("List of IWGP Tag Team Champions",
                                     "IWGP Tag Team Championship"),
    "iwgp_jr_tag_team":             ("List of IWGP Junior Heavyweight Tag Team Champions",
                                     "IWGP Junior Heavyweight Tag Team Championship"),
    "iwgp_united_states":           ("List of IWGP United States Heavyweight Champions",
                                     "IWGP United States Heavyweight Championship"),
    "never_openweight":             ("List of NEVER Openweight Champions",
                                     "NEVER Openweight Championship"),
    "never_openweight_six_man":     ("NEVER Openweight 6-Man Tag Team Championship",
                                     "NEVER Openweight Six-Man Tag Team Championship"),

    # =======================================================================
    # AJPW — All Japan Pro Wrestling
    # =======================================================================
    "ajpw_triple_crown":            ("List of Triple Crown Heavyweight Champions",
                                     "Triple Crown Heavyweight Championship"),
    "ajpw_world_tag_team":          ("List of World Tag Team Champions (AJPW)",
                                     "World Tag Team Championship (AJPW)",
                                     "AJPW World Tag Team Championship"),
    "ajpw_junior_heavyweight":      ("List of AJPW World Junior Heavyweight Champions",
                                     "AJPW World Junior Heavyweight Championship",
                                     "World Junior Heavyweight Championship (AJPW)"),
    "ajpw_jr_tag_team":             ("AJPW All Asia Tag Team Championship",
                                     "All Asia Tag Team Championship"),

    # =======================================================================
    # NOAH — Pro Wrestling Noah
    # =======================================================================
    "noah_ghc_heavyweight":         ("List of GHC Heavyweight Champions",
                                     "GHC Heavyweight Championship"),
    "noah_ghc_jr_heavyweight":      ("List of GHC Junior Heavyweight Champions",
                                     "GHC Junior Heavyweight Championship"),
    "noah_ghc_national":            ("GHC National Championship",
                                     "List of GHC National Champions"),
    "noah_ghc_tag_team":            ("List of GHC Tag Team Champions",
                                     "GHC Tag Team Championship"),
    "noah_ghc_jr_tag_team":         ("List of GHC Junior Heavyweight Tag Team Champions",
                                     "GHC Junior Heavyweight Tag Team Championship"),

    # =======================================================================
    # ROH — Ring of Honor (now under AEW ownership)
    # =======================================================================
    "roh_world":                    ("List of ROH World Champions",
                                     "ROH World Championship"),
    "roh_world_television":         ("List of ROH World Television Champions",
                                     "ROH World Television Championship"),
    "roh_world_tag_team":           ("List of ROH World Tag Team Champions",
                                     "ROH World Tag Team Championship"),
    "roh_world_six_man":            ("List of ROH World Six-Man Tag Team Champions",
                                     "ROH World Six-Man Tag Team Championship"),
    "roh_pure":                     ("List of ROH Pure Champions",
                                     "ROH Pure Championship"),
    "roh_womens_world":             ("List of ROH Women's World Champions",
                                     "ROH Women's World Championship"),

    # =======================================================================
    # CMLL / AAA — Mexican lineages (Lucha Libre)
    # =======================================================================
    "cmll_world_heavyweight":       ("List of CMLL World Heavyweight Champions",),
    "cmll_world_tag_team":          ("CMLL World Tag Team Championship",
                                     "List of CMLL World Tag Team Champions"),
    "cmll_world_trios":             ("CMLL World Trios Championship",
                                     "List of CMLL World Trios Champions"),
    "cmll_world_welterweight":      ("CMLL World Welterweight Championship",
                                     "List of CMLL World Welterweight Champions"),
    "cmll_world_middleweight":      ("CMLL World Middleweight Championship",
                                     "List of CMLL World Middleweight Champions"),
    "cmll_world_lightweight":       ("CMLL World Lightweight Championship",
                                     "List of CMLL World Lightweight Champions"),
    "cmll_world_light_heavyweight": ("CMLL World Light Heavyweight Championship",
                                     "List of CMLL World Light Heavyweight Champions"),
    "aaa_mega":                     ("List of AAA Mega Champions",
                                     "AAA Mega Championship"),
    "aaa_latin_american":           ("AAA Latin American Championship",
                                     "List of AAA Latin American Champions"),
    "aaa_reina_de_reinas":          ("AAA Reina de Reinas Championship",
                                     "List of AAA Reina de Reinas Champions"),
    "aaa_world_tag_team":           ("AAA World Tag Team Championship",
                                     "List of AAA World Tag Team Champions"),
    "aaa_world_trios":              ("AAA World Trios Championship",
                                     "List of AAA World Trios Champions"),

    # =======================================================================
    # Stardom — premier joshi (women's) promotion
    # =======================================================================
    "stardom_world":                ("World of Stardom Championship",
                                     "List of World of Stardom Champions"),
    "stardom_world_wonder":         ("Wonder of Stardom Championship",
                                     "List of Wonder of Stardom Champions"),
    "stardom_high_speed":           ("High Speed Championship",
                                     "List of High Speed Champions"),
    "stardom_artist_of_stardom":    ("Artist of Stardom Championship",
                                     "List of Artist of Stardom Champions"),
    "stardom_goddess_of_stardom":   ("Goddess of Stardom Championship",
                                     "List of Goddess of Stardom Champions"),
    "stardom_future_of_stardom":    ("Future of Stardom Championship",
                                     "List of Future of Stardom Champions"),

    # =======================================================================
    # Other notable indie + international titles
    # =======================================================================
    "pwg_world":                    ("List of PWG World Champions",
                                     "PWG World Championship"),
    "pwg_world_tag_team":           ("PWG World Tag Team Championship",
                                     "List of PWG World Tag Team Champions"),
    "mlw_world_heavyweight":        ("List of MLW World Heavyweight Champions",
                                     "MLW World Heavyweight Championship"),
    "mlw_national_openweight":      ("MLW National Openweight Championship",),
    "mlw_world_middleweight":       ("MLW World Middleweight Championship",),
    "gcw_world":                    ("List of GCW World Champions",
                                     "GCW World Championship",
                                     "Game Changer Wrestling World Championship"),
    "deathmatch_gcw":               ("List of GCW World Title Champions",
                                     "GCW World Championship"),
    "njpw_strong_openweight":       ("NJPW Strong Openweight Championship",),
    "njpw_strong_openweight_tag":   ("NJPW Strong Openweight Tag Team Championship",),

    # =======================================================================
    # Halls of fame — non-belt lineages with lots of notability-validated
    # wrestler names. Treat like a mega-list for discovery purposes.
    #
    # Round-2 codex flagged: WWE HOF (and a few others) include celebrity
    # inductees who are NOT pro wrestlers (Drew Carey, Bob Uecker, Pete
    # Rose, Donald Trump). The discovery loop skips slugs in
    # `_HOF_DISCOVERY_SLUGS` for naive queueing — instead the inductee
    # must pass the per-page classifier (Infobox Wrestler / wrestling
    # categories) before a Wrestler row is persisted. Catching errors at
    # *persist* time is already done by the contract; flagging at
    # *queue* time prevents wasted API calls and Earl flag noise.
    # =======================================================================
    "wwe_hall_of_fame":             ("List of WWE Hall of Fame inductees",),
    "pwhof":                        ("Professional Wrestling Hall of Fame and Museum",),
    "wcw_hall_of_fame":             ("WCW Hall of Fame",),
    "wonf4w_hall_of_fame":          ("Wrestling Observer Newsletter Hall of Fame",),
    "japanese_wrestling_hof":       ("Wrestling Observer Newsletter Hall of Fame",
                                     "Tokyo Sports Puroresu Awards"),
    "lucha_hall_of_fame":           ("WON Hall of Fame",
                                     "Wrestling Observer Newsletter Hall of Fame"),
}


# Slugs whose pages mix wrestlers with celebrity inductees / honorees.
# The discovery loop applies a per-page classification gate before
# queueing names from these slugs, to avoid creating SourceFetch rows
# for Bob Uecker / Drew Carey / Pete Rose under `entity_type='wrestler'`.
_HOF_DISCOVERY_SLUGS = frozenset({
    "wwe_hall_of_fame",
    "pwhof",
    "wcw_hall_of_fame",
    "wonf4w_hall_of_fame",
    "japanese_wrestling_hof",
    "lucha_hall_of_fame",
})


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
    # Round-2 fix: generic concept names that would otherwise pass the
    # display-text gate when they appear in older title-history tables
    # (e.g. historical "Tag team" placeholder rows).
    "tag team", "tag teams", "stable", "manager", "managers",
    "promoter", "referee", "announcer", "valet",
}
_NON_WRESTLER_TOKENS = (
    "championship", "title", "tournament", "promotion",
    "association", "federation",
    # Round-2 fix: concept-page suffixes that frequently appear in display
    # text and would slip past the literal-name gate.
    " (professional wrestling)", " (wrestling)",
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


def _link_targets_for_name_cell(ctx: dict) -> list[str]:
    """
    Return all usable Wikipedia article titles linked by the Champion
    cell. Multiple targets are emitted for tag/trios champion rows where
    the cell has one ``<a>`` per partner.

    Round-2 fix (codex + claude both flagged): the previous helper only
    returned the FIRST link, silently dropping tag-team partners ("Bret
    Hart & Jim Neidhart" emitted only Bret). The new shape lets the
    extractor surface every named champion in the cell.

    Each target is validated to be:
      * a /wiki/ link (not external, not edit / redlink)
      * NOT in a non-article namespace (Category, File, etc.)
      * NOT a generic concept page per classifier.is_generic_wiki_title
        (gates /wiki/Tag_team, /wiki/Stable_(professional_wrestling),
        list pages, disambiguation pages)
    """
    # Local import — classifier imports persist paths; module-level
    # import would create a cycle.
    from .classifier import is_generic_wiki_title

    cells = ctx.get("__cells__") or ()
    idx = (ctx.get("__col_index__") or {}).get("name")
    if idx is None or idx >= len(cells):
        return []
    anchors = cells[idx].find_all("a", href=True)
    targets: list[str] = []
    for a in anchors:
        if "new" in (a.get("class") or []):
            continue  # red link
        href = a["href"]
        if not href.startswith(_WIKI_LINK_PREFIX):
            continue
        target = href[len(_WIKI_LINK_PREFIX):].split("#", 1)[0].split("?", 1)[0]
        if not target:
            continue
        if any(target.startswith(ns) for ns in _WIKI_NAMESPACES_TO_SKIP):
            continue
        decoded = urllib.parse.unquote(target).replace("_", " ")
        if is_generic_wiki_title(decoded):
            # Concept page (/wiki/Tag_team, /wiki/Manager_(professional_wrestling))
            # — never a wrestler.
            continue
        # Skip team/disambig suffixes that survived is_generic_wiki_title
        # — articles like "The New Day (professional wrestling)" link to
        # a tag-team article, not a wrestler.
        low = decoded.lower()
        if any(t in low for t in _NON_WRESTLER_TOKENS):
            continue
        if decoded not in targets:
            targets.append(decoded)
    return targets


def _link_target_for_name_cell(ctx: dict) -> Optional[str]:
    """Back-compat single-target helper — returns the first valid link."""
    targets = _link_targets_for_name_cell(ctx)
    return targets[0] if targets else None


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

    Round-2 fix: a second pass collects EVERY valid wiki link in each
    champion cell, so tag-team and trios partners aren't silently
    dropped. The framework's `_clean_champion_name` still returns the
    first link as the primary row, but here we walk every cell again
    and yield additional anchors as separate entries. Each candidate
    name is run through the same generic-title / non-wrestler filters
    the cleaner uses, so noise can't leak in via this path.

    Returns (ordered_unique_names, total_rows_seen).
    """
    from bs4 import BeautifulSoup
    seen: dict[str, None] = {}  # ordered set

    # Pass 1: framework extract (back-compat path).
    for row, _snippets in extract_tables(html, _CHAMPION_SPEC):
        seen.setdefault(row.name, None)

    # Pass 2: walk every champion cell for additional <a> links.
    soup = BeautifulSoup(html or "", "lxml")
    for table in soup.find_all("table"):
        if not _is_champion_table(table):
            continue
        rows = table.find_all("tr")
        if len(rows) < 2:
            continue
        headers = [
            (c.get_text(" ", strip=True) or "").strip().lower().rstrip(":")
            for c in rows[0].find_all(["th", "td"])
        ]
        name_col_idx = next(
            (i for i, h in enumerate(headers) if h in _CHAMPION_HEADERS), None,
        )
        if name_col_idx is None:
            continue

        # Reuse the multi-target gate by constructing a minimal ctx.
        for tr in rows[1:]:
            cells = tr.find_all(["td", "th"])
            if name_col_idx >= len(cells):
                continue
            row_cell_texts = [c.get_text(" ", strip=True) for c in cells]
            row_ctx = {
                "__cells__": cells,
                "__cell_texts__": row_cell_texts,
                "__col_index__": {"name": name_col_idx},
            }
            # Reign-row filter — skip header sub-rows that don't carry data.
            if not _keep_real_reign_row(row_ctx):
                continue
            for target in _link_targets_for_name_cell(row_ctx):
                # Apply the same length / sanity gates as _clean_champion_name
                # so a junk link can't sneak in via this path.
                if not (3 <= len(target) <= 80):
                    continue
                low = target.lower()
                if low in _NON_WRESTLER_NAMES:
                    continue
                if any(t in low for t in _NON_WRESTLER_TOKENS):
                    continue
                seen.setdefault(target, None)

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

        # Round-2 fix: Hall-of-Fame lists mix wrestlers with celebrity
        # honorees (Drew Carey, Bob Uecker, Pete Rose). Tag those slugs
        # so the downstream classify-on-fetch path knows to require
        # stronger wrestler-evidence before persisting. The
        # `from_hof_discovery=True` flag is read by fetch_wrestler_candidates
        # (and falls through harmlessly if that helper doesn't yet
        # consume it — Earl will catch persisted non-wrestlers).
        from_hof = slug in _HOF_DISCOVERY_SLUGS

        if to_queue:
            try:
                fetch_wrestler_candidates(
                    to_queue, force=False, from_hof_discovery=from_hof,
                )
            except TypeError:
                # Back-compat: older fetch_wrestler_candidates signature
                # doesn't accept the kwarg. The classifier still gates
                # at persist time so accuracy is preserved.
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
