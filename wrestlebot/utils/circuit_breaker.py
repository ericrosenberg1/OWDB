"""
Circuit Breaker Pattern Implementation

Prevents cascading failures by temporarily disabling failing services.

States:
- CLOSED: Normal operation
- OPEN: Too many failures, circuit is open (requests blocked)
- HALF_OPEN: Testing if service has recovered
"""

import time
import logging
from enum import Enum
from typing import Callable, Any
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker to prevent repeated failures.

    Usage:
        breaker = CircuitBreaker(
            failure_threshold=5,
            timeout=300,
            name="wikipedia"
        )

        @breaker
        def scrape_wikipedia():
            # Your code here
            pass
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 300,
        half_open_requests: int = 2,
        name: str = "unnamed"
    ):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.half_open_requests = half_open_requests
        self.name = name

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED

    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap functions with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not self.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN"
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except Exception as e:
                self.record_failure()
                raise e

        return wrapper

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if time.time() - self.last_failure_time >= self.timeout:
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to HALF_OPEN"
                )
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            # Allow limited requests to test recovery
            return True

        return False

    def record_success(self):
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.half_open_requests:
                logger.info(
                    f"Circuit breaker '{self.name}' transitioning to CLOSED"
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Failed during recovery test, go back to OPEN
            logger.warning(
                f"Circuit breaker '{self.name}' transitioning back to OPEN "
                f"(recovery test failed)"
            )
            self.state = CircuitState.OPEN

        elif self.failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker '{self.name}' transitioning to OPEN "
                f"({self.failure_count} failures)"
            )
            self.state = CircuitState.OPEN

    def reset(self):
        """Manually reset the circuit breaker."""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0

    def get_status(self) -> dict:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "can_execute": self.can_execute()
        }


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """Manage multiple circuit breakers."""

    def __init__(self):
        self.breakers = {}

    def get_breaker(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 300,
        half_open_requests: int = 2
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(
                failure_threshold=failure_threshold,
                timeout=timeout,
                half_open_requests=half_open_requests,
                name=name
            )
        return self.breakers[name]

    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self.breakers.values():
            breaker.reset()

    def get_all_status(self) -> dict:
        """Get status of all circuit breakers."""
        return {
            name: breaker.get_status()
            for name, breaker in self.breakers.items()
        }


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
