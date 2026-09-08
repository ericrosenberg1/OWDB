"""
Tests for the agent tool registry (`owdb_django.wrestlebot.agents.tools`).

Coverage:
    - Regression: `_t_generate_bio` (the "generate_bio" tool JR/Al call from
      the agentic tool-use loop) referenced `bio.attempts`, but GeneratedBio
      only defines `attempt_number` (see models.GeneratedBio). Every call
      that reached the final `_ok(...)` raised AttributeError, which
      `dispatch()` catches and turns into an `ok=False` error result — so
      the tool reported failure to the calling LLM on every single
      invocation, even when the bio was generated, verified, AND promoted
      live to Wrestler.about underneath it. No test exercised this path
      before (bio.py / tools.py are both ~0% covered), so nothing caught it.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler
from owdb_django.wrestlebot.agents.tools import JR_TOOLS, dispatch


class GenerateBioToolTests(TestCase):
    def setUp(self):
        self.wrestler = Wrestler.objects.create(name="Test Wrestler")

    @staticmethod
    def _available_client():
        client = mock.Mock()
        client.available = True
        return client

    @mock.patch("owdb_django.wrestlebot.pipeline.bio.generate_and_verify_with_retry")
    @mock.patch("owdb_django.wrestlebot.claude_client.ClaudeClient")
    def test_generate_bio_tool_succeeds_and_reports_attempt_number(
        self, mock_client_cls, mock_generate
    ):
        """A verified bio must come back ok=True with the real attempt_number,
        not crash with AttributeError on the old `bio.attempts` access."""
        mock_client_cls.return_value = self._available_client()
        mock_generate.return_value = SimpleNamespace(
            status="verified",
            text="A verified biography.",
            attempt_number=2,
        )

        result = dispatch(JR_TOOLS, "generate_bio", {"wrestler_id": self.wrestler.id})

        self.assertTrue(result.get("ok"), msg=result)
        self.assertNotIn("AttributeError", result.get("error", ""))
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(result["bio_status"], "verified")

        self.wrestler.refresh_from_db()
        self.assertEqual(self.wrestler.about, "A verified biography.")

    @mock.patch("owdb_django.wrestlebot.pipeline.bio.generate_and_verify_with_retry")
    @mock.patch("owdb_django.wrestlebot.claude_client.ClaudeClient")
    def test_generate_bio_tool_reports_rejected_without_promoting(
        self, mock_client_cls, mock_generate
    ):
        """A permanently-rejected bio still reports ok=True (the tool call
        itself succeeded) but must not overwrite Wrestler.about."""
        mock_client_cls.return_value = self._available_client()
        mock_generate.return_value = SimpleNamespace(
            status="permanently_rejected",
            text="An unverifiable draft.",
            attempt_number=3,
        )

        result = dispatch(JR_TOOLS, "generate_bio", {"wrestler_id": self.wrestler.id})

        self.assertTrue(result.get("ok"), msg=result)
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["bio_status"], "permanently_rejected")

        self.wrestler.refresh_from_db()
        self.assertFalse(self.wrestler.about, "about must stay unset when the bio is rejected")

    @mock.patch("owdb_django.wrestlebot.claude_client.ClaudeClient")
    def test_generate_bio_tool_missing_wrestler(self, mock_client_cls):
        mock_client_cls.return_value = self._available_client()

        result = dispatch(JR_TOOLS, "generate_bio", {"wrestler_id": 999999})

        self.assertFalse(result.get("ok"))
        self.assertIn("not found", result.get("error", ""))
