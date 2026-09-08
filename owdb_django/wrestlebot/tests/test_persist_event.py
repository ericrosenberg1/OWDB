"""
Regression tests for pipeline/persist_event.py::persist_event.

Coverage:
    - `event.venue` used to be reassigned on ANY re-persist where the
      newly-resolved venue differed from what's already stored (no
      "already set" check, unlike every other field here, and no drift
      log at all) -- silently relinking an already-correct event to a
      different venue. Now first-write-wins, with a drift warning logged
      instead of a silent overwrite.
    - `event.attendance` used to check `not event.attendance`, which
      treats a genuine attendance of 0 (e.g. a closed-set taping) the
      same as "unset" and lets a later source silently overwrite it.
      Now checks `is None`.
"""

from __future__ import annotations

from datetime import date

from django.test import TestCase

from owdb_django.owdbapp.models import Event, Venue
from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.pipeline.persist_event import persist_event
from owdb_django.wrestlebot.sources.base import EventFields, FieldSnippet


def _make_fetch(candidate_name="Test Event"):
    return SourceFetch.objects.create(
        source="wikipedia",
        url="https://en.wikipedia.org/wiki/Test_Event",
        http_status=200,
        content_hash="cafebabe" * 8,
        candidate_name=candidate_name,
    )


def _wwe_fields(venue_name=None, attendance=None, event_date=None):
    kwargs = dict(
        name=FieldSnippet(value="Test Event", snippet="article title"),
        date=FieldSnippet(value=event_date or date(2024, 1, 1), snippet="infobox date"),
        promotion_name=FieldSnippet(value="WWE", snippet="infobox promotion"),
    )
    if venue_name is not None:
        kwargs["venue_name"] = FieldSnippet(value=venue_name, snippet="infobox venue")
    if attendance is not None:
        kwargs["attendance"] = FieldSnippet(value=attendance, snippet="infobox attendance")
    return EventFields(**kwargs)


class EventVenueFirstWriteWinsTests(TestCase):
    def test_venue_set_when_previously_unset(self):
        fetch = _make_fetch()
        result = persist_event("Test Event", _wwe_fields(venue_name="Madison Square Garden"), fetch)
        self.assertIsNotNone(result)
        event = Event.objects.get(id=result.event_id)
        self.assertIsNotNone(event.venue)
        self.assertEqual(event.venue.name, "Madison Square Garden")

    def test_second_source_does_not_silently_relink_the_venue(self):
        fetch1 = _make_fetch()
        result1 = persist_event(
            "Test Event", _wwe_fields(venue_name="Madison Square Garden"), fetch1
        )
        original_venue_id = Event.objects.get(id=result1.event_id).venue_id
        self.assertIsNotNone(original_venue_id)

        fetch2 = _make_fetch()
        fetch2.entity_id = result1.event_id
        fetch2.entity_type = "event"
        with self.assertLogs(
            "owdb_django.wrestlebot.pipeline.persist_event", level="WARNING"
        ) as cm:
            persist_event("Test Event", _wwe_fields(venue_name="T-Mobile Arena"), fetch2)

        self.assertTrue(any("Source drift" in msg for msg in cm.output))
        event = Event.objects.get(id=result1.event_id)
        self.assertEqual(
            event.venue_id,
            original_venue_id,
            "the original venue must survive a disagreeing second source",
        )
        self.assertEqual(event.venue.name, "Madison Square Garden")
        # The disagreeing venue is still stubbed out (for later reconciliation)
        # -- just not linked onto this event.
        self.assertTrue(Venue.objects.filter(name="T-Mobile Arena").exists())


class EventAttendanceZeroTests(TestCase):
    def test_attendance_zero_is_preserved_not_treated_as_unset(self):
        fetch1 = _make_fetch()
        result1 = persist_event("Test Event", _wwe_fields(attendance=0), fetch1)
        event = Event.objects.get(id=result1.event_id)
        self.assertEqual(event.attendance, 0)

        fetch2 = _make_fetch()
        fetch2.entity_id = result1.event_id
        fetch2.entity_type = "event"
        persist_event("Test Event", _wwe_fields(attendance=15000), fetch2)

        event.refresh_from_db()
        self.assertEqual(
            event.attendance,
            0,
            "a genuine attendance of 0 must not be overwritten by a later source",
        )

    def test_attendance_is_set_when_previously_unset(self):
        fetch = _make_fetch()
        result = persist_event("Test Event", _wwe_fields(attendance=15000), fetch)
        event = Event.objects.get(id=result.event_id)
        self.assertEqual(event.attendance, 15000)
