"""
WrestleBot 2.0 Discovery Engine

Finds new entities to add to the database from various sources.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db.models import Count, Q
from django.utils.text import slugify

logger = logging.getLogger(__name__)


class EntityDiscovery:
    """
    Discovers new entities from external sources.

    Discovery methods:
    1. Parse existing data for references to unknown entities
    2. Search external sources (Wikipedia, Cagematch) for new entries
    3. Follow relationships to find connected entities
    """

    def __init__(self):
        self._coordinator = None
        self._wikipedia_scraper = None
        self._cagematch_scraper = None

    @property
    def coordinator(self):
        """Lazy load scraper coordinator."""
        if self._coordinator is None:
            from ..scrapers.coordinator import ScraperCoordinator
            self._coordinator = ScraperCoordinator()
        return self._coordinator

    @property
    def wikipedia_scraper(self):
        """Lazy load Wikipedia scraper."""
        if self._wikipedia_scraper is None:
            from ..scrapers.wikipedia import WikipediaScraper
            self._wikipedia_scraper = WikipediaScraper()
        return self._wikipedia_scraper

    @property
    def cagematch_scraper(self):
        """Lazy load Cagematch scraper."""
        if self._cagematch_scraper is None:
            from ..scrapers.cagematch import CagematchScraper
            self._cagematch_scraper = CagematchScraper()
        return self._cagematch_scraper

    def discover_wrestlers_from_matches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find wrestler names mentioned in match text but not in database.

        Parses match descriptions for wrestler names and creates entries
        for those not found in the database.
        """
        from ..models import Match, Wrestler

        discovered = []
        existing_names = set(
            Wrestler.objects.values_list('name', flat=True).iterator()
        )
        existing_names_lower = {name.lower() for name in existing_names}

        # Also check aliases
        for wrestler in Wrestler.objects.exclude(aliases='').exclude(aliases__isnull=True):
            if wrestler.aliases:
                for alias in wrestler.aliases.split(','):
                    existing_names_lower.add(alias.strip().lower())

        # Get recent matches with text that might contain names
        matches = Match.objects.exclude(
            match_text=''
        ).exclude(
            match_text__isnull=True
        ).order_by('-id')[:500]

        potential_names: Set[str] = set()

        for match in matches:
            # Extract names from match text
            names = self._extract_names_from_match(match.match_text)
            for name in names:
                if name.lower() not in existing_names_lower:
                    potential_names.add(name)

        # Verify and add new wrestlers
        for name in list(potential_names)[:limit]:
            try:
                # Try to find on Wikipedia
                wrestler_data = self.wikipedia_scraper.search_wrestler(name)
                if wrestler_data:
                    discovered.append({
                        'name': name,
                        'data': wrestler_data,
                        'source': 'wikipedia',
                    })
                    logger.info(f"Discovered wrestler from match text: {name}")
            except Exception as e:
                logger.warning(f"Failed to verify wrestler {name}: {e}")

        return discovered[:limit]

    def _extract_names_from_match(self, match_text: str) -> List[str]:
        """Extract potential wrestler names from match text."""
        names = []

        # Common patterns in match text:
        # "John Cena defeated Randy Orton"
        # "The Rock vs Stone Cold Steve Austin"
        # "Triple H (c) vs Shawn Michaels"

        # Remove common non-name words
        stop_words = {
            'defeated', 'def', 'beat', 'pinned', 'submitted', 'won', 'lost',
            'drew', 'retained', 'captured', 'defended', 'vacant', 'vacated',
            'via', 'by', 'after', 'with', 'and', 'the', 'for', 'match',
            'title', 'championship', 'belt', 'minutes', 'seconds', 'time',
            'disqualification', 'dq', 'countout', 'count', 'out', 'pinfall',
            'submission', 'referee', 'stoppage', 'no', 'contest', 'draw',
            'table', 'ladder', 'cage', 'cell', 'steel', 'falls', 'anywhere',
        }

        # Split by common separators
        parts = re.split(r'\s+vs\.?\s+|\s+def\.?\s+|\s+defeated\s+|\s+beat\s+|\s+&\s+|\s+and\s+', match_text, flags=re.IGNORECASE)

        for part in parts:
            # Clean up the part
            part = re.sub(r'\([^)]*\)', '', part)  # Remove parentheses content
            part = re.sub(r'\[[^\]]*\]', '', part)  # Remove bracket content
            part = part.strip()

            # Check if it looks like a name (2-4 capitalized words)
            words = part.split()
            if 1 <= len(words) <= 4:
                # Check if words are mostly capitalized and not stop words
                valid_words = [
                    w for w in words
                    if w[0].isupper() and w.lower() not in stop_words
                ]
                if len(valid_words) >= len(words) * 0.5:
                    name = ' '.join(words)
                    if len(name) >= 3:  # Minimum name length
                        names.append(name)

        return names

    def discover_wrestlers_from_wikipedia(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover new wrestlers from Wikipedia wrestler lists.

        Checks Wikipedia's wrestler category pages for entries not in database.
        """
        from ..models import Wrestler

        discovered = []
        existing_names = set(
            Wrestler.objects.values_list('name', flat=True).iterator()
        )
        existing_names_lower = {name.lower() for name in existing_names}

        try:
            # Get list of wrestlers from Wikipedia
            wrestlers = self.wikipedia_scraper.scrape_wrestlers(limit=limit * 2)

            for wrestler_data in wrestlers:
                name = wrestler_data.get('name', '')
                if name.lower() not in existing_names_lower:
                    discovered.append({
                        'name': name,
                        'data': wrestler_data,
                        'source': 'wikipedia',
                    })
                    existing_names_lower.add(name.lower())

                    if len(discovered) >= limit:
                        break

            logger.info(f"Discovered {len(discovered)} wrestlers from Wikipedia")

        except Exception as e:
            logger.error(f"Failed to discover wrestlers from Wikipedia: {e}")

        return discovered

    def discover_events_from_promotions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover events for promotions that have few events.

        Finds promotions with low event counts and searches for their events.
        """
        from ..models import Promotion, Event

        discovered = []

        # Find promotions with few events
        promotions_needing_events = Promotion.objects.annotate(
            event_count=Count('events')
        ).filter(
            event_count__lt=10
        ).order_by('event_count')[:5]

        for promotion in promotions_needing_events:
            try:
                # Search Wikipedia for events
                events = self.wikipedia_scraper.search_promotion_events(
                    promotion.name,
                    promotion.abbreviation,
                    limit=limit
                )

                for event_data in events:
                    # Check if event already exists
                    event_name = event_data.get('name', '')
                    event_date = event_data.get('date', '')

                    exists = Event.objects.filter(
                        name__iexact=event_name,
                        date=event_date
                    ).exists()

                    if not exists:
                        event_data['promotion_name'] = promotion.name
                        discovered.append({
                            'name': event_name,
                            'data': event_data,
                            'source': 'wikipedia',
                        })

                        if len(discovered) >= limit:
                            break

            except Exception as e:
                logger.warning(f"Failed to discover events for {promotion.name}: {e}")

            if len(discovered) >= limit:
                break

        logger.info(f"Discovered {len(discovered)} events from promotions")
        return discovered

    def discover_promotions_from_wrestlers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover promotions mentioned in wrestler data but not in database.

        Parses wrestler bios and histories for promotion references.
        """
        from ..models import Wrestler, Promotion

        discovered = []
        existing_promos = set(
            Promotion.objects.values_list('name', flat=True).iterator()
        )
        existing_promos_lower = {name.lower() for name in existing_promos}

        # Also check abbreviations
        for promo in Promotion.objects.exclude(abbreviation='').exclude(abbreviation__isnull=True):
            if promo.abbreviation:
                existing_promos_lower.add(promo.abbreviation.lower())

        # Common promotion names to look for
        known_promotions = {
            'WWE', 'AEW', 'TNA', 'IMPACT', 'ROH', 'NJPW', 'CMLL', 'AAA',
            'ECW', 'WCW', 'NWA', 'MLW', 'GCW', 'PWG', 'NOAH', 'AJPW',
            'DDT', 'STARDOM', 'SHIMMER', 'CHIKARA', 'CZW', 'ICW', 'OVW',
            'FCW', 'NXT', 'WWF', 'AWA', 'WCCW', 'SMW', 'USWA', 'GAEA',
        }

        # Get wrestlers with bios
        wrestlers = Wrestler.objects.exclude(
            bio=''
        ).exclude(
            bio__isnull=True
        )[:200]

        potential_promos: Set[str] = set()

        for wrestler in wrestlers:
            if wrestler.bio:
                # Look for promotion names in bio
                for promo in known_promotions:
                    if promo in wrestler.bio and promo.lower() not in existing_promos_lower:
                        potential_promos.add(promo)

        # Try to get more info on discovered promotions
        for promo_name in list(potential_promos)[:limit]:
            try:
                promo_data = self.wikipedia_scraper.search_promotion(promo_name)
                if promo_data:
                    discovered.append({
                        'name': promo_name,
                        'data': promo_data,
                        'source': 'wikipedia',
                    })
                    logger.info(f"Discovered promotion from wrestler bio: {promo_name}")
            except Exception as e:
                logger.warning(f"Failed to verify promotion {promo_name}: {e}")

        return discovered[:limit]

    def discover_venues_from_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Discover venues mentioned in events but not in database.
        """
        from ..models import Event, Venue

        discovered = []

        # Get events without venues that might have venue info
        events = Event.objects.filter(
            venue__isnull=True
        ).exclude(
            Q(venue_name='') | Q(venue_name__isnull=True)
        )[:limit * 2]

        existing_venues = set(
            Venue.objects.values_list('name', flat=True).iterator()
        )
        existing_venues_lower = {name.lower() for name in existing_venues}

        for event in events:
            venue_name = getattr(event, 'venue_name', None)
            if venue_name and venue_name.lower() not in existing_venues_lower:
                discovered.append({
                    'name': venue_name,
                    'data': {
                        'name': venue_name,
                        'location': getattr(event, 'venue_location', ''),
                    },
                    'source': 'event_data',
                })
                existing_venues_lower.add(venue_name.lower())

                if len(discovered) >= limit:
                    break

        logger.info(f"Discovered {len(discovered)} venues from events")
        return discovered

    def run_discovery_cycle(
        self,
        entity_types: List[str] = None,
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run a full discovery cycle for specified entity types.

        Args:
            entity_types: List of entity types to discover (default: all)
            limit: Maximum entities to discover per type

        Returns:
            Dict mapping entity type to list of discovered entities
        """
        if entity_types is None:
            entity_types = ['wrestler', 'event', 'promotion', 'venue']

        results = {}

        for entity_type in entity_types:
            try:
                if entity_type == 'wrestler':
                    # Combine multiple discovery methods
                    from_matches = self.discover_wrestlers_from_matches(limit=limit // 2)
                    from_wikipedia = self.discover_wrestlers_from_wikipedia(limit=limit // 2)
                    results['wrestler'] = from_matches + from_wikipedia

                elif entity_type == 'event':
                    results['event'] = self.discover_events_from_promotions(limit=limit)

                elif entity_type == 'promotion':
                    results['promotion'] = self.discover_promotions_from_wrestlers(limit=limit)

                elif entity_type == 'venue':
                    results['venue'] = self.discover_venues_from_events(limit=limit)

                logger.info(f"Discovery cycle for {entity_type}: found {len(results.get(entity_type, []))} entities")

            except Exception as e:
                logger.error(f"Discovery cycle failed for {entity_type}: {e}")
                results[entity_type] = []

        return results

    def import_discovered_entities(
        self,
        discoveries: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, int]:
        """
        Import discovered entities into the database.

        Returns count of successfully imported entities per type.
        """
        from .models import WrestleBotActivity

        imported = {}

        for entity_type, entities in discoveries.items():
            count = 0

            for discovery in entities:
                try:
                    start_time = time.time()
                    entity_id = None

                    if entity_type == 'wrestler':
                        entity_id = self.coordinator.import_wrestler(discovery['data'])
                    elif entity_type == 'event':
                        entity_id = self.coordinator.import_event(discovery['data'])
                    elif entity_type == 'promotion':
                        entity_id = self.coordinator.import_promotion(discovery['data'])
                    elif entity_type == 'venue':
                        entity_id = self._import_venue(discovery['data'])

                    if entity_id:
                        count += 1
                        duration_ms = int((time.time() - start_time) * 1000)

                        # Log the activity
                        WrestleBotActivity.log_activity(
                            action_type='discover',
                            entity_type=entity_type,
                            entity_id=entity_id,
                            entity_name=discovery['name'],
                            source=discovery.get('source', 'unknown'),
                            details={'imported_data': discovery['data']},
                            duration_ms=duration_ms,
                        )

                except Exception as e:
                    logger.error(f"Failed to import {entity_type} {discovery['name']}: {e}")
                    WrestleBotActivity.log_activity(
                        action_type='error',
                        entity_type=entity_type,
                        entity_id=0,
                        entity_name=discovery['name'],
                        source=discovery.get('source', 'unknown'),
                        success=False,
                        error_message=str(e),
                    )

            imported[entity_type] = count

        return imported

    def _import_venue(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a venue to the database."""
        from ..models import Venue

        name = data.get('name', '')
        if not name:
            return None

        venue, created = Venue.objects.get_or_create(
            name=name,
            defaults={
                'slug': slugify(name),
                'location': data.get('location', ''),
                'capacity': data.get('capacity'),
            }
        )

        if created:
            logger.info(f"Created venue: {name}")
            return venue.id
        else:
            logger.debug(f"Venue already exists: {name}")
            return venue.id
