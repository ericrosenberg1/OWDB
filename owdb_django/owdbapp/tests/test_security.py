"""
Security tests for OWDB.

These use `proxied_client()` rather than a bare `Client()`. Under
APP_ENV=production a plain-HTTP test request is 301'd by SecurityMiddleware before
any view runs, so every assertion below would check the redirect instead of the
thing it names — see proxied_client.py for the full explanation (ROS-1210).
"""

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from .proxied_client import proxied_client


class SecurityHeadersTest(TestCase):
    """Tests for security headers."""

    def setUp(self):
        self.client = proxied_client()

    def test_x_frame_options(self):
        """Test X-Frame-Options header is set.

        Not wrapped in override_settings(DEBUG=False): the production security
        block runs at settings-import time, so flipping DEBUG here changes
        nothing. DENY holds either way — production sets it explicitly and it is
        also Django's default.
        """
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Frame-Options"), "DENY")

    def test_content_type_options(self):
        """Test X-Content-Type-Options header."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_proxied_https_is_not_redirected(self):
        """A proxied HTTPS request reaches the view instead of being redirected.

        This is the setting the rest of the file leans on. If SECURE_PROXY_SSL_HEADER
        is ever dropped, this test names the cause — otherwise every other test here
        fails with an unexplained 301, and production redirect-loops.
        """
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    @override_settings(
        SECURE_HSTS_SECONDS=31536000,
        SECURE_HSTS_INCLUDE_SUBDOMAINS=True,
        SECURE_HSTS_PRELOAD=True,
    )
    def test_hsts_header_on_proxied_https(self):
        """The production HSTS settings produce the header we expect.

        Values are overridden rather than read from settings so this carries the
        same signal under APP_ENV=test, where the production block never runs
        (ROS-1214). That the block *sets* these values is gated separately, in
        test_production_settings.py.
        """
        response = self.client.get(reverse("index"))
        self.assertEqual(
            response.get("Strict-Transport-Security"),
            "max-age=31536000; includeSubDomains; preload",
        )

    @override_settings(SECURE_HSTS_SECONDS=31536000)
    def test_hsts_header_not_sent_over_plain_http(self):
        """HSTS rides only on responses Django considers secure.

        Not a nice-to-have: it is why the header depends on SECURE_PROXY_SSL_HEADER
        and X-Forwarded-Proto surviving the proxy. A bare client stands in for a
        request that lost them — if this ever starts returning the header, the
        secure/insecure distinction has broken somewhere.
        """
        response = Client().get(reverse("index"))
        self.assertIsNone(response.get("Strict-Transport-Security"))


class CSRFProtectionTest(TestCase):
    """Tests for CSRF protection."""

    def setUp(self):
        # Referer is supplied because Django applies strict Referer checking to
        # HTTPS requests. Without a valid one the 403s below prove only that the
        # Referer was absent, and would still pass with token checking disabled.
        # With it, the rejection is "CSRF cookie not set" — the real subject.
        self.client = proxied_client(
            enforce_csrf_checks=True, headers={"Referer": "https://testserver/"}
        )
        self.user = User.objects.create_user(
            username="csrfuser", email="csrf@example.com", password="testpassword123"
        )

    def test_login_requires_csrf(self):
        """Test that login POST requires CSRF token."""
        response = self.client.post(
            reverse("login"), {"username": "csrfuser", "password": "testpassword123"}
        )
        self.assertEqual(response.status_code, 403)  # CSRF failure

    def test_logout_requires_csrf(self):
        """Test that logout POST requires CSRF token."""
        # Login first (without CSRF checks)
        client = proxied_client()
        client.login(username="csrfuser", password="testpassword123")

        # Now try to logout with CSRF enforcement
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 403)


class OpenRedirectTest(TestCase):
    """Tests for open redirect prevention."""

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="redirectuser", email="redirect@example.com", password="testpassword123"
        )

    def test_login_prevents_open_redirect(self):
        """Test that login doesn't redirect to external URLs."""
        response = self.client.post(
            reverse("login") + "?next=https://evil.com",
            {"username": "redirectuser", "password": "testpassword123"},
        )
        # Should redirect to index, not external URL
        self.assertRedirects(response, reverse("index"))

    def test_login_allows_internal_redirect(self):
        """Test that login allows internal redirects."""
        response = self.client.post(
            reverse("login") + "?next=/wrestlers/",
            {"username": "redirectuser", "password": "testpassword123"},
        )
        # Should redirect to wrestlers page
        self.assertRedirects(response, "/wrestlers/")


