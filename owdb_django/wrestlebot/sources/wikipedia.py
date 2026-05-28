"""
Wikipedia source adapter.

Wraps the existing WikipediaScraper (which handles rate-limiting, robots.txt,
and the MediaWiki API surface) and adds typed extraction with per-field
snippet capture.

Extraction is intentionally conservative:
- Only fields with strong infobox structure get extracted.
- "Born" is parsed for both birth date and birth name, falling back to None
  on ambiguous formatting rather than guessing.
- Multi-valued fields (ring names, finishers) are captured as the raw delimiter-
  separated string we'll later split downstream.

If a field can't be confidently parsed, it's omitted. Better empty than wrong.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from ...owdbapp.scrapers.wikipedia import WikipediaScraper
from ...owdbapp.scrapers.utils import clean_text
from .base import (
    ActionFigureFields,
    BookFields,
    EventFields,
    FetchResult,
    FieldSnippet,
    PodcastFields,
    PromotionFields,
    SourceAdapter,
    SpecialFields,
    StableFields,
    ThemeSongFields,
    TitleFields,
    TrainingSchoolFields,
    TVShowFields,
    VenueFields,
    VideoGameFields,
    WrestlerFields,
)

logger = logging.getLogger(__name__)


class WikipediaAdapter(SourceAdapter):
    source_name = "wikipedia"

    def __init__(self):
        self._scraper = WikipediaScraper()

    # ------------------------------------------------------------------ fetch

    def fetch_wrestler_by_name(self, name: str) -> Optional[FetchResult]:
        """
        Fetch the parsed HTML of a Wikipedia page by title.

        Uses the MediaWiki action=parse API with redirects=1 so that
        title aliases (e.g., "Andre the Giant" -> "André the Giant") are
        followed server-side. Returns None if the page does not exist or
        is a disambiguation.
        """
        title = name.strip()
        if not title:
            return None

        data = self._scraper._api_request({
            "action": "parse",
            "page": title,
            "prop": "text",
            "redirects": 1,
            "disableeditsection": "true",
        })
        if not data or "parse" not in data:
            return None

        # The resolved title (after redirects) is in data["parse"]["title"].
        resolved_title = data["parse"].get("title") or title
        text = data["parse"].get("text")
        html: Optional[str] = text if isinstance(text, str) else (text.get("*") if isinstance(text, dict) else None)
        if not html:
            return None

        # Skip disambiguation pages. They have a clear marker.
        if 'disambiguation' in html[:5000].lower() and 'class="disambig"' in html:
            logger.debug("Skipping disambiguation page: %s", title)
            return None

        url = f"https://en.wikipedia.org/wiki/{quote(resolved_title.replace(' ', '_'))}"
        return FetchResult(
            url=url,
            http_status=200,
            raw_content=html,
            source_id=resolved_title,
        )

    # ---------------------------------------------------------------- extract

    def extract_wrestler(
        self,
        raw_content: str,
        article_title: Optional[str] = None,
    ) -> Optional[WrestlerFields]:
        """
        Parse a Wikipedia HTML page into typed WrestlerFields.

        Returns None if no infobox is present (not a structured wrestler page).

        When `article_title` is provided, also computes `best_known_as` from
        the article's lede ("better known by his ring name X") or by stripping
        a Wikipedia disambig suffix ("Rikishi (wrestler)" → "Rikishi"). The
        persist layer prefers this over the article title for display.
        """
        if not raw_content:
            return None

        soup = BeautifulSoup(raw_content, "lxml")

        # Pull best_known_as BEFORE we destructively strip noise from the
        # infobox — the lede paragraph lives in the article body and is
        # untouched by infobox cleanup, but we keep the order anyway.
        best_known = None
        if article_title:
            best_known = _best_known_as_from_article(soup, article_title)

        # Wrestler pages typically use Template:Infobox professional wrestler,
        # which renders as table.infobox.vcard. Some use plain table.infobox.
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None

        # Strip noise that would otherwise pollute multi-line extraction:
        #   <sup class="reference"> — footnote markers like [1], [a]
        #   <style>, <script>       — embedded metadata
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = WrestlerFields()

        # Walk infobox rows. Each row has a <th> label and <td> value.
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue

            label_text = clean_text(th.get_text()).lower()
            # For multi-value cells (aliases, trained_by, finishers, etc.) Wikipedia
            # uses <br> and <li> as item separators. We extract two views:
            #   value_text     — single-line summary (for parsing dates, years)
            #   value_items    — list of values broken on <br>/<li>
            value_text = clean_text(td.get_text())
            value_items = self._extract_multiline(td)
            if not label_text or not value_text:
                continue

            snippet_text = f"{label_text}: {value_text}"
            self._dispatch_field(fields, label_text, value_text, value_items, snippet_text, td)

        # If we didn't capture even a name, treat the page as a non-wrestler.
        if fields.name is None and not fields.populated_fields():
            return None

        if best_known:
            fields.best_known_as = best_known

        return fields

    # ----------------------------------------------------- field-level parsers

    def _dispatch_field(
        self,
        fields: WrestlerFields,
        label: str,
        value: str,
        value_items: list[str],
        snippet: str,
        td,
    ) -> None:
        """Route an infobox row to the right field parser."""
        # Birth name + birth date + nationality may all be embedded in "Born".
        if label in ("born",):
            self._parse_born(fields, value, snippet)
            return

        if label in ("died",):
            self._parse_died(fields, value, snippet)
            return

        if label in ("birth name",) and fields.real_name is None:
            fields.real_name = FieldSnippet(value=value, snippet=snippet)
            return

        if label in ("ring name", "ring names", "ring name(s)"):
            # Multi-value cell: join cleanly with commas.
            joined = self._join_items(value_items, value)
            fields.aliases = FieldSnippet(value=joined, snippet=snippet)
            return

        if label in ("billed from", "residence", "hometown"):
            # "Billed from" is the in-character home; "Residence" is real-world.
            # Prefer "Billed from" since that's what fans recognize. For multi-
            # value cells, take only the first non-parenthetical entry.
            primary = self._first_non_parenthetical(value_items, value)
            if label == "billed from" or fields.hometown is None:
                fields.hometown = FieldSnippet(value=primary, snippet=snippet)
                return

        if label == "nationality":
            fields.nationality = FieldSnippet(value=value, snippet=snippet)
            return

        if label in ("debut",):
            year = self._parse_year(value)
            if year is not None:
                fields.debut_year = FieldSnippet(value=year, snippet=snippet)
            return

        if label in ("retired",):
            year = self._parse_year(value)
            if year is not None:
                fields.retirement_year = FieldSnippet(value=year, snippet=snippet)
            return

        if label in ("height",):
            fields.height = FieldSnippet(value=value, snippet=snippet)
            return

        if label in ("weight",):
            fields.weight = FieldSnippet(value=value, snippet=snippet)
            return

        if label in ("trained by", "trainer", "trainers"):
            joined = self._join_items(value_items, value)
            fields.trained_by = FieldSnippet(value=joined, snippet=snippet)
            return

        if label in ("occupation", "occupations", "other occupation",
                     "other occupations", "profession", "professions"):
            # Wikipedia's "Occupation(s)" cell on wrestler pages often
            # includes secondary careers: "Wrestler, Commentator, Actor".
            # We detect commentator/announcer/referee/manager/trainer here
            # and tag the wrestler with a multi-role string.
            joined = self._join_items(value_items, value).lower()
            roles_found = ["wrestler"]
            role_patterns = (
                ("color commentator", "color_commentator"),
                ("commentator", "commentator"),
                ("announcer", "announcer"),
                ("ring announcer", "ring_announcer"),
                ("referee", "referee"),
                ("manager", "manager"),
                ("promoter", "promoter"),
                ("booker", "booker"),
                ("trainer", "trainer"),
                ("road agent", "road_agent"),
            )
            for needle, tag in role_patterns:
                if needle in joined and tag not in roles_found:
                    roles_found.append(tag)
            if len(roles_found) > 1:  # only set if we found something beyond "wrestler"
                fields.roles = FieldSnippet(
                    value=", ".join(roles_found), snippet=snippet,
                )
            return

        if label in ("name",) and fields.name is None:
            # Page-name fallback. Usually the infobox heading.
            fields.name = FieldSnippet(value=value, snippet=snippet)
            return

    # ------------------------------------------- multi-value cell extraction

    @staticmethod
    def _extract_address_text(td) -> str:
        """
        Pull text from an address-style cell with ', ' separators between
        line-broken segments. Wikipedia uses <br>, <span>, and <a> to break
        addresses; without a separator they concatenate ("WilliamsStreetAtlanta").
        """
        # Strip footnote markers first.
        for noisy in td.find_all(["sup", "style", "script"]):
            noisy.decompose()
        text = td.get_text(separator=", ", strip=True)
        # Coalesce ", , " sequences, collapse whitespace.
        text = re.sub(r"(,\s*){2,}", ", ", text)
        text = re.sub(r"\s{2,}", " ", text)
        # Strip stray comma at edges.
        text = text.strip(", \t\n")
        return text

    @staticmethod
    def _extract_multiline(td) -> list[str]:
        """
        Pull a Wikipedia infobox cell into a list of individual items,
        respecting <br> and <li> boundaries.

        Examples:
            <td>Hollywood Hogan<br>Hulk Boulder</td>  -> ["Hollywood Hogan", "Hulk Boulder"]
            <td><ul><li>A</li><li>B</li></ul></td>    -> ["A", "B"]
            <td>Single value</td>                     -> ["Single value"]
            <td><a>Dublin</a>, <a>Ireland</a></td>    -> ["Dublin, Ireland"]
        """
        text = td.get_text(separator="\n", strip=True)
        raw_items: list[str] = []
        for raw in text.split("\n"):
            cleaned = clean_text(raw)
            if cleaned:
                raw_items.append(cleaned)

        # Coalesce items that look like continuation punctuation onto the
        # prior item. This handles Wikipedia's habit of structuring locations
        # as <a>Dublin</a>, <a>Ireland</a> which extracts as ["Dublin", ", Ireland"].
        merged: list[str] = []
        for item in raw_items:
            if merged and item.startswith((",", ";", ")")):
                merged[-1] = merged[-1] + item if item.startswith(")") else merged[-1] + " " + item
                # Collapse double spaces and " ," patterns.
                merged[-1] = re.sub(r"\s+,", ",", merged[-1])
                merged[-1] = re.sub(r"\s{2,}", " ", merged[-1]).strip()
                continue
            merged.append(item)
        return merged

    @staticmethod
    def _join_items(items: list[str], fallback: str) -> str:
        """Join multi-value items with ', '. Falls back to single-line value if empty."""
        deduped: list[str] = []
        seen: set[str] = set()
        for it in items:
            if it not in seen:
                deduped.append(it)
                seen.add(it)
        if not deduped:
            return fallback
        # Drop entries that look like context annotations (e.g., "(as Hulk Hogan)").
        meaningful = [it for it in deduped if not (it.startswith("(") and it.endswith(")"))]
        return ", ".join(meaningful) if meaningful else ", ".join(deduped)

    @staticmethod
    def _first_non_parenthetical(items: list[str], fallback: str) -> str:
        """Return the first item that isn't a parenthetical annotation."""
        for it in items:
            if not (it.startswith("(") and it.endswith(")")):
                return it
        return fallback

    # ------------------------------------------------- "Born" / "Died" parsing

    _DATE_PATTERNS: tuple[str, ...] = (
        "%B %d, %Y",        # August 11, 1953
        "%d %B %Y",         # 11 August 1953
        "%Y-%m-%d",         # 1953-08-11
        "%b %d, %Y",        # Aug 11, 1953
    )

    def _parse_born(self, fields: WrestlerFields, value: str, snippet: str) -> None:
        """
        Parse Wikipedia's "Born" infobox cell.

        Common shape:
          "Terrence Eugene Bollea (1953-08-11) August 11, 1953 (age 71) Augusta, Georgia, U.S."

        We extract:
          - birth date  (the (YYYY-MM-DD) hidden marker, or a clean date string)
          - real_name   (the leading proper-noun phrase if it looks like a name)
          - hometown    (a trailing "City, State[, Country]" if no Billed-from)
        """
        # 1) Birth date — prefer the (YYYY-MM-DD) marker since it's unambiguous.
        m = re.search(r"\((\d{4})-(\d{2})-(\d{2})\)", value)
        if m:
            try:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                fields.birth_date = FieldSnippet(value=d, snippet=snippet)
            except ValueError:
                pass

        # 2) If no ISO marker, fall back to fuzzy parsing of common formats.
        if fields.birth_date is None:
            cleaned = re.sub(r"\([^)]*\)", " ", value)  # strip parentheticals
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            for pattern in self._DATE_PATTERNS:
                # Try to find a date substring matching this pattern.
                d = self._try_parse_date(cleaned, pattern)
                if d is not None:
                    fields.birth_date = FieldSnippet(value=d, snippet=snippet)
                    break

        # 3) Real name — usually the part before the first "(YYYY-MM-DD)" marker
        # or before the first parenthetical date.
        if fields.real_name is None:
            # Cut at the first "(" since that's where the date parens start.
            head = value.split("(", 1)[0].strip().rstrip(",")
            if head and self._looks_like_proper_name(head):
                fields.real_name = FieldSnippet(value=head, snippet=snippet)

    def _parse_died(self, fields: WrestlerFields, value: str, snippet: str) -> None:
        """Parse the "Died" infobox cell for a death date."""
        m = re.search(r"\((\d{4})-(\d{2})-(\d{2})\)", value)
        if m:
            try:
                d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                fields.death_date = FieldSnippet(value=d, snippet=snippet)
                return
            except ValueError:
                pass

        cleaned = re.sub(r"\([^)]*\)", " ", value)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for pattern in self._DATE_PATTERNS:
            d = self._try_parse_date(cleaned, pattern)
            if d is not None:
                fields.death_date = FieldSnippet(value=d, snippet=snippet)
                return

    @staticmethod
    def _try_parse_date(text: str, pattern: str) -> Optional[date]:
        """Slide `pattern` over `text` looking for a parseable match."""
        # Crude but effective: try the whole string, then progressively shorter prefixes.
        # For real corpus we'd want a proper date-extraction lib, but stdlib is fine.
        for length in range(len(text), 5, -1):
            substr = text[:length]
            try:
                dt = datetime.strptime(substr, pattern)
                if 1850 <= dt.year <= datetime.now().year:
                    return dt.date()
            except ValueError:
                continue
        return None

    @staticmethod
    def _looks_like_proper_name(text: str) -> bool:
        """Heuristic: a real-name candidate should be 1-5 capitalized tokens."""
        tokens = text.split()
        if not (1 <= len(tokens) <= 6):
            return False
        # At least 2 tokens should look like proper-cased words.
        capped = sum(1 for t in tokens if t[:1].isupper() and not t.isupper())
        return capped >= max(1, len(tokens) - 1)

    # ----------------------------------------------------------- year parsing

    @staticmethod
    def _parse_year(text: str) -> Optional[int]:
        """
        Extract the FIRST 4-digit year (1900-current+1) from arbitrary text.

        Uses non-digit boundaries instead of \\b so we match years even when
        they're concatenated to letters (Wikipedia sometimes joins text nodes
        without separators: "August 23, 1975April 17, 2010").
        """
        m = re.search(r"(?<!\d)((?:19|20)\d{2})(?!\d)", text)
        if not m:
            return None
        year = int(m.group(1))
        if 1900 <= year <= datetime.now().year + 1:
            return year
        return None

    # ---------------------------------------------------- discovery (helpers)

    def list_category_members(self, category: str, limit: int = 100) -> list[str]:
        """
        Enumerate Wikipedia page titles in a category. Used by the discovery
        pipeline to find candidate wrestler names.
        """
        return self._scraper.get_category_members(category, limit=limit)

    # ================================================================ EVENTS

    def fetch_event_by_name(self, name: str) -> Optional[FetchResult]:
        """Same shape as fetch_wrestler_by_name — distinct so caller intent is clear."""
        return self.fetch_wrestler_by_name(name)

    def extract_event(self, raw_content: str) -> Optional[EventFields]:
        """
        Parse a Wikipedia HTML event page (PPV, TV special, etc.) into
        EventFields. Common infobox labels we handle:
            "Date", "Venue", "City", "Promotion", "Attendance",
            "Tagline" (skipped), "PPV chronology" (skipped).
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = EventFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower()
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("date", "dates"):
                d = self._parse_event_date(value)
                if d is not None:
                    fields.date = FieldSnippet(value=d, snippet=snippet)
                continue

            if label in ("venue", "arena"):
                fields.venue_name = FieldSnippet(value=value, snippet=snippet)
                # Pull the wiki-link target for the venue if present, so persist
                # can create a stub Venue with a wikipedia_url.
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    target = link["href"][len("/wiki/"):].split("#", 1)[0]
                    from urllib.parse import unquote as _unquote
                    target = _unquote(target).replace("_", " ")
                    fields.venue_wiki_link = FieldSnippet(value=target, snippet=snippet)
                continue

            if label in ("city", "cities", "location"):
                if fields.venue_location is None:
                    fields.venue_location = FieldSnippet(value=value, snippet=snippet)
                continue

            if label in ("promotion", "promotions", "promoter"):
                fields.promotion_name = FieldSnippet(value=value, snippet=snippet)
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    target = link["href"][len("/wiki/"):].split("#", 1)[0]
                    from urllib.parse import unquote as _unquote
                    target = _unquote(target).replace("_", " ")
                    fields.promotion_wiki_link = FieldSnippet(value=target, snippet=snippet)
                continue

            if label in ("attendance",):
                # Attendance cells often contain ranges ("68,000–70,000"),
                # parenthetical notes ("75,167 (announced)"), and multiple
                # comma-grouped numbers. We strip parens first, then split on
                # range separators (en-dash, em-dash, hyphen-between-digits,
                # "to"), and take only the first number — that's the typical
                # "announced" / lower-bound figure. Bare digit-stripping (the
                # old behaviour) concatenated ranges into nonsense.
                cell = value.split("(")[0]
                # Split on any range marker or " to "
                parts = re.split(r"[–—-]|\bto\b", cell)
                first = parts[0] if parts else cell
                num = re.sub(r"[^\d]", "", first)
                if num:
                    try:
                        n = int(num)
                        # Sanity-cap: real wrestling events cap around 200K.
                        if 100 <= n <= 200_000:
                            fields.attendance = FieldSnippet(value=n, snippet=snippet)
                    except ValueError:
                        pass
                continue

        if not fields.populated_fields():
            return None
        return fields

    @staticmethod
    def _parse_event_date(value: str) -> Optional[date]:
        """Parse an event date cell. Wikipedia shows ISO and prose forms."""
        m = re.search(r"\((\d{4})-(\d{2})-(\d{2})\)", value)
        if m:
            try:
                return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                return None
        cleaned = re.sub(r"\([^)]*\)", " ", value)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        for pattern in WikipediaAdapter._DATE_PATTERNS:
            d = WikipediaAdapter._try_parse_date(cleaned, pattern)
            if d is not None:
                return d
        return None

    # ================================================================ VENUES

    def fetch_venue_by_name(self, name: str) -> Optional[FetchResult]:
        """Same Wikipedia fetch pathway as wrestlers; routes through redirects."""
        return self.fetch_wrestler_by_name(name)

    def extract_venue(self, raw_content: str) -> Optional[VenueFields]:
        """
        Parse a Wikipedia venue/arena page. Common infobox labels:
            "Location", "Address", "Coordinates" (skipped), "Capacity",
            "Opened", "Renovated", "Owner", "Operator", "Architect"...
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = VenueFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower()
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("location", "address", "full address"):
                if fields.location is None:
                    # Address cells are multi-segment; use the comma-separator
                    # extractor instead of the default concatenated text.
                    address_value = WikipediaAdapter._extract_address_text(td)
                    fields.location = FieldSnippet(value=address_value, snippet=snippet)
                continue

            if label in ("capacity",):
                cap = WikipediaAdapter._parse_capacity(value)
                if cap is not None:
                    fields.capacity = FieldSnippet(value=cap, snippet=snippet)
                continue

            # "Opened" is the date the venue first opened to the public — the
            # canonical "opened year". We deliberately do NOT match
            # "broke ground" / "construction broke ground" / "inaugurated"
            # / "completed" / "closed" / "renovated" — those are all date-ish
            # labels but mean something different and were causing wrong
            # values to land in opened_year.
            if label == "opened":
                year = WikipediaAdapter._parse_year(value)
                if year is not None and fields.opened_year is None:
                    fields.opened_year = FieldSnippet(value=year, snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    # ================================================================ PROMOS

    def fetch_promotion_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_promotion(self, raw_content: str) -> Optional[PromotionFields]:
        """
        Parse a Wikipedia wrestling promotion page. Typical infobox labels:
            "Founded", "Founder(s)", "Headquarters", "Acronym", "Industry",
            "Closed", "Key people", "Website".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = PromotionFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower()
            label = label.replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("acronym", "short name", "abbreviation"):
                if fields.abbreviation is None:
                    fields.abbreviation = FieldSnippet(value=value[:50], snippet=snippet)
                continue
            if label in ("founded", "founded in", "established"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None and fields.founded_year is None:
                    fields.founded_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("closed", "defunct", "dissolved"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None and fields.closed_year is None:
                    fields.closed_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("headquarters", "headquartered", "based in"):
                if fields.headquarters is None:
                    # Multi-segment addresses need comma separators.
                    hq_value = WikipediaAdapter._extract_address_text(td)
                    fields.headquarters = FieldSnippet(value=hq_value, snippet=snippet)
                continue
            if label in ("founder", "founders", "founder(s)"):
                if fields.founder is None:
                    fields.founder = FieldSnippet(value=value, snippet=snippet)
                continue
            if label in ("website", "url"):
                m = re.search(r"https?://[^\s<>\"]+", value)
                if m and fields.website is None:
                    fields.website = FieldSnippet(value=m.group(0), snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    @staticmethod
    def _parse_capacity(value: str) -> Optional[int]:
        """
        Pull the largest plausible capacity number out of a value cell.
        Multi-config venues list "Basketball: 19,812 Hockey: 18,006 Boxing: 20,789" —
        we take the largest. Strips footnote markers and commas.
        """
        text = re.sub(r"\[\d+\]", "", value)
        numbers = []
        for m in re.findall(r"(\d{1,3}(?:,\d{3})+|\d{4,6})", text):
            try:
                n = int(m.replace(",", ""))
                if 100 <= n <= 250_000:  # plausible arena range
                    numbers.append(n)
            except ValueError:
                continue
        return max(numbers) if numbers else None

    # ================================================================ BOOKS

    def fetch_book_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_book(self, raw_content: str) -> Optional[BookFields]:
        """
        Parse a Wikipedia book article. Common Template:Infobox book labels:
            "Author", "Publisher", "Publication date", "ISBN", "Country", "Language".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = BookFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("author", "authors"):
                fields.author = FieldSnippet(value=value, snippet=snippet)
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    target = link["href"][len("/wiki/"):].split("#", 1)[0]
                    from urllib.parse import unquote as _unquote
                    fields.author_wiki_link = FieldSnippet(
                        value=_unquote(target).replace("_", " "), snippet=snippet,
                    )
                continue
            if label in ("publisher",):
                fields.publisher = FieldSnippet(value=value, snippet=snippet)
                continue
            if label in ("publication date", "published", "publication"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.publication_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("isbn",):
                m = re.search(r"\d[\d\-Xx]{9,16}", value)
                if m:
                    fields.isbn = FieldSnippet(value=m.group(0).replace("-", "")[:20], snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    # ============================================================ VIDEO GAMES

    def fetch_video_game_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_video_game(self, raw_content: str) -> Optional[VideoGameFields]:
        """
        Parse a Wikipedia video game article. Common Template:Infobox VG labels:
            "Developer(s)", "Publisher(s)", "Platform(s)", "Release", "Series", "Genre".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = VideoGameFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("developer", "developers", "developer(s)"):
                fields.developer = FieldSnippet(value=value, snippet=snippet)
                continue
            if label in ("publisher", "publishers", "publisher(s)"):
                fields.publisher = FieldSnippet(value=value, snippet=snippet)
                continue
            if label in ("platform", "platforms", "platform(s)", "system", "systems"):
                # Multi-platform — use comma separator.
                joined = WikipediaAdapter._extract_address_text(td)
                fields.systems = FieldSnippet(value=joined[:255], snippet=snippet)
                continue
            if label in ("release", "released", "release date", "release dates"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.release_year = FieldSnippet(value=year, snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    # =============================================================== PODCASTS

    def fetch_podcast_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_podcast(self, raw_content: str) -> Optional[PodcastFields]:
        """
        Parse a Wikipedia podcast article. Common Template:Infobox podcast labels:
            "Hosted by", "Genre", "Language", "Length", "Started", "Ended",
            "Number of episodes", "Provider".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")
        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = PodcastFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("hosted by", "host", "hosts", "presented by", "presenter"):
                # Multi-host: collect comma-separated names and any /wiki/ links.
                items = WikipediaAdapter._extract_multiline(td)
                joined = WikipediaAdapter._join_items(items, value)
                fields.hosts = FieldSnippet(value=joined[:255], snippet=snippet)

                from urllib.parse import unquote as _unquote
                wiki_links: list[str] = []
                for a in td.find_all("a", href=True):
                    href = a.get("href", "")
                    if href.startswith("/wiki/") and "Category:" not in href:
                        t = href[len("/wiki/"):].split("#", 1)[0]
                        wiki_links.append(_unquote(t).replace("_", " "))
                if wiki_links:
                    fields.host_wiki_links = FieldSnippet(
                        value=", ".join(wiki_links)[:500], snippet=snippet,
                    )
                continue
            if label in ("started", "launched", "first episode", "original release"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.launch_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("ended", "final episode"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.end_year = FieldSnippet(value=year, snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    # ========================================================= ACTION FIGURES

    def fetch_action_figure_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_action_figure(self, raw_content: str) -> Optional[ActionFigureFields]:
        """
        Parse a Wikipedia action figure article. Action figure pages typically
        use Template:Infobox toy or have no formal infobox. Key labels:
            "Manufacturer", "Country", "Available", "Released", "Discontinued"
        Some pages document only the line history in prose.
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate — same as classifier; reject non-wrestling pages.
        head_text = ""
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "professional wrestling", "wrestling promotion", "wrestler",
            "wwe", "wwf", "wcw", "ecw", "aew",
        )):
            return None

        # Subject-check: article's first sentence must describe the SUBJECT
        # as an action figure line, not a toy company or wrestling promotion.
        # Catches "Jakks Pacific" (toy company w/ wrestling licensee) being
        # mis-classified as an action_figure.
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        figure_subject_patterns = (
            "action figure",
            "wrestling figure",
            "toy line",
        )
        if not any(p in first_sentence for p in figure_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        fields = ActionFigureFields()
        if infobox is not None:
            for noisy in infobox.find_all(["sup", "style", "script"]):
                noisy.decompose()
            for row in infobox.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if not th or not td:
                    continue
                label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
                value = clean_text(td.get_text())
                if not label or not value:
                    continue
                snippet = f"{label}: {value}"
                if label in ("manufacturer", "company", "made by"):
                    fields.manufacturer = FieldSnippet(value=value[:255], snippet=snippet)
                    continue
                if label in ("available", "released", "release date", "release", "production"):
                    year = WikipediaAdapter._parse_year(value)
                    if year is not None and fields.start_year is None:
                        fields.start_year = FieldSnippet(value=year, snippet=snippet)
                    continue
                if label in ("discontinued", "ended"):
                    year = WikipediaAdapter._parse_year(value)
                    if year is not None and fields.end_year is None:
                        fields.end_year = FieldSnippet(value=year, snippet=snippet)
                    continue

        # Even without an infobox, we can derive manufacturer + promotion from
        # the lead prose using strict patterns. Only attempt if the first
        # sentence explicitly identifies them.
        if body is not None:
            first_p = ""
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_p = t
                        break

            # Manufacturer detection — match well-known toy companies.
            if fields.manufacturer is None and first_p:
                for mfr in ("Jakks Pacific", "Mattel", "Hasbro", "Galoob",
                            "Jazwares", "LJN", "Toy Biz", "Funko",
                            "WCT", "Bend-Ems"):
                    if mfr in first_p:
                        fields.manufacturer = FieldSnippet(
                            value=mfr, snippet=f"first paragraph: {first_p[:200]}",
                        )
                        break

            # Promotion detection — pull the linked promotion from lead, if any.
            if body is not None:
                for a in (body.find_all("a", href=True) if body else [])[:30]:
                    href = a.get("href", "")
                    if href.startswith("/wiki/"):
                        from urllib.parse import unquote as _unquote
                        target = _unquote(href[len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                        if target in ("WWE", "World Wrestling Federation", "WCW",
                                      "World Championship Wrestling", "AEW",
                                      "All Elite Wrestling", "ECW",
                                      "Extreme Championship Wrestling"):
                            fields.promotion_wiki_link = FieldSnippet(
                                value=target, snippet=f"lead link: {target}",
                            )
                            break

        if not fields.populated_fields():
            return None
        return fields

    # ============================================================ THEME SONGS

    def fetch_theme_song_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_theme_song(self, raw_content: str) -> Optional[ThemeSongFields]:
        """
        Parse a Wikipedia song article (Template:Infobox song). Labels:
            "Released", "Recorded", "Genre", "Length", "Label",
            "Songwriter(s)", "Producer(s)".
        Wrestling-relevance gate applies (must reference wrestling in lead).
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate.
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        wrestling_terms = (
            "wrestler", "professional wrestling", "wwe", "wwf", "wcw",
            "entrance theme", "entrance music", "theme song",
        )
        if not any(kw in head_text for kw in wrestling_terms):
            return None

        # Subject-check: first sentence must describe the SUBJECT as a song,
        # not an album/film/wrestler that happens to mention wrestling music.
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        song_subject_patterns = (
            " is a song ", " is a single ", " is the theme",
            " is an entrance ", " is a theme",
        )
        if not any(p in first_sentence for p in song_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = ThemeSongFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"
            if label in ("artist", "by", "performed by", "performer", "performers"):
                fields.artist = FieldSnippet(value=value, snippet=snippet)
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    from urllib.parse import unquote as _unquote
                    target = _unquote(link["href"][len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                    fields.artist_wiki_link = FieldSnippet(value=target, snippet=snippet)
                continue
            if label in ("released", "release date", "release"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.release_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("from the album", "album"):
                fields.album = FieldSnippet(value=value[:255], snippet=snippet)
                continue

        if not fields.populated_fields():
            return None
        return fields

    # ================================================================== TITLES

    def fetch_title_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_title(self, raw_content: str) -> Optional[TitleFields]:
        """
        Parse a Wikipedia championship article. Common Template:Infobox
        professional wrestling championship labels:
            "Promotion", "Brand", "Date established", "First champion",
            "Current champion", "Won at", "Date won".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "professional wrestling", "wrestling championship",
            "wrestler", "wrestling promotion",
        )):
            return None

        # Subject must be a championship
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        title_subject_patterns = (
            "championship", "title", "champion of",
        )
        if not any(p in first_sentence for p in title_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = TitleFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("promotion", "promotions"):
                fields.promotion_name = FieldSnippet(value=value, snippet=snippet)
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    from urllib.parse import unquote as _unquote
                    target = _unquote(link["href"][len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                    fields.promotion_wiki_link = FieldSnippet(value=target, snippet=snippet)
                continue
            if label in ("date established", "established", "introduced", "first awarded"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.debut_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("retired", "deactivated", "discontinued"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.retirement_year = FieldSnippet(value=year, snippet=snippet)
                continue

        # Title type detection from first sentence
        if "tag team" in first_sentence:
            fields.title_type = FieldSnippet(value="tag_team", snippet="from first sentence")
        elif "women's" in first_sentence or "womens" in first_sentence:
            fields.title_type = FieldSnippet(value="women_singles", snippet="from first sentence")
        elif "singles" in first_sentence or "heavyweight" in first_sentence:
            fields.title_type = FieldSnippet(value="singles", snippet="from first sentence")

        if not fields.populated_fields():
            return None
        return fields

    # ================================================================ STABLES

    def fetch_stable_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_stable(self, raw_content: str) -> Optional[StableFields]:
        """
        Parse a Wikipedia stable/faction article. Common Template:Infobox
        professional wrestling group / stable labels:
            "Members", "Former members", "Leader(s)", "Debut", "Disbanded",
            "Promotions", "Stable of".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "professional wrestling", "wrestling stable", "wrestling faction",
            "wrestler", "wrestling tag team",
        )):
            return None

        # Subject must be a stable/faction/team
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        stable_subject_patterns = (
            "stable", "faction", "tag team", "wrestling group", "supergroup",
        )
        if not any(p in first_sentence for p in stable_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = StableFields()
        from urllib.parse import unquote as _unquote

        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("promotion", "promotions"):
                fields.promotion_name = FieldSnippet(value=value, snippet=snippet)
                link = td.find("a", href=True)
                if link and link.get("href", "").startswith("/wiki/"):
                    target = _unquote(link["href"][len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                    fields.promotion_wiki_link = FieldSnippet(value=target, snippet=snippet)
                continue
            if label in ("debut", "formed", "established"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.formed_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("disbanded", "broke up", "split", "ended"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.disbanded_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("leader", "leaders", "leader(s)"):
                wiki_links: list[str] = []
                for a in td.find_all("a", href=True):
                    href = a.get("href", "")
                    if href.startswith("/wiki/"):
                        target = _unquote(href[len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                        wiki_links.append(target)
                if wiki_links:
                    fields.leader_wiki_links = FieldSnippet(
                        value=", ".join(wiki_links)[:500], snippet=snippet,
                    )
                continue
            if label in ("members", "former members"):
                wiki_links = []
                for a in td.find_all("a", href=True):
                    href = a.get("href", "")
                    if href.startswith("/wiki/"):
                        target = _unquote(href[len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                        if target not in wiki_links:
                            wiki_links.append(target)
                if wiki_links:
                    # Append to existing member_wiki_links (members + former).
                    existing = fields.member_wiki_links.value if fields.member_wiki_links else ""
                    combined = existing + (", " if existing else "") + ", ".join(wiki_links)
                    fields.member_wiki_links = FieldSnippet(
                        value=combined[:1500], snippet=snippet,
                    )
                continue

        if not fields.populated_fields():
            return None
        return fields

    # ============================================================== TV SHOWS

    def fetch_tv_show_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_tv_show(self, raw_content: str) -> Optional[TVShowFields]:
        """
        Parse a Wikipedia TV show article. Common Template:Infobox television
        labels: "Genre", "Created by", "Original network", "Original release",
        "Network", "Production company".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "professional wrestling", "wrestler", "wrestling program",
            "wrestling television", "wrestling promotion",
        )):
            return None

        # Subject must be a TV show / series
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        tv_subject_patterns = (
            "television program", "television series", "tv series",
            "television show", "professional wrestling television program",
            "weekly wrestling", "wrestling program",
        )
        if not any(p in first_sentence for p in tv_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = TVShowFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("network", "original network", "current network",
                         "channel", "original release on"):
                fields.network = FieldSnippet(value=value[:255], snippet=snippet)
                continue
            if label in ("original release", "first aired", "release"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None and fields.premiere_year is None:
                    fields.premiere_year = FieldSnippet(value=year, snippet=snippet)
                continue
            if label in ("finale", "final episode", "last aired", "ended"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.finale_year = FieldSnippet(value=year, snippet=snippet)
                continue

        # Promotion detection from lead-paragraph wiki-links
        from urllib.parse import unquote as _unquote
        if body is not None:
            for a in body.find_all("a", href=True)[:40]:
                href = a.get("href", "")
                if href.startswith("/wiki/"):
                    target = _unquote(href[len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                    if target in ("WWE", "World Wrestling Entertainment",
                                  "World Wrestling Federation",
                                  "All Elite Wrestling", "AEW",
                                  "Total Nonstop Action Wrestling",
                                  "Impact Wrestling", "Ring of Honor",
                                  "World Championship Wrestling"):
                        fields.promotion_wiki_link = FieldSnippet(
                            value=target, snippet=f"lead link: {target}",
                        )
                        break

        if not fields.populated_fields():
            return None
        return fields

    # ================================================== SPECIALS / DOCUMENTARIES

    def fetch_special_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_special(self, raw_content: str) -> Optional[SpecialFields]:
        """
        Parse a Wikipedia film/documentary article. Common Template:Infobox
        film labels: "Directed by", "Produced by", "Release date", "Country".
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        # Wrestling-relevance gate
        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "professional wrestling", "wrestler", "wrestling industry",
            "wrestling documentary", "wwe", "wwf", "wcw", "aew",
        )):
            return None

        # Subject must be a documentary/film/TV special
        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        special_patterns = (
            "documentary film", "documentary", "biographical film",
            "drama film", "comedy film", " is a film ", " is a 20",
            " is an american film", "television film", "tv film",
            "tv special", "documentary series",
        )
        if not any(p in first_sentence for p in special_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        if not infobox:
            return None
        for noisy in infobox.find_all(["sup", "style", "script"]):
            noisy.decompose()

        fields = SpecialFields()
        for row in infobox.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
            value = clean_text(td.get_text())
            if not label or not value:
                continue
            snippet = f"{label}: {value}"

            if label in ("directed by", "director", "directors"):
                fields.director = FieldSnippet(value=value[:255], snippet=snippet)
                continue
            if label in ("release date", "release dates", "released",
                         "original release", "first aired"):
                year = WikipediaAdapter._parse_year(value)
                if year is not None:
                    fields.release_year = FieldSnippet(value=year, snippet=snippet)
                continue

        # Type detection from first sentence
        if "documentary series" in first_sentence:
            fields.type = FieldSnippet(value="series", snippet="from first sentence")
        elif "documentary" in first_sentence:
            fields.type = FieldSnippet(value="documentary", snippet="from first sentence")
        elif "television special" in first_sentence or "tv special" in first_sentence:
            fields.type = FieldSnippet(value="tv_special", snippet="from first sentence")
        elif "film" in first_sentence:
            fields.type = FieldSnippet(value="movie", snippet="from first sentence")

        if not fields.populated_fields():
            return None
        return fields

    # ====================================================== TRAINING SCHOOLS

    def fetch_training_school_by_name(self, name: str) -> Optional[FetchResult]:
        return self.fetch_wrestler_by_name(name)

    def extract_training_school(self, raw_content: str) -> Optional[TrainingSchoolFields]:
        """
        Parse a Wikipedia wrestling training-school article. Examples:
        Hart Dungeon, Killer Kowalski's wrestling school, Monster Factory,
        WWE Performance Center. Often these are sections within larger
        articles, but some have their own pages.

        Wrestling-relevance gate + subject-pattern gate apply.
        """
        if not raw_content:
            return None
        soup = BeautifulSoup(raw_content, "lxml")

        body = soup.find("div", class_=re.compile(r"mw-parser-output"))
        head_text = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    head_text += " " + child.get_text(separator=" ", strip=True).lower()
                    if len(head_text) > 1500:
                        break
        if not any(kw in head_text for kw in (
            "wrestling school", "wrestling academy", "wrestler",
            "professional wrestling", "training facility",
        )):
            return None

        first_sentence = ""
        if body is not None:
            for child in body.children:
                if getattr(child, "name", None) == "p":
                    t = child.get_text(separator=" ", strip=True)
                    if len(t) > 30:
                        first_sentence = re.split(r"(?<=[.!?])\s+", t, maxsplit=1)[0].lower()
                        break
        school_subject_patterns = (
            "wrestling school", "wrestling academy",
            "training school", "wrestling dungeon",
            "training facility", "developmental territory",
            "performance center",
        )
        if not any(p in first_sentence for p in school_subject_patterns):
            return None

        infobox = soup.find("table", class_=re.compile(r"\binfobox\b"))
        fields = TrainingSchoolFields()
        if infobox is not None:
            for noisy in infobox.find_all(["sup", "style", "script"]):
                noisy.decompose()
            for row in infobox.find_all("tr"):
                th = row.find("th")
                td = row.find("td")
                if not th or not td:
                    continue
                label = clean_text(th.get_text()).lower().replace("\xa0", " ").strip().rstrip(":")
                value = clean_text(td.get_text())
                if not label or not value:
                    continue
                snippet = f"{label}: {value}"
                if label in ("location", "based", "based in", "address"):
                    if fields.location is None:
                        fields.location = FieldSnippet(
                            value=WikipediaAdapter._extract_address_text(td),
                            snippet=snippet,
                        )
                    continue
                if label in ("founded", "established", "opened"):
                    year = WikipediaAdapter._parse_year(value)
                    if year is not None and fields.founded_year is None:
                        fields.founded_year = FieldSnippet(value=year, snippet=snippet)
                    continue
                if label in ("closed", "defunct"):
                    year = WikipediaAdapter._parse_year(value)
                    if year is not None and fields.closed_year is None:
                        fields.closed_year = FieldSnippet(value=year, snippet=snippet)
                    continue
                if label in ("founder", "founders", "founder(s)"):
                    if fields.founder is None:
                        fields.founder = FieldSnippet(value=value, snippet=snippet)
                    continue
                if label in ("head trainer", "trainer", "trainers",
                             "owner", "owner(s)", "head coach"):
                    if fields.head_trainer is None:
                        fields.head_trainer = FieldSnippet(value=value, snippet=snippet)
                    continue
                if label in ("parent", "parent organization", "operated by"):
                    link = td.find("a", href=True)
                    if link and link.get("href", "").startswith("/wiki/"):
                        from urllib.parse import unquote as _unquote
                        target = _unquote(link["href"][len("/wiki/"):].split("#", 1)[0]).replace("_", " ")
                        fields.parent_promotion_wiki_link = FieldSnippet(
                            value=target, snippet=snippet,
                        )
                    continue

        if not fields.populated_fields():
            return None
        return fields


# ----------------------------------------------------------------------------
# Best-known-as parser
# ----------------------------------------------------------------------------
#
# Wikipedia wrestler articles are titled inconsistently from a fan's
# perspective. Editors pick whichever name has the most weight for that
# article — sometimes the ring name ("Triple H"), sometimes the legal name
# ("Matt Bloom"), sometimes a real name with a disambig suffix
# ("Glenn Jacobs" lives at "Kane (wrestler)"). For display in OWDB, we want
# the name fans actually know — "Mr. Perfect", not "Curt Hennig"; "Rikishi",
# not "Rikishi (wrestler)".
#
# Two signals, in priority order:
#   1. The article's lede paragraph almost always contains one of:
#        "better known by his ring name X"
#        "also known by the ring name X"
#        "best known under the ring names X and Y"
#        "known professionally as X"
#      The first ring name in this phrase is the wrestler's best-known
#      identity. (When there's no such phrase — Matt Bloom, John Cena — the
#      article title is already the best display name.)
#   2. As a fallback, strip a Wikipedia disambig suffix like "(wrestler)"
#      from the article title. These suffixes exist only to disambiguate
#      articles, not because fans say "Rikishi (wrestler)".

# Allow "Mr. Perfect" / "St. Patrick" style internal periods by rejecting
# the period as a sentence stop only when preceded by a known abbreviation.
_BEST_KNOWN_PERIOD_STOP = (
    r"(?<!Mr)(?<!Mrs)(?<!Ms)(?<!Dr)(?<!Jr)(?<!Sr)(?<!St)"
    r"\.\s*(?:[A-Z]|$)"
)

# Variant 1: "better/also/best known [professionally] (as | by/under his ring name) X"
_BEST_KNOWN_LEDE_RE = re.compile(
    r"""
    \b(?:better|also|best)\s+known\s+
    (?:professionally\s+)?
    (?:
        as
      | (?:by|under)\s+(?:his|her|their|the)\s+(?:ring|stage)\s+names?
    )
    \s+
    ['"“‘]?\s*
    (?P<name>[A-ZÀ-ÖØ-Þa-zà-öø-þ][^,(]*?)
    \s*['"”’]?
    (?:,|\s*\(or\b|""" + _BEST_KNOWN_PERIOD_STOP + r"""|\s+(?:is|was|who|were)\b|$)
    """,
    re.X,
)

# Variant 2: "known professionally as X" (no "better"/"also"/"best" prefix)
_BEST_KNOWN_PROFESSIONAL_RE = re.compile(
    r"""
    \bknown\s+professionally\s+as\s+
    ['"“‘]?\s*
    (?P<name>[A-ZÀ-ÖØ-Þa-zà-öø-þ][^,(]*?)
    \s*['"”’]?
    (?:,|\s*\(or\b|""" + _BEST_KNOWN_PERIOD_STOP + r"""|\s+(?:is|was|who|were)\b|$)
    """,
    re.X,
)

# Wikipedia disambig suffixes we'll strip for display. Conservative list —
# only the ones observed on wrestler articles. Other parentheticals
# ("(born 1972)", "(Maryland)") carry information and should stay.
_DISAMBIG_SUFFIX_RE = re.compile(
    r"\s*\((?:wrestler|professional wrestler|wrestler born \d{4})\)\s*$",
    re.I,
)


def _first_lede_paragraph(soup) -> Optional[str]:
    """Return the first long <p> in the article body, or None."""
    body = soup.find("div", class_="mw-parser-output") or soup
    for p in body.find_all("p", recursive=True):
        # Skip <p> tags that live inside the infobox or a sidebar table.
        if p.find_parent("table"):
            continue
        text = p.get_text(" ", strip=True)
        if len(text) > 50:
            return text
    return None


def _ring_name_from_lede(lede: str) -> Optional[str]:
    """Extract the first ring name from a "better known as" phrase, if any."""
    for rx in (_BEST_KNOWN_LEDE_RE, _BEST_KNOWN_PROFESSIONAL_RE):
        m = rx.search(lede)
        if not m:
            continue
        name = m.group("name").strip().strip('"“”‘’\'').rstrip(".").strip()
        # "his ring names X and Y" / "X, Y, and Z" — first is the most famous.
        for sep in (" and ", ", "):
            if sep in name:
                name = name.split(sep, 1)[0].strip()
        if 2 <= len(name) <= 80:
            return name
    return None


def _best_known_as_from_article(soup, article_title: str) -> Optional[FieldSnippet]:
    """
    Compute the wrestler's best-known display name, or None if the article
    title is already the best name. See module-level comment block.
    """
    lede = _first_lede_paragraph(soup)
    if lede:
        name = _ring_name_from_lede(lede)
        if name and name.lower() != article_title.lower():
            return FieldSnippet(
                value=name,
                snippet=lede[:240],
                confidence=92,
            )
    stripped = _DISAMBIG_SUFFIX_RE.sub("", article_title).strip()
    if stripped and stripped != article_title:
        return FieldSnippet(
            value=stripped,
            snippet=f"(article title disambig stripped: {article_title!r} -> {stripped!r})",
            confidence=88,
        )
    return None
