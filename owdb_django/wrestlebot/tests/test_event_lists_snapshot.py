"""
Snapshot parity tests for the schema-driven event-list + title-history
extractors.

Captured Wikipedia HTML fixtures live in `fixtures/wiki_*.html.gz`. Their
expected outputs were recorded with the legacy imperative extractors and
stored as `fixtures/expected_*.json`. When the extractors are reimplemented
on top of `TableExtractorSpec`, these tests guarantee the new output is
byte-identical with the old.

The fixtures also exercise the bug the framework was designed to prevent:
the PPV list contains continuation rows whose "Event" cell is really a
"City, State" string (the "Rosemont, Illinois" bug); the row_filter must
drop these.
"""

from __future__ import annotations

import gzip
import json
import os

from django.test import TestCase

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def _load_html(name: str) -> str:
    path = os.path.join(FIXTURE_DIR, name)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return f.read()


def _load_json(name: str):
    path = os.path.join(FIXTURE_DIR, name)
    with open(path) as f:
        return json.load(f)


class PPVExtractorSnapshotTests(TestCase):
    def setUp(self):
        self.html = _load_html("wiki_ppv_ecw.html.gz")
        self.expected = _load_json("expected_ppv_ecw.json")

    def test_matches_legacy_snapshot(self):
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_ppvs_from_html,
        )

        actual = [e.to_dict() for e in extract_ppvs_from_html(self.html, "ecw")]
        self.assertEqual(actual, self.expected)

    def test_row_filter_drops_location_continuation_rows(self):
        """
        Any extracted event's `name` field must not look like a bare
        "City, State" continuation row (e.g. 'Rosemont, Illinois').
        """
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_ppvs_from_html,
        )

        events = extract_ppvs_from_html(self.html, "ecw")
        for e in events:
            n = (e.name or "").strip()
            if "," in n and len(n) < 80:
                after = n.split(",")[-1].strip()
                # State / country suffix with no other tokens → continuation.
                # Use the same shape the framework's row_filter rejects.
                looks_like_state_suffix = (
                    after
                    and after[0].isupper()
                    and len(after) <= 30
                    and after.replace(" ", "").replace(".", "").isalpha()
                )
                self.assertFalse(
                    looks_like_state_suffix,
                    f"continuation row leaked through: {e!r}",
                )


class EpisodeExtractorSnapshotTests(TestCase):
    def setUp(self):
        self.html = _load_html("wiki_episodes_dynamite.html.gz")
        self.expected = _load_json("expected_episodes_dynamite.json")

    def test_matches_legacy_snapshot(self):
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_episodes_from_html,
        )

        actual = [e.to_dict() for e in extract_episodes_from_html(self.html, "dynamite")]
        self.assertEqual(actual, self.expected)

    def test_row_filter_drops_non_numbered_rows(self):
        """
        Rows whose first cell doesn't start with a digit must be dropped.
        The fixture's tables include some header/sub-section rows where
        the first cell is "Debut episode" or similar.
        """
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_episodes_from_html,
        )

        eps = extract_episodes_from_html(self.html, "dynamite")
        for ep in eps:
            self.assertIsInstance(
                ep.episode_number,
                int,
                f"row without numeric episode_number leaked through: {ep!r}",
            )


class EvidenceNonEmptyTests(TestCase):
    """
    Acceptance criterion: every extracted row carries a FieldSnippet with a
    non-empty `snippet` text. The accuracy contract (`enforce(...)`) needs
    a quotable evidence string per required field — without one, the bulk
    ingest writes provisional rows that never graduate to verified.
    """

    def _assert_every_snippet_populated(self, spec, html):
        from owdb_django.wrestlebot.sources._schema import extract_tables

        rows = extract_tables(html, spec)
        self.assertGreater(len(rows), 0)
        for inst, snippets in rows:
            for fname, snip in snippets.items():
                self.assertTrue(
                    snip.snippet,
                    f"empty snippet for {fname!r} on {inst!r}",
                )

    def test_ppv_snippets_populated(self):
        from owdb_django.wrestlebot.pipeline.event_lists import _ppv_spec

        self._assert_every_snippet_populated(
            _ppv_spec("ecw"),
            _load_html("wiki_ppv_ecw.html.gz"),
        )

    def test_episode_snippets_populated(self):
        from owdb_django.wrestlebot.pipeline.event_lists import _episode_spec

        self._assert_every_snippet_populated(
            _episode_spec("dynamite"),
            _load_html("wiki_episodes_dynamite.html.gz"),
        )

    def test_champion_snippets_populated(self):
        from owdb_django.wrestlebot.pipeline.title_history import _CHAMPION_SPEC

        self._assert_every_snippet_populated(
            _CHAMPION_SPEC,
            _load_html("wiki_title_ecw.html.gz"),
        )


class TitleHistoryExtractorSnapshotTests(TestCase):
    def setUp(self):
        self.html = _load_html("wiki_title_ecw.html.gz")
        self.expected = _load_json("expected_title_ecw.json")

    def test_matches_legacy_snapshot(self):
        from owdb_django.wrestlebot.pipeline.title_history import (
            extract_champions_from_html,
        )

        champs, raw_count = extract_champions_from_html(self.html)
        self.assertEqual(
            {"champions": champs, "raw_count_seen": raw_count},
            self.expected,
        )

    def test_row_filter_drops_header_subrows(self):
        """
        Champion rows must look like real reign rows (a number in the
        first cell, or a year somewhere). Pure-text section headers
        embedded in the table must be filtered out.
        """
        from owdb_django.wrestlebot.pipeline.title_history import (
            extract_champions_from_html,
        )

        champs, _ = extract_champions_from_html(self.html)
        # No champion entry should look like a championship or section name.
        for name in champs:
            self.assertNotIn("Championship", name)
            self.assertNotIn("Title", name)
            self.assertNotIn(":", name)


