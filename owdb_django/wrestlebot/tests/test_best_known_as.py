"""
Tests for the Wikipedia adapter's `best_known_as` extraction.

Wikipedia titles wrestler articles inconsistently — sometimes at the ring
name ("Triple H"), sometimes at the legal name ("Matt Bloom"), sometimes
at a ring name with a disambig suffix ("Rikishi (wrestler)"). The adapter
detects the "fans know him as" name from the article's lede and from
disambig-suffix stripping; the persist layer uses that for `Wrestler.name`.

These tests pin the four representative shapes:

  - Lede-driven swap   : "Curt Hennig" → "Mr. Perfect"
  - Disambig-only swap : "Rikishi (wrestler)" → "Rikishi"
  - No swap, no signal : "Matt Bloom" (no "better known as" phrase)
  - No swap, identical : "Hulk Hogan" (lede says "Hulk Hogan", same as title)
"""

from __future__ import annotations

import gzip
import os

from django.test import TestCase

from owdb_django.wrestlebot.sources.wikipedia import (
    WikipediaAdapter,
    _best_known_as_from_article,
)
from owdb_django.wrestlebot.sources.base import FieldSnippet
from bs4 import BeautifulSoup

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_html(name: str) -> str:
    with gzip.open(os.path.join(FIXTURE_DIR, name), "rt", encoding="utf-8") as f:
        return f.read()


class BestKnownAsFromLedeTests(TestCase):
    """
    Direct unit tests of the parser against fixture HTML, bypassing the
    full extract pipeline. Asserts the (value, presence-or-absence) pair
    for each canonical case.
    """

    def _check(self, fixture: str, article_title: str, expected: str | None):
        soup = BeautifulSoup(_load_html(fixture), "lxml")
        snip = _best_known_as_from_article(soup, article_title)
        if expected is None:
            self.assertIsNone(
                snip,
                f"expected no best_known_as for {article_title!r}, got {snip!r}",
            )
        else:
            self.assertIsNotNone(snip, f"expected {expected!r} for {article_title!r}, got None")
            self.assertEqual(snip.value, expected)
            # Snippet must carry quotable evidence so the accuracy contract
            # can attribute the name to a source.
            self.assertTrue(snip.snippet, "best_known_as snippet must be non-empty")

    def test_real_name_article_swaps_to_ring_name(self):
        # Article title is the legal name; lede declares the ring name.
        self._check(
            "wiki_wrestler_curt_hennig.html.gz",
            article_title="Curt Hennig",
            expected="Mr. Perfect",
        )

    def test_disambig_suffix_stripped_when_no_lede_signal(self):
        # Lede says "best known under the ring names Rikishi and Fatu" —
        # we pick the first ring name. Even without that signal, the
        # disambig-strip fallback would also produce "Rikishi".
        self._check(
            "wiki_wrestler_rikishi.html.gz",
            article_title="Rikishi (wrestler)",
            expected="Rikishi",
        )

    def test_no_signal_no_swap(self):
        # Matt Bloom's lede has no "better known as" phrase — he held too
        # many ring names (Albert, A-Train, Tensai, Giant Bernard) for
        # any one to dominate. Leave article title in place.
        self._check(
            "wiki_wrestler_matt_bloom.html.gz",
            article_title="Matt Bloom",
            expected=None,
        )

    def test_lede_matches_title_no_swap(self):
        # Hulk Hogan's lede says "better known by his ring name Hulk Hogan" —
        # same as the article title, so we'd be swapping it for itself.
        # The parser returns None to signal "no change needed."
        self._check(
            "wiki_wrestler_hulk_hogan.html.gz",
            article_title="Hulk Hogan",
            expected=None,
        )


class BestKnownAsViaExtractWrestlerTests(TestCase):
    """
    Integration tests: confirm extract_wrestler populates WrestlerFields
    .best_known_as when article_title is provided, and leaves it None
    when article_title is omitted (backwards compatibility for callers
    that pre-date the new signature).
    """

    def setUp(self):
        self.adapter = WikipediaAdapter()
        self.html = _load_html("wiki_wrestler_curt_hennig.html.gz")

    def test_populates_when_title_supplied(self):
        fields = self.adapter.extract_wrestler(self.html, article_title="Curt Hennig")
        self.assertIsNotNone(fields)
        self.assertIsNotNone(fields.best_known_as)
        self.assertEqual(fields.best_known_as.value, "Mr. Perfect")

    def test_skipped_when_title_omitted(self):
        # Old call shape — adapter shouldn't crash, just skip the field.
        fields = self.adapter.extract_wrestler(self.html)
        self.assertIsNotNone(fields)
        self.assertIsNone(fields.best_known_as)


