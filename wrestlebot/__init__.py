"""
WrestleBot - Standalone Wrestling Data Collection Service

This service runs independently of Django and continuously collects
wrestling data from multiple sources, then publishes to Django via REST API.

Key Features:
- No time limits - runs indefinitely
- Circuit breaker pattern for fault tolerance
- Smart rate limiting per source
- Retry queue for failed operations
- Self-healing and auto-recovery
"""

__version__ = "2.0.0"
