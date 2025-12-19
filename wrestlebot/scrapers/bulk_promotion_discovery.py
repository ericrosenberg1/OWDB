"""
Bulk Promotion Discovery

Discovers all wrestling promotions from Wikipedia categories.
"""

import logging
import requests
import time
from typing import List, Dict, Set
import re

logger = logging.getLogger(__name__)


class BulkPromotionDiscovery:
    """Efficiently discover promotions from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"

    CATEGORIES = [
        "Professional_wrestling_promotions",
        "American_professional_wrestling_promotions",
        "Japanese_professional_wrestling_promotions",
        "Mexican_professional_wrestling_promotions",
        "Canadian_professional_wrestling_promotions",
        "British_professional_wrestling_promotions",
        "Australian_professional_wrestling_promotions",
        "Independent_professional_wrestling_promotions_in_the_United_States",
        "Defunct_professional_wrestling_promotions",
        "Former_professional_wrestling_promotions",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.all_promotion_names: Set[str] = set()

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
                'cmlimit': '500',
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

                if 'continue' in data and 'cmcontinue' in data['continue']:
                    continuation = data['continue']['cmcontinue']
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                logger.error(f"Error fetching category {category}: {e}")
                break

        logger.info(f"Category {category}: found {len(all_members)} total members")
        return all_members

    def discover_all_promotions(self) -> List[str]:
        """Discover ALL promotions from all categories."""
        logger.info("Starting bulk promotion discovery from all categories...")

        for category in self.CATEGORIES:
            members = self.get_all_category_members(category)
            self.all_promotion_names.update(members)
            logger.info(f"Total unique promotions discovered so far: {len(self.all_promotion_names)}")

        promotion_list = sorted(list(self.all_promotion_names))
        logger.info(f"Discovery complete: {len(promotion_list)} unique promotions found")

        return promotion_list

    def get_promotion_details_batch(self, titles: List[str]) -> List[Dict]:
        """Get details for multiple promotions in one API call."""
        if not titles:
            return []

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

                        name = title.replace(' (wrestling)', '').replace(' (professional wrestling)', '')
                        # Create valid slug - only letters, numbers, hyphens, underscores
                        slug = name.lower().replace(' ', '-').replace("'", '').replace('&', 'and')
                        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                        slug = slug.strip('-_')

                        promotion_data = {
                            'name': name,
                            'slug': slug,
                            'about': extract[:1000] if extract else '',
                            'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        }

                        # Extract founded year
                        founded_match = re.search(r'(?:founded|established).*?(\d{4})', extract, re.IGNORECASE)
                        if founded_match:
                            promotion_data['founded_year'] = int(founded_match.group(1))

                        # Extract closed year
                        closed_match = re.search(r'(?:closed|defunct|ceased).*?(\d{4})', extract, re.IGNORECASE)
                        if closed_match:
                            promotion_data['closed_year'] = int(closed_match.group(1))

                        # Extract abbreviation (look for common patterns like "WWE", "AEW", etc.)
                        abbrev_match = re.search(r'\b([A-Z]{2,6})\b', extract[:500])
                        if abbrev_match and abbrev_match.group(1) != title:
                            promotion_data['abbreviation'] = abbrev_match.group(1)

                        all_details.append(promotion_data)

                logger.info(f"Fetched details for batch {i//batch_size + 1} ({len(batch)} promotions)")
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching batch: {e}")

        return all_details
