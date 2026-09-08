"""
Tests for the Wikipedia Results-table match extractor.

Coverage:
    - card_position is stable across reruns (idempotency).
    - When a page has multiple Results tables (e.g., pre-show + main card,
      or multi-night PPVs), each table gets its own position namespace so
      adding/removing a sibling table doesn't collide on (event, match_order)
      in persistence.
    - persist_matches_for_event prunes orphan Wikipedia-sourced Match rows
      whose match_order no longer appears in the extracted set (so a
      sibling table appearing on Wikipedia doesn't leave stale rows behind).
"""

from __future__ import annotations

from datetime import date

from django.test import SimpleTestCase, TestCase

from owdb_django.owdbapp.models import Event, Match, Promotion, Wrestler
from owdb_django.wrestlebot.models import FieldProvenance, SourceFetch
from owdb_django.wrestlebot.pipeline.match_extract import (
    extract_matches, persist_matches_for_event,
)


# Minimal HTML that satisfies _looks_like_results_table:
# - first column header is "No."
# - row contains "Results" and "Stipulation"/"Match"
_TWO_TABLE_HTML = """
<html><body>
<h2>Pre-show</h2>
<table class="wikitable">
  <tr><th>No.</th><th>Results</th><th>Stipulations</th><th>Times</th></tr>
  <tr><td>1</td><td>Aja Kong defeated Bull Nakano by pinfall</td>
      <td>Singles match</td><td>10:00</td></tr>
  <tr><td>2</td><td>Manami Toyota defeated Akira Hokuto by submission</td>
      <td>Singles match</td><td>12:34</td></tr>
</table>

<h2>Main card</h2>
<table class="wikitable">
  <tr><th>No.</th><th>Results</th><th>Stipulations</th><th>Times</th></tr>
  <tr><td>1</td><td>Owen Hart defeated Bret Hart by pinfall</td>
      <td>Singles match</td><td>20:21</td></tr>
  <tr><td>2</td><td>Razor Ramon defeated Diesel by pinfall</td>
      <td>Singles match for the Intercontinental Championship</td><td>15:00</td></tr>
  <tr><td>3</td><td>The Undertaker defeated Yokozuna by pinfall</td>
      <td>Casket match</td><td>17:00</td></tr>
</table>
</body></html>
"""

_MAIN_CARD_ONLY_HTML = """
<html><body>
<h2>Main card</h2>
<table class="wikitable">
  <tr><th>No.</th><th>Results</th><th>Stipulations</th><th>Times</th></tr>
  <tr><td>1</td><td>Owen Hart defeated Bret Hart by pinfall</td>
      <td>Singles match</td><td>20:21</td></tr>
  <tr><td>2</td><td>Razor Ramon defeated Diesel by pinfall</td>
      <td>Singles match for the Intercontinental Championship</td><td>15:00</td></tr>
  <tr><td>3</td><td>The Undertaker defeated Yokozuna by pinfall</td>
      <td>Casket match</td><td>17:00</td></tr>
</table>
</body></html>
"""


class MatchOrderIdempotencyTests(SimpleTestCase):
    """card_position must be deterministic and not collide across tables."""

    def test_card_position_stable_across_reruns(self):
        run1 = [m.card_position for m in extract_matches(_TWO_TABLE_HTML)]
        run2 = [m.card_position for m in extract_matches(_TWO_TABLE_HTML)]
        self.assertEqual(run1, run2)

    def test_each_table_has_its_own_namespace(self):
        # First table → 1, 2. Second table → 101, 102, 103.
        positions = [m.card_position for m in extract_matches(_TWO_TABLE_HTML)]
        self.assertEqual(positions, [1, 2, 101, 102, 103])

    def test_positions_unique_when_multiple_tables(self):
        # Regression: the old code accumulated a single counter across tables,
        # which gave [1,2,3,4,5]. Per-table reset without namespacing would
        # collide as [1,2,1,2,3]. We assert uniqueness so neither bug returns.
        positions = [m.card_position for m in extract_matches(_TWO_TABLE_HTML)]
        self.assertEqual(len(positions), len(set(positions)))

    def test_single_table_starts_at_one(self):
        positions = [m.card_position for m in extract_matches(_MAIN_CARD_ONLY_HTML)]
        self.assertEqual(positions, [1, 2, 3])


