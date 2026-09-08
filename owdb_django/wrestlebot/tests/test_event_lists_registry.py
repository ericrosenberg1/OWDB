"""
Well-formedness tests for wb_ingest_event_lists' promotion/show registries.

`PPV_LIST_PAGES` and `EPISODE_LIST_PAGES` (in `pipeline/event_lists.py`) are
hand-maintained dicts of Wikipedia article titles. This environment can't
hit live Wikipedia to re-verify every URL resolves on every test run (that
verification was done manually — via WebSearch + WebFetch against the live
site — when each entry below was added; see the comments above
`PPV_LIST_PAGES`), but we CAN pin the *shape* every entry must have so a
future edit can't quietly break the registry: every promotion/show key
needs its supporting name-map and promotion-link entries, every page-title
tuple is non-empty, and every title at least looks like a real Wikipedia
"List of ..." article rather than a typo'd fragment.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from owdb_django.wrestlebot.pipeline import event_lists


class PPVRegistryShapeTests(SimpleTestCase):
    def test_every_promotion_has_a_nonempty_tuple_of_page_titles(self):
        for key, titles in event_lists.PPV_LIST_PAGES.items():
            self.assertIsInstance(key, str)
            self.assertTrue(key, "promotion key must not be blank")
            self.assertIsInstance(titles, tuple, f"{key}: page titles must be a tuple")
            self.assertGreater(len(titles), 0, f"{key}: needs at least one candidate title")
            for t in titles:
                self.assertIsInstance(t, str, f"{key}: title {t!r} must be a string")
                self.assertTrue(t.strip(), f"{key}: blank page title")
                self.assertTrue(
                    t.lower().startswith("list of"),
                    f"{key}: title {t!r} doesn't look like a Wikipedia 'List of ...' article",
                )

    def test_every_promotion_key_has_a_display_name(self):
        for key in event_lists.PPV_LIST_PAGES:
            self.assertIn(
                key,
                event_lists.PROMOTION_NAME_MAP,
                f"{key}: missing PROMOTION_NAME_MAP entry",
            )
            self.assertTrue(event_lists.PROMOTION_NAME_MAP[key].strip())

    def test_expected_major_promotions_present(self):
        """
        Pins the autonomy-prep expansion: WWE/AEW/NJPW/TNA/ROH/WCW/ECW plus
        NWA/MLW/AAA all have real, verified Wikipedia list pages.
        """
        for key in ("wwe", "aew", "njpw", "tna", "roh", "wcw", "ecw", "nwa", "mlw", "aaa"):
            self.assertIn(key, event_lists.PPV_LIST_PAGES, f"expected promotion {key!r} registered")

    def test_cmll_deliberately_absent(self):
        """
        CMLL has no consolidated "List of CMLL ... events" (or equivalent)
        Wikipedia article — verified live 2026-09. Only per-year weekly-show
        articles and standalone named-show pages exist, neither of which fit
        this ingester's one-page-per-promotion shape. This test pins that
        omission as deliberate so a future contributor doesn't "fix" it by
        guessing a URL that 404s.
        """
        self.assertNotIn("cmll", event_lists.PPV_LIST_PAGES)


class EpisodeRegistryShapeTests(SimpleTestCase):
    def test_every_show_has_a_nonempty_tuple_of_page_titles(self):
        for key, titles in event_lists.EPISODE_LIST_PAGES.items():
            self.assertIsInstance(key, str)
            self.assertTrue(key, "show key must not be blank")
            self.assertIsInstance(titles, tuple, f"{key}: page titles must be a tuple")
            self.assertGreater(len(titles), 0, f"{key}: needs at least one candidate title")
            for t in titles:
                self.assertIsInstance(t, str, f"{key}: title {t!r} must be a string")
                self.assertTrue(t.strip(), f"{key}: blank page title")
                self.assertTrue(
                    t.lower().startswith("list of"),
                    f"{key}: title {t!r} doesn't look like a Wikipedia 'List of ...' article",
                )

    def test_every_show_key_maps_to_a_known_promotion(self):
        for key in event_lists.EPISODE_LIST_PAGES:
            self.assertIn(
                key,
                event_lists._SHOW_TO_PROMOTION,
                f"{key}: missing _SHOW_TO_PROMOTION entry",
            )
            promo_key = event_lists._SHOW_TO_PROMOTION[key]
            self.assertIn(
                promo_key,
                event_lists.PROMOTION_NAME_MAP,
                f"{key}: _SHOW_TO_PROMOTION points at unknown promotion {promo_key!r}",
            )

    def test_every_show_key_has_a_display_name(self):
        for key in event_lists.EPISODE_LIST_PAGES:
            self.assertIn(
                key,
                event_lists.SHOW_NAME_MAP,
                f"{key}: missing SHOW_NAME_MAP entry",
            )
            self.assertTrue(event_lists.SHOW_NAME_MAP[key].strip())

    def test_expected_shows_present(self):
        """
        Pins the autonomy-prep expansion: the pre-existing weekly shows plus
        NJPW Strong (the real "weekly NJPW World show" — "NJPW World" itself
        is the streaming platform, not a show with its own episode list) and
        NWA Powerrr, both verified live 2026-09.
        """
        for key in (
            "raw",
            "smackdown",
            "dynamite",
            "collision",
            "impact",
            "njpw_strong",
            "nwa_powerrr",
        ):
            self.assertIn(key, event_lists.EPISODE_LIST_PAGES, f"expected show {key!r} registered")
