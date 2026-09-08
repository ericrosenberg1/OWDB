"""
Tests for the `wb_generate_bio --verify-only` cost-control regression.

Coverage:
    - Regression: `wb_generate_bio --verify-only` (no `--wrestler`) queried
      every GeneratedBio with status='pending' and called Claude (via
      verify_bio) once per row with NO limit applied -- the one path in the
      whole bio-generation surface that didn't cap its Claude-call count.
      Every other path (the default generate+verify loop, the non-wrestler
      branch, bots/jr.py, tasks.py, agents/tools.py's generate_bio tool)
      slices its queryset by --limit/limit before touching Claude. A batch
      of bios stuck at 'pending' (e.g. a prior run crashed between generate
      and verify) would otherwise trigger one uncapped Claude call per row.
"""

from __future__ import annotations

from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler
from owdb_django.wrestlebot.models import GeneratedBio


class VerifyOnlyBudgetTests(TestCase):
    def _make_pending_bio(self, i):
        w = Wrestler.objects.create(name=f"Wrestler {i}")
        return GeneratedBio.objects.create(
            entity_type="wrestler",
            entity_id=w.id,
            text=f"Draft bio {i}",
            model="claude-sonnet-4-6",
            status="pending",
        )

    @mock.patch("owdb_django.wrestlebot.management.commands.wb_generate_bio.verify_bio")
    @mock.patch("owdb_django.wrestlebot.management.commands.wb_generate_bio.ClaudeClient")
    def test_verify_only_without_wrestler_ids_is_capped_by_limit(
        self, mock_client_cls, mock_verify_bio
    ):
        client = mock.Mock()
        client.available = True
        client.credential = mock.Mock(source="ANTHROPIC_API_KEY", is_oauth=False)
        client.model = "claude-sonnet-4-6"
        mock_client_cls.return_value = client

        # verify_bio would call Claude for every row it's handed. Simulate
        # a transient/no-op outcome so we only need to count invocations.
        mock_verify_bio.return_value = None

        for i in range(15):
            self._make_pending_bio(i)
        self.assertEqual(GeneratedBio.objects.filter(status="pending").count(), 15)

        out = StringIO()
        call_command("wb_generate_bio", "--verify-only", "--limit", "4", stdout=out)

        self.assertEqual(
            mock_verify_bio.call_count,
            4,
            "verify_bio must be capped by --limit when no --wrestler ids are given, "
            "not called once per every pending row",
        )

    @mock.patch("owdb_django.wrestlebot.management.commands.wb_generate_bio.verify_bio")
    @mock.patch("owdb_django.wrestlebot.management.commands.wb_generate_bio.ClaudeClient")
    def test_verify_only_with_explicit_wrestler_ids_ignores_limit(
        self, mock_client_cls, mock_verify_bio
    ):
        """Explicit --wrestler ids are a deliberate, bounded request by
        construction -- they should all be processed regardless of --limit."""
        client = mock.Mock()
        client.available = True
        client.credential = mock.Mock(source="ANTHROPIC_API_KEY", is_oauth=False)
        client.model = "claude-sonnet-4-6"
        mock_client_cls.return_value = client
        mock_verify_bio.return_value = None

        bios = [self._make_pending_bio(i) for i in range(3)]
        wrestler_ids = [b.entity_id for b in bios]

        out = StringIO()
        args = ["wb_generate_bio", "--verify-only", "--limit", "1"]
        for wid in wrestler_ids:
            args += ["--wrestler", str(wid)]
        call_command(*args, stdout=out)

        self.assertEqual(mock_verify_bio.call_count, 3)
