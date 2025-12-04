"""
WrestleBot - AI-powered wrestling data discovery and enrichment.

This is the main bot class that coordinates:
1. Wikipedia API fetching
2. AI-powered data processing
3. Database imports with deduplication
4. Activity logging

COPYRIGHT COMPLIANCE:
- Only extracts factual, non-copyrightable data (names, dates, numbers)
- Never copies prose descriptions or creative content
- Always attributes sources with Wikipedia URLs
- Respects trademarks by using official names only
"""

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from .wikipedia_api import WikipediaAPIFetcher
from .ai_processor import OllamaProcessor

logger = logging.getLogger(__name__)


class WrestleBot:
    """
    Self-hosted AI bot for wrestling data discovery.

    The bot runs in the background via Celery Beat, slowly and
    respectfully gathering factual data from Wikipedia and
    enriching it using a local AI model.
    """

    def __init__(self):
        self.wikipedia = WikipediaAPIFetcher()
        self.ai = OllamaProcessor()
        self.batch_id = None
        self._config = None

    @property
    def config(self):
        """Get the bot configuration."""
        if self._config is None:
            from ..models import WrestleBotConfig
            self._config = WrestleBotConfig.get_config()
        return self._config

    def refresh_config(self):
        """Refresh configuration from database."""
        self._config = None
        return self.config

    def start_batch(self) -> str:
        """Start a new batch of operations."""
        self.batch_id = str(uuid.uuid4())[:8]
        return self.batch_id

    def log_action(
        self,
        action_type: str,
        entity_type: str,
        entity_name: str,
        entity_id: Optional[int] = None,
        source_url: Optional[str] = None,
        source_title: Optional[str] = None,
        data_extracted: Optional[Dict] = None,
        ai_confidence: Optional[float] = None,
        ai_reasoning: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Log an action to the database."""
        from ..models import WrestleBotLog

        try:
            WrestleBotLog.objects.create(
                action_type=action_type,
                entity_type=entity_type,
                entity_name=entity_name,
                entity_id=entity_id,
                source_url=source_url,
                source_title=source_title,
                data_extracted=data_extracted or {},
                ai_model=self.ai.model if self.ai.is_available() else None,
                ai_confidence=ai_confidence,
                ai_reasoning=ai_reasoning,
                batch_id=self.batch_id,
                success=success,
                error_message=error_message,
            )
        except Exception as e:
            logger.error(f"Failed to log action: {e}")

    def can_run(self) -> bool:
        """Check if the bot can run (rate limits, enabled, etc.)."""
        self.refresh_config()
        return self.config.can_add_items()

    def run_discovery_cycle(self, max_items: int = 10) -> Dict[str, int]:
        """
        Run a single discovery cycle.

        This is the main entry point called by Celery Beat.
        It discovers new entities, verifies them with AI, and
        imports them to the database.
        """
        self.refresh_config()

        if not self.config.enabled:
            logger.info("WrestleBot is disabled")
            return {'status': 'disabled'}

        if not self.config.can_add_items():
            logger.info("WrestleBot rate limited")
            return {'status': 'rate_limited'}

        self.start_batch()
        results = {
            'wrestlers_discovered': 0,
            'wrestlers_added': 0,
            'promotions_discovered': 0,
            'promotions_added': 0,
            'events_discovered': 0,
            'events_added': 0,
            'titles_discovered': 0,
            'titles_added': 0,
            'errors': 0,
        }

        # Determine what to focus on based on config
        items_per_type = max(1, max_items // 4)

        if self.config.focus_wrestlers:
            w_disc, w_add = self._discover_wrestlers(items_per_type)
            results['wrestlers_discovered'] = w_disc
            results['wrestlers_added'] = w_add

        if self.config.focus_promotions:
            p_disc, p_add = self._discover_promotions(items_per_type)
            results['promotions_discovered'] = p_disc
            results['promotions_added'] = p_add

        if self.config.focus_events and self.config.can_add_items():
            e_disc, e_add = self._discover_events(items_per_type)
            results['events_discovered'] = e_disc
            results['events_added'] = e_add

        if self.config.focus_titles and self.config.can_add_items():
            t_disc, t_add = self._discover_titles(items_per_type)
            results['titles_discovered'] = t_disc
            results['titles_added'] = t_add

        # Update config with last run time
        self.config.last_run = timezone.now()
        self.config.save(update_fields=['last_run'])

        logger.info(f"WrestleBot cycle complete: {results}")
        return results

    def _discover_wrestlers(self, limit: int) -> Tuple[int, int]:
        """Discover and import new wrestlers."""
        from ..models import Wrestler

        discovered = 0
        added = 0

        try:
            wrestlers = self.wikipedia.discover_new_wrestlers(limit=limit * 2)
            discovered = len(wrestlers)

            for data in wrestlers:
                if not self.config.can_add_items():
                    break

                try:
                    wrestler_id = self._import_wrestler(data)
                    if wrestler_id:
                        added += 1
                        self.config.record_items_added()
                except Exception as e:
                    logger.error(f"Error importing wrestler {data.get('name')}: {e}")
                    self.log_action(
                        action_type='error',
                        entity_type='wrestler',
                        entity_name=data.get('name', 'Unknown'),
                        source_url=data.get('source_url'),
                        success=False,
                        error_message=str(e),
                    )

        except Exception as e:
            logger.error(f"Error discovering wrestlers: {e}")
            self.config.total_errors += 1
            self.config.save(update_fields=['total_errors'])

        return discovered, added

    def _discover_promotions(self, limit: int) -> Tuple[int, int]:
        """Discover and import new promotions."""
        discovered = 0
        added = 0

        try:
            promotions = self.wikipedia.discover_new_promotions(limit=limit * 2)
            discovered = len(promotions)

            for data in promotions:
                if not self.config.can_add_items():
                    break

                try:
                    promo_id = self._import_promotion(data)
                    if promo_id:
                        added += 1
                        self.config.record_items_added()
                except Exception as e:
                    logger.error(f"Error importing promotion {data.get('name')}: {e}")
                    self.log_action(
                        action_type='error',
                        entity_type='promotion',
                        entity_name=data.get('name', 'Unknown'),
                        source_url=data.get('source_url'),
                        success=False,
                        error_message=str(e),
                    )

        except Exception as e:
            logger.error(f"Error discovering promotions: {e}")
            self.config.total_errors += 1
            self.config.save(update_fields=['total_errors'])

        return discovered, added

    def _discover_events(self, limit: int) -> Tuple[int, int]:
        """Discover and import new events."""
        discovered = 0
        added = 0

        try:
            events = self.wikipedia.discover_new_events(limit=limit * 2)
            discovered = len(events)

            for data in events:
                if not self.config.can_add_items():
                    break

                try:
                    event_id = self._import_event(data)
                    if event_id:
                        added += 1
                        self.config.record_items_added()
                except Exception as e:
                    logger.error(f"Error importing event {data.get('name')}: {e}")
                    self.log_action(
                        action_type='error',
                        entity_type='event',
                        entity_name=data.get('name', 'Unknown'),
                        source_url=data.get('source_url'),
                        success=False,
                        error_message=str(e),
                    )

        except Exception as e:
            logger.error(f"Error discovering events: {e}")
            self.config.total_errors += 1
            self.config.save(update_fields=['total_errors'])

        return discovered, added

    def _discover_titles(self, limit: int) -> Tuple[int, int]:
        """Discover and import new championship titles."""
        discovered = 0
        added = 0

        try:
            titles = self.wikipedia.discover_new_titles(limit=limit * 2)
            discovered = len(titles)

            for data in titles:
                if not self.config.can_add_items():
                    break

                try:
                    title_id = self._import_title(data)
                    if title_id:
                        added += 1
                        self.config.record_items_added()
                except Exception as e:
                    logger.error(f"Error importing title {data.get('name')}: {e}")
                    self.log_action(
                        action_type='error',
                        entity_type='title',
                        entity_name=data.get('name', 'Unknown'),
                        source_url=data.get('source_url'),
                        success=False,
                        error_message=str(e),
                    )

        except Exception as e:
            logger.error(f"Error discovering titles: {e}")
            self.config.total_errors += 1
            self.config.save(update_fields=['total_errors'])

        return discovered, added

    @transaction.atomic
    def _import_wrestler(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a wrestler to the database with AI verification."""
        from ..models import Wrestler

        name = data.get('name')
        if not name:
            return None

        # Check for duplicates
        if Wrestler.objects.filter(name__iexact=name).exists():
            self.log_action(
                action_type='skip',
                entity_type='wrestler',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='Duplicate - already exists',
            )
            return None

        # AI verification if enabled
        confidence = 0.7
        reasoning = "Imported from Wikipedia"

        if self.config.require_verification:
            if self.ai.is_available():
                valid, confidence, reasoning = self.ai.verify_wrestler_data(data)
            else:
                # Use fallback validation when AI unavailable
                valid, confidence, reasoning = self.ai.fallback_verify(data)

            if not valid or confidence < self.config.min_confidence_threshold:
                self.log_action(
                    action_type='skip',
                    entity_type='wrestler',
                    entity_name=name,
                    source_url=data.get('source_url'),
                    ai_confidence=confidence,
                    ai_reasoning=reasoning,
                    success=False,
                )
                return None

        # Enrich data with AI if available
        if self.ai.is_available():
            data = self.ai.enrich_wrestler_data(data)

        # Create the wrestler
        wrestler = Wrestler.objects.create(
            name=name,
            slug=slugify(name)[:255],
            real_name=data.get('real_name', '')[:255] if data.get('real_name') else None,
            aliases=data.get('aliases', '')[:1000] if data.get('aliases') else None,
            hometown=data.get('hometown', '')[:255] if data.get('hometown') else None,
            nationality=data.get('nationality', '')[:255] if data.get('nationality') else None,
            finishers=data.get('finishers', '')[:1000] if data.get('finishers') else None,
            debut_year=data.get('debut_year'),
            retirement_year=data.get('retirement_year'),
        )

        # Log the action
        self.log_action(
            action_type='create',
            entity_type='wrestler',
            entity_name=name,
            entity_id=wrestler.id,
            source_url=data.get('source_url'),
            source_title=data.get('source_title'),
            data_extracted={k: v for k, v in data.items() if k not in ['source', 'source_url', 'source_title']},
            ai_confidence=confidence,
            ai_reasoning=reasoning,
        )

        logger.info(f"WrestleBot created wrestler: {name}")
        return wrestler.id

    @transaction.atomic
    def _import_promotion(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a promotion to the database with AI verification."""
        from ..models import Promotion

        name = data.get('name')
        if not name:
            return None

        # Check for duplicates
        if Promotion.objects.filter(name__iexact=name).exists():
            self.log_action(
                action_type='skip',
                entity_type='promotion',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='Duplicate - already exists',
            )
            return None

        # AI verification
        confidence = 0.7
        reasoning = "Imported from Wikipedia"

        if self.config.require_verification:
            if self.ai.is_available():
                valid, confidence, reasoning = self.ai.verify_promotion_data(data)
            else:
                valid, confidence, reasoning = self.ai.fallback_verify(data)

            if not valid or confidence < self.config.min_confidence_threshold:
                self.log_action(
                    action_type='skip',
                    entity_type='promotion',
                    entity_name=name,
                    source_url=data.get('source_url'),
                    ai_confidence=confidence,
                    ai_reasoning=reasoning,
                    success=False,
                )
                return None

        # Create the promotion
        promotion = Promotion.objects.create(
            name=name,
            slug=slugify(name)[:255],
            abbreviation=data.get('abbreviation', '')[:50] if data.get('abbreviation') else None,
            founded_year=data.get('founded_year'),
            closed_year=data.get('closed_year'),
            website=data.get('website', '')[:200] if data.get('website') else None,
        )

        self.log_action(
            action_type='create',
            entity_type='promotion',
            entity_name=name,
            entity_id=promotion.id,
            source_url=data.get('source_url'),
            source_title=data.get('source_title'),
            data_extracted={k: v for k, v in data.items() if k not in ['source', 'source_url', 'source_title']},
            ai_confidence=confidence,
            ai_reasoning=reasoning,
        )

        logger.info(f"WrestleBot created promotion: {name}")
        return promotion.id

    @transaction.atomic
    def _import_event(self, data: Dict[str, Any]) -> Optional[int]:
        """Import an event to the database with AI verification."""
        from ..models import Event, Venue, Promotion

        name = data.get('name')
        date_str = data.get('date')

        if not name or not date_str:
            return None

        # Parse date
        try:
            from datetime import datetime
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return None

        # Check for duplicates
        if Event.objects.filter(name__iexact=name, date=event_date).exists():
            self.log_action(
                action_type='skip',
                entity_type='event',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='Duplicate - already exists',
            )
            return None

        # AI verification
        confidence = 0.7
        reasoning = "Imported from Wikipedia"

        if self.config.require_verification:
            if self.ai.is_available():
                valid, confidence, reasoning = self.ai.verify_event_data(data)
            else:
                valid, confidence, reasoning = self.ai.fallback_verify(data)

            if not valid or confidence < self.config.min_confidence_threshold:
                self.log_action(
                    action_type='skip',
                    entity_type='event',
                    entity_name=name,
                    source_url=data.get('source_url'),
                    ai_confidence=confidence,
                    ai_reasoning=reasoning,
                    success=False,
                )
                return None

        # Get or create venue
        venue = None
        if data.get('venue_name'):
            venue, _ = Venue.objects.get_or_create(
                name=data['venue_name'][:255],
                defaults={
                    'slug': slugify(data['venue_name'])[:255],
                    'location': data.get('venue_location', '')[:255] if data.get('venue_location') else None,
                }
            )

        # Get or create promotion
        promotion = None
        if data.get('promotion_name'):
            promotion, _ = Promotion.objects.get_or_create(
                name=data['promotion_name'][:255],
                defaults={'slug': slugify(data['promotion_name'])[:255]}
            )
        else:
            # Try to infer promotion from event name
            if 'WWE' in name or 'WWF' in name:
                promotion, _ = Promotion.objects.get_or_create(
                    name='WWE',
                    defaults={'slug': 'wwe', 'abbreviation': 'WWE'}
                )
            elif 'AEW' in name:
                promotion, _ = Promotion.objects.get_or_create(
                    name='All Elite Wrestling',
                    defaults={'slug': 'all-elite-wrestling', 'abbreviation': 'AEW'}
                )

        if not promotion:
            self.log_action(
                action_type='skip',
                entity_type='event',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='No promotion identified',
                success=False,
            )
            return None

        # Create the event
        event = Event.objects.create(
            name=name[:255],
            slug=slugify(f"{name}-{event_date.year}")[:255],
            date=event_date,
            promotion=promotion,
            venue=venue,
            attendance=data.get('attendance'),
        )

        self.log_action(
            action_type='create',
            entity_type='event',
            entity_name=name,
            entity_id=event.id,
            source_url=data.get('source_url'),
            source_title=data.get('source_title'),
            data_extracted={k: v for k, v in data.items() if k not in ['source', 'source_url', 'source_title']},
            ai_confidence=confidence,
            ai_reasoning=reasoning,
        )

        logger.info(f"WrestleBot created event: {name}")
        return event.id

    @transaction.atomic
    def _import_title(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a championship title to the database."""
        from ..models import Title, Promotion

        name = data.get('name')
        if not name:
            return None

        # Check for duplicates
        if Title.objects.filter(name__iexact=name).exists():
            self.log_action(
                action_type='skip',
                entity_type='title',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='Duplicate - already exists',
            )
            return None

        # Get or create promotion
        promotion = None
        if data.get('promotion_name'):
            promotion, _ = Promotion.objects.get_or_create(
                name=data['promotion_name'][:255],
                defaults={'slug': slugify(data['promotion_name'])[:255]}
            )
        else:
            # Try to infer from title name
            if 'WWE' in name or 'WWF' in name:
                promotion, _ = Promotion.objects.get_or_create(
                    name='WWE',
                    defaults={'slug': 'wwe', 'abbreviation': 'WWE'}
                )
            elif 'AEW' in name:
                promotion, _ = Promotion.objects.get_or_create(
                    name='All Elite Wrestling',
                    defaults={'slug': 'all-elite-wrestling', 'abbreviation': 'AEW'}
                )
            elif 'NWA' in name:
                promotion, _ = Promotion.objects.get_or_create(
                    name='National Wrestling Alliance',
                    defaults={'slug': 'nwa', 'abbreviation': 'NWA'}
                )

        if not promotion:
            self.log_action(
                action_type='skip',
                entity_type='title',
                entity_name=name,
                source_url=data.get('source_url'),
                ai_reasoning='No promotion identified',
                success=False,
            )
            return None

        # Create the title
        title = Title.objects.create(
            name=name[:255],
            slug=slugify(name)[:255],
            promotion=promotion,
            debut_year=data.get('debut_year'),
            retirement_year=data.get('retirement_year'),
        )

        self.log_action(
            action_type='create',
            entity_type='title',
            entity_name=name,
            entity_id=title.id,
            source_url=data.get('source_url'),
            source_title=data.get('source_title'),
            data_extracted={k: v for k, v in data.items() if k not in ['source', 'source_url', 'source_title']},
            ai_confidence=0.7,
            ai_reasoning='Imported from Wikipedia',
        )

        logger.info(f"WrestleBot created title: {name}")
        return title.id

    def get_statistics(self) -> Dict[str, Any]:
        """Get WrestleBot statistics."""
        from ..models import WrestleBotLog

        logs = WrestleBotLog.objects.all()

        stats = {
            'enabled': self.config.enabled,
            'ai_available': self.ai.is_available(),
            'ai_model': self.ai.model if self.ai.is_available() else None,
            'total_items_added': self.config.total_items_added,
            'items_today': self.config.items_added_today,
            'items_this_hour': self.config.items_added_this_hour,
            'max_per_hour': self.config.max_items_per_hour,
            'max_per_day': self.config.max_items_per_day,
            'total_errors': self.config.total_errors,
            'last_run': self.config.last_run,
            'logs_total': logs.count(),
            'logs_by_action': {},
            'logs_by_entity': {},
        }

        # Aggregate by action type
        for action_type, _ in WrestleBotLog.ACTION_TYPES:
            count = logs.filter(action_type=action_type).count()
            if count > 0:
                stats['logs_by_action'][action_type] = count

        # Aggregate by entity type
        for entity_type, _ in WrestleBotLog.ENTITY_TYPES:
            count = logs.filter(entity_type=entity_type).count()
            if count > 0:
                stats['logs_by_entity'][entity_type] = count

        return stats
