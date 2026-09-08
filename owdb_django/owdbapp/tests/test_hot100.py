"""
Tests for the Hot 100 ranking calculator.

Regression coverage for the owdbapp bug-fix sweep, item 1:
``_calc_news_score``, ``_calc_social_score`` and ``_calc_views_score`` used to
return an ``md5(wrestler.name...)``-derived pseudo-random number dressed up as
"deterministic variation", fabricated data blended into ``total_score`` as if
it were real news/social/analytics signal, worth up to ~30 raw points (roughly
a third of a wrestler's score) for a wrestler with zero real match activity.
They now return 0 until those integrations actually exist.
"""

from datetime import date

from django.test import TestCase

from ..models import Hot100Calculator, Wrestler


class Hot100FakeDataRemovedTest(TestCase):
    """The three unimplemented score components never fabricate a number."""

    def setUp(self):
        self.calculator = Hot100Calculator(year=2026, month=1)
        # Deliberately maximal "rich profile": every field the old hash-based
        # methods used to reward (long bio, all three source URLs, an image,
        # a recent debut, no retirement year) is populated, so the old code
        # would have scored this wrestler up to ~28 fake points despite them
        # having zero real matches. Two different names, because the old
        # implementation's "variation" hashed the wrestler's name, so
        # different names had to produce different fake scores.
        self.wrestler_a = Wrestler.objects.create(
            name="Alpha Wrestler",
            debut_year=2015,
            about="A" * 500,
            wikipedia_url="https://en.wikipedia.org/wiki/Alpha_Wrestler",
            cagematch_url="https://www.cagematch.net/?id=2&nr=1",
            profightdb_url="https://www.profightdb.com/wrestlers/alpha.html",
            image_url="https://example.com/alpha.jpg",
        )
        self.wrestler_b = Wrestler.objects.create(
            name="Zeta Wrestler",
            debut_year=2020,
            about="B" * 500,
            wikipedia_url="https://en.wikipedia.org/wiki/Zeta_Wrestler",
            cagematch_url="https://www.cagematch.net/?id=2&nr=2",
            profightdb_url="https://www.profightdb.com/wrestlers/zeta.html",
            image_url="https://example.com/zeta.jpg",
        )

    def test_news_score_is_always_zero(self):
        self.assertEqual(self.calculator._calc_news_score(self.wrestler_a), 0.0)
        self.assertEqual(self.calculator._calc_news_score(self.wrestler_b), 0.0)

    def test_social_score_is_always_zero(self):
        self.assertEqual(self.calculator._calc_social_score(self.wrestler_a), 0.0)
        self.assertEqual(self.calculator._calc_social_score(self.wrestler_b), 0.0)

    def test_views_score_is_always_zero(self):
        self.assertEqual(self.calculator._calc_views_score(self.wrestler_a), 0.0)
        self.assertEqual(self.calculator._calc_views_score(self.wrestler_b), 0.0)

    def test_total_score_excludes_fabricated_components(self):
        """total_score must equal match+importance+title+opponent only.

        With no real match, title, or previous-ranking data, every one of
        those four real components is 0 for this wrestler, so under the old
        code (hash-based news/social/views fabricating up to ~28 points for
        exactly this "rich profile, zero activity" shape), total_score would
        have been nonzero despite there being no real signal at all.
        """
        start_date = date(2026, 1, 1)
        end_date = date(2026, 2, 1)
        score_data = self.calculator._calculate_wrestler_score(
            self.wrestler_a, start_date, end_date
        )
        self.assertEqual(score_data["news_mention_score"], 0.0)
        self.assertEqual(score_data["social_engagement_score"], 0.0)
        self.assertEqual(score_data["website_views_score"], 0.0)
        expected_total = round(
            score_data["match_count_score"]
            + score_data["match_importance_score"]
            + score_data["title_activity_score"]
            + score_data["opponent_quality_score"],
            2,
        )
        self.assertEqual(score_data["total_score"], expected_total)
        # The concrete regression: a fully "rich" profile with zero real
        # wrestling activity must score exactly 0, not ~28 fabricated points.
        self.assertEqual(score_data["total_score"], 0.0)
