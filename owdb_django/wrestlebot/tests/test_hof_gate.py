"""
Tests for the Hall-of-Fame discovery gate in fetch_wrestler_candidates.

Discovery from Wikipedia's HOF lists pulls in celebrity honorees alongside
real wrestlers — Drew Carey, Bob Uecker, Pete Rose, Donald Trump. Without
the gate we'd write Wrestler rows for those names with no provenance, and
Earl would spend cycles flagging them after the fact.

The gate runs `classify_html` against the fetched HTML before the
SourceFetch row is created with `entity_type='wrestler'`. Non-wrestler
pages get a row with `entity_type=None` + `extraction_outcome='persist_refused'`
so they don't enter the extract queue but also don't get refetched.
"""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.pipeline.fetch import fetch_wrestler_candidates
from owdb_django.wrestlebot.sources.base import FetchResult


# Minimal wrestler page: has the labels classify_html needs to score
# "wrestler" with confidence (Real name, Trained by, Ring name(s)).
_WRESTLER_HTML = """
<div class="mw-parser-output">
  <p>Joe Wrestler is an American professional wrestler.</p>
  <table class="infobox biography vcard">
    <tr><th>Birth name</th><td>Joseph Wrestler</td></tr>
    <tr><th>Born</th><td>January 1, 1980</td></tr>
    <tr><th>Ring name(s)</th><td>Joe Wrestler<br>The Wrestler</td></tr>
    <tr><th>Trained by</th><td>Some Trainer</td></tr>
    <tr><th>Debut</th><td>2000</td></tr>
  </table>
  <p>His career in professional wrestling started in 2000.</p>
</div>
"""

# Minimal celebrity (non-wrestler) page: baseball-player shaped infobox.
# classify_html should return None or non-"wrestler".
_BASEBALL_PLAYER_HTML = """
<div class="mw-parser-output">
  <p>Bob Honoree was an American baseball broadcaster.</p>
  <table class="infobox vcard">
    <tr><th>Born</th><td>January 1, 1934</td></tr>
    <tr><th>Position</th><td>Catcher</td></tr>
    <tr><th>Batted</th><td>Right</td></tr>
    <tr><th>Threw</th><td>Right</td></tr>
    <tr><th>MLB debut</th><td>April 1955</td></tr>
    <tr><th>Teams</th><td>Milwaukee Braves</td></tr>
  </table>
  <p>He was inducted into the WWE Hall of Fame in 2010 as a celebrity.</p>
</div>
"""


def _fake_fetch(name: str) -> FetchResult:
    """Return wrestler HTML for "Joe Wrestler", baseball HTML otherwise."""
    if name == "Joe Wrestler":
        html = _WRESTLER_HTML
    else:
        html = _BASEBALL_PLAYER_HTML
    return FetchResult(
        url=f"https://en.wikipedia.org/wiki/{name.replace(' ', '_')}",
        http_status=200,
        raw_content=html,
        source_id=name,
    )


class HOFGateTests(TestCase):
    def setUp(self):
        # Patch fetch_wrestler_by_name on the WikipediaAdapter so we don't
        # hit the real network.
        patcher = patch(
            "owdb_django.wrestlebot.sources.wikipedia.WikipediaAdapter.fetch_wrestler_by_name",
            side_effect=_fake_fetch,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_gate_off_persists_everything_as_wrestler(self):
        """
        Without `from_hof_discovery=True`, the legacy behavior persists
        every fetch with entity_type='wrestler' regardless of content.
        """
        fetches = fetch_wrestler_candidates(["Joe Wrestler", "Bob Honoree"])
        self.assertEqual(len(fetches), 2)
        for f in fetches:
            self.assertEqual(f.entity_type, "wrestler")
            self.assertIsNone(f.used_at, "ungated fetch should stay in queue")
            self.assertEqual(f.extraction_outcome, "")

    def test_gate_on_drops_non_wrestler_from_queue(self):
        """
        With `from_hof_discovery=True`, the baseball-player page is
        recorded with entity_type=None + persist_refused so it never
        enters the wrestler extract queue.
        """
        fetches = fetch_wrestler_candidates(
            ["Joe Wrestler", "Bob Honoree"], from_hof_discovery=True
        )
        self.assertEqual(len(fetches), 2)

        wrestler_fetch = next(f for f in fetches if f.candidate_name == "Joe Wrestler")
        self.assertEqual(wrestler_fetch.entity_type, "wrestler")
        self.assertIsNone(wrestler_fetch.used_at)
        self.assertEqual(wrestler_fetch.extraction_outcome, "")

        honoree_fetch = next(f for f in fetches if f.candidate_name == "Bob Honoree")
        self.assertIsNone(honoree_fetch.entity_type)
        self.assertIsNotNone(honoree_fetch.used_at)
        self.assertEqual(honoree_fetch.extraction_outcome, "persist_refused")
        # The raw HTML is still kept so a human (or a later, smarter
        # classifier) can review the rejection.
        self.assertEqual(honoree_fetch.raw_content, _BASEBALL_PLAYER_HTML)

    def test_gated_rejection_does_not_enter_extract_queue(self):
        """
        The extract queue selects on `used_at__isnull=True` and
        `entity_type='wrestler'`. Gated rejections must match neither.
        """
        fetch_wrestler_candidates(["Bob Honoree"], from_hof_discovery=True)
        queue = SourceFetch.objects.filter(entity_type="wrestler", used_at__isnull=True)
        self.assertEqual(queue.count(), 0)