class InputValidationTest(TestCase):
    """Tests for input validation."""

    def setUp(self):
        self.client = proxied_client()

    def test_search_handles_special_characters(self):
        """Test that search handles special characters safely."""
        special_chars = "<script>alert('xss')</script>"
        response = self.client.get(reverse("wrestlers"), {"q": special_chars})
        self.assertEqual(response.status_code, 200)
        # XSS payload should not appear raw in the response
        # (assertNotContains("<script>") would false-positive on any page JS)
        self.assertNotContains(response, special_chars)

    def test_search_handles_sql_injection_attempt(self):
        """Test that search handles SQL injection attempts safely."""
        sql_injection = "'; DROP TABLE wrestlers; --"
        response = self.client.get(reverse("wrestlers"), {"q": sql_injection})
        self.assertEqual(response.status_code, 200)

    def test_signup_username_validation(self):
        """Test username validation on signup."""
        # Username too short
        response = self.client.post(
            reverse("signup"),
            {
                "username": "ab",  # Less than 3 chars
                "email": "test@example.com",
                "password1": "testpassword123",
                "password2": "testpassword123",
            },
        )
        self.assertContains(response, "at least 3 characters")

    def test_signup_password_mismatch(self):
        """Test password mismatch on signup."""
        response = self.client.post(
            reverse("signup"),
            {
                "username": "testuser",
                "email": "test@example.com",
                "password1": "testpassword123",
                "password2": "differentpassword",
            },
        )
        self.assertContains(response, "Passwords do not match")


class SessionSecurityTest(TestCase):
    """Tests for session security."""

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="sessionuser", email="session@example.com", password="testpassword123"
        )

    def test_session_created_on_login(self):
        """Test that session is created on login."""
        self.client.login(username="sessionuser", password="testpassword123")
        self.assertIn("sessionid", self.client.cookies)

    def test_session_destroyed_on_logout(self):
        """Test that session is destroyed on logout."""
        self.client.login(username="sessionuser", password="testpassword123")
        self.assertNotEqual(self.client.cookies["sessionid"].value, "")
        self.client.post(reverse("logout"))
        # Session cookie should be cleared
        self.assertEqual(self.client.cookies["sessionid"].value, "")


class ProductionCookieFlagsTest(TestCase):
    """The session and CSRF cookies carry the flags production configures.

    Same reasoning as the HSTS tests above: the values are overridden rather than
    inherited from the ambient APP_ENV, so these keep their meaning under
    APP_ENV=test where the production block is skipped entirely (ROS-1214).

    Cookies are read off a real response, not off `client.login()` — the test
    client's login shortcut copies `SESSION_COOKIE_SECURE` by hand and ignores
    HttpOnly and SameSite, so it would pass even if SessionMiddleware set neither.
    """

    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="cookieuser", email="cookie@example.com", password="testpassword123"
        )

    @override_settings(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    def test_session_cookie_carries_production_flags(self):
        response = self.client.post(
            reverse("login"), {"username": "cookieuser", "password": "testpassword123"}
        )
        cookie = response.cookies["sessionid"]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

    @override_settings(
        CSRF_COOKIE_SECURE=True,
        CSRF_COOKIE_HTTPONLY=True,
        CSRF_COOKIE_SAMESITE="Lax",
    )
    def test_csrf_cookie_carries_production_flags(self):
        response = self.client.get(reverse("login"))
        cookie = response.cookies["csrftoken"]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")


class HealthCheckRedirectExemptTest(TestCase):
    """The container healthcheck hits /health/ over plain HTTP on localhost.

    With SECURE_SSL_REDIRECT on and no exemption, SecurityMiddleware returns a
    301 before the view runs, and `curl -f` counts that as success — so the
    check reported healthy while the app was broken (ROS-1204/ROS-1207).

    These use a plain client on purpose: the point is what an unproxied,
    plain-HTTP caller gets.
    """

    def setUp(self):
        self.client = Client()

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^health/$"])
    def test_health_is_not_ssl_redirected(self):
        """/health/ answers over plain HTTP instead of redirecting."""
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^health/$"])
    def test_other_paths_still_ssl_redirect(self):
        """The exemption is scoped to /health/ — everything else still 301s."""
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))
