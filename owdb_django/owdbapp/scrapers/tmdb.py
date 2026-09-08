"""
TMDB (The Movie Database) API client for movies and TV shows.

TMDB offers a free API for non-commercial use. We use it to fetch:
- Wrestling documentaries and movies
- Wrestling TV shows and specials
- Cast/crew information (for wrestler appearances)

API Documentation: https://developer.themoviedb.org/docs
Rate Limit: 50 requests per second (very generous)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from django.conf import settings

from .api_client import APIClient, with_error_handling

logger = logging.getLogger(__name__)


class TMDBClient(APIClient):
    """
    TMDB API client for movies and TV shows.

    Requires a free API key from https://www.themoviedb.org/settings/api
    """

    API_NAME = "tmdb"
    BASE_URL = "https://api.themoviedb.org/3"
    REQUIRES_AUTH = True

    # TMDB is very generous with rate limits
    REQUESTS_PER_MINUTE = 40  # Stay well under 50/sec limit
    REQUESTS_PER_HOUR = 2000
    REQUESTS_PER_DAY = 20000

    CACHE_TTL = 86400  # 24 hours - content doesn't change often

    # Wrestling-related keywords and genres
    WRESTLING_KEYWORDS = [
        "professional wrestling",
        "wrestling",
        "wwe",
        "wwf",
        "wcw",
        "ecw",
        "aew",
        "njpw",
        "tna",
        "impact wrestling",
        "lucha libre",
    ]

    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or os.getenv("TMDB_API_KEY") or getattr(
            settings, "TMDB_API_KEY", None
        )
        super().__init__(api_key)

        if self.api_key:
            self.session.params = {"api_key": self.api_key}

    def _is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    @with_error_handling
    def search_movies(
        self, query: str, page: int = 1, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for movies by title."""
        if not self._is_configured():
            return []

        params = {"query": query, "page": page, "include_adult": "false"}
        if year:
            params["year"] = year

        data = self.request("/search/movie", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def search_tv(
        self, query: str, page: int = 1, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for TV shows by title."""
        if not self._is_configured():
            return []

        params = {"query": query, "page": page, "include_adult": "false"}
        if year:
            params["first_air_date_year"] = year

        data = self.request("/search/tv", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def search_person(self, name: str, page: int = 1) -> List[Dict[str, Any]]:
        """Search for people (actors, crew) by name."""
        if not self._is_configured():
            return []

        params = {"query": name, "page": page, "include_adult": "false"}
        data = self.request("/search/person", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a movie."""
        if not self._is_configured():
            return None

        data = self.request(
            f"/movie/{movie_id}",
            params={"append_to_response": "credits,keywords"},
        )
        return data

    @with_error_handling
    def get_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a TV show."""
        if not self._is_configured():
            return None

        data = self.request(
            f"/tv/{tv_id}",
            params={"append_to_response": "credits,keywords"},
        )
        return data

    @with_error_handling
    def get_person_details(self, person_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed information about a person."""
        if not self._is_configured():
            return None

        data = self.request(
            f"/person/{person_id}",
            params={"append_to_response": "combined_credits"},
        )
        return data

    @with_error_handling
    def discover_wrestling_movies(
        self, page: int = 1, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover wrestling-related movies using keywords."""
        if not self._is_configured():
            return []

        # Genre 99 = Documentary, 28 = Action, 18 = Drama
        params = {
            "page": page,
            "sort_by": "popularity.desc",
            "with_keywords": "9715|4613|179093",  # wrestling, WWE, pro wrestling
            "include_adult": "false",
        }
        if year:
            params["primary_release_year"] = year

        data = self.request("/discover/movie", params=params)
        if not data:
            return []

        return data.get("results", [])

    @with_error_handling
    def discover_wrestling_tv(
        self, page: int = 1, year: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Discover wrestling-related TV shows."""
        if not self._is_configured():
            return []

        params = {
            "page": page,
            "sort_by": "popularity.desc",
            "with_keywords": "9715|4613|179093",
            "include_adult": "false",
        }
        if year:
            params["first_air_date_year"] = year

        data = self.request("/discover/tv", params=params)
        if not data:
            return []

        return data.get("results", [])

    def search_wrestling_content(
        self, limit: int = 50
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for all wrestling-related content.
        Returns movies and TV shows.
        """
        results = {"movies": [], "tv_shows": []}

        if not self._is_configured():
            logger.warning("TMDB API key not configured")
            return results

        # Search by keywords
        for keyword in self.WRESTLING_KEYWORDS[:5]:  # Limit to avoid rate limits
            movies = self.search_movies(keyword)
            if movies:
                results["movies"].extend(movies[:10])

            tv_shows = self.search_tv(keyword)
            if tv_shows:
                results["tv_shows"].extend(tv_shows[:10])

            if (
                len(results["movies"]) >= limit
                and len(results["tv_shows"]) >= limit
            ):
                break

        # Discover using wrestling keywords
        discovered_movies = self.discover_wrestling_movies()
        if discovered_movies:
            results["movies"].extend(discovered_movies)

        discovered_tv = self.discover_wrestling_tv()
        if discovered_tv:
            results["tv_shows"].extend(discovered_tv)

        # Deduplicate by TMDB ID
        seen_movies = set()
        unique_movies = []
        for movie in results["movies"]:
            if movie.get("id") not in seen_movies:
                seen_movies.add(movie["id"])
                unique_movies.append(movie)
        results["movies"] = unique_movies[:limit]

        seen_tv = set()
        unique_tv = []
        for show in results["tv_shows"]:
            if show.get("id") not in seen_tv:
                seen_tv.add(show["id"])
                unique_tv.append(show)
        results["tv_shows"] = unique_tv[:limit]

        return results

    def parse_movie_for_special(self, movie: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TMDB movie data to our Special model format."""
        release_date = movie.get("release_date", "")
        release_year = int(release_date[:4]) if release_date else None

        # Determine type based on genres
        genres = [g.get("name", "").lower() for g in movie.get("genres", [])]
        if "documentary" in genres:
            special_type = "documentary"
        else:
            special_type = "movie"

        return {
            "title": movie.get("title", ""),
            "release_year": release_year,
            "type": special_type,
            "about": movie.get("overview", "")[:500] if movie.get("overview") else None,
            "source": "tmdb",
            "source_id": str(movie.get("id")),
            "source_url": f"https://www.themoviedb.org/movie/{movie.get('id')}",
        }

    def parse_tv_for_special(self, show: Dict[str, Any]) -> Dict[str, Any]:
        """Convert TMDB TV data to our Special model format."""
        first_air = show.get("first_air_date", "")
        release_year = int(first_air[:4]) if first_air else None

        # Determine type
        genres = [g.get("name", "").lower() for g in show.get("genres", [])]
        if "documentary" in genres:
            special_type = "documentary"
        elif show.get("number_of_seasons", 0) > 1:
            special_type = "series"
        else:
            special_type = "tv_special"

        return {
            "title": show.get("name", ""),
            "release_year": release_year,
            "type": special_type,
            "about": show.get("overview", "")[:500] if show.get("overview") else None,
            "source": "tmdb",
            "source_id": str(show.get("id")),
            "source_url": f"https://www.themoviedb.org/tv/{show.get('id')}",
        }

    def scrape_specials(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling-related movies and TV shows."""
        specials = []
        content = self.search_wrestling_content(limit=limit)

        # Process movies
        for movie in content["movies"]:
            details = self.get_movie_details(movie["id"])
            if details:
                special = self.parse_movie_for_special(details)
                if special.get("title"):
                    specials.append(special)

        # Process TV shows
        for show in content["tv_shows"]:
            details = self.get_tv_details(show["id"])
            if details:
                special = self.parse_tv_for_special(details)
                if special.get("title"):
                    specials.append(special)

        logger.info(f"TMDB: Scraped {len(specials)} wrestling specials")
        return specials[:limit]

    # =========================================================================
    # TV Episode Methods for TV Episode Tracking System
    # =========================================================================

    # TMDB IDs for major wrestling TV shows
    WRESTLING_SHOWS = {
        # WWE
        'wwe_raw': 4370,
        'wwe_smackdown': 4371,
        'wwe_nxt': 35521,
        'wwe_main_event': 45533,
        # AEW
        'aew_dynamite': 89770,
        'aew_rampage': 130542,
        'aew_collision': 227367,
        # TNA/Impact
        'impact_wrestling': 4431,
        # Historical
        'wcw_nitro': 13579,
        'wcw_thunder': 14247,
        'ecw_hardcore_tv': 16347,
    }

    @with_error_handling
    def get_tv_season(self, tv_id: int, season_number: int) -> Optional[Dict]:
        """
        Get all episodes for a specific season.

        Args:
            tv_id: TMDB TV show ID
            season_number: Season number (1-indexed)

        Returns:
            Season data including episodes list, or None on failure
        """
        if not self._is_configured():
            return None
        return self.request(f"/tv/{tv_id}/season/{season_number}")

    @with_error_handling
    def get_tv_episode(
        self, tv_id: int, season_number: int, episode_number: int
    ) -> Optional[Dict]:
        """
        Get details for a specific episode.

        Args:
            tv_id: TMDB TV show ID
            season_number: Season number
            episode_number: Episode number within the season

        Returns:
            Episode data or None on failure
        """
        if not self._is_configured():
            return None
        return self.request(
            f"/tv/{tv_id}/season/{season_number}/episode/{episode_number}"
        )

    @with_error_handling
    def get_latest_episodes(self, tv_id: int, limit: int = 10) -> List[Dict]:
        """
        Get the most recent episodes for a show.

        Args:
            tv_id: TMDB TV show ID
            limit: Maximum number of episodes to return

        Returns:
            List of episode data dicts, most recent first
        """
        if not self._is_configured():
            return []

        details = self.get_tv_details(tv_id)
        if not details:
            return []

        episodes = []
        last_season = details.get('number_of_seasons', 0)

        if last_season > 0:
            season_data = self.get_tv_season(tv_id, last_season)
            if season_data and 'episodes' in season_data:
                # Sort by air date descending and return most recent
                sorted_eps = sorted(
                    season_data['episodes'],
                    key=lambda x: x.get('air_date', '') or '',
                    reverse=True
                )
                episodes = sorted_eps[:limit]

        return episodes

    def get_all_episodes_for_season(
        self, tv_id: int, season_number: int
    ) -> List[Dict]:
        """
        Get all episodes for a specific season.

        Args:
            tv_id: TMDB TV show ID
            season_number: Season number

        Returns:
            List of episode data dicts
        """
        season_data = self.get_tv_season(tv_id, season_number)
        if season_data and 'episodes' in season_data:
            return season_data['episodes']
        return []

    def get_all_tracked_show_updates(self) -> Dict[str, List[Dict]]:
        """
        Check all tracked wrestling shows for new episodes.

        Returns:
            Dict mapping show key to list of recent episodes
        """
        updates = {}
        for show_key, tmdb_id in self.WRESTLING_SHOWS.items():
            episodes = self.get_latest_episodes(tmdb_id, limit=5)
            if episodes:
                updates[show_key] = episodes
        return updates

    def parse_episode_for_event(
        self, episode: Dict, show_name: str, promotion_abbrev: str
    ) -> Dict[str, Any]:
        """
        Convert TMDB episode data to our Event model format.

        Args:
            episode: TMDB episode data dict
            show_name: Name of the TV show (e.g., "WWE Raw")
            promotion_abbrev: Promotion abbreviation (e.g., "WWE")

        Returns:
            Dict with fields for Event model
        """
        air_date = episode.get('air_date')
        ep_num = episode.get('episode_number')
        season_num = episode.get('season_number')

        # Build episode name (e.g., "WWE Raw #1500" or use TMDB title)
        episode_name = episode.get('name', '')
        if ep_num and not episode_name:
            name = f"{show_name} #{ep_num}"
        elif ep_num and episode_name:
            # If TMDB provides a title, use it but include episode number
            name = f"{show_name} #{ep_num}: {episode_name}"
        else:
            name = episode_name or f"{show_name} Episode"

        return {
            'name': name,
            'date': air_date,
            'episode_number': ep_num,
            'season_number': season_num,
            'event_type': 'tv_episode',
            'tmdb_episode_id': episode.get('id'),
            'about': episode.get('overview', '')[:500] if episode.get('overview') else None,
            'source': 'tmdb',
        }

    def get_show_season_count(self, tv_id: int) -> int:
        """
        Get the total number of seasons for a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            Number of seasons, or 0 if show not found
        """
        details = self.get_tv_details(tv_id)
        if details:
            return details.get('number_of_seasons', 0)
        return 0

    def get_show_premiere_date(self, tv_id: int) -> Optional[str]:
        """
        Get the premiere date for a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            Premiere date string (YYYY-MM-DD) or None
        """
        details = self.get_tv_details(tv_id)
        if details:
            return details.get('first_air_date')
        return None

    def get_show_status(self, tv_id: int) -> Optional[str]:
        """
        Get the current status of a TV show.

        Args:
            tv_id: TMDB TV show ID

        Returns:
            Status string (e.g., "Returning Series", "Ended") or None
        """
        details = self.get_tv_details(tv_id)
        if details:
            return details.get('status')
        return None
