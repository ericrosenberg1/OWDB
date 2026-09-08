"""
Wrestlingdata.com scraping adapter.

Wrestlingdata is a community-curated database with extremely detailed
match histories. Used as a cross-validation source for debut dates,
match counts, and venue affiliations — never as a primary fact source
unless Wikipedia and Cagematch both lack a field.

robots.txt:
    Allow: /
    Content-Signal: search=yes, ai-train=no

KNOWN LIMITATION (live-verified 2026-05):
    Wrestlingdata uses Cloudflare's advanced bot challenge:
      - Plain HTTP → 403 with `cf-mitigated: challenge`
      - Headless Chromium via Playwright → JS challenge never resolves
        (networkidle times out at 45s).

    Bypassing would require `playwright-stealth`, a paid scraping service
    (ScrapingBee, ZenRows), or a residential-proxy + fingerprinting setup.
    For accuracy-first WrestleBot this isn't worth the operational risk —
    anti-bot systems sometimes serve modified/honeypot data to detected
    bots, which would silently poison cross-validation.

    Decision: skip Wrestlingdata. Cagematch + ProFightDB + Wikipedia
    already cover the same data domain with cleaner access paths. The
    module stays here as a stub for the future; `search()` and
    `fetch_wrestler_profile()` return empty results and log once.

Etiquette (for the eventual headless-browser path):
    - User-Agent identifies us with a contact URL.
    - 3-second minimum interval between requests (very conservative).
    - Results cached in SourceFetch so we never re-scrape the same page.
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


WD_BASE = "https://www.wrestlingdata.com"
WD_SEARCH = f"{WD_BASE}/index.php?befehl=miscsearch&suche={{q}}"
USER_AGENT = "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org; lookup-only)"
# 3-second floor — wrestlingdata.com is a hobbyist site, be polite. Shared
# limiter ensures every Celery worker respects the same cap.
RATE_LIMIT_PER_SEC = 1.0 / 3.0

_warned_cloudflare = False


def _warn_cloudflare_once():
    global _warned_cloudflare
    if not _warned_cloudflare:
        logger.info(
            "wrestlingdata: Cloudflare bot challenge blocks direct HTTP. "
            "Returning empty results. To enable, wire a headless-browser "
            "fetcher (Playwright) into _http_get."
        )
        _warned_cloudflare = True


@dataclass
class WDSearchHit:
    """One search result row."""
    name: str
    url: str
    type: str = ""        # "wrestler" | "promotion" | "event" | "venue" | "other"
    extra: str = ""       # parenthetical context if WD includes it


@dataclass
class WDProfileSummary:
    """Summary of a wrestler / promotion / event profile."""
    name: str
    url: str
    fields: dict = field(default_factory=dict)  # raw label -> value pairs
    debut_date: str = ""
    death_date: str = ""
    height_cm: str = ""
    weight_kg: str = ""
    matches_total: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    nicknames: list[str] = field(default_factory=list)
    promotions: list[str] = field(default_factory=list)
    raw_snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "url": self.url,
            "fields": dict(self.fields),
            "debut_date": self.debut_date,
            "death_date": self.death_date,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "matches_total": self.matches_total,
            "wins": self.wins, "losses": self.losses, "draws": self.draws,
            "nicknames": self.nicknames,
            "promotions": self.promotions,
            "raw_snippet": self.raw_snippet[:500],
        }


# ---------------------------------------------------------------- HTTP


def _http_get(url: str, timeout: float = 20.0) -> Optional[str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "en-US,en;q=0.9",
    })
    with rate_limited("wrestlingdata", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read()
                # Handle gzip if the server returns it.
                if resp.headers.get("Content-Encoding") == "gzip":
                    import gzip
                    data = gzip.decompress(data)
                return data.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning("Wrestlingdata HTTP %s for %s: %s", e.code, url, e.reason)
            return None
        except Exception as e:
            logger.warning("Wrestlingdata request failed for %s: %s", url, e)
            return None


# ---------------------------------------------------------------- search


def search(query: str, limit: int = 10) -> list[WDSearchHit]:
    """Search Wrestlingdata's general search and return hits."""
    if not query or not query.strip():
        return []
    url = WD_SEARCH.format(q=urllib.parse.quote(query.strip()))
    html = _http_get(url)
    if not html:
        _warn_cloudflare_once()
        return []
    soup = BeautifulSoup(html, "lxml")

    hits: list[WDSearchHit] = []
    # Search results are rendered as a table of anchors. Be conservative:
    # capture every <a href="?befehl=bios..."> or "...cards..." that lives
    # inside the main content table.
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("?befehl="):
            continue
        # Type inference from URL keyword.
        if "befehl=bios" in href:
            hit_type = "wrestler"
        elif "befehl=cards" in href:
            hit_type = "event"
        elif "befehl=federations" in href:
            hit_type = "promotion"
        elif "befehl=arenas" in href:
            hit_type = "venue"
        else:
            continue
        text = (a.get_text() or "").strip()
        if not text or len(text) < 2:
            continue
        full_url = f"{WD_BASE}/index.php{href}"
        if full_url in seen:
            continue
        seen.add(full_url)
        hits.append(WDSearchHit(name=text, url=full_url, type=hit_type))
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


