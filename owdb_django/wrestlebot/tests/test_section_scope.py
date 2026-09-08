"""
Tests for section-aware EntityMention extraction.

The book / video-game linker logic needs to know which section of an
article a wrestler mention came from. A wrestler mentioned in the lede
of a video-game article is likely an exec or a cover star; a wrestler
mentioned in the `==Roster==` section IS the roster.
"""

from __future__ import annotations

from django.test import TestCase

from owdb_django.wrestlebot.models import EntityMention, SourceFetch
from owdb_django.wrestlebot.pipeline.mentions import (
    extract_mentions_from_lead,
    extract_mentions_with_sections,
    persist_mentions_for_entity,
)


# A minimal Wikipedia-shaped article body with a lede, an h2 section, and
# an h3 sub-section. Each section links to a different wrestler.
_ARTICLE_HTML = """
<div class="mw-parser-output">
  <p>
    <a href="/wiki/WWE_2K22">WWE 2K22</a> is a professional wrestling video
    game developed by Visual Concepts.
    Cover star: <a href="/wiki/Rey_Mysterio">Rey Mysterio</a>.
  </p>
  <h2><span class="mw-headline">Roster</span></h2>
  <p>
    Roster members include
    <a href="/wiki/Roman_Reigns">Roman Reigns</a>,
    <a href="/wiki/Becky_Lynch">Becky Lynch</a>,
    and <a href="/wiki/Drew_McIntyre">Drew McIntyre</a>.
  </p>
  <h2><span class="mw-headline">Development</span></h2>
  <p>
    The game was greenlit under
    <a href="/wiki/Vince_McMahon">Vince McMahon</a>'s tenure.
  </p>
</div>
"""


class ExtractWithSectionsTests(TestCase):
    def test_lede_mentions_have_null_section(self):
        out = extract_mentions_with_sections(_ARTICLE_HTML)
        lede_links = [m["wiki_link"] for m in out if m["section_label"] is None]
        self.assertIn("Rey Mysterio", lede_links)
        self.assertIn("WWE 2K22", lede_links)

    def test_section_label_is_lowercased(self):
        out = extract_mentions_with_sections(_ARTICLE_HTML)
        roster = [m for m in out if m["wiki_link"] == "Roman Reigns"]
        self.assertEqual(len(roster), 1)
        self.assertEqual(roster[0]["section_label"], "roster")

    def test_subsection_inherits_until_next_heading(self):
        out = extract_mentions_with_sections(_ARTICLE_HTML)
        dev = [m for m in out if m["wiki_link"] == "Vince McMahon"]
        self.assertEqual(len(dev), 1)
        self.assertEqual(dev[0]["section_label"], "development")

    def test_legacy_lead_extractor_still_returns_only_lede(self):
        """`extract_mentions_from_lead` must keep its prior contract."""
        out = extract_mentions_from_lead(_ARTICLE_HTML)
        links = [m["wiki_link"] for m in out]
        self.assertIn("Rey Mysterio", links)
        self.assertNotIn("Roman Reigns", links)  # was in ==Roster==
        self.assertNotIn("Vince McMahon", links)  # was in ==Development==


class PersistMentionsSectionAwareTests(TestCase):
    def setUp(self):
        self.fetch = SourceFetch.objects.create(
            source="wikipedia",
            url="https://en.wikipedia.org/wiki/WWE_2K22",
            entity_type="video_game",
            entity_id=42,
            candidate_name="WWE 2K22",
            http_status=200,
            content_hash="z" * 64,
            raw_content=_ARTICLE_HTML,
        )

    def test_section_aware_persists_section_labels(self):
        n = persist_mentions_for_entity(
            "video_game", 42, self.fetch, section_aware=True,
        )
        self.assertGreater(n, 0)
        rr = EntityMention.objects.get(source_fetch=self.fetch, wiki_link="Roman Reigns")
        self.assertEqual(rr.section_label, "roster")
        cover = EntityMention.objects.get(source_fetch=self.fetch, wiki_link="Rey Mysterio")
        self.assertIsNone(cover.section_label)

    def test_default_extraction_still_lede_only(self):
        n = persist_mentions_for_entity("video_game", 42, self.fetch)
        # Lede-only: Rey Mysterio + WWE 2K22 (self-link), no roster names.
        links = list(EntityMention.objects.filter(source_fetch=self.fetch).values_list(
            "wiki_link", flat=True
        ))
        self.assertIn("Rey Mysterio", links)
        self.assertNotIn("Roman Reigns", links)
