"""
Upcoming-events scrapers for each major promotion.

Each promotion publishes its own schedule page in its own format. This
module exposes a uniform interface:

    fetch_upcoming(promotion_key) -> list[UpcomingEvent]

Currently supported promotion_key values:
    "wwe", "aew", "njpw"  — confirmed accessible
    "tna", "roh"          — TODO

STATUS / KNOWN LIMITATIONS (live-verified 2026-05):
    - WWE.com is heavily client-rendered: the public HTML contains dates
      (datetime= attributes) but the event names are populated by JS. The
      scraper below extracts what's reliably present in static HTML and
      will return dates with placeholder names like 'Tickets landing page'.
      Fixing this needs either (a) Playwright-backed fetcher, (b) WWE's
      internal JSON endpoint (no public docs), or (c) Wikipedia as a
      fallback for upcoming PPVs.
    - AEW + NJPW pages have similar quirks per-site.

For the immediate "ESPN feel" we ship the framework + WWE date harvest;
per-promotion tuning is a follow-up. The Match ingest pipeline (which
gives us recent + historic results) is higher value than client-rendered
upcoming-schedule pages.

Accuracy contract:
    Each event row carries the original source URL. Names and dates are
    taken verbatim from the source. We never invent attendance, results,
    or anything else — these are purely advertised schedule entries.
"""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from bs4 import BeautifulSoup

from ..rate_limit import rate_limited

logger = logging.getLogger(__name__)


USER_AGENT = "Mozilla/5.0 (compatible; wrestlingdb-wrestlebot/1.0; +https://wrestlingdb.org)"
# WWE/AEW/NJPW event pages share one bucket — they don't share IPs, but
# the value of being a polite scraper is the same.
RATE_LIMIT_PER_SEC = 1.0 / 2.5


@dataclass
class UpcomingEvent:
    promotion_key: str          # "wwe" / "aew" / "njpw" / ...
    name: str
    event_date: Optional[date]  # parsed local date when available
    event_datetime_iso: str = ""
    venue_name: str = ""
    city: str = ""
    country: str = ""
    source_url: str = ""

    def to_dict(self) -> dict:
        return {
            "promotion": self.promotion_key,
            "name": self.name,
            "event_date": self.event_date.isoformat() if self.event_date else "",
            "event_datetime_iso": self.event_datetime_iso,
            "venue_name": self.venue_name,
            "city": self.city,
            "country": self.country,
            "source_url": self.source_url,
        }


def _http_get(url: str) -> Optional[str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
    })
    with rate_limited("upcoming_events", per_second=RATE_LIMIT_PER_SEC):
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning("upcoming_events HTTP %s for %s: %s", e.code, url, e.reason)
            return None
        except Exception as e:
            logger.warning("upcoming_events request failed for %s: %s", url, e)
            return None


def _parse_iso_to_date(iso: str) -> Optional[date]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).date()
    except Exception:
        return None


# ---------------------------------------------------------------- WWE

WWE_EVENTS_URL = "https://www.wwe.com/events"