class OrphanPruneTests(TestCase):
    """
    When Wikipedia adds a pre-show table to a page that previously had only
    the main card, main-card matches shift from [1, 2, 3] to [101, 102, 103].
    The old rows must be pruned so the DB matches the source 1:1.
    """

    def setUp(self):
        self.promo = Promotion.objects.create(name="Test Pro")
        self.event = Event.objects.create(
            name="Test PPV", date=date(2024, 1, 1), promotion=self.promo,
        )
        # Seed wrestlers so participants resolve and match rows reach
        # 'verified' state (incidental — we just don't want the contract
        # enforcer to interact weirdly with our orphan assertions).
        for nm in [
            "Owen Hart", "Bret Hart", "Razor Ramon", "Diesel",
            "The Undertaker", "Yokozuna",
            "Aja Kong", "Bull Nakano", "Manami Toyota", "Akira Hokuto",
        ]:
            Wrestler.objects.create(name=nm)

    def _make_fetch(self, html: str) -> SourceFetch:
        return SourceFetch.objects.create(
            source="wikipedia",
            url=f"https://en.wikipedia.org/wiki/Test_{id(html)}",
            entity_type="event", entity_id=self.event.id,
            candidate_name="Test", http_status=200,
            content_hash=f"hash-{id(html)}",
            raw_content=html,
        )

    def test_orphans_pruned_when_table_layout_shifts(self):
        # Initial state: only main card. Persist creates 3 matches at
        # match_order=1,2,3.
        fetch1 = self._make_fetch(_MAIN_CARD_ONLY_HTML)
        stats1 = persist_matches_for_event(self.event, fetch=fetch1)
        self.assertEqual(stats1["created"], 3)
        self.assertEqual(stats1["orphans_pruned"], 0)
        self.assertEqual(
            sorted(Match.objects.filter(event=self.event)
                   .values_list("match_order", flat=True)),
            [1, 2, 3],
        )

        # Wikipedia editor adds a pre-show table. Re-extract should yield
        # positions [1, 2, 101, 102, 103]. The pre-existing match_order=3
        # row is now an orphan and must be deleted.
        fetch2 = self._make_fetch(_TWO_TABLE_HTML)
        stats2 = persist_matches_for_event(self.event, fetch=fetch2)
        self.assertEqual(stats2["extracted"], 5)
        self.assertEqual(stats2["orphans_pruned"], 1)
        self.assertEqual(
            sorted(Match.objects.filter(event=self.event)
                   .values_list("match_order", flat=True)),
            [1, 2, 101, 102, 103],
        )

    def test_field_provenance_for_orphans_is_cleared(self):
        # Persist once; capture the Match.id at match_order=3 and confirm it
        # has FieldProvenance rows.
        fetch1 = self._make_fetch(_MAIN_CARD_ONLY_HTML)
        persist_matches_for_event(self.event, fetch=fetch1)
        orphan_id = Match.objects.get(event=self.event, match_order=3).id
        self.assertGreater(
            FieldProvenance.objects.filter(
                entity_type="match", entity_id=orphan_id,
            ).count(),
            0,
        )

        # Re-persist with the pre-show variant. The match_order=3 row gets
        # pruned; its FieldProvenance must go with it.
        fetch2 = self._make_fetch(_TWO_TABLE_HTML)
        persist_matches_for_event(self.event, fetch=fetch2)
        self.assertFalse(
            Match.objects.filter(id=orphan_id).exists(),
        )
        self.assertEqual(
            FieldProvenance.objects.filter(
                entity_type="match", entity_id=orphan_id,
            ).count(),
            0,
        )

    def test_non_wikipedia_matches_are_not_pruned(self):
        # A manually-added Cagematch match at match_order=3 should survive
        # a Wikipedia re-extraction that doesn't include position 3.
        Match.objects.create(
            event=self.event, match_order=999,
            match_text="Manual entry from Cagematch",
            verification_source="cagematch",
        )
        fetch = self._make_fetch(_MAIN_CARD_ONLY_HTML)
        stats = persist_matches_for_event(self.event, fetch=fetch)
        self.assertEqual(stats["orphans_pruned"], 0)
        self.assertTrue(
            Match.objects.filter(event=self.event, match_order=999).exists(),
        )
