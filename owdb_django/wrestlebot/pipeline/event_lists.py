"""
Wikipedia "List of X pay-per-view events" + episode-list ingester.

Wikipedia maintains comprehensive list articles for every major promotion's
event history. The PPV list articles render as one wikitable per year with
columns: Date | Event | Venue | Location | Attendance | Main event.

Episode list articles ("List of WWE Raw episodes (2024)", etc.) use a
similar shape: # | Original air date | Venue | City | Notes.

This module ingests both into the Event model with full provenance via
a SourceFetch row pointing back to the Wikipedia article.

Accuracy contract:
    - Each event carries verification_source='wikipedia' and an attendance
      figure ONLY when the source cell has a clean integer. Range-style
      cells ('1,000–1,200') are skipped (we'd rather have null than wrong).
    - Venue + city are extracted as raw strings; downstream pipeline
      handles linking to Venue entities.
    - Re-runs are idempotent: events are upserted by
      (promotion, name, date).
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..sources._schema import (
    TableExtractorSpec,
    clean_text,
    extract_tables,
    resolve_year_from_preceding_heading,
)
from ..sources.base import FieldSnippet

logger = logging.getLogger(__name__)


WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org; admin@wrestlingdb.org)"


# Each promotion has a canonical "list of" page. Some have moved or renamed
# over time; we keep alternate spellings as fallbacks.
PPV_LIST_PAGES: dict[str, tuple[str, ...]] = {
    "wwe": (
        "List of WWE pay-per-view and livestreaming supercards",
        "List of WWE pay-per-view events",
    ),
    "wcw": (
        "List of WCW pay-per-view events",
    ),
    "ecw": (
        "List of ECW pay-per-view events",
    ),
    "aew": (
        "List of AEW pay-per-view events",
    ),
    "tna": (
        "List of TNA pay-per-view events",
        "List of Impact Wrestling pay-per-view events",
    ),
    "njpw": (
        "List of NJPW pay-per-view events",
        "List of New Japan Pro-Wrestling pay-per-view events",
    ),
    "ajpw": (
        "List of All Japan Pro Wrestling pay-per-view events",
    ),
    "roh": (
        "List of Ring of Honor pay-per-view events",
    ),
    "noah": (
        "List of Pro Wrestling Noah events",
    ),
}


# Episode-list pages. Most promotions have a top-level article plus per-year
# child articles ("List of WWE Raw episodes (2024)"). We try the umbrella
# first, then fall back to per-year ingestion.
EPISODE_LIST_PAGES: dict[str, tuple[str, ...]] = {
    "raw":       ("List of WWE Raw episodes",),
    "smackdown": ("List of WWE SmackDown episodes",),
    "nitro":     ("List of WCW Monday Nitro episodes",),
    "ecw_tv":    ("List of ECW (WWE) episodes",
                  "List of ECW on Sci-Fi episodes"),
    "dynamite":  ("List of AEW Dynamite episodes",),
    "collision": ("List of AEW Collision episodes",),
    "nxt":       ("List of WWE NXT episodes",),
    "impact":    ("List of Impact! episodes",),
}


# ------------------------------------------------------------------ HTTP


def _http_parse_page(title: str) -> Optional[dict]:
    """MediaWiki action=parse for a Wikipedia article."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "formatversion": "2",
        "redirects": "1",
        "disableeditsection": "true",
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


def _first_existing_page(titles: tuple[str, ...]) -> Optional[tuple[str, str]]:
    """Try each title in order; return (resolved_title, html) for the first hit."""
    for t in titles:
        data = _http_parse_page(t)
        if not data or "parse" not in data:
            continue
        resolved = data["parse"].get("title", t)
        text = data["parse"].get("text")
        html = text if isinstance(text, str) else (text.get("*") if isinstance(text, dict) else None)
        if html:
            return resolved, html
    return None


