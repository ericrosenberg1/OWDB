"""
Centralized API client with rate limiting, caching, and error handling.

This module provides a unified interface for all external API calls with:
- Automatic rate limiting per API
- Response caching
- Retry logic with exponential backoff
- Comprehensive error handling and logging
- Circuit breaker pattern for failing APIs
"""

import hashlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

T = TypeVar('T')


class APIStatus(Enum):
    """API health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class APIError:
    """Represents an API error for reporting."""
    api_name: str
    endpoint: str
    error_type: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_code: Optional[int] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_name": self.api_name,
            "endpoint": self.endpoint,
            "error_type": self.error_type,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "response_code": self.response_code,
            "retry_count": self.retry_count,
        }


class ErrorReporter:
    """Collects and reports API errors."""

    CACHE_KEY = "api_errors"
    MAX_ERRORS = 100

    @classmethod
    def report(cls, error: APIError):
        """Report an API error."""
        errors = cache.get(cls.CACHE_KEY, [])
        errors.append(error.to_dict())

        # Keep only recent errors
        if len(errors) > cls.MAX_ERRORS:
            errors = errors[-cls.MAX_ERRORS:]

        cache.set(cls.CACHE_KEY, errors, timeout=86400)  # 24 hours
        logger.warning(
            f"API Error [{error.api_name}] {error.error_type}: {error.message}"
        )

    @classmethod
    def get_errors(cls, api_name: Optional[str] = None) -> List[Dict]:
        """Get reported errors, optionally filtered by API."""
        errors = cache.get(cls.CACHE_KEY, [])
        if api_name:
            errors = [e for e in errors if e["api_name"] == api_name]
        return errors

    @classmethod
    def clear_errors(cls, api_name: Optional[str] = None):
        """Clear errors, optionally for a specific API."""
        if api_name:
            errors = cache.get(cls.CACHE_KEY, [])
            errors = [e for e in errors if e["api_name"] != api_name]
            cache.set(cls.CACHE_KEY, errors, timeout=86400)
        else:
            cache.delete(cls.CACHE_KEY)


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent hammering failing APIs.

    States:
    - CLOSED: Normal operation
    - OPEN: API is failing, reject requests immediately
    - HALF_OPEN: Testing if API has recovered
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 300,  # 5 minutes
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._cache_key = f"circuit_breaker_{name}"

    def _get_state(self) -> Dict:
        """Get current circuit breaker state."""
        return cache.get(self._cache_key, {
            "failures": 0,
            "state": "closed",
            "last_failure": None,
        })

    def _set_state(self, state: Dict):
        """Set circuit breaker state."""
        cache.set(self._cache_key, state, timeout=86400)

    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""
        state = self._get_state()

        if state["state"] == "closed":
            return False

        if state["state"] == "open":
            # Check if we should transition to half-open
            last_failure = state.get("last_failure")
            if last_failure:
                elapsed = time.time() - last_failure
                if elapsed >= self.recovery_timeout:
                    state["state"] = "half_open"
                    self._set_state(state)
                    return False
            return True

        return False  # half-open allows requests

    def record_success(self):
        """Record a successful request."""
        state = self._get_state()
        state["failures"] = 0
        state["state"] = "closed"
        self._set_state(state)

    def record_failure(self):
        """Record a failed request."""
        state = self._get_state()
        state["failures"] = state.get("failures", 0) + 1
        state["last_failure"] = time.time()

        if state["failures"] >= self.failure_threshold:
            state["state"] = "open"
            logger.warning(f"Circuit breaker OPEN for {self.name}")

        self._set_state(state)

    def get_status(self) -> APIStatus:
        """Get current API status based on circuit state."""
        state = self._get_state()
        if state["state"] == "closed":
            return APIStatus.HEALTHY
        elif state["state"] == "half_open":
            return APIStatus.DEGRADED
        return APIStatus.UNAVAILABLE


class RateLimiter:
    """
    Token bucket rate limiter with Redis backing.
    Supports per-minute, per-hour, and per-day limits.
    """

    def __init__(
        self,
        name: str,
        requests_per_minute: int = 30,
        requests_per_hour: int = 500,
        requests_per_day: int = 5000,
    ):
        self.name = name
        self.rpm = requests_per_minute
        self.rph = requests_per_hour
        self.rpd = requests_per_day
        self._cache_prefix = f"ratelimit_{name}"

    def _get_key(self, period: str) -> str:
        """Get cache key for a time period."""
        now = int(time.time())
        if period == "minute":
            bucket = now // 60
        elif period == "hour":
            bucket = now // 3600
        else:  # day
            bucket = now // 86400
        return f"{self._cache_prefix}_{period}_{bucket}"

    def _get_counts(self) -> Tuple[int, int, int]:
        """Get current request counts."""
        return (
            cache.get(self._get_key("minute"), 0),
            cache.get(self._get_key("hour"), 0),
            cache.get(self._get_key("day"), 0),
        )

    def _increment(self):
        """Increment all counters."""
        for period, ttl in [("minute", 120), ("hour", 7200), ("day", 172800)]:
            key = self._get_key(period)
            current = cache.get(key, 0)
            cache.set(key, current + 1, timeout=ttl)

    def check_limit(self) -> Tuple[bool, Optional[int]]:
        """
        Check if request is within limits.
        Returns (allowed, wait_seconds).
        """
        minute, hour, day = self._get_counts()

        if day >= self.rpd:
            wait = 86400 - (int(time.time()) % 86400)
            return False, wait

        if hour >= self.rph:
            wait = 3600 - (int(time.time()) % 3600)
            return False, wait

        if minute >= self.rpm:
            wait = 60 - (int(time.time()) % 60)
            return False, wait

        return True, None

    def acquire(self, timeout: int = 60) -> bool:
        """Acquire permission to make a request."""
        start = time.time()

        while time.time() - start < timeout:
            allowed, wait = self.check_limit()
            if allowed:
                self._increment()
                return True

            if wait and wait > timeout - (time.time() - start):
                return False

            time.sleep(min(wait or 1, 5))

        return False

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limit statistics."""
        minute, hour, day = self._get_counts()
        return {
            "minute": {"current": minute, "limit": self.rpm},
            "hour": {"current": hour, "limit": self.rph},
            "day": {"current": day, "limit": self.rpd},
        }


