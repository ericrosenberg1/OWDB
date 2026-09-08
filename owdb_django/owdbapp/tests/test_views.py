"""
Tests for OWDB views.

These use `proxied_client()` rather than a bare `Client()`. Under
APP_ENV=production a plain-HTTP test request is 301'd by SecurityMiddleware before
any view runs, so every assertion below would check the redirect instead of the
view — see proxied_client.py for the full explanation (ROS-1210).
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone

from ..models import Wrestler, Promotion, Event, Venue, Match, UserProfile
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
