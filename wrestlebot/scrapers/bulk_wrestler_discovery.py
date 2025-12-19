"""
Bulk Wrestler Discovery

Uses Wikipedia's API efficiently to discover ALL wrestlers from categories,
then processes them in bulk without rate limit issues.
"""

import logging
import requests
import time
from typing import List, Dict, Set
import re

logger = logging.getLogger(__name__)


class BulkWrestlerDiscovery:
    """Efficiently discover thousands of wrestlers from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"

    # All wrestling-related categories
    CATEGORIES = [
        "Professional_wrestlers",
        "American_professional_wrestlers",
        "Japanese_professional_wrestlers",
        "Mexican_professional_wrestlers",
        "Canadian_professional_wrestlers",
        "British_professional_wrestlers",
        "Australian_professional_wrestlers",
        "German_professional_wrestlers",
        "French_professional_wrestlers",
        "Italian_professional_wrestlers",
        "WWE_Hall_of_Fame_inductees",
        "AEW_wrestlers",
        "WWE_wrestlers",
        "NXT_wrestlers",
        "Impact_Wrestling_wrestlers",
        "Ring_of_Honor_wrestlers",
        "Lucha_Libre_AAA_Worldwide_wrestlers",
        "New_Japan_Pro-Wrestling_wrestlers",
        "All_Elite_Wrestling_personnel",
        "Women_professional_wrestlers",
        "Male_professional_wrestlers",
        "Professional_wrestling_tag_teams",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.all_wrestler_names: Set[str] = set()

    def get_all_category_members(self, category: str) -> List[str]:
        """Get ALL members from a category using pagination."""
        all_members = []
        continuation = None

        logger.info(f"Fetching ALL members from category: {category}")

        while True:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmlimit': '500',  # Max allowed
                'cmtype': 'page',
            }

            if continuation:
                params['cmcontinue'] = continuation

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()

                if 'query' in data and 'categorymembers' in data['query']:
                    members = [
                        member['title']
                        for member in data['query']['categorymembers']
                        if not member['title'].startswith('Category:')
                        and not member['title'].startswith('List of')
                        and not member['title'].startswith('Template:')
                    ]
                    all_members.extend(members)
                    logger.info(f"  Fetched {len(members)} members (total: {len(all_members)})")

                # Check for continuation
                if 'continue' in data and 'cmcontinue' in data['continue']:
                    continuation = data['continue']['cmcontinue']
                    time.sleep(0.5)  # Be nice to Wikipedia
                else:
                    break

            except Exception as e:
                logger.error(f"Error fetching category {category}: {e}")
                break

        logger.info(f"Category {category}: found {len(all_members)} total members")
        return all_members

    def discover_all_wrestlers(self) -> List[str]:
        """Discover ALL wrestlers from all categories."""
        logger.info("Starting bulk wrestler discovery from all categories...")

        for category in self.CATEGORIES:
            members = self.get_all_category_members(category)
            self.all_wrestler_names.update(members)
            logger.info(f"Total unique wrestlers discovered so far: {len(self.all_wrestler_names)}")

        wrestler_list = sorted(list(self.all_wrestler_names))
        logger.info(f"Discovery complete: {len(wrestler_list)} unique wrestlers found")

        return wrestler_list

    def get_wrestler_details_batch(self, titles: List[str]) -> List[Dict]:
        """Get details for multiple wrestlers in one API call."""
        if not titles:
            return []

        # API allows up to 50 titles per request
        batch_size = 50
        all_details = []

        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'extracts|pageimages',
                'exintro': True,
                'explaintext': True,
                'pithumbsize': 300,
            }

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                response.raise_for_status()
                data = response.json()

                if 'query' in data and 'pages' in data['query']:
                    for page_data in data['query']['pages'].values():
                        if 'missing' in page_data:
                            continue

                        title = page_data.get('title', '')
                        extract = page_data.get('extract', '')

                        # Parse data
                        name = title.replace(' (wrestler)', '').replace(' (professional wrestler)', '')
                        slug = name.lower().replace(' ', '-').replace("'", '')

                        wrestler_data = {
                            'name': name,
                            'slug': slug,
                            'about': extract[:1000] if extract else '',
                            'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        }

                        # Extract debut year
                        debut_match = re.search(r'debut(?:ed)?\s+in\s+(\d{4})', extract, re.IGNORECASE)
                        if debut_match:
                            wrestler_data['debut_year'] = int(debut_match.group(1))

                        all_details.append(wrestler_data)

                logger.info(f"Fetched details for batch {i//batch_size + 1} ({len(batch)} wrestlers)")
                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"Error fetching batch: {e}")

        return all_details
