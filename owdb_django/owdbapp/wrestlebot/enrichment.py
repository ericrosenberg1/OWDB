"""
WrestleBot 2.0 Enrichment Engine

Improves existing database entries by adding missing data from external sources.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Count, Q
from django.utils import timezone

from .scoring import CompletenessScorer, ScoreBreakdown

logger = logging.getLogger(__name__)


class EntityEnrichment:
    """
    Enriches existing entries with more data from external sources.

    Enrichment strategies:
    1. Fill missing fields from Wikipedia
    2. Add images from Wikimedia Commons
    3. Cross-reference with Cagematch for additional data
    4. Use AI (Claude) for bio generation and data validation
    """

    def __init__(self):
        from . import ScraperProvider
        self.scorer = CompletenessScorer()
        self._scrapers = ScraperProvider()
        self._ai_enhancer = None

    @property
    def wikipedia_scraper(self):
        """Get Wikipedia scraper from shared provider."""
        return self._scrapers.wikipedia_scraper

    @property
    def wikimedia_client(self):
        """Get Wikimedia Commons client from shared provider."""
        return self._scrapers.wikimedia_client

    @property
    def cagematch_scraper(self):
        """Get Cagematch scraper from shared provider."""
        return self._scrapers.cagematch_scraper

    @property
    def ai_enhancer(self):
        """Lazy load AI enhancer (if available)."""
        if self._ai_enhancer is None:
            try:
                from .ai_enhancer import AIEnhancer
                self._ai_enhancer = AIEnhancer()
            except Exception:
                self._ai_enhancer = None
        return self._ai_enhancer

    def get_entities_needing_enrichment(
        self,
        entity_type: str,
        max_score: float = 50.0,
        limit: int = 20
    ) -> List[Tuple[Any, ScoreBreakdown]]:
        """
        Get entities with low completeness scores.

        Args:
            entity_type: Type of entity (wrestler, promotion, event, etc.)
            max_score: Maximum score to include (lower = more incomplete)
            limit: Maximum entities to return

        Returns:
            List of (entity, score_breakdown) tuples sorted by score
        """
        from ..models import Wrestler, Promotion, Event, Title, Venue

        model_map = {
            'wrestler': Wrestler,
            'promotion': Promotion,
            'event': Event,
            'title': Title,
            'venue': Venue,
        }

        model_class = model_map.get(entity_type)
        if not model_class:
            logger.warning(f"Unknown entity type: {entity_type}")
            return []

        return self.scorer.get_low_score_entities(
            model_class,
            max_score=max_score,
            limit=limit
        )

    def enrich_wrestler(self, wrestler) -> Dict[str, Any]:
        """
        Enrich a wrestler with missing data.

        Returns dict of fields that were updated.
        """
        from .models import WrestleBotActivity

        start_time = time.time()
        updated_fields = {}
        sources_used = []

        # Get current score to see what's missing
        breakdown = self.scorer.score_wrestler(wrestler)
        missing = breakdown.missing_fields

        logger.info(f"Enriching wrestler {wrestler.name} (score: {breakdown.percentage}%, missing: {missing})")

        # Try Wikipedia for missing text fields
        if any(f in missing for f in ['real_name', 'hometown', 'nationality', 'about', 'debut_year', 'finishers']):
            try:
                wiki_data = self.wikipedia_scraper.scrape_wrestler_by_name(wrestler.name)
                if wiki_data:
                    sources_used.append('wikipedia')

                    if 'real_name' in missing and wiki_data.get('real_name'):
                        wrestler.real_name = wiki_data['real_name'][:255]
                        updated_fields['real_name'] = wiki_data['real_name']

                    if 'hometown' in missing and wiki_data.get('hometown'):
                        wrestler.hometown = wiki_data['hometown'][:255]
                        updated_fields['hometown'] = wiki_data['hometown']

                    if 'nationality' in missing and wiki_data.get('nationality'):
                        wrestler.nationality = wiki_data['nationality'][:255]
                        updated_fields['nationality'] = wiki_data['nationality']

                    if 'debut_year' in missing and wiki_data.get('debut_year'):
                        wrestler.debut_year = wiki_data['debut_year']
                        updated_fields['debut_year'] = wiki_data['debut_year']

                    if 'finishers' in missing and wiki_data.get('finishers'):
                        wrestler.finishers = wiki_data['finishers'][:1000]
                        updated_fields['finishers'] = wiki_data['finishers']

            except Exception as e:
                logger.warning(f"Wikipedia enrichment failed for {wrestler.name}: {e}")

        # Try Wikimedia Commons for image
        if 'image_url' in missing:
            try:
                image_data = self.wikimedia_client.find_wrestler_image(
                    name=wrestler.name,
                    real_name=wrestler.real_name
                )
                if image_data and image_data.get('url'):
                    from ..services import get_image_cache_service
                    cache_service = get_image_cache_service()

                    if cache_service.cache_and_update_entity(wrestler, image_data, archive_old=False):
                        sources_used.append('wikimedia_commons')
                        updated_fields['image_url'] = image_data['url']

            except Exception as e:
                logger.warning(f"Image fetch failed for {wrestler.name}: {e}")

        # Save if any updates were made
        if updated_fields:
            wrestler.save()
            duration_ms = int((time.time() - start_time) * 1000)

            # Log the activity
            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='wrestler',
                entity_id=wrestler.id,
                entity_name=wrestler.name,
                source=', '.join(sources_used),
                details={
                    'updated_fields': list(updated_fields.keys()),
                    'previous_score': breakdown.percentage,
                },
                duration_ms=duration_ms,
            )

            logger.info(f"Enriched wrestler {wrestler.name}: {list(updated_fields.keys())}")

        return updated_fields

    def enrich_promotion(self, promotion) -> Dict[str, Any]:
        """Enrich a promotion with missing data."""
        from .models import WrestleBotActivity

        start_time = time.time()
        updated_fields = {}
        sources_used = []

        breakdown = self.scorer.score_promotion(promotion)
        missing = breakdown.missing_fields

        logger.info(f"Enriching promotion {promotion.name} (score: {breakdown.percentage}%, missing: {missing})")

        # Try Wikipedia using parse_promotion_page
        if any(f in missing for f in ['about', 'founded_year', 'abbreviation', 'headquarters', 'website']):
            try:
                # Use parse_promotion_page with the promotion name as the Wikipedia title
                wiki_data = self.wikipedia_scraper.parse_promotion_page(promotion.name)
                if wiki_data:
                    sources_used.append('wikipedia')

                    if 'founded_year' in missing and wiki_data.get('founded_year'):
                        promotion.founded_year = wiki_data['founded_year']
                        updated_fields['founded_year'] = wiki_data['founded_year']

                    if 'abbreviation' in missing and wiki_data.get('abbreviation'):
                        promotion.abbreviation = wiki_data['abbreviation'][:50]
                        updated_fields['abbreviation'] = wiki_data['abbreviation']

                    if 'website' in missing and wiki_data.get('website'):
                        promotion.website = wiki_data['website'][:500]
                        updated_fields['website'] = wiki_data['website']

            except Exception as e:
                logger.warning(f"Wikipedia enrichment failed for {promotion.name}: {e}")

        # Try Wikimedia Commons for logo
        if 'image_url' in missing:
            try:
                image_data = self.wikimedia_client.find_promotion_image(
                    name=promotion.name,
                    abbreviation=promotion.abbreviation
                )
                if image_data and image_data.get('url'):
                    from ..services import get_image_cache_service
                    cache_service = get_image_cache_service()

                    if cache_service.cache_and_update_entity(promotion, image_data, archive_old=False):
                        sources_used.append('wikimedia_commons')
                        updated_fields['image_url'] = image_data['url']

            except Exception as e:
                logger.warning(f"Image fetch failed for {promotion.name}: {e}")

        if updated_fields:
            promotion.save()
            duration_ms = int((time.time() - start_time) * 1000)

            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='promotion',
                entity_id=promotion.id,
                entity_name=promotion.name,
                source=', '.join(sources_used),
                details={
                    'updated_fields': list(updated_fields.keys()),
                    'previous_score': breakdown.percentage,
                },
                duration_ms=duration_ms,
            )

            logger.info(f"Enriched promotion {promotion.name}: {list(updated_fields.keys())}")

        return updated_fields

    def enrich_event(self, event) -> Dict[str, Any]:
        """Enrich an event with missing data."""
        from .models import WrestleBotActivity

        start_time = time.time()
        updated_fields = {}
        sources_used = []

        breakdown = self.scorer.score_event(event)
        missing = breakdown.missing_fields

        logger.info(f"Enriching event {event.name} (score: {breakdown.percentage}%, missing: {missing})")

        # Try Wikipedia for event details using parse_event_page
        if any(f in missing for f in ['venue', 'attendance', 'about']):
            try:
                wiki_data = self.wikipedia_scraper.parse_event_page(event.name)
                if wiki_data:
                    sources_used.append('wikipedia')

                    if 'attendance' in missing and wiki_data.get('attendance'):
                        event.attendance = wiki_data['attendance']
                        updated_fields['attendance'] = wiki_data['attendance']

                    # Handle venue
                    if 'venue' in missing and wiki_data.get('venue_name'):
                        from ..models import Venue
                        from django.utils.text import slugify

                        venue, _ = Venue.objects.get_or_create(
                            name=wiki_data['venue_name'],
                            defaults={
                                'slug': slugify(wiki_data['venue_name']),
                                'location': wiki_data.get('venue_location', ''),
                            }
                        )
                        event.venue = venue
                        updated_fields['venue'] = wiki_data['venue_name']

            except Exception as e:
                logger.warning(f"Wikipedia enrichment failed for {event.name}: {e}")

        # Try Wikimedia Commons for event poster/image
        if 'image_url' in missing:
            try:
                image_data = self.wikimedia_client.find_event_image(
                    name=event.name,
                    promotion=event.promotion.abbreviation if event.promotion else None,
                    year=event.date.year if event.date else None
                )
                if image_data and image_data.get('url'):
                    from ..services import get_image_cache_service
                    cache_service = get_image_cache_service()

                    if cache_service.cache_and_update_entity(event, image_data, archive_old=False):
                        sources_used.append('wikimedia_commons')
                        updated_fields['image_url'] = image_data['url']

            except Exception as e:
                logger.warning(f"Image fetch failed for {event.name}: {e}")

        if updated_fields:
            event.save()
            duration_ms = int((time.time() - start_time) * 1000)

            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='event',
                entity_id=event.id,
                entity_name=event.name,
                source=', '.join(sources_used),
                details={
                    'updated_fields': list(updated_fields.keys()),
                    'previous_score': breakdown.percentage,
                },
                duration_ms=duration_ms,
            )

            logger.info(f"Enriched event {event.name}: {list(updated_fields.keys())}")

        return updated_fields

    def enrich_venue(self, venue) -> Dict[str, Any]:
        """Enrich a venue with missing data."""
        from .models import WrestleBotActivity

        start_time = time.time()
        updated_fields = {}
        sources_used = []

        breakdown = self.scorer.score_venue(venue)
        missing = breakdown.missing_fields

        logger.info(f"Enriching venue {venue.name} (score: {breakdown.percentage}%, missing: {missing})")

        # Try Wikipedia for venue details using get_infobox_data
        if any(f in missing for f in ['location', 'capacity', 'about']):
            try:
                wiki_data = self.wikipedia_scraper.get_infobox_data(venue.name)
                if wiki_data:
                    sources_used.append('wikipedia')

                    if 'location' in missing:
                        # Try various location field names from Wikipedia infoboxes
                        location = (wiki_data.get('location') or wiki_data.get('city') or
                                   wiki_data.get('address'))
                        if location:
                            venue.location = location[:255]
                            updated_fields['location'] = location

                    if 'capacity' in missing:
                        capacity_str = wiki_data.get('capacity') or wiki_data.get('seating_capacity')
                        if capacity_str:
                            # Try to extract number from capacity string
                            import re
                            numbers = re.findall(r'[\d,]+', capacity_str.replace(',', ''))
                            if numbers:
                                try:
                                    venue.capacity = int(numbers[0])
                                    updated_fields['capacity'] = venue.capacity
                                except ValueError:
                                    pass

            except Exception as e:
                logger.warning(f"Wikipedia enrichment failed for {venue.name}: {e}")

        # Try Wikimedia Commons for venue image
        if 'image_url' in missing:
            try:
                image_data = self.wikimedia_client.find_venue_image(
                    name=venue.name,
                    location=venue.location
                )
                if image_data and image_data.get('url'):
                    from ..services import get_image_cache_service
                    cache_service = get_image_cache_service()

                    if cache_service.cache_and_update_entity(venue, image_data, archive_old=False):
                        sources_used.append('wikimedia_commons')
                        updated_fields['image_url'] = image_data['url']

            except Exception as e:
                logger.warning(f"Image fetch failed for {venue.name}: {e}")

        if updated_fields:
            venue.save()
            duration_ms = int((time.time() - start_time) * 1000)

            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='venue',
                entity_id=venue.id,
                entity_name=venue.name,
                source=', '.join(sources_used),
                details={
                    'updated_fields': list(updated_fields.keys()),
                    'previous_score': breakdown.percentage,
                },
                duration_ms=duration_ms,
            )

            logger.info(f"Enriched venue {venue.name}: {list(updated_fields.keys())}")

        return updated_fields

    def run_enrichment_cycle(
        self,
        entity_types: List[str] = None,
        max_score: float = 50.0,
        limit: int = 10,
        pause_ms: int = 500
    ) -> Dict[str, int]:
        """
        Run a full enrichment cycle for specified entity types.

        Args:
            entity_types: List of entity types to enrich (default: all)
            max_score: Maximum score to include for enrichment
            limit: Maximum entities to enrich per type
            pause_ms: Milliseconds to pause between operations

        Returns:
            Dict mapping entity type to count of enriched entities
        """
        if entity_types is None:
            entity_types = ['wrestler', 'promotion', 'event', 'venue']

        results = {}

        for entity_type in entity_types:
            enriched_count = 0

            try:
                entities = self.get_entities_needing_enrichment(
                    entity_type=entity_type,
                    max_score=max_score,
                    limit=limit
                )

                for entity, breakdown in entities:
                    try:
                        if entity_type == 'wrestler':
                            updated = self.enrich_wrestler(entity)
                        elif entity_type == 'promotion':
                            updated = self.enrich_promotion(entity)
                        elif entity_type == 'event':
                            updated = self.enrich_event(entity)
                        elif entity_type == 'venue':
                            updated = self.enrich_venue(entity)
                        else:
                            updated = {}

                        if updated:
                            enriched_count += 1

                        # Pause between operations to be gentle on APIs
                        if pause_ms > 0:
                            time.sleep(pause_ms / 1000)

                    except Exception as e:
                        logger.error(f"Failed to enrich {entity_type}: {e}")

                logger.info(f"Enrichment cycle for {entity_type}: enriched {enriched_count} entities")

            except Exception as e:
                logger.error(f"Enrichment cycle failed for {entity_type}: {e}")

            results[entity_type] = enriched_count

        return results

    def enrich_with_ai(self, entity, entity_type: str) -> Dict[str, Any]:
        """
        Use AI (Claude) to enhance entity data.

        Only used when AI is enabled and for high-value operations like
        generating bios or resolving data inconsistencies.
        """
        from .models import WrestleBotActivity, WrestleBotConfig

        if not WrestleBotConfig.is_ai_enabled():
            logger.debug("AI enhancement skipped: AI is disabled")
            return {}

        if self.ai_enhancer is None:
            logger.warning("AI enhancement skipped: AI enhancer not available")
            return {}

        start_time = time.time()
        updated_fields = {}

        try:
            if entity_type == 'wrestler':
                # Generate about (bio) if missing
                breakdown = self.scorer.score_wrestler(entity)
                if 'about' in breakdown.missing_fields:
                    bio = self.ai_enhancer.generate_wrestler_bio(entity)
                    if bio:
                        entity.about = bio[:5000]
                        entity.save(update_fields=['about', 'updated_at'])
                        updated_fields['about'] = bio[:100] + '...'

            duration_ms = int((time.time() - start_time) * 1000)

            if updated_fields:
                WrestleBotActivity.log_activity(
                    action_type='enrich',
                    entity_type=entity_type,
                    entity_id=entity.id,
                    entity_name=str(entity),
                    source='claude_api',
                    details={'updated_fields': list(updated_fields.keys())},
                    ai_assisted=True,
                    duration_ms=duration_ms,
                )

        except Exception as e:
            logger.error(f"AI enhancement failed: {e}")
            WrestleBotActivity.log_activity(
                action_type='error',
                entity_type=entity_type,
                entity_id=entity.id,
                entity_name=str(entity),
                source='claude_api',
                success=False,
                error_message=str(e),
                ai_assisted=True,
            )

        return updated_fields

    def verify_wrestler_data(self, wrestler) -> Dict[str, Any]:
        """
        Cross-verify wrestler data against multiple sources.

        Checks for consistency across Wikipedia and Cagematch.
        Returns dict with verification results and any corrections.
        """
        from .models import WrestleBotActivity

        results = {
            'verified': True,
            'sources_checked': [],
            'discrepancies': [],
            'corrections': {},
        }

        # Get data from Wikipedia
        wiki_data = None
        try:
            wiki_data = self.wikipedia_scraper.scrape_wrestler_by_name(wrestler.name)
            if wiki_data:
                results['sources_checked'].append('wikipedia')
        except Exception as e:
            logger.debug(f"Wikipedia verification failed for {wrestler.name}: {e}")

        # Get data from Cagematch
        cm_data = None
        try:
            cm_data = self.cagematch_scraper.scrape_wrestler_by_name(wrestler.name)
            if cm_data:
                results['sources_checked'].append('cagematch')
        except Exception as e:
            logger.debug(f"Cagematch verification failed for {wrestler.name}: {e}")

        if not wiki_data and not cm_data:
            results['verified'] = False
            results['discrepancies'].append('No data found in external sources')
            return results

        # Cross-verify debut year
        if wrestler.debut_year:
            wiki_debut = wiki_data.get('debut_year') if wiki_data else None
            cm_debut = cm_data.get('debut_year') if cm_data else None

            if wiki_debut and cm_debut and wiki_debut != cm_debut:
                results['discrepancies'].append(
                    f"Debut year mismatch: DB={wrestler.debut_year}, "
                    f"Wikipedia={wiki_debut}, Cagematch={cm_debut}"
                )
            elif wiki_debut and wrestler.debut_year != wiki_debut:
                results['discrepancies'].append(
                    f"Debut year differs from Wikipedia: DB={wrestler.debut_year}, Wiki={wiki_debut}"
                )

        # Cross-verify real name
        if wrestler.real_name:
            wiki_real = wiki_data.get('real_name') if wiki_data else None
            cm_real = cm_data.get('real_name') if cm_data else None

            # Check for significant differences
            if wiki_real and cm_real:
                from ..scrapers.coordinator import DataValidator
                if DataValidator.similarity(wiki_real, cm_real) < 0.8:
                    results['discrepancies'].append(
                        f"Real name mismatch: Wikipedia='{wiki_real}', Cagematch='{cm_real}'"
                    )

        # If we have sources but no current data, suggest corrections
        if not wrestler.debut_year:
            wiki_debut = wiki_data.get('debut_year') if wiki_data else None
            cm_debut = cm_data.get('debut_year') if cm_data else None
            if wiki_debut and cm_debut and wiki_debut == cm_debut:
                results['corrections']['debut_year'] = wiki_debut
            elif wiki_debut:
                results['corrections']['debut_year'] = wiki_debut
            elif cm_debut:
                results['corrections']['debut_year'] = cm_debut

        if not wrestler.real_name:
            wiki_real = wiki_data.get('real_name') if wiki_data else None
            if wiki_real:
                results['corrections']['real_name'] = wiki_real

        if not wrestler.hometown:
            wiki_hometown = wiki_data.get('hometown') if wiki_data else None
            cm_hometown = cm_data.get('hometown') if cm_data else None
            if wiki_hometown:
                results['corrections']['hometown'] = wiki_hometown
            elif cm_hometown:
                results['corrections']['hometown'] = cm_hometown

        # Log verification activity
        if results['discrepancies'] or results['corrections']:
            WrestleBotActivity.log_activity(
                action_type='verify',
                entity_type='wrestler',
                entity_id=wrestler.id,
                entity_name=wrestler.name,
                source=', '.join(results['sources_checked']),
                details={
                    'discrepancies': results['discrepancies'],
                    'suggested_corrections': results['corrections'],
                },
            )

        return results

    def apply_verified_corrections(
        self,
        wrestler,
        corrections: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply corrections that have been verified across multiple sources.

        Only updates fields that are currently empty and have verified data.
        """
        from .models import WrestleBotActivity

        updated_fields = {}

        for field, value in corrections.items():
            current_value = getattr(wrestler, field, None)
            # Only update if current value is empty
            if not current_value and value:
                setattr(wrestler, field, value)
                updated_fields[field] = value

        if updated_fields:
            wrestler.save()
            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='wrestler',
                entity_id=wrestler.id,
                entity_name=wrestler.name,
                source='cross_verification',
                details={
                    'updated_fields': list(updated_fields.keys()),
                    'verified': True,
                },
            )
            logger.info(f"Applied verified corrections to {wrestler.name}: {list(updated_fields.keys())}")

        return updated_fields

    def run_verification_cycle(
        self,
        entity_type: str = 'wrestler',
        limit: int = 10,
        apply_corrections: bool = True
    ) -> Dict[str, int]:
        """
        Run a verification cycle to cross-check and correct data.

        Args:
            entity_type: Type of entity to verify (currently only 'wrestler')
            limit: Maximum entities to verify
            apply_corrections: Whether to auto-apply verified corrections

        Returns:
            Dict with counts of verified, discrepancies found, and corrections applied
        """
        from ..models import Wrestler

        results = {
            'verified': 0,
            'discrepancies': 0,
            'corrections_applied': 0,
            'corrections_available': 0,
        }

        if entity_type != 'wrestler':
            logger.warning(f"Verification not yet implemented for {entity_type}")
            return results

        # Get wrestlers that need verification (incomplete data)
        wrestlers = Wrestler.objects.filter(
            Q(debut_year__isnull=True) |
            Q(real_name__isnull=True) | Q(real_name='') |
            Q(hometown__isnull=True) | Q(hometown='')
        ).order_by('?')[:limit]

        for wrestler in wrestlers:
            try:
                verification = self.verify_wrestler_data(wrestler)

                if verification['verified']:
                    results['verified'] += 1
                if verification['discrepancies']:
                    results['discrepancies'] += len(verification['discrepancies'])
                if verification['corrections']:
                    results['corrections_available'] += len(verification['corrections'])

                    if apply_corrections:
                        applied = self.apply_verified_corrections(
                            wrestler,
                            verification['corrections']
                        )
                        results['corrections_applied'] += len(applied)

                # Small pause to be gentle on external APIs
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Verification failed for {wrestler.name}: {e}")

        logger.info(f"Verification cycle complete: {results}")
        return results
