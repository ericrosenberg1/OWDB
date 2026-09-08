"""
Tests for the /wrestlebot/health/ endpoint.

The view is a re-implementation of the legacy in-app health check against
the new owdb_django.wrestlebot models. These tests pin the JSON shape so
external monitors (which were already pointed at the old endpoint) keep
working after the cutover.
"""

from __future__ import annotations

import json
from datetime import timedelta

from django.test import Client, TestCase
from django.utils import timezone

from owdb_django.wrestlebot.models import (
    EarlObservation,
    FieldProvenance,
    SourceFetch,
    WrestleBotActivity,
    WrestleBotConfig,
)


class WrestleBotHealthTests(TestCase):
    def _get(self):
        resp = Client().get("/wrestlebot/health/")
        self.assertEqual(resp.status_code, 200, resp.content)
        return json.loads(resp.content)

    def test_default_shape(self):
        """No bot config, no fetches — endpoint still returns the full shape."""
        data = self._get()
        for k in (
            "healthy", "enabled", "rate_limiter",
            "today", "queue", "totals", "timestamp",
        ):
            self.assertIn(k, data, f"missing key {k!r} in response")
        # Defaults: enabled True, healthy True, queue empty.
        self.assertTrue(data["enabled"])
        self.assertTrue(data["healthy"])
        self.assertEqual(data["queue"]["total"], 0)
        self.assertIn(data["rate_limiter"], {"redis", "local_fallback"})

    def test_disabled_config_marks_unhealthy(self):
        WrestleBotConfig.objects.update_or_create(
            key="enabled", defaults={"value": False},
        )
        data = self._get()
        self.assertFalse(data["enabled"])
        self.assertFalse(data["healthy"])

    def test_queue_counts_unprocessed_fetches(self):
        # Three queued fetches across two types; one processed (excluded).
        SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/A",
            entity_type="wrestler", candidate_name="A",
            http_status=200, content_hash="a" * 64, raw_content="",
        )
        SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/B",
            entity_type="wrestler", candidate_name="B",
            http_status=200, content_hash="b" * 64, raw_content="",
        )
        SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/E1",
            entity_type="event", candidate_name="E1",
            http_status=200, content_hash="e" * 64, raw_content="",
        )
        SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/Done",
            entity_type="wrestler", candidate_name="Done",
            http_status=200, content_hash="d" * 64, raw_content="",
            used_at=timezone.now(),
        )

        data = self._get()
        self.assertEqual(data["queue"]["total"], 3)
        self.assertEqual(data["queue"]["by_entity_type"], {"wrestler": 2, "event": 1})

    def test_today_counts_recent_only(self):
        # Fetch from 48h ago — excluded. Fresh fetch — included.
        old = SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/Old",
            entity_type="wrestler", candidate_name="Old",
            http_status=200, content_hash="o" * 64, raw_content="",
        )
        SourceFetch.objects.filter(id=old.id).update(
            fetched_at=timezone.now() - timedelta(hours=48),
        )
        SourceFetch.objects.create(
            source="wikipedia", url="https://en.wikipedia.org/wiki/New",
            entity_type="wrestler", candidate_name="New",
            http_status=200, content_hash="n" * 64, raw_content="",
        )

        data = self._get()
        self.assertEqual(data["today"]["fetches"], 1)

    def test_error_activity_counted(self):
        WrestleBotActivity.objects.create(
            action_type="error",
            entity_type="wrestler", entity_id=1,
            entity_name="X", source="wikipedia",
            success=False, error_message="boom",
        )
        data = self._get()
        self.assertEqual(data["today"]["errors"], 1)
