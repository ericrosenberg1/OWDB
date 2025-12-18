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

WRESTLEBOT_SOFT_LIMIT = 8 * 60  # 8 minutes for WrestleBot cycles
WRESTLEBOT_HARD_LIMIT = 10 * 60  # 10 minutes hard kill

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
def scrape_wikipedia_wrestlers(self, limit: int = 50):
    """
    Scrape wrestler data from Wikipedia.
    Runs periodically to discover new wrestlers and update existing ones.
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

        wrestlers = scraper.scrape_wrestlers(limit=limit)
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
def scrape_wikipedia_promotions(self, limit: int = 25):
    """Scrape promotion data from Wikipedia."""
    lock_key = "scrape_wikipedia_promotions_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Wikipedia promotion scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import WikipediaScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = WikipediaScraper()
        coordinator = ScraperCoordinator()

        promotions = scraper.scrape_promotions(limit=limit)
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
def scrape_wikipedia_events(self, limit: int = 50):
    """Scrape event data from Wikipedia."""
    lock_key = "scrape_wikipedia_events_lock"
    lock_timeout = SCRAPER_HARD_LIMIT + 60

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("Wikipedia event scrape skipped: previous run still active")
        return {"scraped": 0, "imported": 0, "status": "skipped_lock"}

    try:
        from .scrapers import WikipediaScraper, ScraperCoordinator, ScraperUnavailableError

        scraper = WikipediaScraper()
        coordinator = ScraperCoordinator()

        events = scraper.scrape_events(limit=limit)
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
# WrestleBot AI Tasks
# =============================================================================

@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=120,  # Retry after 2 minutes (was 10)
    soft_time_limit=WRESTLEBOT_SOFT_LIMIT,
    time_limit=WRESTLEBOT_HARD_LIMIT,
    autoretry_for=(Exception,),
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minute delay
    retry_jitter=True,  # Add randomness to prevent thundering herd
)
def wrestlebot_discovery_cycle(self, max_items: int = 10):
    """
    Run a WrestleBot discovery cycle.

    This task discovers new wrestling entities from Wikipedia,
    verifies them with AI, and imports them to the database.

    Runs every minute via Celery Beat.

    Features:
    - Soft time limit of 8 minutes (graceful shutdown)
    - Hard time limit of 10 minutes (forced kill)
    - Auto-retry with exponential backoff on failure
    - Circuit breaker on AI service to prevent freezing
    """
    from django.utils import timezone

    # Prevent overlapping runs which can cause thrashing/timeouts
    lock_key = "wrestlebot_cycle_lock"
    lock_time_key = f"{lock_key}_time"
    # Slightly longer than hard limit to give the previous run time to finish
    lock_timeout = WRESTLEBOT_HARD_LIMIT + 120

    if not cache.add(lock_key, True, timeout=lock_timeout):
        logger.info("WrestleBot cycle skipped: another cycle already running")
        return {"status": "skipped", "reason": "already_running"}

    cache.set(lock_time_key, timezone.now(), timeout=lock_timeout)

    try:
        from .wrestlebot import WrestleBot

        bot = WrestleBot()

        if not bot.can_run():
            logger.info("WrestleBot skipped: disabled")
            return {"status": "skipped", "reason": "disabled"}

        results = bot.run_discovery_cycle(max_items=max_items)
        logger.info(f"WrestleBot cycle complete: {results}")
        return results

    except SoftTimeLimitExceeded:
        logger.warning("WrestleBot cycle exceeded soft time limit - graceful shutdown")
        return {
            "status": "timeout",
            "reason": "Exceeded soft time limit",
            "will_retry": self.request.retries < self.max_retries
        }

    except Exception as e:
        logger.error(f"WrestleBot discovery cycle failed: {e}")
        # autoretry_for handles the retry automatically
        raise

    finally:
        cache.delete(lock_key)
        cache.delete(lock_time_key)

@shared_task
def wrestlebot_cleanup_old_logs():
    """
    Clean up old WrestleBot logs. Keep last 30 days.

    Runs weekly via Celery Beat.
    """
    from .models import WrestleBotLog
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=30)
    deleted, _ = WrestleBotLog.objects.filter(created_at__lt=cutoff).delete()

    logger.info(f"Cleaned up {deleted} old WrestleBot logs")
    return deleted


@shared_task
def wrestlebot_reset_daily_limits():
    """
    Reset WrestleBot daily limits.

    Runs daily via Celery Beat.
    """
    from .models import WrestleBotConfig

    try:
        config = WrestleBotConfig.get_config()
        config.reset_daily_count()
        logger.info("Reset WrestleBot daily limits")
        return {"status": "reset"}
    except Exception as e:
        logger.error(f"Failed to reset WrestleBot limits: {e}")
        return {"status": "error", "error": str(e)}


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
def fetch_wrestler_images(self, batch_size: int = 20):
    """
    Fetch CC-licensed images for wrestlers without images.

    Prioritizes wrestlers by match count (most active first).
    Only uses images with permissive CC licenses.

    Runs every 6 hours via Celery Beat.
    """
    try:
        from .models import Wrestler
        from .scrapers import WikimediaCommonsClient
        from django.utils import timezone

        client = WikimediaCommonsClient()

        # Get wrestlers without images, ordered by match count
        wrestlers = Wrestler.objects.filter(
            image_url__isnull=True
        ).annotate(
            match_count=Count('matches')
        ).order_by('-match_count')[:batch_size]

        fetched = 0
        for wrestler in wrestlers:
            try:
                result = client.find_wrestler_image(
                    name=wrestler.name,
                    real_name=wrestler.real_name
                )

                if result and result.get('url'):
                    wrestler.image_url = result.get('thumb_url') or result.get('url')
                    wrestler.image_source_url = result.get('description_url')
                    wrestler.image_license = result.get('license', '')
                    wrestler.image_credit = result.get('artist', '')
                    wrestler.image_fetched_at = timezone.now()
                    wrestler.save(update_fields=[
                        'image_url', 'image_source_url', 'image_license',
                        'image_credit', 'image_fetched_at'
                    ])
                    fetched += 1
                    logger.info(f"Fetched image for wrestler: {wrestler.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {wrestler.name}: {e}")
                continue

        logger.info(f"Wrestler images: fetched {fetched}/{len(wrestlers)}")
        return {"fetched": fetched, "attempted": len(wrestlers)}

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
def fetch_promotion_images(self, batch_size: int = 10):
    """
    Fetch CC-licensed images/logos for promotions without images.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Promotion
        from .scrapers import WikimediaCommonsClient
        from django.utils import timezone

        client = WikimediaCommonsClient()

        # Get promotions without images, ordered by event count
        promotions = Promotion.objects.filter(
            image_url__isnull=True
        ).annotate(
            event_count=Count('events')
        ).order_by('-event_count')[:batch_size]

        fetched = 0
        for promotion in promotions:
            try:
                result = client.find_promotion_image(
                    name=promotion.name,
                    abbreviation=promotion.abbreviation
                )

                if result and result.get('url'):
                    promotion.image_url = result.get('thumb_url') or result.get('url')
                    promotion.image_source_url = result.get('description_url')
                    promotion.image_license = result.get('license', '')
                    promotion.image_credit = result.get('artist', '')
                    promotion.image_fetched_at = timezone.now()
                    promotion.save(update_fields=[
                        'image_url', 'image_source_url', 'image_license',
                        'image_credit', 'image_fetched_at'
                    ])
                    fetched += 1
                    logger.info(f"Fetched image for promotion: {promotion.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {promotion.name}: {e}")
                continue

        logger.info(f"Promotion images: fetched {fetched}/{len(promotions)}")
        return {"fetched": fetched, "attempted": len(promotions)}

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
def fetch_venue_images(self, batch_size: int = 10):
    """
    Fetch CC-licensed images for venues without images.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Venue
        from .scrapers import WikimediaCommonsClient
        from django.utils import timezone

        client = WikimediaCommonsClient()

        # Get venues without images, ordered by event count
        venues = Venue.objects.filter(
            image_url__isnull=True
        ).annotate(
            event_count=Count('events')
        ).order_by('-event_count')[:batch_size]

        fetched = 0
        for venue in venues:
            try:
                result = client.find_venue_image(
                    name=venue.name,
                    location=venue.location
                )

                if result and result.get('url'):
                    venue.image_url = result.get('thumb_url') or result.get('url')
                    venue.image_source_url = result.get('description_url')
                    venue.image_license = result.get('license', '')
                    venue.image_credit = result.get('artist', '')
                    venue.image_fetched_at = timezone.now()
                    venue.save(update_fields=[
                        'image_url', 'image_source_url', 'image_license',
                        'image_credit', 'image_fetched_at'
                    ])
                    fetched += 1
                    logger.info(f"Fetched image for venue: {venue.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {venue.name}: {e}")
                continue

        logger.info(f"Venue images: fetched {fetched}/{len(venues)}")
        return {"fetched": fetched, "attempted": len(venues)}

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
def fetch_title_images(self, batch_size: int = 10):
    """
    Fetch CC-licensed images for championship titles without images.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Title
        from .scrapers import WikimediaCommonsClient
        from django.utils import timezone

        client = WikimediaCommonsClient()

        # Get titles without images, ordered by title match count
        titles = Title.objects.filter(
            image_url__isnull=True
        ).annotate(
            match_count=Count('title_matches')
        ).order_by('-match_count')[:batch_size]

        fetched = 0
        for title in titles:
            try:
                result = client.find_title_image(
                    name=title.name,
                    promotion=title.promotion.abbreviation or title.promotion.name
                )

                if result and result.get('url'):
                    title.image_url = result.get('thumb_url') or result.get('url')
                    title.image_source_url = result.get('description_url')
                    title.image_license = result.get('license', '')
                    title.image_credit = result.get('artist', '')
                    title.image_fetched_at = timezone.now()
                    title.save(update_fields=[
                        'image_url', 'image_source_url', 'image_license',
                        'image_credit', 'image_fetched_at'
                    ])
                    fetched += 1
                    logger.info(f"Fetched image for title: {title.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {title.name}: {e}")
                continue

        logger.info(f"Title images: fetched {fetched}/{len(titles)}")
        return {"fetched": fetched, "attempted": len(titles)}

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
def fetch_event_images(self, batch_size: int = 15):
    """
    Fetch CC-licensed images for events without images.

    Runs every 12 hours via Celery Beat.
    """
    try:
        from .models import Event
        from .scrapers import WikimediaCommonsClient
        from django.utils import timezone

        client = WikimediaCommonsClient()

        # Get events without images, ordered by most recent
        events = Event.objects.filter(
            image_url__isnull=True
        ).order_by('-date')[:batch_size]

        fetched = 0
        for event in events:
            try:
                result = client.find_event_image(
                    name=event.name,
                    promotion=event.promotion.abbreviation or event.promotion.name,
                    year=event.date.year if event.date else None
                )

                if result and result.get('url'):
                    event.image_url = result.get('thumb_url') or result.get('url')
                    event.image_source_url = result.get('description_url')
                    event.image_license = result.get('license', '')
                    event.image_credit = result.get('artist', '')
                    event.image_fetched_at = timezone.now()
                    event.save(update_fields=[
                        'image_url', 'image_source_url', 'image_license',
                        'image_credit', 'image_fetched_at'
                    ])
                    fetched += 1
                    logger.info(f"Fetched image for event: {event.name}")

            except Exception as e:
                logger.warning(f"Failed to fetch image for {event.name}: {e}")
                continue

        logger.info(f"Event images: fetched {fetched}/{len(events)}")
        return {"fetched": fetched, "attempted": len(events)}

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


