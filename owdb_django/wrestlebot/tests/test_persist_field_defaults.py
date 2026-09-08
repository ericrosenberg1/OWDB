"""
Regression tests: a non-blank Django model `default=` can poison the
persist-layer's "is this field empty" check, silently discarding a
genuinely-extracted value on every single ingest.

Both bugs share the same shape: `Model.objects.create(...)` applies the
field's `default=` the instant the row is constructed -- before the
persist function's field-write loop ever inspects it -- so
`current in (None, "", b"")` is never True and the real extracted value
is thrown away in favor of the model default, forever, with no way to
tell from the DB alone that anything went wrong.

    - Wrestler.roles defaults to "wrestler" (owdbapp/models.py). A
      multi-role extraction (e.g. "wrestler, commentator") from
      sources/wikipedia.py was always discarded by persist_wrestler
      (pipeline/persist.py), plus spammed a spurious source_drift
      WrestleBotActivity row every time ("wrestler" != "wrestler,
      commentator" always compares unequal).
    - Special.type defaults to "other" (owdbapp/models.py). A real
      classification (documentary/movie/tv_special/series) from
      extract_special() (sources/wikipedia.py) was always discarded by
      persist_special (pipeline/persist_show.py).
"""

from __future__ import annotations

from django.test import TestCase

from owdb_django.owdbapp.models import Special, Wrestler
from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.pipeline.persist import persist_wrestler
from owdb_django.wrestlebot.pipeline.persist_show import persist_special
from owdb_django.wrestlebot.sources.base import (
    FieldSnippet,
    SpecialFields,
    WrestlerFields,
)


def _make_fetch(source="wikipedia", candidate_name="Test Candidate"):
    return SourceFetch.objects.create(
        source=source,
        url="https://en.wikipedia.org/wiki/Test_Candidate",
        http_status=200,
        content_hash="deadbeef" * 8,
        candidate_name=candidate_name,
    )


class WrestlerRolesDefaultTests(TestCase):
    def test_multi_role_extraction_is_written_on_first_persist(self):
        fetch = _make_fetch(candidate_name="Multi Role Wrestler")
        fields = WrestlerFields(
            name=FieldSnippet(value="Multi Role Wrestler", snippet="infobox name"),
            roles=FieldSnippet(
                value="wrestler, commentator", snippet="Occupation(s): wrestler, commentator"
            ),
        )

        result = persist_wrestler("Multi Role Wrestler", fields, fetch)

        self.assertIsNotNone(result)
        self.assertIn("roles", result.fields_written)
        self.assertNotIn("roles", result.fields_skipped)

        wrestler = Wrestler.objects.get(id=result.wrestler_id)
        self.assertEqual(wrestler.roles, "wrestler, commentator")

    def test_pure_wrestler_role_never_produces_a_snippet(self):
        """Sanity check on the fix's safety argument: the extractor only
        ever sets fields.roles when it found MORE than just "wrestler",
        so a wrestler-only page yields no roles snippet, and the model
        default ("wrestler") is left alone -- correctly."""
        fetch = _make_fetch(candidate_name="Plain Wrestler")
        fields = WrestlerFields(
            name=FieldSnippet(value="Plain Wrestler", snippet="infobox name"),
            roles=None,
        )

        result = persist_wrestler("Plain Wrestler", fields, fetch)

        self.assertIsNotNone(result)
        self.assertNotIn("roles", result.fields_written)
        wrestler = Wrestler.objects.get(id=result.wrestler_id)
        self.assertEqual(wrestler.roles, "wrestler")

    def test_second_source_does_not_reset_an_already_written_role(self):
        """First-write-wins must still hold once a real value has landed."""
        fetch1 = _make_fetch(candidate_name="Multi Role Wrestler 2")
        fields1 = WrestlerFields(
            name=FieldSnippet(value="Multi Role Wrestler 2", snippet="infobox name"),
            roles=FieldSnippet(value="wrestler, referee", snippet="Occupation(s): wrestler, referee"),
        )
        result1 = persist_wrestler("Multi Role Wrestler 2", fields1, fetch1)
        self.assertIn("roles", result1.fields_written)

        fetch2 = _make_fetch(candidate_name="Multi Role Wrestler 2")
        fetch2.entity_id = result1.wrestler_id
        fetch2.entity_type = "wrestler"
        fields2 = WrestlerFields(
            roles=FieldSnippet(
                value="wrestler, announcer", snippet="Occupation(s): wrestler, announcer"
            ),
        )
        result2 = persist_wrestler("Multi Role Wrestler 2", fields2, fetch2)

        self.assertIn("roles", result2.fields_skipped)
        wrestler = Wrestler.objects.get(id=result1.wrestler_id)
        self.assertEqual(wrestler.roles, "wrestler, referee")


class SpecialTypeDefaultTests(TestCase):
    def test_documentary_classification_is_written_on_first_persist(self):
        fetch = _make_fetch(candidate_name="Some Wrestling Documentary")
        fields = SpecialFields(
            title=FieldSnippet(value="Some Wrestling Documentary", snippet="article title"),
            type=FieldSnippet(value="documentary", snippet="from first sentence"),
        )

        result = persist_special("Some Wrestling Documentary", fields, fetch)

        self.assertIsNotNone(result)
        self.assertIn("type", result.fields_written)
        special = Special.objects.get(id=result.special_id)
        self.assertEqual(special.type, "documentary")
