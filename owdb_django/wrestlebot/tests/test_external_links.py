"""
Tests for pipeline/external_links.py.

Coverage:
    - extract_external_links finds cagematch.net / profightdb.com hrefs
      and takes the first hit per host.
    - is_cagematch_wrestler_url only accepts the id=2 (wrestler) route,
      not id=1 (event).
    - Regression: apply_external_links_to_wrestler wrote cagematch_url /
      profightdb_url directly onto the Wrestler with zero FieldProvenance
      -- the only field-write path in the whole persist layer that did
      this for genuinely-extracted content (as opposed to the
      intentionally-provenance-free "stamp the fetch URL" case used
      elsewhere for wikipedia_url). Now records provenance like every
      other extracted field, which required passing the SourceFetch
      itself (not just its raw_content) so there's something for the
      FieldProvenance row to point at.
"""

from __future__ import annotations

from django.test import TestCase

from owdb_django.owdbapp.models import Wrestler
from owdb_django.wrestlebot.models import FieldProvenance, SourceFetch
from owdb_django.wrestlebot.pipeline.external_links import (
    apply_external_links_to_wrestler,
    extract_external_links,
    is_cagematch_wrestler_url,
)

_HTML_WITH_LINKS = """
<html><body>
<h2>External links</h2>
<ul>
  <li><a href="https://www.cagematch.net/?id=2&nr=123&name=Test">Cagematch profile</a></li>
  <li><a href="https://www.profightdb.com/wrestlers/test-wrestler-456.html">ProFightDB profile</a></li>
</ul>
</body></html>
"""

_HTML_WITH_EVENT_LINK_ONLY = """
<html><body>
<a href="https://www.cagematch.net/?id=1&nr=999">Cagematch event page</a>
</body></html>
"""


class ExtractExternalLinksTests(TestCase):
    def test_finds_both_known_hosts(self):
        found = extract_external_links(_HTML_WITH_LINKS)
        self.assertEqual(
            found["cagematch_url"], "https://www.cagematch.net/?id=2&nr=123&name=Test"
        )
        self.assertEqual(
            found["profightdb_url"],
            "https://www.profightdb.com/wrestlers/test-wrestler-456.html",
        )

    def test_empty_html_returns_empty_dict(self):
        self.assertEqual(extract_external_links(""), {})
        self.assertEqual(extract_external_links(None), {})


class CagematchWrestlerUrlTests(TestCase):
    def test_id_2_is_a_wrestler_route(self):
        self.assertTrue(is_cagematch_wrestler_url("https://www.cagematch.net/?id=2&nr=123"))

    def test_id_1_is_an_event_route_not_a_wrestler(self):
        self.assertFalse(is_cagematch_wrestler_url("https://www.cagematch.net/?id=1&nr=999"))


class ApplyExternalLinksToWrestlerTests(TestCase):
    def _make_fetch(self, html):
        return SourceFetch.objects.create(
            source="wikipedia",
            url="https://en.wikipedia.org/wiki/Test_Wrestler",
            http_status=200,
            content_hash="abc123" * 10,
            raw_content=html,
        )

    def test_sets_fields_and_records_provenance(self):
        w = Wrestler.objects.create(name="Test Wrestler")
        fetch = self._make_fetch(_HTML_WITH_LINKS)

        changed = apply_external_links_to_wrestler(w, fetch)

        self.assertEqual(set(changed.keys()), {"cagematch_url", "profightdb_url"})
        w.refresh_from_db()
        self.assertEqual(w.cagematch_url, "https://www.cagematch.net/?id=2&nr=123&name=Test")
        self.assertEqual(
            w.profightdb_url, "https://www.profightdb.com/wrestlers/test-wrestler-456.html"
        )

        provenance_fields = set(
            FieldProvenance.objects.filter(
                entity_type="wrestler", entity_id=w.id
            ).values_list("field_name", flat=True)
        )
        self.assertEqual(
            provenance_fields,
            {"cagematch_url", "profightdb_url"},
            "every field this function writes must carry FieldProvenance, "
            "same as every other extracted field in the persist pipeline",
        )

    def test_does_not_overwrite_an_already_set_field(self):
        w = Wrestler.objects.create(
            name="Test Wrestler 2", cagematch_url="https://www.cagematch.net/?id=2&nr=1"
        )
        fetch = self._make_fetch(_HTML_WITH_LINKS)

        changed = apply_external_links_to_wrestler(w, fetch)

        self.assertNotIn("cagematch_url", changed)
        w.refresh_from_db()
        self.assertEqual(w.cagematch_url, "https://www.cagematch.net/?id=2&nr=1")

    def test_rejects_cagematch_event_route(self):
        w = Wrestler.objects.create(name="Test Wrestler 3")
        fetch = self._make_fetch(_HTML_WITH_EVENT_LINK_ONLY)

        changed = apply_external_links_to_wrestler(w, fetch)

        self.assertEqual(changed, {})
        w.refresh_from_db()
        self.assertFalse(w.cagematch_url)
