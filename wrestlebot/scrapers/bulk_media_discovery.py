"""
Bulk Media Discovery

Discovers wrestling video games, books, podcasts, documentaries from Wikipedia and APIs.
"""

import logging
import requests
import time
from typing import List, Dict, Set
import re

logger = logging.getLogger(__name__)


class BulkVideoGameDiscovery:
    """Discover wrestling video games from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    CATEGORIES = [
        "Professional_wrestling_video_games",
        "WWE_video_games",
        "AEW_video_games",
        "WCW_video_games",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })

    def discover_all(self) -> List[Dict]:
        """Discover all wrestling video games."""
        all_games = set()

        for category in self.CATEGORIES:
            members = self._get_category_members(category)
            all_games.update(members)

        logger.info(f"Discovered {len(all_games)} unique video games")
        return self._get_details(list(all_games))

    def _get_category_members(self, category: str) -> Set[str]:
        """Get all members from category."""
        members = set()
        continuation = None

        while True:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmlimit': '500',
                'cmtype': 'page',
            }
            if continuation:
                params['cmcontinue'] = continuation

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                data = response.json()

                if 'query' in data and 'categorymembers' in data['query']:
                    for member in data['query']['categorymembers']:
                        title = member['title']
                        if not title.startswith(('Category:', 'List of', 'Template:')):
                            members.add(title)

                if 'continue' not in data:
                    break
                continuation = data['continue'].get('cmcontinue')
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
                break

        return members

    def _get_details(self, titles: List[str]) -> List[Dict]:
        """Get details for games."""
        all_details = []
        batch_size = 50

        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
            }

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                data = response.json()

                if 'query' in data and 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'missing' in page:
                            continue

                        title = page.get('title', '')
                        extract = page.get('extract', '')

                        # Create valid slug - only letters, numbers, hyphens, underscores
                        slug = title.lower().replace(' ', '-').replace("'", '')
                        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                        slug = slug.strip('-_')

                        game_data = {
                            'name': title,
                            'slug': slug,
                            'about': extract[:1000] if extract else '',
                        }

                        # Extract release year
                        year_match = re.search(r'(?:released|published).*?(\d{4})', extract, re.IGNORECASE)
                        if year_match:
                            game_data['release_year'] = int(year_match.group(1))

                        # Extract systems/platforms
                        systems_match = re.search(r'(?:for|on|platforms?:?)\s+([^\n.]+(?:PlayStation|Xbox|Nintendo|PC|Arcade)[^\n.]*)', extract, re.IGNORECASE)
                        if systems_match:
                            game_data['systems'] = systems_match.group(1).strip()

                        # Extract developer
                        dev_match = re.search(r'developed by\s+([^,.\n]+)', extract, re.IGNORECASE)
                        if dev_match:
                            game_data['developer'] = dev_match.group(1).strip()

                        # Extract publisher
                        pub_match = re.search(r'published by\s+([^,.\n]+)', extract, re.IGNORECASE)
                        if pub_match:
                            game_data['publisher'] = pub_match.group(1).strip()

                        all_details.append(game_data)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching game details: {e}")

        return all_details


class BulkBookDiscovery:
    """Discover wrestling books from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    CATEGORIES = [
        "Professional_wrestling_books",
        "Professional_wrestling_autobiographies",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })

    def discover_all(self) -> List[Dict]:
        """Discover all wrestling books."""
        all_books = set()

        for category in self.CATEGORIES:
            members = self._get_category_members(category)
            all_books.update(members)

        logger.info(f"Discovered {len(all_books)} unique books")
        return self._get_details(list(all_books))

    def _get_category_members(self, category: str) -> Set[str]:
        """Get all members from category."""
        members = set()
        continuation = None

        while True:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmlimit': '500',
                'cmtype': 'page',
            }
            if continuation:
                params['cmcontinue'] = continuation

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                data = response.json()

                if 'query' in data and 'categorymembers' in data['query']:
                    for member in data['query']['categorymembers']:
                        title = member['title']
                        if not title.startswith(('Category:', 'List of', 'Template:')):
                            members.add(title)

                if 'continue' not in data:
                    break
                continuation = data['continue'].get('cmcontinue')
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
                break

        return members

    def _get_details(self, titles: List[str]) -> List[Dict]:
        """Get details for books."""
        all_details = []
        batch_size = 50

        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
            }

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                data = response.json()

                if 'query' in data and 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'missing' in page:
                            continue

                        title = page.get('title', '')
                        extract = page.get('extract', '')

                        # Extract author from title (often in format "Title (Author book)")
                        author_match = re.search(r'\(([^)]+(?:autobiography|book))\)', title, re.IGNORECASE)
                        author = None
                        if author_match:
                            author = author_match.group(1).replace(' autobiography', '').replace(' book', '').strip()
                            title = title.replace(author_match.group(0), '').strip()
                        else:
                            # Try to extract from content
                            author_match = re.search(r'(?:by|written by|author:?)\s+([^,.\n]+)', extract, re.IGNORECASE)
                            if author_match:
                                author = author_match.group(1).strip()

                        # Create valid slug - only letters, numbers, hyphens, underscores
                        slug = title.lower().replace(' ', '-').replace("'", '')
                        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                        slug = slug.strip('-_')

                        book_data = {
                            'title': title,
                            'slug': slug,
                            'about': extract[:1000] if extract else '',
                        }

                        if author:
                            book_data['author'] = author

                        # Extract publication year
                        year_match = re.search(r'(?:published|released).*?(\d{4})', extract, re.IGNORECASE)
                        if year_match:
                            book_data['publication_year'] = int(year_match.group(1))

                        # Extract ISBN
                        isbn_match = re.search(r'ISBN[:\s]*([\d-]+)', extract, re.IGNORECASE)
                        if isbn_match:
                            book_data['isbn'] = isbn_match.group(1)

                        # Extract publisher
                        pub_match = re.search(r'publisher[:\s]*([^,.\n]+)', extract, re.IGNORECASE)
                        if pub_match:
                            book_data['publisher'] = pub_match.group(1).strip()

                        all_details.append(book_data)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching book details: {e}")

        return all_details


