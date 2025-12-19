"""
Bulk Event Discovery

Discovers wrestling events from Wikipedia categories.
"""

import logging
import requests
import time
from typing import List, Dict, Set
import re
from datetime import datetime

logger = logging.getLogger(__name__)


class BulkEventDiscovery:
    """Efficiently discover wrestling events from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"

    CATEGORIES = [
        "WWE_pay-per-view_events",
        "AEW_pay-per-view_events",
        "WrestleMania",
        "Royal_Rumble",
        "SummerSlam",
        "Survivor_Series",
        "WWE_Network_events",
        "NXT_TakeOver",
        "New_Japan_Pro-Wrestling_events",
        "Ring_of_Honor_pay-per-view_events",
        "Impact_Wrestling_pay-per-view_events",
        "WCW_pay-per-view_events",
        "ECW_pay-per-view_events",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.all_event_names: Set[str] = set()

    def get_all_category_members(self, category: str) -> List[str]:
        """Get ALL members from a category using pagination."""
        all_members = []
        continuation = None

        logger.info(f"Fetching events from category: {category}")

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

                if 'continue' in data and 'cmcontinue' in data['continue']:
                    continuation = data['continue']['cmcontinue']
                    time.sleep(0.5)
                else:
                    break

            except Exception as e:
                logger.error(f"Error fetching category {category}: {e}")
                break

        logger.info(f"Category {category}: found {len(all_members)} events")
        return all_members

    def discover_all_events(self) -> List[str]:
        """Discover ALL events from all categories."""
        logger.info("Starting bulk event discovery...")

        for category in self.CATEGORIES:
            members = self.get_all_category_members(category)
            self.all_event_names.update(members)
            logger.info(f"Total unique events discovered: {len(self.all_event_names)}")

        event_list = sorted(list(self.all_event_names))
        logger.info(f"Discovery complete: {len(event_list)} unique events found")

        return event_list

    def get_event_details_batch(self, titles: List[str]) -> List[Dict]:
        """Get details for multiple events in one API call."""
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

                        # Extract event name and slug
                        name = title
                        slug = name.lower().replace(' ', '-').replace("'", '').replace(':', '')

                        event_data = {
                            'name': name,
                            'slug': slug,
                        }

                        # Try to extract date (various formats)
                        date_patterns = [
                            r'(\w+\s+\d{1,2},\s+\d{4})',  # "January 25, 2020"
                            r'(\d{4}-\d{2}-\d{2})',  # "2020-01-25"
                            r'held on.*?(\w+\s+\d{1,2},\s+\d{4})',
                            r'took place.*?(\w+\s+\d{1,2},\s+\d{4})',
                        ]

                        for pattern in date_patterns:
                            date_match = re.search(pattern, extract[:500], re.IGNORECASE)
                            if date_match:
                                try:
                                    date_str = date_match.group(1)
                                    # Try to parse date
                                    if '-' in date_str:
                                        event_data['date'] = date_str
                                    else:
                                        parsed = datetime.strptime(date_str, '%B %d, %Y')
                                        event_data['date'] = parsed.strftime('%Y-%m-%d')
                                    break
                                except:
                                    pass

                        # Extract venue
                        venue_match = re.search(r'(?:at|held at)(?:\s+the)?\s+([^.,\n]+(?:Arena|Stadium|Center|Centre|Garden|Dome|Hall|Coliseum))', extract, re.IGNORECASE)
                        if venue_match:
                            event_data['venue_name'] = venue_match.group(1).strip()

                        # Extract location from venue
                        location_match = re.search(r'in\s+([^.,\n]+(?:,\s*[A-Z]{2})?)', extract[:500])
                        if location_match:
                            event_data['venue_location'] = location_match.group(1).strip()

                        # Extract promotion (look for WWE, AEW, etc. in first paragraph)
                        promo_match = re.search(r'\b(WWE|AEW|WCW|ECW|NXT|NJPW|Impact Wrestling|Ring of Honor|ROH)\b', extract[:200])
                        if promo_match:
                            event_data['promotion_name'] = promo_match.group(1)

                        # Extract attendance
                        attendance_match = re.search(r'attendance.*?(\d{1,3}(?:,\d{3})+)', extract, re.IGNORECASE)
                        if attendance_match:
                            try:
                                event_data['attendance'] = int(attendance_match.group(1).replace(',', ''))
                            except:
                                pass

                        all_details.append(event_data)

                logger.info(f"Fetched details for batch {i//batch_size + 1} ({len(batch)} events)")
                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching batch: {e}")

        return all_details
