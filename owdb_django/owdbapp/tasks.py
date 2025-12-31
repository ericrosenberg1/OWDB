from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.core.cache import cache
from django.db.models import Count

import logging
import random

logger = logging.getLogger(__name__)


# =============================================================================
# Task Time Limits - Prevents tasks from freezing indefinitely
# =============================================================================
# soft_time_limit: Task receives SoftTimeLimitExceeded, can cleanup
# time_limit: Task is forcefully killed (hard limit)

SCRAPER_SOFT_LIMIT = 10 * 60  # 10 minutes for scrapers
SCRAPER_HARD_LIMIT = 12 * 60  # 12 minutes hard kill

IMAGE_FETCH_SOFT_LIMIT = 5 * 60  # 5 minutes for image fetching
IMAGE_FETCH_HARD_LIMIT = 7 * 60  # 7 minutes hard kill


# =============================================================================
# Scraping Tasks
# =============================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_wikipedia_wrestlers(self, limit: int = 50, rotate_category: bool = True):
    """
    Scrape wrestler data from Wikipedia.

    Uses category rotation by default to stay within rate limits.
    Each run scrapes only ONE category, cycling through all categories
    across multiple runs.

    Args:
        limit: Max wrestlers to scrape per category
        rotate_category: If True (default), scrape one category per run and rotate
    """
    lock_key = "scrape_wikipedia_wrestlers_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Wikipedia wrestler scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import WikipediaScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = WikipediaScraper()
        coordinator = ScraperCoordinator()

        wrestlers = scraper.scrape_wrestlers(limit=limit, rotate_category=rotate_category)
        imported = 0

        for wrestler_data in wrestlers:
            wrestler_id = coordinator.import_wrestler(wrestler_data)
            if wrestler_id:
                imported += 1

        logger.info(f"Wikipedia wrestlers: scraped {len(wrestlers)}, imported {imported}")
        return {"scraped": len(wrestlers), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("Wikipedia wrestler scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia wrestler scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_wikipedia_promotions(self, limit: int = 25, rotate_category: bool = True):
    """
    Scrape promotion data from Wikipedia.

    Uses category rotation by default to stay within rate limits.
    """
    lock_key = "scrape_wikipedia_promotions_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Wikipedia promotion scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import WikipediaScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = WikipediaScraper()
        coordinator = ScraperCoordinator()

        promotions = scraper.scrape_promotions(limit=limit, rotate_category=rotate_category)
        imported = 0

        for promotion_data in promotions:
            promotion_id = coordinator.import_promotion(promotion_data)
            if promotion_id:
                imported += 1

        logger.info(f"Wikipedia promotions: scraped {len(promotions)}, imported {imported}")
        return {"scraped": len(promotions), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("Wikipedia promotion scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia promotion scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_wikipedia_events(self, limit: int = 50, rotate_category: bool = True):
    """
    Scrape event data from Wikipedia.

    Uses category rotation by default to stay within rate limits.
    """
    lock_key = "scrape_wikipedia_events_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Wikipedia event scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import WikipediaScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = WikipediaScraper()
        coordinator = ScraperCoordinator()

        events = scraper.scrape_events(limit=limit, rotate_category=rotate_category)
        imported = 0

        for event_data in events:
            event_id = coordinator.import_event(event_data)
            if event_id:
                imported += 1

        logger.info(f"Wikipedia events: scraped {len(events)}, imported {imported}")
        return {"scraped": len(events), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("Wikipedia events scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia event scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_cagematch_wrestlers(self, limit: int = 25):
    """
    Scrape wrestler data from Cagematch.
    Lower limits due to more restrictive rate limiting.
    """
    lock_key = "scrape_cagematch_wrestlers_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Cagematch wrestler scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import CagematchScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = CagematchScraper()
        coordinator = ScraperCoordinator()

        wrestlers = scraper.scrape_wrestlers(limit=limit)
        imported = 0

        for wrestler_data in wrestlers:
            wrestler_id = coordinator.import_wrestler(wrestler_data)
            if wrestler_id:
                imported += 1

        logger.info(f"Cagematch wrestlers: scraped {len(wrestlers)}, imported {imported}")
        return {"scraped": len(wrestlers), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("Cagematch wrestler scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        logger.error(f"Cagematch unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Cagematch wrestler scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_cagematch_events(self, limit: int = 25):
    """Scrape recent events from Cagematch."""
    lock_key = "scrape_cagematch_events_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Cagematch event scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import CagematchScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = CagematchScraper()
        coordinator = ScraperCoordinator()

        events = scraper.scrape_events(limit=limit)
        imported = 0

        for event_data in events:
            event_id = coordinator.import_event(event_data)
            if event_id:
                imported += 1

        logger.info(f"Cagematch events: scraped {len(events)}, imported {imported}")
        return {"scraped": len(events), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("Cagematch events scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        logger.error(f"Cagematch unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Cagematch event scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_profightdb_wrestlers(self, limit: int = 25):
    """Scrape wrestler data from ProFightDB."""
    lock_key = "scrape_profightdb_wrestlers_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("ProFightDB wrestler scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import ProFightDBScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = ProFightDBScraper()
        coordinator = ScraperCoordinator()

        wrestlers = scraper.scrape_wrestlers(limit=limit)
        imported = 0

        for wrestler_data in wrestlers:
            wrestler_id = coordinator.import_wrestler(wrestler_data)
            if wrestler_id:
                imported += 1

        logger.info(f"ProFightDB wrestlers: scraped {len(wrestlers)}, imported {imported}")
        return {"scraped": len(wrestlers), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("ProFightDB wrestler scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        # Don't retry if the source is completely unavailable (SSL errors, etc.)
        logger.error(f"ProFightDB unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"ProFightDB wrestler scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=600,
    soft_time_limit=SCRAPER_SOFT_LIMIT,
    time_limit=SCRAPER_HARD_LIMIT,
)
def scrape_profightdb_events(self, limit: int = 25):
    """Scrape events from ProFightDB."""
    lock_key = "scrape_profightdb_events_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("ProFightDB event scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import ProFightDBScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = ProFightDBScraper()
        coordinator = ScraperCoordinator()

        events = scraper.scrape_events(limit=limit)
        imported = 0

        for event_data in events:
            event_id = coordinator.import_event(event_data)
            if event_id:
                imported += 1

        logger.info(f"ProFightDB events: scraped {len(events)}, imported {imported}")
        return {"scraped": len(events), "imported": imported}

    except SoftTimeLimitExceeded:
        logger.warning("ProFightDB events scrape exceeded time limit")
        return {"scraped": 0, "imported": 0, "status": "timeout"}

    except ScraperUnavailableError as e:
        # Don't retry if the source is completely unavailable (SSL errors, etc.)
        logger.error(f"ProFightDB unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"ProFightDB event scrape failed: {e}")
        raise self.retry(exc=e)
    finally:
        cache.delete(lock_key)


# =============================================================================
# API Tasks - Movies, Games, Books, Podcasts
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_tmdb_specials(self, limit: int = 30):
    """Fetch wrestling movies and TV shows from TMDB."""
    try:
        from .scrapers import TMDBClient, ScraperCoordinator

        client = TMDBClient()
        coordinator = ScraperCoordinator()

        specials = client.scrape_specials(limit=limit)
        imported = 0

        for special_data in specials:
            special_id = coordinator.import_special(special_data)
            if special_id:
                imported += 1

        logger.info(f"TMDB specials: scraped {len(specials)}, imported {imported}")
        return {"scraped": len(specials), "imported": imported}

    except Exception as e:
        logger.error(f"TMDB fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_rawg_videogames(self, limit: int = 30):
    """Fetch wrestling video games from RAWG."""
    try:
        from .scrapers import RAWGClient, ScraperCoordinator

        client = RAWGClient()
        coordinator = ScraperCoordinator()

        games = client.scrape_videogames(limit=limit)
        imported = 0

        for game_data in games:
            game_id = coordinator.import_videogame(game_data)
            if game_id:
                imported += 1

        logger.info(f"RAWG videogames: scraped {len(games)}, imported {imported}")
        return {"scraped": len(games), "imported": imported}

    except Exception as e:
        logger.error(f"RAWG fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_openlibrary_books(self, limit: int = 30):
    """Fetch wrestling books from Open Library (no auth required!)."""
    try:
        from .scrapers import OpenLibraryClient, ScraperCoordinator

        client = OpenLibraryClient()
        coordinator = ScraperCoordinator()

        books = client.scrape_books(limit=limit)
        imported = 0

        for book_data in books:
            book_id = coordinator.import_book(book_data)
            if book_id:
                imported += 1

        logger.info(f"Open Library books: scraped {len(books)}, imported {imported}")
        return {"scraped": len(books), "imported": imported}

    except Exception as e:
        logger.error(f"Open Library fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_googlebooks_books(self, limit: int = 30):
    """Fetch wrestling books from Google Books."""
    try:
        from .scrapers import GoogleBooksClient, ScraperCoordinator

        client = GoogleBooksClient()
        coordinator = ScraperCoordinator()

        books = client.scrape_books(limit=limit)
        imported = 0

        for book_data in books:
            book_id = coordinator.import_book(book_data)
            if book_id:
                imported += 1

        logger.info(f"Google Books: scraped {len(books)}, imported {imported}")
        return {"scraped": len(books), "imported": imported}

    except Exception as e:
        logger.error(f"Google Books fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_itunes_podcasts(self, limit: int = 30):
    """Fetch wrestling podcasts from iTunes (no auth required!)."""
    try:
        from .scrapers import ITunesPodcastClient, ScraperCoordinator

        client = ITunesPodcastClient()
        coordinator = ScraperCoordinator()

        podcasts = client.scrape_podcasts(limit=limit)
        imported = 0

        for podcast_data in podcasts:
            podcast_id = coordinator.import_podcast(podcast_data)
            if podcast_id:
                imported += 1

        logger.info(f"iTunes podcasts: scraped {len(podcasts)}, imported {imported}")
        return {"scraped": len(podcasts), "imported": imported}

    except Exception as e:
        logger.error(f"iTunes fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def fetch_podcastindex_podcasts(self, limit: int = 30):
    """Fetch wrestling podcasts from Podcast Index."""
    try:
        from .scrapers import PodcastIndexClient, ScraperCoordinator

        client = PodcastIndexClient()
        coordinator = ScraperCoordinator()

        podcasts = client.scrape_podcasts(limit=limit)
        imported = 0

        for podcast_data in podcasts:
            podcast_id = coordinator.import_podcast(podcast_data)
            if podcast_id:
                imported += 1

        logger.info(f"Podcast Index: scraped {len(podcasts)}, imported {imported}")
        return {"scraped": len(podcasts), "imported": imported}

    except Exception as e:
        logger.error(f"Podcast Index fetch failed: {e}")
        raise self.retry(exc=e)


# =============================================================================
# Master Orchestration Tasks
# =============================================================================

@shared_task
def run_all_scrapers():
    """
    Master task that coordinates all web scrapers.

    PARALLELIZED: Sources are independent (Wikipedia, Cagematch, ProFightDB)
    so they can run in parallel. Each source has its own rate limiter.
    """
    from celery import group

    # All sources run in parallel since they're independent
    # Each source has its own rate limiter, so no conflicts
    all_scraper_tasks = group(
        # Wikipedia tasks
        scrape_wikipedia_wrestlers.s(50),
        scrape_wikipedia_promotions.s(25),
        scrape_wikipedia_events.s(50),
        # Cagematch tasks
        scrape_cagematch_wrestlers.s(25),
        scrape_cagematch_events.s(25),
        # ProFightDB tasks
        scrape_profightdb_wrestlers.s(25),
        scrape_profightdb_events.s(25),
    )

    all_scraper_tasks.apply_async()
    logger.info("Started parallelized web scrapers workflow")
    return {"status": "started"}


@shared_task
def run_all_apis():
    """
    Master task that fetches from all APIs.
    APIs are generally more reliable and faster than web scraping.
    """
    from celery import group

    # APIs can run in parallel (different services, different rate limits)
    api_tasks = group(
        fetch_tmdb_specials.s(30),
        fetch_rawg_videogames.s(30),
        fetch_openlibrary_books.s(30),
        fetch_googlebooks_books.s(20),  # Lower limit - daily quota
        fetch_itunes_podcasts.s(30),
        fetch_podcastindex_podcasts.s(30),
    )

    api_tasks.apply_async()
    logger.info("Started API fetch workflow")
    return {"status": "started"}


@shared_task
def run_full_import():
    """
    Run a complete data import from all sources.
    Use sparingly - this is resource intensive!
    """
    from celery import chain

    # Run scrapers first, then APIs
    workflow = chain(
        run_all_scrapers.s(),
        run_all_apis.s(),
    )

    workflow.apply_async()
    logger.info("Started full import workflow")
    return {"status": "started"}


@shared_task
def get_scraper_stats():
    """Get current rate limit and scraping statistics."""
    from .scrapers import ScraperCoordinator

    coordinator = ScraperCoordinator()
    stats = coordinator.get_stats()

    # Cache the stats for display
    cache.set("scraper_stats", stats, timeout=300)

    logger.info(f"Scraper stats: {stats}")
    return stats


@shared_task
def reset_daily_api_limits():
    """Reset daily API request counts for all keys. Run daily via Celery Beat."""
    from .models import APIKey
    from django.utils import timezone

    today = timezone.now().date()
    updated = APIKey.objects.filter(last_reset__lt=today).update(
        requests_today=0,
        last_reset=today
    )
    logger.info(f"Reset daily limits for {updated} API keys")
    return updated


@shared_task
def warm_stats_cache():
    """Pre-compute and cache database statistics. Run every 5 minutes for real-time accuracy."""
    from .models import Wrestler, Promotion, Event, Match, Title, Venue, VideoGame, Podcast, Book, Special

    stats = {
        'wrestlers': Wrestler.objects.count(),
        'promotions': Promotion.objects.count(),
        'events': Event.objects.count(),
        'matches': Match.objects.count(),
        'titles': Title.objects.count(),
        'venues': Venue.objects.count(),
        'video_games': VideoGame.objects.count(),
        'podcasts': Podcast.objects.count(),
        'books': Book.objects.count(),
        'specials': Special.objects.count(),
    }

    # Cache for 10 minutes (task runs every 5 min, so always fresh)
    cache.set('homepage_stats', stats, timeout=600)
    logger.info(f"Warmed stats cache: {stats}")
    return stats


@shared_task
def cleanup_inactive_api_keys():
    """Remove API keys that haven't been used in 90 days. Run weekly."""
    from .models import APIKey
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = APIKey.objects.filter(
        last_used__lt=cutoff,
        is_paid=False
    ).delete()

    logger.info(f"Cleaned up {deleted} inactive API keys")
    return deleted


# =============================================================================
# Image Fetch Tasks (Wikimedia Commons CC Images)
# =============================================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=IMAGE_FETCH_SOFT_LIMIT,
    time_limit=IMAGE_FETCH_HARD_LIMIT,
)
def fetch_wrestler_images(self, batch_size: int = 20, refresh_old: bool = True):
    """
    Fetch CC-licensed images for wrestlers and cache to R2.

    - Fetches images for wrestlers without images
    - Optionally refreshes images older than 30 days with better alternatives
    - Caches all images to Cloudflare R2 CDN
    - Archives old images to history for users to browse

    Runs every 6 hours via Celery Beat.
    """
    try:
        from .models import Wrestler
        from .scrapers import WikimediaCommonsClient
        from .services import get_image_cache_service
        from django.db.models import Q
        from django.utils import timezone
        from datetime import timedelta

        client = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        fetched = 0
        refreshed = 0

        # 1. First, fetch images for wrestlers without any image
        wrestlers_no_image = Wrestler.objects.filter(
            image_url__isnull=True
        ).annotate(
            match_count=Count('matches')
        ).order_by('-match_count')[:batch_size]

        for wrestler in wrestlers_no_image:
            try:
                result = client.find_wrestler_image(
                    name=wrestler.name,
                    real_name=wrestler.real_name
                )

                if result and result.get('url'):
                    if cache_service.cache_and_update_entity(wrestler, result, archive_old=False):
                        fetched += 1
                        logger.info(f"Fetched and cached image for wrestler: {wrestler.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {wrestler.name}: {e}")
                continue

        # 2. Refresh old images (older than 30 days) if enabled
        if refresh_old and fetched < batch_size:
            remaining = batch_size - fetched
            cutoff = timezone.now() - timedelta(days=30)

            wrestlers_old_image = Wrestler.objects.filter(
                image_url__isnull=False,
                image_fetched_at__lt=cutoff
            ).annotate(
                match_count=Count('matches')
            ).order_by('image_fetched_at')[:remaining]

            for wrestler in wrestlers_old_image:
                try:
                    result = client.find_wrestler_image(
                        name=wrestler.name,
                        real_name=wrestler.real_name
                    )

                    if result and result.get('url'):
                        new_url = result.get('url') or result.get('thumb_url')
                        # Only update if it's a different image
                        if new_url != wrestler.image_original_url:
                            if cache_service.cache_and_update_entity(wrestler, result, archive_old=True):
                                refreshed += 1
                                logger.info(f"Refreshed image for wrestler: {wrestler.name}")
                        else:
                            # Same image, update timestamp
                            wrestler.image_fetched_at = timezone.now()
                            wrestler.save(update_fields=['image_fetched_at'])

                except Exception as e:
                    logger.warning(f"Failed to refresh image for {wrestler.name}: {e}")
                    continue

        logger.info(f"Wrestler images: fetched {fetched}, refreshed {refreshed}")
        return {"fetched": fetched, "refreshed": refreshed, "attempted": len(wrestlers_no_image)}

    except Exception as e:
        logger.error(f"Wrestler image fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=IMAGE_FETCH_SOFT_LIMIT,
    time_limit=IMAGE_FETCH_HARD_LIMIT,
)
def fetch_promotion_images(self, batch_size: int = 10, refresh_old: bool = True):
    """
    Fetch CC-licensed images/logos for promotions and cache to R2.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Promotion
        from .scrapers import WikimediaCommonsClient
        from .services import get_image_cache_service
        from django.utils import timezone
        from datetime import timedelta

        client = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        fetched = 0
        refreshed = 0

        # Get promotions without images, ordered by event count
        promotions = Promotion.objects.filter(
            image_url__isnull=True
        ).annotate(
            event_count=Count('events')
        ).order_by('-event_count')[:batch_size]

        for promotion in promotions:
            try:
                result = client.find_promotion_image(
                    name=promotion.name,
                    abbreviation=promotion.abbreviation
                )

                if result and result.get('url'):
                    if cache_service.cache_and_update_entity(promotion, result, archive_old=False):
                        fetched += 1
                        logger.info(f"Fetched and cached image for promotion: {promotion.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {promotion.name}: {e}")
                continue

        # Refresh old images
        if refresh_old and fetched < batch_size:
            remaining = batch_size - fetched
            cutoff = timezone.now() - timedelta(days=30)

            old_promotions = Promotion.objects.filter(
                image_url__isnull=False,
                image_fetched_at__lt=cutoff
            ).order_by('image_fetched_at')[:remaining]

            for promotion in old_promotions:
                try:
                    result = client.find_promotion_image(
                        name=promotion.name,
                        abbreviation=promotion.abbreviation
                    )
                    if result and result.get('url'):
                        new_url = result.get('url') or result.get('thumb_url')
                        if new_url != promotion.image_original_url:
                            if cache_service.cache_and_update_entity(promotion, result, archive_old=True):
                                refreshed += 1
                        else:
                            promotion.image_fetched_at = timezone.now()
                            promotion.save(update_fields=['image_fetched_at'])
                except Exception as e:
                    logger.warning(f"Failed to refresh image for {promotion.name}: {e}")

        logger.info(f"Promotion images: fetched {fetched}, refreshed {refreshed}")
        return {"fetched": fetched, "refreshed": refreshed, "attempted": len(promotions)}

    except Exception as e:
        logger.error(f"Promotion image fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=IMAGE_FETCH_SOFT_LIMIT,
    time_limit=IMAGE_FETCH_HARD_LIMIT,
)
def fetch_venue_images(self, batch_size: int = 10, refresh_old: bool = True):
    """
    Fetch CC-licensed images for venues and cache to R2.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Venue
        from .scrapers import WikimediaCommonsClient
        from .services import get_image_cache_service
        from django.utils import timezone
        from datetime import timedelta

        client = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        fetched = 0
        refreshed = 0

        # Get venues without images
        venues = Venue.objects.filter(
            image_url__isnull=True
        ).annotate(
            event_count=Count('events')
        ).order_by('-event_count')[:batch_size]

        for venue in venues:
            try:
                result = client.find_venue_image(
                    name=venue.name,
                    location=venue.location
                )
                if result and result.get('url'):
                    if cache_service.cache_and_update_entity(venue, result, archive_old=False):
                        fetched += 1
                        logger.info(f"Fetched and cached image for venue: {venue.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch image for {venue.name}: {e}")

        # Refresh old images
        if refresh_old and fetched < batch_size:
            remaining = batch_size - fetched
            cutoff = timezone.now() - timedelta(days=30)
            old_venues = Venue.objects.filter(
                image_url__isnull=False,
                image_fetched_at__lt=cutoff
            ).order_by('image_fetched_at')[:remaining]

            for venue in old_venues:
                try:
                    result = client.find_venue_image(name=venue.name, location=venue.location)
                    if result and result.get('url'):
                        new_url = result.get('url') or result.get('thumb_url')
                        if new_url != venue.image_original_url:
                            if cache_service.cache_and_update_entity(venue, result, archive_old=True):
                                refreshed += 1
                        else:
                            venue.image_fetched_at = timezone.now()
                            venue.save(update_fields=['image_fetched_at'])
                except Exception as e:
                    logger.warning(f"Failed to refresh image for {venue.name}: {e}")

        logger.info(f"Venue images: fetched {fetched}, refreshed {refreshed}")
        return {"fetched": fetched, "refreshed": refreshed, "attempted": len(venues)}

    except Exception as e:
        logger.error(f"Venue image fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=IMAGE_FETCH_SOFT_LIMIT,
    time_limit=IMAGE_FETCH_HARD_LIMIT,
)
def fetch_title_images(self, batch_size: int = 10, refresh_old: bool = True):
    """
    Fetch CC-licensed images for championship titles and cache to R2.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Title
        from .scrapers import WikimediaCommonsClient
        from .services import get_image_cache_service
        from django.utils import timezone
        from datetime import timedelta

        client = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        fetched = 0
        refreshed = 0

        # Get titles without images
        titles = Title.objects.filter(
            image_url__isnull=True
        ).annotate(
            match_count=Count('title_matches')
        ).order_by('-match_count')[:batch_size]

        for title in titles:
            try:
                result = client.find_title_image(
                    name=title.name,
                    promotion=title.promotion.abbreviation or title.promotion.name if title.promotion else None
                )
                if result and result.get('url'):
                    if cache_service.cache_and_update_entity(title, result, archive_old=False):
                        fetched += 1
                        logger.info(f"Fetched and cached image for title: {title.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch image for {title.name}: {e}")

        # Refresh old images
        if refresh_old and fetched < batch_size:
            remaining = batch_size - fetched
            cutoff = timezone.now() - timedelta(days=30)
            old_titles = Title.objects.filter(
                image_url__isnull=False,
                image_fetched_at__lt=cutoff
            ).order_by('image_fetched_at')[:remaining]

            for title in old_titles:
                try:
                    result = client.find_title_image(
                        name=title.name,
                        promotion=title.promotion.abbreviation or title.promotion.name if title.promotion else None
                    )
                    if result and result.get('url'):
                        new_url = result.get('url') or result.get('thumb_url')
                        if new_url != title.image_original_url:
                            if cache_service.cache_and_update_entity(title, result, archive_old=True):
                                refreshed += 1
                        else:
                            title.image_fetched_at = timezone.now()
                            title.save(update_fields=['image_fetched_at'])
                except Exception as e:
                    logger.warning(f"Failed to refresh image for {title.name}: {e}")

        logger.info(f"Title images: fetched {fetched}, refreshed {refreshed}")
        return {"fetched": fetched, "refreshed": refreshed, "attempted": len(titles)}

    except Exception as e:
        logger.error(f"Title image fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=IMAGE_FETCH_SOFT_LIMIT,
    time_limit=IMAGE_FETCH_HARD_LIMIT,
)
def fetch_event_images(self, batch_size: int = 15, refresh_old: bool = True):
    """
    Fetch CC-licensed images for events and cache to R2.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Event
        from .scrapers import WikimediaCommonsClient
        from .services import get_image_cache_service
        from django.utils import timezone
        from datetime import timedelta

        client = WikimediaCommonsClient()
        cache_service = get_image_cache_service()

        fetched = 0
        refreshed = 0

        # Get events without images
        events = Event.objects.filter(
            image_url__isnull=True
        ).order_by('-date')[:batch_size]

        for event in events:
            try:
                result = client.find_event_image(
                    name=event.name,
                    promotion=event.promotion.abbreviation or event.promotion.name if event.promotion else None,
                    year=event.date.year if event.date else None
                )
                if result and result.get('url'):
                    if cache_service.cache_and_update_entity(event, result, archive_old=False):
                        fetched += 1
                        logger.info(f"Fetched and cached image for event: {event.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch image for {event.name}: {e}")

        # Refresh old images
        if refresh_old and fetched < batch_size:
            remaining = batch_size - fetched
            cutoff = timezone.now() - timedelta(days=30)
            old_events = Event.objects.filter(
                image_url__isnull=False,
                image_fetched_at__lt=cutoff
            ).order_by('image_fetched_at')[:remaining]

            for event in old_events:
                try:
                    result = client.find_event_image(
                        name=event.name,
                        promotion=event.promotion.abbreviation or event.promotion.name if event.promotion else None,
                        year=event.date.year if event.date else None
                    )
                    if result and result.get('url'):
                        new_url = result.get('url') or result.get('thumb_url')
                        if new_url != event.image_original_url:
                            if cache_service.cache_and_update_entity(event, result, archive_old=True):
                                refreshed += 1
                        else:
                            event.image_fetched_at = timezone.now()
                            event.save(update_fields=['image_fetched_at'])
                except Exception as e:
                    logger.warning(f"Failed to refresh image for {event.name}: {e}")

        logger.info(f"Event images: fetched {fetched}, refreshed {refreshed}")
        return {"fetched": fetched, "refreshed": refreshed, "attempted": len(events)}

    except Exception as e:
        logger.error(f"Event image fetch failed: {e}")
        raise self.retry(exc=e)


@shared_task
def run_all_image_fetches():
    """
    Master task that fetches images for all entity types.

    Runs as a coordinated workflow to avoid overwhelming Wikimedia Commons.
    """
    from celery import chain

    # Run image fetches sequentially to respect rate limits
    workflow = chain(
        fetch_wrestler_images.s(20),
        fetch_promotion_images.s(10),
        fetch_venue_images.s(10),
        fetch_title_images.s(10),
        fetch_event_images.s(15),
    )

    workflow.apply_async()
    logger.info("Started image fetch workflow")
    return {"status": "started"}


# =============================================================================
# Hot 100 Rankings Task
# =============================================================================

@shared_task(
    bind=True,
    soft_time_limit=5 * 60,
    time_limit=7 * 60,
)
def generate_hot100_ranking(self, year: int = None, month: int = None, publish: bool = True):
    """
    Generate monthly Hot 100 wrestler rankings.

    Runs automatically on the 1st of each month via Celery Beat.
    Can also be triggered manually to regenerate rankings.

    Args:
        year: Year to generate ranking for (default: previous month)
        month: Month to generate ranking for (default: previous month)
        publish: Whether to publish the ranking immediately
    """
    from django.utils import timezone
    from datetime import date
    from .models import Hot100Calculator, Hot100Ranking

    try:
        # Default to previous month
        if year is None or month is None:
            today = timezone.now().date()
            if today.month == 1:
                year = today.year - 1
                month = 12
            else:
                year = today.year
                month = today.month - 1

        logger.info(f"Generating Hot 100 ranking for {month}/{year}")

        calculator = Hot100Calculator(year, month)
        ranking = calculator.generate_ranking(publish=publish)

        entry_count = ranking.entries.count()
        logger.info(f"Hot 100 generated: {entry_count} entries for {ranking}")

        return {
            "status": "success",
            "year": year,
            "month": month,
            "entries": entry_count,
            "published": publish,
        }

    except Exception as e:
        logger.error(f"Failed to generate Hot 100 ranking: {e}", exc_info=True)
        raise self.retry(exc=e, max_retries=2)


# =============================================================================
# WrestleBot 2.0 Tasks - Autonomous Data Enhancement
# =============================================================================

WRESTLEBOT_SOFT_LIMIT = 10 * 60  # 10 minutes
WRESTLEBOT_HARD_LIMIT = 12 * 60  # 12 minutes


@shared_task(
    bind=True,
    soft_time_limit=WRESTLEBOT_SOFT_LIMIT,
    time_limit=WRESTLEBOT_HARD_LIMIT,
)
def wrestlebot_master(self):
    """
    Master orchestrator task - analyzes what work needs to be done.

    This is a lightweight task that runs every 30 minutes to check
    database state and log what the bot is planning to do.
    """
    lock_key = "wrestlebot_master_lock"
    lock_timeout = WRESTLEBOT_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("WrestleBot master skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot import WrestleBot
        bot = WrestleBot()
        result = bot.run_master_cycle()
        logger.info(f"WrestleBot master cycle: {result}")
        return result

    except Exception as e:
        logger.error(f"WrestleBot master failed: {e}")
        return {"status": "error", "error": str(e)}

    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    soft_time_limit=WRESTLEBOT_SOFT_LIMIT,
    time_limit=WRESTLEBOT_HARD_LIMIT,
)
def wrestlebot_discovery_cycle(self, batch_size: int = 5):
    """
    Run a discovery cycle - find and add new entries.

    Runs every 2 hours via Celery Beat.
    Discovers new wrestlers, events, promotions from various sources.
    """
    lock_key = "wrestlebot_discovery_lock"
    lock_timeout = WRESTLEBOT_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("WrestleBot discovery skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot import WrestleBot
        bot = WrestleBot()

        if not bot.is_enabled():
            return {"status": "disabled"}

        result = bot.run_discovery_cycle(batch_size=batch_size)
        logger.info(f"WrestleBot discovery cycle: {result}")
        return result

    except Exception as e:
        logger.error(f"WrestleBot discovery failed: {e}")
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    soft_time_limit=WRESTLEBOT_SOFT_LIMIT,
    time_limit=WRESTLEBOT_HARD_LIMIT,
)
def wrestlebot_enrichment_cycle(self, batch_size: int = 10):
    """
    Run an enrichment cycle - improve existing entries.

    Runs every hour via Celery Beat.
    Adds missing data (bios, dates, etc.) to incomplete entries.
    """
    lock_key = "wrestlebot_enrichment_lock"
    lock_timeout = WRESTLEBOT_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("WrestleBot enrichment skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot import WrestleBot
        bot = WrestleBot()

        if not bot.is_enabled():
            return {"status": "disabled"}

        result = bot.run_enrichment_cycle(batch_size=batch_size)
        logger.info(f"WrestleBot enrichment cycle: {result}")
        return result

    except Exception as e:
        logger.error(f"WrestleBot enrichment failed: {e}")
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=600,
    soft_time_limit=WRESTLEBOT_SOFT_LIMIT,
    time_limit=WRESTLEBOT_HARD_LIMIT,
)
def wrestlebot_image_cycle(self, batch_size: int = 10):
    """
    Run an image fetching cycle - add CC-licensed images.

    Runs every 4 hours via Celery Beat.
    Fetches images from Wikimedia Commons for entities without images.
    """
    lock_key = "wrestlebot_image_lock"
    lock_timeout = WRESTLEBOT_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("WrestleBot image cycle skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot import WrestleBot
        bot = WrestleBot()

        if not bot.is_enabled():
            return {"status": "disabled"}

        result = bot.run_image_cycle(batch_size=batch_size)
        logger.info(f"WrestleBot image cycle: {result}")
        return result

    except Exception as e:
        logger.error(f"WrestleBot image cycle failed: {e}")
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


@shared_task
def wrestlebot_get_status():
    """
    Get current WrestleBot status and statistics.

    Can be called manually to check bot status.
    """
    try:
        from .wrestlebot import WrestleBot
        bot = WrestleBot()
        status = bot.get_status()
        cache.set("wrestlebot_status", status, timeout=300)
        return status

    except Exception as e:
        logger.error(f"Failed to get WrestleBot status: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=15 * 60,  # 15 minutes
    time_limit=20 * 60,
)
def wrestlebot_match_cleanup(self, dry_run: bool = False, limit: int = 5000):
    """
    Clean up synthetic/invalid match data.

    Removes:
    - Matches with deceased wrestlers appearing after death
    - Matches with retired wrestlers appearing after retirement
    - Matches with impossible era combinations

    Fixes:
    - Tag teams stored as single wrestlers (replaces with individual members)

    Args:
        dry_run: If True, don't actually make changes (just report)
        limit: Maximum matches to check

    Runs every 6 hours via Celery Beat.
    """
    lock_key = "wrestlebot_match_cleanup_lock"
    lock_timeout = 25 * 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Match cleanup skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot.quality import DataCleaner

        cleaner = DataCleaner()
        results = cleaner.find_and_fix_match_issues(dry_run=dry_run, limit=limit)

        logger.info(f"Match cleanup complete: {results}")
        return results

    except Exception as e:
        logger.error(f"Match cleanup failed: {e}")
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=10 * 60,
    time_limit=15 * 60,
)
def wrestlebot_synthetic_cleanup(self, dry_run: bool = False):
    """
    Find and delete synthetic/fabricated events.

    Identifies:
    - Future events with deceased wrestlers
    - Far-future events with suspicious name patterns

    Args:
        dry_run: If True, don't actually delete (just report)

    Runs daily via Celery Beat.
    """
    lock_key = "wrestlebot_synthetic_cleanup_lock"
    lock_timeout = 20 * 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Synthetic cleanup skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .wrestlebot.quality import DataCleaner

        cleaner = DataCleaner()

        # Clean up events with deceased wrestlers
        deceased_results = cleaner.find_and_delete_synthetic_events(dry_run=dry_run)

        # Clean up far-future events with suspicious names
        pattern_results = cleaner.detect_synthetic_by_name_pattern(dry_run=dry_run)

        results = {
            'dry_run': dry_run,
            'deceased_cleanup': deceased_results,
            'pattern_cleanup': pattern_results,
            'total_events_deleted': (
                deceased_results.get('events_deleted', 0) +
                pattern_results.get('events_deleted', 0)
            ),
        }

        logger.info(f"Synthetic cleanup complete: {results}")
        return results

    except Exception as e:
        logger.error(f"Synthetic cleanup failed: {e}")
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


# =============================================================================
# TV Episode Tracking Tasks
# =============================================================================

TV_EPISODE_SOFT_LIMIT = 8 * 60   # 8 minutes
TV_EPISODE_HARD_LIMIT = 10 * 60  # 10 minutes


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    soft_time_limit=TV_EPISODE_SOFT_LIMIT,
    time_limit=TV_EPISODE_HARD_LIMIT,
)
def poll_tv_episodes(self):
    """
    Poll for new TV episodes every 15 minutes.

    Quick check - only hits TMDB, not Cagematch.
    Creates new episode Events for recently aired shows.

    This task runs frequently to ensure new episodes are captured
    shortly after they air (Raw, SmackDown, Dynamite, etc.)
    """
    from celery.exceptions import SoftTimeLimitExceeded

    lock_key = "poll_tv_episodes_lock"
    lock_timeout = TV_EPISODE_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("TV episode poll skipped: previous run still active")
        return {"status": "skipped_lock"}

    try:
        from .scrapers.tv_episodes import TVEpisodeScraper

        scraper = TVEpisodeScraper()
        results = scraper.poll_for_new_episodes()

        logger.info(
            "TV episode poll: checked %d shows, found %d new episodes",
            results['shows_checked'], results['new_episodes']
        )

        return results

    except SoftTimeLimitExceeded:
        logger.warning("TV episode poll exceeded time limit")
        return {"status": "timeout"}

    except Exception as e:
        logger.error("TV episode poll failed: %s", e)
        raise self.retry(exc=e)

    finally:
        cache.delete(lock_key)


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=30 * 60,  # 30 minutes
    time_limit=35 * 60,
)
def backfill_show_episodes(self, show_id: int, year: int = None):
    """
    Backfill historical episodes for a specific show.

    Run manually or scheduled for off-peak hours.

    Args:
        show_id: ID of the TVShow to backfill
        year: Optional specific year to backfill (all years if None)
    """
    from datetime import date

    from .models import TVShow
    from .scrapers.tv_episodes import TVEpisodeScraper

    try:
        show = TVShow.objects.get(id=show_id)
    except TVShow.DoesNotExist:
        logger.error("Show %d not found for backfill", show_id)
        return {"error": f"Show {show_id} not found"}

    scraper = TVEpisodeScraper()

    if year:
        results = scraper.backfill_show_by_year(show, year)
        logger.info("Backfilled %s for %d: %s", show.name, year, results)
    else:
        results = scraper.backfill_all_episodes(show)
        logger.info("Backfilled all episodes for %s: %s", show.name, results)

    return results


@shared_task(
    bind=True,
    max_retries=2,
    soft_time_limit=60 * 60,  # 60 minutes for full backfill
    time_limit=65 * 60,
)
def backfill_all_tv_shows(self, year: int = None):
    """
    Backfill episodes for all TV shows with TMDB IDs.

    WARNING: This is a long-running task. Use for initial setup only.

    Args:
        year: Optional specific year to backfill (all years if None)
    """
    from .models import TVShow
    from .scrapers.tv_episodes import TVEpisodeScraper

    shows = TVShow.objects.filter(tmdb_id__isnull=False)
    scraper = TVEpisodeScraper()

    total_results = {
        'shows_processed': 0,
        'total_created': 0,
        'total_updated': 0,
        'total_errors': 0,
    }

    for show in shows:
        try:
            if year:
                results = scraper.backfill_show_by_year(show, year)
            else:
                results = scraper.backfill_all_episodes(show)

            total_results['shows_processed'] += 1
            total_results['total_created'] += results.get('created', 0)
            total_results['total_updated'] += results.get('updated', 0)
            total_results['total_errors'] += results.get('errors', 0)

            logger.info("Backfilled %s: %s", show.name, results)

        except Exception as e:
            logger.error("Error backfilling %s: %s", show.name, e)
            total_results['total_errors'] += 1

    logger.info("TV show backfill complete: %s", total_results)
    return total_results


@shared_task(bind=True)
def verify_tv_show_completeness(self, show_id: int):
    """
    Verify that a TV show has all episodes from TMDB.

    Compares our episode count against TMDB's episode count.

    Args:
        show_id: ID of the TVShow to verify
    """
    from .models import TVShow
    from .scrapers.tv_episodes import TVEpisodeScraper

    try:
        show = TVShow.objects.get(id=show_id)
    except TVShow.DoesNotExist:
        return {"error": f"Show {show_id} not found"}

    scraper = TVEpisodeScraper()
    results = scraper.verify_episode_count(show)

    if not results.get('complete', True):
        logger.warning(
            "Show %s is missing %d episodes (TMDB: %d, DB: %d)",
            show.name,
            results['difference'],
            results['tmdb_count'],
            results['db_count']
        )
    else:
        logger.info("Show %s episode count verified: %d episodes", show.name, results['db_count'])

    return results


@shared_task(bind=True)
def verify_all_tv_shows(self):
    """
    Verify episode completeness for all TV shows.

    Returns summary of shows that are missing episodes.
    """
    from .models import TVShow
    from .scrapers.tv_episodes import TVEpisodeScraper

    shows = TVShow.objects.filter(tmdb_id__isnull=False)
    scraper = TVEpisodeScraper()

    results = {
        'shows_checked': 0,
        'shows_complete': 0,
        'shows_incomplete': [],
    }

    for show in shows:
        try:
            verification = scraper.verify_episode_count(show)
            results['shows_checked'] += 1

            if verification.get('complete', True):
                results['shows_complete'] += 1
            else:
                results['shows_incomplete'].append({
                    'show': show.name,
                    'show_id': show.id,
                    'tmdb_count': verification['tmdb_count'],
                    'db_count': verification['db_count'],
                    'missing': verification['difference'],
                })

        except Exception as e:
            logger.error("Error verifying %s: %s", show.name, e)

    logger.info(
        "TV show verification: %d checked, %d complete, %d incomplete",
        results['shows_checked'],
        results['shows_complete'],
        len(results['shows_incomplete'])
    )

    return results