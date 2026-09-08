"""
Wrestling match ratings scraper.

Scrapes match quality ratings from various sources to help AI understand
which matches are considered classics and why.

Sources:
- ProFightDB (top-rated matches with Meltzer ratings)
- WrestleTalk Stats (comprehensive ratings database)
- Wikipedia (5+ star matches list)

We only scrape publicly available factual ratings data.
"""

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin

from bs4 import BeautifulSoup

from .base import BaseScraper, retry_on_failure

logger = logging.getLogger(__name__)


class MatchRatingsScraper(BaseScraper):
    """
    Scraper for wrestling match quality ratings.
    Helps AI learn which matches are considered historically significant.
    """

    SOURCE_NAME = "match_ratings"
    BASE_URL = "http://www.profightdb.com"

    # Conservative limits
    REQUESTS_PER_MINUTE = 5
    REQUESTS_PER_HOUR = 50
    REQUESTS_PER_DAY = 400

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        text = " ".join(text.split())
        return text.strip()

    def _parse_rating(self, text: str) -> Optional[float]:
        """Extract rating value from text."""
        if not text:
            return None

        # Match patterns like "5.0", "4.5", "★★★★★"
        number_match = re.search(r"(\d+(?:\.\d+)?)", text)
        if number_match:
            try:
                rating = float(number_match.group(1))
                # Ratings are typically 0-7 scale (Meltzer goes beyond 5)
                if 0 <= rating <= 7:
                    return rating
            except ValueError:
                pass

        # Count stars
        star_count = text.count("★") + text.count("*")
        if star_count > 0:
            # Look for half stars
            half_stars = text.count("½") + text.count("0.5")
            return float(star_count) + (0.5 if half_stars > 0 else 0)

        return None

    @retry_on_failure(max_retries=2)
    def scrape_profightdb_top_rated(self, year: Optional[int] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Scrape top-rated matches from ProFightDB.

        Args:
            year: Optional year to filter by (e.g., 2024)
            limit: Maximum number of matches to return

        Returns:
            List of match records with ratings
        """
        if year:
            url = f"{self.BASE_URL}/top-rated-matches-{year}.html"
        else:
            url = f"{self.BASE_URL}/top-rated-matches.html"

        response = self.fetch(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        matches = []

        # ProFightDB uses tables for match listings
        table = soup.find("table", class_=re.compile("match|result|rating"))
        if not table:
            # Try finding any table with match data
            tables = soup.find_all("table")
            for t in tables:
                if t.find("th", string=re.compile("rating|match|wrestler", re.I)):
                    table = t
                    break

        if not table:
            logger.warning(f"Could not find match ratings table at {url}")
            return []

        rows = table.find_all("tr")[1:]  # Skip header row

        for row in rows:
            if len(matches) >= limit:
                break

            try:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue

                # Extract match participants (usually first 2-3 cells)
                participants = []
                for cell in cells[:3]:
                    text = self._clean_text(cell.get_text())
                    # Look for wrestler names (skip dates, ratings, etc)
                    if text and not re.match(r"^\d+\.?\d*$", text) and not re.match(r"\d{4}-\d{2}-\d{2}", text):
                        # Check if it's a link to a wrestler
                        link = cell.find("a", href=re.compile(r"wrestler|worker"))
                        if link or "vs" in text.lower() or "def" in text.lower():
                            participants.append(text)

                if not participants:
                    continue

                # Extract rating (usually in a cell by itself)
                rating = None
                rating_cell = row.find("td", class_=re.compile("rating|star")) or \
                              row.find("td", string=re.compile(r"^\d+\.?\d*$"))

                if rating_cell:
                    rating = self._parse_rating(rating_cell.get_text())

                # Extract date
                date_cell = row.find("td", string=re.compile(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}"))
                date = self._clean_text(date_cell.get_text()) if date_cell else None

                # Extract event name
                event_cell = row.find("td", class_=re.compile("event")) or \
                            row.find("a", href=re.compile("event"))
                event = self._clean_text(event_cell.get_text()) if event_cell else None

                match_data = {
                    "source": "profightdb",
                    "participants": " vs ".join(participants[:2]) if len(participants) >= 2 else participants[0] if participants else None,
                    "rating": rating,
                    "date": date,
                    "event": event,
                    "year": year,
                }

                # Only add if we have key data
                if match_data["participants"] and match_data["rating"]:
                    matches.append(match_data)
                    logger.debug(f"Scraped match: {match_data['participants']} - {match_data['rating']}★")

            except Exception as e:
                logger.warning(f"Failed to parse match row: {e}")
                continue

        logger.info(f"Scraped {len(matches)} rated matches from ProFightDB (year={year or 'all'})")
        return matches

    @retry_on_failure(max_retries=2)
    def scrape_wikipedia_five_star_matches(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Scrape the Wikipedia list of 5+ star matches.

        This is a curated list of historically significant matches.

        Returns:
            List of elite-rated matches
        """
        url = "https://en.wikipedia.org/wiki/List_of_professional_wrestling_matches_rated_5_or_more_stars_by_Dave_Meltzer"

        response = self.fetch(url)
        if not response:
            return []

        soup = BeautifulSoup(response.text, "lxml")
        matches = []

        # Wikipedia uses tables organized by year
        tables = soup.find_all("table", class_="wikitable")

        for table in tables:
            if len(matches) >= limit:
                break

            rows = table.find_all("tr")[1:]  # Skip header

            for row in rows:
                if len(matches) >= limit:
                    break

                try:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 4:
                        continue

                    # Wikipedia format: Date | Event | Match | Rating
                    date = self._clean_text(cells[0].get_text()) if len(cells) > 0 else None
                    event = self._clean_text(cells[1].get_text()) if len(cells) > 1 else None
                    participants = self._clean_text(cells[2].get_text()) if len(cells) > 2 else None
                    rating_text = self._clean_text(cells[3].get_text()) if len(cells) > 3 else None

                    rating = self._parse_rating(rating_text) if rating_text else None

                    if not participants or not rating:
                        continue

                    match_data = {
                        "source": "wikipedia",
                        "participants": participants,
                        "rating": rating,
                        "date": date,
                        "event": event,
                        "year": int(date.split("-")[0]) if date and "-" in date else None,
                    }

                    matches.append(match_data)
                    logger.debug(f"Scraped 5★ match: {participants} - {rating}★")

                except Exception as e:
                    logger.warning(f"Failed to parse Wikipedia match row: {e}")
                    continue

        logger.info(f"Scraped {len(matches)} 5+ star matches from Wikipedia")
        return matches

    def scrape_top_matches(self, years: Optional[List[int]] = None, per_year_limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape top-rated matches, optionally filtered by years.

        Args:
            years: Optional list of years to scrape (e.g., [2023, 2024, 2025])
            per_year_limit: Max matches per year

        Returns:
            Combined list of top-rated matches
        """
        all_matches = []

        # If years specified, scrape each year
        if years:
            for year in years:
                try:
                    matches = self.scrape_profightdb_top_rated(year=year, limit=per_year_limit)
                    all_matches.extend(matches)
                except Exception as e:
                    logger.error(f"Failed to scrape ratings for year {year}: {e}")
                    continue
        else:
            # Scrape all-time top rated
            try:
                matches = self.scrape_profightdb_top_rated(year=None, limit=per_year_limit * 3)
                all_matches.extend(matches)
            except Exception as e:
                logger.error(f"Failed to scrape all-time top rated matches: {e}")

        # Also get Wikipedia's 5+ star list (historical significance)
        try:
            elite_matches = self.scrape_wikipedia_five_star_matches(limit=50)
            all_matches.extend(elite_matches)
        except Exception as e:
            logger.error(f"Failed to scrape Wikipedia 5★ matches: {e}")

        # Deduplicate by participants + date
        seen = set()
        unique_matches = []
        for match in all_matches:
            key = (match.get("participants"), match.get("date"))
            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        logger.info(f"Scraped total of {len(unique_matches)} unique top-rated matches")
        return unique_matches
