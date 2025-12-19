"""
Source Rotator - Intelligent multi-source scraping with rate limit handling.

This module manages multiple data sources and automatically rotates between them
when rate limits are hit, ensuring continuous data collection without delays.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum

from django.core.cache import cache

logger = logging.getLogger(__name__)


class SourceStatus(Enum):
    """Status of a data source."""
    AVAILABLE = "available"
    RATE_LIMITED = "rate_limited"
    UNAVAILABLE = "unavailable"
    COOLDOWN = "cooldown"


@dataclass
class SourceState:
    """Tracks the state of a single data source."""
    name: str
    priority: int = 1  # Lower = higher priority
    status: SourceStatus = SourceStatus.AVAILABLE
    available_at: Optional[datetime] = None
    consecutive_failures: int = 0
    requests_made: int = 0
    last_success: Optional[datetime] = None

    def is_available(self) -> bool:
        """Check if the source is available for requests."""
        if self.status == SourceStatus.UNAVAILABLE:
            return False
        if self.status in (SourceStatus.RATE_LIMITED, SourceStatus.COOLDOWN):
            if self.available_at and datetime.now() < self.available_at:
                return False
            # Time has passed, reset to available
            self.status = SourceStatus.AVAILABLE
            self.available_at = None
        return True

    def mark_rate_limited(self, cooldown_seconds: int = 300):
        """Mark the source as rate limited."""
        self.status = SourceStatus.RATE_LIMITED
        self.available_at = datetime.now() + timedelta(seconds=cooldown_seconds)
        logger.info(f"Source {self.name} rate limited, available at {self.available_at}")

    def mark_success(self):
        """Mark a successful request."""
        self.status = SourceStatus.AVAILABLE
        self.consecutive_failures = 0
        self.requests_made += 1
        self.last_success = datetime.now()

    def mark_failure(self, is_fatal: bool = False):
        """Mark a failed request."""
        self.consecutive_failures += 1
        if is_fatal or self.consecutive_failures >= 5:
            self.status = SourceStatus.UNAVAILABLE
            logger.warning(f"Source {self.name} marked unavailable after {self.consecutive_failures} failures")
        else:
            # Short cooldown after non-fatal failure
            self.status = SourceStatus.COOLDOWN
            self.available_at = datetime.now() + timedelta(seconds=30)


class SourceRotator:
    """
    Manages rotation between multiple data sources for resilient scraping.

    When one source hits rate limits, automatically switches to alternative
    sources and returns to the original source when cooldown expires.
    """

    CACHE_KEY_PREFIX = "source_rotator_"

    def __init__(self, entity_type: str):
        """
        Initialize the rotator for a specific entity type.

        Args:
            entity_type: The type of entity being scraped (wrestlers, promotions, etc.)
        """
        self.entity_type = entity_type
        self.sources: Dict[str, SourceState] = {}
        self._load_state()

    def _cache_key(self) -> str:
        """Get the cache key for this rotator's state."""
        return f"{self.CACHE_KEY_PREFIX}{self.entity_type}"

    def _load_state(self):
        """Load source states from cache."""
        cached = cache.get(self._cache_key())
        if cached:
            for name, data in cached.items():
                self.sources[name] = SourceState(
                    name=name,
                    priority=data.get('priority', 1),
                    status=SourceStatus(data.get('status', 'available')),
                    available_at=data.get('available_at'),
                    consecutive_failures=data.get('consecutive_failures', 0),
                    requests_made=data.get('requests_made', 0),
                )

    def _save_state(self):
        """Save source states to cache."""
        data = {}
        for name, state in self.sources.items():
            data[name] = {
                'priority': state.priority,
                'status': state.status.value,
                'available_at': state.available_at,
                'consecutive_failures': state.consecutive_failures,
                'requests_made': state.requests_made,
            }
        cache.set(self._cache_key(), data, timeout=3600)  # 1 hour

    def register_source(self, name: str, priority: int = 1):
        """
        Register a data source with the rotator.

        Args:
            name: Unique identifier for the source
            priority: Lower number = higher priority (default sources first)
        """
        if name not in self.sources:
            self.sources[name] = SourceState(name=name, priority=priority)
            logger.debug(f"Registered source: {name} (priority {priority})")

    def get_next_source(self) -> Optional[str]:
        """
        Get the next available source, respecting priority and rate limits.

        Returns:
            Source name or None if all sources are rate limited/unavailable
        """
        available = [
            (name, state) for name, state in self.sources.items()
            if state.is_available()
        ]

        if not available:
            # Find the source that will be available soonest
            rate_limited = [
                (name, state) for name, state in self.sources.items()
                if state.status == SourceStatus.RATE_LIMITED and state.available_at
            ]
            if rate_limited:
                soonest = min(rate_limited, key=lambda x: x[1].available_at)
                wait_time = (soonest[1].available_at - datetime.now()).total_seconds()
                if wait_time > 0 and wait_time < 60:
                    logger.info(f"Waiting {wait_time:.0f}s for {soonest[0]} to become available")
                    time.sleep(wait_time + 1)
                    soonest[1].status = SourceStatus.AVAILABLE
                    return soonest[0]
            logger.warning(f"No available sources for {self.entity_type}")
            return None

        # Sort by priority (lower is better), then by requests made (load balancing)
        available.sort(key=lambda x: (x[1].priority, x[1].requests_made))
        return available[0][0]

    def mark_rate_limited(self, source_name: str, cooldown_seconds: int = 300):
        """Mark a source as rate limited and trigger rotation."""
        if source_name in self.sources:
            self.sources[source_name].mark_rate_limited(cooldown_seconds)
            self._save_state()

    def mark_success(self, source_name: str):
        """Mark a successful request to a source."""
        if source_name in self.sources:
            self.sources[source_name].mark_success()
            self._save_state()

    def mark_failure(self, source_name: str, is_fatal: bool = False):
        """Mark a failed request to a source."""
        if source_name in self.sources:
            self.sources[source_name].mark_failure(is_fatal)
            self._save_state()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all sources."""
        return {
            name: {
                'status': state.status.value,
                'available': state.is_available(),
                'requests_made': state.requests_made,
                'consecutive_failures': state.consecutive_failures,
                'available_at': state.available_at.isoformat() if state.available_at else None,
                'last_success': state.last_success.isoformat() if state.last_success else None,
            }
            for name, state in self.sources.items()
        }

    def reset_all(self):
        """Reset all sources to available status."""
        for state in self.sources.values():
            state.status = SourceStatus.AVAILABLE
            state.available_at = None
            state.consecutive_failures = 0
        self._save_state()


class MultiSourceScraper:
    """
    Scraper that automatically rotates between multiple sources.

    Usage:
        scraper = MultiSourceScraper('wrestlers')
        scraper.register('wikipedia', WikipediaScraper(), priority=1)
        scraper.register('cagematch', CagematchScraper(), priority=2)
        scraper.register('profightdb', ProFightDBScraper(), priority=3)

        # Will automatically use wikipedia first, rotate to cagematch if rate limited
        wrestlers = scraper.scrape(method='scrape_wrestlers', limit=50)
    """

    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.rotator = SourceRotator(entity_type)
        self.scrapers: Dict[str, Any] = {}

    def register(self, name: str, scraper: Any, priority: int = 1):
        """Register a scraper with the multi-source system."""
        self.scrapers[name] = scraper
        self.rotator.register_source(name, priority)

    def scrape(
        self,
        method: str,
        limit: int = 50,
        merge_results: bool = True,
        max_sources: int = 3,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Scrape data using available sources with automatic rotation.

        Args:
            method: The scraper method to call (e.g., 'scrape_wrestlers')
            limit: Maximum items to return
            merge_results: Whether to combine results from multiple sources
            max_sources: Maximum number of sources to try
            **kwargs: Additional arguments to pass to the scraper method

        Returns:
            List of scraped items
        """
        all_results = []
        sources_tried = 0
        items_needed = limit

        while items_needed > 0 and sources_tried < max_sources:
            source_name = self.rotator.get_next_source()
            if not source_name:
                break

            scraper = self.scrapers.get(source_name)
            if not scraper:
                continue

            sources_tried += 1

            try:
                # Call the scraper method
                scrape_fn = getattr(scraper, method, None)
                if not scrape_fn:
                    logger.warning(f"Source {source_name} has no method {method}")
                    continue

                results = scrape_fn(limit=items_needed, **kwargs)

                if results:
                    all_results.extend(results)
                    self.rotator.mark_success(source_name)
                    items_needed = limit - len(all_results) if merge_results else 0
                    logger.info(f"Got {len(results)} items from {source_name}")
                else:
                    # Empty results might indicate rate limiting
                    self.rotator.mark_rate_limited(source_name, cooldown_seconds=180)

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limit indicators
                if any(ind in error_str for ind in ['rate limit', '429', 'too many requests']):
                    self.rotator.mark_rate_limited(source_name, cooldown_seconds=300)
                    logger.info(f"Rate limit detected for {source_name}, rotating...")
                elif any(ind in error_str for ind in ['ssl', 'connection', 'timeout']):
                    self.rotator.mark_failure(source_name, is_fatal=True)
                else:
                    self.rotator.mark_failure(source_name)

                logger.warning(f"Error from {source_name}: {e}")
                continue

            if not merge_results:
                break

        return all_results[:limit]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all registered sources."""
        return self.rotator.get_stats()


# Pre-configured multi-source scrapers for common entity types
def get_wrestler_scraper() -> MultiSourceScraper:
    """Get a pre-configured multi-source scraper for wrestlers."""
    from .wikipedia import WikipediaScraper
    from .cagematch import CagematchScraper
    from .profightdb import ProFightDBScraper

    scraper = MultiSourceScraper('wrestlers')
    scraper.register('wikipedia', WikipediaScraper(), priority=1)
    scraper.register('cagematch', CagematchScraper(), priority=2)
    scraper.register('profightdb', ProFightDBScraper(), priority=3)
    return scraper


def get_promotion_scraper() -> MultiSourceScraper:
    """Get a pre-configured multi-source scraper for promotions."""
    from .wikipedia import WikipediaScraper
    from .cagematch import CagematchScraper

    scraper = MultiSourceScraper('promotions')
    scraper.register('wikipedia', WikipediaScraper(), priority=1)
    scraper.register('cagematch', CagematchScraper(), priority=2)
    return scraper


def get_event_scraper() -> MultiSourceScraper:
    """Get a pre-configured multi-source scraper for events."""
    from .wikipedia import WikipediaScraper
    from .cagematch import CagematchScraper
    from .profightdb import ProFightDBScraper

    scraper = MultiSourceScraper('events')
    scraper.register('cagematch', CagematchScraper(), priority=1)  # Cagematch best for events
    scraper.register('profightdb', ProFightDBScraper(), priority=2)
    scraper.register('wikipedia', WikipediaScraper(), priority=3)
    return scraper
