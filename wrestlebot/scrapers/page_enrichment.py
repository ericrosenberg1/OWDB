"""
Page Enrichment Discovery

Analyzes existing pages to find missing entities and improve content.
Discovers wrestlers, promotions, titles, etc. mentioned but not yet in database.
"""

import logging
import requests
import re
from typing import List, Dict, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class PageEnrichmentDiscovery:
    """Discover and enrich pages based on existing content."""

    def __init__(self, api_client):
        self.api_client = api_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.wikipedia_base = "https://en.wikipedia.org/w/api.php"

    def analyze_page_for_missing_entities(self, page_type: str, page_data: Dict) -> Dict:
        """
        Analyze a page's content to find mentioned entities not yet in database.

        Returns:
            {
                'wrestlers': [names],
                'promotions': [names],
                'titles': [names],
                'events': [names]
            }
        """
        content = page_data.get('about', '') or ''

        # Extract names mentioned in content
        mentioned = {
            'wrestlers': self._extract_wrestler_names(content),
            'promotions': self._extract_promotion_names(content),
            'titles': self._extract_title_names(content),
            'events': self._extract_event_names(content)
        }

        return mentioned

    def _extract_wrestler_names(self, text: str) -> Set[str]:
        """Extract potential wrestler names from text."""
        names = set()

        # Look for patterns like "defeated X", "vs X", "teamed with X"
        patterns = [
            r'(?:defeated|beat|lost to|faced|wrestled|vs\.?|versus|teamed with|partnered with|feuded with)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            r'(?:champion|title holder|wrestler)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+(?:won|held|defended|lost)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                # Filter out common words
                if match.lower() not in ['the', 'a', 'an', 'this', 'that', 'and', 'or', 'but']:
                    if len(match.split()) <= 4:  # Reasonable name length
                        names.add(match.strip())

        return names

    def _extract_promotion_names(self, text: str) -> Set[str]:
        """Extract potential promotion names from text."""
        names = set()

        # Look for common promotion patterns
        patterns = [
            r'\b(WWE|WWF|WCW|ECW|AEW|NXT|TNA|Impact Wrestling|Ring of Honor|ROH|NJPW|New Japan Pro-Wrestling)\b',
            r'\b([A-Z]{2,6})\s+(?:Wrestling|Championship Wrestling)',
            r'(?:in|for|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\s+Wrestling)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                names.add(match.strip())

        return names

    def _extract_title_names(self, text: str) -> Set[str]:
        """Extract potential championship titles from text."""
        names = set()

        # Look for championship patterns
        patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\s+Championship',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,4})\s+(?:Title|Belt|Champion)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if 'championship' not in match.lower():  # Will be added back
                    names.add(match.strip() + ' Championship')

        return names

    def _extract_event_names(self, text: str) -> Set[str]:
        """Extract potential event names from text."""
        names = set()

        # Look for event patterns
        patterns = [
            r'\b(WrestleMania|Royal Rumble|SummerSlam|Survivor Series|Money in the Bank|Hell in a Cell)\s*\d*\b',
            r'(?:at|during)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+\d{4}',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                names.add(match.strip())

        return names

    def get_random_incomplete_page(self) -> Optional[Dict]:
        """Get a random page that could use enrichment."""
        try:
            import random

            # Try to get wrestlers from database first
            status = self.api_client.get_status()
            if not status:
                return None

            total_wrestlers = status.get('total_wrestlers', 0)
            total_promotions = status.get('total_promotions', 0)
            total_events = status.get('total_events', 0)

            # Pick a random entity type to enrich
            choices = []
            if total_wrestlers > 0:
                choices.append('wrestler')
            if total_promotions > 0:
                choices.append('promotion')
            if total_events > 0:
                choices.append('event')

            if not choices:
                logger.info("No existing pages to enrich yet")
                return None

            entity_type = random.choice(choices)

            # Get a random page from that type
            if entity_type == 'wrestler':
                offset = random.randint(0, max(0, total_wrestlers - 10))
                wrestlers = self.api_client.list_wrestlers(limit=10, offset=offset)
                if wrestlers:
                    wrestler = random.choice(wrestlers)
                    return {
                        'type': 'wrestler',
                        'title': wrestler.get('name', ''),
                        'content': wrestler.get('about', ''),
                        'url': wrestler.get('wikipedia_url', ''),
                        'entity': wrestler
                    }

            elif entity_type == 'promotion':
                offset = random.randint(0, max(0, total_promotions - 10))
                promotions = self.api_client.list_promotions(limit=10, offset=offset)
                if promotions:
                    promotion = random.choice(promotions)
                    return {
                        'type': 'promotion',
                        'title': promotion.get('name', ''),
                        'content': promotion.get('about', ''),
                        'url': promotion.get('wikipedia_url', ''),
                        'entity': promotion
                    }

            elif entity_type == 'event':
                offset = random.randint(0, max(0, total_events - 10))
                events = self.api_client.list_events(limit=10, offset=offset)
                if events:
                    event = random.choice(events)
                    return {
                        'type': 'event',
                        'title': event.get('name', ''),
                        'content': event.get('about', ''),
                        'url': event.get('wikipedia_url', ''),
                        'entity': event
                    }

            return None

        except Exception as e:
            logger.error(f"Error getting incomplete page: {e}")
            return None

    def _get_wrestler_needing_enrichment(self) -> Optional[Dict]:
        """Find a wrestler that needs more information."""
        # Search Wikipedia for a random wrestling-related page
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'random',
                'rnnamespace': 0,
                'rnlimit': 1,
            }

            response = self.session.get(self.wikipedia_base, params=params, timeout=10)
            data = response.json()

            if 'query' in data and 'random' in data['query']:
                title = data['query']['random'][0]['title']

                # Get page content
                page_info = self._get_wikipedia_page(title)
                if page_info and 'wrestling' in page_info.get('extract', '').lower():
                    return {
                        'type': 'wrestler',
                        'title': title,
                        'content': page_info.get('extract', ''),
                        'url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    }

        except Exception as e:
            logger.error(f"Error finding page for enrichment: {e}")

        return None

    def _get_wikipedia_page(self, title: str) -> Optional[Dict]:
        """Get Wikipedia page content."""
        try:
            params = {
                'action': 'query',
                'format': 'json',
                'titles': title,
                'prop': 'extracts',
                'explaintext': True,
                'exintro': False,  # Get full text
            }

            response = self.session.get(self.wikipedia_base, params=params, timeout=10)
            data = response.json()

            if 'query' in data and 'pages' in data['query']:
                page = next(iter(data['query']['pages'].values()))
                if 'missing' not in page:
                    return {
                        'title': page.get('title'),
                        'extract': page.get('extract', '')
                    }

        except Exception as e:
            logger.error(f"Error fetching Wikipedia page: {e}")

        return None

    def enrich_wrestler_from_wikipedia(self, wrestler_name: str) -> Optional[Dict]:
        """Get detailed wrestler information from Wikipedia."""
        try:
            # Search for wrestler page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{wrestler_name} wrestler',
                'srlimit': 1,
            }

            response = self.session.get(self.wikipedia_base, params=search_params, timeout=10)
            data = response.json()

            if 'query' in data and 'search' in data['query'] and data['query']['search']:
                title = data['query']['search'][0]['title']

                # Get full page content
                page_info = self._get_wikipedia_page(title)
                if not page_info:
                    return None

                extract = page_info['extract']

                # Extract wrestler data
                name = title.replace(' (wrestler)', '').replace(' (professional wrestler)', '')
                slug = name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                wrestler_data = {
                    'name': name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',  # More content
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                }

                # Extract detailed information
                self._extract_wrestler_details(extract, wrestler_data)

                return wrestler_data

        except Exception as e:
            logger.error(f"Error enriching wrestler {wrestler_name}: {e}")

        return None

    def _extract_wrestler_details(self, text: str, data: Dict):
        """Extract detailed information from wrestler biography."""
        # Real name
        real_name_match = re.search(r'(?:born|real name|birth name)(?:\s+as)?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})', text, re.IGNORECASE)
        if real_name_match:
            data['real_name'] = real_name_match.group(1).strip()

        # Birth date
        birth_match = re.search(r'born\s+(?:on\s+)?(\w+\s+\d{1,2},\s+\d{4})', text, re.IGNORECASE)
        if birth_match:
            try:
                from dateutil import parser
                data['birth_date'] = parser.parse(birth_match.group(1)).strftime('%Y-%m-%d')
            except:
                pass

        # Debut year
        debut_match = re.search(r'debut(?:ed)?(?:\s+in)?\s+(\d{4})', text, re.IGNORECASE)
        if debut_match:
            data['debut_year'] = int(debut_match.group(1))

        # Retirement year
        retired_match = re.search(r'retired(?:\s+in)?\s+(\d{4})', text, re.IGNORECASE)
        if retired_match:
            data['retirement_year'] = int(retired_match.group(1))

        # Hometown
        hometown_match = re.search(r'from\s+([^,.\n]+,\s*[A-Z]{2})', text)
        if hometown_match:
            data['hometown'] = hometown_match.group(1).strip()

        # Nationality
        nationality_match = re.search(r'(?:American|Japanese|Mexican|Canadian|British|Australian|German|French|Italian)\s+(?:professional\s+)?wrestler', text, re.IGNORECASE)
        if nationality_match:
            nationality = nationality_match.group(0).split()[0]
            data['nationality'] = nationality.capitalize()

        # Height
        height_match = re.search(r'(\d+)\s*(?:ft|feet)\s+(\d+)\s*(?:in|inches)', text)
        if height_match:
            data['height'] = f"{height_match.group(1)}'{height_match.group(2)}\""

        # Weight
        weight_match = re.search(r'(\d{2,3})\s*(?:lb|lbs|pounds)', text)
        if weight_match:
            data['weight'] = f"{weight_match.group(1)} lbs"

        # Finishers
        finisher_match = re.search(r'(?:finishing move|finisher)s?:?\s+([^\n.]+)', text, re.IGNORECASE)
        if finisher_match:
            finishers = finisher_match.group(1).strip()
            # Clean up
            finishers = re.sub(r'\s+and\s+', ', ', finishers)
            data['finishers'] = finishers[:200]  # Limit length

    def create_or_update_entity(self, entity_type: str, entity_name: str) -> Optional[Dict]:
        """Create or update an entity (wrestler, promotion, etc.)."""
        try:
            if entity_type == 'wrestler':
                wrestler_data = self.enrich_wrestler_from_wikipedia(entity_name)
                if wrestler_data:
                    return self.api_client.create_wrestler(wrestler_data)

            elif entity_type == 'promotion':
                # TODO: Implement promotion enrichment
                pass

            elif entity_type == 'title':
                # TODO: Implement title enrichment
                pass

            elif entity_type == 'event':
                # TODO: Implement event enrichment
                pass

        except Exception as e:
            logger.error(f"Error creating/updating {entity_type} {entity_name}: {e}")

        return None
