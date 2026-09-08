"""
ProFightDB (Internet Wrestling Database) scraping adapter.

ProFightDB exposes detailed wrestler profiles + complete match histories.
For WrestleBot, it serves as a cross-validation source: birthdate, place
of birth, match count, and championship history can be reconciled against
Wikipedia and Cagematch.

robots.txt: not published. We follow general scraping etiquette:
    - Identifying User-Agent with contact URL.
    - 2-second minimum interval between requests.
    - Cache aggressively via SourceFetch.
    - Lookup-on-demand only — no bulk crawling.

Accuracy contract:
    PFDB data is community-curated, similar quality to Wikipedia. We
    treat it as one vote among several when reconciling fields. Any
    disagreement with Wikipedia + Cagematch logs an Earl observation
    rather than overwriting.
"""

from __future__ import annotations

import logging
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from bs4 import BeautifulSoup

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)


PFDB_BASE = "http://www.profightdb.com"
PFDB_SEARCH = f"{PFDB_BASE}/search.html?search-term={{q}}"
USER_AGENT = "Mozilla/5.0 (compatible; wrestlingdb-wrestlebot/1.0; +https://wrestlingdb.org)"
# ProFightDB is a scraping target, so we go slow. Shared limiter keyed
# `profightdb` enforces this across all Celery workers + the web process.
RATE_LIMIT_PER_SEC = 1.0 / 2.0


@dataclass
class PFDBSearchHit:
    """One search-result row."""
    name: str
    url: str
    promotion: str = ""  # PFDB shows current-promotion in parens after the name


@dataclass
class PFDBProfile:
    """A wrestler profile summary."""
    name: str
    url: str
    fields: dict = field(default_factory=dict)
    real_name: str = ""
    date_of_birth: str = ""
    place_of_birth: str = ""
    nationality: str = ""
    gender: str = ""
    matches_total: Optional[int] = None
    matches_ppv: Optional[int] = None
    ring_names: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    raw_snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "url": self.url,
            "fields": dict(self.fields),
            "real_name": self.real_name,
            "date_of_birth": self.date_of_birth,
            "place_of_birth": self.place_of_birth,
            "nationality": self.nationality,
            "gender": self.gender,
            "matches_total": self.matches_total,
            "matches_ppv": self.matches_ppv,
            "ring_names": self.ring_names,
            "titles": self.titles[:15],
            "raw_snippet": self.raw_snippet[:500],
        }


# ---------------------------------------------------------------- HTTP


