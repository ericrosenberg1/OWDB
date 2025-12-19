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
        self.start_time = None
        self.wrestlers_added = 0
        self.bulk_mode_complete = False

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
            logger.info("Wikipedia scrapers initialized")
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
                if not self.api_client.health_check():
                    logger.warning("API health check failed, will retry next cycle")
                else:
                    logger.info("API health check: OK")

                # Run bulk discovery on first cycle
                if cycle == 1 and not self.bulk_mode_complete:
                    try:
                        logger.info("=== BULK MODE: Discovering ALL wrestlers from Wikipedia ===")

                        # Get all wrestler names from categories
                        all_names = self.bulk_scraper.discover_all_wrestlers()
                        logger.info(f"Discovered {len(all_names)} unique wrestler names")

                        # Process in batches
                        batch_size = 100
                        for i in range(0, min(len(all_names), 1000), batch_size):  # Limit to 1000 for now
                            batch_names = all_names[i:i + batch_size]
                            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_names)} wrestlers")

                            # Get details for batch
                            wrestlers = self.bulk_scraper.get_wrestler_details_batch(batch_names)

                            # Add to database
                            for wrestler_data in wrestlers:
                                try:
                                    result = self.api_client.create_wrestler(wrestler_data)
                                    if result:
                                        self.wrestlers_added += 1
                                        if self.wrestlers_added % 10 == 0:
                                            logger.info(f"Progress: {self.wrestlers_added} wrestlers added")
                                except Exception as e:
                                    # Don't log every error, just continue
                                    pass

                        self.bulk_mode_complete = True
                        logger.info(f"=== BULK MODE COMPLETE: Added {self.wrestlers_added} wrestlers ===")

                    except Exception as e:
                        logger.error(f"Bulk discovery failed: {e}", exc_info=True)
                        self.bulk_mode_complete = True  # Don't retry

                # Run incremental scraping after bulk mode
                elif self.bulk_mode_complete and cycle % 10 == 1:
                    try:
                        logger.info("Starting incremental scraping cycle...")

                        # Discover new wrestlers from Wikipedia
                        wrestlers = self.scraper.discover_wrestlers(max_wrestlers=5)

                        if wrestlers:
                            logger.info(f"Discovered {len(wrestlers)} wrestlers, adding to database...")

                            for wrestler_data in wrestlers:
                                try:
                                    result = self.api_client.create_wrestler(wrestler_data)
                                    if result:
                                        self.wrestlers_added += 1
                                        logger.info(f"✓ Added wrestler: {wrestler_data['name']}")
                                except Exception as e:
                                    pass
                        else:
                            logger.info("No new wrestlers discovered this cycle")

                    except Exception as e:
                        logger.error(f"Scraping cycle failed: {e}", exc_info=True)

                # Sleep between cycles
                logger.info("Sleeping for 5 seconds...")
                time.sleep(5)

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
            logger.info(f"Total wrestlers added: {self.wrestlers_added}")

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
