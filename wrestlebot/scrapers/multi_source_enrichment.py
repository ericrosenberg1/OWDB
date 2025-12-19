"""
Multi-source data enrichment system for WrestlingDB.

This module aggregates wrestling data from multiple sources to create
the most complete and accurate encyclopedia possible:

- Wikipedia: Biographical info, career history
- Cagematch.net: Complete match database, ratings
- ProFightDB: Additional statistics and profiles
- Internet Wrestling Database (IWD): Historical data
- Wrestling Observer: Ratings and statistics

The system intelligently merges data from multiple sources, resolving
conflicts and creating comprehensive, rich profiles.
"""

import logging
import requests
from typing import Dict, List, Optional, Set
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class MultiSourceEnrichment:
    """
    Aggregates wrestling data from multiple sources.

    Philosophy: No single source has complete data. Wikipedia may miss
    recent matches, Cagematch has comprehensive match history, ProFightDB
    has additional stats. Combine them all for the ultimate database.
    """

    def __init__(self, api_client):
        self.api_client = api_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestlingDB-Bot/1.0 (+https://wrestlingdb.com)'
        })

        # Source priorities for different data types
        self.source_priority = {
            'birth_date': ['wikipedia', 'cagematch', 'profightdb'],
            'real_name': ['wikipedia', 'cagematch', 'profightdb'],
            'debut_year': ['cagematch', 'wikipedia', 'profightdb'],
            'hometown': ['wikipedia', 'profightdb', 'cagematch'],
            'height': ['cagematch', 'wikipedia', 'profightdb'],
            'weight': ['cagematch', 'wikipedia', 'profightdb'],
            'finishers': ['cagematch', 'wikipedia', 'profightdb'],
            'matches': ['cagematch'],  # Cagematch is the authority on matches
            'ratings': ['cagematch', 'observer'],
        }

    def enrich_wrestler(self, wrestler_name: str, existing_data: Optional[Dict] = None) -> Dict:
        """
        Enrich wrestler data by aggregating from all available sources.

        Args:
            wrestler_name: Name of the wrestler
            existing_data: Any existing data we already have

        Returns:
            Enriched wrestler data dictionary
        """
        logger.info(f"Enriching {wrestler_name} from multiple sources")

        # Start with existing data or empty dict
        enriched = existing_data.copy() if existing_data else {'name': wrestler_name}

        # Collect data from each source
        sources_data = {}

        try:
            # Wikipedia: Great for biographical info and career overview
            logger.info(f"  Fetching Wikipedia data for {wrestler_name}")
            wikipedia_data = self._get_wikipedia_data(wrestler_name)
            if wikipedia_data:
                sources_data['wikipedia'] = wikipedia_data
                logger.info(f"  ✓ Wikipedia: Found {len(wikipedia_data)} fields")

        except Exception as e:
            logger.warning(f"  Wikipedia fetch failed: {e}")

        try:
            # Cagematch: The gold standard for match data
            logger.info(f"  Fetching Cagematch data for {wrestler_name}")
            cagematch_data = self._get_cagematch_data(wrestler_name)
            if cagematch_data:
                sources_data['cagematch'] = cagematch_data
                logger.info(f"  ✓ Cagematch: Found {len(cagematch_data)} fields")

        except Exception as e:
            logger.warning(f"  Cagematch fetch failed: {e}")

        try:
            # ProFightDB: Additional stats and profiles
            logger.info(f"  Fetching ProFightDB data for {wrestler_name}")
            profightdb_data = self._get_profightdb_data(wrestler_name)
            if profightdb_data:
                sources_data['profightdb'] = profightdb_data
                logger.info(f"  ✓ ProFightDB: Found {len(profightdb_data)} fields")

        except Exception as e:
            logger.warning(f"  ProFightDB fetch failed: {e}")

        # Merge data intelligently based on priorities
        enriched = self._merge_sources(enriched, sources_data)

        # Store source URLs for attribution
        if 'wikipedia' in sources_data and sources_data['wikipedia'].get('url'):
            enriched['wikipedia_url'] = sources_data['wikipedia']['url']
        if 'cagematch' in sources_data and sources_data['cagematch'].get('url'):
            enriched['cagematch_url'] = sources_data['cagematch']['url']
        if 'profightdb' in sources_data and sources_data['profightdb'].get('url'):
            enriched['profightdb_url'] = sources_data['profightdb']['url']

        logger.info(f"Enrichment complete: {len(enriched)} total fields")
        return enriched

    def _merge_sources(self, base: Dict, sources: Dict[str, Dict]) -> Dict:
        """
        Intelligently merge data from multiple sources.

        Strategy:
        1. Use source priorities for each field type
        2. Prefer more complete/detailed data
        3. Combine lists (e.g., finishers from multiple sources)
        4. Keep track of what came from where (for transparency)
        """
        merged = base.copy()

        # For each potential field, check sources in priority order
        all_fields = set()
        for source_data in sources.values():
            all_fields.update(source_data.keys())

        for field in all_fields:
            if field in ['url', 'source']:  # Skip metadata fields
                continue

            # Get priority list for this field, or default
            priorities = self.source_priority.get(field, ['wikipedia', 'cagematch', 'profightdb'])

            # Find first source with this field
            for source_name in priorities:
                if source_name in sources:
                    source_data = sources[source_name]
                    if field in source_data and source_data[field]:
                        value = source_data[field]

                        # Special handling for list fields (combine from all sources)
                        if field in ['finishers', 'signature_moves', 'aliases', 'trained_by']:
                            existing = merged.get(field, '')
                            if existing:
                                # Combine and deduplicate
                                existing_list = [x.strip() for x in existing.split(',')]
                                new_list = [x.strip() for x in value.split(',') if x.strip()]
                                combined = list(set(existing_list + new_list))
                                merged[field] = ', '.join(combined)
                            else:
                                merged[field] = value
                        else:
                            # For singular fields, only use if we don't have it yet
                            if not merged.get(field):
                                merged[field] = value

                        break  # Found it, move to next field

        return merged

    def _get_wikipedia_data(self, wrestler_name: str) -> Optional[Dict]:
        """Fetch wrestler data from Wikipedia."""
        # This is a placeholder - reuse existing Wikipedia scraper
        from .page_enrichment import PageEnrichmentDiscovery

        enrichment = PageEnrichmentDiscovery(self.api_client)
        data = enrichment.enrich_wrestler_from_wikipedia(wrestler_name)

        if data:
            return {
                'real_name': data.get('real_name'),
                'birth_date': data.get('birth_date'),
                'debut_year': data.get('debut_year'),
                'retirement_year': data.get('retirement_year'),
                'hometown': data.get('hometown'),
                'nationality': data.get('nationality'),
                'height': data.get('height'),
                'weight': data.get('weight'),
                'finishers': data.get('finishers'),
                'about': data.get('about'),
                'url': data.get('wikipedia_url'),
                'source': 'wikipedia'
            }

        return None

    def _get_cagematch_data(self, wrestler_name: str) -> Optional[Dict]:
        """
        Fetch wrestler data from Cagematch.net.

        Cagematch is the gold standard for match history and ratings.
        """
        # TODO: Implement Cagematch scraper
        # For now, return None to avoid errors
        logger.info("  Cagematch scraper not yet implemented")
        return None

    def _get_profightdb_data(self, wrestler_name: str) -> Optional[Dict]:
        """
        Fetch wrestler data from ProFightDB.

        ProFightDB has good stats and additional profile information.
        """
        # TODO: Implement ProFightDB scraper
        # For now, return None to avoid errors
        logger.info("  ProFightDB scraper not yet implemented")
        return None

    def enrich_promotion(self, promotion_name: str, existing_data: Optional[Dict] = None) -> Dict:
        """Enrich promotion data from multiple sources."""
        logger.info(f"Enriching promotion: {promotion_name}")

        enriched = existing_data.copy() if existing_data else {'name': promotion_name}

        # Fetch from sources (similar to wrestler enrichment)
        # TODO: Implement multi-source promotion enrichment

        return enriched

    def enrich_stable(self, stable_name: str, existing_data: Optional[Dict] = None) -> Dict:
        """
        Enrich stable/faction data from multiple sources.

        Stables are particularly interesting because different sources may list
        different members at different times.
        """
        logger.info(f"Enriching stable: {stable_name}")

        enriched = existing_data.copy() if existing_data else {'name': stable_name}

        # Fetch from sources
        # TODO: Implement stable enrichment

        return enriched

    def get_match_history(self, wrestler_name: str, limit: int = 100) -> List[Dict]:
        """
        Get complete match history for a wrestler.

        This is where Cagematch really shines - they have the most
        comprehensive match database.
        """
        logger.info(f"Fetching match history for {wrestler_name}")

        matches = []

        # TODO: Implement Cagematch match history scraper
        # Cagematch has detailed match cards, dates, locations, opponents, results

        return matches
