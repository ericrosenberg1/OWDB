"""
Tests for the accuracy contract — the structural backbone that makes
"100% accuracy" enforceable rather than aspirational.

Coverage:
    - Contract.is_satisfied returns False when required FieldProvenance
      rows are missing, True when all present.
    - enforce() returns 'candidate' on hard-block (forbidden_state),
      'provisional' on missing provenance only, 'verified' when both pass.
    - check_provenance_coverage() observes verified entities without
      contract-required provenance.
    - record_provenance + bulk_synthetic_provenance write `snippet` and
      `confidence` correctly.
    - venue_name_not_a_city catches the multi-venue row bug.
    - match_must_have_participants catches verified-zero-participant
      matches.
"""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from owdb_django.owdbapp.models import (
    Event,
    Match,
    Promotion,
    Venue,
    Wrestler,
)
from owdb_django.wrestlebot.models import SourceFetch, FieldProvenance
from owdb_django.wrestlebot.pipeline import accuracy_contract
from owdb_django.wrestlebot.pipeline._provenance import (
    record_provenance,
    bulk_synthetic_provenance,
    entity_has_full_provenance,
)


def _make_source_fetch():
    return SourceFetch.objects.create(
        source="wikipedia",
        url="https://en.wikipedia.org/wiki/Test",
        entity_type="event",
        entity_id=0,
        candidate_name="Test",
        http_status=200,
        content_hash="testhash",
        raw_content="<html/>",
    )


class ProvenanceWriterTests(TestCase):
    """The shared writer + bulk variant."""

    def setUp(self):
        self.fetch = _make_source_fetch()
        self.venue = Venue.objects.create(name="Test Arena")

    def test_record_provenance_writes_snippet(self):
        fp = record_provenance(
            entity_type="venue",
            entity_id=self.venue.id,
            field_name="name",
            value="Test Arena",
            source_fetch=self.fetch,
            snippet="snippet text here",
            confidence=85,
        )
        self.assertEqual(fp.snippet, "snippet text here")
        self.assertEqual(fp.value, "Test Arena")
        self.assertEqual(fp.confidence, 85)
        # captured_at alias works (was broken before P0-1)
        self.assertEqual(fp.captured_at, fp.extracted_at)

    def test_record_provenance_clamps_confidence(self):
        fp = record_provenance(
            entity_type="venue",
            entity_id=self.venue.id,
            field_name="name",
            value="X",
            source_fetch=self.fetch,
            confidence=999,
        )
        self.assertEqual(fp.confidence, 100)

    def test_bulk_synthetic_provenance_writes_all_fields(self):
        n = bulk_synthetic_provenance(
            entity_type="venue",
            entity_id=self.venue.id,
            field_values={"name": "A", "location": "B", "capacity": 1000},
            source_fetch=self.fetch,
            snippet_hint="row text",
            confidence=70,
        )
        self.assertEqual(n, 3)
        rows = FieldProvenance.objects.filter(
            entity_type="venue",
            entity_id=self.venue.id,
        )
        for r in rows:
            self.assertEqual(r.snippet, "row text")
            self.assertEqual(r.confidence, 70)

    def test_bulk_synthetic_skips_empty_values(self):
        n = bulk_synthetic_provenance(
            entity_type="venue",
            entity_id=self.venue.id,
            field_values={"name": "A", "city": None, "capacity": ""},
            source_fetch=self.fetch,
            snippet_hint="x",
        )
        self.assertEqual(n, 1)

    def test_entity_has_full_provenance(self):
        self.assertFalse(
            entity_has_full_provenance("venue", self.venue.id, required_fields=("name",))
        )
        record_provenance(
            entity_type="venue",
            entity_id=self.venue.id,
            field_name="name",
            value="Test Arena",
            source_fetch=self.fetch,
        )
        self.assertTrue(
            entity_has_full_provenance("venue", self.venue.id, required_fields=("name",))
        )


