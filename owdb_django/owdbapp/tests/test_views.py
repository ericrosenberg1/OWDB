"""
Tests for OWDB views.

These use `proxied_client()` rather than a bare `Client()`. Under
APP_ENV=production a plain-HTTP test request is 301'd by SecurityMiddleware before
any view runs, so every assertion below would check the redirect instead of the
view — see proxied_client.py for the full explanation (ROS-1210).
"""

from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import (
    Wrestler,
    Promotion,
    Event,
    Venue,
    Match,
    Title,
    Stable,
    Book,
    ActionFigure,
    ThemeSong,
    TrainingSchool,
    TVShow,
    UserRating,
    UserProfile,
)
from ..views import RATING_ENTITY_DETAIL_URL_NAMES, RATING_ENTITY_MODELS
from .proxied_client import proxied_client


class PublicViewsTest(TestCase):
    """Tests for public-facing views."""

    def setUp(self):
        self.client = proxied_client()
        # Create some test data
        self.wrestler = Wrestler.objects.create(name="Test Wrestler", hometown="Test City")
        self.promotion = Promotion.objects.create(name="Test Promotion", abbreviation="TP")
        self.venue = Venue.objects.create(name="Test Arena", location="Test Location")
        self.event = Event.objects.create(
            name="Test Event",
            promotion=self.promotion,
            venue=self.venue,
            date=timezone.now().date(),
        )

    def test_homepage(self):
        """Test homepage loads correctly."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "OWDB")

    def test_wrestlers_list(self):
        """Test wrestlers list page."""
        response = self.client.get(reverse("wrestlers"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Wrestler")

    def test_wrestler_detail(self):
        """Test wrestler detail page."""
        response = self.client.get(reverse("wrestler_detail", args=[self.wrestler.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Wrestler")

    def test_wrestler_detail_by_slug(self):
        """Test wrestler detail page by slug."""
        response = self.client.get(reverse("wrestler_detail_slug", args=[self.wrestler.slug]))
        self.assertEqual(response.status_code, 200)

    def test_promotions_list(self):
        """Test promotions list page."""
        response = self.client.get(reverse("promotions"))
        self.assertEqual(response.status_code, 200)

    def test_events_list(self):
        """Test events list page."""
        response = self.client.get(reverse("events"))
        self.assertEqual(response.status_code, 200)

    def test_venues_list(self):
        """Test venues list page."""
        response = self.client.get(reverse("venues"))
        self.assertEqual(response.status_code, 200)

    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_about_page(self):
        """Test about page."""
        response = self.client.get(reverse("about"))
        self.assertEqual(response.status_code, 200)

    def test_privacy_page(self):
        """Test privacy page."""
        response = self.client.get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)

    def test_homepage_discloses_api_is_in_development(self):
        """Regression for the owdbapp bug-fix sweep, item 2: the homepage's
        API CTA used to read like a working API existed (no working /api/
        endpoint exists anywhere in urls.py)."""
        response = self.client.get(reverse("index"))
        self.assertContains(response, "in development")
        self.assertNotContains(response, "Get API Access")

    def test_about_page_discloses_api_is_in_development(self):
        """Same regression as above, for the about page's "Use the API" card."""
        response = self.client.get(reverse("about"))
        self.assertContains(response, "in development")
        self.assertNotContains(response, "Get API Access")