class BulkDocumentaryDiscovery:
    """Discover wrestling documentaries from Wikipedia."""

    BASE_URL = "https://en.wikipedia.org/w/api.php"
    CATEGORIES = [
        "Professional_wrestling_documentary_films",
        "WWE_television_specials",
        "Documentary_films_about_professional_wrestling",
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WrestleBot/2.0 (Wrestling Database; https://wrestlingdb.org)'
        })

    def discover_all(self) -> List[Dict]:
        """Discover all wrestling documentaries."""
        all_docs = set()

        for category in self.CATEGORIES:
            members = self._get_category_members(category)
            all_docs.update(members)

        logger.info(f"Discovered {len(all_docs)} unique documentaries")
        return self._get_details(list(all_docs))

    def _get_category_members(self, category: str) -> Set[str]:
        """Get all members from category."""
        members = set()
        continuation = None

        while True:
            params = {
                'action': 'query',
                'format': 'json',
                'list': 'categorymembers',
                'cmtitle': f'Category:{category}',
                'cmlimit': '500',
                'cmtype': 'page',
            }
            if continuation:
                params['cmcontinue'] = continuation

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=10)
                data = response.json()

                if 'query' in data and 'categorymembers' in data['query']:
                    for member in data['query']['categorymembers']:
                        title = member['title']
                        if not title.startswith(('Category:', 'List of', 'Template:')):
                            members.add(title)

                if 'continue' not in data:
                    break
                continuation = data['continue'].get('cmcontinue')
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
                break

        return members

    def _get_details(self, titles: List[str]) -> List[Dict]:
        """Get details for documentaries."""
        all_details = []
        batch_size = 50

        for i in range(0, len(titles), batch_size):
            batch = titles[i:i + batch_size]

            params = {
                'action': 'query',
                'format': 'json',
                'titles': '|'.join(batch),
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
            }

            try:
                response = self.session.get(self.BASE_URL, params=params, timeout=15)
                data = response.json()

                if 'query' in data and 'pages' in data['query']:
                    for page in data['query']['pages'].values():
                        if 'missing' in page:
                            continue

                        title = page.get('title', '')
                        extract = page.get('extract', '')

                        # Create valid slug - only letters, numbers, hyphens, underscores
                        slug = title.lower().replace(' ', '-').replace("'", '')
                        slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
                        slug = slug.strip('-_')

                        doc_data = {
                            'title': title,
                            'slug': slug,
                            'about': extract[:1000] if extract else '',
                            'type': 'documentary',
                        }

                        # Extract release year
                        year_match = re.search(r'(?:released|aired).*?(\d{4})', extract, re.IGNORECASE)
                        if year_match:
                            doc_data['release_year'] = int(year_match.group(1))

                        all_details.append(doc_data)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error fetching documentary details: {e}")

        return all_details