def _http_get(url: str, timeout: float = 20.0) -> Optional[str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with rate_limited("profightdb", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning("ProFightDB HTTP %s for %s: %s", e.code, url, e.reason)
            return None
        except Exception as e:
            logger.warning("ProFightDB request failed for %s: %s", url, e)
            return None


# ---------------------------------------------------------------- search


_WRESTLER_HREF_RE = re.compile(r"^/wrestlers/[a-z0-9\-]+-\d+\.html$", re.IGNORECASE)


def search(query: str, limit: int = 10) -> list[PFDBSearchHit]:
    """
    Search wrestlers by name. Returns top hits.

    PFDB's search page shows a 'current roster' navigation block at the
    top followed by the actual search-match section. We filter out the
    roster by requiring the link text to share at least one significant
    token with the query.
    """
    if not query or not query.strip():
        return []
    query_tokens = {
        t.lower() for t in re.findall(r"[a-zA-Z0-9']{3,}", query)
    }
    if not query_tokens:
        return []
    url = PFDB_SEARCH.format(q=urllib.parse.quote_plus(query.strip()))
    html = _http_get(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    hits: list[PFDBSearchHit] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not _WRESTLER_HREF_RE.match(href):
            continue
        full = PFDB_BASE + href
        if full in seen:
            continue
        name = (a.get_text() or "").strip()
        if not name or len(name) < 2:
            continue
        # Only keep links whose visible name shares a significant token
        # with the search query — drops the navigation roster.
        name_tokens = {t.lower() for t in re.findall(r"[a-zA-Z0-9']{3,}", name)}
        if not (name_tokens & query_tokens):
            continue
        seen.add(full)
        promotion = ""
        nxt = a.next_sibling
        if nxt and getattr(nxt, "string", None):
            m = re.match(r"\s*\(([^)]+)\)", nxt.string)
            if m:
                promotion = m.group(1).strip()
        hits.append(PFDBSearchHit(name=name, url=full, promotion=promotion))
        if len(hits) >= max(1, min(limit, 25)):
            break
    return hits


# ---------------------------------------------------------------- profile


_INT_RE = re.compile(r"-?\d+")


def _to_int(s: str) -> Optional[int]:
    if not s:
        return None
    m = _INT_RE.search(s.replace(",", ""))
    return int(m.group(0)) if m else None


# Labels we extract from the inline-bold profile table. Order matters —
# the regex uses the next-label-or-end as a terminator, so listing them
# left-to-right means each value stops at the next label.
_PFDB_LABELS = (
    "Name", "Preferred Name", "Date Of Birth", "Place of Birth",
    "Nationality", "Gender", "Matches", "Ring Name(s)",
)


def _parse_profile_table(text: str) -> dict[str, str]:
    """
    PFDB renders the profile table as inline '<b>Label:</b> Value' chunks
    that collapse to one long line of text. Split it back into labelled
    fields using known label terminators.
    """
    out: dict[str, str] = {}
    # Build a regex like: (Name|Preferred Name|...):
    escaped = [re.escape(l) for l in _PFDB_LABELS]
    label_re = "(?:" + "|".join(escaped) + ")"
    # Match LABEL: VALUE-up-to-next-label-or-end.
    pattern = re.compile(
        rf"({label_re})\s*:\s*(.*?)\s*(?=(?:{label_re})\s*:|$)",
        re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        key = m.group(1).strip().lower()
        val = m.group(2).strip()
        if val:
            out[key] = val
    return out


def fetch_wrestler_profile(url: str) -> Optional[PFDBProfile]:
    """Fetch and parse a ProFightDB wrestler profile page."""
    if not url or "profightdb.com" not in url:
        return None
    html = _http_get(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")

    name = ""
    h1 = soup.find("h1")
    if h1:
        name = (h1.get_text() or "").strip()

    tables = soup.find_all("table")
    fields: dict[str, str] = {}
    if tables:
        # Profile data is in the first table on a successful profile page.
        first_text = tables[0].get_text(" ", strip=True)
        fields = _parse_profile_table(first_text)

    # Championship history is typically the second table.
    titles: list[str] = []
    if len(tables) >= 2:
        for line in tables[1].get_text("\n", strip=True).splitlines():
            line = line.strip()
            if line and 3 < len(line) < 120 and "match" not in line.lower():
                titles.append(line)
                if len(titles) >= 30:
                    break

    profile = PFDBProfile(name=name, url=url, fields=fields, titles=titles)

    profile.real_name = fields.get("name") or ""
    profile.date_of_birth = fields.get("date of birth") or ""
    profile.place_of_birth = fields.get("place of birth") or ""
    profile.nationality = fields.get("nationality") or ""
    profile.gender = fields.get("gender") or ""

    matches_raw = fields.get("matches") or ""
    if matches_raw:
        profile.matches_total = _to_int(matches_raw)
        ppv_match = re.search(r"\(\s*(\d+)\s*Pay Per View\s*\)", matches_raw, re.I)
        if ppv_match:
            profile.matches_ppv = int(ppv_match.group(1))

    ring_raw = fields.get("ring name(s)") or fields.get("ring names") or ""
    if ring_raw:
        profile.ring_names = [n.strip() for n in re.split(r"[,/;]", ring_raw) if n.strip()][:20]

    profile.raw_snippet = (tables[0].get_text(" ", strip=True)[:2000] if tables else "")
    return profile


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    args = sys.argv[1:] or ["Bret Hart"]
    hits = search(args[0], limit=3)
    print(f"{len(hits)} hits:")
    for h in hits:
        print(f"  {h.name}  ({h.promotion})  ->  {h.url}")
    if hits:
        prof = fetch_wrestler_profile(hits[0].url)
        if prof:
            print(json.dumps(prof.to_dict(), indent=2))
