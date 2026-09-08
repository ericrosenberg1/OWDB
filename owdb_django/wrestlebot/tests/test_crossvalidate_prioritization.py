"""
Regression pin for JR's Wikidata cross-validation candidate selection.

`Wrestler.get_completeness_score()` / `.get_incomplete_profiles()`
(owdbapp/models.py) already existed to prioritize enrichment work, but
nothing called them: `tasks._stage_crossvalidate` (reused by
`bots/jr.py::JR._stage_crossvalidate` for the deterministic `wb_jr` bulk
cycle) picked wrestlers via plain `.order_by("id")` — oldest-created
first, with no regard for how complete their profile already was.

These tests pin the fix (`_crossvalidate_candidates`, extracted from
`_stage_crossvalidate` so the selection logic is testable without mocking
network calls): candidates now come from `get_incomplete_profiles()`'s
priority ordering, narrowed to wrestlers that actually have a Wikipedia
URL (required to resolve a Wikidata QID) and haven't already been
cross-validated. A future refactor that quietly drops this prioritization
(e.g. reverting to `.order_by("id")`) should fail
`test_prioritizes_incomplete_profile_over_older_but_more_complete_one`.
"""

from __future__ import annotations

from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler
from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.tasks import _crossvalidate_candidates


class CrossvalidateCandidatePrioritizationTests(TestCase):
    def test_prioritizes_incomplete_profile_over_older_but_more_complete_one(self):
        # Created FIRST (lowest id) but already fairly complete: has a
        # Wikipedia URL, real_name/hometown/nationality all set. Under
        # get_incomplete_profiles()'s Case/When, this lands in priority
        # bucket 3 (no debut_year), not bucket 1.
        older_more_complete = Wrestler.objects.create(
            name="Older More Complete",
            wikipedia_url="https://en.wikipedia.org/wiki/Older_More_Complete",
            real_name="Real Name One",
            hometown="Somewhere, USA",
            nationality="American",
            debut_year=None,
        )
        # Created SECOND (higher id) but missing real_name -> priority
        # bucket 1 (has wikipedia_url, missing a key field) — ranked ahead
        # of bucket 3 regardless of creation order.
        newer_incomplete = Wrestler.objects.create(
            name="Newer Incomplete",
            wikipedia_url="https://en.wikipedia.org/wiki/Newer_Incomplete",
            real_name=None,
            hometown="Elsewhere",
            nationality="Canadian",
        )
        # No wikipedia_url at all: get_incomplete_profiles() would still
        # rank it (its lower-priority buckets don't require a Wikipedia
        # URL), but _crossvalidate_candidates must skip it — there's no
        # way to resolve a Wikidata QID without one.
        no_wikipedia_url = Wrestler.objects.create(
            name="No Wikipedia URL",
            wikipedia_url=None,
            real_name=None,
        )

        # Sanity check the id ordering this test depends on.
        self.assertLess(older_more_complete.id, newer_incomplete.id)

        candidates = _crossvalidate_candidates(limit=5)
        names = [w.name for w in candidates]

        self.assertNotIn(
            no_wikipedia_url.name,
            names,
            "a wrestler with no wikipedia_url can't resolve a Wikidata QID and must be skipped",
        )
        self.assertIn(newer_incomplete.name, names)
        self.assertIn(older_more_complete.name, names)
        self.assertLess(
            names.index(newer_incomplete.name),
            names.index(older_more_complete.name),
            "the newer-but-more-incomplete wrestler must be prioritized ahead of the "
            "older-but-more-complete one — plain `.order_by('id')` gets this backwards",
        )

    def test_skips_wrestlers_already_cross_validated(self):
        already_done = Wrestler.objects.create(
            name="Already Done",
            wikipedia_url="https://en.wikipedia.org/wiki/Already_Done",
            real_name=None,  # would otherwise be top priority
        )
        SourceFetch.objects.create(
            source="wikidata",
            url="https://www.wikidata.org/wiki/Special:EntityData/Q1.json",
            entity_type="wrestler",
            entity_id=already_done.id,
            candidate_name=already_done.name,
            http_status=200,
            content_hash="abc123",
            raw_content="{}",
        )
        still_pending = Wrestler.objects.create(
            name="Still Pending",
            wikipedia_url="https://en.wikipedia.org/wiki/Still_Pending",
            real_name=None,
        )

        names = [w.name for w in _crossvalidate_candidates(limit=5)]
        self.assertNotIn(already_done.name, names)
        self.assertIn(still_pending.name, names)

    def test_respects_limit(self):
        for i in range(5):
            Wrestler.objects.create(
                name=f"Wrestler {i}",
                wikipedia_url=f"https://en.wikipedia.org/wiki/Wrestler_{i}",
                real_name=None,
            )
        self.assertEqual(len(_crossvalidate_candidates(limit=2)), 2)

    def test_limit_zero_or_negative_returns_empty(self):
        Wrestler.objects.create(
            name="Irrelevant",
            wikipedia_url="https://en.wikipedia.org/wiki/Irrelevant",
            real_name=None,
        )
        self.assertEqual(_crossvalidate_candidates(limit=0), [])
        self.assertEqual(_crossvalidate_candidates(limit=-1), [])
