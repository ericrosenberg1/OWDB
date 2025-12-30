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
        from . import ScraperProvider
        self._scrapers = ScraperProvider()

    @property
    def coordinator(self):
        """Get scraper coordinator from shared provider."""
        return self._scrapers.coordinator

    @property
    def wikipedia_scraper(self):
        """Get Wikipedia scraper from shared provider."""
        return self._scrapers.wikipedia_scraper

    @property
    def cagematch_scraper(self):
        """Get Cagematch scraper from shared provider."""
        return self._scrapers.cagematch_scraper

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
                # Try to find on Wikipedia using scrape_wrestler_by_name
                wrestler_data = self.wikipedia_scraper.scrape_wrestler_by_name(name)
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
        """
        Extract potential wrestler names from match text.

        Common patterns:
        - "John Cena defeated Randy Orton"
        - "The Rock vs Stone Cold Steve Austin"
        - "Triple H (c) vs Shawn Michaels"
        - "Team Alpha (Wrestler A, Wrestler B) vs Team Beta"
        - "Wrestler A & Wrestler B defeated Wrestler C & Wrestler D"
        """
        names = []

        # Common non-name words to filter out
        stop_words = {
            'defeated', 'def', 'beat', 'pinned', 'submitted', 'won', 'lost',
            'drew', 'retained', 'captured', 'defended', 'vacant', 'vacated',
            'via', 'by', 'after', 'with', 'and', 'the', 'for', 'match',
            'title', 'championship', 'belt', 'minutes', 'seconds', 'time',
            'disqualification', 'dq', 'countout', 'count', 'out', 'pinfall',
            'submission', 'referee', 'stoppage', 'no', 'contest', 'draw',
            'table', 'ladder', 'cage', 'cell', 'steel', 'falls', 'anywhere',
            'team', 'vs', 'over', 'in', 'at', 'to', 'from', 'into',
        }

        # First, clean the text
        text = match_text

        # Remove parenthetical content like (c) for champion, (2:15) for time
        text = re.sub(r'\([^)]*\)', ' ', text)
        # Remove bracket content
        text = re.sub(r'\[[^\]]*\]', ' ', text)

        # Split by all common separators to get individual names
        # This includes: vs, vs., defeated, def., beat, &, and, comma
        parts = re.split(
            r'\s+vs\.?\s+|\s+def\.?\s+|\s+defeated\s+|\s+beat\s+'
            r'|\s+&\s+|\s+and\s+|\s*,\s*|\s+over\s+',
            text,
            flags=re.IGNORECASE
        )

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Skip if it's too short or too long
            words = part.split()
            if not (1 <= len(words) <= 5):
                continue

            # Skip if it's mostly stop words
            non_stop_words = [
                w for w in words
                if w.lower() not in stop_words and len(w) > 1
            ]
            if len(non_stop_words) < len(words) * 0.5:
                continue

            # Check if it looks like a name (starts with capital, reasonable length)
            # Allow "The Rock", "Stone Cold Steve Austin", etc.
            first_word = words[0]
            if not first_word[0].isupper():
                continue

            # Build the potential name
            name = ' '.join(words)

            # Validate the name
            if len(name) >= 3 and len(name) <= 50:  # Reasonable name length
                # Skip common non-wrestler terms that might slip through
                lower_name = name.lower()
                if lower_name in {'world', 'heavyweight', 'champion', 'title match'}:
                    continue
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

        Scrapes Wikipedia event categories and filters by promotion.
        """
        from ..models import Promotion, Event

        discovered = []

        # Find promotions with few events
        promotions_needing_events = Promotion.objects.annotate(
            event_count=Count('events')
        ).filter(
            event_count__lt=10
        ).order_by('event_count')[:5]

        # Get promotion names/abbreviations for matching
        promo_names = {
            p.name.lower(): p.name for p in promotions_needing_events
        }
        promo_abbrevs = {
            p.abbreviation.lower(): p.name
            for p in promotions_needing_events
            if p.abbreviation
        }

        try:
            # Scrape events from Wikipedia categories
            events = self.wikipedia_scraper.scrape_events(limit=limit * 3)

            for event_data in events:
                event_name = event_data.get('name', '')
                event_date = event_data.get('date', '')
                promo_name = event_data.get('promotion_name', '')

                # Try to match to one of our promotions needing events
                matched_promo = None
                if promo_name:
                    matched_promo = promo_names.get(promo_name.lower()) or promo_abbrevs.get(promo_name.lower())
                else:
                    # Check if event name contains promotion name/abbrev
                    event_lower = event_name.lower()
                    for abbrev, full_name in promo_abbrevs.items():
                        if abbrev in event_lower:
                            matched_promo = full_name
                            break

                if not matched_promo:
                    continue

                # Check if event already exists
                exists = Event.objects.filter(
                    name__iexact=event_name,
                    date=event_date
                ).exists() if event_date else Event.objects.filter(name__iexact=event_name).exists()

                if not exists:
                    event_data['promotion_name'] = matched_promo
                    discovered.append({
                        'name': event_name,
                        'data': event_data,
                        'source': 'wikipedia',
                    })

                    if len(discovered) >= limit:
                        break

        except Exception as e:
            logger.warning(f"Failed to discover events from Wikipedia: {e}")

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

        # Get wrestlers with about (bio) text
        wrestlers = Wrestler.objects.exclude(
            about=''
        ).exclude(
            about__isnull=True
        )[:200]

        potential_promos: Set[str] = set()

        for wrestler in wrestlers:
            if wrestler.about:
                # Look for promotion names in about text
                for promo in known_promotions:
                    if promo in wrestler.about and promo.lower() not in existing_promos_lower:
                        potential_promos.add(promo)

        # Scrape promotions from Wikipedia and check if any match
        try:
            wiki_promos = self.wikipedia_scraper.scrape_promotions(limit=50)
            promo_by_name = {p.get('name', '').lower(): p for p in wiki_promos}
            promo_by_abbrev = {
                p.get('abbreviation', '').lower(): p
                for p in wiki_promos
                if p.get('abbreviation')
            }

            for promo_name in list(potential_promos)[:limit]:
                promo_data = promo_by_name.get(promo_name.lower()) or promo_by_abbrev.get(promo_name.lower())
                if promo_data:
                    discovered.append({
                        'name': promo_name,
                        'data': promo_data,
                        'source': 'wikipedia',
                    })
                    logger.info(f"Discovered promotion from wrestler bio: {promo_name}")

        except Exception as e:
            logger.warning(f"Failed to verify promotions: {e}")

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

        # The Venue.save() method now handles unique slug generation
        venue, created = Venue.objects.get_or_create(
            name=name,
            defaults={
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
