#!/usr/bin/env python3
"""
WrestleBot - Standalone Wrestling Data Collection Service

Main entry point for the WrestleBot service.
"""

import os
import sys
import signal
import logging
import time
from pathlib import Path
from datetime import datetime

# Add current directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent))

from api_client.django_api import DjangoAPIClient
from utils.circuit_breaker import circuit_breaker_manager
from scrapers import WikipediaWrestlerScraper
from scrapers.bulk_wrestler_discovery import BulkWrestlerDiscovery
from scrapers.bulk_promotion_discovery import BulkPromotionDiscovery
from scrapers.bulk_event_discovery import BulkEventDiscovery
from scrapers.bulk_media_discovery import (
    BulkVideoGameDiscovery,
    BulkBookDiscovery,
    BulkDocumentaryDiscovery
)
from scrapers.page_enrichment import PageEnrichmentDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/wrestlebot.log')
    ]
)

logger = logging.getLogger(__name__)


class WrestleBotService:
    """Main WrestleBot service."""

    def __init__(self):
        self.running = False
        self.api_client = None
        self.scraper = None
        self.bulk_scraper = None
        self.bulk_promotion_scraper = None
        self.bulk_event_scraper = None
        self.bulk_videogame_scraper = None
        self.bulk_book_scraper = None
        self.bulk_documentary_scraper = None
        self.page_enrichment = None
        self.start_time = None
        self.wrestlers_added = 0
        self.promotions_added = 0
        self.events_added = 0
        self.videogames_added = 0
        self.books_added = 0
        self.documentaries_added = 0
        self.entities_enriched = 0
        self.bulk_modes_complete = {
            'wrestlers': False,
            'promotions': False,
            'events': False,
            'videogames': False,
            'books': False,
            'documentaries': False,
        }

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def initialize(self):
        """Initialize the service."""
        logger.info("=" * 70)
        logger.info("WrestleBot Service v2.0.0")
        logger.info("=" * 70)

        # Check for API token
        api_token = os.getenv('WRESTLEBOT_API_TOKEN')
        if not api_token:
            logger.error(
                "WRESTLEBOT_API_TOKEN environment variable not set!\n"
                "Run: python manage.py setup_wrestlebot_user\n"
                "Then: export WRESTLEBOT_API_TOKEN=your-token-here"
            )
            sys.exit(1)

        # Initialize API client
        try:
            self.api_client = DjangoAPIClient()
            logger.info(f"Django API: {self.api_client.api_url}")
        except Exception as e:
            logger.error(f"Failed to initialize API client: {e}")
            sys.exit(1)

        # Initialize scrapers
        try:
            self.scraper = WikipediaWrestlerScraper()
            self.bulk_scraper = BulkWrestlerDiscovery()
            self.bulk_promotion_scraper = BulkPromotionDiscovery()
            self.bulk_event_scraper = BulkEventDiscovery()
            self.bulk_videogame_scraper = BulkVideoGameDiscovery()
            self.bulk_book_scraper = BulkBookDiscovery()
            self.bulk_documentary_scraper = BulkDocumentaryDiscovery()
            self.page_enrichment = PageEnrichmentDiscovery(self.api_client)
            logger.info("All discovery scrapers initialized (bulk + page enrichment)")
        except Exception as e:
            logger.error(f"Failed to initialize scrapers: {e}")
            sys.exit(1)

        # Test API connection
        if not self.api_client.health_check():
            logger.error(
                "Django API health check failed!\n"
                "Make sure Django is running: python manage.py runserver"
            )
            sys.exit(1)

        logger.info("API health check: OK")

        # Get status from Django
        status = self.api_client.get_status()
        if status:
            logger.info(f"Django version: {status.get('version')}")
            logger.info(f"Database connected: {status.get('database_connected')}")
            logger.info(f"Total wrestlers: {status.get('total_wrestlers')}")
            logger.info(f"Total promotions: {status.get('total_promotions')}")
            logger.info(f"Total events: {status.get('total_events')}")
            logger.info(f"Total articles: {status.get('total_articles')}")

        logger.info("=" * 70)
        logger.info("Service initialized successfully")
        logger.info("=" * 70)

    def run(self):
        """Run the main service loop."""
        self.running = True
        self.start_time = datetime.now()
        cycle = 0

        logger.info("Starting main service loop...")

        while self.running:
            try:
                cycle += 1
                logger.info(f"\n--- Cycle {cycle} ---")

                # Heartbeat
                uptime = (datetime.now() - self.start_time).total_seconds()
                logger.info(f"Uptime: {uptime:.0f} seconds")

                # Check API connection
                api_healthy = self.api_client.health_check()
                if not api_healthy:
                    logger.warning("API health check failed, will retry next cycle")
                else:
                    logger.info("API health check: OK")

                # Run bulk discovery stages in order until complete
                if not api_healthy:
                    logger.info("Skipping bulk/enrichment work while API is unhealthy")
                elif not self.bulk_modes_complete['wrestlers']:
                    try:
                        logger.info("=== BULK MODE: Discovering ALL wrestlers from Wikipedia ===")
                        all_names = self.bulk_scraper.discover_all_wrestlers()
                        logger.info(f"Discovered {len(all_names)} unique wrestler names")

                        batch_size = 100
                        errors = 0
                        for i in range(0, len(all_names), batch_size):
                            batch_names = all_names[i:i + batch_size]
                            wrestlers = self.bulk_scraper.get_wrestler_details_batch(batch_names)

                            for wrestler_data in wrestlers:
                                try:
                                    result = self.api_client.create_wrestler(wrestler_data)
                                    if result:
                                        self.wrestlers_added += 1
                                        if self.wrestlers_added % 50 == 0:
                                            logger.info(f"Progress: {self.wrestlers_added} wrestlers added")
                                except Exception as e:
                                    errors += 1
                                    if errors <= 5:
                                        logger.warning(
                                            f"Failed to create wrestler {wrestler_data.get('name')}: {e}"
                                        )

                        if errors:
                            logger.warning(f"Wrestler bulk had {errors} errors")

                        self.bulk_modes_complete['wrestlers'] = True
                        logger.info(f"=== WRESTLERS BULK COMPLETE: Added {self.wrestlers_added} ===")

                    except Exception as e:
                        logger.error(f"Wrestler bulk discovery failed: {e}", exc_info=True)

                elif not self.bulk_modes_complete['promotions']:
                    try:
                        logger.info("=== BULK MODE: Discovering ALL promotions from Wikipedia ===")
                        all_names = self.bulk_promotion_scraper.discover_all_promotions()
                        logger.info(f"Discovered {len(all_names)} unique promotions")

                        batch_size = 100
                        errors = 0
                        for i in range(0, len(all_names), batch_size):
                            batch_names = all_names[i:i + batch_size]
                            promotions = self.bulk_promotion_scraper.get_promotion_details_batch(batch_names)

                            for promotion_data in promotions:
                                try:
                                    result = self.api_client.create_promotion(promotion_data)
                                    if result:
                                        self.promotions_added += 1
                                        if self.promotions_added % 20 == 0:
                                            logger.info(f"Progress: {self.promotions_added} promotions added")
                                except Exception as e:
                                    errors += 1
                                    if errors <= 5:
                                        logger.warning(
                                            f"Failed to create promotion {promotion_data.get('name')}: {e}"
                                        )

                        if errors:
                            logger.warning(f"Promotion bulk had {errors} errors")

                        self.bulk_modes_complete['promotions'] = True
                        logger.info(f"=== PROMOTIONS BULK COMPLETE: Added {self.promotions_added} ===")

                    except Exception as e:
                        logger.error(f"Promotion bulk discovery failed: {e}", exc_info=True)

                elif not self.bulk_modes_complete['events']:
                    try:
                        logger.info("=== BULK MODE: Discovering ALL events from Wikipedia ===")
                        all_names = self.bulk_event_scraper.discover_all_events()
                        logger.info(f"Discovered {len(all_names)} unique events")

                        batch_size = 100
                        errors = 0
                        for i in range(0, len(all_names), batch_size):
                            batch_names = all_names[i:i + batch_size]
                            events = self.bulk_event_scraper.get_event_details_batch(batch_names)

                            for event_data in events:
                                try:
                                    result = self.api_client.create_event(event_data)
                                    if result:
                                        self.events_added += 1
                                        if self.events_added % 20 == 0:
                                            logger.info(f"Progress: {self.events_added} events added")
                                except Exception as e:
                                    errors += 1
                                    if errors <= 5:
                                        logger.warning(
                                            f"Failed to create event {event_data.get('name')}: {e}"
                                        )

                        if errors:
                            logger.warning(f"Event bulk had {errors} errors")

                        self.bulk_modes_complete['events'] = True
                        logger.info(f"=== EVENTS BULK COMPLETE: Added {self.events_added} ===")

                    except Exception as e:
                        logger.error(f"Event bulk discovery failed: {e}", exc_info=True)

                elif not self.bulk_modes_complete['videogames']:
                    try:
                        logger.info("=== BULK MODE: Discovering video games ===")
                        games = self.bulk_videogame_scraper.discover_all()

                        errors = 0
                        for game_data in games:
                            try:
                                result = self.api_client.create_videogame(game_data)
                                if result:
                                    self.videogames_added += 1
                            except Exception as e:
                                errors += 1
                                if errors <= 5:
                                    logger.warning(
                                        f"Failed to create video game {game_data.get('name')}: {e}"
                                    )

                        if errors:
                            logger.warning(f"Video game bulk had {errors} errors")

                        self.bulk_modes_complete['videogames'] = True
                        logger.info(f"=== VIDEO GAMES BULK COMPLETE: Added {self.videogames_added} ===")

                    except Exception as e:
                        logger.error(f"Video game bulk discovery failed: {e}", exc_info=True)

                elif not self.bulk_modes_complete['books']:
                    try:
                        logger.info("=== BULK MODE: Discovering books ===")
                        books = self.bulk_book_scraper.discover_all()

                        errors = 0
                        for book_data in books:
                            try:
                                result = self.api_client.create_book(book_data)
                                if result:
                                    self.books_added += 1
                            except Exception as e:
                                errors += 1
                                if errors <= 5:
                                    logger.warning(
                                        f"Failed to create book {book_data.get('title')}: {e}"
                                    )

                        if errors:
                            logger.warning(f"Book bulk had {errors} errors")

                        self.bulk_modes_complete['books'] = True
                        logger.info(f"=== BOOKS BULK COMPLETE: Added {self.books_added} ===")

                    except Exception as e:
                        logger.error(f"Book bulk discovery failed: {e}", exc_info=True)

                elif not self.bulk_modes_complete['documentaries']:
                    try:
                        logger.info("=== BULK MODE: Discovering documentaries ===")
                        docs = self.bulk_documentary_scraper.discover_all()

                        errors = 0
                        for doc_data in docs:
                            try:
                                result = self.api_client.create_special(doc_data)
                                if result:
                                    self.documentaries_added += 1
                            except Exception as e:
                                errors += 1
                                if errors <= 5:
                                    logger.warning(
                                        f"Failed to create documentary {doc_data.get('title')}: {e}"
                                    )

                        if errors:
                            logger.warning(f"Documentary bulk had {errors} errors")

                        self.bulk_modes_complete['documentaries'] = True
                        logger.info(f"=== DOCUMENTARIES BULK COMPLETE: Added {self.documentaries_added} ===")

                    except Exception as e:
                        logger.error(f"Documentary bulk discovery failed: {e}", exc_info=True)

                # Run incremental page enrichment after all bulk modes complete
                # Every cycle (15 seconds) - enrich one page
                elif all(self.bulk_modes_complete.values()):
                    try:
                        logger.info("=== PAGE ENRICHMENT CYCLE ===")

                        # Get a random wrestling-related Wikipedia page
                        page = self.page_enrichment.get_random_incomplete_page()

                        if page and 'content' in page:
                            # Analyze page for missing entities
                            logger.info(f"Analyzing: {page.get('title', 'Unknown')}")
                            mentioned = self.page_enrichment.analyze_page_for_missing_entities(
                                page.get('type', 'wrestler'),
                                {'about': page['content']}
                            )

                            # Process discovered entities - try multiple types, not just first wrestler
                            entity_created = False

                            # Try wrestlers first (up to 3 attempts)
                            for wrestler_name in list(mentioned.get('wrestlers', []))[:3]:
                                if entity_created:
                                    break
                                logger.info(f"Found mentioned wrestler: {wrestler_name}")

                                # Try to create/enrich this wrestler
                                result = self.page_enrichment.create_or_update_entity('wrestler', wrestler_name)
                                if result:
                                    self.entities_enriched += 1
                                    # Check HTTP status to determine if new or updated
                                    if result.get('_http_status') == 201:
                                        self.wrestlers_added += 1
                                        logger.info(f"✓ Created NEW wrestler: {wrestler_name}")
                                    else:
                                        logger.info(f"✓ Updated existing wrestler: {wrestler_name}")
                                    entity_created = True

                            # Try promotions if no wrestler was created (up to 2 attempts)
                            if not entity_created:
                                for promotion_name in list(mentioned.get('promotions', []))[:2]:
                                    logger.info(f"Found mentioned promotion: {promotion_name}")
                                    result = self.page_enrichment.create_or_update_entity('promotion', promotion_name)
                                    if result:
                                        self.entities_enriched += 1
                                        if result.get('_http_status') == 201:
                                            logger.info(f"✓ Created NEW promotion: {promotion_name}")
                                        else:
                                            logger.info(f"✓ Updated existing promotion: {promotion_name}")
                                        entity_created = True
                                        break

                            # Try events if nothing else was created (up to 2 attempts)
                            if not entity_created:
                                for event_name in list(mentioned.get('events', []))[:2]:
                                    logger.info(f"Found mentioned event: {event_name}")
                                    result = self.page_enrichment.create_or_update_entity('event', event_name)
                                    if result:
                                        self.entities_enriched += 1
                                        if result.get('_http_status') == 201:
                                            logger.info(f"✓ Created NEW event: {event_name}")
                                        else:
                                            logger.info(f"✓ Updated existing event: {event_name}")
                                        entity_created = True
                                        break

                            # Try stables if nothing else was created
                            if not entity_created:
                                for stable_name in list(mentioned.get('stables', []))[:2]:
                                    logger.info(f"Found mentioned stable: {stable_name}")
                                    result = self.page_enrichment.create_or_update_entity('stable', stable_name)
                                    if result:
                                        self.entities_enriched += 1
                                        if result.get('_http_status') == 201:
                                            logger.info(f"✓ Created NEW stable: {stable_name}")
                                        else:
                                            logger.info(f"✓ Updated existing stable: {stable_name}")
                                        entity_created = True
                                        break

                            # Try titles if nothing else was created
                            if not entity_created:
                                for title_name in list(mentioned.get('titles', []))[:2]:
                                    logger.info(f"Found mentioned title: {title_name}")
                                    result = self.page_enrichment.create_or_update_entity('title', title_name)
                                    if result:
                                        self.entities_enriched += 1
                                        if result.get('_http_status') == 201:
                                            logger.info(f"✓ Created NEW title: {title_name}")
                                        else:
                                            logger.info(f"✓ Updated existing title: {title_name}")
                                        entity_created = True
                                        break

                            # Try venues if nothing else was created
                            if not entity_created:
                                for venue_name in list(mentioned.get('venues', []))[:2]:
                                    logger.info(f"Found mentioned venue: {venue_name}")
                                    result = self.page_enrichment.create_or_update_entity('venue', venue_name)
                                    if result:
                                        self.entities_enriched += 1
                                        if result.get('_http_status') == 201:
                                            logger.info(f"✓ Created NEW venue: {venue_name}")
                                        else:
                                            logger.info(f"✓ Updated existing venue: {venue_name}")
                                        entity_created = True
                                        break

                        else:
                            # Try autonomous quality improvement first
                            logger.info("Running autonomous quality improvement cycle...")
                            improved = self.page_enrichment.find_and_enrich_incomplete_entries()

                            if improved > 0:
                                self.entities_enriched += improved
                                logger.info(f"✓ Autonomously improved {improved} entries")
                            else:
                                # Fallback to direct wrestler discovery
                                logger.info("No entries to improve, trying direct discovery...")
                                wrestlers = self.scraper.discover_wrestlers(max_wrestlers=1)
                                if wrestlers:
                                    for wrestler_data in wrestlers:
                                        try:
                                            result = self.api_client.create_wrestler(wrestler_data)
                                            if result:
                                                if result.get('_http_status') == 201:
                                                    self.wrestlers_added += 1
                                                    logger.info(f"✓ Created NEW wrestler: {wrestler_data['name']}")
                                                else:
                                                    logger.info(f"✓ Updated existing wrestler: {wrestler_data['name']}")
                                        except Exception as e:
                                            pass

                    except Exception as e:
                        logger.error(f"Enrichment cycle failed: {e}", exc_info=True)

                # Sleep 15 seconds between enrichment cycles
                logger.info(f"Total enriched: {self.entities_enriched} | Sleeping 15 seconds...")
                time.sleep(15)

            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                # Don't crash, just log and continue
                time.sleep(10)

        logger.info("Service loop ended")

    def shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down WrestleBot service...")

        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()
            logger.info(f"Total uptime: {uptime:.0f} seconds")
            logger.info(f"Total entities added:")
            logger.info(f"  Wrestlers: {self.wrestlers_added}")
            logger.info(f"  Promotions: {self.promotions_added}")
            logger.info(f"  Events: {self.events_added}")
            logger.info(f"  Video Games: {self.videogames_added}")
            logger.info(f"  Books: {self.books_added}")
            logger.info(f"  Documentaries: {self.documentaries_added}")
            logger.info(f"  Pages Enriched: {self.entities_enriched}")

        logger.info("Shutdown complete")


def main():
    """Main entry point."""
    service = WrestleBotService()

    try:
        service.initialize()
        service.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        service.shutdown()


if __name__ == '__main__':
    main()
