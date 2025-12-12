"""
Base scraper classes with rate limiting, robots.txt compliance, and error handling.
"""

import hashlib
import logging
import random
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using token bucket algorithm with Redis-backed state.
    Ensures we respect API limits across all workers.
    """

    def __init__(
        self,
        name: str,
        requests_per_minute: int = 10,
        requests_per_hour: int = 100,
        requests_per_day: int = 1000,
    ):
        self.name = name
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.rpd = requests_per_day
        self.cache_prefix = f"scraper_ratelimit_{name}"

    def _get_counts(self) -> Tuple[int, int, int]:
        """Get current request counts from cache."""
        minute_key = f"{self.cache_prefix}_minute_{int(time.time() // 60)}"
        hour_key = f"{self.cache_prefix}_hour_{int(time.time() // 3600)}"
        day_key = f"{self.cache_prefix}_day_{int(time.time() // 86400)}"

        return (
            cache.get(minute_key, 0),
            cache.get(hour_key, 0),
            cache.get(day_key, 0),
        )

    def _increment(self):
        """Increment request counts."""
        now = int(time.time())
        minute_key = f"{self.cache_prefix}_minute_{now // 60}"
        hour_key = f"{self.cache_prefix}_hour_{now // 3600}"
        day_key = f"{self.cache_prefix}_day_{now // 86400}"

        # Increment with appropriate TTLs
        for key, ttl in [(minute_key, 120), (hour_key, 7200), (day_key, 172800)]:
            current = cache.get(key, 0)
            cache.set(key, current + 1, timeout=ttl)

    def can_request(self) -> Tuple[bool, Optional[int]]:
        """
        Check if a request can be made.
        Returns (can_request, wait_seconds) tuple.
        """
        minute_count, hour_count, day_count = self._get_counts()

        if day_count >= self.rpd:
            # Wait until next day
            seconds_until_midnight = 86400 - (int(time.time()) % 86400)
            return False, seconds_until_midnight

        if hour_count >= self.rph:
            # Wait until next hour
            seconds_until_hour = 3600 - (int(time.time()) % 3600)
            return False, seconds_until_hour

        if minute_count >= self.rpm:
            # Wait until next minute
            seconds_until_minute = 60 - (int(time.time()) % 60)
            return False, seconds_until_minute

        return True, None

    def acquire(self, timeout: int = 300) -> bool:
        """
        Acquire permission to make a request, waiting if necessary.
        Returns True if acquired, False if timeout exceeded.
        """
        start_time = time.time()

        while True:
            can_req, wait_time = self.can_request()

            if can_req:
                self._increment()
                return True

            if time.time() - start_time + (wait_time or 0) > timeout:
                return False

            # Wait with jitter to avoid thundering herd
            sleep_time = min(wait_time or 60, timeout - (time.time() - start_time))
            if sleep_time > 0:
                time.sleep(sleep_time + random.uniform(0, 1))

    def get_stats(self) -> Dict[str, Any]:
        """Get current rate limit statistics."""
        minute_count, hour_count, day_count = self._get_counts()
        return {
            "name": self.name,
            "minute": {"current": minute_count, "limit": self.rpm},
            "hour": {"current": hour_count, "limit": self.rph},
            "day": {"current": day_count, "limit": self.rpd},
        }


class RobotsChecker:
    """
    Checks robots.txt compliance for URLs.
    Caches robots.txt files to avoid repeated fetches.
    """

    CACHE_TTL = 86400  # 24 hours

    def __init__(self, user_agent: str = "OWDBBot/1.0"):
        self.user_agent = user_agent
        self._parsers: Dict[str, RobotFileParser] = {}

    def _get_robots_url(self, url: str) -> str:
        """Get the robots.txt URL for a given URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _get_parser(self, url: str) -> Optional[RobotFileParser]:
        """Get or fetch the robots.txt parser for a URL."""
        robots_url = self._get_robots_url(url)
        cache_key = f"robots_txt_{hashlib.md5(robots_url.encode()).hexdigest()}"

        # Check memory cache first
        if robots_url in self._parsers:
            return self._parsers[robots_url]

        # Check Redis cache
        cached_content = cache.get(cache_key)
        if cached_content is not None:
            parser = RobotFileParser()
            parser.parse(cached_content.split("\n"))
            self._parsers[robots_url] = parser
            return parser

        # Fetch robots.txt
        try:
            response = requests.get(
                robots_url,
                headers={"User-Agent": self.user_agent},
                timeout=10,
            )

            if response.status_code == 200:
                content = response.text
                cache.set(cache_key, content, timeout=self.CACHE_TTL)

                parser = RobotFileParser()
                parser.parse(content.split("\n"))
                self._parsers[robots_url] = parser
                return parser
            elif response.status_code == 404:
                # No robots.txt means everything is allowed
                cache.set(cache_key, "", timeout=self.CACHE_TTL)
                return None

        except requests.RequestException as e:
            logger.warning(f"Failed to fetch robots.txt from {robots_url}: {e}")
            return None

        return None

    def can_fetch(self, url: str) -> bool:
        """Check if the URL can be fetched according to robots.txt."""
        parser = self._get_parser(url)
        if parser is None:
            return True  # No robots.txt or error, assume allowed
        return parser.can_fetch(self.user_agent, url)

    def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get the crawl delay from robots.txt."""
        parser = self._get_parser(url)
        if parser is None:
            return None
        try:
            delay = parser.crawl_delay(self.user_agent)
            return float(delay) if delay else None
        except AttributeError:
            return None


class ScraperUnavailableError(Exception):
    """Raised when a scraper source is completely unavailable (e.g., SSL errors, site down)."""
    pass


class BaseScraper(ABC):
    """
    Abstract base class for all scrapers.
    Implements rate limiting, robots.txt compliance, and common utilities.
    """

    # Override in subclasses
    SOURCE_NAME: str = "base"
    BASE_URL: str = ""
    USER_AGENT: str = "OWDBBot/1.0 (+https://wrestlingdb.org/about/bot)"

    # Default rate limits (conservative)
    REQUESTS_PER_MINUTE: int = 10
    REQUESTS_PER_HOUR: int = 100
    REQUESTS_PER_DAY: int = 1000

    # Request settings
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0

    # Circuit breaker settings - stop if too many consecutive failures
    MAX_CONSECUTIVE_FAILURES: int = 5

    def __init__(self):
        self.rate_limiter = RateLimiter(
            name=self.SOURCE_NAME,
            requests_per_minute=self.REQUESTS_PER_MINUTE,
            requests_per_hour=self.REQUESTS_PER_HOUR,
            requests_per_day=self.REQUESTS_PER_DAY,
        )
        self.robots_checker = RobotsChecker(user_agent=self.USER_AGENT)
        self.session = self._create_session()
        self._last_request_time = 0
        self._consecutive_failures = 0
        self._is_unavailable = False

    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            }
        )
        return session

    def _respect_crawl_delay(self, url: str):
        """Wait for the appropriate crawl delay."""
        delay = self.robots_checker.get_crawl_delay(url)
        if delay:
            min_delay = delay
        else:
            # Default minimum delay between requests
            min_delay = 1.0

        elapsed = time.time() - self._last_request_time
        if elapsed < min_delay:
            time.sleep(min_delay - elapsed + random.uniform(0, 0.5))

    def _check_circuit_breaker(self):
        """Check if the scraper should stop due to too many failures."""
        if self._is_unavailable:
            raise ScraperUnavailableError(
                f"{self.SOURCE_NAME} is unavailable after {self.MAX_CONSECUTIVE_FAILURES} consecutive failures"
            )

    def _record_success(self):
        """Record a successful request and reset failure counter."""
        self._consecutive_failures = 0

    def _record_failure(self, is_fatal: bool = False):
        """
        Record a failed request.

        Args:
            is_fatal: If True (e.g., SSL errors), immediately mark as unavailable
        """
        self._consecutive_failures += 1
        if is_fatal or self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            self._is_unavailable = True
            logger.error(
                f"{self.SOURCE_NAME} marked as unavailable after "
                f"{self._consecutive_failures} consecutive failures"
            )

    def _is_fatal_error(self, error: Exception) -> bool:
        """Check if an error indicates the source is completely unavailable."""
        error_str = str(error).lower()
        fatal_indicators = [
            'ssl',
            'certificate',
            'handshake',
            'connection refused',
            'name or service not known',
            'no route to host',
        ]
        return any(indicator in error_str for indicator in fatal_indicators)

    def fetch(self, url: str, allow_redirects: bool = True) -> Optional[requests.Response]:
        """
        Fetch a URL with rate limiting and robots.txt compliance.
        Returns None if the request fails or is not allowed.
        Raises ScraperUnavailableError if the source is completely unavailable.
        """
        # Check circuit breaker first
        self._check_circuit_breaker()

        # Check robots.txt
        if not self.robots_checker.can_fetch(url):
            logger.info(f"Robots.txt disallows fetching: {url}")
            return None

        # Acquire rate limit permission
        if not self.rate_limiter.acquire(timeout=300):
            logger.warning(f"Rate limit timeout for {self.SOURCE_NAME}")
            return None

        # Respect crawl delay
        self._respect_crawl_delay(url)

        # Make request with retries
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                self._last_request_time = time.time()
                response = self.session.get(
                    url,
                    timeout=self.REQUEST_TIMEOUT,
                    allow_redirects=allow_redirects,
                )
                response.raise_for_status()
                self._record_success()
                return response

            except requests.RequestException as e:
                last_error = e
                wait_time = self.RETRY_BACKOFF ** attempt
                logger.warning(
                    f"Request failed for {url} (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}"
                )

                # Check for fatal errors (SSL, DNS, etc.) - don't retry these
                if self._is_fatal_error(e):
                    logger.error(f"Fatal error for {self.SOURCE_NAME}: {e}")
                    self._record_failure(is_fatal=True)
                    raise ScraperUnavailableError(
                        f"{self.SOURCE_NAME} unavailable: {e}"
                    )

                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(wait_time)

        # All retries failed
        self._record_failure()
        self._check_circuit_breaker()
        return None

    def get_cached_or_fetch(
        self, url: str, cache_ttl: int = 3600
    ) -> Optional[str]:
        """
        Get page content from cache or fetch it.
        Returns the HTML content or None.
        """
        cache_key = f"scraper_page_{hashlib.md5(url.encode()).hexdigest()}"
        cached = cache.get(cache_key)

        if cached is not None:
            logger.debug(f"Cache hit for {url}")
            return cached

        response = self.fetch(url)
        if response is None:
            return None

        content = response.text
        cache.set(cache_key, content, timeout=cache_ttl)
        return content

    @abstractmethod
    def scrape_wrestlers(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape wrestler data. Override in subclasses."""
        pass

    @abstractmethod
    def scrape_promotions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape promotion data. Override in subclasses."""
        pass

    @abstractmethod
    def scrape_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Scrape event data. Override in subclasses."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get scraper statistics."""
        return {
            "source": self.SOURCE_NAME,
            "rate_limits": self.rate_limiter.get_stats(),
        }


def retry_on_failure(max_retries: int = 3, backoff: float = 2.0):
    """Decorator for retrying failed operations."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff ** attempt
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt + 1}): {e}, "
                            f"retrying in {wait_time}s"
                        )
                        time.sleep(wait_time)
            raise last_exception

        return wrapper

    return decorator
