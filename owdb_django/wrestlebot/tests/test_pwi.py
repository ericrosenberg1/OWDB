"""
Tests for the PWI 500 / PWI Female 50/100/150 ingester.

Coverage:
    - Manual wrestler links are preserved across reruns even when the
      auto name-match fails (different spelling, alias not yet added,
      etc.). This is the "100% accuracy first" contract: a human (or Al
      Snow) correction must never be silently undone by automation.
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase

from owdb_django.owdbapp.models import (
    ExternalRanking, ExternalRankingEntry, Wrestler,
)
from owdb_django.wrestlebot.pipeline import pwi
from owdb_django.wrestlebot.pipeline.pwi import PWIEntry


class PreservesManualLinkOnRerunTests(TestCase):
    """
    Regression: prior code passed `wrestler=w if w else None` in defaults,
    which clobbered manually-linked wrestlers to NULL whenever the next
    rerun's name lookup failed.
    """

    def _run_with(self, entries):
        with mock.patch.object(pwi, "fetch_pwi_list", return_value=entries):
            return pwi.ingest_pwi_list("pwi_500", 2024)

    def test_manual_link_survives_failed_auto_match(self):
        # First run: published name doesn't match any Wrestler, so the
        # entry is created with wrestler=NULL.
        first = self._run_with([
            PWIEntry(position=1, wrestler_name="Hulk Hogan"),
        ])
        self.assertEqual(first["matched_wrestlers"], 0)
        entry = ExternalRankingEntry.objects.get(
            ranking_id=first["ranking_id"], position=1,
        )
        self.assertIsNone(entry.wrestler)

        # A human (or Al Snow) manually links the entry to the correct
        # Wrestler row, whose canonical name differs from what PWI
        # published this year.
        terry = Wrestler.objects.create(name="Terry Bollea")
        entry.wrestler = terry
        entry.save(update_fields=["wrestler"])

        # Rerun the ingester. The published name STILL doesn't auto-match
        # ("Hulk Hogan" != "Terry Bollea", no alias on file).
        second = self._run_with([
            PWIEntry(position=1, wrestler_name="Hulk Hogan"),
        ])
        self.assertEqual(second["matched_wrestlers"], 0)

        entry.refresh_from_db()
        self.assertEqual(
            entry.wrestler_id, terry.id,
            "manual wrestler link must survive a rerun where the auto "
            "name-match fails — otherwise automation silently undoes "
            "human corrections",
        )

    def test_auto_match_still_sets_fk_on_existing_entry(self):
        # Entry exists with no link. The wrestler row exists and IS
        # name-matchable. A rerun should set the FK (no manual link to
        # protect here).
        first = self._run_with([
            PWIEntry(position=2, wrestler_name="Roman Reigns"),
        ])
        ExternalRankingEntry.objects.get(
            ranking_id=first["ranking_id"], position=2, wrestler__isnull=True,
        )

        roman = Wrestler.objects.create(name="Roman Reigns")
        second = self._run_with([
            PWIEntry(position=2, wrestler_name="Roman Reigns"),
        ])
        self.assertEqual(second["matched_wrestlers"], 1)
        entry = ExternalRankingEntry.objects.get(
            ranking_id=second["ranking_id"], position=2,
        )
        self.assertEqual(entry.wrestler_id, roman.id)
