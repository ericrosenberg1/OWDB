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
        self.start_time = None

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

                # TODO: Add actual scraping logic here
                # For now, just demonstrate the service is running

                # Example: Create a test article (commented out)
                # article_data = {
                #     "title": f"Test Article {cycle}",
                #     "slug": f"test-article-{cycle}",
                #     "content": "This is a test article from WrestleBot standalone service",
                #     "category": "news",
                #     "author": "WrestleBot"
                # }
                # result = self.api_client.create_article(article_data)
                # if result:
                #     logger.info(f"Created article: {result.get('id')}")

                # Sleep between cycles (5 seconds for testing, will be configurable)
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
