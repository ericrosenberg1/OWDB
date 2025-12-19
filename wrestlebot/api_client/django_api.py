"""
Django REST API Client for WrestleBot

Handles all communication with the Django backend via REST API.
"""

import os
import requests
import logging
from typing import Optional, Dict, List, Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class DjangoAPIClient:
    """
    Client for interacting with Django REST API.

    Usage:
        client = DjangoAPIClient(
            api_url="http://localhost:8000/api/wrestlebot",
            api_token="your-token-here"
        )

        # Create a wrestler
        wrestler = client.create_wrestler({
            "name": "Stone Cold Steve Austin",
            "slug": "stone-cold-steve-austin",
            "real_name": "Steve Austin",
            "debut_year": 1989
        })

        # Bulk import
        client.bulk_import({
            "wrestlers": [...],
            "promotions": [...]
        })
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        timeout: int = 30,
        retry_attempts: int = 3
    ):
        self.api_url = api_url or os.getenv(
            'DJANGO_API_URL',
            'http://localhost:8000/api/wrestlebot'
        )
        self.api_token = api_token or os.getenv('WRESTLEBOT_API_TOKEN')

        if not self.api_token:
            raise ValueError(
                "API token not provided. Set WRESTLEBOT_API_TOKEN environment variable"
            )

        self.timeout = timeout
        self.retry_attempts = retry_attempts

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
            'User-Agent': 'WrestleBot/2.0'
        })

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Make HTTP request with retry logic."""
        url = urljoin(self.api_url + '/', endpoint)

        for attempt in range(self.retry_attempts):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout
                )

                response.raise_for_status()
                return response.json() if response.content else None

            except requests.exceptions.HTTPError as e:
                if response.status_code == 400:
                    # Bad request - don't retry
                    logger.error(f"Bad request to {url}: {response.text}")
                    raise
                elif response.status_code == 401:
                    # Unauthorized - don't retry
                    logger.error("API authentication failed - check token")
                    raise
                elif attempt < self.retry_attempts - 1:
                    logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                    continue
                else:
                    logger.error(f"Request failed after {self.retry_attempts} attempts")
                    raise

            except requests.exceptions.RequestException as e:
                if attempt < self.retry_attempts - 1:
                    logger.warning(f"Request error (attempt {attempt + 1}): {e}")
                    continue
                else:
                    logger.error(f"Request failed after {self.retry_attempts} attempts")
                    raise

        return None

    def health_check(self) -> bool:
        """Check if Django API is accessible."""
        try:
            response = self._make_request('GET', 'health/')
            return response.get('status') == 'ok'
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def get_status(self) -> Optional[Dict]:
        """Get service status and statistics."""
        try:
            return self._make_request('GET', 'status/')
        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return None

    # Wrestler endpoints
    def create_wrestler(self, data: Dict) -> Optional[Dict]:
        """Create or update a wrestler."""
        try:
            return self._make_request('POST', 'wrestlers/', data=data)
        except Exception as e:
            logger.error(f"Failed to create wrestler: {e}")
            return None

    def get_wrestler(self, slug: str) -> Optional[Dict]:
        """Get wrestler by slug."""
        try:
            return self._make_request('GET', f'wrestlers/{slug}/')
        except Exception as e:
            logger.error(f"Failed to get wrestler {slug}: {e}")
            return None

    # Promotion endpoints
    def create_promotion(self, data: Dict) -> Optional[Dict]:
        """Create or update a promotion."""
        try:
            return self._make_request('POST', 'promotions/', data=data)
        except Exception as e:
            logger.error(f"Failed to create promotion: {e}")
            return None

    # Event endpoints
    def create_event(self, data: Dict) -> Optional[Dict]:
        """Create an event."""
        try:
            return self._make_request('POST', 'events/', data=data)
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None

    # Bulk import endpoint
    def bulk_import(self, data: Dict) -> Optional[Dict]:
        """
        Bulk import multiple entity types at once.

        Args:
            data: Dictionary with entity types as keys:
                {
                    "wrestlers": [...],
                    "promotions": [...],
                    "events": [...],
                    "videogames": [...],
                    "books": [...],
                    "podcasts": [...],
                    "specials": [...]
                }

        Returns:
            Results dictionary with counts of created/updated/errors
        """
        try:
            return self._make_request('POST', 'bulk/import/', data=data)
        except Exception as e:
            logger.error(f"Failed to bulk import: {e}")
            return None

    # Video game, book, podcast, special endpoints
    def create_videogame(self, data: Dict) -> Optional[Dict]:
        """Create a video game entry."""
        try:
            return self._make_request('POST', 'videogames/', data=data)
        except Exception as e:
            logger.error(f"Failed to create video game: {e}")
            return None

    def create_book(self, data: Dict) -> Optional[Dict]:
        """Create a book entry."""
        try:
            return self._make_request('POST', 'books/', data=data)
        except Exception as e:
            logger.error(f"Failed to create book: {e}")
            return None

    def create_podcast(self, data: Dict) -> Optional[Dict]:
        """Create a podcast entry."""
        try:
            return self._make_request('POST', 'podcasts/', data=data)
        except Exception as e:
            logger.error(f"Failed to create podcast: {e}")
            return None

    def create_special(self, data: Dict) -> Optional[Dict]:
        """Create a special (movie/TV) entry."""
        try:
            return self._make_request('POST', 'specials/', data=data)
        except Exception as e:
            logger.error(f"Failed to create special: {e}")
            return None

    def list_wrestlers(self, limit: int = 10, offset: int = 0) -> Optional[List[Dict]]:
        """List wrestlers with pagination."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = self._make_request('GET', 'wrestlers/', params=params)
            return response.get('results', []) if response else []
        except Exception as e:
            logger.error(f"Failed to list wrestlers: {e}")
            return []

    def list_promotions(self, limit: int = 10, offset: int = 0) -> Optional[List[Dict]]:
        """List promotions with pagination."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = self._make_request('GET', 'promotions/', params=params)
            return response.get('results', []) if response else []
        except Exception as e:
            logger.error(f"Failed to list promotions: {e}")
            return []

    def list_events(self, limit: int = 10, offset: int = 0) -> Optional[List[Dict]]:
        """List events with pagination."""
        try:
            params = {'limit': limit, 'offset': offset}
            response = self._make_request('GET', 'events/', params=params)
            return response.get('results', []) if response else []
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return []
