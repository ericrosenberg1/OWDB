"""
Wikipedia API Fetcher for WrestleBot.

This module fetches data from Wikipedia using their official REST API,
with strong safeguards to ensure copyright compliance:

1. Only extracts FACTUAL data (names, dates, numbers) - never prose
2. Uses structured API endpoints for infobox data when available
3. Respects rate limits and API terms of service
4. All content is processed through AI to extract only facts
5. Source URLs are always preserved for attribution

Wikipedia's factual data (names, dates, records) is not copyrightable
under US law (Feist v. Rural). However, we still:
- Credit Wikipedia as source
- Link back to original articles
- Never copy prose, descriptions, or original expression
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urljoin

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class WikipediaAPIFetcher:
    """
    Fetches wrestling data from Wikipedia API with copyright safeguards.

    Uses Wikipedia's official API endpoints:
    - REST API for article content
    - Action API for category members and search
    """

    API_BASE = "https://en.wikipedia.org/w/api.php"
    REST_BASE = "https://en.wikipedia.org/api/rest_v1"

    # Rate limiting - very conservative
    REQUESTS_PER_SECOND = 1
    CACHE_TTL = 3600  # 1 hour

    # Wrestling-related categories to explore
    WRESTLER_CATEGORIES = [
        "American_male_professional_wrestlers",
        "Japanese_male_professional_wrestlers",
        "Mexican_male_professional_wrestlers",
        "Canadian_male_professional_wrestlers",
        "British_male_professional_wrestlers",
        "American_female_professional_wrestlers",
        "Japanese_female_professional_wrestlers",
        "WWE_Hall_of_Fame_inductees",
        "AEW_wrestlers",
        "WWE_Champions",
        "World_Heavyweight_Champions_(WWE)",
        "Professional_wrestlers_from_New_York_(state)",
        "Professional_wrestlers_from_California",
        "Professional_wrestlers_from_Texas",
    ]

    PROMOTION_CATEGORIES = [
        "Professional_wrestling_promotions",
        "American_professional_wrestling_promotions",
        "Japanese_professional_wrestling_promotions",
        "Mexican_professional_wrestling_promotions",
        "British_professional_wrestling_promotions",
        "Professional_wrestling_promotions_in_Canada",
    ]

    EVENT_CATEGORIES = [
        "WWE_pay-per-view_events",
        "AEW_pay-per-view_events",
        "Impact_Wrestling_pay-per-view_events",
        "New_Japan_Pro-Wrestling_events",
        "Professional_wrestling_annual_events",
        "WrestleMania",
        "Royal_Rumble",
        "SummerSlam",
        "Survivor_Series",
    ]

    TITLE_CATEGORIES = [
        "Professional_wrestling_championships",
        "World_heavyweight_wrestling_championships",
        "WWE_championships",
        "AEW_championships",
        "Women's_professional_wrestling_championships",
        "Tag_team_wrestling_championships",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/1.0 (https://wrestlingdb.org/wrestlebot; '
                          'contact@wrestlingdb.org) Python/requests',
            'Accept': 'application/json',
        })
        self._last_request = 0

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request
        if elapsed < 1 / self.REQUESTS_PER_SECOND:
            time.sleep(1 / self.REQUESTS_PER_SECOND - elapsed)
        self._last_request = time.time()

    def _api_request(
        self,
        params: Dict[str, Any],
        use_cache: bool = True
    ) -> Optional[Dict]:
        """Make a request to the Wikipedia Action API."""
        params['format'] = 'json'
        params['formatversion'] = '2'

        # Create a stable cache key using MD5 hash (safe for all cache backends)
        sorted_params = sorted(params.items())
        params_str = json.dumps(sorted_params, sort_keys=True)
        cache_key = f"wikiapi:{hashlib.md5(params_str.encode()).hexdigest()}"

        if use_cache:
            cached = cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached

        self._rate_limit()

        try:
            response = self.session.get(self.API_BASE, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if use_cache and data:
                cache.set(cache_key, data, self.CACHE_TTL)

            return data

        except requests.RequestException as e:
            logger.error(f"Wikipedia API error: {e}")
            return None

    def _rest_request(self, endpoint: str, use_cache: bool = True) -> Optional[Dict]:
        """Make a request to the Wikipedia REST API."""
        cache_key = f"wikirest:{hashlib.md5(endpoint.encode()).hexdigest()}"

        if use_cache:
            cached = cache.get(cache_key)
            if cached and isinstance(cached, dict):
                return cached

        self._rate_limit()

        try:
            url = f"{self.REST_BASE}{endpoint}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()

            if use_cache and data:
                cache.set(cache_key, data, self.CACHE_TTL)

            return data

        except requests.RequestException as e:
            logger.error(f"Wikipedia REST API error: {e}")
            return None

    def get_category_members(
        self,
        category: str,
        limit: int = 50,
        cmtype: str = "page"
    ) -> List[Dict[str, str]]:
        """
        Get members of a Wikipedia category.

        Returns list of dicts with 'title' and 'pageid'.
        """
        members = []
        params = {
            'action': 'query',
            'list': 'categorymembers',
            'cmtitle': f'Category:{category}',
            'cmlimit': min(limit, 500),
            'cmtype': cmtype,
        }

        while len(members) < limit:
            data = self._api_request(params)
            if not data or not isinstance(data, dict) or 'query' not in data:
                break

            category_members = data['query'].get('categorymembers', [])
            if not isinstance(category_members, list):
                break

            for member in category_members:
                if len(members) >= limit:
                    break
                # Skip if member is not a dict
                if not isinstance(member, dict):
                    continue
                # Skip category pages and lists
                title = member.get('title', '')
                if not title.startswith('Category:') and 'List of' not in title:
                    members.append({
                        'title': title,
                        'pageid': member.get('pageid'),
                    })

            if 'continue' in data:
                params['cmcontinue'] = data['continue']['cmcontinue']
            else:
                break

        return members

    def search_articles(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for Wikipedia articles."""
        params = {
            'action': 'query',
            'list': 'search',
            'srsearch': query,
            'srlimit': limit,
            'srprop': 'snippet|titlesnippet',
        }

        data = self._api_request(params)
        if not data or 'query' not in data:
            return []

        return data['query'].get('search', [])

    def get_article_summary(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get article summary via REST API.

        Returns structured data including:
        - title, description, extract (first paragraph)
        - content_urls for source attribution
        """
        encoded_title = quote(title.replace(' ', '_'), safe='')
        data = self._rest_request(f"/page/summary/{encoded_title}")

        if data and data.get('type') == 'standard':
            return {
                'title': data.get('title'),
                'description': data.get('description'),
                'extract': data.get('extract'),
                'source_url': data.get('content_urls', {}).get('desktop', {}).get('page'),
                'wikibase_item': data.get('wikibase_item'),  # Wikidata ID
            }
        return None

    def get_article_html(self, title: str) -> Optional[str]:
        """Get article HTML for infobox parsing."""
        params = {
            'action': 'parse',
            'page': title,
            'prop': 'text',
            'disableeditsection': 'true',
            'disabletoc': 'true',
        }

        data = self._api_request(params)
        if data and isinstance(data, dict) and 'parse' in data:
            text_data = data['parse'].get('text')
            # formatversion=2 returns text directly as string
            # older format returns {'*': 'html content'}
            if isinstance(text_data, str):
                return text_data
            elif isinstance(text_data, dict):
                return text_data.get('*')
        return None

    def extract_infobox_data(self, html: str) -> Dict[str, str]:
        """
        Extract structured data from Wikipedia infobox.

        IMPORTANT: This extracts only FACTUAL data like:
        - Names (ring name, birth name)
        - Dates (birth, debut, retirement)
        - Places (birthplace, billed from)
        - Numeric data (height, weight, reign count)

        It does NOT extract prose descriptions or copyrightable content.
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, 'lxml')
        infobox = soup.find('table', class_='infobox')

        if not infobox:
            return {}

        data = {}
        for row in infobox.find_all('tr'):
            header = row.find('th')
            value = row.find('td')

            if header and value:
                # Get clean header text
                header_text = self._clean_text(header.get_text())
                if not header_text:
                    continue

                # Get clean value - strip references and extra formatting
                value_text = self._clean_text(value.get_text())
                if not value_text:
                    continue

                # Normalize the key
                key = header_text.lower().replace(' ', '_').replace("'", '')
                data[key] = value_text

        return data

    def _clean_text(self, text: str) -> str:
        """Clean extracted text, removing references and extra whitespace."""
        # Remove reference markers like [1], [2]
        text = re.sub(r'\[\d+\]', '', text)
        # Remove edit links
        text = re.sub(r'\[edit\]', '', text)
        # Clean whitespace
        text = ' '.join(text.split())
        return text.strip()

    def get_wrestler_data(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get factual wrestler data from Wikipedia.

        Returns only non-copyrightable factual data:
        - Ring name, real name, nicknames
        - Birth date/place
        - Career dates (debut, retirement)
        - Trained by (names only)
        - Billing location
        - Finishing moves (names only)

        Does NOT include:
        - Biography prose
        - Career descriptions
        - Match summaries
        """
        html = self.get_article_html(title)
        if not html:
            return None

        infobox = self.extract_infobox_data(html)
        if not infobox:
            return None

        # Map Wikipedia fields to our model
        wrestler_data = {
            'source': 'wikipedia',
            'source_url': f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            'source_title': title,
        }

        # Name mappings
        wrestler_data['name'] = title

        if 'birth_name' in infobox:
            wrestler_data['real_name'] = infobox['birth_name']
        elif 'born' in infobox:
            # Sometimes contains birth name
            born = infobox['born']
            # Try to extract just the name part (before date)
            if not any(c.isdigit() for c in born[:20]):
                wrestler_data['real_name'] = born.split('(')[0].strip()

        # Ring names / aliases
        ring_names = infobox.get('ring_names') or infobox.get('ring_name', '')
        if ring_names:
            wrestler_data['aliases'] = ring_names

        # Location info
        if 'billed_from' in infobox:
            wrestler_data['hometown'] = infobox['billed_from']
        elif 'residence' in infobox:
            wrestler_data['hometown'] = infobox['residence']

        # Career dates
        if 'debut' in infobox:
            year = self._extract_year(infobox['debut'])
            if year:
                wrestler_data['debut_year'] = year

        if 'retired' in infobox:
            year = self._extract_year(infobox['retired'])
            if year:
                wrestler_data['retirement_year'] = year

        # Nationality (from birthplace if available)
        if 'birth_place' in infobox:
            wrestler_data['birth_place'] = infobox['birth_place']

        # Finishing moves (just the names, not descriptions)
        if 'finishing_moves' in infobox or 'finishing_move' in infobox:
            moves = infobox.get('finishing_moves') or infobox.get('finishing_move', '')
            wrestler_data['finishers'] = moves

        return wrestler_data

    def get_promotion_data(self, title: str) -> Optional[Dict[str, Any]]:
        """Get factual promotion data from Wikipedia."""
        html = self.get_article_html(title)
        if not html:
            return None

        infobox = self.extract_infobox_data(html)
        if not infobox:
            return None

        promotion_data = {
            'source': 'wikipedia',
            'source_url': f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            'source_title': title,
            'name': title,
        }

        # Abbreviation
        if 'acronym' in infobox:
            promotion_data['abbreviation'] = infobox['acronym']
        elif 'short_name' in infobox:
            promotion_data['abbreviation'] = infobox['short_name']

        # Founded year
        if 'founded' in infobox:
            year = self._extract_year(infobox['founded'])
            if year:
                promotion_data['founded_year'] = year

        # Defunct year
        defunct_field = infobox.get('defunct') or infobox.get('closed')
        if defunct_field:
            year = self._extract_year(defunct_field)
            if year:
                promotion_data['closed_year'] = year

        # Website
        if 'website' in infobox:
            url = self._extract_url(infobox['website'])
            if url:
                promotion_data['website'] = url

        return promotion_data

    def get_event_data(self, title: str) -> Optional[Dict[str, Any]]:
        """Get factual event data from Wikipedia."""
        html = self.get_article_html(title)
        if not html:
            return None

        infobox = self.extract_infobox_data(html)
        if not infobox:
            return None

        event_data = {
            'source': 'wikipedia',
            'source_url': f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            'source_title': title,
            'name': title,
        }

        # Date
        date_field = infobox.get('date') or infobox.get('dates')
        if date_field:
            date = self._extract_date(date_field)
            if date:
                event_data['date'] = date

        # Venue
        if 'venue' in infobox:
            event_data['venue_name'] = infobox['venue']

        # Location
        location = infobox.get('city') or infobox.get('location')
        if location:
            event_data['venue_location'] = location

        # Attendance
        if 'attendance' in infobox:
            attendance = self._extract_number(infobox['attendance'])
            if attendance:
                event_data['attendance'] = attendance

        # Promotion
        if 'promotion' in infobox:
            event_data['promotion_name'] = infobox['promotion']

        return event_data

    def get_title_data(self, title: str) -> Optional[Dict[str, Any]]:
        """Get factual championship title data from Wikipedia."""
        html = self.get_article_html(title)
        if not html:
            return None

        infobox = self.extract_infobox_data(html)
        if not infobox:
            return None

        title_data = {
            'source': 'wikipedia',
            'source_url': f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}",
            'source_title': title,
            'name': title,
        }

        # Promotion
        if 'promotion' in infobox:
            title_data['promotion_name'] = infobox['promotion']
        elif 'current_promotion' in infobox:
            title_data['promotion_name'] = infobox['current_promotion']

        # Date created
        if 'date_created' in infobox or 'created' in infobox:
            date_field = infobox.get('date_created') or infobox.get('created')
            year = self._extract_year(date_field)
            if year:
                title_data['debut_year'] = year

        # Retired
        if 'date_retired' in infobox or 'retired' in infobox:
            date_field = infobox.get('date_retired') or infobox.get('retired')
            year = self._extract_year(date_field)
            if year:
                title_data['retirement_year'] = year

        return title_data

    def _extract_year(self, text: str) -> Optional[int]:
        """Extract a 4-digit year from text."""
        match = re.search(r'\b(19|20)\d{2}\b', text)
        if match:
            year = int(match.group())
            if 1900 <= year <= datetime.now().year + 1:
                return year
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Try to extract and parse a date from text."""
        # Common date patterns
        patterns = [
            (r'(\w+ \d{1,2}, \d{4})', '%B %d, %Y'),  # January 1, 2020
            (r'(\d{1,2} \w+ \d{4})', '%d %B %Y'),     # 1 January 2020
            (r'(\d{4}-\d{2}-\d{2})', '%Y-%m-%d'),     # 2020-01-01
        ]

        for pattern, fmt in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    dt = datetime.strptime(match.group(1), fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None

    def _extract_number(self, text: str) -> Optional[int]:
        """Extract a number from text (e.g., attendance)."""
        # Remove commas and other formatting
        cleaned = re.sub(r'[^\d]', '', text)
        if cleaned:
            try:
                return int(cleaned)
            except ValueError:
                pass
        return None

    def _extract_url(self, text: str) -> Optional[str]:
        """Extract a URL from text."""
        match = re.search(r'https?://[^\s<>"]+', text)
        if match:
            return match.group()
        return None

    def discover_new_wrestlers(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Discover new wrestlers from Wikipedia categories.

        Uses rotating category index to ensure variety across cycles.
        """
        from ..models import Wrestler, WrestleBotLog

        # Get recently skipped names to avoid retrying
        recently_skipped = set(
            WrestleBotLog.objects.filter(
                entity_type='wrestler',
                action_type='skip',
            ).values_list('entity_name', flat=True)[:200]
        )

        # Rotate through categories based on current time
        import time
        category_index = int(time.time() // 300) % len(self.WRESTLER_CATEGORIES)
        # Use 2 consecutive categories for variety
        categories = [
            self.WRESTLER_CATEGORIES[category_index % len(self.WRESTLER_CATEGORIES)],
            self.WRESTLER_CATEGORIES[(category_index + 1) % len(self.WRESTLER_CATEGORIES)],
        ]

        wrestlers = []
        existing_names = set(
            Wrestler.objects.values_list('name', flat=True)
        )
        skip_names = existing_names | recently_skipped

        for category in categories:
            if len(wrestlers) >= limit:
                break

            members = self.get_category_members(category, limit=limit * 3)

            for member in members:
                if len(wrestlers) >= limit:
                    break

                title = member['title']
                if title in skip_names:
                    continue

                data = self.get_wrestler_data(title)
                if data and self._is_valid_wrestler_data(data):
                    wrestlers.append(data)
                    skip_names.add(title)

        return wrestlers

    def discover_new_promotions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Discover new promotions from Wikipedia categories."""
        from ..models import Promotion, WrestleBotLog

        # Get recently skipped names to avoid retrying
        recently_skipped = set(
            WrestleBotLog.objects.filter(
                entity_type='promotion',
                action_type='skip',
            ).values_list('entity_name', flat=True)[:100]
        )

        # Rotate through categories
        import time
        category_index = int(time.time() // 300) % len(self.PROMOTION_CATEGORIES)
        categories = [
            self.PROMOTION_CATEGORIES[category_index % len(self.PROMOTION_CATEGORIES)],
            self.PROMOTION_CATEGORIES[(category_index + 1) % len(self.PROMOTION_CATEGORIES)],
        ]

        promotions = []
        existing_names = set(
            Promotion.objects.values_list('name', flat=True)
        )
        skip_names = existing_names | recently_skipped

        for category in categories:
            if len(promotions) >= limit:
                break

            members = self.get_category_members(category, limit=limit * 3)

            for member in members:
                if len(promotions) >= limit:
                    break

                title = member['title']
                if title in skip_names:
                    continue

                data = self.get_promotion_data(title)
                if data:
                    promotions.append(data)
                    skip_names.add(title)

        return promotions

    def discover_new_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Discover new events from Wikipedia categories."""
        from ..models import Event, WrestleBotLog

        # Get recently skipped names to avoid retrying
        recently_skipped = set(
            WrestleBotLog.objects.filter(
                entity_type='event',
                action_type='skip',
            ).values_list('entity_name', flat=True)[:100]
        )

        # Rotate through categories
        import time
        category_index = int(time.time() // 300) % len(self.EVENT_CATEGORIES)
        categories = [
            self.EVENT_CATEGORIES[category_index % len(self.EVENT_CATEGORIES)],
            self.EVENT_CATEGORIES[(category_index + 1) % len(self.EVENT_CATEGORIES)],
        ]

        events = []
        existing_names = set(
            Event.objects.values_list('name', flat=True)
        )
        skip_names = existing_names | recently_skipped

        for category in categories:
            if len(events) >= limit:
                break

            members = self.get_category_members(category, limit=limit * 3)

            for member in members:
                if len(events) >= limit:
                    break

                title = member['title']
                if title in skip_names:
                    continue

                data = self.get_event_data(title)
                if data and 'date' in data:  # Events need dates
                    events.append(data)
                    skip_names.add(title)

        return events

    def discover_new_titles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Discover new championship titles from Wikipedia categories."""
        from ..models import Title, WrestleBotLog

        # Get recently skipped names to avoid retrying
        recently_skipped = set(
            WrestleBotLog.objects.filter(
                entity_type='title',
                action_type='skip',
            ).values_list('entity_name', flat=True)[:100]
        )

        # Rotate through categories
        import time
        category_index = int(time.time() // 300) % len(self.TITLE_CATEGORIES)
        categories = [
            self.TITLE_CATEGORIES[category_index % len(self.TITLE_CATEGORIES)],
            self.TITLE_CATEGORIES[(category_index + 1) % len(self.TITLE_CATEGORIES)],
        ]

        titles = []
        existing_names = set(
            Title.objects.values_list('name', flat=True)
        )
        skip_names = existing_names | recently_skipped

        for category in categories:
            if len(titles) >= limit:
                break

            members = self.get_category_members(category, limit=limit * 3)

            for member in members:
                if len(titles) >= limit:
                    break

                title = member['title']
                if title in skip_names:
                    continue

                data = self.get_title_data(title)
                if data:
                    titles.append(data)
                    skip_names.add(title)

        return titles

    def _is_valid_wrestler_data(self, data: Dict[str, Any]) -> bool:
        """Check if wrestler data has minimum required fields."""
        # Must have a name
        if not data.get('name'):
            return False

        # Should have at least one other field
        optional_fields = [
            'real_name', 'aliases', 'hometown', 'debut_year',
            'retirement_year', 'finishers'
        ]
        has_extra = any(data.get(f) for f in optional_fields)

        return has_extra