class ContractEnforceTests(TestCase):
    def setUp(self):
        self.fetch = _make_source_fetch()
        self.promotion = Promotion.objects.create(name="Test Pro")

    def test_event_without_provenance_is_provisional(self):
        ev = Event.objects.create(
            name="Test Event",
            date=date(2024, 1, 1),
            promotion=self.promotion,
        )
        state, reasons = accuracy_contract.enforce("event", ev)
        # Missing both name + date provenance.
        self.assertEqual(state, accuracy_contract.PROVISIONAL)
        self.assertTrue(any("name" in r for r in reasons))

    def test_event_with_provenance_is_verified(self):
        ev = Event.objects.create(
            name="Test Event",
            date=date(2024, 1, 1),
            promotion=self.promotion,
        )
        record_provenance(
            entity_type="event",
            entity_id=ev.id,
            field_name="name",
            value="Test Event",
            source_fetch=self.fetch,
        )
        record_provenance(
            entity_type="event",
            entity_id=ev.id,
            field_name="date",
            value="2024-01-01",
            source_fetch=self.fetch,
        )
        state, _ = accuracy_contract.enforce("event", ev)
        self.assertEqual(state, accuracy_contract.VERIFIED)

    def test_event_without_promotion_is_candidate(self):
        """Forbidden-state check is a hard block; provenance alone isn't enough."""
        ev = Event.objects.create(
            name="Orphan",
            date=date(2024, 1, 1),
            promotion=self.promotion,  # Django requires it; we'll null it
        )
        ev.promotion_id = None
        # Provide provenance for required fields too.
        record_provenance(
            entity_type="event",
            entity_id=ev.id,
            field_name="name",
            value="X",
            source_fetch=self.fetch,
        )
        record_provenance(
            entity_type="event",
            entity_id=ev.id,
            field_name="date",
            value="X",
            source_fetch=self.fetch,
        )
        # Despite provenance, no promotion → candidate (hard block).
        state, _ = accuracy_contract.enforce("event", ev)
        self.assertEqual(state, accuracy_contract.CANDIDATE)

    def test_venue_name_looks_like_location_blocks(self):
        v = Venue.objects.create(name="Rosemont, Illinois")
        record_provenance(
            entity_type="venue",
            entity_id=v.id,
            field_name="name",
            value="Rosemont, Illinois",
            source_fetch=self.fetch,
        )
        # Provenance passes but the structural check blocks it.
        state, reasons = accuracy_contract.enforce("venue", v)
        self.assertEqual(state, accuracy_contract.CANDIDATE)
        self.assertTrue(any("location" in r.lower() for r in reasons))

    def test_match_no_participants_blocks(self):
        ev = Event.objects.create(
            name="E",
            date=date(2024, 1, 1),
            promotion=self.promotion,
        )
        m = Match.objects.create(event=ev, match_text="X defeated Y")
        record_provenance(
            entity_type="match",
            entity_id=m.id,
            field_name="match_text",
            value="X defeated Y",
            source_fetch=self.fetch,
        )
        state, _ = accuracy_contract.enforce("match", m)
        self.assertEqual(state, accuracy_contract.CANDIDATE)

    def test_match_with_participant_is_verified(self):
        ev = Event.objects.create(
            name="E",
            date=date(2024, 1, 1),
            promotion=self.promotion,
        )
        m = Match.objects.create(event=ev, match_text="X defeated Y")
        w = Wrestler.objects.create(name="X")
        m.wrestlers.add(w)
        record_provenance(
            entity_type="match",
            entity_id=m.id,
            field_name="match_text",
            value="X defeated Y",
            source_fetch=self.fetch,
        )
        state, _ = accuracy_contract.enforce("match", m)
        self.assertEqual(state, accuracy_contract.VERIFIED)


class ConsistencyMatchTests(TestCase):
    """check_match() rules."""

    def setUp(self):
        self.promotion = Promotion.objects.create(name="P")
        self.event = Event.objects.create(
            name="E",
            date=date(2024, 1, 1),
            promotion=self.promotion,
        )

    def test_match_no_participants_fires(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_match

        m = Match.objects.create(event=self.event, match_text="x")
        issues = check_match(m)
        self.assertTrue(any(i.rule == "match_no_participants" for i in issues))

    def test_match_duration_4h_fires(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_match

        w = Wrestler.objects.create(name="X")
        m = Match.objects.create(
            event=self.event,
            match_text="x",
            duration_seconds=5 * 3600,
        )
        m.wrestlers.add(w)
        issues = check_match(m)
        self.assertTrue(any(i.rule == "match_duration_implausible" for i in issues))

    def test_match_title_change_without_title_fires(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_match

        w = Wrestler.objects.create(name="X")
        m = Match.objects.create(
            event=self.event,
            match_text="x",
            title_changed=True,
        )
        m.wrestlers.add(w)
        issues = check_match(m)
        self.assertTrue(any(i.rule == "match_title_change_without_title" for i in issues))


class ProvenanceCoverageTests(TestCase):
    """check_provenance_coverage observes verified-without-provenance rows."""

    def setUp(self):
        self.fetch = _make_source_fetch()
        self.promotion = Promotion.objects.create(name="P")

    def test_verified_event_without_provenance_flagged(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_provenance_coverage

        ev = Event.objects.create(
            name="No Prov Event",
            date=date(2024, 1, 1),
            promotion=self.promotion,
            verified=True,
            verification_state="verified",
        )
        issues = check_provenance_coverage("event", ev)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].rule, "verified_without_provenance")
        self.assertEqual(issues[0].severity, "error")

    def test_verified_with_provenance_no_finding(self):
        from owdb_django.wrestlebot.pipeline.consistency import check_provenance_coverage

        ev = Event.objects.create(
            name="OK Event",
            date=date(2024, 1, 1),
            promotion=self.promotion,
            verified=True,
            verification_state="verified",
        )
        bulk_synthetic_provenance(
            entity_type="event",
            entity_id=ev.id,
            field_values={"name": ev.name, "date": ev.date.isoformat()},
            source_fetch=self.fetch,
            snippet_hint="x",
            confidence=80,
        )
        issues = check_provenance_coverage("event", ev)
        self.assertEqual(issues, [])

    def test_candidate_state_not_flagged(self):
        """Only verified rows are subject to provenance-coverage enforcement."""
        from owdb_django.wrestlebot.pipeline.consistency import check_provenance_coverage

        ev = Event.objects.create(
            name="X",
            date=date(2024, 1, 1),
            promotion=self.promotion,
            verified=False,
            verification_state="candidate",
        )
        issues = check_provenance_coverage("event", ev)
        self.assertEqual(issues, [])
