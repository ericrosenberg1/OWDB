"""
Tests for the url-slug dedupe pass in ingest_title_history_discovery.

The title-history fix queues Wikipedia link targets ("Curt Hennig"), but
the wrestler may already exist under their ring name ("Mr. Perfect") with
the same wikipedia_url. Plain name-and-alias dedupe misses that overlap
and queues a redundant fetch (wasting API quota and risking a duplicate
Wrestler row if the persist layer doesn't catch the redirect).
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler
from owdb_django.wrestlebot.pipeline.title_history import (
    TitleHistoryFinding,
    _wiki_url_slug,
    ingest_title_history_discovery,
)


class WikiUrlSlugHelperTests(TestCase):
    def test_extracts_path_after_wiki(self):
        self.assertEqual(
            _wiki_url_slug("https://en.wikipedia.org/wiki/Curt_Hennig"),
            "curt_hennig",
        )

    def test_keeps_disambig_suffix(self):
        self.assertEqual(
            _wiki_url_slug("https://en.wikipedia.org/wiki/Rikishi_(wrestler)"),
            "rikishi_(wrestler)",
        )

    def test_strips_fragment_and_query(self):
        self.assertEqual(
            _wiki_url_slug("https://en.wikipedia.org/wiki/Curt_Hennig#Career?foo=bar"),
            "curt_hennig",
        )

    def test_handles_missing_url(self):
        self.assertEqual(_wiki_url_slug(""), "")
        self.assertEqual(_wiki_url_slug("https://example.com/x"), "")


class TitleHistoryDedupeByUrlTests(TestCase):
    def test_wrestler_with_url_dedupes_against_link_target(self):
        """
        Wrestler stored as name="Mr. Perfect" with wikipedia_url ending in
        /Curt_Hennig must dedupe a "Curt Hennig" candidate — the title-
        history fix queues link targets, and the previous name-only logic
        would have re-queued it.
        """
        Wrestler.objects.create(
            name="Mr. Perfect",
            slug="mr-perfect",
            wikipedia_url="https://en.wikipedia.org/wiki/Curt_Hennig",
        )

        # Fake a title-history page that only has "Curt Hennig" as a champ.
        finding = TitleHistoryFinding(
            title_slug="wwe_intercontinental",
            resolved_wikipedia_title="List of WWE Intercontinental Champions",
            source_url="https://en.wikipedia.org/wiki/List_of_WWE_Intercontinental_Champions",
            unique_champions=["Curt Hennig"],
            raw_count_seen=1,
        )

        with (
            patch(
                "owdb_django.wrestlebot.pipeline.title_history.discover_from_title_history",
                return_value=finding,
            ),
            patch("owdb_django.wrestlebot.pipeline.fetch.fetch_wrestler_candidates") as mock_fetch,
        ):
            report = ingest_title_history_discovery(title_slug="wwe_intercontinental")

        # No fetch should have been triggered.
        mock_fetch.assert_not_called()
        self.assertEqual(report["wwe_intercontinental"]["already_in_db"], 1)
        self.assertEqual(report["wwe_intercontinental"]["queued_for_ingest"], 0)

    def test_truly_unknown_wrestler_still_queues(self):
        """Sanity: the dedupe only suppresses URL-overlap candidates."""
        finding = TitleHistoryFinding(
            title_slug="wwe_intercontinental",
            resolved_wikipedia_title="List of WWE Intercontinental Champions",
            source_url="https://en.wikipedia.org/wiki/List_of_WWE_Intercontinental_Champions",
            unique_champions=["Newcomer Joe"],
            raw_count_seen=1,
        )
        with (
            patch(
                "owdb_django.wrestlebot.pipeline.title_history.discover_from_title_history",
                return_value=finding,
            ),
            patch("owdb_django.wrestlebot.pipeline.fetch.fetch_wrestler_candidates") as mock_fetch,
        ):
            report = ingest_title_history_discovery(title_slug="wwe_intercontinental")

        mock_fetch.assert_called_once()
        args, kwargs = mock_fetch.call_args
        self.assertIn("Newcomer Joe", list(args[0]))
        self.assertEqual(report["wwe_intercontinental"]["queued_for_ingest"], 1)