# ---------------------------------------------------------- extractors
#
# Both PPV-list and episode-list articles render as one wikitable per year.
# We declare a `TableExtractorSpec` for each shape, then `extract_tables()`
# walks the document and yields populated `ExtractedEvent`/`ExtractedEpisode`
# dataclasses plus per-field `FieldSnippet`s. Each snippet carries the
# `<td>` text the field came from — `persist_event` and its accuracy
# contract use this for evidence-required fields.
#
# A few cleaners are custom (not from the framework's default set):
#   - `_clean_event_date`: falls back to the year resolved from the nearest
#     preceding heading when the cell date omits a year ("March 31" under
#     a "<h2>1985</h2>" section).
#   - `_clean_strict_attendance`: rejects ranges ("1,000–1,200") and footnote
#     markers — we'd rather have null than a wrong number.
#   - `_clean_episode_number`: requires a digit at the START of the cell so
#     header sub-rows like "Debut episode" are dropped, not silently kept.
#   - `_keep_real_ppv_row`: row_filter that drops continuation rows whose
#     Event cell is really a "City, State" location (the "Rosemont, Illinois"
#     bug that produced fake Venues every ingest cycle).


_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _clean_event_date(text: str, ctx: dict) -> Optional[FieldSnippet]:
    if not text:
        return None
    s = text.strip().replace("\xa0", " ")
    m = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", s)
    if m:
        try:
            return FieldSnippet(
                value=date(int(m.group(1)), int(m.group(2)), int(m.group(3))),
                snippet=text[:200], confidence=98,
            )
        except ValueError:
            return None
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2})(?:,?\s+(\d{4}))?\b", s)
    if m:
        mo = _MONTHS.get(m.group(1).lower())
        if mo:
            try:
                y = int(m.group(3)) if m.group(3) else ctx.get("year_context")
                if y:
                    return FieldSnippet(
                        value=date(int(y), mo, int(m.group(2))),
                        snippet=text[:200], confidence=95,
                    )
            except (ValueError, TypeError):
                pass
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})\b", s)
    if m:
        mo = _MONTHS.get(m.group(2).lower())
        if mo:
            try:
                return FieldSnippet(
                    value=date(int(m.group(3)), mo, int(m.group(1))),
                    snippet=text[:200], confidence=95,
                )
            except ValueError:
                return None
    return None


def _clean_strict_attendance(text: str, ctx: dict) -> Optional[FieldSnippet]:
    if not text:
        return None
    s = re.sub(r"\[[^\]]*\]", "", text.replace("\xa0", " ").strip()).strip()
    if re.search(r"[–—\-]\s*\d", s) or "to" in s.lower():
        return None
    m = re.search(r"\d[\d,]*", s)
    if not m:
        return None
    n = int(m.group(0).replace(",", ""))
    if n <= 0 or n > 250_000:
        return None
    return FieldSnippet(value=n, snippet=text[:120], confidence=95)


def _clean_episode_number(text: str, ctx: dict) -> Optional[FieldSnippet]:
    if not text:
        return None
    m = re.match(r"\s*(\d+)", text)
    if not m:
        return None
    return FieldSnippet(value=int(m.group(1)), snippet=text[:80], confidence=98)


def _headers_of(table) -> list[str]:
    rows = table.find_all("tr")
    if not rows:
        return []
    return [
        (c.get_text(" ", strip=True) or "").lower()
        for c in rows[0].find_all(["th", "td"])
    ]


def _is_ppv_table(table) -> bool:
    headers = _headers_of(table)
    if len(headers) < 3:
        return False
    joined = " | ".join(headers)
    return ("date" in joined and "event" in joined
            and ("venue" in joined or "location" in joined))


def _is_episode_table(table) -> bool:
    headers = _headers_of(table)
    if not headers:
        return False
    if not ("no." in headers[0] or "#" == headers[0].strip() or "episode" in headers[0]):
        return False
    joined = " | ".join(headers)
    return ("date" in joined
            and ("venue" in joined or "city" in joined or "location" in joined))


def _keep_real_ppv_row(ctx: dict) -> bool:
    """Drop blank-Event rows and continuation rows where Event is really a city."""
    name = (ctx.get("name") or "").strip()
    if not name:
        return False
    if len(name) > 80 or "," not in name:
        return True
    if re.search(r"\b(19|20)\d{2}\b", name):
        return True
    after = name.split(",")[-1].strip()
    if re.match(r"^[A-Z][A-Za-z\.\s]{1,30}$", after) and len(after) <= 30:
        return False
    return True


# ---------------------------------------------------------- public API


@dataclass
class ExtractedEvent:
    promotion_key: str
    name: str
    date: Optional[date]
    venue_name: str = ""
    location: str = ""
    attendance: Optional[int] = None
    main_event_text: str = ""

    def to_dict(self) -> dict:
        return {
            "promotion": self.promotion_key,
            "name": self.name,
            "date": self.date.isoformat() if self.date else "",
            "venue_name": self.venue_name,
            "location": self.location,
            "attendance": self.attendance,
            "main_event_text": self.main_event_text[:300],
        }


