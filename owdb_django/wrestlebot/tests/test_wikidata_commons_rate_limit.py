"""
Tests confirming Wikidata and Wikimedia Commons calls are rate-limited.

Before this fix, `sources/wikidata.py` and `sources/commons.py` made raw
`urlopen()` calls with zero throttling of any kind — unlike every other
external-source adapter that talks directly to its API (musicbrainz,
discogs, brave_search, tavily_search, profightdb, wrestlingdb,
upcoming_events), which all route through the shared Redis-backed
`rate_limited()` bucket in `rate_limit.py`. Both modules are hit repeatedly
by the image-sweep cascade and cross-validation stage across potentially
many entities, so an unbounded loop here could hammer Wikimedia's API with
no ceiling at all.

These tests pin the fix: every outbound call from each module's single
HTTP choke point (`_http_get_json`) must go through `rate_limited()` under
that module's own key, with a real (not infinite) per-second ceiling.
"""

from __future__ import annotations

import json
from unittest import mock

from django.test import SimpleTestCase

from owdb_django.wrestlebot.sources import commons, wikidata


def _fake_response(payload: bytes):
    """A context-manager stand-in for urlopen()'s return value."""
    resp = mock.MagicMock()
    resp.read.return_value = payload
    resp.__enter__.return_value = resp
    resp.__exit__.return_value = False
    return resp


class WikidataRateLimitTests(SimpleTestCase):
    def test_http_get_json_is_rate_limited_under_the_wikidata_key(self):
        with (
            mock.patch.object(wikidata, "rate_limited") as mock_rl,
            mock.patch.object(wikidata, "urlopen", return_value=_fake_response(b'{"ok": true}')),
        ):
            result = wikidata._http_get_json(
                "https://www.wikidata.org/wiki/Special:EntityData/Q1.json"
            )

        self.assertEqual(result, {"ok": True})
        mock_rl.assert_called_once_with("wikidata", per_second=wikidata.RATE_LIMIT_PER_SEC)

    def test_rate_limit_constant_is_a_real_ceiling(self):
        # Not unlimited, not absurdly tight — see the comment above the
        # constant: WMF infra, deliberately more generous than Cagematch's
        # 500/day, but still bounded.
        self.assertGreater(wikidata.RATE_LIMIT_PER_SEC, 0)
        self.assertLessEqual(wikidata.RATE_LIMIT_PER_SEC, 5.0)

    def test_resolve_qid_also_goes_through_the_rate_limiter(self):
        """resolve_qid_for_wikipedia_title() shares the same choke point."""
        payload = {"query": {"pages": {"1": {"pageprops": {"wikibase_item": "Q123"}}}}}
        with (
            mock.patch.object(wikidata, "rate_limited") as mock_rl,
            mock.patch.object(
                wikidata,
                "urlopen",
                return_value=_fake_response(json.dumps(payload).encode()),
            ),
        ):
            qid = wikidata.resolve_qid_for_wikipedia_title("Bret Hart")

        self.assertEqual(qid, "Q123")
        mock_rl.assert_called_once_with("wikidata", per_second=wikidata.RATE_LIMIT_PER_SEC)


class CommonsRateLimitTests(SimpleTestCase):
    def test_http_get_json_is_rate_limited_under_the_commons_key(self):
        with (
            mock.patch.object(commons, "rate_limited") as mock_rl,
            mock.patch.object(commons, "urlopen", return_value=_fake_response(b'{"ok": true}')),
        ):
            result = commons._http_get_json("https://commons.wikimedia.org/w/api.php?action=query")

        self.assertEqual(result, {"ok": True})
        mock_rl.assert_called_once_with("commons", per_second=commons.RATE_LIMIT_PER_SEC)

    def test_rate_limit_constant_is_a_real_ceiling(self):
        self.assertGreater(commons.RATE_LIMIT_PER_SEC, 0)
        self.assertLessEqual(commons.RATE_LIMIT_PER_SEC, 5.0)

    def test_fetch_image_for_qid_reuses_the_same_choke_point(self):
        """
        Every network path in commons.py (fetch_image_for_qid,
        resolve_commons_category_for_qid, fetch_commons_category_files,
        fetch_wikipedia_body_image_filenames, fetch_image_metadata) must
        go through `_http_get_json` so they all inherit its rate limit —
        pin one representative call site so a future refactor that adds a
        direct `urlopen()` call bypassing it gets caught.
        """
        entity_payload = {
            "entities": {
                "Q1": {
                    "claims": {
                        "P18": [
                            {
                                "mainsnak": {
                                    "snaktype": "value",
                                    "datavalue": {"value": "Example.jpg"},
                                }
                            }
                        ]
                    }
                }
            }
        }
        with (
            mock.patch.object(commons, "rate_limited") as mock_rl,
            mock.patch.object(
                commons,
                "urlopen",
                return_value=_fake_response(json.dumps(entity_payload).encode()),
            ),
        ):
            result = commons.fetch_image_for_qid("Q1")

        self.assertIsNotNone(result)
        self.assertEqual(result["filename"], "Example.jpg")
        mock_rl.assert_called_once_with("commons", per_second=commons.RATE_LIMIT_PER_SEC)
