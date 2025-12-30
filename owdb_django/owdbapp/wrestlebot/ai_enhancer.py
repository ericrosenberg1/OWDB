"""
WrestleBot 2.0 AI Enhancer

Optional Claude API integration for intelligent data enhancement.
Only activated when ANTHROPIC_API_KEY environment variable is set.
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class AIEnhancer:
    """
    Uses Claude API for intelligent data enhancement.

    Features:
    - Bio generation from available data
    - Duplicate detection and resolution
    - Data validation and inconsistency detection
    - Information extraction from unstructured text

    Cost Control:
    - Rate limited to max 100 API calls per day
    - Aggressive caching of responses
    - Fallback to rule-based logic when quota exceeded
    """

    DAILY_LIMIT = 100
    CACHE_TTL = 86400 * 7  # Cache responses for 7 days

    def __init__(self):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        self._client = None
        self._available = None

    @property
    def client(self):
        """Lazy load Anthropic client."""
        if self._client is None and self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.warning("anthropic package not installed")
                self._client = False
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic client: {e}")
                self._client = False
        return self._client if self._client else None

    @property
    def is_available(self) -> bool:
        """Check if AI enhancement is available."""
        if self._available is None:
            self._available = bool(self.api_key and self.client)
        return self._available

    def _get_daily_call_count(self) -> int:
        """Get number of API calls made today."""
        today = timezone.now().date().isoformat()
        return cache.get(f'ai_enhancer_calls_{today}', 0)

    def _increment_call_count(self):
        """Increment daily API call counter."""
        today = timezone.now().date().isoformat()
        key = f'ai_enhancer_calls_{today}'
        current = cache.get(key, 0)
        cache.set(key, current + 1, timeout=86400)

    def _can_make_call(self) -> bool:
        """Check if we can make another API call today."""
        return self._get_daily_call_count() < self.DAILY_LIMIT

    def _get_cached_response(self, cache_key: str) -> Optional[str]:
        """Get cached API response."""
        return cache.get(f'ai_response_{cache_key}')

    def _cache_response(self, cache_key: str, response: str):
        """Cache API response."""
        cache.set(f'ai_response_{cache_key}', response, timeout=self.CACHE_TTL)

    def _make_api_call(self, prompt: str, max_tokens: int = 1000) -> Optional[str]:
        """
        Make a rate-limited, cached API call to Claude.

        Returns the response text or None if failed/unavailable.
        """
        if not self.is_available:
            logger.debug("AI enhancer not available")
            return None

        if not self._can_make_call():
            logger.warning("AI enhancer daily limit reached")
            return None

        # Check cache first
        cache_key = hashlib.md5(prompt.encode()).hexdigest()
        cached = self._get_cached_response(cache_key)
        if cached:
            logger.debug("Using cached AI response")
            return cached

        try:
            message = self.client.messages.create(
                model="claude-3-haiku-20240307",  # Use Haiku for cost efficiency
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            self._increment_call_count()

            response = message.content[0].text if message.content else None
            if response:
                self._cache_response(cache_key, response)

            return response

        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return None

    def generate_wrestler_bio(self, wrestler) -> Optional[str]:
        """
        Generate a professional biography for a wrestler.

        Uses available data to create a coherent, factual biography.
        """
        if not self.is_available:
            return None

        # Gather available data
        data_points = []

        if wrestler.name:
            data_points.append(f"Ring name: {wrestler.name}")
        if wrestler.real_name:
            data_points.append(f"Real name: {wrestler.real_name}")
        if wrestler.hometown:
            data_points.append(f"From: {wrestler.hometown}")
        if wrestler.nationality:
            data_points.append(f"Nationality: {wrestler.nationality}")
        if wrestler.debut_year:
            data_points.append(f"Debuted: {wrestler.debut_year}")
        if wrestler.retirement_year:
            data_points.append(f"Retired: {wrestler.retirement_year}")
        if wrestler.aliases:
            data_points.append(f"Also known as: {wrestler.aliases}")
        if wrestler.finishers:
            data_points.append(f"Signature moves: {wrestler.finishers}")

        # Get promotion info
        if hasattr(wrestler, 'promotions') and wrestler.promotions.exists():
            promos = ', '.join([p.name for p in wrestler.promotions.all()[:5]])
            data_points.append(f"Promotions worked for: {promos}")

        # Get title info
        if hasattr(wrestler, 'title_reigns'):
            titles = wrestler.title_reigns.all()[:5]
            if titles:
                title_names = ', '.join([t.title.name for t in titles if t.title])
                data_points.append(f"Championships: {title_names}")

        if not data_points:
            logger.debug(f"Not enough data to generate bio for {wrestler.name}")
            return None

        prompt = f"""Write a brief, professional wrestling biography (2-3 paragraphs) for the following wrestler based on the available information. Be factual and avoid speculation. Write in an encyclopedic style.