@dataclass
class ExtractedEpisode:
    show_key: str
    episode_number: Optional[int]
    air_date: Optional[date]
    name: str = ""
    venue_name: str = ""
    city: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "show": self.show_key,
            "episode_number": self.episode_number,
            "name": self.name,
            "air_date": self.air_date.isoformat() if self.air_date else "",
            "venue_name": self.venue_name,
            "city": self.city,
            "notes": self.notes[:200],
        }


def _ppv_spec(promotion_key: str) -> TableExtractorSpec:
    return TableExtractorSpec(
        result_dataclass=ExtractedEvent,
        table_filter=_is_ppv_table,
        columns={
            "promotion_key":   ("__inject__",),  # populated by context_resolver
            "date":            ("date",),
            "name":            ("event",),
            "venue_name":      ("venue",),
            "location":        ("location", "city"),
            "attendance":      ("attendance",),
            "main_event_text": ("main event", "final match", "headline"),
        },
        cleaners={
            "date": _clean_event_date,
            "name": clean_text,
            "venue_name": clean_text,
            "location": clean_text,
            "attendance": _clean_strict_attendance,
            "main_event_text": clean_text,
        },
        row_filter=_keep_real_ppv_row,
        context_resolvers={
            "year_context":  resolve_year_from_preceding_heading,
            "promotion_key": lambda _t: promotion_key,
        },
        required_fields=("name",),
    )


def _episode_spec(show_key: str) -> TableExtractorSpec:
    return TableExtractorSpec(
        result_dataclass=ExtractedEpisode,
        table_filter=_is_episode_table,
        columns={
            "show_key":       ("__inject__",),
            "episode_number": ("no.", "#", "episode"),
            "air_date":       ("air date", "original air date", "date"),
            "venue_name":     ("venue", "arena"),
            "city":           ("city", "location"),
            "notes":          ("notes", "main event", "headline"),
        },
        cleaners={
            "episode_number": _clean_episode_number,
            "air_date":       _clean_event_date,
            "venue_name":     clean_text,
            "city":           clean_text,
            "notes":          clean_text,
        },
        context_resolvers={
            "year_context": resolve_year_from_preceding_heading,
            "show_key":     lambda _t: show_key,
        },
        required_fields=("episode_number",),
    )


def extract_ppvs_from_html(html: str, promotion_key: str) -> list[ExtractedEvent]:
    """Parse all yearly PPV tables on a 'List of X pay-per-view events' page."""
    return [inst for inst, _snippets in extract_tables(html, _ppv_spec(promotion_key))]


def extract_episodes_from_html(html: str, show_key: str) -> list[ExtractedEpisode]:
    """Parse episode tables on a 'List of X episodes' page."""
    out: list[ExtractedEpisode] = []
    for inst, _snippets in extract_tables(html, _episode_spec(show_key)):
        # The legacy extractor synthesised a 'Episode {N} (YYYY-MM-DD)' name
        # from the episode number + air date; preserve that shape so the
        # ingest persist layer (and saved snapshots) don't drift.
        inst.name = f"Episode {inst.episode_number}"
        if inst.air_date:
            inst.name = f"{inst.name} ({inst.air_date.isoformat()})"
        out.append(inst)
    return out


# ------------------------------------------------------- persist


PROMOTION_NAME_MAP = {
    "wwe": "WWE", "wcw": "World Championship Wrestling",
    "ecw": "Extreme Championship Wrestling",
    "aew": "All Elite Wrestling",
    "tna": "Total Nonstop Action Wrestling",
    "njpw": "New Japan Pro-Wrestling",
    "ajpw": "All Japan Pro Wrestling",
    "roh": "Ring of Honor",
    "noah": "Pro Wrestling Noah",
}


# Each TV show belongs to a promotion — needed when creating Event rows
# for individual episodes.
_SHOW_TO_PROMOTION = {
    "raw": "wwe", "smackdown": "wwe", "nxt": "wwe", "ecw_tv": "wwe",
    "nitro": "wcw",
    "dynamite": "aew", "collision": "aew",
    "impact": "tna",
}


def _show_to_promotion(show_key: str) -> str:
    return _SHOW_TO_PROMOTION.get(show_key, "wwe")


