"""
RAWG Video Games Database API client.

RAWG is a free video game database API with comprehensive game data.
We use it to fetch wrestling video games.

API Documentation: https://rawg.io/apidocs
Rate Limit: 20,000 requests/month for free tier
"""

import logging
import os
from typing import Any, Dict, List, Optional

from django.conf import settings

from .api_client import APIClient, with_error_handling

logger = logging.getLogger(__name__)


class RAWGClient(APIClient):
    """
    RAWG API client for video games.

    Get a free API key at https://rawg.io/apidocs
    """

    API_NAME = "rawg"
    BASE_URL = "https://api.rawg.io/api"
    REQUIRES_AUTH = True

    # RAWG monthly limit is 20,000 requests
    # ~667/day, ~28/hour, but we'll be conservative
    REQUESTS_PER_MINUTE = 10
    REQUESTS_PER_HOUR = 100
    REQUESTS_PER_DAY = 500

    CACHE_TTL = 86400  # 24 hours

    # Wrestling game search terms
    WRESTLING_SEARCH_TERMS = [
        "WWE",
        "wrestling",
        "WWF",
        "WCW",
        "AEW",
        "SmackDown",
        "Raw",
        "pro wrestling",
        "TNA",
        "Fire Pro",
        "Lucha",
    ]

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("RAWG_API_KEY") or getattr(
            settings, "RAWG_API_KEY", None
        )
        super().__init__(api_key)

    def _is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def _add_key(self, params: Dict) -> Dict:
        """Add API key to params."""
        if self.api_key:
            params["key"] = self.api_key
        return params

    @with_error_handling
    def search_games(
        self,
        query: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for games by name."""
        if not self._is_configured():
            return []

        params = self._add_key({
            "search": query,
            "page": page,
            "page_size": page_size,
            "search_precise": "true",
        })

        data = self.request("/games", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def get_game_details(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a game."""
        if not self._is_configured():
            return None

        params = self._add_key({})
        data = self.request(f"/games/{game_id}", params=params)
        return data

    @with_error_handling
    def get_game_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """Get game by slug."""
        if not self._is_configured():
            return None

        params = self._add_key({})
        data = self.request(f"/games/{slug}", params=params)
        return data

    @with_error_handling
    def list_games_by_genre(
        self,
        genre: str,
        page: int = 1,
        page_size: int = 20,
        ordering: str = "-rating",
    ) -> List[Dict[str, Any]]:
        """List games by genre."""
        if not self._is_configured():
            return []

        params = self._add_key({
            "genres": genre,
            "page": page,
            "page_size": page_size,
            "ordering": ordering,
        })

        data = self.request("/games", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def list_games_by_tag(
        self,
        tag: str,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """List games by tag."""
        if not self._is_configured():
            return []

        params = self._add_key({
            "tags": tag,
            "page": page,
            "page_size": page_size,
        })

        data = self.request("/games", params=params)
        if not data:
            return []

        return data.get("results", [])

    def search_wrestling_games(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for all wrestling-related video games."""
        games = []
        seen_ids = set()

        if not self._is_configured():
            logger.warning("RAWG API key not configured")
            return []

        # Search by various wrestling terms
        for term in self.WRESTLING_SEARCH_TERMS:
            if len(games) >= limit:
                break

            results = self.search_games(term, page_size=20)
            for game in results:
                game_id = game.get("id")
                if game_id and game_id not in seen_ids:
                    seen_ids.add(game_id)
                    games.append(game)

        # Also search by "sports" genre + wrestling tag
        tag_results = self.list_games_by_tag("wrestling", page_size=40)
        for game in tag_results:
            game_id = game.get("id")
            if game_id and game_id not in seen_ids:
                seen_ids.add(game_id)
                games.append(game)

        return games[:limit]

    def parse_game_for_videogame(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """Convert RAWG game data to our VideoGame model format."""
        # Extract release year
        released = game.get("released", "")
        release_year = int(released[:4]) if released else None

        # Extract platforms
        platforms = []
        for platform_info in game.get("platforms", []):
            platform = platform_info.get("platform", {})
            if platform.get("name"):
                platforms.append(platform["name"])

        # Extract developers
        developers = []
        for dev in game.get("developers", []):
            if dev.get("name"):
                developers.append(dev["name"])

        # Extract publishers
        publishers = []
        for pub in game.get("publishers", []):
            if pub.get("name"):
                publishers.append(pub["name"])

        return {
            "name": game.get("name", ""),
            "release_year": release_year,
            "systems": ", ".join(platforms[:5]) if platforms else None,
            "developer": ", ".join(developers[:2]) if developers else None,
            "publisher": ", ".join(publishers[:2]) if publishers else None,
            "about": game.get("description_raw", "")[:500] if game.get("description_raw") else None,
            "source": "rawg",
            "source_id": str(game.get("id")),
            "source_url": f"https://rawg.io/games/{game.get('slug', game.get('id'))}",
        }

    def scrape_videogames(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling video games."""
        videogames = []
        games = self.search_wrestling_games(limit=limit)

        for game in games:
            # Get full details for each game
            details = self.get_game_details(game["id"])
            if details:
                videogame = self.parse_game_for_videogame(details)
                if videogame.get("name"):
                    videogames.append(videogame)
            else:
                # Fall back to basic info
                videogame = self.parse_game_for_videogame(game)
                if videogame.get("name"):
                    videogames.append(videogame)

        logger.info(f"RAWG: Scraped {len(videogames)} wrestling video games")
        return videogames[:limit]


class IGDBClient(APIClient):
    """
    IGDB API client (Twitch-owned).

    IGDB requires Twitch OAuth - more complex setup but comprehensive data.
    This is a fallback if RAWG is unavailable.

    API Documentation: https://api-docs.igdb.com/
    """

    API_NAME = "igdb"
    BASE_URL = "https://api.igdb.com/v4"
    REQUIRES_AUTH = True

    REQUESTS_PER_MINUTE = 4  # 4 requests/second limit
    REQUESTS_PER_HOUR = 200
    REQUESTS_PER_DAY = 2000

    CACHE_TTL = 86400

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.client_id = client_id or os.getenv("IGDB_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("IGDB_CLIENT_SECRET")
        self._access_token: Optional[str] = None
        self._token_expires: float = 0
        super().__init__()

    def _is_configured(self) -> bool:
        """Check if credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def _get_access_token(self) -> Optional[str]:
        """Get or refresh OAuth access token."""
        import time

        if self._access_token and time.time() < self._token_expires:
            return self._access_token

        if not self._is_configured():
            return None

        try:
            response = self.session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "grant_type": "client_credentials",
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data.get("access_token")
            # Token expires in ~60 days, but refresh early
            self._token_expires = time.time() + data.get("expires_in", 3600) - 300

            return self._access_token

        except Exception as e:
            logger.error(f"Failed to get IGDB access token: {e}")
            return None

    def igdb_request(
        self,
        endpoint: str,
        query: str,
    ) -> Optional[List[Dict[str, Any]]]:
        """Make an IGDB API request with Apicalypse query."""
        token = self._get_access_token()
        if not token:
            return None

        if not self.rate_limiter.acquire(timeout=60):
            return None

        try:
            response = self.session.post(
                f"{self.BASE_URL}/{endpoint}",
                headers={
                    "Client-ID": self.client_id,
                    "Authorization": f"Bearer {token}",
                },
                data=query,
                timeout=30,
            )
            response.raise_for_status()
            self.circuit_breaker.record_success()
            return response.json()

        except Exception as e:
            logger.error(f"IGDB request failed: {e}")
            self.circuit_breaker.record_failure()
            return None

    def search_wrestling_games(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for wrestling games in IGDB."""
        if not self._is_configured():
            logger.warning("IGDB credentials not configured")
            return []

        # IGDB uses Apicalypse query language
        query = f"""
        search "wrestling";
        fields name, first_release_date, platforms.name,
               involved_companies.company.name, involved_companies.developer,
               involved_companies.publisher, summary, url;
        limit {limit};
        """

        results = self.igdb_request("games", query)
        return results or []

    def parse_game_for_videogame(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """Convert IGDB game data to our VideoGame model format."""
        import datetime

        # Parse release date (Unix timestamp)
        release_date = game.get("first_release_date")
        release_year = None
        if release_date:
            try:
                dt = datetime.datetime.fromtimestamp(release_date)
                release_year = dt.year
            except (ValueError, OSError):
                pass

        # Extract platforms
        platforms = [p.get("name", "") for p in game.get("platforms", [])]

        # Extract developers and publishers
        developers = []
        publishers = []
        for company_info in game.get("involved_companies", []):
            company_name = company_info.get("company", {}).get("name", "")
            if company_name:
                if company_info.get("developer"):
                    developers.append(company_name)
                if company_info.get("publisher"):
                    publishers.append(company_name)

        return {
            "name": game.get("name", ""),
            "release_year": release_year,
            "systems": ", ".join(platforms[:5]) if platforms else None,
            "developer": ", ".join(developers[:2]) if developers else None,
            "publisher": ", ".join(publishers[:2]) if publishers else None,
            "about": game.get("summary", "")[:500] if game.get("summary") else None,
            "source": "igdb",
            "source_id": str(game.get("id")),
            "source_url": game.get("url", ""),
        }

    def scrape_videogames(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling video games from IGDB."""
        videogames = []
        games = self.search_wrestling_games(limit=limit)

        for game in games:
            videogame = self.parse_game_for_videogame(game)
            if videogame.get("name"):
                videogames.append(videogame)

        logger.info(f"IGDB: Scraped {len(videogames)} wrestling video games")
        return videogames