class BestKnownAsRegexEdgeCases(TestCase):
    """
    Targeted regex tests using synthetic ledes. These pin the variants
    the regex must tolerate without re-fetching real Wikipedia HTML.
    """

    def _extract(self, lede: str, article_title: str = "Article Title"):
        from owdb_django.wrestlebot.sources.wikipedia import _ring_name_from_lede

        return _ring_name_from_lede(lede)

    def test_better_known_by_ring_name(self):
        self.assertEqual(
            self._extract("X (born 1970), better known by his ring name Bad Dude, is a wrestler."),
            "Bad Dude",
        )

    def test_also_known_by_the_ring_name(self):
        self.assertEqual(
            self._extract("X (born 1970), also known by the ring name Triple H, is a wrestler."),
            "Triple H",
        )

    def test_best_known_under_ring_names_picks_first(self):
        # When the lede lists multiple ring names with "and", the first is
        # the most-famous one — that's the one we want to surface.
        self.assertEqual(
            self._extract(
                "X (born 1970) is a wrestler best known under the ring names Tensai and A-Train."
            ),
            "Tensai",
        )

    def test_known_professionally_as(self):
        self.assertEqual(
            self._extract("X (born 1970), known professionally as Kane, is a wrestler."),
            "Kane",
        )

    def test_quoted_ring_name_strips_quotes(self):
        # Wikipedia wraps some ring names in quotes — "Dwayne Johnson ... ring name 'The Rock'".
        self.assertEqual(
            self._extract('X (born 1970), also known by his ring name "The Rock", is an actor.'),
            "The Rock",
        )

    def test_internal_period_preserved(self):
        # "Mr. Perfect" — internal period must not be treated as a sentence stop.
        self.assertEqual(
            self._extract(
                "X (born 1970), better known by his ring name Mr. Perfect, was a wrestler."
            ),
            "Mr. Perfect",
        )

    def test_stage_name_variant(self):
        # André the Giant: "stage name" instead of "ring name".
        self.assertEqual(
            self._extract(
                "X (born 1970), best known by his stage name André the Giant, was a wrestler."
            ),
            "André the Giant",
        )

    def test_no_phrase_returns_none(self):
        self.assertIsNone(
            self._extract(
                "John Cena (born 1977) is an American actor and retired professional wrestler."
            ),
        )


class PersistUsesBestKnownAsTests(TestCase):
    """
    End-to-end check that persist_wrestler honors best_known_as when
    creating a wrestler row.
    """

    def test_canonical_name_prefers_best_known_as(self):
        from owdb_django.owdbapp.models import Wrestler
        from owdb_django.wrestlebot.models import SourceFetch
        from owdb_django.wrestlebot.sources.base import WrestlerFields
        from owdb_django.wrestlebot.pipeline.persist import persist_wrestler

        fetch = SourceFetch.objects.create(
            source="wikipedia",
            url="https://en.wikipedia.org/wiki/Curt_Hennig",
            entity_type="wrestler",
            candidate_name="Curt Hennig",
            http_status=200,
            content_hash="x" * 64,
            raw_content="",
        )
        fields = WrestlerFields(
            real_name=FieldSnippet(value="Curtis Michael Hennig", snippet="Born", confidence=95),
            aliases=FieldSnippet(
                value="Mr. Perfect, Curt Hennig", snippet="Ring names", confidence=90
            ),
            best_known_as=FieldSnippet(
                value="Mr. Perfect",
                snippet="better known by his ring name Mr. Perfect",
                confidence=92,
            ),
        )

        result = persist_wrestler("Curt Hennig", fields, fetch)
        self.assertIsNotNone(result)
        wrestler = Wrestler.objects.get(id=result.wrestler_id)
        self.assertEqual(wrestler.name, "Mr. Perfect")
        # Legal name and aliases preserved.
        self.assertEqual(wrestler.real_name, "Curtis Michael Hennig")
        self.assertIn("Curt Hennig", wrestler.aliases or "")

    def test_falls_back_to_candidate_when_no_best_known_as(self):
        from owdb_django.owdbapp.models import Wrestler
        from owdb_django.wrestlebot.models import SourceFetch
        from owdb_django.wrestlebot.sources.base import WrestlerFields
        from owdb_django.wrestlebot.pipeline.persist import persist_wrestler

        fetch = SourceFetch.objects.create(
            source="wikipedia",
            url="https://en.wikipedia.org/wiki/Matt_Bloom",
            entity_type="wrestler",
            candidate_name="Matt Bloom",
            http_status=200,
            content_hash="y" * 64,
            raw_content="",
        )
        # best_known_as deliberately unset — Matt Bloom has no clear winner.
        fields = WrestlerFields(
            real_name=FieldSnippet(value="Matthew Jason Bloom", snippet="Born", confidence=95),
        )
        result = persist_wrestler("Matt Bloom", fields, fetch)
        self.assertIsNotNone(result)
        wrestler = Wrestler.objects.get(id=result.wrestler_id)
        self.assertEqual(wrestler.name, "Matt Bloom")
