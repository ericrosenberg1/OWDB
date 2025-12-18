"""
Wikipedia Wrestler Scraper

Discovers and scrapes wrestler data from Wikipedia.
"""

import logging
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class WikipediaWrestlerScraper:
    """Scrapes wrestler data from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"

    # Categories to search for wrestlers
    WRESTLER_CATEGORIES = [
        "American_professional_wrestlers",
        "Japanese_professional_wrestlers",
        "Mexican_professional_wrestlers",
        "Canadian_professional_wrestlers",
        "British_professional_wrestlers",
        "WWE_Hall_of_Fame_inductees",
        "AEW_wrestlers",
        "WWE_wrestlers",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.last_request_time = 0
        self.min_delay = 1.0  # Minimum 1 second between requests

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()

    def get_category_members(self, category: str, limit: int = 20) -> List[str]:
        """Get member pages from a Wikipedia category."""
        self._rate_limit()

        params = {
            'action': 'query',
            'format': 'json',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': limit,
            'cmtype': 'page',  # Only pages, not subcategories
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            members = []
            if 'query' in data and 'categorymembers' in data['query']:
                members = [
                    member['title']
                    for member in data['query']['categorymembers']
                    if not member['title'].startswith('Category:')
                ]

            logger.info(f"Found {len(members)} members in category {category}")
            return members

        except Exception as e:
            logger.error(f"Failed to get category members for {category}: {e}")
            return []

    def get_page_info(self, title: str) -> Optional[Dict]:
        """Get basic information about a Wikipedia page."""
        self._rate_limit()

        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'extracts|pageimages',
            'exintro': True,
            'explaintext': True,
            'pithumbsize': 300,
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                page_data = next(iter(data['query']['pages'].values()))

                if 'missing' in page_data:
                    return None

                return {
                    'title': page_data.get('title'),
                    'extract': page_data.get('extract', ''),
                    'thumbnail': page_data.get('thumbnail', {}).get('source'),
                    'url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get page info for {title}: {e}")
            return None

    def parse_wrestler_data(self, title: str, page_info: Dict) -> Optional[Dict]:
        """Parse wrestler data from Wikipedia page info."""
        extract = page_info.get('extract', '')

        # Very basic parsing - just get the name and create a slug
        name = title

        # Skip disambiguation pages and lists
        if '(disambiguation)' in name or name.startswith('List of'):
            return None

        # Remove common suffixes
        for suffix in [' (wrestler)', ' (professional wrestler)']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]

        # Create slug
        slug = name.lower().replace(' ', '-').replace("'", '')

        # Extract very basic info
        wrestler_data = {
            'name': name,
            'slug': slug,
            'wikipedia_url': page_info['url'],
            'about': extract[:500] if extract else '',  # First 500 chars
        }

        # Try to extract debut year from text
        import re
        debut_match = re.search(r'debut(?:ed)?\s+in\s+(\d{4})', extract, re.IGNORECASE)
        if debut_match:
            wrestler_data['debut_year'] = int(debut_match.group(1))

        return wrestler_data

    def discover_wrestlers(self, max_wrestlers: int = 10) -> List[Dict]:
        """Discover wrestlers from Wikipedia categories."""
        wrestlers = []
        checked_titles = set()

        logger.info(f"Starting wrestler discovery (max: {max_wrestlers})")

        for category in self.WRESTLER_CATEGORIES:
            if len(wrestlers) >= max_wrestlers:
                break

            logger.info(f"Checking category: {category}")
            members = self.get_category_members(category, limit=20)

            for title in members:
                if len(wrestlers) >= max_wrestlers:
                    break

                if title in checked_titles:
                    continue

                checked_titles.add(title)

                page_info = self.get_page_info(title)
                if not page_info:
                    continue

                wrestler_data = self.parse_wrestler_data(title, page_info)
                if wrestler_data:
                    wrestlers.append(wrestler_data)
                    logger.info(f"Discovered wrestler: {wrestler_data['name']}")

        logger.info(f"Discovery complete: found {len(wrestlers)} wrestlers")
        return wrestlers
