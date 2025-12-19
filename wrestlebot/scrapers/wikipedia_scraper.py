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
        self.discovered_slugs = set()  # Track discovered wrestlers
        self.current_category_index = 0
        self.current_category_offset = 0

    def _rate_limit(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()

    def get_category_members(self, category: str, limit: int = 20, offset: int = 0) -> List[str]:
        """Get member pages from a Wikipedia category with pagination."""
        self._rate_limit()

        params = {
            'action': 'query',
            'format': 'json',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': limit,
            'cmtype': 'page',  # Only pages, not subcategories
        }

        # Add offset for pagination if needed
        if offset > 0:
            params['cmstart'] = offset

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

            logger.info(f"Found {len(members)} members in category {category} (offset: {offset})")
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
        """Discover NEW wrestlers from Wikipedia categories with pagination."""
        wrestlers = []
        attempts = 0
        max_attempts = 50  # Prevent infinite loops

        logger.info(f"Starting wrestler discovery (max: {max_wrestlers})")

        while len(wrestlers) < max_wrestlers and attempts < max_attempts:
            attempts += 1

            # Get current category
            if self.current_category_index >= len(self.WRESTLER_CATEGORIES):
                self.current_category_index = 0
                self.current_category_offset += 20  # Move to next page

            category = self.WRESTLER_CATEGORIES[self.current_category_index]
            logger.info(f"Checking category: {category} (offset: {self.current_category_offset})")

            members = self.get_category_members(category, limit=20, offset=self.current_category_offset)

            if not members:
                # No more members in this category, move to next
                self.current_category_index += 1
                self.current_category_offset = 0
                logger.info(f"Category exhausted, moving to next")
                continue

            found_new = False
            for title in members:
                if len(wrestlers) >= max_wrestlers:
                    break

                # Create slug to check if already discovered
                slug = title.lower().replace(' ', '-').replace("'", '')
                for suffix in ['-wrestler', '-professional-wrestler']:
                    if slug.endswith(suffix):
                        slug = slug[:-len(suffix)]

                if slug in self.discovered_slugs:
                    continue

                page_info = self.get_page_info(title)
                if not page_info:
                    continue

                wrestler_data = self.parse_wrestler_data(title, page_info)
                if wrestler_data:
                    self.discovered_slugs.add(wrestler_data['slug'])
                    wrestlers.append(wrestler_data)
                    found_new = True
                    logger.info(f"Discovered NEW wrestler: {wrestler_data['name']}")

            if not found_new:
                # Didn't find any new wrestlers in this batch, move to next category
                self.current_category_index += 1
                self.current_category_offset = 0

        logger.info(f"Discovery complete: found {len(wrestlers)} new wrestlers (total tracked: {len(self.discovered_slugs)})")
        return wrestlers