class ChampionLinkTargetTests(TestCase):
    """
    Champion cells with `<a href="/wiki/...">` anchors must be queued by
    their link target, not their display text — otherwise ring names that
    collide with Wikipedia disambig pages ("Mr. Perfect", "The Texas
    Tornado", "Rikishi") send the fetcher to the wrong article.

    See SourceFetch #310-323 — five ~25%-of-failures incidents that all
    traced to display-text queuing on the IC + US + WCW + ECW belt pages.
    """

    def setUp(self):
        self.html = _load_html("wiki_title_wwe_intercontinental.html.gz")
        self.expected = _load_json("expected_title_wwe_intercontinental.json")

    def test_matches_snapshot(self):
        from owdb_django.wrestlebot.pipeline.title_history import (
            extract_champions_from_html,
        )

        champs, raw_count = extract_champions_from_html(self.html)
        self.assertEqual(
            {"champions": champs, "raw_count_seen": raw_count},
            self.expected,
        )

    def test_disambig_ring_names_resolve_to_link_targets(self):
        """
        Every name in the bug report — "Mr. Perfect", "The Texas Tornado",
        "The Mountie", "The Godfather", "Rikishi" — must be replaced by
        its `/wiki/...` link target. Display-text queuing would land each
        on a disambig page and fail extraction.
        """
        from owdb_django.wrestlebot.pipeline.title_history import (
            extract_champions_from_html,
        )

        champs, _ = extract_champions_from_html(self.html)
        champ_set = set(champs)

        # Each pair: (display text we MUST NOT queue, link target we MUST queue).
        for display, link_target in [
            ("Mr. Perfect", "Curt Hennig"),
            ("The Texas Tornado", "Kerry Von Erich"),
            ("The Mountie", "Jacques Rougeau"),
            ("The Godfather", "The Godfather (wrestler)"),
            ("Rikishi", "Rikishi (wrestler)"),
        ]:
            self.assertNotIn(
                display,
                champ_set,
                f"display text {display!r} leaked through — would fetch disambig page",
            )
            self.assertIn(
                link_target,
                champ_set,
                f"link target {link_target!r} missing — anchor href was not followed",
            )

    def test_red_link_falls_back_to_display_text(self):
        """
        Red links (Wikipedia anchors with class="new") point at
        `?action=edit&redlink=1`, not a real article. The cleaner must
        ignore them and fall back to the display text.
        """
        from owdb_django.wrestlebot.sources._schema import extract_tables
        from owdb_django.wrestlebot.pipeline.title_history import _CHAMPION_SPEC

        red_link_html = """
        <table class="wikitable">
          <tr><th>No.</th><th>Champion</th><th>Date</th></tr>
          <tr>
            <td>1</td>
            <td><a href="/wiki/Some_Indy_Guy?action=edit&amp;redlink=1"
                   class="new">Some Indy Guy</a></td>
            <td>April 6, 2024</td>
          </tr>
        </table>
        """
        rows = extract_tables(red_link_html, _CHAMPION_SPEC)
        names = [r[0].name for r in rows]
        self.assertEqual(names, ["Some Indy Guy"])

    def test_namespace_link_falls_back_to_display_text(self):
        """
        Anchors pointing at Wikipedia namespaces (`/wiki/Category:...`,
        `/wiki/File:...`, etc.) are never wrestler articles. The cleaner
        must ignore them and fall back to display text.
        """
        from owdb_django.wrestlebot.sources._schema import extract_tables
        from owdb_django.wrestlebot.pipeline.title_history import _CHAMPION_SPEC

        ns_html = """
        <table class="wikitable">
          <tr><th>No.</th><th>Champion</th><th>Date</th></tr>
          <tr>
            <td>1</td>
            <td><a href="/wiki/Category:Wrestlers">Some Wrestler</a></td>
            <td>April 6, 2024</td>
          </tr>
        </table>
        """
        rows = extract_tables(ns_html, _CHAMPION_SPEC)
        self.assertEqual([r[0].name for r in rows], ["Some Wrestler"])

    def test_anchor_with_disambig_parens_preserved(self):
        """
        When a wrestler's Wikipedia article lives at a disambiguated
        title ("Rikishi (wrestler)", "The Godfather (wrestler)"), we
        queue the title verbatim — the parens are part of the article
        name and the fetch API handles them correctly.
        """
        from owdb_django.wrestlebot.sources._schema import extract_tables
        from owdb_django.wrestlebot.pipeline.title_history import _CHAMPION_SPEC

        html = """
        <table class="wikitable">
          <tr><th>No.</th><th>Champion</th><th>Date</th></tr>
          <tr>
            <td>1</td>
            <td><a href="/wiki/Rikishi_(wrestler)">Rikishi</a></td>
            <td>April 6, 2024</td>
          </tr>
        </table>
        """
        rows = extract_tables(html, _CHAMPION_SPEC)
        self.assertEqual([r[0].name for r in rows], ["Rikishi (wrestler)"])
