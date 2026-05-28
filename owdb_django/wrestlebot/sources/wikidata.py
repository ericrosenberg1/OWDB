"""
Wikidata source adapter — used purely for cross-validation against Wikipedia.

Wikidata is the structured-data sister project of Wikipedia. It's edited by a
separate community on a different cadence and exposes its data as a stable
JSON API, so it makes a credible second source for accuracy checking.

The adapter resolves a wrestler's QID via the Wikipedia API (one call), then
fetches the entity JSON (second call) and extracts a few high-confidence
typed fields. Q-reference values (place of birth -> Q36312 "Calgary") are
not resolved in v3.0 — only direct-value claims are extracted.

CC0 licensed; safe to cite by name in the verification stamp.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from typing import Optional
from urllib.request import Request, urlopen

from .base import (
    FetchResult,
    FieldSnippet,
    SourceAdapter,
    WrestlerFields,
)

logger = logging.getLogger(__name__)


WIKIDATA_ENTITY_URL = "https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
WIKIPEDIA_QID_LOOKUP = (
    "https://en.wikipedia.org/w/api.php"
    "?action=query&prop=pageprops&ppprop=wikibase_item"
    "&titles={title}&format=json"
)
USER_AGENT = "wrestlingdb-wrestlebot/1.0 (+https://wrestlingdb.org; admin@wrestlingdb.org)"


# Property IDs we look up from Wikidata claims.
P_INSTANCE_OF = "P31"
P_DATE_OF_BIRTH = "P569"
P_DATE_OF_DEATH = "P570"
P_GENDER = "P21"
P_CITIZENSHIP = "P27"
P_OCCUPATION = "P106"
P_SPORT = "P641"


def _http_get_json(url: str, timeout: float = 10.0) -> Optional[dict]:
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.debug("Wikidata HTTP failure for %s: %s", url, e)
        return None


def resolve_qid_for_wikipedia_title(title: str) -> Optional[str]:
    """Resolve a Wikipedia page title to its Wikidata Q-ID (e.g. 'Q81324')."""
    if not title:
        return None
    from urllib.parse import quote

    url = WIKIPEDIA_QID_LOOKUP.format(title=quote(title))
    data = _http_get_json(url)
    if not data:
        return None
    pages = data.get("query", {}).get("pages", {}) or {}
    for _, page in pages.items():
        qid = page.get("pageprops", {}).get("wikibase_item")
        if qid:
            return qid
    return None


def _parse_wikidata_time(claim_value: dict) -> Optional[date]:
    """
    Parse a Wikidata 'time' datavalue into a Python date.

    Wikidata times look like {'time': '+1957-07-02T00:00:00Z', 'precision': 11, ...}.
    Precision 11 = day, 10 = month, 9 = year, 8 = decade. We only return a
    `date` for precision >= 11 (full day). Less precise values are returned
    as None to avoid false-precision cross-validation hits.
    """
    if not isinstance(claim_value, dict):
        return None
    time_str = claim_value.get("time", "")
    precision = int(claim_value.get("precision", 0) or 0)
    if precision < 11:
        return None
    # Format: '+YYYY-MM-DDT00:00:00Z' or '-YYYY-MM-DDT...' for BC dates.
    m = re.match(r"^([+-])(\d{4,})-(\d{2})-(\d{2})T", time_str)
    if not m:
        return None
    sign, y, mo, d = m.groups()
    if sign == "-":
        return None  # BC dates we don't care about for wrestlers
    try:
        return date(int(y), int(mo), int(d))
    except ValueError:
        return None


class WikidataAdapter(SourceAdapter):
    source_name = "wikidata"

    def fetch_wrestler_by_qid(self, qid: str) -> Optional[FetchResult]:
        """Fetch a Wikidata entity JSON by Q-ID."""
        if not qid or not re.match(r"^Q\d+$", qid):
            return None
        url = WIKIDATA_ENTITY_URL.format(qid=qid)
        data = _http_get_json(url)
        if not data or "entities" not in data:
            return None
        if qid not in data["entities"]:
            return None
        # Store the entity-only slice as raw content (not the whole envelope).
        raw_text = json.dumps(data["entities"][qid])
        return FetchResult(
            url=url,
            http_status=200,
            raw_content=raw_text,
            source_id=qid,
        )

    def fetch_wrestler_by_name(self, name: str) -> Optional[FetchResult]:
        qid = resolve_qid_for_wikipedia_title(name)
        if not qid:
            return None
        return self.fetch_wrestler_by_qid(qid)

    def extract_wrestler(self, raw_content: str) -> Optional[WrestlerFields]:
        """Parse stored Wikidata entity JSON into typed WrestlerFields."""
        if not raw_content:
            return None
        try:
            entity = json.loads(raw_content)
        except json.JSONDecodeError:
            return None
        if not isinstance(entity, dict) or "claims" not in entity:
            return None

        claims = entity["claims"]
        fields = WrestlerFields()

        # We deliberately do NOT extract `name` here. The English label on
        # Wikidata is sometimes a disambig variant ("Pat Patterson (wrestler)")
        # or even an entirely different rendering ("Angela Quentina Arnold" vs
        # "A. Q. A."). Wikidata is a *cross-check*, not the source of truth for
        # the wrestler's display name; renaming from here creates duplicates.
        # The persist layer falls back to candidate_name (the existing
        # wrestler's name) when fields.name is None.

        # date of birth (P569)
        for c in claims.get(P_DATE_OF_BIRTH, []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            d = _parse_wikidata_time(v)
            if d is not None:
                fields.birth_date = FieldSnippet(
                    value=d,
                    snippet=f"Wikidata P569: {d.isoformat()}",
                )
                break

        # date of death (P570)
        for c in claims.get(P_DATE_OF_DEATH, []):
            v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
            d = _parse_wikidata_time(v)
            if d is not None:
                fields.death_date = FieldSnippet(
                    value=d,
                    snippet=f"Wikidata P570: {d.isoformat()}",
                )
                break

        # If we extracted nothing useful, treat as a parse failure.
        if not fields.populated_fields():
            return None
        return fields
