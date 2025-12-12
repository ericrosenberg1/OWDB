from celery import shared_task
from django.core.cache import cache
from django.db.models import Count

import logging
import random

logger = logging.getLogger(__name__)


# =============================================================================
# Scraping Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_wikipedia_wrestlers(self, limit: int = 50):
    """
    Scrape wrestler data from Wikipedia.
    Runs periodically to discover new wrestlers and update existing ones.
    """
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

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia wrestler scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_wikipedia_promotions(self, limit: int = 25):
    """Scrape promotion data from Wikipedia."""
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

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia promotion scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def scrape_wikipedia_events(self, limit: int = 50):
    """Scrape event data from Wikipedia."""
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

    except ScraperUnavailableError as e:
        logger.error(f"Wikipedia unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Wikipedia event scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def scrape_cagematch_wrestlers(self, limit: int = 25):
    """
    Scrape wrestler data from Cagematch.
    Lower limits due to more restrictive rate limiting.
    """
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

    except ScraperUnavailableError as e:
        logger.error(f"Cagematch unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Cagematch wrestler scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def scrape_cagematch_events(self, limit: int = 25):
    """Scrape recent events from Cagematch."""
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

    except ScraperUnavailableError as e:
        logger.error(f"Cagematch unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"Cagematch event scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def scrape_profightdb_wrestlers(self, limit: int = 25):
    """Scrape wrestler data from ProFightDB."""
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

    except ScraperUnavailableError as e:
        # Don't retry if the source is completely unavailable (SSL errors, etc.)
        logger.error(f"ProFightDB unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"ProFightDB wrestler scrape failed: {e}")
        raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=600)
def scrape_profightdb_events(self, limit: int = 25):
    """Scrape events from ProFightDB."""
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

    except ScraperUnavailableError as e:
        # Don't retry if the source is completely unavailable (SSL errors, etc.)
        logger.error(f"ProFightDB unavailable, skipping: {e}")
        return {"scraped": 0, "imported": 0, "error": str(e), "status": "source_unavailable"}

    except Exception as e:
        logger.error(f"ProFightDB event scrape failed: {e}")
        raise self.retry(exc=e)


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
    Runs with staggered delays to avoid overwhelming any single source.
    """
    from celery import chain, group

    # Web scrapers run sequentially to respect rate limits
    wikipedia_tasks = group(
        scrape_wikipedia_wrestlers.s(50),
        scrape_wikipedia_promotions.s(25),
        scrape_wikipedia_events.s(50),
    )

    cagematch_tasks = group(
        scrape_cagematch_wrestlers.s(25),
        scrape_cagematch_events.s(25),
    )

    profightdb_tasks = group(
        scrape_profightdb_wrestlers.s(25),
        scrape_profightdb_events.s(25),
    )

    workflow = chain(
        wikipedia_tasks,
        cagematch_tasks,
        profightdb_tasks,
    )

    workflow.apply_async()
    logger.info("Started web scrapers workflow")
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
    """Pre-compute and cache database statistics. Run hourly."""
    from .models import Wrestler, Promotion, Event, Match, Title

    stats = {
        'wrestlers': Wrestler.objects.count(),
        'promotions': Promotion.objects.count(),
        'events': Event.objects.count(),
        'matches': Match.objects.count(),
        'titles': Title.objects.count(),
    }

    cache.set('homepage_stats', stats, timeout=3600)  # 1 hour
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

@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def wrestlebot_discovery_cycle(self, max_items: int = 10):
    """
    Run a WrestleBot discovery cycle.

    This task discovers new wrestling entities from Wikipedia,
    verifies them with AI, and imports them to the database.

    Runs every 30 minutes via Celery Beat.
    """
    try:
        from .wrestlebot import WrestleBot

        bot = WrestleBot()

        if not bot.can_run():
            logger.info("WrestleBot skipped: disabled or rate limited")
            return {"status": "skipped", "reason": "disabled or rate limited"}

        results = bot.run_discovery_cycle(max_items=max_items)
        logger.info(f"WrestleBot cycle complete: {results}")
        return results

    except Exception as e:
        logger.error(f"WrestleBot discovery cycle failed: {e}")
        raise self.retry(exc=e)


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


@shared_task
def wrestlebot_get_stats():
    """
    Get and cache WrestleBot statistics.

    Runs hourly via Celery Beat.
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
