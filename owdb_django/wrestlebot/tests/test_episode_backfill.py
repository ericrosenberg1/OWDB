"""
Persist-side tests for the multi-show episode backfill.

`ingest_episode_list()` is the one entry point for every show. It tries the
numbered episode list first and falls back to the named special-episode
list, then runs both shapes through the same persist, provenance and
accuracy-contract code.

Wikipedia is never called here. Each test feeds `_first_existing_page` a
small HTML string, so the assertions are about what lands in the database,
not about what Wikipedia happens to say today.
"""

from __future__ import annotations

from unittest import mock

from django.test import TestCase

from owdb_django.owdbapp.models import Event, Promotion, TVShow, Venue
from owdb_django.wrestlebot.pipeline import event_lists

_NUMBERED_HTML = """
<html><body>
<h2>2023</h2>
<table class="wikitable">
 <tr><th>No.</th><th>Date</th><th>Location</th><th>Venue</th><th>Main event</th></tr>
 <tr>
   <td>1</td><td>June 17, 2023</td>
   <td rowspan="2">Chicago, Illinois</td>
   <td rowspan="2">United Center</td>
   <td>CM Punk vs. Samoa Joe</td>
 </tr>
 <tr>
   <td>2</td><td>June 24, 2023</td>
   <td>Ricky Starks vs. Jay White</td>
 </tr>
</table>
</body></html>
"""

_SPECIAL_HTML = """
<html><body>
<h2>1993</h2>
<table class="wikitable">
 <tr><th>Date</th><th>Episode</th><th>Venue</th><th>Location</th>
     <th>Final match</th><th>Rating (millions)</th><th>Notes</th></tr>
 <tr>
   <td>January 11</td><td>Monday Night Raw Premiere</td>
   <td>Manhattan Center</td><td>New York City, New York</td>
   <td>The Undertaker vs. Damien Demento</td><td>2.5</td><td></td>
 </tr>
 <tr>
   <td>August 23</td><td>Tribute to the Troops</td>
   <td>— N/a</td><td>— N/a</td><td>— N/a</td><td>— N/a</td><td></td>
 </tr>
</table>
</body></html>
"""

_EMPTY_HTML = "<html><body><p>No episode tables here.</p></body></html>"


def _page(title, html):
    """Stand in for `_first_existing_page`, which would hit Wikipedia."""
    return lambda titles: (title, html) if titles else None


class NumberedListIngestTests(TestCase):
    def test_creates_the_show_its_promotion_and_its_episodes(self):
        with mock.patch.object(
            event_lists,
            "_first_existing_page",
            _page("List of AEW Collision episodes", _NUMBERED_HTML),
        ):
            stats = event_lists.ingest_episode_list("collision")

        self.assertEqual(stats["list_kind"], "numbered")
        self.assertEqual(stats["created"], 2)
        show = TVShow.objects.get(name="AEW Collision")
        self.assertEqual(show.promotion.name, "All Elite Wrestling")
        self.assertEqual(show.episodes.count(), 2)

    def test_a_brand_new_show_does_not_blow_up_on_the_non_null_promotion(self):
        """
        `TVShow.promotion` cannot be null. A bare `get_or_create(name=...)`
        raised IntegrityError for any show not already in the database,
        which was every show but the four that already had rows.
        """
        self.assertFalse(TVShow.objects.filter(name="NWA Powerrr").exists())
        with mock.patch.object(
            event_lists,
            "_first_existing_page",
            _page("List of NWA Powerrr episodes", _NUMBERED_HTML),
        ):
            stats = event_lists.ingest_episode_list("nwa_powerrr")

        self.assertEqual(stats["created"], 2)
        show = TVShow.objects.get(name="NWA Powerrr")
        self.assertEqual(show.promotion.name, "National Wrestling Alliance")

    def test_spanned_venue_reaches_every_episode_under_it(self):
        with mock.patch.object(
            event_lists,
            "_first_existing_page",
            _page("List of AEW Collision episodes", _NUMBERED_HTML),
        ):
            event_lists.ingest_episode_list("collision")

        venues = {e.venue.name for e in Event.objects.filter(event_type="tv_episode")}
        self.assertEqual(venues, {"United Center"})
        abouts = {e.about for e in Event.objects.filter(event_type="tv_episode")}
        self.assertEqual(abouts, {"CM Punk vs. Samoa Joe", "Ricky Starks vs. Jay White"})

    def test_generated_names_use_a_hyphen_not_an_em_dash(self):
        with mock.patch.object(
            event_lists,
            "_first_existing_page",
            _page("List of AEW Collision episodes", _NUMBERED_HTML),
        ):
            event_lists.ingest_episode_list("collision")

        for event in Event.objects.filter(event_type="tv_episode"):
            self.assertNotIn("—", event.name)
            self.assertRegex(event.name, r"^AEW Collision - \d{4}-\d{2}-\d{2}$")

    def test_rerunning_updates_in_place_instead_of_duplicating(self):
        patched = mock.patch.object(
            event_lists,
            "_first_existing_page",
            _page("List of AEW Collision episodes", _NUMBERED_HTML),
        )
        with patched:
            event_lists.ingest_episode_list("collision")
            second = event_lists.ingest_episode_list("collision")

        self.assertEqual(second["created"], 0)
        self.assertEqual(second["updated"], 2)
        self.assertEqual(Event.objects.filter(event_type="tv_episode").count(), 2)


