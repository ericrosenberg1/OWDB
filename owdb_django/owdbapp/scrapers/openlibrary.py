"""
Open Library API client for books.

Open Library is a free, open-source library catalog with millions of books.
No API key required! We use it to fetch wrestling-related books.

API Documentation: https://openlibrary.org/developers/api
Rate Limit: Be reasonable (~100 requests/minute is safe)
"""

import logging
from typing import Any, Dict, List, Optional

from .api_client import APIClient, with_error_handling

logger = logging.getLogger(__name__)


class OpenLibraryClient(APIClient):
    """
    Open Library API client for books.

    No authentication required - completely free and open!
    """

    API_NAME = "openlibrary"
    BASE_URL = "https://openlibrary.org"
    REQUIRES_AUTH = False

    # Be respectful - it's a non-profit
    REQUESTS_PER_MINUTE = 20
    REQUESTS_PER_HOUR = 500
    REQUESTS_PER_DAY = 5000

    CACHE_TTL = 86400  # 24 hours

    # Wrestling-related search terms for books
    WRESTLING_SEARCH_TERMS = [
        "professional wrestling",
        "WWE",
        "wrestling biography",
        "wrestling history",
        "pro wrestling",
        "WCW",
        "WWF wrestling",
        "wrestling memoir",
        "Hulk Hogan",
        "Stone Cold Steve Austin",
        "The Rock Dwayne Johnson",
        "wrestling legends",
    ]

    @with_error_handling
    def search_books(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for books by title or subject."""
        params = {
            "q": query,
            "page": page,
            "limit": limit,
            "fields": "key,title,author_name,first_publish_year,isbn,publisher,subject",
        }

        data = self.request("/search.json", params=params)
        if not data:
            return []

        return data.get("docs", [])

    @with_error_handling
    def search_by_subject(
        self,
        subject: str,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search for books by subject."""
        # Subject API uses different URL pattern
        subject_slug = subject.lower().replace(" ", "_")
        params = {
            "limit": limit,
            "offset": offset,
        }

        data = self.request(f"/subjects/{subject_slug}.json", params=params)
        if not data:
            return []

        return data.get("works", [])

    @with_error_handling
    def get_book_by_isbn(self, isbn: str) -> Optional[Dict[str, Any]]:
        """Get book details by ISBN."""
        # Clean ISBN
        isbn = isbn.replace("-", "").replace(" ", "")

        data = self.request(f"/isbn/{isbn}.json")
        return data

    @with_error_handling
    def get_work_details(self, work_key: str) -> Optional[Dict[str, Any]]:
        """Get detailed work information."""
        # Work key is like "/works/OL123W"
        if not work_key.startswith("/works/"):
            work_key = f"/works/{work_key}"

        data = self.request(f"{work_key}.json")
        return data

    @with_error_handling
    def get_author_details(self, author_key: str) -> Optional[Dict[str, Any]]:
        """Get author information."""
        if not author_key.startswith("/authors/"):
            author_key = f"/authors/{author_key}"

        data = self.request(f"{author_key}.json")
        return data

    def search_wrestling_books(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for all wrestling-related books."""
        books = []
        seen_keys = set()

        # Search by various terms
        for term in self.WRESTLING_SEARCH_TERMS:
            if len(books) >= limit:
                break

            results = self.search_books(term, limit=20)
            for book in results:
                key = book.get("key")
                if key and key not in seen_keys:
                    seen_keys.add(key)
                    books.append(book)

        # Also search by subject
        subject_results = self.search_by_subject("professional_wrestling", limit=30)
        for work in subject_results:
            key = work.get("key")
            if key and key not in seen_keys:
                seen_keys.add(key)
                books.append(work)

        return books[:limit]

    def parse_book_for_model(self, book: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Open Library book data to our Book model format."""
        # Handle both search results and work details
        title = book.get("title", "")

        # Authors - can be in different formats
        authors = book.get("author_name", [])
        if not authors and book.get("authors"):
            # Work format has author objects
            authors = []
            for author in book.get("authors", []):
                if isinstance(author, dict):
                    author_key = author.get("author", {}).get("key")
                    if author_key:
                        # Would need to fetch author name
                        authors.append(author_key.split("/")[-1])

        author = ", ".join(authors[:3]) if authors else None

        # Publication year
        pub_year = book.get("first_publish_year")
        if not pub_year and book.get("first_publish_date"):
            try:
                pub_year = int(book["first_publish_date"][:4])
            except (ValueError, TypeError):
                pass

        # ISBN - get first valid one
        isbn = None
        isbns = book.get("isbn", [])
        if isbns:
            for i in isbns:
                if len(i) in (10, 13):
                    isbn = i
                    break

        # Publisher
        publishers = book.get("publisher", [])
        publisher = publishers[0] if publishers else None

        # Build source URL
        key = book.get("key", "")
        if key:
            source_url = f"https://openlibrary.org{key}"
        else:
            source_url = None

        return {
            "title": title,
            "author": author,
            "publication_year": pub_year,
            "isbn": isbn,
            "publisher": publisher,
            "source": "openlibrary",
            "source_id": key,
            "source_url": source_url,
        }

    def scrape_books(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling-related books."""
        books_data = []
        books = self.search_wrestling_books(limit=limit)

        for book in books:
            parsed = self.parse_book_for_model(book)
            if parsed.get("title"):
                books_data.append(parsed)

        logger.info(f"Open Library: Scraped {len(books_data)} wrestling books")
        return books_data[:limit]


class GoogleBooksClient(APIClient):
    """
    Google Books API client.

    Free tier allows 1,000 queries/day without API key,
    or 1,000 queries/day with API key.

    API Documentation: https://developers.google.com/books/docs/v1/using
    """

    API_NAME = "googlebooks"
    BASE_URL = "https://www.googleapis.com/books/v1"
    REQUIRES_AUTH = False  # Works without key, but limited

    REQUESTS_PER_MINUTE = 10
    REQUESTS_PER_HOUR = 100
    REQUESTS_PER_DAY = 1000

    CACHE_TTL = 86400

    def __init__(self, api_key: Optional[str] = None):
        import os
        from django.conf import settings as django_settings

        api_key = api_key or os.getenv("GOOGLE_BOOKS_API_KEY") or getattr(
            django_settings, "GOOGLE_BOOKS_API_KEY", None
        )
        super().__init__(api_key)

    @with_error_handling
    def search_books(
        self,
        query: str,
        start_index: int = 0,
        max_results: int = 20,
    ) -> List[Dict[str, Any]]:
        """Search for books."""
        params = {
            "q": query,
            "startIndex": start_index,
            "maxResults": min(max_results, 40),  # API max is 40
            "printType": "books",
        }

        if self.api_key:
            params["key"] = self.api_key

        data = self.request("/volumes", params=params)
        if not data:
            return []

        return data.get("items", [])

    @with_error_handling
    def get_book_details(self, volume_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed book information."""
        params = {}
        if self.api_key:
            params["key"] = self.api_key

        data = self.request(f"/volumes/{volume_id}", params=params)
        return data

    def search_wrestling_books(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Search for wrestling-related books."""
        books = []
        seen_ids = set()

        search_terms = [
            "professional wrestling",
            "WWE biography",
            "wrestling history",
            "pro wrestling memoir",
        ]

        for term in search_terms:
            if len(books) >= limit:
                break

            results = self.search_books(term, max_results=20)
            for book in results:
                book_id = book.get("id")
                if book_id and book_id not in seen_ids:
                    seen_ids.add(book_id)
                    books.append(book)

        return books[:limit]

    def parse_book_for_model(self, book: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Google Books data to our Book model format."""
        info = book.get("volumeInfo", {})

        title = info.get("title", "")
        authors = info.get("authors", [])
        author = ", ".join(authors[:3]) if authors else None

        # Publication year
        pub_date = info.get("publishedDate", "")
        pub_year = None
        if pub_date:
            try:
                pub_year = int(pub_date[:4])
            except (ValueError, TypeError):
                pass

        # ISBN
        isbn = None
        for identifier in info.get("industryIdentifiers", []):
            if identifier.get("type") in ("ISBN_13", "ISBN_10"):
                isbn = identifier.get("identifier")
                break

        publisher = info.get("publisher")

        return {
            "title": title,
            "author": author,
            "publication_year": pub_year,
            "isbn": isbn,
            "publisher": publisher,
            "about": info.get("description", "")[:500] if info.get("description") else None,
            "source": "googlebooks",
            "source_id": book.get("id"),
            "source_url": info.get("infoLink"),
        }

    def scrape_books(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scrape wrestling-related books."""
        books_data = []
        books = self.search_wrestling_books(limit=limit)

        for book in books:
            parsed = self.parse_book_for_model(book)
            if parsed.get("title"):
                books_data.append(parsed)

        logger.info(f"Google Books: Scraped {len(books_data)} wrestling books")
        return books_data[:limit]
