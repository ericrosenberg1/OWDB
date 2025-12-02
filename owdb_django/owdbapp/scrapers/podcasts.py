"""
Podcast APIs for wrestling podcasts.

We use multiple free podcast APIs:
- Podcast Index: Free, open API with comprehensive data
- iTunes Search API: Free, no auth required
- Listen Notes: Free tier available

API Documentation:
- Podcast Index: https://podcastindex-org.github.io/docs-api/
- iTunes: https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
"""

import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional

from django.conf import settings

from .api_client import APIClient, with_error_handling

logger = logging.getLogger(__name__)


class PodcastIndexClient(APIClient):
    """
    Podcast Index API client.

    Free and open podcast database. Requires API key (free registration).
    https://api.podcastindex.org/
    """

    API_NAME = "podcastindex"
    BASE_URL = "https://api.podcastindex.org/api/1.0"
    REQUIRES_AUTH = True

    REQUESTS_PER_MINUTE = 10
    REQUESTS_PER_HOUR = 300
    REQUESTS_PER_DAY = 3000

    CACHE_TTL = 86400

    # Wrestling podcast search terms
    WRESTLING_SEARCH_TERMS = [
        "wrestling",
        "WWE",
        "pro wrestling",
        "AEW",
        "wrestling news",
        "wrestling podcast",
        "wrestling observer",
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        self.api_key = api_key or os.getenv("PODCAST_INDEX_API_KEY") or getattr(
            settings, "PODCAST_INDEX_API_KEY", None
        )
        self.api_secret = api_secret or os.getenv("PODCAST_INDEX_API_SECRET") or getattr(
            settings, "PODCAST_INDEX_API_SECRET", None
        )
        super().__init__(self.api_key)

    def _is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.api_key and self.api_secret)

    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for Podcast Index."""
        if not self._is_configured():
            return {}

        # Podcast Index uses a time-based auth header
        auth_date = str(int(time.time()))
        auth_string = self.api_key + self.api_secret + auth_date
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()

        return {
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": auth_date,
            "Authorization": auth_hash,
            "User-Agent": "OWDBBot/1.0",
        }

    def request(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        **kwargs,
    ) -> Optional[Dict]:
        """Override request to add auth headers."""
        if self._is_configured():
            self.session.headers.update(self._get_auth_headers())

        return super().request(endpoint, params, **kwargs)

    @with_error_handling
    def search_podcasts(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for podcasts by term."""
        if not self._is_configured():
            return []

        params = {
            "q": query,
            "max": limit,
        }

        data = self.request("/search/byterm", params=params)
        if not data:
            return []

        return data.get("feeds", [])

    @with_error_handling
    def get_podcast_by_id(self, feed_id: int) -> Optional[Dict[str, Any]]:
        """Get podcast details by ID."""
        if not self._is_configured():
            return None

        params = {"id": feed_id}
        data = self.request("/podcasts/byfeedid", params=params)

        if data and data.get("feed"):
            return data["feed"]
        return None

    def search_wrestling_podcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for wrestling-related podcasts."""
        podcasts = []
        seen_ids = set()

        if not self._is_configured():
            logger.warning("Podcast Index credentials not configured")
            return []

        for term in self.WRESTLING_SEARCH_TERMS:
            if len(podcasts) >= limit:
                break

            results = self.search_podcasts(term, limit=20)
            for podcast in results:
                feed_id = podcast.get("id")
                if feed_id and feed_id not in seen_ids:
                    seen_ids.add(feed_id)
                    podcasts.append(podcast)

        return podcasts[:limit]

    def parse_podcast_for_model(self, podcast: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Podcast Index data to our Podcast model format."""
        # Extract launch year from newestItemPubdate or other dates
        launch_year = None
        oldest_date = podcast.get("oldestItemPubdate")
        if oldest_date:
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(oldest_date)
                launch_year = dt.year
            except (ValueError, OSError, TypeError):
                pass

        return {
            "name": podcast.get("title", ""),
            "hosts": podcast.get("author", ""),
            "launch_year": launch_year,
            "url": podcast.get("url") or podcast.get("link"),
            "about": podcast.get("description", "")[:500] if podcast.get("description") else None,
            "source": "podcastindex",
            "source_id": str(podcast.get("id")),
            "source_url": f"https://podcastindex.org/podcast/{podcast.get('id')}",
        }

    def scrape_podcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling podcasts."""
        podcasts_data = []
        podcasts = self.search_wrestling_podcasts(limit=limit)

        for podcast in podcasts:
            parsed = self.parse_podcast_for_model(podcast)
            if parsed.get("name"):
                podcasts_data.append(parsed)

        logger.info(f"Podcast Index: Scraped {len(podcasts_data)} wrestling podcasts")
        return podcasts_data[:limit]


class ITunesPodcastClient(APIClient):
    """
    iTunes Search API for podcasts.

    Completely free, no authentication required!
    https://developer.apple.com/library/archive/documentation/AudioVideo/Conceptual/iTuneSearchAPI/
    """

    API_NAME = "itunes"
    BASE_URL = "https://itunes.apple.com"
    REQUIRES_AUTH = False

    REQUESTS_PER_MINUTE = 20
    REQUESTS_PER_HOUR = 200
    REQUESTS_PER_DAY = 2000

    CACHE_TTL = 86400

    WRESTLING_SEARCH_TERMS = [
        "wrestling",
        "WWE podcast",
        "pro wrestling",
        "AEW podcast",
        "wrestling news",
    ]

    @with_error_handling
    def search_podcasts(
        self,
        query: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for podcasts."""
        params = {
            "term": query,
            "media": "podcast",
            "limit": limit,
        }

        data = self.request("/search", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def get_podcast_by_id(self, podcast_id: int) -> Optional[Dict[str, Any]]:
        """Get podcast details by iTunes ID."""
        params = {"id": podcast_id}
        data = self.request("/lookup", params=params)

        if data and data.get("results"):
            return data["results"][0]
        return None

    def search_wrestling_podcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for wrestling-related podcasts."""
        podcasts = []
        seen_ids = set()

        for term in self.WRESTLING_SEARCH_TERMS:
            if len(podcasts) >= limit:
                break

            results = self.search_podcasts(term, limit=20)
            for podcast in results:
                podcast_id = podcast.get("collectionId")
                if podcast_id and podcast_id not in seen_ids:
                    seen_ids.add(podcast_id)
                    podcasts.append(podcast)

        return podcasts[:limit]

    def parse_podcast_for_model(self, podcast: Dict[str, Any]) -> Dict[str, Any]:
        """Convert iTunes podcast data to our Podcast model format."""
        # Extract launch year from releaseDate
        launch_year = None
        release_date = podcast.get("releaseDate", "")
        if release_date:
            try:
                launch_year = int(release_date[:4])
            except (ValueError, TypeError):
                pass

        return {
            "name": podcast.get("collectionName", ""),
            "hosts": podcast.get("artistName", ""),
            "launch_year": launch_year,
            "url": podcast.get("collectionViewUrl"),
            "about": None,  # iTunes doesn't provide descriptions in search
            "source": "itunes",
            "source_id": str(podcast.get("collectionId")),
            "source_url": podcast.get("collectionViewUrl"),
        }

    def scrape_podcasts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling podcasts from iTunes."""
        podcasts_data = []
        podcasts = self.search_wrestling_podcasts(limit=limit)

        for podcast in podcasts:
            parsed = self.parse_podcast_for_model(podcast)
            if parsed.get("name"):
                podcasts_data.append(parsed)

        logger.info(f"iTunes: Scraped {len(podcasts_data)} wrestling podcasts")
        return podcasts_data[:limit]


class ListenNotesClient(APIClient):
    """
    Listen Notes API client.

    Free tier: 300 queries/month
    https://www.listennotes.com/api/docs/

    Note: Very limited free tier, use sparingly.
    """

    API_NAME = "listennotes"
    BASE_URL = "https://listen-api.listennotes.com/api/v2"
    REQUIRES_AUTH = True

    # Very conservative due to 300/month limit
    REQUESTS_PER_MINUTE = 1
    REQUESTS_PER_HOUR = 5
    REQUESTS_PER_DAY = 10

    CACHE_TTL = 604800  # 7 days to minimize API calls

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("LISTEN_NOTES_API_KEY") or getattr(
            settings, "LISTEN_NOTES_API_KEY", None
        )
        super().__init__(api_key)

        if self.api_key:
            self.session.headers["X-ListenAPI-Key"] = self.api_key

    def _is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @with_error_handling
    def search_podcasts(
        self,
        query: str,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for podcasts."""
        if not self._is_configured():
            return []

        params = {
            "q": query,
            "type": "podcast",
            "offset": offset,
            "only_in": "title,description",
        }

        data = self.request("/search", params=params)
        if not data:
            return []

        return data.get("results", [])

    def search_wrestling_podcasts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for wrestling podcasts - limited due to API quotas."""
        if not self._is_configured():
            logger.warning("Listen Notes API key not configured")
            return []

        # Only do one search to conserve API calls
        results = self.search_podcasts("professional wrestling podcast", offset=0)
        return results[:limit]

    def parse_podcast_for_model(self, podcast: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Listen Notes data to our Podcast model format."""
        # Extract launch year from earliest_pub_date_ms
        launch_year = None
        earliest_pub = podcast.get("earliest_pub_date_ms")
        if earliest_pub:
            try:
                import datetime
                dt = datetime.datetime.fromtimestamp(earliest_pub / 1000)
                launch_year = dt.year
            except (ValueError, OSError, TypeError):
                pass

        return {
            "name": podcast.get("title_original", ""),
            "hosts": podcast.get("publisher_original", ""),
            "launch_year": launch_year,
            "url": podcast.get("website"),
            "about": podcast.get("description_original", "")[:500] if podcast.get("description_original") else None,
            "source": "listennotes",
            "source_id": podcast.get("id"),
            "source_url": podcast.get("listennotes_url"),
        }

    def scrape_podcasts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape wrestling podcasts from Listen Notes - limited."""
        podcasts_data = []
        podcasts = self.search_wrestling_podcasts(limit=limit)

        for podcast in podcasts:
            parsed = self.parse_podcast_for_model(podcast)
            if parsed.get("name"):
                podcasts_data.append(parsed)

        logger.info(f"Listen Notes: Scraped {len(podcasts_data)} wrestling podcasts")
        return podcasts_data
