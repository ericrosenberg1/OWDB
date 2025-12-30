"""
Wikipedia scraper for wrestling data.

Wikipedia content is available under CC BY-SA license. We only extract
factual, non-copyrightable data such as:
- Names and ring names
- Birth dates and places
- Career dates
- Promotion affiliations
- Championship histories (factual records)

We do NOT extract:
- Copyrighted prose descriptions
- Images or logos
- Match commentary or storyline descriptions
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure
from .utils import clean_text, parse_date, parse_year

logger = logging.getLogger(__name__)


class WikipediaScraper(BaseScraper):
    """
    Scraper for Wikipedia wrestling data.
    Uses the Wikipedia API where possible for structured data.
    """

    SOURCE_NAME = "wikipedia"
    BASE_URL = "https://en.wikipedia.org"
    API_URL = "https://en.wikipedia.org/w/api.php"

    # Conservative rate limits for Wikipedia
    REQUESTS_PER_MINUTE = 30  # Wikipedia allows higher, but we're respectful
    REQUESTS_PER_HOUR = 500
    REQUESTS_PER_DAY = 5000

    # Category pages to scrape
    WRESTLER_CATEGORIES = [
        "Category:American_male_professional_wrestlers",
        "Category:Japanese_male_professional_wrestlers",
        "Category:Mexican_male_professional_wrestlers",
        "Category:Canadian_male_professional_wrestlers",
        "Category:British_male_professional_wrestlers",
        "Category:American_female_professional_wrestlers",
        "Category:Japanese_female_professional_wrestlers",
        "Category:Mexican_female_professional_wrestlers",
        "Category:WWE_Hall_of_Fame_inductees",
        "Category:Professional_wrestling_trainers",
    ]

    PROMOTION_CATEGORIES = [
        "Category:Professional_wrestling_promotions",
        "Category:American_professional_wrestling_promotions",
        "Category:Japanese_professional_wrestling_promotions",
        "Category:Mexican_professional_wrestling_promotions",
        "Category:British_professional_wrestling_promotions",
    ]

    EVENT_CATEGORIES = [
        "Category:WWE_pay-per-view_events",
        "Category:AEW_pay-per-view_events",
        "Category:Impact_Wrestling_pay-per-view_events",
        "Category:New_Japan_Pro-Wrestling_events",
        "Category:Professional_wrestling_annual_events",
    ]

    def _api_request(self, params: Dict[str, Any]) -> Optional[Dict]:
        """Make a request to the Wikipedia API."""
        params["format"] = "json"
        params["formatversion"] = "2"

        try:
            response = self.fetch(f"{self.API_URL}?{self._encode_params(params)}")
            if response:
                return response.json()
        except Exception as e:
            logger.error(f"Wikipedia API error: {e}")
        return None

    def _encode_params(self, params: Dict[str, Any]) -> str:
        """URL-encode API parameters."""
        return "&".join(f"{k}={quote(str(v))}" for k, v in params.items())

    def get_category_members(
        self, category: str, limit: int = 100, cmtype: str = "page"
    ) -> List[str]:
        """Get page titles from a Wikipedia category."""
        titles = []
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmlimit": min(limit, 500),
            "cmtype": cmtype,
        }

        while len(titles) < limit:
            data = self._api_request(params)
            if not data or "query" not in data:
                break

            members = data["query"].get("categorymembers", [])
            for member in members:
                if len(titles) >= limit:
                    break
                titles.append(member["title"])

            # Check for continuation
            if "continue" in data:
                params["cmcontinue"] = data["continue"]["cmcontinue"]
            else:
                break

        return titles

    def get_page_content(self, title: str) -> Optional[str]:
        """Get the HTML content of a Wikipedia page."""
        params = {
            "action": "parse",
            "page": title,
            "prop": "text",
            "disableeditsection": "true",
        }

        data = self._api_request(params)
        if data and "parse" in data:
            text = data["parse"]["text"]
            # With formatversion=2, text is returned directly as a string
            # With formatversion=1, it's wrapped in {"*": "..."}
            return text if isinstance(text, str) else text.get("*")
        return None

    def get_infobox_data(self, title: str) -> Optional[Dict[str, str]]:
        """Extract infobox data from a Wikipedia page."""
        html = self.get_page_content(title)
        if not html:
            return None

        soup = BeautifulSoup(html, "lxml")
        infobox = soup.find("table", class_="infobox")

        if not infobox:
            return None

        data = {"title": title}

        for row in infobox.find_all("tr"):
            header = row.find("th")
            value = row.find("td")

            if header and value:
                key = clean_text(header.get_text())
                val = clean_text(value.get_text())
                if key and val:
                    data[key.lower().replace(" ", "_")] = val

        return data

    @retry_on_failure(max_retries=3)
    def parse_wrestler_page(self, title: str) -> Optional[Dict[str, Any]]:
        """Parse a wrestler's Wikipedia page for factual data."""
        infobox = self.get_infobox_data(title)
        if not infobox:
            return None

        wrestler = {
            "name": title,
            "source": "wikipedia",
            "source_url": f"{self.BASE_URL}/wiki/{quote(title.replace(' ', '_'))}",
        }

        # Map infobox fields to our model
        field_mapping = {
            "birth_name": "real_name",
            "born": "real_name",  # Sometimes contains birth name
            "ring_name": "aliases",
            "ring_names": "aliases",
            "billed_from": "hometown",
            "residence": "hometown",
            "nationality": "nationality",
            "trained_by": None,  # Skip - not in our model
            "debut": "debut_year",
            "retired": "retirement_year",
        }

        for wiki_field, our_field in field_mapping.items():
            if wiki_field in infobox and our_field:
                value = infobox[wiki_field]

                if our_field in ("debut_year", "retirement_year"):
                    year = parse_year(value)
                    if year:
                        wrestler[our_field] = year
                else:
                    wrestler[our_field] = value

        # Extract finishers if present
        if "finishing_move" in infobox or "finishing_moves" in infobox:
            finishers = infobox.get("finishing_move") or infobox.get("finishing_moves", "")
            wrestler["finishers"] = finishers

        return wrestler

    @retry_on_failure(max_retries=3)
    def parse_promotion_page(self, title: str) -> Optional[Dict[str, Any]]:
        """Parse a promotion's Wikipedia page for factual data."""
        infobox = self.get_infobox_data(title)
        if not infobox:
            return None

        promotion = {
            "name": title,
            "source": "wikipedia",
            "source_url": f"{self.BASE_URL}/wiki/{quote(title.replace(' ', '_'))}",
        }

        # Map infobox fields
        if "acronym" in infobox:
            promotion["abbreviation"] = infobox["acronym"]
        elif "short_name" in infobox:
            promotion["abbreviation"] = infobox["short_name"]

        if "founded" in infobox:
            year = parse_year(infobox["founded"])
            if year:
                promotion["founded_year"] = year

        if "defunct" in infobox or "closed" in infobox:
            defunct = infobox.get("defunct") or infobox.get("closed", "")
            year = parse_year(defunct)
            if year:
                promotion["closed_year"] = year

        if "website" in infobox:
            # Extract URL from text
            url_match = re.search(r"https?://[^\s<>\"]+", infobox["website"])
            if url_match:
                promotion["website"] = url_match.group()

        return promotion

    @retry_on_failure(max_retries=3)
    def parse_event_page(self, title: str) -> Optional[Dict[str, Any]]:
        """Parse an event's Wikipedia page for factual data."""
        infobox = self.get_infobox_data(title)
        if not infobox:
            return None

        event = {
            "name": title,
            "source": "wikipedia",
            "source_url": f"{self.BASE_URL}/wiki/{quote(title.replace(' ', '_'))}",
        }

        # Map infobox fields
        if "date" in infobox or "dates" in infobox:
            date_text = infobox.get("date") or infobox.get("dates", "")
            date = parse_date(date_text)
            if date:
                event["date"] = date

        if "venue" in infobox:
            event["venue_name"] = infobox["venue"]

        if "city" in infobox:
            event["venue_location"] = infobox["city"]
        elif "location" in infobox:
            event["venue_location"] = infobox["location"]

        if "attendance" in infobox:
            # Extract number from attendance
            attendance = re.sub(r"[^\d]", "", infobox["attendance"])
            if attendance:
                try:
                    event["attendance"] = int(attendance)
                except ValueError:
                    pass

        if "promotion" in infobox:
            event["promotion_name"] = infobox["promotion"]

        return event

    def scrape_wrestlers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape wrestler data from Wikipedia."""
        wrestlers = []
        seen_titles = set()

        for category in self.WRESTLER_CATEGORIES:
            if len(wrestlers) >= limit:
                break

            logger.info(f"Scraping category: {category}")
            titles = self.get_category_members(category, limit=limit - len(wrestlers))

            for title in titles:
                if len(wrestlers) >= limit:
                    break

                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # Skip disambiguation and list pages
                if any(
                    x in title.lower()
                    for x in ["(disambiguation)", "list of", "category:"]
                ):
                    continue

                wrestler = self.parse_wrestler_page(title)
                if wrestler:
                    wrestlers.append(wrestler)
                    logger.debug(f"Scraped wrestler: {title}")

        logger.info(f"Scraped {len(wrestlers)} wrestlers from Wikipedia")
        return wrestlers

    def scrape_promotions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape promotion data from Wikipedia."""
        promotions = []
        seen_titles = set()

        for category in self.PROMOTION_CATEGORIES:
            if len(promotions) >= limit:
                break

            logger.info(f"Scraping category: {category}")
            titles = self.get_category_members(category, limit=limit - len(promotions))

            for title in titles:
                if len(promotions) >= limit:
                    break

                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # Skip disambiguation and list pages
                if any(
                    x in title.lower()
                    for x in ["(disambiguation)", "list of", "category:"]
                ):
                    continue

                promotion = self.parse_promotion_page(title)
                if promotion:
                    promotions.append(promotion)
                    logger.debug(f"Scraped promotion: {title}")

        logger.info(f"Scraped {len(promotions)} promotions from Wikipedia")
        return promotions

    def scrape_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape event data from Wikipedia."""
        events = []
        seen_titles = set()

        for category in self.EVENT_CATEGORIES:
            if len(events) >= limit:
                break

            logger.info(f"Scraping category: {category}")
            titles = self.get_category_members(category, limit=limit - len(events))

            for title in titles:
                if len(events) >= limit:
                    break

                if title in seen_titles:
                    continue
                seen_titles.add(title)

                # Skip disambiguation and list pages
                if any(
                    x in title.lower()
                    for x in ["(disambiguation)", "list of", "category:"]
                ):
                    continue

                event = self.parse_event_page(title)
                if event and "date" in event:  # Only include events with dates
                    events.append(event)
                    logger.debug(f"Scraped event: {title}")

        logger.info(f"Scraped {len(events)} events from Wikipedia")
        return events

    def scrape_wrestler_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Search for and scrape a specific wrestler by name."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": f"{name} professional wrestler",
            "srlimit": 5,
        }

        data = self._api_request(params)
        if not data or "query" not in data:
            return None

        for result in data["query"].get("search", []):
            title = result["title"]
            wrestler = self.parse_wrestler_page(title)
            if wrestler:
                return wrestler

        return None