def fetch_wwe_upcoming() -> list[UpcomingEvent]:
    """
    Scrape WWE.com/events. Event cards expose ISO datetime via the
    `datetime=` attribute on a <time> element, plus venue + city on
    surrounding markup.
    """
    html = _http_get(WWE_EVENTS_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")

    out: list[UpcomingEvent] = []
    seen: set[tuple[str, str]] = set()

    # WWE renders each event as a Drupal "node" element. We use a generous
    # selector — any anchor with class containing 'event' and a sibling
    # <time> — and let de-duplication clean up. Fallback selector below.
    for node in soup.find_all(attrs={"datetime": True}):
        iso = node.get("datetime", "").strip()
        if not iso:
            continue
        # Walk up to find the event card container.
        card = node.find_parent("article") or node.find_parent("div") or node
        if card is None:
            continue
        # Name — prefer the headline link text.
        name = ""
        for selector in [
            lambda c: c.find("h2"), lambda c: c.find("h3"),
            lambda c: c.find("a", class_=re.compile(r"(title|headline)", re.I)),
            lambda c: c.find("a"),
        ]:
            try:
                el = selector(card)
            except Exception:
                el = None
            if el:
                name = (el.get_text() or "").strip()
                if name:
                    break
        if not name:
            continue
        # Venue / city — WWE wraps these in <div class="event-info"> or
        # <span class="venue">. Be lenient.
        venue = ""
        city = ""
        for el in card.find_all(["span", "div"]):
            cls = " ".join(el.get("class") or [])
            text = (el.get_text() or "").strip()
            if not text or len(text) > 200:
                continue
            low = cls.lower()
            if "venue" in low and not venue:
                venue = text
            elif ("city" in low or "location" in low) and not city:
                city = text
        key = (name, iso)
        if key in seen:
            continue
        seen.add(key)
        out.append(UpcomingEvent(
            promotion_key="wwe",
            name=name,
            event_date=_parse_iso_to_date(iso),
            event_datetime_iso=iso,
            venue_name=venue,
            city=city,
            country="",
            source_url=WWE_EVENTS_URL,
        ))
    return out


# ---------------------------------------------------------------- AEW

AEW_EVENTS_URL = "https://www.allelitewrestling.com/aew-events"


def fetch_aew_upcoming() -> list[UpcomingEvent]:
    """Scrape AEW's events listing."""
    html = _http_get(AEW_EVENTS_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[UpcomingEvent] = []
    seen: set[str] = set()

    # AEW uses similar pattern — look for time tags + nearby titles.
    for node in soup.find_all(attrs={"datetime": True}):
        iso = node.get("datetime", "").strip()
        if not iso:
            continue
        card = node.find_parent("article") or node.find_parent("div")
        if card is None:
            continue
        # Title — try anchors with title-like class first.
        name = ""
        for el in card.find_all(["h2", "h3", "h4", "a"]):
            text = (el.get_text() or "").strip()
            if text and 3 < len(text) < 200:
                name = text
                break
        if not name or name in seen:
            continue
        seen.add(name)
        # Venue + city pulled from any element with venue/location class.
        venue = ""
        city = ""
        for el in card.find_all(["span", "div", "p"]):
            cls = " ".join(el.get("class") or []).lower()
            t = (el.get_text() or "").strip()
            if not t or len(t) > 200:
                continue
            if "venue" in cls and not venue:
                venue = t
            elif ("city" in cls or "location" in cls) and not city:
                city = t
        out.append(UpcomingEvent(
            promotion_key="aew",
            name=name,
            event_date=_parse_iso_to_date(iso),
            event_datetime_iso=iso,
            venue_name=venue,
            city=city,
            source_url=AEW_EVENTS_URL,
        ))
    return out


# ---------------------------------------------------------------- NJPW

NJPW_SCHEDULE_URL = "https://www.njpw1972.com/schedule/"


def fetch_njpw_upcoming() -> list[UpcomingEvent]:
    """Scrape NJPW's schedule page."""
    html = _http_get(NJPW_SCHEDULE_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: list[UpcomingEvent] = []

    # NJPW renders schedule cards under .schedule__item with a .date and .title.
    for card in soup.select(".schedule__item, .event-list__item, article.event"):
        date_text = ""
        date_el = card.find(class_=re.compile(r"(date|day)", re.I)) or card.find("time")
        if date_el:
            date_text = (date_el.get_text() or "").strip()
        title_el = (card.find(class_=re.compile(r"(title|name)", re.I))
                   or card.find(["h2", "h3", "h4", "a"]))
        name = (title_el.get_text() or "").strip() if title_el else ""
        if not name:
            continue
        # Parse date — NJPW formats vary; best effort.
        ev_date: Optional[date] = None
        m = re.search(r"(\d{4})[\-./](\d{1,2})[\-./](\d{1,2})", date_text)
        if m:
            try:
                ev_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                ev_date = None
        venue_el = card.find(class_=re.compile(r"(venue|place|location)", re.I))
        venue = (venue_el.get_text() or "").strip() if venue_el else ""
        out.append(UpcomingEvent(
            promotion_key="njpw",
            name=name,
            event_date=ev_date,
            event_datetime_iso="",
            venue_name=venue,
            country="Japan",
            source_url=NJPW_SCHEDULE_URL,
        ))
    return out


# ---------------------------------------------------------------- dispatch

FETCHERS = {
    "wwe": fetch_wwe_upcoming,
    "aew": fetch_aew_upcoming,
    "njpw": fetch_njpw_upcoming,
}


def fetch_upcoming(promotion_key: str) -> list[UpcomingEvent]:
    fn = FETCHERS.get(promotion_key.lower())
    if not fn:
        raise ValueError(
            f"Unknown promotion_key={promotion_key!r}; "
            f"supported: {sorted(FETCHERS)}"
        )
    return fn()


def fetch_all_upcoming() -> dict[str, list[UpcomingEvent]]:
    """Run every supported fetcher in turn; returns {promotion_key: events}."""
    out: dict[str, list[UpcomingEvent]] = {}
    for key, fn in FETCHERS.items():
        try:
            out[key] = fn()
        except Exception as e:
            logger.warning("fetch_upcoming(%s) failed: %s", key, e)
            out[key] = []
    return out


if __name__ == "__main__":  # pragma: no cover
    import sys
    keys = sys.argv[1:] or sorted(FETCHERS)
    for k in keys:
        evs = fetch_upcoming(k)
        print(f"{k}: {len(evs)} upcoming events")
        for e in evs[:5]:
            print(f"  {e.event_date}  {e.name}  ({e.venue_name or '?'})")
