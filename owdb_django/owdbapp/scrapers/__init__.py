# OWDB Scrapers & APIs - Automated data collection for the wrestling database
#
# LEGAL NOTICE:
# This module only collects publicly available, factual information that is
# not protected by copyright. We respect robots.txt, API terms, and rate limits.
#
# WEB SCRAPERS:
# - Wikipedia: Factual data under CC BY-SA license
# - Cagematch.net: Public wrestling database
# - ProFightDB: Historical wrestling data
#
# FREE APIs:
# - TMDB: Movies and TV shows (free API key required)
# - RAWG: Video games database (free API key required)
# - IGDB: Video games via Twitch (free, OAuth required)
# - Open Library: Books (no auth required - completely free!)
# - Google Books: Books (works without key, limited)
# - iTunes Search: Podcasts (no auth required - completely free!)
# - Podcast Index: Podcasts (free API key required)
#
# We do NOT collect:
# - Copyrighted content (descriptions, reviews, commentary)
# - Trademarked logos or images
# - Content behind paywalls
# - Private/non-public information

# Base classes
from .api_client import APIClient, RateLimiter, ErrorReporter, CircuitBreaker

# Web scrapers
from .base import BaseScraper, ScraperUnavailableError
from .wikipedia import WikipediaScraper
from .cagematch import CagematchScraper
from .profightdb import ProFightDBScraper

# API clients
from .tmdb import TMDBClient
from .rawg import RAWGClient, IGDBClient
from .openlibrary import OpenLibraryClient, GoogleBooksClient
from .podcasts import PodcastIndexClient, ITunesPodcastClient, ListenNotesClient

# Coordinator
from .coordinator import ScraperCoordinator, DataValidator, DataDeduplicator

__all__ = [
    # Base
    'APIClient',
    'RateLimiter',
    'ErrorReporter',
    'CircuitBreaker',
    'BaseScraper',
    'ScraperUnavailableError',
    # Web scrapers
    'WikipediaScraper',
    'CagematchScraper',
    'ProFightDBScraper',
    # API clients
    'TMDBClient',
    'RAWGClient',
    'IGDBClient',
    'OpenLibraryClient',
    'GoogleBooksClient',
    'PodcastIndexClient',
    'ITunesPodcastClient',
    'ListenNotesClient',
    # Coordinator
    'ScraperCoordinator',
    'DataValidator',
    'DataDeduplicator',
]