Available information:
{chr(10).join(data_points)}

Write only the biography text, no headers or labels."""

        bio = self._make_api_call(prompt, max_tokens=500)

        if bio and len(bio) > 50:
            logger.info(f"Generated AI bio for {wrestler.name}")
            return bio.strip()

        return None

    def resolve_duplicates(self, entries: List[Dict[str, Any]]) -> List[List[int]]:
        """
        Identify potential duplicate entries.

        Returns list of lists, where each inner list contains IDs
        of entries that are likely duplicates of each other.
        """
        if not self.is_available or not entries:
            return []

        # Format entries for the prompt
        entry_text = []
        for i, entry in enumerate(entries):
            entry_text.append(f"{i+1}. Name: {entry.get('name', 'Unknown')}")
            if entry.get('aliases'):
                entry_text.append(f"   Aliases: {entry.get('aliases')}")
            if entry.get('real_name'):
                entry_text.append(f"   Real name: {entry.get('real_name')}")

        prompt = f"""Analyze these wrestling entries and identify which ones are likely duplicates (same person with different spellings or names). Return a JSON array of arrays, where each inner array contains the entry numbers that are duplicates.

Entries:
{chr(10).join(entry_text)}

Return only valid JSON, like: [[1,3], [2,5,7]] or [] if no duplicates.
If no duplicates are found, return an empty array: []"""

        response = self._make_api_call(prompt, max_tokens=200)

        if response:
            try:
                # Extract JSON from response
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('\n', 1)[1]
                    response = response.rsplit('```', 1)[0]

                duplicates = json.loads(response)
                if isinstance(duplicates, list):
                    # Convert to IDs
                    result = []
                    for group in duplicates:
                        if isinstance(group, list):
                            # Convert 1-indexed to actual IDs
                            ids = [entries[i-1].get('id') for i in group if 0 < i <= len(entries)]
                            if len(ids) > 1:
                                result.append(ids)
                    return result
            except json.JSONDecodeError:
                logger.warning("Failed to parse duplicate detection response")

        return []

    def extract_wrestler_info(self, text: str) -> Dict[str, Any]:
        """
        Extract structured wrestler information from unstructured text.

        Useful for parsing Wikipedia article text or other sources.
        """
        if not self.is_available or not text:
            return {}

        # Truncate very long text
        if len(text) > 3000:
            text = text[:3000] + "..."

        prompt = f"""Extract wrestler information from this text. Return a JSON object with any of these fields you can find:
- name (ring name)
- real_name
- hometown (city, state/country)
- nationality
- debut_year (as integer)
- retirement_year (as integer, if retired)
- finishers (comma-separated list)
- height
- weight
- trained_by

Only include fields with confident data. Return only valid JSON.

Text:
{text}"""

        response = self._make_api_call(prompt, max_tokens=300)

        if response:
            try:
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('\n', 1)[1]
                    response = response.rsplit('```', 1)[0]

                data = json.loads(response)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                logger.warning("Failed to parse extracted wrestler info")

        return {}

    def validate_data(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate entity data for inconsistencies.

        Returns dict with 'valid' boolean and 'issues' list.
        """
        if not self.is_available or not entity_data:
            return {'valid': True, 'issues': []}

        prompt = f"""Check this wrestling database entry for inconsistencies or potential errors. Look for:
- Impossible dates (debut before birth, etc.)
- Logical inconsistencies
- Potentially incorrect data

Data:
{json.dumps(entity_data, indent=2, default=str)}

Return a JSON object with:
- "valid": true/false
- "issues": list of issue descriptions (empty if valid)

Return only valid JSON."""

        response = self._make_api_call(prompt, max_tokens=300)

        if response:
            try:
                response = response.strip()
                if response.startswith('```'):
                    response = response.split('\n', 1)[1]
                    response = response.rsplit('```', 1)[0]

                result = json.loads(response)
                if isinstance(result, dict):
                    return {
                        'valid': result.get('valid', True),
                        'issues': result.get('issues', [])
                    }
            except json.JSONDecodeError:
                logger.warning("Failed to parse validation response")

        return {'valid': True, 'issues': []}

    def get_stats(self) -> Dict[str, Any]:
        """Get AI enhancer statistics."""
        return {
            'available': self.is_available,
            'calls_today': self._get_daily_call_count(),
            'daily_limit': self.DAILY_LIMIT,
            'remaining': max(0, self.DAILY_LIMIT - self._get_daily_call_count()),
        }
