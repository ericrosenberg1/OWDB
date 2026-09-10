"""
Snapshot parity tests for the schema-driven event-list + title-history
extractors.

Captured Wikipedia HTML fixtures live in `fixtures/wiki_*.html.gz`. Their
expected outputs are recorded in `fixtures/expected_*.json` and pin the
extractors' behaviour so a later refactor cannot quietly change what the
ingest writes.

The fixtures also exercise the bug the framework was designed to prevent:
the PPV list contains continuation rows whose "Event" cell is really a
"City, State" string (the "Rosemont, Illinois" bug); the row_filter must
drop these.

The expected files were first recorded off the legacy imperative
extractors, then re-recorded once on 2026-09-10 when `extract_tables()`
started expanding `rowspan` and `colspan` into a rectangular grid
(`_schema.expand_table_grid`). Every difference in that re-record was a
correction, never a loss:

  * ECW PPVs: 7 rows had been reading one column to the left of where they
    belonged, because the year cell above them was spanned down. They were
    landing main-event text in `name` ("Rhino vs. Kid Kash" as an event
    name) and a city in `venue_name`. Row count did not move, 119 either
    way.
  * AEW Dynamite: 69 episodes had the main-event text filed as the `city`
    and no venue at all, from the residency runs where Wikipedia spans one
    venue cell down over the whole run.
  * WWE Intercontinental title history: two genuine champions, Charles
    Wright and John Layfield, had been dropped outright. Nothing was
    removed.
  * ECW title history: identical before and after.

If a future change moves these files again, diff them and justify each
row the same way rather than re-recording on faith.
"""

from __future__ import annotations

import gzip
import json
import os

from django.test import SimpleTestCase, TestCase

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


class SpecialEpisodeExtractorTests(TestCase):
    """
    The "List of X special episodes" shape, which is all Wikipedia carries
    for WWE Raw and WWE SmackDown.

    Fixture captured live 2026-09-10 from "List of WWE Raw special
    episodes". Unlike the numbered lists, every row here has a real title
    and no episode number.
    """

    def setUp(self):
        self.html = _load_html("wiki_special_episodes_raw.html.gz")
        self.expected = _load_json("expected_special_episodes_raw.json")

    def test_matches_snapshot(self):
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_special_episodes_from_html,
        )

        actual = [e.to_dict() for e in extract_special_episodes_from_html(self.html, "raw")]
        self.assertEqual(actual, self.expected)

    def test_every_row_has_a_title_and_a_date(self):
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_special_episodes_from_html,
        )

        eps = extract_special_episodes_from_html(self.html, "raw")
        self.assertGreater(len(eps), 100)
        for ep in eps:
            self.assertTrue(ep.name.strip(), f"blank name on {ep!r}")
            self.assertIsNotNone(ep.air_date, f"no air date on {ep!r}")

    def test_year_comes_from_the_section_heading(self):
        """
        These tables print "January 11" with the year only in the heading
        above, so a row that loses its heading context silently lands in
        the wrong year.
        """
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_special_episodes_from_html,
        )

        eps = extract_special_episodes_from_html(self.html, "raw")
        premiere = [e for e in eps if e.name == "Monday Night Raw Premiere"]
        self.assertEqual(len(premiere), 1)
        self.assertEqual(premiere[0].air_date.isoformat(), "1993-01-11")

    def test_main_event_lands_in_notes_not_in_the_city(self):
        """The rowspan bug's signature: match text filed as a location."""
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_special_episodes_from_html,
        )

        for ep in extract_special_episodes_from_html(self.html, "raw"):
            self.assertNotIn(" vs. ", ep.city or "")
            self.assertNotIn(" vs. ", ep.venue_name or "")

    def test_placeholder_cells_never_become_venues(self):
        """
        These pages write "— N/a" for an unknown venue. Passed through, it
        mints a Venue literally named "— N/a".
        """
        from owdb_django.wrestlebot.pipeline.event_lists import (
            extract_special_episodes_from_html,
        )

        for ep in extract_special_episodes_from_html(self.html, "raw"):
            for value in (ep.venue_name, ep.city, ep.notes):
                self.assertNotIn("N/a", value or "")
                self.assertNotEqual((value or "").strip(), "—")

    def test_two_date_column_shape_is_skipped(self):
        """
        A `colspan="2"` "Dates" header over a Taping / Airing sub-row leaves
        two columns with identical header text, so nothing says which is the
        broadcast date. Those tables are excluded on purpose.
        """
        from bs4 import BeautifulSoup

        from owdb_django.wrestlebot.pipeline.event_lists import (
            _is_special_episode_table,
        )

        two_date = BeautifulSoup(
            """
            <table class="wikitable">
             <tr><th rowspan="2">#</th><th rowspan="2">Title</th>
                 <th colspan="2">Dates</th><th rowspan="2">Venue</th></tr>
             <tr><th>Taping</th><th>Airing</th></tr>
             <tr><td>1220</td><td>New Year's SmackDown</td>
                 <td>January 4</td><td>January 6</td><td>FedExForum</td></tr>
            </table>
            """,
            "lxml",
        ).find("table")
        self.assertFalse(_is_special_episode_table(two_date))

        one_date = BeautifulSoup(
            """
            <table class="wikitable">
             <tr><th>Date</th><th>Episode</th><th>Venue</th><th>Location</th>
                 <th>Final match</th><th>Notes</th></tr>
             <tr><td>January 11</td><td>Monday Night Raw Premiere</td>
                 <td>Manhattan Center</td><td>New York City, New York</td>
                 <td>The Undertaker vs. Damien Demento</td><td></td></tr>
            </table>
            """,
            "lxml",
        ).find("table")
        self.assertTrue(_is_special_episode_table(one_date))


class SpecialEpisodeNamingTests(SimpleTestCase):
    """`special_episode_name` decides whether a title needs the show prefixed."""

    def test_title_that_already_names_the_show_is_left_alone(self):
        from owdb_django.wrestlebot.pipeline.event_lists import special_episode_name

        self.assertEqual(
            special_episode_name("raw", "Monday Night Raw Premiere"),
            "Monday Night Raw Premiere",
        )
        self.assertEqual(
            special_episode_name("smackdown", "WrestleMania SmackDown"),
            "WrestleMania SmackDown",
        )

    def test_title_that_does_not_name_the_show_gets_it_prefixed(self):
        from owdb_django.wrestlebot.pipeline.event_lists import special_episode_name

        self.assertEqual(
            special_episode_name("raw", "Tribute to the Troops"),
            "WWE Raw: Tribute to the Troops",
        )
        self.assertEqual(
            special_episode_name("smackdown", "Brock Lesnar 20th Anniversary Show"),
            "WWE SmackDown: Brock Lesnar 20th Anniversary Show",
        )

    def test_punctuation_does_not_hide_the_show_name(self):
        """ "Smack-Down!" still names the show."""
        from owdb_django.wrestlebot.pipeline.event_lists import special_episode_name

        self.assertEqual(
            special_episode_name("smackdown", "New Year's Smack-Down!"),
            "New Year's Smack-Down!",
        )

    def test_blank_title_falls_back_to_the_show_name(self):
        from owdb_django.wrestlebot.pipeline.event_lists import special_episode_name

        self.assertEqual(special_episode_name("raw", "  "), "WWE Raw")