class SearchViewsTest(TestCase):
    """Tests for search functionality."""

    def setUp(self):
        self.client = proxied_client()
        Wrestler.objects.create(name="John Cena", hometown="West Newbury")
        Wrestler.objects.create(name="CM Punk", hometown="Chicago")
        Wrestler.objects.create(name="Daniel Bryan", hometown="Aberdeen")

    def test_search_wrestlers(self):
        """Test searching wrestlers by name."""
        response = self.client.get(reverse("wrestlers"), {"q": "John"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "John Cena")
        self.assertNotContains(response, "CM Punk")

    def test_search_wrestlers_by_hometown(self):
        """Test searching wrestlers by hometown."""
        response = self.client.get(reverse("wrestlers"), {"q": "Chicago"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CM Punk")

    def test_empty_search(self):
        """Test empty search returns all results."""
        response = self.client.get(reverse("wrestlers"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        # Should contain all wrestlers
        self.assertContains(response, "John Cena")
        self.assertContains(response, "CM Punk")

    def test_search_query_length_limit(self):
        """Test that very long search queries are truncated."""
        long_query = "a" * 500
        response = self.client.get(reverse("wrestlers"), {"q": long_query})
        # Should not error
        self.assertEqual(response.status_code, 200)


class AuthenticationViewsTest(TestCase):
    """Tests for authentication views."""

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        UserProfile.objects.create(user=self.user, email_verified=True, can_contribute=True)

    def test_login_page_loads(self):
        """Test login page loads."""
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_signup_page_loads(self):
        """Test signup page loads."""
        response = self.client.get(reverse("signup"))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        """Test successful login."""
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "testpassword123"}
        )
        self.assertRedirects(response, reverse("index"))

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        response = self.client.post(
            reverse("login"), {"username": "testuser", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username")

    def test_logout_requires_post(self):
        """Test that logout requires POST method."""
        self.client.login(username="testuser", password="testpassword123")
        # GET should fail
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)

    def test_logout_with_post(self):
        """Test logout with POST method."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("index"))

    def test_authenticated_user_redirect_from_login(self):
        """Test that authenticated users are redirected from login page."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("login"))
        self.assertRedirects(response, reverse("index"))


class RateLimitingTest(TestCase):
    """Tests for rate limiting on auth views."""

    def setUp(self):
        self.client = proxied_client()

    def test_signup_rate_limiting(self):
        """Test that signup is rate limited when the counter is at the limit."""
        from django.core.cache import cache

        # Pre-set the cache to simulate 5 previous attempts from the test IP
        # (avoids flakiness from live request accumulation in test env)
        cache.set("rate_limit:signup:127.0.0.1", 5, timeout=600)

        response = self.client.post(
            reverse("signup"),
            {
                "username": "testuser_limited",
                "email": "limited@example.com",
                "password1": "testpassword123",
                "password2": "testpassword123",
            },
        )

        self.assertContains(response, "Too many signup attempts")

    def test_login_rate_limiting(self):
        """Test that login is rate limited."""
        # Make 11 login attempts (limit is 10)
        for i in range(11):
            response = self.client.post(
                reverse("login"), {"username": "nonexistent", "password": "wrongpassword"}
            )

        # 11th attempt should show rate limit message
        self.assertContains(response, "Too many login attempts")


class ReviewGateViewsTest(TestCase):
    """
    Proves the review gate at the HTTP layer: a rejected entity is absent
    from its list view and 404s on its own detail page, while candidate
    and provisional entities stay fully visible — the regression check
    that would have caught a "hide anything not verified" allowlist
    mistake instead of the intended "hide only rejected" blocklist.
    """

    def setUp(self):
        self.client = proxied_client()
        self.rejected_promotion = Promotion.objects.create(
            name="Rejected Test Promotion", verification_state="rejected"
        )
        self.candidate_wrestler = Wrestler.objects.create(
            name="Candidate Test Wrestler", verification_state="candidate"
        )
        self.provisional_wrestler = Wrestler.objects.create(
            name="Provisional Test Wrestler", verification_state="provisional"
        )
        self.rejected_wrestler = Wrestler.objects.create(
            name="Rejected Test Wrestler", verification_state="rejected"
        )

    def test_rejected_promotion_absent_from_list(self):
        response = self.client.get(reverse("promotions"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Rejected Test Promotion")

    def test_rejected_promotion_detail_404s(self):
        response = self.client.get(reverse("promotion_detail", args=[self.rejected_promotion.pk]))
        self.assertEqual(response.status_code, 404)

    def test_rejected_wrestler_absent_from_list(self):
        response = self.client.get(reverse("wrestlers"))
        self.assertNotContains(response, "Rejected Test Wrestler")

    def test_rejected_wrestler_detail_404s(self):
        response = self.client.get(reverse("wrestler_detail", args=[self.rejected_wrestler.pk]))
        self.assertEqual(response.status_code, 404)

    def test_candidate_wrestler_still_visible_in_list_and_detail(self):
        """Regression test: `.public()` must not act like a `verified`-only allowlist."""
        list_response = self.client.get(reverse("wrestlers"))
        self.assertContains(list_response, "Candidate Test Wrestler")
        detail_response = self.client.get(
            reverse("wrestler_detail", args=[self.candidate_wrestler.pk])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Candidate Test Wrestler")

    def test_provisional_wrestler_still_visible_in_list_and_detail(self):
        list_response = self.client.get(reverse("wrestlers"))
        self.assertContains(list_response, "Provisional Test Wrestler")
        detail_response = self.client.get(
            reverse("wrestler_detail", args=[self.provisional_wrestler.pk])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Provisional Test Wrestler")

    def test_candidate_entity_shows_unverified_badge(self):
        response = self.client.get(reverse("wrestler_detail", args=[self.candidate_wrestler.pk]))
        self.assertContains(response, "Unverified")

    def test_provisional_entity_shows_provisional_badge(self):
        response = self.client.get(reverse("wrestler_detail", args=[self.provisional_wrestler.pk]))
        self.assertContains(response, "Provisional")

    def test_verified_entity_has_no_review_gate_badge(self):
        verified = Wrestler.objects.create(
            name="Verified Test Wrestler", verification_state="verified"
        )
        response = self.client.get(reverse("wrestler_detail", args=[verified.pk]))
        self.assertNotContains(response, "Unverified")
        self.assertNotContains(response, "Provisional")


class ReviewGateRelationalLeakViewTest(TestCase):
    """A rejected Match must not leak through an Event's own detail page."""

    def setUp(self):
        self.client = proxied_client()
        self.promotion = Promotion.objects.create(name="Leak View Promotion")
        self.event = Event.objects.create(
            name="Leak View Event", promotion=self.promotion, date=timezone.now().date()
        )
        Match.objects.create(
            event=self.event, match_text="Rejected Leak Match", verification_state="rejected"
        )
        Match.objects.create(
            event=self.event, match_text="Good Leak Match", verification_state="verified"
        )

    def test_rejected_match_not_shown_on_event_detail(self):
        response = self.client.get(reverse("event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Rejected Leak Match")
        self.assertContains(response, "Good Leak Match")


class ReviewGateEventLeakViewTest(TestCase):
    """
    A rejected Event must not leak through the pages of the entities it is
    linked to (promotion, venue, wrestler, title), their counts, their
    Linked From sections, the events list, or the homepage, while a
    provisional Event stays visible in every one of those places.

    Both events sit at the same venue and promotion, and each has one
    verified match for the same title won by the same wrestler, so the
    only thing separating them is the event's own verification_state.
    """

    def setUp(self):
        self.client = proxied_client()
        self.promotion = Promotion.objects.create(name="Gate Test Promotion")
        self.venue = Venue.objects.create(name="Gate Test Arena")
        self.wrestler = Wrestler.objects.create(name="Gate Test Wrestler")
        self.opponent = Wrestler.objects.create(name="Gate Test Opponent")
        self.title = Title.objects.create(name="Gate Test Championship", promotion=self.promotion)
        self.rejected_event = Event.objects.create(
            name="Rejected Gate Event",
            promotion=self.promotion,
            venue=self.venue,
            date=date(2024, 3, 1),
            attendance=5000,
            verification_state="rejected",
        )
        self.provisional_event = Event.objects.create(
            name="Provisional Gate Event",
            promotion=self.promotion,
            venue=self.venue,
            date=date(2024, 3, 2),
            attendance=3000,
            verification_state="provisional",
        )
        for event in (self.rejected_event, self.provisional_event):
            match = Match.objects.create(
                event=event,
                match_text="Gate test match",
                title=self.title,
                winner=self.wrestler,
                verification_state="verified",
            )
            match.wrestlers.add(self.wrestler, self.opponent)

    def assert_only_provisional_event(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Provisional Gate Event")
        self.assertNotContains(response, "Rejected Gate Event")
        # The slug is what a link would carry, so check it too.
        self.assertNotContains(response, self.rejected_event.slug)

    def test_promotion_page_hides_rejected_event_everywhere(self):
        response = self.client.get(reverse("promotion_detail", args=[self.promotion.pk]))
        self.assert_only_provisional_event(response)
        self.assertEqual(response.context["stats"]["total_events"], 1)
        self.assertEqual(sum(row["count"] for row in response.context["timeline"]), 1)
        self.assertEqual([e.pk for e in response.context["events"]], [self.provisional_event.pk])

    def test_venue_page_hides_rejected_event_everywhere(self):
        response = self.client.get(reverse("venue_detail", args=[self.venue.pk]))
        self.assert_only_provisional_event(response)
        self.assertEqual(response.context["events"].paginator.count, 1)
        self.assertEqual(response.context["stats"]["total_events"], 1)
        self.assertEqual(response.context["stats"]["total_attendance"], 3000)

    def test_wrestler_page_hides_rejected_event_everywhere(self):
        response = self.client.get(reverse("wrestler_detail", args=[self.wrestler.pk]))
        self.assert_only_provisional_event(response)
        self.assertEqual(response.context["meta_counts"]["events"], 1)
        self.assertEqual(response.context["meta_counts"]["matches"], 1)
        self.assertEqual(response.context["record"]["total"], 1)
        self.assertEqual(response.context["record"]["wins"], 1)
        self.assertEqual(
            [m.event_id for m in response.context["matches"]], [self.provisional_event.pk]
        )

    def test_title_page_hides_rejected_event_everywhere(self):
        response = self.client.get(reverse("title_detail", args=[self.title.pk]))
        self.assert_only_provisional_event(response)
        self.assertEqual(
            [m.event_id for m in response.context["title_matches"]], [self.provisional_event.pk]
        )
        self.assertEqual(
            [m.event_id for m in response.context["championship_history"]],
            [self.provisional_event.pk],
        )

    def test_events_list_hides_rejected_event(self):
        response = self.client.get(reverse("events"))
        self.assert_only_provisional_event(response)

    def test_homepage_hides_rejected_event_and_does_not_count_it(self):
        response = self.client.get(reverse("index"))
        self.assert_only_provisional_event(response)
        self.assertEqual(response.context["stats"]["events"], 1)
        self.assertEqual(response.context["stats"]["matches"], 1)

    def test_rejected_event_detail_still_404s(self):
        response = self.client.get(reverse("event_detail", args=[self.rejected_event.pk]))
        self.assertEqual(response.status_code, 404)


class AccountViewsTest(TestCase):
    """Tests for account management views."""

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        UserProfile.objects.create(user=self.user)

    def test_account_requires_login(self):
        """Test account page requires authentication."""
        response = self.client.get(reverse("account"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('account')}")

    def test_account_page_loads(self):
        """Test account page loads when logged in."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("account"))
        self.assertEqual(response.status_code, 200)

    def test_account_page_discloses_api_is_in_development(self):
        """Regression for the owdbapp bug-fix sweep, item 2: real users could
        generate/delete/toggle API keys here with no indication the API they
        are supposedly for has zero working endpoints anywhere in the app."""
        self.client.login(username="testuser", password="testpassword123")
        response = self.client.get(reverse("account"))
        self.assertContains(response, "in development")
        # The old copy showed a curl example against a real-looking endpoint
        # as though it worked today.
        self.assertNotContains(response, "X-API-Key")


# =============================================================================
# Part A: Action Figures / Theme Songs / Training Schools
#
# All three are TimeStampedModel, not VerificationMixin — a plain `verified`
# boolean (same shape as Book/VideoGame/Podcast/Special), no
# `verification_state`, no `.public()` review gate, no `rejected` state.
# That's a real finding, not an assumption: confirmed by reading models.py
# before writing these views. So there is no "rejected entity excluded" test
# to mirror here — instead, "unverified still visible" is the honest
# equivalent of ReviewGateViewsTest's candidate/provisional checks, proving
# `verified=False` (the common case; wrestlebot doesn't backfill it) isn't
# mistaken for a takedown state.
# =============================================================================


class ActionFigureViewsTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.figure = ActionFigure.objects.create(
            name="WWF Hasbro Wrestling Superstars", manufacturer="Hasbro"
        )

    def test_action_figures_list_renders(self):
        response = self.client.get(reverse("action_figures"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WWF Hasbro Wrestling Superstars")

    def test_action_figure_detail_renders(self):
        response = self.client.get(reverse("action_figure_detail", args=[self.figure.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "WWF Hasbro Wrestling Superstars")

    def test_action_figure_detail_by_slug(self):
        response = self.client.get(reverse("action_figure_detail_slug", args=[self.figure.slug]))
        self.assertEqual(response.status_code, 200)

    def test_unverified_action_figure_still_visible_in_list_and_detail(self):
        unverified = ActionFigure.objects.create(name="Unverified Figure Line")
        self.assertFalse(unverified.verified)
        list_response = self.client.get(reverse("action_figures"))
        self.assertContains(list_response, "Unverified Figure Line")
        detail_response = self.client.get(reverse("action_figure_detail", args=[unverified.pk]))
        self.assertEqual(detail_response.status_code, 200)


class ThemeSongViewsTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.song = ThemeSong.objects.create(title="Real American", artist="Rick Derringer")

    def test_theme_songs_list_renders(self):
        response = self.client.get(reverse("theme_songs"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real American")

    def test_theme_song_detail_renders(self):
        response = self.client.get(reverse("theme_song_detail", args=[self.song.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Real American")

    def test_theme_song_detail_by_slug(self):
        response = self.client.get(reverse("theme_song_detail_slug", args=[self.song.slug]))
        self.assertEqual(response.status_code, 200)

    def test_unverified_theme_song_still_visible_in_list_and_detail(self):
        unverified = ThemeSong.objects.create(title="Unverified Song")
        self.assertFalse(unverified.verified)
        list_response = self.client.get(reverse("theme_songs"))
        self.assertContains(list_response, "Unverified Song")
        detail_response = self.client.get(reverse("theme_song_detail", args=[unverified.pk]))
        self.assertEqual(detail_response.status_code, 200)


class TrainingSchoolViewsTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.school = TrainingSchool.objects.create(
            name="Hart Dungeon", location="Calgary, Alberta"
        )

    def test_training_schools_list_renders(self):
        response = self.client.get(reverse("training_schools"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hart Dungeon")

    def test_training_school_detail_renders(self):
        response = self.client.get(reverse("training_school_detail", args=[self.school.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hart Dungeon")

    def test_training_school_detail_by_slug(self):
        response = self.client.get(reverse("training_school_detail_slug", args=[self.school.slug]))
        self.assertEqual(response.status_code, 200)

    def test_unverified_training_school_still_visible_in_list_and_detail(self):
        unverified = TrainingSchool.objects.create(name="Unverified School")
        self.assertFalse(unverified.verified)
        list_response = self.client.get(reverse("training_schools"))
        self.assertContains(list_response, "Unverified School")
        detail_response = self.client.get(reverse("training_school_detail", args=[unverified.pk]))
        self.assertEqual(detail_response.status_code, 200)


class NewEntityNavTest(TestCase):
    """The three new list pages are reachable from the site nav, not just by
    direct URL — otherwise wrestlebot's extracted rows would still be
    effectively invisible to a visitor who doesn't already know the URL."""

    def setUp(self):
        self.client = proxied_client()

    def test_homepage_nav_links_to_new_entity_types(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, reverse("action_figures"))
        self.assertContains(response, reverse("theme_songs"))
        self.assertContains(response, reverse("training_schools"))


# =============================================================================
# TV Shows: the first public pages for TVShow.
#
# Unlike the three Part-A entity types above, TVShow carries
# VerificationMixin, so it has the four-state review gate. These mirror
# ThemeSongViewsTest for the basic list/detail/slug coverage, then
# ReviewGateViewsTest for the gate itself (rejected hidden, candidate and
# provisional visible with a badge), then ReviewGateRelationalLeakViewTest
# for episodes, which are gated Event rows linked through Event.tv_show.
# =============================================================================


class TVShowViewsTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.promotion = Promotion.objects.create(name="Show Promotion", abbreviation="SP")
        self.show = TVShow.objects.create(
            name="Monday Night Raw",
            promotion=self.promotion,
            network="USA Network",
            verification_state="verified",
        )

    def _episode(self, name, **overrides):
        fields = {
            "name": name,
            "promotion": self.promotion,
            "tv_show": self.show,
            "date": timezone.now().date(),
        }
        fields.update(overrides)
        return Event.objects.create(**fields)

    def test_tv_shows_list_renders(self):
        response = self.client.get(reverse("tv_shows"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday Night Raw")
        self.assertContains(response, reverse("tv_show_detail", args=[self.show.pk]))

    def test_tv_shows_list_searches_by_name_network_and_promotion(self):
        other_promotion = Promotion.objects.create(name="Other Promotion")
        TVShow.objects.create(name="Dynamite", promotion=other_promotion, network="TBS")
        for query in ("Raw", "USA Network", "Show Promotion"):
            response = self.client.get(reverse("tv_shows"), {"q": query})
            self.assertContains(response, "Monday Night Raw", msg_prefix=query)
            self.assertNotContains(response, "Dynamite", msg_prefix=query)

    def test_tv_show_detail_renders(self):
        response = self.client.get(reverse("tv_show_detail", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday Night Raw")
        self.assertContains(response, "USA Network")
        self.assertContains(response, reverse("promotion_detail", args=[self.promotion.pk]))

    def test_tv_show_detail_by_slug(self):
        response = self.client.get(reverse("tv_show_detail_slug", args=[self.show.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday Night Raw")

    def test_candidate_and_provisional_shows_still_visible(self):
        """`.public()` is a rejected-only blocklist, not a verified allowlist."""
        candidate = TVShow.objects.create(
            name="Candidate Show", promotion=self.promotion, verification_state="candidate"
        )
        provisional = TVShow.objects.create(
            name="Provisional Show", promotion=self.promotion, verification_state="provisional"
        )
        list_response = self.client.get(reverse("tv_shows"))
        self.assertContains(list_response, "Candidate Show")
        self.assertContains(list_response, "Provisional Show")
        for show in (candidate, provisional):
            detail_response = self.client.get(reverse("tv_show_detail", args=[show.pk]))
            self.assertEqual(detail_response.status_code, 200, show.name)
            self.assertContains(detail_response, show.name)

    def test_candidate_show_wears_unverified_badge(self):
        candidate = TVShow.objects.create(
            name="Candidate Show", promotion=self.promotion, verification_state="candidate"
        )
        response = self.client.get(reverse("tv_show_detail", args=[candidate.pk]))
        self.assertContains(response, "Unverified")

    def test_verified_show_has_no_review_gate_badge(self):
        response = self.client.get(reverse("tv_show_detail", args=[self.show.pk]))
        self.assertNotContains(response, "Unverified")
        self.assertNotContains(response, "Provisional")

    def test_rejected_show_absent_from_list_and_404s_on_detail(self):
        rejected = TVShow.objects.create(
            name="Rejected Show", promotion=self.promotion, verification_state="rejected"
        )
        list_response = self.client.get(reverse("tv_shows"))
        self.assertNotContains(list_response, "Rejected Show")
        by_pk = self.client.get(reverse("tv_show_detail", args=[rejected.pk]))
        self.assertEqual(by_pk.status_code, 404)
        by_slug = self.client.get(reverse("tv_show_detail_slug", args=[rejected.slug]))
        self.assertEqual(by_slug.status_code, 404)

    def test_episodes_listed_on_show_detail(self):
        self._episode("Raw Episode 1", episode_number=1)
        response = self.client.get(reverse("tv_show_detail", args=[self.show.pk]))
        self.assertContains(response, "Raw Episode 1")
        self.assertContains(response, "Episodes (1)")

    def test_rejected_episode_not_shown_on_show_detail(self):
        self._episode("Good Raw Episode", verification_state="verified")
        self._episode("Rejected Raw Episode", verification_state="rejected")
        response = self.client.get(reverse("tv_show_detail", args=[self.show.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Good Raw Episode")
        self.assertNotContains(response, "Rejected Raw Episode")

    def test_verification_stamp_finds_tv_show_source_fetches(self):
        """The wrestlebot writes SourceFetch.entity_type="tv_show", while the
        stamp used to look up a bare lowercased class name ("tvshow") and so
        could never find a show's sources. Regression for that."""
        from owdb_django.wrestlebot.models import SourceFetch

        SourceFetch.objects.create(
            source="wikipedia",
            url="https://en.wikipedia.org/wiki/WWE_Raw",
            entity_type="tv_show",
            entity_id=self.show.pk,
            candidate_name="Monday Night Raw",
            http_status=200,
            content_hash="rawhash",
            raw_content="<html/>",
        )
        response = self.client.get(reverse("tv_show_detail", args=[self.show.pk]))
        self.assertContains(response, "Verified from 1 source")

    def test_event_detail_links_to_its_tv_show(self):
        episode = self._episode("Raw Episode 1", episode_number=1)
        response = self.client.get(reverse("event_detail", args=[episode.pk]))
        self.assertContains(response, reverse("tv_show_detail", args=[self.show.pk]))

    def test_promotion_detail_lists_its_tv_shows_but_not_rejected_ones(self):
        TVShow.objects.create(
            name="Rejected Promo Show", promotion=self.promotion, verification_state="rejected"
        )
        response = self.client.get(reverse("promotion_detail", args=[self.promotion.pk]))
        self.assertContains(response, reverse("tv_show_detail", args=[self.show.pk]))
        self.assertNotContains(response, "Rejected Promo Show")

    def test_homepage_nav_links_to_tv_shows(self):
        response = self.client.get(reverse("index"))
        self.assertContains(response, reverse("tv_shows"))


# =============================================================================
# Part B, item 1: UserRating (favorite toggle + 1-10 rating)
#
# UserRating associates to an entity via a hand-rolled (entity_type,
# entity_id) pair — a CharField `choices` + a plain PositiveIntegerField PK —
# NOT Django's contenttypes GenericForeignKey. Confirmed by reading the
# field list on models.py before building anything on top of it.
# RATING_ENTITY_MODELS (views.py) maps each declared choice to its real
# model; the first test below pins that the two never drift apart.
# =============================================================================


class UserRatingEntityMapTest(TestCase):
    def test_rating_entity_models_matches_declared_choices(self):
        declared = {choice for choice, _label in UserRating.ENTITY_TYPE_CHOICES}
        self.assertEqual(set(RATING_ENTITY_MODELS.keys()), declared)

    def test_every_rateable_entity_type_links_to_a_detail_page(self):
        """Every entity type a user can favorite has a public detail page, so
        "My Favorites" can link each row. TVShow was the one gap (it had no
        routes at all) until it got public pages. Pins that the two maps
        never drift apart again and that every URL name still resolves."""
        self.assertEqual(set(RATING_ENTITY_DETAIL_URL_NAMES), set(RATING_ENTITY_MODELS))
        for entity_type, url_name in RATING_ENTITY_DETAIL_URL_NAMES.items():
            self.assertTrue(reverse(url_name, args=[1]), entity_type)


class RateEntityViewTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(username="rater", password="testpassword123")
        self.wrestler = Wrestler.objects.create(name="Rateable Wrestler")

    def test_toggle_favorite_requires_login(self):
        response = self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "wrestler",
                "entity_id": self.wrestler.pk,
                "action": "toggle_favorite",
                "next": reverse("wrestler_detail", args=[self.wrestler.pk]),
            },
        )
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('rate_entity')}")
        self.assertFalse(UserRating.objects.exists())

    def test_toggle_favorite_creates_then_removes(self):
        self.client.login(username="rater", password="testpassword123")
        detail_url = reverse("wrestler_detail", args=[self.wrestler.pk])
        post_data = {
            "entity_type": "wrestler",
            "entity_id": self.wrestler.pk,
            "action": "toggle_favorite",
            "next": detail_url,
        }
        response = self.client.post(reverse("rate_entity"), post_data)
        self.assertRedirects(response, detail_url)
        rating = UserRating.objects.get(
            user=self.user, entity_type="wrestler", entity_id=self.wrestler.pk
        )
        self.assertTrue(rating.is_favorite)

        self.client.post(reverse("rate_entity"), post_data)
        rating.refresh_from_db()
        self.assertFalse(rating.is_favorite)

    def test_rate_entity_sets_rating(self):
        self.client.login(username="rater", password="testpassword123")
        detail_url = reverse("wrestler_detail", args=[self.wrestler.pk])
        response = self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "wrestler",
                "entity_id": self.wrestler.pk,
                "action": "rate",
                "rating": "8",
                "next": detail_url,
            },
        )
        self.assertRedirects(response, detail_url)
        rating = UserRating.objects.get(
            user=self.user, entity_type="wrestler", entity_id=self.wrestler.pk
        )
        self.assertEqual(rating.rating, 8)

    def test_rate_entity_can_clear_rating(self):
        self.client.login(username="rater", password="testpassword123")
        UserRating.objects.create(
            user=self.user, entity_type="wrestler", entity_id=self.wrestler.pk, rating=5
        )
        detail_url = reverse("wrestler_detail", args=[self.wrestler.pk])
        self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "wrestler",
                "entity_id": self.wrestler.pk,
                "action": "rate",
                "rating": "",
                "next": detail_url,
            },
        )
        rating = UserRating.objects.get(
            user=self.user, entity_type="wrestler", entity_id=self.wrestler.pk
        )
        self.assertIsNone(rating.rating)

    def test_rate_entity_rejects_out_of_range_rating(self):
        self.client.login(username="rater", password="testpassword123")
        detail_url = reverse("wrestler_detail", args=[self.wrestler.pk])
        self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "wrestler",
                "entity_id": self.wrestler.pk,
                "action": "rate",
                "rating": "11",
                "next": detail_url,
            },
        )
        self.assertFalse(UserRating.objects.filter(rating=11).exists())

    def test_rate_entity_rejects_entity_type_not_in_declared_choices(self):
        """A type outside UserRating.ENTITY_TYPE_CHOICES must not be silently
        accepted. (`venue` used to be the example here: a gated entity that
        was missing from the choices. It is declared now, see the test below,
        so this uses a type that no model backs.)"""
        self.client.login(username="rater", password="testpassword123")
        venue = Venue.objects.create(name="Rateable Venue")
        self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "arena",
                "entity_id": venue.pk,
                "action": "toggle_favorite",
                "next": reverse("index"),
            },
        )
        self.assertFalse(UserRating.objects.exists())

    def test_venue_can_be_favorited(self):
        """Venue is gated and has a public detail page, and it was the one
        such entity a user could not favorite or rate. Regression for that."""
        self.client.login(username="rater", password="testpassword123")
        venue = Venue.objects.create(name="Rateable Venue")
        self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "venue",
                "entity_id": venue.pk,
                "action": "toggle_favorite",
                "next": reverse("venue_detail", args=[venue.pk]),
            },
        )
        row = UserRating.objects.get(entity_type="venue", entity_id=venue.pk)
        self.assertTrue(row.is_favorite)

    def test_tv_show_can_be_favorited(self):
        """TVShow is gated and, as of its public pages, the last rate-able
        entity type to get a detail page to post back to."""
        self.client.login(username="rater", password="testpassword123")
        promotion = Promotion.objects.create(name="Rateable Promotion")
        show = TVShow.objects.create(name="Rateable Show", promotion=promotion)
        self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "tv_show",
                "entity_id": show.pk,
                "action": "toggle_favorite",
                "next": reverse("tv_show_detail", args=[show.pk]),
            },
        )
        row = UserRating.objects.get(entity_type="tv_show", entity_id=show.pk)
        self.assertTrue(row.is_favorite)

    def test_rate_entity_404s_for_rejected_entity(self):
        rejected = Wrestler.objects.create(name="Rejected Rateable", verification_state="rejected")
        self.client.login(username="rater", password="testpassword123")
        response = self.client.post(
            reverse("rate_entity"),
            {
                "entity_type": "wrestler",
                "entity_id": rejected.pk,
                "action": "toggle_favorite",
                "next": reverse("index"),
            },
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(UserRating.objects.exists())

    def test_rating_widget_visible_only_when_logged_in(self):
        detail_url = reverse("wrestler_detail", args=[self.wrestler.pk])
        anon_response = self.client.get(detail_url)
        self.assertNotContains(anon_response, "Save Rating")

        self.client.login(username="rater", password="testpassword123")
        auth_response = self.client.get(detail_url)
        self.assertContains(auth_response, "Save Rating")


class RatingWidgetPresentOnDetailPagesTest(TestCase):
    """
    The rating widget is wired into 9 detail templates: the eight gated
    (VerificationMixin) entity types with a public page and a matching
    UserRating.ENTITY_TYPE_CHOICES entry (wrestler, promotion, event, match,
    title, stable, venue, TV show), plus ThemeSong, the one Part-A entity
    type ENTITY_TYPE_CHOICES already anticipated. Venue joined the choices in
    migration 0031 but its template was never given the widget, and TVShow
    had no public page at all. Both are covered now. This proves every
    template that should have it, does.
    """

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(username="widgetcheck", password="testpassword123")
        self.client.login(username="widgetcheck", password="testpassword123")

        self.promotion = Promotion.objects.create(name="Widget Promotion")
        self.venue = Venue.objects.create(name="Widget Venue")
        self.event = Event.objects.create(
            name="Widget Event",
            promotion=self.promotion,
            venue=self.venue,
            date=timezone.now().date(),
        )
        self.wrestler = Wrestler.objects.create(name="Widget Wrestler")
        self.match = Match.objects.create(event=self.event, match_text="Widget Match")
        self.title = Title.objects.create(name="Widget Title", promotion=self.promotion)
        self.stable = Stable.objects.create(name="Widget Stable")
        self.song = ThemeSong.objects.create(title="Widget Song")
        self.show = TVShow.objects.create(name="Widget Show", promotion=self.promotion)

    def test_widget_present_on_each_detail_page(self):
        urls = [
            reverse("wrestler_detail", args=[self.wrestler.pk]),
            reverse("promotion_detail", args=[self.promotion.pk]),
            reverse("event_detail", args=[self.event.pk]),
            reverse("match_detail", args=[self.match.pk]),
            reverse("title_detail", args=[self.title.pk]),
            reverse("stable_detail", args=[self.stable.pk]),
            reverse("venue_detail", args=[self.venue.pk]),
            reverse("tv_show_detail", args=[self.show.pk]),
            reverse("theme_song_detail", args=[self.song.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertContains(response, "Save Rating", msg_prefix=url)


class MyFavoritesViewTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(username="favuser", password="testpassword123")
        self.wrestler = Wrestler.objects.create(name="Favorited Wrestler")

    def test_requires_login(self):
        response = self.client.get(reverse("my_favorites"))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('my_favorites')}")

    def test_shows_favorited_entity(self):
        UserRating.objects.create(
            user=self.user, entity_type="wrestler", entity_id=self.wrestler.pk, is_favorite=True
        )
        self.client.login(username="favuser", password="testpassword123")
        response = self.client.get(reverse("my_favorites"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Favorited Wrestler")

    def test_excludes_non_favorited_rating(self):
        UserRating.objects.create(
            user=self.user,
            entity_type="wrestler",
            entity_id=self.wrestler.pk,
            rating=7,
            is_favorite=False,
        )
        self.client.login(username="favuser", password="testpassword123")
        response = self.client.get(reverse("my_favorites"))
        self.assertNotContains(response, "Favorited Wrestler")

    def test_nav_links_to_my_favorites_when_logged_in(self):
        self.client.login(username="favuser", password="testpassword123")
        response = self.client.get(reverse("index"))
        self.assertContains(response, reverse("my_favorites"))

    def test_favorited_tv_show_links_to_its_detail_page(self):
        """Regression: TVShow had no public route, so a favorited show sat in
        this list as bare text. It links to its detail page now."""
        promotion = Promotion.objects.create(name="Fav Promotion")
        show = TVShow.objects.create(name="Favorited Show", promotion=promotion)
        UserRating.objects.create(
            user=self.user, entity_type="tv_show", entity_id=show.pk, is_favorite=True
        )
        self.client.login(username="favuser", password="testpassword123")
        response = self.client.get(reverse("my_favorites"))
        self.assertContains(response, "Favorited Show")
        self.assertContains(response, reverse("tv_show_detail", args=[show.pk]))


# =============================================================================
# Part B, item 2: Wrestler.get_completeness_score()
# =============================================================================


class WrestlerCompletenessDisplayTest(TestCase):
    def setUp(self):
        self.client = proxied_client()

    def test_completeness_percentage_shown_on_detail_page(self):
        wrestler = Wrestler.objects.create(name="Bare Wrestler")
        response = self.client.get(reverse("wrestler_detail", args=[wrestler.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"{wrestler.get_completeness_score()}% complete")


# =============================================================================
# Part B, item 3: honest entry counts on the homepage
# =============================================================================


class HomepageVerifiedStatsTest(TestCase):
    def setUp(self):
        self.client = proxied_client()

    def test_homepage_shows_total_and_verified_counts(self):
        Wrestler.objects.create(name="Verified Wrestler", verification_state="verified")
        Wrestler.objects.create(name="Candidate Wrestler", verification_state="candidate")
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["stats"]["wrestlers"], 2)
        self.assertEqual(response.context["verified_stats"]["wrestlers"], 1)
        self.assertContains(response, "1 verified")

    def test_homepage_verified_book_count_uses_verified_boolean(self):
        """Book predates VerificationMixin — no verification_state — so its
        honest count reads the plain `verified` boolean instead."""
        Book.objects.create(title="Verified Book", verified=True)
        Book.objects.create(title="Unverified Book", verified=False)
        response = self.client.get(reverse("index"))
        self.assertEqual(response.context["stats"]["books"], 2)
        self.assertEqual(response.context["verified_stats"]["books"], 1)
