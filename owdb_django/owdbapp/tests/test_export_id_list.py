"""
Tests for the export_id_list management command — the bonus item from the
REST API v1 plan: a manually-invokable, TMDB-style ID-export dump.
Deliberately NOT wired to Celery Beat (see the command's own docstring);
these tests only exercise `call_command` directly.
"""

import gzip
import json
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase

from ..models import Promotion, Wrestler


class ExportIdListCommandTest(TestCase):
    def setUp(self):
        Wrestler.objects.create(name="Verified Wrestler", verification_state="verified")
        Wrestler.objects.create(name="Rejected Wrestler", verification_state="rejected")
        Promotion.objects.create(name="Test Promotion", verification_state="verified")

    def _read_export(self, directory, slug):
        matches = list(Path(directory).glob(f"{slug}_ids_*.json.gz"))
        self.assertEqual(len(matches), 1, f"expected exactly one {slug} export file in {directory}")
        with gzip.open(matches[0], "rt", encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]

    def test_export_writes_one_gzip_file_per_requested_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            call_command(
                "export_id_list", output_dir=tmp, entities=["wrestlers", "promotions"], verbosity=0
            )
            wrestler_rows = self._read_export(tmp, "wrestlers")
            promotion_rows = self._read_export(tmp, "promotions")

        promotion_names = {row["name"] for row in promotion_rows}
        self.assertEqual(promotion_names, {"Test Promotion"})
        wrestler_names = {row["name"] for row in wrestler_rows}
        self.assertIn("Verified Wrestler", wrestler_names)
        # Every row is {"id": ..., "name": ...} — an id list, not full records.
        self.assertEqual(set(wrestler_rows[0].keys()), {"id", "name"})

    def test_export_excludes_rejected_rows(self):
        """Same review gate as the website and the REST API: a `rejected`
        wrestler must not appear in the id export either."""
        with tempfile.TemporaryDirectory() as tmp:
            call_command("export_id_list", output_dir=tmp, entities=["wrestlers"], verbosity=0)
            rows = self._read_export(tmp, "wrestlers")

        names = {row["name"] for row in rows}
        self.assertNotIn("Rejected Wrestler", names)
        self.assertIn("Verified Wrestler", names)

    def test_default_run_exports_every_entity_type(self):
        with tempfile.TemporaryDirectory() as tmp:
            call_command("export_id_list", output_dir=tmp, verbosity=0)
            files = list(Path(tmp).glob("*.json.gz"))

        self.assertEqual(len(files), 11)
