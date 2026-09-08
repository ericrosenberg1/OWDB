"""
Tests for the v1 REST API (owdb_django/owdbapp/api/, api_urls.py).

These use `proxied_client()` rather than a bare `Client()` — see
proxied_client.py / test_views.py for why (ROS-1210): under
APP_ENV=production a plain-HTTP request 301s before any view runs.
"""

from datetime import date

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse

from owdb_django.owdbapp.api.throttling import APIKeyRateThrottle
from owdb_django.owdbapp.models import (
    APIKey,
    Book,
    Event,
    Match,
    Podcast,
    Promotion,
    Special,
    Stable,
    Title,
    Venue,
    VideoGame,
    Wrestler,
)

from .proxied_client import proxied_client


class CatalogAPITest(TestCase):
    """List + detail for every v1 resource, gated and plain alike."""

    def setUp(self):
        self.client = proxied_client()
        self.promotion = Promotion.objects.create(
            name="Test Promotion", abbreviation="TP", verification_state="verified"
        )
        self.venue = Venue.objects.create(name="Test Arena", location="Test City")
        self.wrestler_a = Wrestler.objects.create(name="Wrestler A", verification_state="verified")
        self.wrestler_b = Wrestler.objects.create(name="Wrestler B", verification_state="verified")
        self.event = Event.objects.create(
            name="Test Event",
            promotion=self.promotion,
            venue=self.venue,
            date=date(2024, 1, 1),
            verification_state="verified",
        )
        self.title = Title.objects.create(
            name="Test Title", promotion=self.promotion, verification_state="verified"
        )
        self.match = Match.objects.create(
            event=self.event,
            match_text="Wrestler A vs Wrestler B",
            winner=self.wrestler_a,
            title=self.title,
            verification_state="verified",
        )
        self.match.wrestlers.set([self.wrestler_a, self.wrestler_b])
        self.stable = Stable.objects.create(
            name="Test Stable", promotion=self.promotion, verification_state="verified"
        )
        self.stable.members.set([self.wrestler_a, self.wrestler_b])
        self.book = Book.objects.create(title="Test Book", author="An Author")
        self.book.related_wrestlers.set([self.wrestler_a])
        self.videogame = VideoGame.objects.create(name="Test Game", release_year=2020)
        self.videogame.wrestlers.set([self.wrestler_a])
        self.podcast = Podcast.objects.create(name="Test Podcast")
        self.podcast.host_wrestlers.set([self.wrestler_b])
        self.special = Special.objects.create(title="Test Special", type="documentary")
        self.special.related_wrestlers.set([self.wrestler_a])

    # -- Wrestler -------------------------------------------------------

    def test_wrestler_list(self):
        response = self.client.get(reverse("api-wrestler-list"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        names = {row["name"] for row in data["results"]}
        self.assertEqual(names, {"Wrestler A", "Wrestler B"})

    def test_wrestler_detail(self):
        response = self.client.get(reverse("api-wrestler-detail", args=[self.wrestler_a.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["name"], "Wrestler A")
        self.assertEqual(body["slug"], self.wrestler_a.slug)
        self.assertIn("is_active", body)
        self.assertIn("verification_state", body)

    def test_wrestler_detail_404_for_unknown_id(self):
        response = self.client.get(reverse("api-wrestler-detail", args=[999999]))
        self.assertEqual(response.status_code, 404)

    # -- Promotion --------------------------------------------------------

    def test_promotion_list_and_detail(self):
        response = self.client.get(reverse("api-promotion-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-promotion-detail", args=[self.promotion.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["abbreviation"], "TP")

    # -- Venue --------------------------------------------------------------

    def test_venue_list_and_detail(self):
        response = self.client.get(reverse("api-venue-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-venue-detail", args=[self.venue.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Test Arena")

    # -- Event: nested promotion/venue --------------------------------------

    def test_event_detail_nests_promotion_and_venue(self):
        response = self.client.get(reverse("api-event-detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["promotion"]["name"], "Test Promotion")
        self.assertEqual(body["venue"]["name"], "Test Arena")

    # -- Title ----------------------------------------------------------

    def test_title_detail_nests_promotion(self):
        response = self.client.get(reverse("api-title-detail", args=[self.title.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["promotion"]["abbreviation"], "TP")
        self.assertIn("is_active", body)

    # -- Match: the "names, not just ids" case -------------------------------

    def test_match_detail_nests_wrestler_and_event_names(self):
        response = self.client.get(reverse("api-match-detail", args=[self.match.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["event"]["name"], "Test Event")
        self.assertEqual(body["winner"]["name"], "Wrestler A")
        self.assertEqual(body["title"]["name"], "Test Title")
        wrestler_names = {w["name"] for w in body["wrestlers"]}
        self.assertEqual(wrestler_names, {"Wrestler A", "Wrestler B"})
        # None of those are bare ids requiring a second round trip.
        self.assertIsInstance(body["winner"], dict)

    def test_match_list(self):
        response = self.client.get(reverse("api-match-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    # -- Stable: nested members ------------------------------------------

    def test_stable_detail_nests_members(self):
        response = self.client.get(reverse("api-stable-detail", args=[self.stable.pk]))
        self.assertEqual(response.status_code, 200)
        member_names = {m["name"] for m in response.json()["members"]}
        self.assertEqual(member_names, {"Wrestler A", "Wrestler B"})

    # -- Plain content: Book / VideoGame / Podcast / Special ----------------

    def test_book_list_and_detail(self):
        response = self.client.get(reverse("api-book-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-book-detail", args=[self.book.pk]))
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["title"], "Test Book")
        self.assertEqual([w["name"] for w in body["related_wrestlers"]], ["Wrestler A"])

    def test_videogame_list_and_detail(self):
        response = self.client.get(reverse("api-videogame-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-videogame-detail", args=[self.videogame.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Test Game")

    def test_podcast_list_and_detail(self):
        response = self.client.get(reverse("api-podcast-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-podcast-detail", args=[self.podcast.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Test Podcast")

    def test_special_list_and_detail(self):
        response = self.client.get(reverse("api-special-list"))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse("api-special-detail", args=[self.special.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Test Special")

    # -- Pagination -----------------------------------------------------

    def test_list_response_is_paginated(self):
        response = self.client.get(reverse("api-wrestler-list"))
        body = response.json()
        self.assertIn("count", body)
        self.assertIn("results", body)
        self.assertIn("next", body)
        self.assertIn("previous", body)


class ReviewGateAPITest(TestCase):
    """
    Every VerificationMixin resource must hide a `rejected` row through the
    API exactly like VerificationQuerySet.public() already hides it on the
    website (owdb_django/owdbapp/views.py) — absent from the list, 404 on
    direct detail access. One pair of assertions per gated resource.
    """

    def setUp(self):
        self.client = proxied_client()
        self.promotion = Promotion.objects.create(
            name="Safe Promotion", verification_state="verified"
        )
        self.rejected_promotion = Promotion.objects.create(
            name="Rejected Promotion", verification_state="rejected"
        )

    def test_rejected_promotion_hidden(self):
        list_response = self.client.get(reverse("api-promotion-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Promotion", names)
        detail_response = self.client.get(
            reverse("api-promotion-detail", args=[self.rejected_promotion.pk])
        )
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_wrestler_hidden(self):
        Wrestler.objects.create(name="Safe Wrestler", verification_state="verified")
        rejected = Wrestler.objects.create(name="Rejected Wrestler", verification_state="rejected")
        list_response = self.client.get(reverse("api-wrestler-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Wrestler", names)
        detail_response = self.client.get(reverse("api-wrestler-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_venue_hidden(self):
        Venue.objects.create(name="Safe Venue", verification_state="verified")
        rejected = Venue.objects.create(name="Rejected Venue", verification_state="rejected")
        list_response = self.client.get(reverse("api-venue-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Venue", names)
        detail_response = self.client.get(reverse("api-venue-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_title_hidden(self):
        Title.objects.create(
            name="Safe Title", promotion=self.promotion, verification_state="verified"
        )
        rejected = Title.objects.create(
            name="Rejected Title", promotion=self.promotion, verification_state="rejected"
        )
        list_response = self.client.get(reverse("api-title-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Title", names)
        detail_response = self.client.get(reverse("api-title-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_event_hidden(self):
        Event.objects.create(
            name="Safe Event",
            promotion=self.promotion,
            date=date(2024, 1, 1),
            verification_state="verified",
        )
        rejected = Event.objects.create(
            name="Rejected Event",
            promotion=self.promotion,
            date=date(2024, 1, 2),
            verification_state="rejected",
        )
        list_response = self.client.get(reverse("api-event-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Event", names)
        detail_response = self.client.get(reverse("api-event-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_match_hidden(self):
        event = Event.objects.create(
            name="Match Event",
            promotion=self.promotion,
            date=date(2024, 1, 3),
            verification_state="verified",
        )
        Match.objects.create(event=event, match_text="Safe Match", verification_state="verified")
        rejected = Match.objects.create(
            event=event, match_text="Rejected Match", verification_state="rejected"
        )
        list_response = self.client.get(reverse("api-match-list"))
        texts = {row["match_text"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Match", texts)
        detail_response = self.client.get(reverse("api-match-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)

    def test_rejected_stable_hidden(self):
        Stable.objects.create(name="Safe Stable", verification_state="verified")
        rejected = Stable.objects.create(name="Rejected Stable", verification_state="rejected")
        list_response = self.client.get(reverse("api-stable-list"))
        names = {row["name"] for row in list_response.json()["results"]}
        self.assertNotIn("Rejected Stable", names)
        detail_response = self.client.get(reverse("api-stable-detail", args=[rejected.pk]))
        self.assertEqual(detail_response.status_code, 404)


class ApiKeyAuthenticationTest(TestCase):
    """X-API-Key handling: missing (anonymous OK), invalid/inactive (401),
    valid (200 + usage bookkeeping updated)."""

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(username="keyowner", password="x")

    def test_missing_key_allows_anonymous_read(self):
        response = self.client.get(reverse("api-wrestler-list"))
        self.assertEqual(response.status_code, 200)

    def test_invalid_key_returns_401(self):
        response = self.client.get(
            reverse("api-wrestler-list"), HTTP_X_API_KEY="not-a-real-key-at-all"
        )
        self.assertEqual(response.status_code, 401)

    def test_inactive_key_returns_401(self):
        api_key = APIKey.objects.create(user=self.user, key=APIKey.generate_key(), is_active=False)
        response = self.client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=api_key.key)
        self.assertEqual(response.status_code, 401)

    def test_valid_key_authenticates_and_updates_usage(self):
        api_key = APIKey.objects.create(user=self.user, key=APIKey.generate_key())
        self.assertIsNone(api_key.last_used)
        self.assertEqual(api_key.requests_total, 0)

        response = self.client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=api_key.key)

        self.assertEqual(response.status_code, 200)
        api_key.refresh_from_db()
        self.assertIsNotNone(api_key.last_used)
        self.assertEqual(api_key.requests_total, 1)
        self.assertEqual(api_key.requests_today, 1)


class ApiThrottlingTest(TestCase):
    """
    Real per-tier enforcement, not just a settings-value assertion — DRF's
    cache-based throttles bind their cache key to the request identity
    (IP for anon, the APIKey row for a keyed request), so the fastest
    faithful way to prove the anon ceiling actually triggers is to make
    exactly that many requests and check the next one is refused. See
    https://www.django-rest-framework.org/api-guide/throttling/.
    """

    def setUp(self):
        self.client = proxied_client()
        # Each throttle scope's cache history is process-global (LocMemCache
        # in tests) and Django doesn't clear it between tests, so an
        # earlier test's anonymous GETs would otherwise count against this
        # one's budget.
        cache.clear()

    def test_anonymous_throttle_triggers_past_100_per_hour(self):
        url = reverse("api-wrestler-list")
        anon_limit = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"]
        self.assertEqual(anon_limit, "100/hour")
        for _ in range(100):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 429)

    def test_authenticated_key_gets_a_higher_ceiling_than_anonymous(self):
        """A valid (non-paid) key must not be capped at the 100/hour anon
        rate — prove it by clearing comfortably past that ceiling (150
        requests) on one key and confirming every one still succeeds.
        Going all the way to the real 1,000/hour boundary here would just
        make the suite slow without testing anything more; the paid tier's
        exact rate is covered directly in test_paid_tier_rate_is_10000_per_hour
        below instead of by another few-thousand-request loop."""
        user = User.objects.create_user(username="throttleuser", password="x")
        api_key = APIKey.objects.create(user=user, key=APIKey.generate_key())
        url = reverse("api-wrestler-list")
        for _ in range(150):
            response = self.client.get(url, HTTP_X_API_KEY=api_key.key)
            self.assertEqual(response.status_code, 200)

    def test_paid_tier_rate_is_10000_per_hour(self):
        """Direct check of APIKeyRateThrottle's rate resolution for a paid
        key. Exhausting a 10,000/hour ceiling with real HTTP requests in a
        test isn't practical; this calls the same allow_request() path
        allow_request() itself uses (resolve scope -> get_rate() ->
        parse_rate()) and checks what it resolved to."""
        user = User.objects.create_user(username="paidowner", password="x")
        paid_key = APIKey.objects.create(user=user, key=APIKey.generate_key(), is_paid=True)
        request = RequestFactory().get("/api/wrestlers/")
        request.auth = paid_key

        throttle = APIKeyRateThrottle()
        allowed = throttle.allow_request(request, view=None)

        self.assertTrue(allowed)
        self.assertEqual(throttle.rate, "10000/hour")
        self.assertEqual(throttle.num_requests, 10000)

    def test_default_throttle_rates_match_published_tiers(self):
        """README.md's Rate Limits table is the source of truth for these
        three numbers; this pins settings.py to it."""
        rates = settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
        self.assertEqual(rates["anon"], "100/hour")
        self.assertEqual(rates["user"], "1000/hour")
        self.assertEqual(rates["paid"], "10000/hour")