@shared_task(soft_time_limit=60, time_limit=90)
def wrestlebot_get_stats():
    """
    Get and cache WrestleBot statistics.

    Runs every 10 minutes via Celery Beat.
    """
    try:
        from .wrestlebot import WrestleBot

        bot = WrestleBot()
        stats = bot.get_statistics()

        # Cache the stats
        cache.set("wrestlebot_stats", stats, timeout=3600)

        logger.info(f"WrestleBot stats: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to get WrestleBot stats: {e}")
        return {"status": "error", "error": str(e)}


@shared_task(soft_time_limit=30, time_limit=60)
def wrestlebot_health_check():
    """
    Health check and self-healing for WrestleBot components.

    Checks:
    1. Ollama AI service availability
    2. Recent task success rate
    3. Celery worker responsiveness
    4. Database connectivity

    If issues detected, takes corrective action:
    - Resets circuit breaker if Ollama is back online
    - Clears stale cache entries
    - Logs warnings for monitoring

    Runs every 2 minutes via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta

    health_status = {
        "timestamp": timezone.now().isoformat(),
        "ai_available": False,
        "db_healthy": False,
        "recent_errors": 0,
        "actions_taken": [],
    }

    try:
        # Check AI availability
        from .wrestlebot.ai_processor import OllamaProcessor, _circuit_breaker

        ai = OllamaProcessor()
        health_status["ai_available"] = ai.is_available(force_check=True)

        # Reset circuit breaker if AI is back online
        if health_status["ai_available"] and _circuit_breaker['open_until'] > 0:
            _circuit_breaker['failures'] = 0
            _circuit_breaker['open_until'] = 0
            health_status["actions_taken"].append("Reset AI circuit breaker")
            logger.info("WrestleBot health check: AI back online, reset circuit breaker")

        # Check recent error rate
        from .models import WrestleBotLog
        recent_cutoff = timezone.now() - timedelta(hours=1)
        recent_logs = WrestleBotLog.objects.filter(created_at__gte=recent_cutoff)
        total_recent = recent_logs.count()
        error_count = recent_logs.filter(success=False).count()
        health_status["recent_errors"] = error_count

        if total_recent > 0:
            error_rate = error_count / total_recent
            if error_rate > 0.5:
                logger.warning(
                    f"WrestleBot health check: High error rate ({error_rate:.1%}) "
                    f"in last hour ({error_count}/{total_recent})"
                )

        # Database health check
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["db_healthy"] = True

        # Cache the health status
        cache.set("wrestlebot_health", health_status, timeout=600)

        return health_status

    except Exception as e:
        logger.error(f"WrestleBot health check failed: {e}")
        health_status["error"] = str(e)
        return health_status


@shared_task(soft_time_limit=60, time_limit=90)
def restart_stale_bot_tasks():
    """
    Check for and restart stale/frozen WrestleBot tasks.

    This task monitors for tasks that may have frozen and
    ensures the discovery cycle keeps running.

    Runs every 5 minutes via Celery Beat.
    """
    from django.utils import timezone
    from datetime import timedelta
    try:
        from django_celery_results.models import TaskResult
    except ImportError:
        TaskResult = None

    actions = []

    try:
        # Check when the last successful discovery cycle ran
        last_success = cache.get("wrestlebot_last_success")
        now = timezone.now()

        # If no success in 10 minutes and bot is enabled, something may be wrong
        if last_success:
            time_since_success = (now - last_success).total_seconds()
            if time_since_success > 600:  # 10 minutes
                logger.warning(
                    f"WrestleBot: No successful cycle in {time_since_success/60:.1f} minutes"
                )
                actions.append(f"Warning: No success in {time_since_success/60:.1f} min")

        # Check for stuck tasks (STARTED but not finished)
        if TaskResult:
            stuck_cutoff = now - timedelta(minutes=10)
            stuck_tasks = TaskResult.objects.filter(
                task_name__contains='wrestlebot',
                status='STARTED',
                date_created__lt=stuck_cutoff
            )

            if stuck_tasks.exists():
                stuck_count = stuck_tasks.count()
                logger.warning(f"Found {stuck_count} potentially stuck WrestleBot tasks")
                actions.append(f"Found {stuck_count} stuck tasks")

                # Mark them as failed so they don't block new runs
                stuck_tasks.update(status='FAILURE')
                actions.append(f"Marked {stuck_count} stuck tasks as failed")
        else:
            actions.append("Task result backend not installed; skipped stuck task scan")

        # Clear stale locks if any
        lock_key = "wrestlebot_cycle_lock"
        if cache.get(lock_key):
            # Check if lock is stale (older than 10 minutes)
            lock_time = cache.get(f"{lock_key}_time")
            if lock_time and (now - lock_time).total_seconds() > 600:
                cache.delete(lock_key)
                cache.delete(f"{lock_key}_time")
                actions.append("Cleared stale bot lock")
                logger.info("Cleared stale WrestleBot cycle lock")

        return {
            "status": "checked",
            "actions": actions,
            "timestamp": now.isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to check stale tasks: {e}")
        return {"status": "error", "error": str(e)}
