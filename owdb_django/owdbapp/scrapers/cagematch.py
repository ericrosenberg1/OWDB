"""
Cagematch.net scraper for wrestling data.

IMPORTANT: Cagematch does NOT have an official API. The site owner has explicitly
stated they have no plans to build one. This scraper accesses the public website
while strictly respecting their robots.txt rules.

robots.txt analysis (https://www.cagematch.net/robots.txt):
- Crawl-delay: 527 seconds (~8.8 minutes between requests)
- Disallowed: /cageboard/, /cgi-bin/, /control/, /database/, /db/, etc.
- We only access public /en/ pages for factual data

Cagematch is a fan-run, community-driven wrestling database. We extract only
factual, non-copyrightable data:
- Wrestler profiles (names, dates, physical stats)
- Match results (dates, participants, outcomes)
- Event information (dates, locations, attendance)
- Match ratings (public fan ratings)

We do NOT extract:
- User-generated content from /cageboard/
- Copyrighted prose descriptions
- Private/internal pages

Ethical considerations:
- This is a volunteer-run site with no commercial API
- We use aggressive caching (24+ hours) to minimize requests
- We respect the extremely long crawl-delay in robots.txt
- We use a descriptive User-Agent with contact info
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, parse_qs, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure
from .utils import clean_text, parse_date, parse_year

logger = logging.getLogger(__name__)


class CagematchScraper(BaseScraper):
    """
    Scraper for Cagematch.net wrestling database.

    IMPORTANT: Cagematch has no official API. Their robots.txt specifies:
    - Crawl-delay: 527 seconds (8.8 minutes)
    - Various paths are disallowed

    We respect these rules by:
    1. Using extremely conservative rate limits
    2. Aggressive caching (24-48 hours for most data)
    3. Only accessing allowed public pages
    4. Using a proper User-Agent with contact info

    This scraper should be used sparingly - primarily for one-time imports
    or infrequent enrichment, not continuous scraping.
    """

    SOURCE_NAME = "cagematch"
    BASE_URL = "https://www.cagematch.net"

    # User-Agent with contact info (good practice for any scraper)
    USER_AGENT = "WrestlingDBBot/1.0 (https://wrestlingdb.org; admin@wrestlingdb.org) - respecting robots.txt"

    # Rate limits based on robots.txt Crawl-delay: 527 seconds
    # robots.txt specifies ~8.8 minutes between requests
    # We round down slightly but stay very conservative
    # With these limits, we can do about 7 requests/hour max
    REQUESTS_PER_MINUTE = 1  # Max 1 per minute (we wait longer via crawl delay)
    REQUESTS_PER_HOUR = 7    # ~527 seconds = ~8.8 min per request = ~7/hour
    REQUESTS_PER_DAY = 100   # ~100 requests/day max (very conservative)

    # Minimum delay between requests (from robots.txt Crawl-delay: 527)
    # We'll use 530 seconds to be safe
    MIN_REQUEST_DELAY = 530  # seconds

    # Cagematch URL patterns
    WRESTLER_URL = "/en/?id=2&nr={wrestler_id}"
    EVENT_URL = "/en/?id=1&nr={event_id}"
    PROMOTION_URL = "/en/?id=8&nr={promotion_id}"
    SEARCH_URL = "/en/?id=2&view=workers&search={query}"

    # Extended cache TTLs - since we can only make ~7 requests/hour,
    # we cache aggressively to avoid re-fetching
    CACHE_TTL_PAGE = 86400 * 2  # 48 hours for individual pages
    CACHE_TTL_LIST = 86400      # 24 hours for listing pages

    def __init__(self):
        """Initialize the Cagematch scraper with robots.txt-compliant settings."""
        super().__init__()
        # Set proper User-Agent
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
        })
        # Override the minimum delay to respect robots.txt Crawl-delay
        self._min_request_delay = self.MIN_REQUEST_DELAY
        logger.info(
            f"CagematchScraper initialized with {self.MIN_REQUEST_DELAY}s crawl delay "
            f"(per robots.txt)"
        )

    def _respect_crawl_delay(self, url: str):
        """
        Override parent's crawl delay to enforce robots.txt Crawl-delay: 527.

        The parent class checks robots.txt for crawl-delay, but we enforce
        our own minimum since we know it's 527 seconds.
        """
        import time
        import random

        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_delay:
            wait_time = self._min_request_delay - elapsed + random.uniform(0, 30)
            logger.debug(
                f"Cagematch crawl delay: waiting {wait_time:.1f}s "
                f"(robots.txt requires {self.MIN_REQUEST_DELAY}s)"
            )
            time.sleep(wait_time)

    def _parse_cagematch_id(self, url: str) -> Optional[int]:
        """Extract the numeric ID from a Cagematch URL."""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        if "nr" in params:
            try:
                return int(params["nr"][0])
            except (ValueError, IndexError):
                pass
        return None

    def search_wrestlers(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for wrestlers by name."""
        url = f"{self.BASE_URL}{self.SEARCH_URL.format(query=quote(query))}"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_LIST)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Find search result table
        table = soup.find("table", class_="TBase")
        if not table:
            return []

        for row in table.find_all("tr")[1:]:  # Skip header row
            if len(results) >= limit:
                break

            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            link = cells[0].find("a")
            if not link:
                continue

            wrestler_url = urljoin(self.BASE_URL, link.get("href", ""))
            wrestler_id = self._parse_cagematch_id(wrestler_url)

            if wrestler_id:
                results.append(
                    {
                        "cagematch_id": wrestler_id,
                        "name": clean_text(link.get_text()),
                        "url": wrestler_url,
                    }
                )

        return results

    @retry_on_failure(max_retries=3)
    def parse_wrestler_page(self, wrestler_id: int) -> Optional[Dict[str, Any]]:
        """Parse a wrestler's Cagematch page for factual data."""
        url = f"{self.BASE_URL}{self.WRESTLER_URL.format(wrestler_id=wrestler_id)}"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_PAGE)

        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        wrestler = {
            "cagematch_id": wrestler_id,
            "source": "cagematch",
            "source_url": url,
        }

        # Find the info box
        info_box = soup.find("div", class_="InformationBoxContents")
        if not info_box:
            return None

        # Get wrestler name from title
        title = soup.find("h1", class_="TextHeader")
        if title:
            wrestler["name"] = clean_text(title.get_text())

        # Parse info box rows
        for row in info_box.find_all("div", class_="InformationBoxRow"):
            label_elem = row.find("div", class_="InformationBoxTitle")
            value_elem = row.find("div", class_="InformationBoxContents")

            if not label_elem or not value_elem:
                continue

            label = clean_text(label_elem.get_text()).lower()
            value = clean_text(value_elem.get_text())

            if "alter ego" in label or "ring name" in label:
                wrestler["aliases"] = value
            elif "real name" in label:
                wrestler["real_name"] = value
            elif "birthday" in label or "born" in label:
                date = parse_date(value)
                if date:
                    wrestler["birth_date"] = date
            elif "birthplace" in label:
                wrestler["hometown"] = value
            elif "nationality" in label:
                wrestler["nationality"] = value
            elif "career" in label or "active" in label:
                # Extract debut and retirement years
                years = re.findall(r"\b(19|20)\d{2}\b", value)
                if years:
                    wrestler["debut_year"] = int(years[0])
                    if len(years) > 1:
                        wrestler["retirement_year"] = int(years[-1])
            elif "finisher" in label or "finishing" in label:
                wrestler["finishers"] = value

        return wrestler

    @retry_on_failure(max_retries=3)
    def parse_event_page(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Parse an event's Cagematch page for factual data."""
        url = f"{self.BASE_URL}{self.EVENT_URL.format(event_id=event_id)}"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_PAGE)

        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        event = {
            "cagematch_id": event_id,
            "source": "cagematch",
            "source_url": url,
        }

        # Get event name from title
        title = soup.find("h1", class_="TextHeader")
        if title:
            event["name"] = clean_text(title.get_text())

        # Parse info box
        info_box = soup.find("div", class_="InformationBoxContents")
        if info_box:
            for row in info_box.find_all("div", class_="InformationBoxRow"):
                label_elem = row.find("div", class_="InformationBoxTitle")
                value_elem = row.find("div", class_="InformationBoxContents")

                if not label_elem or not value_elem:
                    continue

                label = clean_text(label_elem.get_text()).lower()
                value = clean_text(value_elem.get_text())

                if "date" in label:
                    date = parse_date(value)
                    if date:
                        event["date"] = date
                elif "venue" in label or "arena" in label:
                    event["venue_name"] = value
                elif "location" in label or "city" in label:
                    event["venue_location"] = value
                elif "attendance" in label:
                    attendance = re.sub(r"[^\d]", "", value)
                    if attendance:
                        try:
                            event["attendance"] = int(attendance)
                        except ValueError:
                            pass
                elif "promotion" in label:
                    event["promotion_name"] = value

        # Parse match card
        matches = []
        match_table = soup.find("div", class_="Matches")
        if match_table:
            for match_row in match_table.find_all("div", class_="Match"):
                match_data = self._parse_match_row(match_row)
                if match_data:
                    matches.append(match_data)

        event["matches"] = matches

        return event

    def _parse_match_row(self, match_row) -> Optional[Dict[str, Any]]:
        """Parse a single match row from an event page."""
        match = {}

        # Get match text (participants)
        match_text_elem = match_row.find("div", class_="MatchCard")
        if match_text_elem:
            match["match_text"] = clean_text(match_text_elem.get_text())

        # Get match result
        result_elem = match_row.find("div", class_="MatchResults")
        if result_elem:
            match["result"] = clean_text(result_elem.get_text())

        # Get match type
        type_elem = match_row.find("div", class_="MatchType")
        if type_elem:
            match["match_type"] = clean_text(type_elem.get_text())

        # Get match rating if available
        rating_elem = match_row.find("div", class_="MatchRating")
        if rating_elem:
            rating_text = clean_text(rating_elem.get_text())
            rating_match = re.search(r"(\d+\.?\d*)", rating_text)
            if rating_match:
                try:
                    match["rating"] = float(rating_match.group(1))
                except ValueError:
                    pass

        if match.get("match_text"):
            return match
        return None

    @retry_on_failure(max_retries=3)
    def parse_promotion_page(self, promotion_id: int) -> Optional[Dict[str, Any]]:
        """Parse a promotion's Cagematch page for factual data."""
        url = f"{self.BASE_URL}{self.PROMOTION_URL.format(promotion_id=promotion_id)}"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_PAGE)

        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        promotion = {
            "cagematch_id": promotion_id,
            "source": "cagematch",
            "source_url": url,
        }

        # Get promotion name from title
        title = soup.find("h1", class_="TextHeader")
        if title:
            promotion["name"] = clean_text(title.get_text())

        # Parse info box
        info_box = soup.find("div", class_="InformationBoxContents")
        if info_box:
            for row in info_box.find_all("div", class_="InformationBoxRow"):
                label_elem = row.find("div", class_="InformationBoxTitle")
                value_elem = row.find("div", class_="InformationBoxContents")

                if not label_elem or not value_elem:
                    continue

                label = clean_text(label_elem.get_text()).lower()
                value = clean_text(value_elem.get_text())

                if "abbreviation" in label or "short" in label:
                    promotion["abbreviation"] = value
                elif "founded" in label:
                    year = parse_year(value)
                    if year:
                        promotion["founded_year"] = year
                elif "closed" in label or "defunct" in label:
                    year = parse_year(value)
                    if year:
                        promotion["closed_year"] = year
                elif "website" in label or "homepage" in label:
                    url_match = re.search(r"https?://[^\s<>\"]+", value)
                    if url_match:
                        promotion["website"] = url_match.group()

        return promotion

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from Cagematch."""
        # Cagematch events listing page
        url = f"{self.BASE_URL}/en/?id=1&view=cards"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_LIST)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        events = []

        # Find event table
        table = soup.find("table", class_="TBase")
        if not table:
            return []

        for row in table.find_all("tr")[1:]:  # Skip header
            if len(events) >= limit:
                break

            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            link = cells[0].find("a")
            if not link:
                continue

            event_url = urljoin(self.BASE_URL, link.get("href", ""))
            event_id = self._parse_cagematch_id(event_url)

            if event_id:
                events.append(
                    {
                        "cagematch_id": event_id,
                        "name": clean_text(link.get_text()),
                        "url": event_url,
                    }
                )

        return events

    def scrape_wrestlers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape wrestler data from Cagematch."""
        wrestlers = []

        # Get wrestler listing
        url = f"{self.BASE_URL}/en/?id=2&view=workers&page=1"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_LIST)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="TBase")

        if not table:
            return []

        for row in table.find_all("tr")[1:]:
            if len(wrestlers) >= limit:
                break

            link = row.find("a")
            if not link:
                continue

            wrestler_url = urljoin(self.BASE_URL, link.get("href", ""))
            wrestler_id = self._parse_cagematch_id(wrestler_url)

            if wrestler_id:
                wrestler = self.parse_wrestler_page(wrestler_id)
                if wrestler:
                    wrestlers.append(wrestler)
                    logger.debug(f"Scraped wrestler: {wrestler.get('name')}")

        logger.info(f"Scraped {len(wrestlers)} wrestlers from Cagematch")
        return wrestlers

    def scrape_promotions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape promotion data from Cagematch."""
        promotions = []

        # Get promotion listing
        url = f"{self.BASE_URL}/en/?id=8&view=promotions"
        html = self.get_cached_or_fetch(url, cache_ttl=self.CACHE_TTL_LIST)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        table = soup.find("table", class_="TBase")

        if not table:
            return []

        for row in table.find_all("tr")[1:]:
            if len(promotions) >= limit:
                break

            link = row.find("a")
            if not link:
                continue

            promotion_url = urljoin(self.BASE_URL, link.get("href", ""))
            promotion_id = self._parse_cagematch_id(promotion_url)

            if promotion_id:
                promotion = self.parse_promotion_page(promotion_id)
                if promotion:
                    promotions.append(promotion)
                    logger.debug(f"Scraped promotion: {promotion.get('name')}")

        logger.info(f"Scraped {len(promotions)} promotions from Cagematch")
        return promotions

    def scrape_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape event data from Cagematch."""
        events = []
        recent = self.get_recent_events(limit=limit)

        for event_info in recent:
            if len(events) >= limit:
                break

            event = self.parse_event_page(event_info["cagematch_id"])
            if event:
                events.append(event)
                logger.debug(f"Scraped event: {event.get('name')}")

        logger.info(f"Scraped {len(events)} events from Cagematch")
        return events
