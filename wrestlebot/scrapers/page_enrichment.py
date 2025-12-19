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
    """
    Discover and enrich pages using multiple data sources.

    Now aggregates data from Wikipedia, Cagematch, ProFightDB to create
    the most complete wrestling encyclopedia possible.
    """

    def __init__(self, api_client):
        self.api_client = api_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })
        self.wikipedia_base = "https://en.wikipedia.org/w/api.php"

        # Initialize multi-source enrichment
        try:
            from .multi_source_enrichment import MultiSourceEnrichment
            self.multi_source = MultiSourceEnrichment(api_client)
            self.use_multi_source = True
            logger.info("Multi-source enrichment enabled (Wikipedia + Cagematch + ProFightDB)")
        except Exception as e:
            logger.warning(f"Multi-source enrichment not available, using Wikipedia only: {e}")
            self.multi_source = None
            self.use_multi_source = False

    def find_and_enrich_incomplete_entries(self) -> int:
        """
        Autonomously find incomplete database entries and enrich them with better data.

        This gives WrestleBot autonomy to improve data quality on its own.
        Returns number of entries enriched.
        """
        enriched_count = 0

        try:
            # Get wrestlers with minimal data (missing key fields)
            wrestlers = self.api_client.list_wrestlers(limit=20)

            for wrestler in wrestlers:
                # Check if wrestler needs enrichment
                needs_enrichment = False
                missing_fields = []

                if not wrestler.get('real_name'):
                    missing_fields.append('real_name')
                    needs_enrichment = True
                if not wrestler.get('debut_year'):
                    missing_fields.append('debut_year')
                    needs_enrichment = True
                if not wrestler.get('hometown'):
                    missing_fields.append('hometown')
                    needs_enrichment = True
                if not wrestler.get('about') or len(wrestler.get('about', '')) < 100:
                    missing_fields.append('about')
                    needs_enrichment = True

                if needs_enrichment:
                    logger.info(f"Autonomously enriching {wrestler['name']} - missing: {', '.join(missing_fields)}")

                    # Use multi-source enrichment if available
                    if self.use_multi_source and self.multi_source:
                        enriched_data = self.multi_source.enrich_wrestler(
                            wrestler['name'],
                            existing_data=wrestler
                        )
                    else:
                        enriched_data = self.enrich_wrestler_from_wikipedia(wrestler['name'])

                    if enriched_data:
                        # Update the wrestler with enriched data
                        result = self.api_client.update_wrestler(wrestler['slug'], enriched_data)
                        if result:
                            enriched_count += 1
                            logger.info(f"✓ Quality improvement: Enriched {wrestler['name']}")
                            break  # Only do one per cycle to avoid overload

        except Exception as e:
            logger.error(f"Error in autonomous quality improvement: {e}")

        return enriched_count

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
        """
        Get a random wrestling-related Wikipedia page to analyze for enrichment.

        This gives the AI autonomy to discover new entities by analyzing
        random wrestling pages and finding wrestlers/promotions/titles/events
        mentioned in those pages that aren't yet in the database.
        """
        logger.info("=== get_random_incomplete_page called ===")
        try:
            # Use Wikipedia's random page feature to find wrestling content
            # This gives AI autonomy to explore and discover new entities organically
            logger.info("About to call _get_random_wrestling_page_from_wikipedia")
            result = self._get_random_wrestling_page_from_wikipedia()
            logger.info(f"_get_random_wrestling_page_from_wikipedia returned: {result is not None}")
            return result

        except Exception as e:
            logger.error(f"Error getting page for enrichment: {e}", exc_info=True)
            return None

    def _get_random_wrestling_page_from_wikipedia(self) -> Optional[Dict]:
        """Get a random wrestling-related page from Wikipedia to analyze."""
        try:
            # Get a random page from wrestling categories
            wrestling_categories = [
                'Professional_wrestlers',
                'Professional_wrestling_promotions',
                'Professional_wrestling_events',
                'Professional_wrestling_champions',
                'Professional_wrestling_in_the_United_States',
                'Professional_wrestling_in_Japan',
            ]

            import random
            category = random.choice(wrestling_categories)
            logger.info(f"Querying Wikipedia category: {category}")

            # Get random members from the category
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmlimit': '20',
                'cmtype': 'page',
            }

            response = self.session.get(self.wikipedia_base, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            logger.info(f"Wikipedia response keys: {list(data.keys())}")

            if 'query' in data and 'categorymembers' in data['query']:
                all_members = data['query']['categorymembers']
                logger.info(f"Found {len(all_members)} total members in category")

                members = [
                    m['title'] for m in all_members
                    if not m['title'].startswith(('Category:', 'List of', 'Template:'))
                ]

                logger.info(f"Filtered to {len(members)} suitable pages")

                if members:
                    # Pick a random page from this category
                    title = random.choice(members)
                    logger.info(f"Selected random page for enrichment: {title} (from {category})")

                    # Get full page content
                    page_info = self._get_wikipedia_page(title)
                    if page_info and page_info.get('extract'):
                        logger.info(f"Got page content ({len(page_info['extract'])} chars) for analysis")
                        return {
                            'type': 'wrestler',  # Default type, will be refined based on content
                            'title': title,
                            'content': page_info.get('extract', ''),
                            'url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                        }
                    else:
                        logger.warning(f"Could not get page content for {title}")
                else:
                    logger.warning(f"No suitable pages after filtering")

            else:
                logger.warning(f"No categorymembers in response. Response: {data}")

            return None

        except Exception as e:
            logger.error(f"Error fetching random Wikipedia page: {e}", exc_info=True)
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
        """
        Get detailed wrestler information from multiple sources.

        Now aggregates data from Wikipedia, Cagematch, and ProFightDB to create
        the most complete profile possible.
        """
        try:
            # If multi-source enrichment is available, use it
            if self.use_multi_source and self.multi_source:
                logger.info(f"Using multi-source enrichment for {wrestler_name}")
                return self.multi_source.enrich_wrestler(wrestler_name)

            # Fallback to Wikipedia-only enrichment
            logger.info(f"Using Wikipedia-only enrichment for {wrestler_name}")
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

    def enrich_promotion_from_wikipedia(self, promotion_name: str) -> Optional[Dict]:
        """Enrich promotion data from Wikipedia."""
        try:
            logger.info(f"Enriching promotion from Wikipedia: {promotion_name}")

            # Search for promotion page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{promotion_name} wrestling',
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

                # Create slug
                name = title
                slug = name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                promotion_data = {
                    'name': name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                }

                # Extract founded year
                founded_match = re.search(r'(?:founded|established)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if founded_match:
                    promotion_data['founded_year'] = int(founded_match.group(1))

                # Extract closed year
                closed_match = re.search(r'(?:closed|defunct|ceased operations)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if closed_match:
                    promotion_data['closed_year'] = int(closed_match.group(1))

                # Extract abbreviation
                abbr_match = re.search(r'\(([A-Z]{2,5})\)', title)
                if abbr_match:
                    promotion_data['abbreviation'] = abbr_match.group(1)

                return promotion_data

        except Exception as e:
            logger.error(f"Error enriching promotion {promotion_name}: {e}")

        return None

    def enrich_event_from_wikipedia(self, event_name: str) -> Optional[Dict]:
        """Enrich event data from Wikipedia."""
        try:
            logger.info(f"Enriching event from Wikipedia: {event_name}")

            # Search for event page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{event_name} wrestling event',
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

                # Create slug
                name = title
                slug = name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                event_data = {
                    'name': name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                }

                # Extract date
                date_match = re.search(r'(\w+\s+\d{1,2},\s+\d{4})', extract)
                if date_match:
                    try:
                        from dateutil import parser
                        event_data['date'] = parser.parse(date_match.group(1)).strftime('%Y-%m-%d')
                    except:
                        pass

                # Try to find promotion from text
                promotion_patterns = ['WWE', 'AEW', 'WCW', 'ECW', 'TNA', 'Impact Wrestling', 'NJPW', 'ROH']
                for promotion in promotion_patterns:
                    if promotion in extract[:500]:  # Check first 500 chars
                        # We'll need to look up the promotion by name
                        # For now, just note it in the about field
                        break

                return event_data

        except Exception as e:
            logger.error(f"Error enriching event {event_name}: {e}")

        return None

    def create_or_update_entity(self, entity_type: str, entity_name: str) -> Optional[Dict]:
        """Create or update an entity (wrestler, promotion, etc.)."""
        try:
            if entity_type == 'wrestler':
                wrestler_data = self.enrich_wrestler_from_wikipedia(entity_name)
                if wrestler_data:
                    return self.api_client.create_wrestler(wrestler_data)

            elif entity_type == 'promotion':
                promotion_data = self.enrich_promotion_from_wikipedia(entity_name)
                if promotion_data:
                    return self.api_client.create_promotion(promotion_data)

            elif entity_type == 'title':
                title_data = self.enrich_title_from_wikipedia(entity_name)
                if title_data:
                    return self.api_client.create_title(title_data)

            elif entity_type == 'stable':
                stable_data = self.enrich_stable_from_wikipedia(entity_name)
                if stable_data:
                    return self.api_client.create_stable(stable_data)

            elif entity_type == 'venue':
                venue_data = self.enrich_venue_from_wikipedia(entity_name)
                if venue_data:
                    return self.api_client.create_venue(venue_data)

            elif entity_type == 'event':
                event_data = self.enrich_event_from_wikipedia(entity_name)
                if event_data:
                    return self.api_client.create_event(event_data)

        except Exception as e:
            logger.error(f"Error creating/updating {entity_type} {entity_name}: {e}")

        return None

    def enrich_title_from_wikipedia(self, title_name: str) -> Optional[Dict]:
        """Enrich championship title data from Wikipedia."""
        try:
            logger.info(f"Enriching title from Wikipedia: {title_name}")

            # Search for title page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{title_name} championship wrestling',
                'srlimit': 1,
            }

            response = self.session.get(self.wikipedia_base, params=search_params, timeout=10)
            data = response.json()

            if 'query' in data and 'search' in data['query'] and data['query']['search']:
                page_title = data['query']['search'][0]['title']

                # Get full page content
                page_info = self._get_wikipedia_page(page_title)
                if not page_info:
                    return None

                extract = page_info['extract']

                # Create slug
                slug = title_name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                title_data = {
                    'name': title_name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                }

                # Extract current champion
                current_match = re.search(r'current champion(?:s)?:?\s+([^\n.]+)', extract, re.IGNORECASE)
                if current_match:
                    title_data['current_champion'] = current_match.group(1).strip()

                # Extract established year
                established_match = re.search(r'(?:established|created)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if established_match:
                    title_data['established_year'] = int(established_match.group(1))

                # Extract retired year
                retired_match = re.search(r'(?:retired|discontinued|deactivated)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if retired_match:
                    title_data['retirement_year'] = int(retired_match.group(1))

                return title_data

        except Exception as e:
            logger.error(f"Error enriching title {title_name}: {e}")

        return None

    def enrich_stable_from_wikipedia(self, stable_name: str) -> Optional[Dict]:
        """Enrich stable/faction data from Wikipedia."""
        try:
            logger.info(f"Enriching stable from Wikipedia: {stable_name}")

            # Search for stable page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{stable_name} wrestling stable',
                'srlimit': 1,
            }

            response = self.session.get(self.wikipedia_base, params=search_params, timeout=10)
            data = response.json()

            if 'query' in data and 'search' in data['query'] and data['query']['search']:
                page_title = data['query']['search'][0]['title']

                # Get full page content
                page_info = self._get_wikipedia_page(page_title)
                if not page_info:
                    return None

                extract = page_info['extract']

                # Create slug
                slug = stable_name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                stable_data = {
                    'name': stable_name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                }

                # Extract formed year
                formed_match = re.search(r'(?:formed|founded)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if formed_match:
                    stable_data['formed_year'] = int(formed_match.group(1))

                # Extract disbanded year
                disbanded_match = re.search(r'(?:disbanded|split|ended)(?:\s+in)?\s+(\d{4})', extract, re.IGNORECASE)
                if disbanded_match:
                    stable_data['disbanded_year'] = int(disbanded_match.group(1))

                # Extract manager
                manager_match = re.search(r'manager:?\s+([^\n.]+)', extract, re.IGNORECASE)
                if manager_match:
                    stable_data['manager'] = manager_match.group(1).strip()

                return stable_data

        except Exception as e:
            logger.error(f"Error enriching stable {stable_name}: {e}")

        return None

    def enrich_venue_from_wikipedia(self, venue_name: str) -> Optional[Dict]:
        """Enrich venue data from Wikipedia."""
        try:
            logger.info(f"Enriching venue from Wikipedia: {venue_name}")

            # Search for venue page
            search_params = {
                'action': 'query',
                'format': 'json',
                'list': 'search',
                'srsearch': f'{venue_name} arena',
                'srlimit': 1,
            }

            response = self.session.get(self.wikipedia_base, params=search_params, timeout=10)
            data = response.json()

            if 'query' in data and 'search' in data['query'] and data['query']['search']:
                page_title = data['query']['search'][0]['title']

                # Get full page content
                page_info = self._get_wikipedia_page(page_title)
                if not page_info:
                    return None

                extract = page_info['extract']

                # Create slug
                slug = venue_name.lower().replace(' ', '-').replace("'", '')
                slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                slug = slug.strip('-_')

                venue_data = {
                    'name': venue_name,
                    'slug': slug,
                    'about': extract[:2000] if extract else '',
                    'wikipedia_url': f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                }

                # Extract location
                location_match = re.search(r'(?:located in|in)\s+([^,\n]+,\s*[A-Z]{2,})', extract, re.IGNORECASE)
                if location_match:
                    venue_data['location'] = location_match.group(1).strip()

                # Extract capacity
                capacity_match = re.search(r'capacity:?\s+([\d,]+)', extract, re.IGNORECASE)
                if capacity_match:
                    try:
                        venue_data['capacity'] = int(capacity_match.group(1).replace(',', ''))
                    except:
                        pass

                return venue_data

        except Exception as e:
            logger.error(f"Error enriching venue {venue_name}: {e}")

        return None