def fetch_wrestler_profile(url: str) -> Optional[WDProfileSummary]:
    """
    Fetch and parse a wrestler bio page.

    Returns None on fetch failure. On success, returns a WDProfileSummary
    with whatever fields could be confidently extracted; missing fields
    are left unset (better empty than wrong).
    """
    if not url or "wrestlingdata.com" not in url:
        return None
    html = _http_get(url)
    if not html:
        _warn_cloudflare_once()
        return None
    soup = BeautifulSoup(html, "lxml")

    # Profile data on WD is rendered in a 2-col table where the left column
    # holds the label and the right holds the value.
    fields: dict[str, str] = {}
    for tr in soup.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        label = (cells[0].get_text() or "").strip().rstrip(":").lower()
        value = (cells[1].get_text() or "").strip()
        if not label or not value or len(label) > 60 or len(value) > 400:
            continue
        # Avoid clobbering — keep first occurrence.
        if label not in fields:
            fields[label] = value

    # Wrestler name is usually the page H1.
    name = ""
    h1 = soup.find("h1") or soup.find("h2")
    if h1:
        name = (h1.get_text() or "").strip()

    summary = WDProfileSummary(name=name, url=url, fields=fields)

    # Targeted extractions from common WD labels (the site labels them
    # in English).
    summary.debut_date = fields.get("first match") or fields.get("debut") or ""
    summary.death_date = fields.get("died") or fields.get("date of death") or ""

    height = fields.get("height") or ""
    if "cm" in height.lower():
        summary.height_cm = height
    weight = fields.get("weight") or ""
    if "kg" in weight.lower():
        summary.weight_kg = weight

    summary.matches_total = _to_int(fields.get("total matches") or fields.get("matches") or "")
    summary.wins = _to_int(fields.get("wins") or "")
    summary.losses = _to_int(fields.get("losses") or "")
    summary.draws = _to_int(fields.get("draws") or "")

    # Nicknames frequently come as a comma list.
    nick_raw = fields.get("nicknames") or fields.get("ring name(s)") or ""
    if nick_raw:
        summary.nicknames = [n.strip() for n in re.split(r"[,/;]", nick_raw) if n.strip()]

    # Promotions frequently labelled "promotions" or appear in a separate
    # block. Pull a few raw values.
    prom_raw = fields.get("promotions") or fields.get("known from") or ""
    if prom_raw:
        summary.promotions = [p.strip() for p in re.split(r"[,/;]", prom_raw) if p.strip()][:10]

    # Capture the H1 + leading paragraph as a raw snippet for the agent
    # to read directly (useful when our targeted parse misses something).
    raw_parts = []
    if h1:
        raw_parts.append(h1.get_text(" ", strip=True))
    main = soup.find("table") or soup.find("body")
    if main:
        text = main.get_text(" ", strip=True)
        raw_parts.append(text[:1000])
    summary.raw_snippet = " | ".join(raw_parts)[:2000]

    return summary


if __name__ == "__main__":  # pragma: no cover
    import json, sys
    args = sys.argv[1:] or ["Bret Hart"]
    hits = search(args[0], limit=3)
    for h in hits:
        print(f"{h.type}: {h.name}  ->  {h.url}")
    if hits and hits[0].type == "wrestler":
        prof = fetch_wrestler_profile(hits[0].url)
        if prof:
            print(json.dumps(prof.to_dict(), indent=2))