class SpecialListIngestTests(TestCase):
    def test_falls_back_to_the_special_list_when_there_is_no_numbered_one(self):
        def fake(titles):
            if titles == event_lists.EPISODE_LIST_PAGES["raw"]:
                return None
            return ("List of WWE Raw special episodes", _SPECIAL_HTML)

        with mock.patch.object(event_lists, "_first_existing_page", fake):
            stats = event_lists.ingest_episode_list("raw")

        self.assertEqual(stats["list_kind"], "special")
        self.assertEqual(stats["created"], 2)
        show = TVShow.objects.get(name="WWE Raw")
        self.assertEqual(show.promotion.name, "WWE")
        self.assertEqual(
            sorted(show.episodes.values_list("name", flat=True)),
            ["Monday Night Raw Premiere", "WWE Raw: Tribute to the Troops"],
        )

    def test_a_numbered_list_that_parses_wins_over_the_special_list(self):
        """
        Ordering matters: a show that later gains a full numbered list on
        Wikipedia must start using it rather than staying on the thinner
        specials page.
        """
        calls = []

        def fake(titles):
            calls.append(titles)
            if titles == event_lists.EPISODE_LIST_PAGES["raw"]:
                return ("List of WWE Raw episodes", _NUMBERED_HTML)
            return ("List of WWE Raw special episodes", _SPECIAL_HTML)

        with mock.patch.object(event_lists, "_first_existing_page", fake):
            stats = event_lists.ingest_episode_list("raw")

        self.assertEqual(stats["list_kind"], "numbered")
        self.assertEqual(calls, [event_lists.EPISODE_LIST_PAGES["raw"]])

    def test_a_numbered_page_that_parses_to_nothing_falls_through(self):
        def fake(titles):
            if titles == event_lists.EPISODE_LIST_PAGES["raw"]:
                return ("List of WWE Raw episodes", _EMPTY_HTML)
            return ("List of WWE Raw special episodes", _SPECIAL_HTML)

        with mock.patch.object(event_lists, "_first_existing_page", fake):
            stats = event_lists.ingest_episode_list("raw")

        self.assertEqual(stats["list_kind"], "special")

    def test_placeholder_venue_cells_never_become_venue_rows(self):
        def fake(titles):
            if titles == event_lists.EPISODE_LIST_PAGES["raw"]:
                return None
            return ("List of WWE Raw special episodes", _SPECIAL_HTML)

        with mock.patch.object(event_lists, "_first_existing_page", fake):
            event_lists.ingest_episode_list("raw")

        self.assertEqual(
            sorted(Venue.objects.values_list("name", flat=True)),
            ["Manhattan Center"],
        )
        tribute = Event.objects.get(name="WWE Raw: Tribute to the Troops")
        self.assertIsNone(tribute.venue)

    def test_show_with_no_page_in_either_registry_reports_an_error(self):
        with mock.patch.object(event_lists, "_first_existing_page", lambda titles: None):
            stats = event_lists.ingest_episode_list("raw")

        self.assertIn("error", stats)
        self.assertEqual(Event.objects.count(), 0)

    def test_unknown_show_key_is_rejected(self):
        stats = event_lists.ingest_episode_list("not_a_show")
        self.assertIn("error", stats)


class ReviewGateTests(TestCase):
    """
    The backfill must not walk through the review gate. `enforce()` treats
    `rejected` as sticky, and the ingest has to respect the state it hands
    back rather than stamping `verified` on everything it writes.
    """

    def _ingest(self):
        def fake(titles):
            if titles == event_lists.EPISODE_LIST_PAGES["raw"]:
                return None
            return ("List of WWE Raw special episodes", _SPECIAL_HTML)

        with mock.patch.object(event_lists, "_first_existing_page", fake):
            return event_lists.ingest_episode_list("raw")

    def test_a_rejected_episode_stays_rejected_across_a_rerun(self):
        self._ingest()
        premiere = Event.objects.get(name="Monday Night Raw Premiere")
        premiere.verification_state = "rejected"
        premiere.save(update_fields=["verification_state"])

        self._ingest()

        premiere.refresh_from_db()
        self.assertEqual(premiere.verification_state, "rejected")

    def test_a_rejected_episode_is_hidden_from_the_public_queryset(self):
        self._ingest()
        premiere = Event.objects.get(name="Monday Night Raw Premiere")
        premiere.verification_state = "rejected"
        premiere.save(update_fields=["verification_state"])

        self._ingest()

        show = TVShow.objects.get(name="WWE Raw")
        public_names = set(show.episodes.public().values_list("name", flat=True))
        self.assertNotIn("Monday Night Raw Premiere", public_names)
        self.assertIn("WWE Raw: Tribute to the Troops", public_names)

    def test_state_comes_from_the_contract_not_from_a_hardcoded_value(self):
        self._ingest()
        states = set(Event.objects.values_list("verification_state", flat=True))
        self.assertTrue(states.issubset({"candidate", "provisional", "verified"}), states)


class ShowRegistryReachabilityTests(TestCase):
    def test_every_special_show_key_is_ingestible(self):
        for key in event_lists.SPECIAL_EPISODE_LIST_PAGES:
            self.assertIn(key, event_lists.SHOW_NAME_MAP, f"{key}: no display name")
            self.assertIn(key, event_lists._SHOW_TO_PROMOTION, f"{key}: no promotion")

    def test_promotion_lookup_creates_a_named_promotion_not_a_key(self):
        promo = event_lists._get_or_create_promotion("wwe")
        self.assertEqual(promo.name, "WWE")
        self.assertEqual(Promotion.objects.filter(name="WWE").count(), 1)