class APIClient:
    """
    Base API client with rate limiting, caching, and error handling.
    Extend this class for specific APIs.
    """

    # Override in subclasses
    API_NAME: str = "base"
    BASE_URL: str = ""
    REQUIRES_AUTH: bool = False

    # Rate limits (override as needed)
    REQUESTS_PER_MINUTE: int = 30
    REQUESTS_PER_HOUR: int = 500
    REQUESTS_PER_DAY: int = 5000

    # Request settings
    TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_BACKOFF: float = 2.0
    CACHE_TTL: int = 3600  # 1 hour default

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.rate_limiter = RateLimiter(
            name=self.API_NAME,
            requests_per_minute=self.REQUESTS_PER_MINUTE,
            requests_per_hour=self.REQUESTS_PER_HOUR,
            requests_per_day=self.REQUESTS_PER_DAY,
        )
        self.circuit_breaker = CircuitBreaker(self.API_NAME)
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a configured requests session."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": "OWDBBot/1.0 (+https://wrestlingdb.org/about/bot)",
            "Accept": "application/json",
        })
        return session

    def _get_cache_key(self, endpoint: str, params: Dict) -> str:
        """Generate a cache key for a request."""
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        key_str = f"{self.API_NAME}:{endpoint}:{param_str}"
        return f"api_cache_{hashlib.md5(key_str.encode()).hexdigest()}"

    def _handle_error(
        self,
        endpoint: str,
        error: Exception,
        response: Optional[requests.Response] = None,
        retry_count: int = 0,
    ):
        """Handle and report an API error."""
        error_type = type(error).__name__
        message = str(error)
        response_code = response.status_code if response else None

        api_error = APIError(
            api_name=self.API_NAME,
            endpoint=endpoint,
            error_type=error_type,
            message=message,
            response_code=response_code,
            retry_count=retry_count,
        )
        ErrorReporter.report(api_error)
        self.circuit_breaker.record_failure()

    def request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        method: str = "GET",
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
    ) -> Optional[Dict]:
        """
        Make an API request with rate limiting, caching, and error handling.

        Args:
            endpoint: API endpoint (appended to BASE_URL)
            params: Query parameters
            method: HTTP method
            use_cache: Whether to use response caching
            cache_ttl: Custom cache TTL (uses CACHE_TTL if not specified)

        Returns:
            JSON response as dict, or None on failure
        """
        params = params or {}
        cache_ttl = cache_ttl or self.CACHE_TTL
        url = f"{self.BASE_URL}{endpoint}"

        # Check circuit breaker
        if self.circuit_breaker.is_open():
            logger.debug(f"Circuit breaker open for {self.API_NAME}, skipping request")
            return None

        # Check cache
        if use_cache and method == "GET":
            cache_key = self._get_cache_key(endpoint, params)
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {self.API_NAME}:{endpoint}")
                return cached

        # Acquire rate limit
        if not self.rate_limiter.acquire(timeout=60):
            logger.warning(f"Rate limit exceeded for {self.API_NAME}")
            return None

        # Make request with retries
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.TIMEOUT,
                )

                # Handle rate limit responses
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"{self.API_NAME} rate limited, waiting {retry_after}s"
                    )
                    time.sleep(min(retry_after, 300))
                    continue

                response.raise_for_status()
                data = response.json()

                # Cache successful response
                if use_cache and method == "GET":
                    cache.set(cache_key, data, timeout=cache_ttl)

                self.circuit_breaker.record_success()
                return data

            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning(
                    f"{self.API_NAME} timeout (attempt {attempt + 1}/{self.MAX_RETRIES})"
                )

            except requests.exceptions.HTTPError as e:
                last_error = e
                if response.status_code in (401, 403):
                    # Auth errors shouldn't retry
                    self._handle_error(endpoint, e, response, attempt)
                    return None
                elif response.status_code >= 500:
                    # Server errors might recover
                    logger.warning(
                        f"{self.API_NAME} server error {response.status_code} "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                    )
                else:
                    self._handle_error(endpoint, e, response, attempt)
                    return None

            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(
                    f"{self.API_NAME} request failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}"
                )

            # Wait before retry with exponential backoff
            if attempt < self.MAX_RETRIES - 1:
                wait_time = self.RETRY_BACKOFF ** attempt
                time.sleep(wait_time)

        # All retries failed
        if last_error:
            self._handle_error(endpoint, last_error, retry_count=self.MAX_RETRIES)

        return None

    def get_status(self) -> Dict[str, Any]:
        """Get API client status."""
        return {
            "name": self.API_NAME,
            "status": self.circuit_breaker.get_status().value,
            "rate_limits": self.rate_limiter.get_stats(),
            "requires_auth": self.REQUIRES_AUTH,
            "has_api_key": bool(self.api_key) if self.REQUIRES_AUTH else None,
        }


def with_error_handling(func: Callable[..., T]) -> Callable[..., Optional[T]]:
    """Decorator for graceful error handling in scraper methods."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> Optional[T]:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None

    return wrapper
