"""
ProFightDB scraper for historical wrestling data.

ProFightDB (profightdb.com) is a historical wrestling database.
We scrape factual data only:
- Wrestler career records
- Historical event results
- Title histories

We respect their robots.txt and rate limits.
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, parse_qs, urlparse

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure

logger = logging.getLogger(__name__)


class ProFightDBScraper(BaseScraper):
    """
    Scraper for ProFightDB historical wrestling database.
    Focuses on historical records and comprehensive career data.
    """

    SOURCE_NAME = "profightdb"
    BASE_URL = "https://www.profightdb.com"

    # Conservative rate limits
    REQUESTS_PER_MINUTE = 5
    REQUESTS_PER_HOUR = 60
    REQUESTS_PER_DAY = 500

    # ProFightDB has SSL certificate issues - disable verification
    VERIFY_SSL = False

    def _create_session(self):
        """Create a requests session with SSL verification disabled for ProFightDB."""
        session = super()._create_session()
        session.verify = self.VERIFY_SSL
        return session

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = " ".join(text.split())
        return text.strip()

    def _parse_date(self, text: str) -> Optional[str]:
        """Parse a date string."""
        if not text:
            return None

        patterns = [
            (r"(\d{4})-(\d{2})-(\d{2})", "%Y-%m-%d"),
            (r"(\w+) (\d{1,2}), (\d{4})", "%B %d, %Y"),
            (r"(\d{1,2})/(\d{1,2})/(\d{4})", "%m/%d/%Y"),
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if "-" in pattern:
                        date_str = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
                    elif "/" in pattern:
                        date_str = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
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
        url = f"{self.BASE_URL}/search?q={quote(query)}"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        results = []

        # Find wrestler search results
        wrestler_section = soup.find("div", id="wrestlers") or soup.find(
            "section", class_="wrestlers"
        )

        if not wrestler_section:
            # Try generic search results
            for link in soup.find_all("a", href=re.compile(r"/wrestlers/")):
                if len(results) >= limit:
                    break

                name = self._clean_text(link.get_text())
                href = link.get("href", "")

                if name and href:
                    results.append(
                        {
                            "name": name,
                            "url": urljoin(self.BASE_URL, href),
                        }
                    )
        else:
            for link in wrestler_section.find_all("a"):
                if len(results) >= limit:
                    break

                name = self._clean_text(link.get_text())
                href = link.get("href", "")

                if name and href:
                    results.append(
                        {
                            "name": name,
                            "url": urljoin(self.BASE_URL, href),
                        }
                    )

        return results

    @retry_on_failure(max_retries=3)
    def parse_wrestler_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse a wrestler's ProFightDB page for factual data."""
        html = self.get_cached_or_fetch(url, cache_ttl=86400)

        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        wrestler = {
            "source": "profightdb",
            "source_url": url,
        }

        # Get wrestler name
        title = soup.find("h1") or soup.find("title")
        if title:
            name = self._clean_text(title.get_text())
            # Remove site name from title
            name = re.sub(r"\s*[-|]\s*ProFightDB.*$", "", name, flags=re.IGNORECASE)
            wrestler["name"] = name

        # Look for info table or details section
        info_table = soup.find("table", class_="info") or soup.find(
            "div", class_="wrestler-info"
        )

        if info_table:
            for row in info_table.find_all("tr"):
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    label = self._clean_text(cells[0].get_text()).lower()
                    value = self._clean_text(cells[1].get_text())

                    if "real name" in label or "birth name" in label:
                        wrestler["real_name"] = value
                    elif "also known as" in label or "ring name" in label:
                        wrestler["aliases"] = value
                    elif "birth" in label and "place" in label:
                        wrestler["hometown"] = value
                    elif "nationality" in label:
                        wrestler["nationality"] = value
                    elif "debut" in label:
                        year = self._parse_year(value)
                        if year:
                            wrestler["debut_year"] = year
                    elif "retired" in label:
                        year = self._parse_year(value)
                        if year:
                            wrestler["retirement_year"] = year
                    elif "finish" in label:
                        wrestler["finishers"] = value

        return wrestler if wrestler.get("name") else None

    @retry_on_failure(max_retries=3)
    def parse_event_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse an event's ProFightDB page for factual data."""
        html = self.get_cached_or_fetch(url, cache_ttl=86400)

        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")

        event = {
            "source": "profightdb",
            "source_url": url,
        }

        # Get event name
        title = soup.find("h1")
        if title:
            event["name"] = self._clean_text(title.get_text())

        # Look for event info
        info_section = soup.find("div", class_="event-info") or soup.find(
            "table", class_="info"
        )

        if info_section:
            text = info_section.get_text()

            # Try to extract date
            date = self._parse_date(text)
            if date:
                event["date"] = date

            # Try to extract venue
            venue_match = re.search(
                r"(?:venue|arena|location):\s*([^,\n]+)", text, re.IGNORECASE
            )
            if venue_match:
                event["venue_name"] = self._clean_text(venue_match.group(1))

            # Try to extract attendance
            attendance_match = re.search(r"attendance:\s*([\d,]+)", text, re.IGNORECASE)
            if attendance_match:
                try:
                    event["attendance"] = int(
                        attendance_match.group(1).replace(",", "")
                    )
                except ValueError:
                    pass

        # Parse match card
        matches = []
        match_table = soup.find("table", class_="matches") or soup.find(
            "div", class_="match-card"
        )

        if match_table:
            for row in match_table.find_all("tr"):
                match_data = self._parse_match_row(row)
                if match_data:
                    matches.append(match_data)

        event["matches"] = matches

        return event if event.get("name") else None

    def _parse_match_row(self, row) -> Optional[Dict[str, Any]]:
        """Parse a single match row from an event page."""
        cells = row.find_all("td")
        if not cells:
            return None

        match = {}

        # Look for participants
        participants = []
        for link in row.find_all("a", href=re.compile(r"/wrestlers/")):
            name = self._clean_text(link.get_text())
            if name:
                participants.append(name)

        if participants:
            match["match_text"] = " vs ".join(participants)

        # Look for result/winner
        for cell in cells:
            text = self._clean_text(cell.get_text()).lower()
            if "def" in text or "defeat" in text or "win" in text:
                match["result"] = self._clean_text(cell.get_text())
                break

        # Look for match type
        type_patterns = [
            "singles",
            "tag team",
            "triple threat",
            "fatal four",
            "battle royal",
            "cage",
            "ladder",
            "tables",
            "tlc",
            "royal rumble",
            "elimination chamber",
        ]

        row_text = row.get_text().lower()
        for pattern in type_patterns:
            if pattern in row_text:
                match["match_type"] = pattern.title()
                break

        return match if match.get("match_text") else None

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from ProFightDB."""
        url = f"{self.BASE_URL}/events"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        events = []

        # Find event links
        for link in soup.find_all("a", href=re.compile(r"/events/")):
            if len(events) >= limit:
                break

            name = self._clean_text(link.get_text())
            href = link.get("href", "")

            if name and href and name.lower() not in ["events", "more"]:
                events.append(
                    {
                        "name": name,
                        "url": urljoin(self.BASE_URL, href),
                    }
                )

        return events

    def get_wrestler_list(self, letter: str = "a", limit: int = 100) -> List[Dict[str, Any]]:
        """Get a list of wrestlers starting with a letter."""
        url = f"{self.BASE_URL}/wrestlers/{letter}"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        wrestlers = []

        for link in soup.find_all("a", href=re.compile(r"/wrestlers/[^/]+$")):
            if len(wrestlers) >= limit:
                break

            name = self._clean_text(link.get_text())
            href = link.get("href", "")

            if name and href:
                wrestlers.append(
                    {
                        "name": name,
                        "url": urljoin(self.BASE_URL, href),
                    }
                )

        return wrestlers

    def scrape_wrestlers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape wrestler data from ProFightDB."""
        wrestlers = []
        letters = "abcdefghijklmnopqrstuvwxyz"

        for letter in letters:
            if len(wrestlers) >= limit:
                break

            wrestler_list = self.get_wrestler_list(
                letter, limit=limit - len(wrestlers)
            )

            for wrestler_info in wrestler_list:
                if len(wrestlers) >= limit:
                    break

                wrestler = self.parse_wrestler_page(wrestler_info["url"])
                if wrestler:
                    wrestlers.append(wrestler)
                    logger.debug(f"Scraped wrestler: {wrestler.get('name')}")

        logger.info(f"Scraped {len(wrestlers)} wrestlers from ProFightDB")
        return wrestlers

    def scrape_promotions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape promotion data from ProFightDB."""
        # ProFightDB doesn't have a dedicated promotions section
        # We extract promotion info from events
        promotions = []
        url = f"{self.BASE_URL}/promotions"
        html = self.get_cached_or_fetch(url, cache_ttl=3600)

        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")

        for link in soup.find_all("a", href=re.compile(r"/promotions/")):
            if len(promotions) >= limit:
                break

            name = self._clean_text(link.get_text())
            href = link.get("href", "")

            if name and href:
                promotion = {
                    "name": name,
                    "source": "profightdb",
                    "source_url": urljoin(self.BASE_URL, href),
                }
                promotions.append(promotion)
                logger.debug(f"Scraped promotion: {name}")

        logger.info(f"Scraped {len(promotions)} promotions from ProFightDB")
        return promotions

    def scrape_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape event data from ProFightDB."""
        events = []
        recent = self.get_recent_events(limit=limit)

        for event_info in recent:
            if len(events) >= limit:
                break

            event = self.parse_event_page(event_info["url"])
            if event and event.get("date"):
                events.append(event)
                logger.debug(f"Scraped event: {event.get('name')}")

        logger.info(f"Scraped {len(events)} events from ProFightDB")
        return events
