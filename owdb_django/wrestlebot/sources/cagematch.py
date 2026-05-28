"""
Cagematch source adapter.

Wraps the existing CagematchScraper (which already handles the site's
527-second robots.txt crawl-delay) and exposes typed extraction over the
same SourceAdapter contract used by the Wikipedia adapter.

Cagematch is rate-limited very heavily by design — we plan ≤1 wrestler
fetch per cycle in autonomous operation. Used purely for cross-validation
against Wikipedia, not as a primary source.

Important: the README and the verification stamp on the public site must
NOT use Cagematch's trademark name or logo (per user instruction). Internally
we use the source slug 'cagematch' for tracking; the public-facing UI
refers to it generically as "external wrestling database".
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from ...owdbapp.scrapers.cagematch import CagematchScraper
from ...owdbapp.scrapers.utils import clean_text
from .base import (
    FetchResult,
    FieldSnippet,
    SourceAdapter,
    WrestlerFields,
)

logger = logging.getLogger(__name__)


def parse_cagematch_id_from_url(url: str) -> Optional[int]:
    """
    Extract the numeric `nr=` parameter from a Cagematch URL.

    Examples:
      http://www.cagematch.net/?id=2&nr=565        -> 565
      https://www.cagematch.net/?id=2&nr=926&s=1   -> 926
    Returns None if the URL doesn't have a wrestler-shaped nr param.
    """
    if not url:
        return None
    try:
        qs = parse_qs(urlparse(url).query)
    except Exception:
        return None
    nr_values = qs.get("nr") or []
    if not nr_values:
        return None
    try:
        return int(nr_values[0])
    except ValueError:
        return None


class CagematchAdapter(SourceAdapter):
    source_name = "cagematch"

    def __init__(self):
        self._scraper = CagematchScraper()

    # ------------------------------------------------------------------ fetch

    def fetch_wrestler_by_name(self, name: str) -> Optional[FetchResult]:
        """
        Cagematch doesn't have a fast name-search API like Wikipedia; the
        v3.0 path is to fetch by cagematch_url instead. This stub is kept
        only for SourceAdapter interface conformance — it returns None.
        """
        return None

    def fetch_wrestler_by_url(self, cagematch_url: str) -> Optional[FetchResult]:
        """
        Fetch a wrestler's Cagematch profile page given the canonical URL.

        Respects the scraper's 527s crawl-delay; expect 1 call per 9 minutes
        in production.
        """
        wrestler_id = parse_cagematch_id_from_url(cagematch_url)
        if wrestler_id is None:
            logger.warning("Not a Cagematch wrestler URL: %s", cagematch_url)
            return None

        url = f"{self._scraper.BASE_URL}/?id=2&nr={wrestler_id}"
        html = self._scraper.get_cached_or_fetch(url, cache_ttl=86400)
        if not html:
            return None

        return FetchResult(
            url=url,
            http_status=200,
            raw_content=html,
            source_id=str(wrestler_id),
        )

    # ---------------------------------------------------------------- extract

    def extract_wrestler(self, raw_content: str) -> Optional[WrestlerFields]:
        """Parse a Cagematch wrestler profile page into typed WrestlerFields."""
        if not raw_content:
            return None

        soup = BeautifulSoup(raw_content, "lxml")
        # The information section is wrapped as <div class="InformationBoxContents">,
        # but rows live inside <div class="InformationBoxRow">. The "real_name"
        # row often is in a separate top-level InformationBoxContents block;
        # we scan all matching blocks below.
        info_blocks = soup.find_all("div", class_="InformationBoxContents")
        if not info_blocks:
            return None

        fields = WrestlerFields()

        # Page heading is the canonical wrestler name on Cagematch.
        heading = soup.find("h1")
        if heading:
            heading_text = clean_text(heading.get_text())
            if heading_text:
                fields.name = FieldSnippet(value=heading_text, snippet=heading_text)

        # Walk every InformationBoxRow on the page.
        for row in soup.find_all("div", class_="InformationBoxRow"):
            title_el = row.find("div", class_="InformationBoxTitle")
            content_el = row.find("div", class_="InformationBoxContents")
            if not title_el or not content_el:
                continue

            label = clean_text(title_el.get_text()).lower().rstrip(":")
            value = clean_text(content_el.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"
            self._dispatch_field(fields, label, value, snippet)

        # If we extracted nothing useful, treat as a parse failure.
        if not fields.populated_fields():
            return None
        return fields

    # ----------------------------------------------------- field-level dispatch

    _CAGEMATCH_DATE_RE = re.compile(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4})"  # DD.MM.YYYY (German format)
    )

    def _dispatch_field(
        self,
        fields: WrestlerFields,
        label: str,
        value: str,
        snippet: str,
    ) -> None:
        # Real name (Cagematch label: "Real name")
        if "real name" in label and fields.real_name is None:
            fields.real_name = FieldSnippet(value=value, snippet=snippet)
            return

        # Aliases ("Alter Egos" or "Ring names")
        if "alter ego" in label or "ring name" in label or "ring names" in label:
            if fields.aliases is None:
                fields.aliases = FieldSnippet(value=value, snippet=snippet)
            return

        # Birth date / birthday
        if "birth" in label and "place" not in label:
            d = self._parse_date(value)
            if d is not None and fields.birth_date is None:
                fields.birth_date = FieldSnippet(value=d, snippet=snippet)
            return

        # Death date
        if "death" in label or "died" in label:
            d = self._parse_date(value)
            if d is not None and fields.death_date is None:
                fields.death_date = FieldSnippet(value=d, snippet=snippet)
            return

        # Birthplace / hometown
        if "birthplace" in label or "hometown" in label:
            if fields.hometown is None:
                fields.hometown = FieldSnippet(value=value, snippet=snippet)
            return

        # Nationality
        if "nationality" in label and fields.nationality is None:
            fields.nationality = FieldSnippet(value=value, snippet=snippet)
            return

        # Height
        if label.startswith("height") and fields.height is None:
            fields.height = FieldSnippet(value=value, snippet=snippet)
            return

        # Weight
        if label.startswith("weight") and fields.weight is None:
            fields.weight = FieldSnippet(value=value, snippet=snippet)
            return

        # Career years (Cagematch: "Active years" or "Wrestling career")
        if "active" in label or "wrestling career" in label or "career" in label:
            years = re.findall(r"\b(19|20)\d{2}\b", value)
            # The regex above captures the first two digits as a group, but the
            # full match is what we want — fall back to a fuller scan.
            years_full = re.findall(r"\b(?:19|20)\d{2}\b", value)
            if years_full:
                try:
                    debut = int(years_full[0])
                    if fields.debut_year is None:
                        fields.debut_year = FieldSnippet(value=debut, snippet=snippet)
                    if len(years_full) > 1:
                        retired = int(years_full[-1])
                        if retired > debut and fields.retirement_year is None:
                            fields.retirement_year = FieldSnippet(value=retired, snippet=snippet)
                except ValueError:
                    pass
            return

    def _parse_date(self, text: str) -> Optional[date]:
        """
        Parse Cagematch's date display. Common formats:
          DD.MM.YYYY  (e.g., "02.07.1957")
          YYYY-MM-DD  (less common but appears)
        """
        if not text:
            return None
        m = self._CAGEMATCH_DATE_RE.search(text)
        if m:
            try:
                day, month, year = (int(g) for g in m.groups())
                if 1850 <= year <= datetime.now().year and 1 <= month <= 12 and 1 <= day <= 31:
                    return date(year, month, day)
            except ValueError:
                pass
        # Fall-through to ISO format
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                pass
        return None
