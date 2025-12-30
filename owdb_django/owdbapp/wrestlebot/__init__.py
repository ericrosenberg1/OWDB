"""
WrestleBot 2.0 - Autonomous Data Enhancement Service

A lightweight, autonomous service that continuously improves the wrestling database by:
1. Discovery - Adding new entries (wrestlers, events, promotions, etc.)
2. Enrichment - Adding more details to incomplete entries
3. Quality - Improving accuracy through cross-source verification

Components:
- bot.py: Main orchestrator
- discovery.py: Find new entities to add
- enrichment.py: Improve existing entries
- scoring.py: Completeness scoring system
- ai_enhancer.py: Optional Claude API integration
- models.py: Activity tracking
"""

from .bot import WrestleBot
from .scoring import CompletenessScorer
from .discovery import EntityDiscovery
from .enrichment import EntityEnrichment


class ScraperProvider:
    """
    Provides lazy-loaded, shared scraper instances.

    Consolidates the lazy loading pattern used across WrestleBot modules.
    Scrapers are expensive to initialize and should be shared.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._wikipedia_scraper = None
            cls._instance._cagematch_scraper = None
            cls._instance._wikimedia_client = None
            cls._instance._coordinator = None
        return cls._instance

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

    @property
    def wikimedia_client(self):
        """Lazy load Wikimedia Commons client."""
        if self._wikimedia_client is None:
            from ..scrapers.wikimedia_commons import WikimediaCommonsClient
            self._wikimedia_client = WikimediaCommonsClient()
        return self._wikimedia_client

    @property
    def coordinator(self):
        """Lazy load scraper coordinator."""
        if self._coordinator is None:
            from ..scrapers.coordinator import ScraperCoordinator
            self._coordinator = ScraperCoordinator()
        return self._coordinator


__all__ = [
    'WrestleBot',
    'CompletenessScorer',
    'EntityDiscovery',
    'EntityEnrichment',
    'ScraperProvider',
]
