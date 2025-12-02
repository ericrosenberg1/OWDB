"""
Scraper coordinator - orchestrates multiple scrapers and handles data import.

This module:
1. Coordinates scraping across multiple sources (web scrapers + APIs)
2. Validates and deduplicates data
3. Merges data from multiple sources
4. Imports clean data into the database
5. Reports errors and statistics
"""

import hashlib
import logging
import re
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify

from .api_client import ErrorReporter

logger = logging.getLogger(__name__)


class DataValidator:
    """Validates and normalizes scraped data."""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a name for comparison."""
        if not name:
            return ""
        name = name.lower().strip()
        name = re.sub(r"[^\w\s]", "", name)
        name = " ".join(name.split())
        return name

    @staticmethod
    def similarity(a: str, b: str) -> float:
        """Calculate string similarity (0.0 to 1.0)."""
        if not a or not b:
            return 0.0
        return SequenceMatcher(
            None, DataValidator.normalize_name(a), DataValidator.normalize_name(b)
        ).ratio()

    @staticmethod
    def validate_year(year: Any) -> Optional[int]:
        """Validate a year value."""
        if year is None:
            return None
        try:
            year = int(year)
            if 1900 <= year <= datetime.now().year + 1:
                return year
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def validate_date(date_str: Any) -> Optional[str]:
        """Validate a date string (YYYY-MM-DD format)."""
        if not date_str:
            return None
        try:
            if isinstance(date_str, str):
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                if 1900 <= dt.year <= datetime.now().year + 1:
                    return date_str
        except ValueError:
            pass
        return None

    @staticmethod
    def validate_url(url: Any) -> Optional[str]:
        """Validate a URL."""
        if not url:
            return None
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url[:500]
        return None

    @staticmethod
    def validate_isbn(isbn: Any) -> Optional[str]:
        """Validate an ISBN."""
        if not isbn:
            return None
        isbn = str(isbn).replace("-", "").replace(" ", "")
        if len(isbn) in (10, 13) and isbn.replace("X", "").isdigit():
            return isbn
        return None

    @staticmethod
    def validate_wrestler(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean wrestler data."""
        if not data.get("name"):
            return False, {}

        cleaned = {
            "name": data["name"].strip()[:255],
            "slug": slugify(data["name"])[:255],
        }

        if data.get("real_name"):
            cleaned["real_name"] = data["real_name"].strip()[:255]
        if data.get("aliases"):
            cleaned["aliases"] = data["aliases"].strip()[:1000]
        if data.get("hometown"):
            cleaned["hometown"] = data["hometown"].strip()[:255]
        if data.get("nationality"):
            cleaned["nationality"] = data["nationality"].strip()[:255]
        if data.get("finishers"):
            cleaned["finishers"] = data["finishers"].strip()[:1000]

        debut = DataValidator.validate_year(data.get("debut_year"))
        if debut:
            cleaned["debut_year"] = debut

        retirement = DataValidator.validate_year(data.get("retirement_year"))
        if retirement:
            cleaned["retirement_year"] = retirement

        return True, cleaned

    @staticmethod
    def validate_promotion(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean promotion data."""
        if not data.get("name"):
            return False, {}

        cleaned = {
            "name": data["name"].strip()[:255],
            "slug": slugify(data["name"])[:255],
        }

        if data.get("abbreviation"):
            cleaned["abbreviation"] = data["abbreviation"].strip()[:50]

        founded = DataValidator.validate_year(data.get("founded_year"))
        if founded:
            cleaned["founded_year"] = founded

        closed = DataValidator.validate_year(data.get("closed_year"))
        if closed:
            cleaned["closed_year"] = closed

        website = DataValidator.validate_url(data.get("website"))
        if website:
            cleaned["website"] = website

        return True, cleaned

    @staticmethod
    def validate_event(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean event data."""
        if not data.get("name") or not data.get("date"):
            return False, {}

        date = DataValidator.validate_date(data["date"])
        if not date:
            return False, {}

        cleaned = {
            "name": data["name"].strip()[:255],
            "date": date,
        }

        slug_base = f"{data['name']}-{date[:4]}"
        cleaned["slug"] = slugify(slug_base)[:255]

        if data.get("venue_name"):
            cleaned["venue_name"] = data["venue_name"].strip()[:255]
        if data.get("venue_location"):
            cleaned["venue_location"] = data["venue_location"].strip()[:255]
        if data.get("attendance"):
            try:
                cleaned["attendance"] = int(data["attendance"])
            except (ValueError, TypeError):
                pass
        if data.get("promotion_name"):
            cleaned["promotion_name"] = data["promotion_name"].strip()[:255]
        if data.get("matches"):
            cleaned["matches"] = data["matches"]

        return True, cleaned

    @staticmethod
    def validate_videogame(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean video game data."""
        if not data.get("name"):
            return False, {}

        cleaned = {
            "name": data["name"].strip()[:255],
            "slug": slugify(data["name"])[:255],
        }

        release = DataValidator.validate_year(data.get("release_year"))
        if release:
            cleaned["release_year"] = release

        if data.get("systems"):
            cleaned["systems"] = data["systems"].strip()[:255]
        if data.get("developer"):
            cleaned["developer"] = data["developer"].strip()[:255]
        if data.get("publisher"):
            cleaned["publisher"] = data["publisher"].strip()[:255]
        if data.get("about"):
            cleaned["about"] = data["about"].strip()[:1000]

        return True, cleaned

    @staticmethod
    def validate_book(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean book data."""
        if not data.get("title"):
            return False, {}

        cleaned = {
            "title": data["title"].strip()[:255],
            "slug": slugify(data["title"])[:255],
        }

        if data.get("author"):
            cleaned["author"] = data["author"].strip()[:255]

        pub_year = DataValidator.validate_year(data.get("publication_year"))
        if pub_year:
            cleaned["publication_year"] = pub_year

        isbn = DataValidator.validate_isbn(data.get("isbn"))
        if isbn:
            cleaned["isbn"] = isbn

        if data.get("publisher"):
            cleaned["publisher"] = data["publisher"].strip()[:255]
        if data.get("about"):
            cleaned["about"] = data["about"].strip()[:1000]

        return True, cleaned

    @staticmethod
    def validate_podcast(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean podcast data."""
        if not data.get("name"):
            return False, {}

        cleaned = {
            "name": data["name"].strip()[:255],
            "slug": slugify(data["name"])[:255],
        }

        if data.get("hosts"):
            cleaned["hosts"] = data["hosts"].strip()[:500]

        launch = DataValidator.validate_year(data.get("launch_year"))
        if launch:
            cleaned["launch_year"] = launch

        end = DataValidator.validate_year(data.get("end_year"))
        if end:
            cleaned["end_year"] = end

        url = DataValidator.validate_url(data.get("url"))
        if url:
            cleaned["url"] = url

        if data.get("about"):
            cleaned["about"] = data["about"].strip()[:1000]

        return True, cleaned

    @staticmethod
    def validate_special(data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Validate and clean special (movie/TV) data."""
        if not data.get("title"):
            return False, {}

        cleaned = {
            "title": data["title"].strip()[:255],
            "slug": slugify(data["title"])[:255],
        }

        release = DataValidator.validate_year(data.get("release_year"))
        if release:
            cleaned["release_year"] = release

        valid_types = ["documentary", "movie", "tv_special", "series", "other"]
        special_type = data.get("type", "other")
        cleaned["type"] = special_type if special_type in valid_types else "other"

        if data.get("about"):
            cleaned["about"] = data["about"].strip()[:1000]

        return True, cleaned


class DataDeduplicator:
    """Handles deduplication of scraped data across all sources."""

    SIMILARITY_THRESHOLD = 0.85

    def __init__(self):
        self._wrestler_cache: Dict[str, int] = {}
        self._promotion_cache: Dict[str, int] = {}
        self._event_cache: Dict[str, int] = {}
        self._videogame_cache: Dict[str, int] = {}
        self._book_cache: Dict[str, int] = {}
        self._podcast_cache: Dict[str, int] = {}
        self._special_cache: Dict[str, int] = {}

    def _generate_fingerprint(self, text: str) -> str:
        """Generate a fingerprint for deduplication."""
        normalized = DataValidator.normalize_name(text)
        return hashlib.md5(normalized.encode()).hexdigest()

    def find_duplicate_wrestler(self, name: str, aliases: str = "") -> Optional[int]:
        """Find a duplicate wrestler by name or aliases."""
        from ..models import Wrestler

        normalized = DataValidator.normalize_name(name)
        if normalized in self._wrestler_cache:
            return self._wrestler_cache[normalized]

        wrestlers = Wrestler.objects.filter(
            Q(name__iexact=name) | Q(aliases__icontains=name)
        )

        for wrestler in wrestlers:
            if DataValidator.similarity(name, wrestler.name) >= self.SIMILARITY_THRESHOLD:
                self._wrestler_cache[normalized] = wrestler.id
                return wrestler.id

            if wrestler.aliases:
                for alias in wrestler.get_aliases_list():
                    if DataValidator.similarity(name, alias) >= self.SIMILARITY_THRESHOLD:
                        self._wrestler_cache[normalized] = wrestler.id
                        return wrestler.id

        if aliases:
            for alias in aliases.split(","):
                alias = alias.strip()
                if alias:
                    wrestlers = Wrestler.objects.filter(
                        Q(name__iexact=alias) | Q(aliases__icontains=alias)
                    )
                    for wrestler in wrestlers:
                        if DataValidator.similarity(alias, wrestler.name) >= self.SIMILARITY_THRESHOLD:
                            self._wrestler_cache[normalized] = wrestler.id
                            return wrestler.id

        return None

    def find_duplicate_promotion(self, name: str, abbreviation: str = "") -> Optional[int]:
        """Find a duplicate promotion by name or abbreviation."""
        from ..models import Promotion

        normalized = DataValidator.normalize_name(name)
        if normalized in self._promotion_cache:
            return self._promotion_cache[normalized]

        promotions = Promotion.objects.filter(
            Q(name__iexact=name)
            | Q(abbreviation__iexact=name)
            | Q(abbreviation__iexact=abbreviation)
        )

        for promotion in promotions:
            if DataValidator.similarity(name, promotion.name) >= self.SIMILARITY_THRESHOLD:
                self._promotion_cache[normalized] = promotion.id
                return promotion.id

            if abbreviation and promotion.abbreviation:
                if abbreviation.lower() == promotion.abbreviation.lower():
                    self._promotion_cache[normalized] = promotion.id
                    return promotion.id

        return None

    def find_duplicate_event(self, name: str, date: str, promotion_name: str = "") -> Optional[int]:
        """Find a duplicate event by name, date, and promotion."""
        from ..models import Event

        cache_key = f"{DataValidator.normalize_name(name)}:{date}"
        if cache_key in self._event_cache:
            return self._event_cache[cache_key]

        events = Event.objects.filter(date=date)
        for event in events:
            if DataValidator.similarity(name, event.name) >= self.SIMILARITY_THRESHOLD:
                self._event_cache[cache_key] = event.id
                return event.id

        return None

    def find_duplicate_videogame(self, name: str, release_year: Optional[int] = None) -> Optional[int]:
        """Find a duplicate video game by name and optional year."""
        from ..models import VideoGame

        normalized = DataValidator.normalize_name(name)
        cache_key = f"{normalized}:{release_year or ''}"

        if cache_key in self._videogame_cache:
            return self._videogame_cache[cache_key]

        games = VideoGame.objects.filter(name__iexact=name)
        if release_year:
            games = games.filter(release_year=release_year)

        for game in games:
            if DataValidator.similarity(name, game.name) >= self.SIMILARITY_THRESHOLD:
                self._videogame_cache[cache_key] = game.id
                return game.id

        # Fallback: check without year
        all_games = VideoGame.objects.all()
        for game in all_games:
            if DataValidator.similarity(name, game.name) >= 0.95:  # Higher threshold without year
                self._videogame_cache[cache_key] = game.id
                return game.id

        return None

    def find_duplicate_book(self, title: str, author: Optional[str] = None, isbn: Optional[str] = None) -> Optional[int]:
        """Find a duplicate book by title, author, or ISBN."""
        from ..models import Book

        # ISBN is the most reliable identifier
        if isbn:
            books = Book.objects.filter(isbn=isbn)
            if books.exists():
                return books.first().id

        normalized = DataValidator.normalize_name(title)
        cache_key = f"{normalized}:{author or ''}"

        if cache_key in self._book_cache:
            return self._book_cache[cache_key]

        books = Book.objects.filter(title__iexact=title)
        for book in books:
            if DataValidator.similarity(title, book.title) >= self.SIMILARITY_THRESHOLD:
                self._book_cache[cache_key] = book.id
                return book.id

        return None

    def find_duplicate_podcast(self, name: str) -> Optional[int]:
        """Find a duplicate podcast by name."""
        from ..models import Podcast

        normalized = DataValidator.normalize_name(name)
        if normalized in self._podcast_cache:
            return self._podcast_cache[normalized]

        podcasts = Podcast.objects.filter(name__iexact=name)
        for podcast in podcasts:
            if DataValidator.similarity(name, podcast.name) >= self.SIMILARITY_THRESHOLD:
                self._podcast_cache[normalized] = podcast.id
                return podcast.id

        return None

    def find_duplicate_special(self, title: str, release_year: Optional[int] = None) -> Optional[int]:
        """Find a duplicate special (movie/TV) by title and year."""
        from ..models import Special

        normalized = DataValidator.normalize_name(title)
        cache_key = f"{normalized}:{release_year or ''}"

        if cache_key in self._special_cache:
            return self._special_cache[cache_key]

        specials = Special.objects.filter(title__iexact=title)
        if release_year:
            specials = specials.filter(release_year=release_year)

        for special in specials:
            if DataValidator.similarity(title, special.title) >= self.SIMILARITY_THRESHOLD:
                self._special_cache[cache_key] = special.id
                return special.id

        return None


class ScraperCoordinator:
    """
    Coordinates multiple scrapers and API clients for data import.
    """

    def __init__(self):
        # Lazy load scrapers and API clients to avoid import issues
        self._scrapers = None
        self._api_clients = None
        self.validator = DataValidator()
        self.deduplicator = DataDeduplicator()

    @property
    def scrapers(self):
        """Lazy load web scrapers."""
        if self._scrapers is None:
            from .wikipedia import WikipediaScraper
            from .cagematch import CagematchScraper
            from .profightdb import ProFightDBScraper

            self._scrapers = {
                "wikipedia": WikipediaScraper(),
                "cagematch": CagematchScraper(),
                "profightdb": ProFightDBScraper(),
            }
        return self._scrapers

    @property
    def api_clients(self):
        """Lazy load API clients."""
        if self._api_clients is None:
            from .tmdb import TMDBClient
            from .rawg import RAWGClient, IGDBClient
            from .openlibrary import OpenLibraryClient, GoogleBooksClient
            from .podcasts import PodcastIndexClient, ITunesPodcastClient

            self._api_clients = {
                "tmdb": TMDBClient(),
                "rawg": RAWGClient(),
                "igdb": IGDBClient(),
                "openlibrary": OpenLibraryClient(),
                "googlebooks": GoogleBooksClient(),
                "podcastindex": PodcastIndexClient(),
                "itunes": ITunesPodcastClient(),
            }
        return self._api_clients

    def get_scraper(self, name: str):
        """Get a scraper by name."""
        return self.scrapers.get(name)

    def get_api_client(self, name: str):
        """Get an API client by name."""
        return self.api_clients.get(name)

    # =========================================================================
    # Import methods for each model type
    # =========================================================================

    @transaction.atomic
    def import_wrestler(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a wrestler to the database."""
        from ..models import Wrestler

        valid, cleaned = DataValidator.validate_wrestler(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_wrestler(
            cleaned["name"], cleaned.get("aliases", "")
        )

        if existing_id:
            wrestler = Wrestler.objects.get(id=existing_id)
            updated = False

            for field in ["real_name", "aliases", "hometown", "nationality", "finishers"]:
                if cleaned.get(field) and not getattr(wrestler, field, None):
                    setattr(wrestler, field, cleaned[field])
                    updated = True

            for field in ["debut_year", "retirement_year"]:
                if cleaned.get(field) and not getattr(wrestler, field, None):
                    setattr(wrestler, field, cleaned[field])
                    updated = True

            if updated:
                wrestler.save()
                logger.debug(f"Updated wrestler: {wrestler.name}")

            return existing_id

        wrestler = Wrestler.objects.create(**cleaned)
        logger.info(f"Created wrestler: {wrestler.name}")
        return wrestler.id

    @transaction.atomic
    def import_promotion(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a promotion to the database."""
        from ..models import Promotion

        valid, cleaned = DataValidator.validate_promotion(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_promotion(
            cleaned["name"], cleaned.get("abbreviation", "")
        )

        if existing_id:
            promotion = Promotion.objects.get(id=existing_id)
            updated = False

            for field in ["abbreviation", "website"]:
                if cleaned.get(field) and not getattr(promotion, field, None):
                    setattr(promotion, field, cleaned[field])
                    updated = True

            for field in ["founded_year", "closed_year"]:
                if cleaned.get(field) and not getattr(promotion, field, None):
                    setattr(promotion, field, cleaned[field])
                    updated = True

            if updated:
                promotion.save()
                logger.debug(f"Updated promotion: {promotion.name}")

            return existing_id

        promotion = Promotion.objects.create(**cleaned)
        logger.info(f"Created promotion: {promotion.name}")
        return promotion.id

    @transaction.atomic
    def import_event(self, data: Dict[str, Any]) -> Optional[int]:
        """Import an event to the database."""
        from ..models import Event, Venue, Promotion

        valid, cleaned = DataValidator.validate_event(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_event(
            cleaned["name"],
            cleaned["date"],
            cleaned.get("promotion_name", ""),
        )

        if existing_id:
            logger.debug(f"Event already exists: {cleaned['name']}")
            return existing_id

        venue = None
        if cleaned.get("venue_name"):
            venue, _ = Venue.objects.get_or_create(
                name=cleaned["venue_name"],
                defaults={
                    "slug": slugify(cleaned["venue_name"]),
                    "location": cleaned.get("venue_location", ""),
                },
            )

        promotion = None
        if cleaned.get("promotion_name"):
            promotion_id = self.deduplicator.find_duplicate_promotion(
                cleaned["promotion_name"]
            )
            if promotion_id:
                promotion = Promotion.objects.get(id=promotion_id)
            else:
                promotion, _ = Promotion.objects.get_or_create(
                    name=cleaned["promotion_name"],
                    defaults={"slug": slugify(cleaned["promotion_name"])},
                )

        if not promotion:
            logger.warning(f"No promotion for event: {cleaned['name']}")
            return None

        event = Event.objects.create(
            name=cleaned["name"],
            slug=cleaned["slug"],
            date=cleaned["date"],
            venue=venue,
            promotion=promotion,
            attendance=cleaned.get("attendance"),
        )

        if cleaned.get("matches"):
            self._import_matches(event, cleaned["matches"])

        logger.info(f"Created event: {event.name}")
        return event.id

    def _import_matches(self, event, matches: List[Dict[str, Any]]):
        """Import matches for an event."""
        from ..models import Match

        for i, match_data in enumerate(matches):
            if not match_data.get("match_text"):
                continue

            Match.objects.create(
                event=event,
                match_text=match_data["match_text"][:1000],
                result=match_data.get("result", "")[:255],
                match_type=match_data.get("match_type", "")[:255],
                match_order=i + 1,
            )

    @transaction.atomic
    def import_videogame(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a video game to the database."""
        from ..models import VideoGame

        valid, cleaned = DataValidator.validate_videogame(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_videogame(
            cleaned["name"], cleaned.get("release_year")
        )

        if existing_id:
            game = VideoGame.objects.get(id=existing_id)
            updated = False

            for field in ["systems", "developer", "publisher", "about"]:
                if cleaned.get(field) and not getattr(game, field, None):
                    setattr(game, field, cleaned[field])
                    updated = True

            if cleaned.get("release_year") and not game.release_year:
                game.release_year = cleaned["release_year"]
                updated = True

            if updated:
                game.save()
                logger.debug(f"Updated video game: {game.name}")

            return existing_id

        game = VideoGame.objects.create(**cleaned)
        logger.info(f"Created video game: {game.name}")
        return game.id

    @transaction.atomic
    def import_book(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a book to the database."""
        from ..models import Book

        valid, cleaned = DataValidator.validate_book(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_book(
            cleaned["title"],
            cleaned.get("author"),
            cleaned.get("isbn"),
        )

        if existing_id:
            book = Book.objects.get(id=existing_id)
            updated = False

            for field in ["author", "isbn", "publisher", "about"]:
                if cleaned.get(field) and not getattr(book, field, None):
                    setattr(book, field, cleaned[field])
                    updated = True

            if cleaned.get("publication_year") and not book.publication_year:
                book.publication_year = cleaned["publication_year"]
                updated = True

            if updated:
                book.save()
                logger.debug(f"Updated book: {book.title}")

            return existing_id

        book = Book.objects.create(**cleaned)
        logger.info(f"Created book: {book.title}")
        return book.id

    @transaction.atomic
    def import_podcast(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a podcast to the database."""
        from ..models import Podcast

        valid, cleaned = DataValidator.validate_podcast(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_podcast(cleaned["name"])

        if existing_id:
            podcast = Podcast.objects.get(id=existing_id)
            updated = False

            for field in ["hosts", "url", "about"]:
                if cleaned.get(field) and not getattr(podcast, field, None):
                    setattr(podcast, field, cleaned[field])
                    updated = True

            for field in ["launch_year", "end_year"]:
                if cleaned.get(field) and not getattr(podcast, field, None):
                    setattr(podcast, field, cleaned[field])
                    updated = True

            if updated:
                podcast.save()
                logger.debug(f"Updated podcast: {podcast.name}")

            return existing_id

        podcast = Podcast.objects.create(**cleaned)
        logger.info(f"Created podcast: {podcast.name}")
        return podcast.id

    @transaction.atomic
    def import_special(self, data: Dict[str, Any]) -> Optional[int]:
        """Import a special (movie/TV) to the database."""
        from ..models import Special

        valid, cleaned = DataValidator.validate_special(data)
        if not valid:
            return None

        existing_id = self.deduplicator.find_duplicate_special(
            cleaned["title"], cleaned.get("release_year")
        )

        if existing_id:
            special = Special.objects.get(id=existing_id)
            updated = False

            if cleaned.get("about") and not special.about:
                special.about = cleaned["about"]
                updated = True

            if cleaned.get("release_year") and not special.release_year:
                special.release_year = cleaned["release_year"]
                updated = True

            if updated:
                special.save()
                logger.debug(f"Updated special: {special.title}")

            return existing_id

        special = Special.objects.create(**cleaned)
        logger.info(f"Created special: {special.title}")
        return special.id

    # =========================================================================
    # Scraping orchestration
    # =========================================================================

    def scrape_and_import(
        self,
        source: str = "all",
        data_type: str = "all",
        limit: int = 100,
    ) -> Dict[str, int]:
        """
        Scrape data from sources and import to database.

        Args:
            source: Scraper/API name or "all"
            data_type: Model type or "all"
            limit: Maximum items to scrape per type

        Returns:
            Dictionary with counts of imported items
        """
        results = {
            "wrestlers_scraped": 0,
            "wrestlers_imported": 0,
            "promotions_scraped": 0,
            "promotions_imported": 0,
            "events_scraped": 0,
            "events_imported": 0,
            "videogames_scraped": 0,
            "videogames_imported": 0,
            "books_scraped": 0,
            "books_imported": 0,
            "podcasts_scraped": 0,
            "podcasts_imported": 0,
            "specials_scraped": 0,
            "specials_imported": 0,
            "errors": 0,
        }

        # Web scrapers
        if source in ("all", "scrapers"):
            for scraper in self.scrapers.values():
                self._run_scraper(scraper, data_type, limit, results)
        elif source in self.scrapers:
            self._run_scraper(self.scrapers[source], data_type, limit, results)

        # API clients
        if source in ("all", "apis"):
            for client in self.api_clients.values():
                self._run_api_client(client, data_type, limit, results)
        elif source in self.api_clients:
            self._run_api_client(self.api_clients[source], data_type, limit, results)

        logger.info(f"Scraping complete: {results}")
        return results

    def _run_scraper(self, scraper, data_type: str, limit: int, results: Dict):
        """Run a web scraper and update results."""
        source_name = getattr(scraper, "SOURCE_NAME", "unknown")
        logger.info(f"Scraping from {source_name}")

        if data_type in ("all", "wrestlers"):
            try:
                wrestlers = scraper.scrape_wrestlers(limit=limit)
                results["wrestlers_scraped"] += len(wrestlers)
                for data in wrestlers:
                    if self.import_wrestler(data):
                        results["wrestlers_imported"] += 1
            except Exception as e:
                logger.error(f"Error scraping wrestlers from {source_name}: {e}")
                results["errors"] += 1

        if data_type in ("all", "promotions"):
            try:
                promotions = scraper.scrape_promotions(limit=limit)
                results["promotions_scraped"] += len(promotions)
                for data in promotions:
                    if self.import_promotion(data):
                        results["promotions_imported"] += 1
            except Exception as e:
                logger.error(f"Error scraping promotions from {source_name}: {e}")
                results["errors"] += 1

        if data_type in ("all", "events"):
            try:
                events = scraper.scrape_events(limit=limit)
                results["events_scraped"] += len(events)
                for data in events:
                    if self.import_event(data):
                        results["events_imported"] += 1
            except Exception as e:
                logger.error(f"Error scraping events from {source_name}: {e}")
                results["errors"] += 1

    def _run_api_client(self, client, data_type: str, limit: int, results: Dict):
        """Run an API client and update results."""
        api_name = getattr(client, "API_NAME", "unknown")
        logger.info(f"Fetching from API: {api_name}")

        # TMDB for specials (movies/TV)
        if api_name == "tmdb" and data_type in ("all", "specials"):
            try:
                specials = client.scrape_specials(limit=limit)
                results["specials_scraped"] += len(specials)
                for data in specials:
                    if self.import_special(data):
                        results["specials_imported"] += 1
            except Exception as e:
                logger.error(f"Error fetching specials from {api_name}: {e}")
                results["errors"] += 1

        # RAWG/IGDB for video games
        if api_name in ("rawg", "igdb") and data_type in ("all", "videogames"):
            try:
                games = client.scrape_videogames(limit=limit)
                results["videogames_scraped"] += len(games)
                for data in games:
                    if self.import_videogame(data):
                        results["videogames_imported"] += 1
            except Exception as e:
                logger.error(f"Error fetching videogames from {api_name}: {e}")
                results["errors"] += 1

        # OpenLibrary/GoogleBooks for books
        if api_name in ("openlibrary", "googlebooks") and data_type in ("all", "books"):
            try:
                books = client.scrape_books(limit=limit)
                results["books_scraped"] += len(books)
                for data in books:
                    if self.import_book(data):
                        results["books_imported"] += 1
            except Exception as e:
                logger.error(f"Error fetching books from {api_name}: {e}")
                results["errors"] += 1

        # Podcast APIs
        if api_name in ("podcastindex", "itunes") and data_type in ("all", "podcasts"):
            try:
                podcasts = client.scrape_podcasts(limit=limit)
                results["podcasts_scraped"] += len(podcasts)
                for data in podcasts:
                    if self.import_podcast(data):
                        results["podcasts_imported"] += 1
            except Exception as e:
                logger.error(f"Error fetching podcasts from {api_name}: {e}")
                results["errors"] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all scrapers and API clients."""
        stats = {
            "scrapers": {},
            "api_clients": {},
            "errors": ErrorReporter.get_errors(),
        }

        for name, scraper in self.scrapers.items():
            stats["scrapers"][name] = scraper.get_stats()

        for name, client in self.api_clients.items():
            stats["api_clients"][name] = client.get_status()

        return stats

    def get_errors(self, api_name: Optional[str] = None) -> List[Dict]:
        """Get reported errors."""
        return ErrorReporter.get_errors(api_name)

    def clear_errors(self, api_name: Optional[str] = None):
        """Clear reported errors."""
        ErrorReporter.clear_errors(api_name)
