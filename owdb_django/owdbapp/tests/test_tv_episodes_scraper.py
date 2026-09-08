"""
Tests for owdb_django/owdbapp/scrapers/tv_episodes.py.

Near-0% coverage before this file existed. Read for real bugs per the
owdbapp bug-fix sweep's "beyond the above" scope, not just to raise a
coverage number. Found two:

1. _create_or_update_episode built the episode name from TMDB data with a
   branch that claimed to "include title if it's meaningful" but actually
   rebuilt the exact same "{show.name} #{ep_num}" string either way, so a
   real TMDB episode title was silently dropped every time.

2. enrich_episode_with_matches assigned episode.cagematch_event_id in memory
   but only called episode.save() when at least one match was successfully
   created. A Cagematch page whose matches all lacked a parseable
   `match_text` (matches_added stays 0) would silently discard the
   cagematch_event_id it had just found.
"""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from ..models import Event, Promotion, TVShow
from ..scrapers.tv_episodes import TVEpisodeScraper


class CreateOrUpdateEpisodeNamingTest(TestCase):
    """Regression for bug 1: a meaningful TMDB title must end up in the name."""

    def setUp(self):
        self.promotion = Promotion.objects.create(name="WWE", abbreviation="WWE")
        self.show = TVShow.objects.create(name="Raw", promotion=self.promotion)
        self.scraper = TVEpisodeScraper()

    def test_meaningful_title_is_included_in_the_episode_name(self):
        event, created = self.scraper._create_or_update_episode(
            self.show,
            {
                "air_date": "2024-01-15",
                "episode_number": 1665,
                "season_number": 32,
                "name": "Reunion Show",
                "id": 999,
                "overview": "A special reunion episode.",
            },
        )
        self.assertTrue(created)
        self.assertEqual(event.name, "Raw #1665: Reunion Show")

    def test_generic_tmdb_placeholder_title_is_not_included(self):
        """TMDB's generic "Episode N" placeholder isn't a real title."""
        event, created = self.scraper._create_or_update_episode(
            self.show,
            {
                "air_date": "2024-01-15",
                "episode_number": 1665,
                "season_number": 32,
                "name": "Episode 1665",
                "id": 999,
            },
        )
        self.assertTrue(created)
        self.assertEqual(event.name, "Raw #1665")

    def test_no_title_at_all_falls_back_to_the_number_only(self):
        event, created = self.scraper._create_or_update_episode(
            self.show,
            {
                "air_date": "2024-01-15",
                "episode_number": 1666,
                "season_number": 32,
                "name": "",
            },
        )
        self.assertTrue(created)
        self.assertEqual(event.name, "Raw #1666")


class EnrichEpisodeWithMatchesTest(TestCase):
    """Regression for bug 2: cagematch_event_id must persist even when no
    match on the page has a parseable match_text.
    """

    def setUp(self):
        self.promotion = Promotion.objects.create(name="WWE", abbreviation="WWE")
        self.show = TVShow.objects.create(name="Raw", promotion=self.promotion)
        self.episode = Event.objects.create(
            name="Raw #1665",
            promotion=self.promotion,
            tv_show=self.show,
            date=timezone.now().date(),
            episode_number=1665,
        )
        self.scraper = TVEpisodeScraper()

    def test_cagematch_event_id_persists_even_when_no_match_has_text(self):
        """The exact bug: matches exist (so the early-return at "no matches
        found" doesn't fire) but every one lacks match_text, so
        matches_added stays 0, but cagematch_event_id must still be saved.
        """
        fake_event_data = {
            "cagematch_id": 555000,
            "matches": [{"match_text": "", "wrestlers": []}],
        }
        with patch.object(self.scraper.cagematch, "search_event", return_value=fake_event_data):
            results = self.scraper.enrich_episode_with_matches(self.episode)

        self.assertEqual(results["matches_added"], 0)
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.cagematch_event_id, 555000)
        # matches_added was 0, so this run alone shouldn't claim verification.
        self.assertFalse(self.episode.verified)

    def test_cagematch_event_id_and_verification_both_persist_on_a_real_match(self):
        fake_event_data = {
            "cagematch_id": 555001,
            "matches": [
                {
                    "match_text": "Wrestler A vs. Wrestler B",
                    "wrestlers": [],
                    "result": "Wrestler A wins",
                    "match_type": "Singles",
                }
            ],
        }
        with patch.object(self.scraper.cagematch, "search_event", return_value=fake_event_data):
            results = self.scraper.enrich_episode_with_matches(self.episode)

        self.assertEqual(results["matches_added"], 1)
        self.assertTrue(results["verified"])
        self.episode.refresh_from_db()
        self.assertEqual(self.episode.cagematch_event_id, 555001)
        self.assertTrue(self.episode.verified)
        self.assertEqual(self.episode.verification_source, "cagematch")

    def test_no_matches_at_all_does_not_save_the_episode(self):
        """Sanity check for the fix: the early return before any data is
        found must not be affected by the episode_needs_save bookkeeping.
        """
        with patch.object(self.scraper.cagematch, "search_event", return_value=None):
            results = self.scraper.enrich_episode_with_matches(self.episode)

        self.assertEqual(results["matches_added"], 0)
        self.episode.refresh_from_db()
        self.assertIsNone(self.episode.cagematch_event_id)
        self.assertFalse(self.episode.verified)
