"""
Cagematch.net scraper for wrestling data.

Cagematch is a public wrestling database. We scrape factual data only:
- Wrestler profiles (names, dates, physical stats)
- Match results (dates, participants, outcomes)
- Event information (dates, locations, attendance)
- Match ratings (public fan ratings)

We respect their robots.txt and rate limits.
We do NOT scrape copyrighted content like match descriptions or reviews.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, parse_qs, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure

logger = logging.getLogger(__name__)


class CagematchScraper(BaseScraper):
    """
    Scraper for Cagematch.net wrestling database.
    Focuses on factual match results and wrestler data.
    """

    SOURCE_NAME = "cagematch"
    BASE_URL = "https://www.cagematch.net"

    # Very conservative rate limits - be respectful to fan-run sites
    REQUESTS_PER_MINUTE = 5
    REQUESTS_PER_HOUR = 60
    REQUESTS_PER_DAY = 500

    # Cagematch URL patterns
    WRESTLER_URL = "/en/?id=2&nr={wrestler_id}"
    EVENT_URL = "/en/?id=1&nr={event_id}"
    PROMOTION_URL = "/en/?id=8&nr={promotion_id}"
    SEARCH_URL = "/en/?id=2&view=workers&search={query}"

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

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        # Remove extra whitespace
        text = " ".join(text.split())
        return text.strip()

    def _parse_date(self, text: str) -> Optional[str]:
        """Parse a date string from Cagematch format."""
        if not text:
            return None

        # Cagematch uses formats like "01.01.2020" or "January 1, 2020"
        patterns = [
            (r"(\d{2})\.(\d{2})\.(\d{4})", "%d.%m.%Y"),  # 01.01.2020
            (r"(\w+) (\d{1,2}), (\d{4})", "%B %d, %Y"),  # January 1, 2020
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if "." in pattern:
                        date_str = f"{match.group(1)}.{match.group(2)}.{match.group(3)}"
                    else:
                        date_str = f"{match.group(1)} {match.group(2)}, {match.group(3)}"
                    dt = datetime.strptime(date_str, date_format)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue

        return None

    def _parse_year(self, text: str) -> Optional[int]:
        """Extract a year from text."""
        if not text:
            return None
        match = re.search(r"\b(19|20)\d{2}\b", text)
        if match:
            return int(match.group())
        return None

    def search_wrestlers(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for wrestlers by name."""
        url = f"{self.BASE_URL}{self.SEARCH_URL.format(query=quote(query))}"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

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
                        "name": self._clean_text(link.get_text()),
                        "url": wrestler_url,
                    }
                )

        return results

    @retry_on_failure(max_retries=3)
    def parse_wrestler_page(self, wrestler_id: int) -> Optional[Dict[str, Any]]:
        """Parse a wrestler's Cagematch page for factual data."""
        url = f"{self.BASE_URL}{self.WRESTLER_URL.format(wrestler_id=wrestler_id)}"
        html = self.get_cached_or_fetch(url, cache_ttl=86400)  # Cache for 24 hours

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
            wrestler["name"] = self._clean_text(title.get_text())

        # Parse info box rows
        for row in info_box.find_all("div", class_="InformationBoxRow"):
            label_elem = row.find("div", class_="InformationBoxTitle")
            value_elem = row.find("div", class_="InformationBoxContents")

            if not label_elem or not value_elem:
                continue

            label = self._clean_text(label_elem.get_text()).lower()
            value = self._clean_text(value_elem.get_text())

            if "alter ego" in label or "ring name" in label:
                wrestler["aliases"] = value
            elif "real name" in label:
                wrestler["real_name"] = value
            elif "birthday" in label or "born" in label:
                date = self._parse_date(value)
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
        html = self.get_cached_or_fetch(url, cache_ttl=86400)

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
            event["name"] = self._clean_text(title.get_text())

        # Parse info box
        info_box = soup.find("div", class_="InformationBoxContents")
        if info_box:
            for row in info_box.find_all("div", class_="InformationBoxRow"):
                label_elem = row.find("div", class_="InformationBoxTitle")
                value_elem = row.find("div", class_="InformationBoxContents")

                if not label_elem or not value_elem:
                    continue

                label = self._clean_text(label_elem.get_text()).lower()
                value = self._clean_text(value_elem.get_text())

                if "date" in label:
                    date = self._parse_date(value)
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
            match["match_text"] = self._clean_text(match_text_elem.get_text())

        # Get match result
        result_elem = match_row.find("div", class_="MatchResults")
        if result_elem:
            match["result"] = self._clean_text(result_elem.get_text())

        # Get match type
        type_elem = match_row.find("div", class_="MatchType")
        if type_elem:
            match["match_type"] = self._clean_text(type_elem.get_text())

        # Get match rating if available
        rating_elem = match_row.find("div", class_="MatchRating")
        if rating_elem:
            rating_text = self._clean_text(rating_elem.get_text())
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
        html = self.get_cached_or_fetch(url, cache_ttl=86400)

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
            promotion["name"] = self._clean_text(title.get_text())

        # Parse info box
        info_box = soup.find("div", class_="InformationBoxContents")
        if info_box:
            for row in info_box.find_all("div", class_="InformationBoxRow"):
                label_elem = row.find("div", class_="InformationBoxTitle")
                value_elem = row.find("div", class_="InformationBoxContents")

                if not label_elem or not value_elem:
                    continue

                label = self._clean_text(label_elem.get_text()).lower()
                value = self._clean_text(value_elem.get_text())

                if "abbreviation" in label or "short" in label:
                    promotion["abbreviation"] = value
                elif "founded" in label:
                    year = self._parse_year(value)
                    if year:
                        promotion["founded_year"] = year
                elif "closed" in label or "defunct" in label:
                    year = self._parse_year(value)
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
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

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
                        "name": self._clean_text(link.get_text()),
                        "url": event_url,
                    }
                )

        return events

    def scrape_wrestlers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape wrestler data from Cagematch."""
        wrestlers = []

        # Get wrestler listing
        url = f"{self.BASE_URL}/en/?id=2&view=workers&page=1"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

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
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

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