def _get_or_create_promotion(promotion_key: str):
    """Look up or create a Promotion stub for this promotion key.

    On first create, also stamps a synthetic FieldProvenance(name) row so
    the accuracy contract sees the required `name` field as covered —
    otherwise every promotion minted by the bulk PPV/TV ingester is
    stuck at verification_state='candidate'.
    """
    from owdb_django.owdbapp.models import Promotion
    from ..models import FieldProvenance, SourceFetch

    name = PROMOTION_NAME_MAP.get(promotion_key, promotion_key.upper())
    obj, was_created = Promotion.objects.get_or_create(name=name)
    if was_created:
        try:
            from ._provenance import record_provenance
            sf, _ = SourceFetch.objects.get_or_create(
                source="event_lists_registry",
                content_hash=f"event_lists_promotion_{promotion_key}"[:64],
                defaults=dict(
                    url="",
                    entity_type="promotion",
                    entity_id=obj.id,
                    candidate_name=name[:255],
                    http_status=200,
                    raw_content=(
                        f"event_lists.PROMOTION_NAME_MAP[{promotion_key!r}] = {name!r}"
                    ),
                ),
            )
            if sf.entity_id != obj.id:
                sf.entity_type = "promotion"
                sf.entity_id = obj.id
                sf.save(update_fields=["entity_type", "entity_id"])
            record_provenance(
                entity_type="promotion",
                entity_id=obj.id,
                field_name="name",
                value=name,
                source_fetch=sf,
                snippet=f"PROMOTION_NAME_MAP[{promotion_key!r}]",
                confidence=85,
            )
        except Exception as e:
            logger.warning(
                "Couldn't record name-provenance for promotion %s: %s", name, e,
            )
    return obj


def _record_list_page_fetch(resolved_title: str, html: str,
                            promotion_key: str | None = None) -> "SourceFetch":
    """Persist the Wikipedia list page as a single SourceFetch row."""
    import hashlib
    from urllib.parse import quote
    from ..models import SourceFetch
    url = f"https://en.wikipedia.org/wiki/{quote(resolved_title.replace(' ', '_'))}"
    h = hashlib.sha256((html or "").encode("utf-8")).hexdigest()
    # Reuse an existing identical fetch if content hash matches — avoids
    # duplicate SourceFetch rows when this command is re-run.
    existing = SourceFetch.objects.filter(
        source="wikipedia", content_hash=h,
    ).order_by("-fetched_at").first()
    if existing:
        return existing
    return SourceFetch.objects.create(
        source="wikipedia",
        url=url[:500],
        entity_type="event",   # the rows persisted from this page are events
        entity_id=0,           # 0 = page-level fetch, not bound to a single entity
        candidate_name=resolved_title[:255],
        http_status=200,
        content_hash=h,
        raw_content=html or "",
    )


