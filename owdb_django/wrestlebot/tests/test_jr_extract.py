"""
Tests for JR's extract stage — specifically that failing extractions still
mark the SourceFetch as used so the queue doesn't recycle dead rows.

Before this fix, `_stage_extract` pulled rows with `used_at__isnull=True`,
and on failure (extractor None, persister None, etc.) the row's `used_at`
stayed NULL — so the next cycle pulled the same dead rows and failed again,
starving genuinely new fetches behind a wall of permanently-broken ones.
"""

from __future__ import annotations

from django.test import TestCase

from owdb_django.wrestlebot.bots.jr import JR
from owdb_django.wrestlebot.models import SourceFetch


def _make_fetch(raw_content: str = "", entity_type: str = "wrestler") -> SourceFetch:
    return SourceFetch.objects.create(
        source="wikipedia",
        url="https://en.wikipedia.org/wiki/Nobody",
        entity_type=entity_type,
        candidate_name="Nobody",
        http_status=200,
        content_hash="nohash",
        raw_content=raw_content,
    )


class JRExtractMarksFetchUsedOnFailureTests(TestCase):
    """Regression: failing extractions must stamp used_at + extraction_outcome."""

    def test_no_fields_marks_fetch_used(self):
        # Empty raw_content => extract_wrestler returns None (no infobox).
        fetch = _make_fetch(raw_content="")
        self.assertIsNone(fetch.used_at)
        self.assertEqual(fetch.extraction_outcome, "")

        result = JR()._extract_and_persist_one(fetch)

        self.assertFalse(result)
        fetch.refresh_from_db()
        self.assertIsNotNone(
            fetch.used_at,
            "Failed extractions must stamp used_at so the queue doesn't recycle them",
        )
        self.assertEqual(fetch.extraction_outcome, "no_fields")

    def test_no_handler_marks_fetch_used(self):
        # Unknown entity_type => no extractor/persister mapping.
        fetch = _make_fetch(entity_type="match")  # not in JR's dispatch table
        result = JR()._extract_and_persist_one(fetch)

        self.assertFalse(result)
        fetch.refresh_from_db()
        self.assertIsNotNone(fetch.used_at)
        self.assertEqual(fetch.extraction_outcome, "no_handler")

    def test_stage_extract_does_not_recycle_failed_rows(self):
        """The whole point: a row that failed once doesn't get re-picked."""
        fetch = _make_fetch(raw_content="")
        jr = JR()

        first = jr._stage_extract(limit=10)
        self.assertEqual(first, 0)  # nothing extracted
        fetch.refresh_from_db()
        self.assertIsNotNone(fetch.used_at)
        first_used_at = fetch.used_at

        # Second pass: pending query filters used_at__isnull=True, so this
        # row should no longer appear; used_at should not be touched again.
        second = jr._stage_extract(limit=10)
        self.assertEqual(second, 0)
        fetch.refresh_from_db()
        self.assertEqual(
            fetch.used_at, first_used_at,
            "used_at should not be re-stamped — the row should have been "
            "filtered out of the pending queue on the second pass",
        )
