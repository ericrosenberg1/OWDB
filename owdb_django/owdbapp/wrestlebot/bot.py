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

    def _infer_promotion(self, name: str):
        """Infer promotion from an event or title name."""
        from ..models import Promotion

        # Common promotion patterns (name -> (db_name, slug, abbreviation))
        PROMOTION_PATTERNS = [
            (['WWE', 'WWF', 'World Wrestling Entertainment'], 'WWE', 'wwe', 'WWE'),
            (['AEW', 'All Elite'], 'All Elite Wrestling', 'all-elite-wrestling', 'AEW'),
            (['NWA', 'National Wrestling Alliance'], 'National Wrestling Alliance', 'nwa', 'NWA'),
            (['WCW', 'World Championship Wrestling'], 'World Championship Wrestling', 'wcw', 'WCW'),
            (['ECW', 'Extreme Championship'], 'Extreme Championship Wrestling', 'ecw', 'ECW'),
            (['TNA', 'Impact', 'Total Nonstop'], 'Impact Wrestling', 'impact-wrestling', 'IMPACT'),
            (['ROH', 'Ring of Honor'], 'Ring of Honor', 'ring-of-honor', 'ROH'),
            (['NJPW', 'New Japan'], 'New Japan Pro-Wrestling', 'njpw', 'NJPW'),
            (['CMLL', 'Consejo Mundial'], 'CMLL', 'cmll', 'CMLL'),
            (['AAA', 'Lucha Libre AAA'], 'Lucha Libre AAA', 'aaa', 'AAA'),
            (['STARDOM'], 'Stardom', 'stardom', 'STARDOM'),
            (['DDT'], 'DDT Pro-Wrestling', 'ddt', 'DDT'),
            (['AJPW', 'All Japan'], 'All Japan Pro Wrestling', 'ajpw', 'AJPW'),
            (['NOAH', 'Pro Wrestling NOAH'], 'Pro Wrestling Noah', 'noah', 'NOAH'),
            (['MLW', 'Major League Wrestling'], 'Major League Wrestling', 'mlw', 'MLW'),
            (['GCW', 'Game Changer'], 'Game Changer Wrestling', 'gcw', 'GCW'),
            (['PWG', 'Pro Wrestling Guerrilla'], 'Pro Wrestling Guerrilla', 'pwg', 'PWG'),
            (['PROGRESS'], 'PROGRESS Wrestling', 'progress', 'PROGRESS'),
            (['RevPro', 'Revolution Pro'], 'Revolution Pro Wrestling', 'revpro', 'RevPro'),
            (['ICW'], 'Insane Championship Wrestling', 'icw', 'ICW'),
            (['OVW', 'Ohio Valley'], 'Ohio Valley Wrestling', 'ovw', 'OVW'),
            (['NXT'], 'WWE NXT', 'nxt', 'NXT'),
            (['EVOLVE'], 'EVOLVE Wrestling', 'evolve', 'EVOLVE'),
            (['CZW', 'Combat Zone'], 'Combat Zone Wrestling', 'czw', 'CZW'),
            (['Wrestle Kingdom', 'G1'], 'New Japan Pro-Wrestling', 'njpw', 'NJPW'),
            (['WrestleMania', 'Royal Rumble', 'SummerSlam', 'Survivor Series'], 'WWE', 'wwe', 'WWE'),
            (['Double or Nothing', 'All Out', 'Full Gear', 'Revolution'], 'All Elite Wrestling', 'all-elite-wrestling', 'AEW'),
        ]

        name_upper = name.upper()
        for patterns, promo_name, slug, abbrev in PROMOTION_PATTERNS:
            for pattern in patterns:
                if pattern.upper() in name_upper:
                    promotion, _ = Promotion.objects.get_or_create(
                        name=promo_name,
                        defaults={'slug': slug, 'abbreviation': abbrev}
                    )
                    return promotion

        return None

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

        # Balance between discovery (new items) and enrichment (completing existing)
        # 60% discovery, 40% enrichment for better data quality
        discovery_items = max(1, int(max_items * 0.6))
        enrichment_items = max(1, int(max_items * 0.4))
        items_per_type = max(1, discovery_items // 4)

        # === ENRICHMENT PHASE (run first to improve existing data) ===
        if enrichment_items > 0:
            enriched = self._run_enrichment_cycle(enrichment_items)
            results['enriched'] = enriched

        # === DISCOVERY PHASE ===
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

        # === INTERLINKING PHASE ===
        linked = self._run_interlinking_cycle(max(1, max_items // 4))
        results['linked'] = linked

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
                threshold = self.config.min_confidence_threshold
            else:
                # Use fallback validation when AI unavailable
                # Lower threshold for fallback since it's simpler validation
                valid, confidence, reasoning = self.ai.fallback_verify(data)
                threshold = min(self.config.min_confidence_threshold, 0.5)

            if not valid or confidence < threshold:
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
                threshold = self.config.min_confidence_threshold
            else:
                valid, confidence, reasoning = self.ai.fallback_verify(data)
                threshold = min(self.config.min_confidence_threshold, 0.5)

            if not valid or confidence < threshold:
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
                threshold = self.config.min_confidence_threshold
            else:
                valid, confidence, reasoning = self.ai.fallback_verify(data)
                threshold = min(self.config.min_confidence_threshold, 0.5)

            if not valid or confidence < threshold:
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
            promotion = self._infer_promotion(name)

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
            promotion = self._infer_promotion(name)

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

    # =========================================================================
    # ENRICHMENT METHODS - Completing existing profiles
    # =========================================================================

    def _run_enrichment_cycle(self, max_items: int) -> int:
        """
        Enrich existing incomplete profiles with more data.
        Returns count of items enriched.
        """
        enriched = 0

        # Get wrestlers needing enrichment
        from ..models import Wrestler, Promotion
        incomplete_wrestlers = Wrestler.get_incomplete_profiles(limit=max_items)

        for wrestler in incomplete_wrestlers:
            try:
                if self._enrich_wrestler(wrestler):
                    enriched += 1
            except Exception as e:
                logger.error(f"Error enriching wrestler {wrestler.name}: {e}")

        # Get promotions needing enrichment (fewer, as there are less)
        incomplete_promotions = Promotion.objects.filter(
            wikipedia_url__isnull=True
        ).order_by('-created_at')[:max(1, max_items // 3)]

        for promotion in incomplete_promotions:
            try:
                if self._enrich_promotion(promotion):
                    enriched += 1
            except Exception as e:
                logger.error(f"Error enriching promotion {promotion.name}: {e}")

        return enriched

    @transaction.atomic
    def _enrich_wrestler(self, wrestler) -> bool:
        """
        Enrich a wrestler's profile with Wikipedia data.
        Returns True if any data was updated.
        """
        from ..models import Wrestler

        # Try to find Wikipedia article if we don't have the URL
        wiki_title = None
        if wrestler.wikipedia_url:
            # Extract title from URL
            wiki_title = wrestler.wikipedia_url.split('/wiki/')[-1].replace('_', ' ')
        else:
            # Search for the wrestler
            wiki_title = self.wikipedia.search_wrestler_wikipedia(wrestler.name)
            if not wiki_title:
                return False

        # Get full data
        data = self.wikipedia.get_full_wrestler_data(wiki_title)
        if not data:
            return False

        # Track what we update
        updated_fields = []

        # Update missing fields (don't overwrite existing data)
        if not wrestler.wikipedia_url and data.get('source_url'):
            wrestler.wikipedia_url = data['source_url']
            updated_fields.append('wikipedia_url')

        if not wrestler.real_name and data.get('real_name'):
            wrestler.real_name = data['real_name'][:255]
            updated_fields.append('real_name')

        if not wrestler.aliases and data.get('aliases'):
            wrestler.aliases = data['aliases'][:1000]
            updated_fields.append('aliases')

        if not wrestler.hometown and data.get('hometown'):
            wrestler.hometown = data['hometown'][:255]
            updated_fields.append('hometown')

        if not wrestler.nationality and data.get('birth_place'):
            # Try to infer nationality from birthplace
            nationality = self._infer_nationality(data['birth_place'])
            if nationality:
                wrestler.nationality = nationality
                updated_fields.append('nationality')

        if not wrestler.debut_year and data.get('debut_year'):
            wrestler.debut_year = data['debut_year']
            updated_fields.append('debut_year')

        if not wrestler.retirement_year and data.get('retirement_year'):
            wrestler.retirement_year = data['retirement_year']
            updated_fields.append('retirement_year')

        if not wrestler.finishers and data.get('finishers'):
            wrestler.finishers = data['finishers'][:1000]
            updated_fields.append('finishers')

        if not wrestler.height and data.get('height'):
            wrestler.height = data['height'][:50]
            updated_fields.append('height')

        if not wrestler.weight and data.get('weight'):
            wrestler.weight = data['weight'][:50]
            updated_fields.append('weight')

        if not wrestler.trained_by and data.get('trained_by'):
            wrestler.trained_by = data['trained_by'][:500]
            updated_fields.append('trained_by')

        if not wrestler.signature_moves and data.get('signature_moves'):
            wrestler.signature_moves = data['signature_moves'][:1000]
            updated_fields.append('signature_moves')

        if not wrestler.birth_date and data.get('birth_date'):
            try:
                from datetime import datetime
                bd = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                wrestler.birth_date = bd
                updated_fields.append('birth_date')
            except (ValueError, TypeError):
                pass

        if updated_fields:
            wrestler.last_enriched = timezone.now()
            updated_fields.append('last_enriched')
            wrestler.save(update_fields=updated_fields)

            self.log_action(
                action_type='enrich',
                entity_type='wrestler',
                entity_name=wrestler.name,
                entity_id=wrestler.id,
                source_url=data.get('source_url'),
                ai_confidence=0.8,
                ai_reasoning=f"Enriched fields: {', '.join(updated_fields)}",
            )
            logger.info(f"Enriched wrestler {wrestler.name}: {updated_fields}")
            return True

        return False

    @transaction.atomic
    def _enrich_promotion(self, promotion) -> bool:
        """Enrich a promotion's profile with Wikipedia data."""
        from ..models import Promotion

        # Search for the promotion on Wikipedia
        wiki_title = self.wikipedia.search_promotion_wikipedia(promotion.name)
        if not wiki_title:
            return False

        data = self.wikipedia.get_full_promotion_data(wiki_title)
        if not data:
            return False

        updated_fields = []

        if not promotion.wikipedia_url and data.get('source_url'):
            promotion.wikipedia_url = data['source_url']
            updated_fields.append('wikipedia_url')

        if not promotion.abbreviation and data.get('abbreviation'):
            promotion.abbreviation = data['abbreviation'][:50]
            updated_fields.append('abbreviation')

        if not promotion.founded_year and data.get('founded_year'):
            promotion.founded_year = data['founded_year']
            updated_fields.append('founded_year')

        if not promotion.closed_year and data.get('closed_year'):
            promotion.closed_year = data['closed_year']
            updated_fields.append('closed_year')

        if not promotion.website and data.get('website'):
            promotion.website = data['website']
            updated_fields.append('website')

        if not promotion.headquarters and data.get('headquarters'):
            promotion.headquarters = data['headquarters'][:255]
            updated_fields.append('headquarters')

        if not promotion.founder and data.get('founder'):
            promotion.founder = data['founder'][:255]
            updated_fields.append('founder')

        if updated_fields:
            promotion.last_enriched = timezone.now()
            updated_fields.append('last_enriched')
            promotion.save(update_fields=updated_fields)

            self.log_action(
                action_type='enrich',
                entity_type='promotion',
                entity_name=promotion.name,
                entity_id=promotion.id,
                source_url=data.get('source_url'),
                ai_confidence=0.8,
                ai_reasoning=f"Enriched fields: {', '.join(updated_fields)}",
            )
            logger.info(f"Enriched promotion {promotion.name}: {updated_fields}")
            return True

        return False

    def _infer_nationality(self, birthplace: str) -> Optional[str]:
        """Infer nationality from birthplace string."""
        if not birthplace:
            return None

        birthplace_lower = birthplace.lower()

        # Common country mappings
        country_mappings = {
            'united states': 'American',
            'u.s.': 'American',
            'usa': 'American',
            'america': 'American',
            'japan': 'Japanese',
            'mexico': 'Mexican',
            'canada': 'Canadian',
            'england': 'English',
            'united kingdom': 'British',
            'uk': 'British',
            'scotland': 'Scottish',
            'wales': 'Welsh',
            'ireland': 'Irish',
            'australia': 'Australian',
            'germany': 'German',
            'france': 'French',
            'italy': 'Italian',
            'spain': 'Spanish',
            'brazil': 'Brazilian',
            'puerto rico': 'Puerto Rican',
            'india': 'Indian',
            'china': 'Chinese',
            'korea': 'Korean',
            'south korea': 'South Korean',
            'new zealand': 'New Zealander',
        }

        for country, nationality in country_mappings.items():
            if country in birthplace_lower:
                return nationality

        # Try to use AI if available
        if self.ai.is_available():
            nationality = self.ai.extract_nationality(birthplace)
            if nationality:
                return nationality

        return None

    # =========================================================================
    # INTERLINKING METHODS - Connecting entities
    # =========================================================================

    def _run_interlinking_cycle(self, max_items: int) -> int:
        """
        Link entities together (wrestlers to promotions, events, etc.)
        Returns count of links created.
        """
        from ..models import Wrestler, Promotion, Match, Event

        linked = 0

        # Find wrestlers without any match records who might have promotion info
        wrestlers_to_link = Wrestler.objects.filter(
            wikipedia_url__isnull=False,
            matches__isnull=True  # No matches yet
        ).order_by('-created_at')[:max_items]

        for wrestler in wrestlers_to_link:
            try:
                links = self._link_wrestler_to_promotions(wrestler)
                linked += links
            except Exception as e:
                logger.error(f"Error linking wrestler {wrestler.name}: {e}")

        return linked

    def _link_wrestler_to_promotions(self, wrestler) -> int:
        """
        Try to link a wrestler to promotions based on Wikipedia data.
        Returns count of links created.
        """
        from ..models import Promotion

        if not wrestler.wikipedia_url:
            return 0

        # Extract promotions from Wikipedia
        wiki_title = wrestler.wikipedia_url.split('/wiki/')[-1].replace('_', ' ')
        promo_names = self.wikipedia.get_wrestler_promotions_from_article(wiki_title)

        if not promo_names:
            return 0

        links_created = 0

        for promo_name in promo_names:
            # Try to find matching promotion
            promotion = self._find_matching_promotion(promo_name)
            if promotion:
                # Log the discovered link (actual match creation would require more data)
                self.log_action(
                    action_type='link',
                    entity_type='wrestler',
                    entity_name=f"{wrestler.name} -> {promotion.name}",
                    entity_id=wrestler.id,
                    ai_confidence=0.7,
                    ai_reasoning=f"Wrestler linked to promotion based on Wikipedia data",
                )
                links_created += 1

        return links_created

    def _find_matching_promotion(self, promo_name: str):
        """Find a promotion matching the given name."""
        from ..models import Promotion
        from django.db.models import Q

        promo_name = promo_name.strip()
        if not promo_name:
            return None

        # Try exact match first
        promotion = Promotion.objects.filter(name__iexact=promo_name).first()
        if promotion:
            return promotion

        # Try abbreviation match
        promotion = Promotion.objects.filter(abbreviation__iexact=promo_name).first()
        if promotion:
            return promotion

        # Try partial match
        promotion = Promotion.objects.filter(
            Q(name__icontains=promo_name) | Q(abbreviation__icontains=promo_name)
        ).first()

        return promotion

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