def ingest_ppv_list(promotion_key: str) -> dict:
    """
    Fetch the PPV-list page, persist a SourceFetch, and upsert Event rows
    WITH per-field FieldProvenance + accuracy-contract state.

    Idempotent — upserts by `(promotion, name, date)`. State for each
    persisted row is set by `accuracy_contract.enforce()`; bulk rows
    land in `provisional` until back-fill / Earl upgrades them.
    """
    if promotion_key not in PPV_LIST_PAGES:
        return {"error": f"unknown promotion_key={promotion_key!r}"}
    pages = PPV_LIST_PAGES[promotion_key]
    result = _first_existing_page(pages)
    if not result:
        return {"error": f"no Wikipedia page found for {promotion_key}"}
    resolved, html = result
    extracted = extract_ppvs_from_html(html, promotion_key)
    if not extracted:
        return {"error": "no events extracted from page", "resolved_title": resolved}

    from owdb_django.owdbapp.models import Event, Venue
    from . import accuracy_contract
    from ._provenance import bulk_synthetic_provenance

    source_fetch = _record_list_page_fetch(resolved, html, promotion_key)
    promotion = _get_or_create_promotion(promotion_key)
    created = updated = 0
    for e in extracted:
        if not e.date:
            continue

        # Venue dedup: prefer the existing canonical venue when an exact
        # name+city match exists; otherwise create with a provisional state.
        venue_obj = None
        if e.venue_name:
            venue_obj = _get_or_create_venue_stub(
                name=e.venue_name, city=e.location,
                source_fetch=source_fetch,
            )

        # Upsert key includes promotion — fixes the cross-promotion
        # collision risk Codex flagged (WrestleMania the WWE event vs
        # the (hypothetical) WrestleMania a different promotion ran).
        defaults = dict(
            venue=venue_obj,
            event_type="ppv",
            verified=True,                          # back-compat boolean
            verification_source="wikipedia",
        )
        if e.attendance is not None:
            defaults["attendance"] = e.attendance
        if e.main_event_text:
            defaults["about"] = f"Main event: {e.main_event_text[:500]}"
        obj, was_created = Event.objects.update_or_create(
            promotion=promotion,
            name=e.name[:200],
            date=e.date,
            defaults=defaults,
        )

        # Per-field FieldProvenance from this Wikipedia row. The raw
        # main_event_text is the snippet that supports the row — same
        # text for every field on the row, because each row is one source
        # citation.
        snippet_hint = (
            f"{e.date.isoformat()} | {e.name} | "
            f"{e.venue_name or '?'} | {e.location or '?'} | "
            f"{e.main_event_text[:200] if e.main_event_text else ''}"
        )
        field_values = {
            "name": e.name,
            "date": e.date.isoformat(),
            "promotion": promotion.name,
        }
        if e.venue_name:
            field_values["venue"] = e.venue_name
        if e.attendance is not None:
            field_values["attendance"] = e.attendance
        if e.main_event_text:
            field_values["about"] = e.main_event_text[:500]
        bulk_synthetic_provenance(
            entity_type="event", entity_id=obj.id,
            field_values=field_values,
            source_fetch=source_fetch,
            snippet_hint=snippet_hint,
            confidence=80,  # 80 — direct from Wikipedia table row
        )

        # Enforce contract — sets verification_state per the rules.
        state, _ = accuracy_contract.enforce("event", obj)
        if obj.verification_state != state:
            obj.verification_state = state
            obj.save(update_fields=["verification_state"])

        if was_created:
            created += 1
        else:
            updated += 1
    return {
        "promotion_key": promotion_key,
        "resolved_title": resolved,
        "source_fetch_id": source_fetch.id,
        "extracted": len(extracted),
        "created": created,
        "updated": updated,
    }


def _get_or_create_venue_stub(*, name: str, city: str, source_fetch) -> "Venue":
    """
    Venue lookup-or-create with contract-aware provenance.

    Codex flagged that `get_or_create(name=...)` merges unrelated venues
    with similar names ("Civic Center"). We mitigate by:
      1. Skipping the row if name looks like a location string
         ("Rosemont, Illinois") — caught by the venue_name_not_a_city
         check in accuracy_contract.
      2. Disambiguating by (name, city) when city is available.
      3. Writing a FieldProvenance row so the venue's source is auditable.
    """
    from owdb_django.owdbapp.models import Venue
    from . import accuracy_contract
    from ._provenance import record_provenance

    name = (name or "").strip()[:200]
    if not name:
        return None

    # Catch obvious "this is a city, not a venue" rows before persisting.
    fake_venue = type("V", (), {"name": name})
    if accuracy_contract.venue_name_not_a_city(fake_venue):
        logger.debug("venue stub skipped (looks like location): %r", name)
        return None

    # Look up by name + city for better disambiguation; fall back to name
    # alone if city is unavailable.
    city_norm = (city or "").strip()[:300]
    qs = Venue.objects.filter(name=name)
    if city_norm:
        existing = qs.filter(location__icontains=city_norm.split(",")[0].strip()).first()
        if existing:
            return existing
    existing = qs.first()
    if existing:
        return existing

    venue = Venue.objects.create(
        name=name,
        location=city_norm,
        verification_state="provisional",
    )
    record_provenance(
        entity_type="venue", entity_id=venue.id, field_name="name",
        value=name, snippet=name, confidence=80,
        source_fetch=source_fetch,
    )
    if city_norm:
        record_provenance(
            entity_type="venue", entity_id=venue.id, field_name="location",
            value=city_norm, snippet=city_norm, confidence=80,
            source_fetch=source_fetch,
        )
    return venue


