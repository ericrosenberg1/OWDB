"""
Wikimedia Commons API client for fetching CC-licensed images.

This client searches Wikimedia Commons for Creative Commons licensed images
to enrich wrestling database records. Only images with permissive licenses
(CC0, CC-BY, CC-BY-SA, Public Domain) are used.

API Documentation: https://commons.wikimedia.org/w/api.php
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

from django.core.cache import cache

from .api_client import APIClient

logger = logging.getLogger(__name__)


class WikimediaCommonsClient(APIClient):
    """
    Client for Wikimedia Commons API.

    Fetches CC-licensed images for wrestlers, promotions, venues, etc.
    Only uses images with permissive licenses for legal compliance.
    """

    API_NAME = "wikimedia_commons"
    BASE_URL = "https://commons.wikimedia.org/w/api.php"
    REQUIRES_AUTH = False

    # Conservative rate limits for Wikimedia
    REQUESTS_PER_MINUTE = 20
    REQUESTS_PER_HOUR = 300
    REQUESTS_PER_DAY = 2000

    # Cache settings
    CACHE_TTL = 86400  # 24 hours for image metadata

    # Allowed licenses (only permissive CC licenses)
    ALLOWED_LICENSES = [
        'cc0',
        'cc-zero',
        'pd',
        'public domain',
        'cc-by',
        'cc-by-2.0',
        'cc-by-2.5',
        'cc-by-3.0',
        'cc-by-4.0',
        'cc-by-sa',
        'cc-by-sa-2.0',
        'cc-by-sa-2.5',
        'cc-by-sa-3.0',
        'cc-by-sa-4.0',
    ]

    # License normalization map
    LICENSE_MAP = {
        'cc0': 'cc0',
        'cc-zero': 'cc0',
        'pd': 'pd',
        'public domain': 'pd',
        'cc-by': 'cc-by',
        'cc-by-2.0': 'cc-by',
        'cc-by-2.5': 'cc-by',
        'cc-by-3.0': 'cc-by',
        'cc-by-4.0': 'cc-by',
        'cc-by-sa': 'cc-by-sa',
        'cc-by-sa-2.0': 'cc-by-sa',
        'cc-by-sa-2.5': 'cc-by-sa',
        'cc-by-sa-3.0': 'cc-by-sa',
        'cc-by-sa-4.0': 'cc-by-sa',
    }

    def __init__(self):
        super().__init__()
        # Override session headers for Wikimedia API
        self.session.headers.update({
            "User-Agent": "OWDBBot/1.0 (https://wrestlingdb.org/about/bot; contact@wrestlingdb.org) Python/requests",
            "Accept": "application/json",
        })

    def _normalize_license(self, license_str: str) -> Optional[str]:
        """Normalize license string to our standard format."""
        if not license_str:
            return None
        license_lower = license_str.lower().strip()
        for key, value in self.LICENSE_MAP.items():
            if key in license_lower:
                return value
        return None

    def _is_allowed_license(self, license_str: str) -> bool:
        """Check if a license is in our allowed list."""
        if not license_str:
            return False
        license_lower = license_str.lower()
        return any(allowed in license_lower for allowed in self.ALLOWED_LICENSES)

    def search_images(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for images on Wikimedia Commons.

        Args:
            query: Search query (e.g., "John Cena wrestler")
            limit: Maximum number of results

        Returns:
            List of image metadata dictionaries
        """
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {query}",
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": min(limit, 50),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": 400,  # Get thumbnail URL
        }

        response = self.request("", params=params)
        if not response or "query" not in response:
            return []

        results = []
        pages = response.get("query", {}).get("pages", {})

        for page_id, page_data in pages.items():
            if page_id == "-1":
                continue

            imageinfo = page_data.get("imageinfo", [{}])[0]
            extmeta = imageinfo.get("extmetadata", {})

            # Extract license info
            license_short = extmeta.get("LicenseShortName", {}).get("value", "")
            license_url = extmeta.get("LicenseUrl", {}).get("value", "")

            # Skip if not an allowed license
            if not self._is_allowed_license(license_short):
                continue

            # Get attribution/credit
            artist = extmeta.get("Artist", {}).get("value", "")
            # Clean HTML from artist field
            artist = re.sub(r'<[^>]+>', '', artist).strip()

            results.append({
                "title": page_data.get("title", ""),
                "page_id": page_id,
                "url": imageinfo.get("url"),
                "thumb_url": imageinfo.get("thumburl"),
                "description_url": imageinfo.get("descriptionurl"),
                "width": imageinfo.get("width"),
                "height": imageinfo.get("height"),
                "mime_type": imageinfo.get("mime"),
                "license": self._normalize_license(license_short),
                "license_raw": license_short,
                "license_url": license_url,
                "artist": artist,
                "description": extmeta.get("ImageDescription", {}).get("value", ""),
            })

        return results

    def get_image_info(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed info for a specific image.

        Args:
            title: Image title (e.g., "File:John Cena 2016.jpg")

        Returns:
            Image metadata dictionary or None
        """
        if not title.startswith("File:"):
            title = f"File:{title}"

        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata|size|mime",
            "iiurlwidth": 800,
        }

        response = self.request("", params=params)
        if not response or "query" not in response:
            return None

        pages = response.get("query", {}).get("pages", {})
        for page_id, page_data in pages.items():
            if page_id == "-1":
                return None

            imageinfo = page_data.get("imageinfo", [{}])[0]
            extmeta = imageinfo.get("extmetadata", {})

            license_short = extmeta.get("LicenseShortName", {}).get("value", "")

            if not self._is_allowed_license(license_short):
                return None

            artist = extmeta.get("Artist", {}).get("value", "")
            artist = re.sub(r'<[^>]+>', '', artist).strip()

            return {
                "title": page_data.get("title", ""),
                "page_id": page_id,
                "url": imageinfo.get("url"),
                "thumb_url": imageinfo.get("thumburl"),
                "description_url": imageinfo.get("descriptionurl"),
                "width": imageinfo.get("width"),
                "height": imageinfo.get("height"),
                "mime_type": imageinfo.get("mime"),
                "license": self._normalize_license(license_short),
                "license_raw": license_short,
                "license_url": extmeta.get("LicenseUrl", {}).get("value", ""),
                "artist": artist,
                "description": extmeta.get("ImageDescription", {}).get("value", ""),
            }

        return None

    def find_wrestler_image(self, name: str, real_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a CC-licensed image for a wrestler.

        Args:
            name: Wrestler's ring name
            real_name: Wrestler's real name (optional, for better results)

        Returns:
            Best matching image metadata or None
        """
        cache_key = f"commons_wrestler_{hashlib.md5(name.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        # Try different search strategies
        queries = [
            f'"{name}" wrestler',
            f'"{name}" wrestling',
            f'"{name}" WWE',
            name,
        ]

        if real_name and real_name != name:
            queries.insert(0, f'"{real_name}" wrestler')

        for query in queries:
            results = self.search_images(query, limit=5)

            # Filter for relevant images
            for result in results:
                # Skip logos, belts, etc.
                title_lower = result.get("title", "").lower()
                if any(skip in title_lower for skip in ["logo", "belt", "championship", "title", "arena", "stadium"]):
                    continue

                # Prefer portrait-oriented images
                width = result.get("width", 0)
                height = result.get("height", 0)
                if width > 0 and height > 0:
                    # Skip very wide images (likely not portraits)
                    if width > height * 1.5:
                        continue

                # Found a suitable image
                cache.set(cache_key, result, timeout=self.CACHE_TTL)
                return result

        # No suitable image found
        cache.set(cache_key, {}, timeout=self.CACHE_TTL)
        return None

    def find_promotion_image(self, name: str, abbreviation: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a CC-licensed image/logo for a promotion.

        Args:
            name: Promotion name
            abbreviation: Promotion abbreviation (e.g., "WWE", "AEW")

        Returns:
            Best matching image metadata or None
        """
        cache_key = f"commons_promotion_{hashlib.md5(name.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        queries = [
            f'"{name}" logo',
            f'"{name}" wrestling',
        ]

        if abbreviation:
            queries.insert(0, f'"{abbreviation}" wrestling logo')
            queries.append(f'"{abbreviation}" wrestling')

        for query in queries:
            results = self.search_images(query, limit=5)

            for result in results:
                # For promotions, we actually want logos
                cache.set(cache_key, result, timeout=self.CACHE_TTL)
                return result

        cache.set(cache_key, {}, timeout=self.CACHE_TTL)
        return None

    def find_venue_image(self, name: str, location: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a CC-licensed image for a venue.

        Args:
            name: Venue name
            location: Venue location (city, state/country)

        Returns:
            Best matching image metadata or None
        """
        cache_key = f"commons_venue_{hashlib.md5(name.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        queries = [
            f'"{name}" arena',
            f'"{name}" stadium',
            name,
        ]

        if location:
            queries.insert(0, f'"{name}" {location}')

        for query in queries:
            results = self.search_images(query, limit=5)

            for result in results:
                # Skip logos for venues
                title_lower = result.get("title", "").lower()
                if "logo" in title_lower:
                    continue

                # Prefer landscape images for venues
                width = result.get("width", 0)
                height = result.get("height", 0)
                if width > 0 and height > 0:
                    # Skip very tall images (likely not venue photos)
                    if height > width * 1.5:
                        continue

                cache.set(cache_key, result, timeout=self.CACHE_TTL)
                return result

        cache.set(cache_key, {}, timeout=self.CACHE_TTL)
        return None

    def find_event_image(self, name: str, promotion: Optional[str] = None, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Find a CC-licensed image for an event.

        Args:
            name: Event name (e.g., "WrestleMania")
            promotion: Promotion name
            year: Event year

        Returns:
            Best matching image metadata or None
        """
        cache_key = f"commons_event_{hashlib.md5(f'{name}_{year}'.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        queries = []

        if year:
            queries.append(f'"{name}" {year}')
            if promotion:
                queries.append(f'"{name}" {promotion} {year}')

        queries.extend([
            f'"{name}" wrestling',
            f'"{name}" logo',
            name,
        ])

        for query in queries:
            results = self.search_images(query, limit=5)

            for result in results:
                cache.set(cache_key, result, timeout=self.CACHE_TTL)
                return result

        cache.set(cache_key, {}, timeout=self.CACHE_TTL)
        return None

    def find_title_image(self, name: str, promotion: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Find a CC-licensed image for a championship title.

        Args:
            name: Title name (e.g., "WWE Championship")
            promotion: Promotion name

        Returns:
            Best matching image metadata or None
        """
        cache_key = f"commons_title_{hashlib.md5(name.encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached if cached else None

        queries = [
            f'"{name}" belt',
            f'"{name}" championship',
            name,
        ]

        if promotion:
            queries.insert(0, f'"{promotion}" "{name}"')

        for query in queries:
            results = self.search_images(query, limit=5)

            for result in results:
                # For titles, prefer images with "belt" or "championship" in title
                title_lower = result.get("title", "").lower()
                if "belt" in title_lower or "championship" in title_lower or "title" in title_lower:
                    cache.set(cache_key, result, timeout=self.CACHE_TTL)
                    return result

            # If no ideal match, return first result
            if results:
                cache.set(cache_key, results[0], timeout=self.CACHE_TTL)
                return results[0]

        cache.set(cache_key, {}, timeout=self.CACHE_TTL)
        return None
