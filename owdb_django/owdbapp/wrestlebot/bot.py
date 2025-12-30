"""
WrestleBot 2.0 Main Orchestrator

The main WrestleBot class that coordinates discovery, enrichment,
and image fetching operations.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)


class WrestleBot:
    """
    Main orchestrator for WrestleBot 2.0.

    Coordinates all bot operations:
    - Discovery: Finding new entities to add
    - Enrichment: Improving existing entries
    - Image fetching: Adding CC-licensed images
    - AI enhancement: Optional Claude API integration

    All operations are designed to be:
    - Low resource: Sleeps between operations
    - Safe: Never deletes data
    - Traceable: All actions logged
    - Configurable: Settings from database
    """

    def __init__(self):
        self._discovery = None
        self._enrichment = None
        self._ai_enhancer = None
        self._config = None

    @property
    def discovery(self):
        """Lazy load discovery engine."""
        if self._discovery is None:
            from .discovery import EntityDiscovery
            self._discovery = EntityDiscovery()
        return self._discovery

    @property
    def enrichment(self):
        """Lazy load enrichment engine."""
        if self._enrichment is None:
            from .enrichment import EntityEnrichment
            self._enrichment = EntityEnrichment()
        return self._enrichment

    @property
    def ai_enhancer(self):
        """Lazy load AI enhancer."""
        if self._ai_enhancer is None:
            try:
                from .ai_enhancer import AIEnhancer
                self._ai_enhancer = AIEnhancer()
            except Exception:
                self._ai_enhancer = None
        return self._ai_enhancer

    @property
    def config(self) -> Dict[str, Any]:
        """Get current configuration."""
        if self._config is None:
            from .models import WrestleBotConfig
            self._config = WrestleBotConfig.get_all()
        return self._config

    def is_enabled(self) -> bool:
        """Check if WrestleBot is enabled."""
        from .models import WrestleBotConfig
        return WrestleBotConfig.is_enabled()

    def reload_config(self):
        """Reload configuration from database."""
        self._config = None

    def run_master_cycle(self) -> Dict[str, Any]:
        """
        Run the master orchestration cycle.

        This is the main entry point called by Celery Beat.
        It decides what work needs to be done and queues it.
        """
        from .models import WrestleBotActivity, WrestleBotStats

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping cycle")
            return {'status': 'disabled'}

        start_time = time.time()
        results = {
            'status': 'completed',
            'operations': [],
        }

        try:
            # Get today's stats
            stats = WrestleBotStats.get_or_create_today()

            # Check what work needs to be done
            work_needed = self._analyze_work_needed()

            # Log what we found
            logger.info(f"WrestleBot master cycle: {work_needed}")

            results['work_analysis'] = work_needed

        except Exception as e:
            logger.error(f"WrestleBot master cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def _analyze_work_needed(self) -> Dict[str, Any]:
        """
        Analyze database to determine what work is needed.

        This is a lightweight check that runs frequently.
        """
        from ..models import Wrestler, Promotion, Event, Venue

        # Count entities needing work
        entities_without_images = {
            'wrestlers': Wrestler.objects.filter(image_url__isnull=True).count(),
            'promotions': Promotion.objects.filter(image_url__isnull=True).count(),
            'events': Event.objects.filter(image_url__isnull=True).count(),
            'venues': Venue.objects.filter(image_url__isnull=True).count(),
        }

        # Quick sample to estimate low-score entities
        from .scoring import CompletenessScorer
        scorer = CompletenessScorer()

        sample_wrestlers = list(Wrestler.objects.order_by('?')[:20])
        low_score_estimate = sum(
            1 for w in sample_wrestlers
            if scorer.score_wrestler(w).percentage < 50
        )

        return {
            'entities_without_images': entities_without_images,
            'estimated_low_score_wrestlers': low_score_estimate * (Wrestler.objects.count() // 20),
            'total_wrestlers': Wrestler.objects.count(),
            'total_promotions': Promotion.objects.count(),
            'total_events': Event.objects.count(),
        }

    def run_discovery_cycle(self, batch_size: int = None) -> Dict[str, Any]:
        """
        Run a discovery cycle to find and add new entities.

        Args:
            batch_size: Number of entities to discover (default from config)

        Returns:
            Dict with discovery results
        """
        from .models import WrestleBotConfig, WrestleBotStats

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping discovery")
            return {'status': 'disabled'}

        if batch_size is None:
            batch_size = WrestleBotConfig.get('discovery_batch_size', 5)

        start_time = time.time()
        pause_ms = WrestleBotConfig.get('pause_between_operations_ms', 500)
        priority_entities = WrestleBotConfig.get('priority_entities', ['wrestler', 'event', 'promotion'])

        results = {
            'status': 'completed',
            'discovered': {},
            'imported': {},
        }

        try:
            # Run discovery for priority entity types
            discoveries = self.discovery.run_discovery_cycle(
                entity_types=priority_entities,
                limit=batch_size
            )

            results['discovered'] = {
                k: len(v) for k, v in discoveries.items()
            }

            # Import discovered entities
            if any(discoveries.values()):
                imported = self.discovery.import_discovered_entities(discoveries)
                results['imported'] = imported

                # Update daily stats
                stats = WrestleBotStats.get_or_create_today()
                total_imported = sum(imported.values())
                stats.increment('discoveries', total_imported)

            logger.info(f"Discovery cycle complete: {results['imported']}")

        except Exception as e:
            logger.error(f"Discovery cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def run_enrichment_cycle(self, batch_size: int = None) -> Dict[str, Any]:
        """
        Run an enrichment cycle to improve existing entities.

        Args:
            batch_size: Number of entities to enrich (default from config)

        Returns:
            Dict with enrichment results
        """
        from .models import WrestleBotConfig, WrestleBotStats

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping enrichment")
            return {'status': 'disabled'}

        if batch_size is None:
            batch_size = WrestleBotConfig.get('enrichment_batch_size', 10)

        start_time = time.time()
        min_score = WrestleBotConfig.get('min_completeness_score', 40)
        pause_ms = WrestleBotConfig.get('pause_between_operations_ms', 500)
        priority_entities = WrestleBotConfig.get('priority_entities', ['wrestler', 'event', 'promotion'])

        results = {
            'status': 'completed',
            'enriched': {},
        }

        try:
            # Run enrichment for priority entity types
            enriched = self.enrichment.run_enrichment_cycle(
                entity_types=priority_entities,
                max_score=min_score,
                limit=batch_size,
                pause_ms=pause_ms
            )

            results['enriched'] = enriched

            # Update daily stats
            stats = WrestleBotStats.get_or_create_today()
            total_enriched = sum(enriched.values())
            stats.increment('enrichments', total_enriched)

            logger.info(f"Enrichment cycle complete: {enriched}")

        except Exception as e:
            logger.error(f"Enrichment cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def run_image_cycle(self, batch_size: int = None) -> Dict[str, Any]:
        """
        Run an image fetching cycle for entities without images.

        Args:
            batch_size: Number of images to fetch (default from config)

        Returns:
            Dict with image fetching results
        """
        from .models import WrestleBotConfig, WrestleBotStats, WrestleBotActivity
        from ..models import Wrestler, Promotion, Event, Venue
        from ..scrapers.wikimedia_commons import WikimediaCommonsClient
        from ..services import get_image_cache_service

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping image cycle")
            return {'status': 'disabled'}

        if batch_size is None:
            batch_size = WrestleBotConfig.get('image_batch_size', 10)

        start_time = time.time()
        pause_ms = WrestleBotConfig.get('pause_between_operations_ms', 500)

        results = {
            'status': 'completed',
            'images_added': {},
        }

        wikimedia = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        try:
            # Distribute batch across entity types
            per_type = max(1, batch_size // 4)

            for model_class, entity_type, find_method in [
                (Wrestler, 'wrestler', wikimedia.find_wrestler_image),
                (Promotion, 'promotion', wikimedia.find_promotion_image),
                (Event, 'event', wikimedia.find_event_image),
                (Venue, 'venue', wikimedia.find_venue_image),
            ]:
                count = 0
                entities = model_class.objects.filter(image_url__isnull=True)[:per_type]

                for entity in entities:
                    try:
                        # Get appropriate search parameters
                        if entity_type == 'wrestler':
                            image_data = find_method(
                                name=entity.name,
                                real_name=getattr(entity, 'real_name', None)
                            )
                        elif entity_type == 'promotion':
                            image_data = find_method(
                                name=entity.name,
                                abbreviation=getattr(entity, 'abbreviation', None)
                            )
                        elif entity_type == 'event':
                            image_data = find_method(
                                name=entity.name,
                                promotion=entity.promotion.abbreviation if entity.promotion else None,
                                year=entity.date.year if entity.date else None
                            )
                        elif entity_type == 'venue':
                            image_data = find_method(
                                name=entity.name,
                                location=getattr(entity, 'location', None)
                            )
                        else:
                            image_data = None

                        if image_data and image_data.get('url'):
                            if cache_service.cache_and_update_entity(entity, image_data, archive_old=False):
                                count += 1

                                # Log activity
                                WrestleBotActivity.log_activity(
                                    action_type='image',
                                    entity_type=entity_type,
                                    entity_id=entity.id,
                                    entity_name=str(entity),
                                    source='wikimedia_commons',
                                    details={'image_url': image_data['url']},
                                )

                        # Pause between operations
                        if pause_ms > 0:
                            time.sleep(pause_ms / 1000)

                    except Exception as e:
                        logger.warning(f"Failed to fetch image for {entity_type} {entity}: {e}")

                results['images_added'][entity_type] = count

            # Update daily stats
            stats = WrestleBotStats.get_or_create_today()
            total_images = sum(results['images_added'].values())
            stats.increment('images_added', total_images)

            logger.info(f"Image cycle complete: {results['images_added']}")

        except Exception as e:
            logger.error(f"Image cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def run_cleanup_cycle(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        Run a data cleanup cycle to fix/remove errors.

        This cycle:
        1. Runs quality checks on all entity types
        2. Auto-fixes fixable issues (whitespace, invalid values)
        3. Splits multi-name entries
        4. Removes clearly invalid entries (placeholders, no relationships)
        5. Reports potential duplicates

        Args:
            dry_run: If True, report what would be done without making changes

        Returns:
            Dict with cleanup results
        """
        from .models import WrestleBotConfig, WrestleBotStats
        from .quality import DataCleaner

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping cleanup")
            return {'status': 'disabled'}

        start_time = time.time()

        results = {
            'status': 'completed',
            'dry_run': dry_run,
        }

        try:
            cleaner = DataCleaner()
            cleanup_results = cleaner.run_cleanup_cycle(
                entity_types=['wrestler', 'event', 'promotion', 'venue'],
                dry_run=dry_run
            )

            results.update(cleanup_results)

            # Update daily stats if not dry run
            if not dry_run:
                stats = WrestleBotStats.get_or_create_today()
                # Log cleanup as verifications
                total_fixed = cleanup_results.get('auto_fixed', 0) + cleanup_results.get('multi_name_split', 0)
                if total_fixed > 0:
                    stats.increment('verifications', total_fixed)

            logger.info(f"Cleanup cycle complete: {cleanup_results}")

        except Exception as e:
            logger.error(f"Cleanup cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def run_verification_cycle(self, batch_size: int = None) -> Dict[str, Any]:
        """
        Run a verification cycle to cross-check data accuracy.

        This cycle:
        1. Gets entities with incomplete data
        2. Cross-references with Wikipedia and Cagematch
        3. Applies verified corrections for missing fields
        4. Reports discrepancies for manual review

        Args:
            batch_size: Number of entities to verify (default 10)

        Returns:
            Dict with verification results
        """
        from .models import WrestleBotConfig, WrestleBotStats

        if not self.is_enabled():
            logger.info("WrestleBot is disabled, skipping verification")
            return {'status': 'disabled'}

        if batch_size is None:
            batch_size = 10

        start_time = time.time()

        results = {
            'status': 'completed',
        }

        try:
            verification_results = self.enrichment.run_verification_cycle(
                entity_type='wrestler',
                limit=batch_size,
                apply_corrections=True
            )

            results.update(verification_results)

            # Update daily stats
            stats = WrestleBotStats.get_or_create_today()
            if verification_results.get('corrections_applied', 0) > 0:
                stats.increment('verifications', verification_results['corrections_applied'])

            logger.info(f"Verification cycle complete: {verification_results}")

        except Exception as e:
            logger.error(f"Verification cycle failed: {e}")
            results['status'] = 'error'
            results['error'] = str(e)

        results['duration_ms'] = int((time.time() - start_time) * 1000)
        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get current WrestleBot status and statistics.

        Returns comprehensive status information for admin dashboard.
        """
        from .models import WrestleBotActivity, WrestleBotConfig, WrestleBotStats
        from ..models import Wrestler, Promotion, Event

        # Get today's stats
        try:
            today_stats = WrestleBotStats.get_or_create_today()
            today_data = {
                'discoveries': today_stats.discoveries,
                'enrichments': today_stats.enrichments,
                'images_added': today_stats.images_added,
                'verifications': today_stats.verifications,
                'errors': today_stats.errors,
            }
        except Exception:
            today_data = {}

        # Get recent activity
        recent_activity = WrestleBotActivity.get_stats(hours=24)

        # Get AI stats if available
        ai_stats = {}
        if self.ai_enhancer and self.ai_enhancer.is_available:
            ai_stats = self.ai_enhancer.get_stats()

        # Get configuration
        config = WrestleBotConfig.get_all()

        return {
            'enabled': config.get('enabled', True),
            'config': config,
            'today': today_data,
            'last_24h': recent_activity,
            'ai': ai_stats,
            'totals': {
                'wrestlers': Wrestler.objects.count(),
                'promotions': Promotion.objects.count(),
                'events': Event.objects.count(),
                'wrestlers_with_images': Wrestler.objects.filter(image_url__isnull=False).count(),
            },
        }


# Singleton instance for convenience
_bot_instance = None


def get_wrestlebot() -> WrestleBot:
    """Get the singleton WrestleBot instance."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = WrestleBot()
    return _bot_instance