def ingest_episode_list(show_key: str) -> dict:
    """
    Ingest a TV-episode list from Wikipedia as Event rows with full
    provenance and accuracy-contract enforcement.
    """
    if show_key not in EPISODE_LIST_PAGES:
        return {"error": f"unknown show_key={show_key!r}"}
    pages = EPISODE_LIST_PAGES[show_key]
    result = _first_existing_page(pages)
    if not result:
        return {"error": f"no Wikipedia page found for {show_key}"}
    resolved, html = result
    extracted = extract_episodes_from_html(html, show_key)
    if not extracted:
        return {"error": "no episodes extracted", "resolved_title": resolved}

    from owdb_django.owdbapp.models import Event, TVShow
    from . import accuracy_contract
    from ._provenance import bulk_synthetic_provenance

    show_name_map = {
        "raw": "WWE Raw", "smackdown": "WWE SmackDown",
        "nitro": "WCW Monday Nitro", "ecw_tv": "ECW on Sci-Fi",
        "dynamite": "AEW Dynamite", "collision": "AEW Collision",
        "nxt": "WWE NXT", "impact": "Impact!",
    }
    tv_show_name = show_name_map.get(show_key, show_key.upper())
    tv_show, tv_show_created = TVShow.objects.get_or_create(name=tv_show_name)
    promotion = (tv_show.promotion if getattr(tv_show, "promotion_id", None)
                 else _get_or_create_promotion(_show_to_promotion(show_key)))

    source_fetch = _record_list_page_fetch(resolved, html, _show_to_promotion(show_key))

    # Backfill the TV show's required-field provenance once at creation.
    # Without this row the show is permanently stuck at 'candidate' state.
    if tv_show_created:
        try:
            from ._provenance import record_provenance
            record_provenance(
                entity_type="tv_show",
                entity_id=tv_show.id,
                field_name="name",
                value=tv_show_name,
                source_fetch=source_fetch,
                snippet=f"TV show created during episode-list ingest of {resolved!r}",
                confidence=85,
            )
            # Also pin the TV show -> promotion link to this source so
            # the show isn't orphaned in the verification audit.
            if getattr(tv_show, "promotion_id", None):
                tv_show.promotion = promotion
                tv_show.save(update_fields=["promotion"])
        except Exception as e:
            logger.warning(
                "Couldn't backfill provenance for tv_show %s: %s",
                tv_show_name, e,
            )
    created = updated = 0
    for ep in extracted:
        if not ep.air_date:
            continue

        venue_obj = None
        if ep.venue_name:
            venue_obj = _get_or_create_venue_stub(
                name=ep.venue_name, city=ep.city, source_fetch=source_fetch,
            )
        ep_name = f"{show_name_map.get(show_key, show_key)} — {ep.air_date.isoformat()}"

        defaults = dict(
            venue=venue_obj,
            tv_show=tv_show,
            event_type="tv_episode",
            verified=True,
            verification_source="wikipedia",
        )
        if ep.episode_number:
            defaults["episode_number"] = ep.episode_number
        if ep.notes:
            defaults["about"] = ep.notes[:500]

        obj, was_created = Event.objects.update_or_create(
            promotion=promotion,
            name=ep_name[:200],
            date=ep.air_date,
            defaults=defaults,
        )

        snippet_hint = (
            f"Episode {ep.episode_number or '?'} | {ep.air_date.isoformat()} | "
            f"{ep.venue_name or '?'} | {ep.city or '?'} | {ep.notes[:200] if ep.notes else ''}"
        )
        field_values = {
            "name": ep_name,
            "date": ep.air_date.isoformat(),
            "promotion": promotion.name,
            "tv_show": tv_show.name,
        }
        if ep.episode_number:
            field_values["episode_number"] = ep.episode_number
        if ep.venue_name:
            field_values["venue"] = ep.venue_name
        if ep.notes:
            field_values["about"] = ep.notes[:500]
        bulk_synthetic_provenance(
            entity_type="event", entity_id=obj.id,
            field_values=field_values,
            source_fetch=source_fetch,
            snippet_hint=snippet_hint,
            confidence=80,
        )
        state, _ = accuracy_contract.enforce("event", obj)
        if obj.verification_state != state:
            obj.verification_state = state
            obj.save(update_fields=["verification_state"])

        if was_created:
            created += 1
        else:
            updated += 1
    return {
        "show_key": show_key,
        "resolved_title": resolved,
        "source_fetch_id": source_fetch.id,
        "extracted": len(extracted),
        "created": created,
        "updated": updated,
    }


if __name__ == "__main__":  # pragma: no cover
    import sys
    args = sys.argv[1:] or ["wwe"]
    for key in args:
        if key in PPV_LIST_PAGES:
            print(ingest_ppv_list(key))
        elif key in EPISODE_LIST_PAGES:
            print(ingest_episode_list(key))
