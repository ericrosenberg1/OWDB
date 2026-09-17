"""
Tests for CanonicalHostMiddleware — www.* must 301 to apex.

We don't want www.wrestlingdb.org as a real surface — it exists only to
catch users who type the www variant out of habit and bounce them to
the canonical wrestlingdb.org with their full path + query preserved.
"""

from __future__ import annotations

from django.core.exceptions import DisallowedHost
from django.test import RequestFactory, TestCase, override_settings

from owdb_django.middleware import CanonicalHostMiddleware


def _passthrough(request):
    """Sentinel response when middleware lets the request through."""
    from django.http import HttpResponse

    return HttpResponse("passed-through")


class CanonicalHostMiddlewareTests(TestCase):
    def setUp(self):
        self.mw = CanonicalHostMiddleware(_passthrough)
        self.factory = RequestFactory()

    @override_settings(ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"])
    def test_www_apex_redirects_to_bare(self):
        request = self.factory.get("/", HTTP_HOST="www.wrestlingdb.org", secure=True)
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://wrestlingdb.org/")

    @override_settings(ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"])
    def test_www_preserves_path_and_query(self):
        request = self.factory.get(
            "/wrestler/bret-hart/",
            data={"tab": "matches", "page": "2"},
            HTTP_HOST="www.wrestlingdb.org",
            secure=True,
        )
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        # Query string comes back url-encoded; check both keys present.
        self.assertTrue(
            response["Location"].startswith("https://wrestlingdb.org/wrestler/bret-hart/?")
        )
        self.assertIn("tab=matches", response["Location"])
        self.assertIn("page=2", response["Location"])

    @override_settings(ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"])
    def test_apex_request_falls_through(self):
        request = self.factory.get("/", HTTP_HOST="wrestlingdb.org", secure=True)
        response = self.mw(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"passed-through")

    @override_settings(ALLOWED_HOSTS=["www.wrestlingdb.org", "wrestlingdb.org"])
    def test_case_insensitive_host_match(self):
        # Browsers / curl sometimes send uppercase host headers.
        request = self.factory.get("/", HTTP_HOST="WWW.WrestlingDB.org", secure=True)
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://wrestlingdb.org/")

    @override_settings(ALLOWED_HOSTS=["localhost", "127.0.0.1"])
    def test_dev_host_with_port_falls_through(self):
        # `localhost:8000` doesn't start with www. — must pass through.
        request = self.factory.get("/", HTTP_HOST="localhost:8000")
        response = self.mw(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["www.example.com", "example.com"])
    def test_generic_www_redirect_works_for_any_domain(self):
        # Middleware isn't hardcoded to wrestlingdb.org — it strips the
        # `www.` prefix from whatever host comes in. Tested with
        # example.com to prove the rule isn't domain-coupled.
        request = self.factory.get("/foo", HTTP_HOST="www.example.com", secure=True)
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://example.com/foo")

    @override_settings(ALLOWED_HOSTS=["images.wrestlingdb.org"])
    def test_non_www_subdomain_falls_through(self):
        # Subdomains that aren't `www.*` (like images.wrestlingdb.org)
        # must NOT be touched — they have their own purpose.
        request = self.factory.get(
            "/wrestlers/79/profile.jpg", HTTP_HOST="images.wrestlingdb.org", secure=True
        )
        response = self.mw(request)
        self.assertEqual(response.status_code, 200)

    @override_settings(ALLOWED_HOSTS=["www.wrestlingdb.org"])
    def test_http_request_redirects_to_http(self):
        # Pre-TLS request → middleware preserves the scheme (the
        # downstream SecurityMiddleware does the http→https upgrade).
        # We don't want this middleware double-counting that responsibility.
        request = self.factory.get("/", HTTP_HOST="www.wrestlingdb.org")
        # secure=False default → request.is_secure() returns False
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "http://wrestlingdb.org/")


class ForwardedHostTrustTests(TestCase):
    """`X-Forwarded-Host` must not decide which host Django thinks it is.

    Regression test for ROS-2862 / Sentry OWDB-F. A scanner sent a valid
    `Host: wrestlingdb.org` alongside a forged
    `X-Forwarded-Host: canary-rustworst-abcd1234.internal`. Production was
    running `USE_X_FORWARDED_HOST = True` behind a cloudflared tunnel that
    forwards client headers verbatim, so the forged value won, failed
    ALLOWED_HOSTS validation, and raised DisallowedHost out of
    CanonicalHostMiddleware's `request.get_host()` call.

    Only ALLOWED_HOSTS stood between that header and host-header poisoning of
    every absolute URL the app builds, so the fix is to stop reading the
    header at all rather than to widen the allowlist.
    """

    def setUp(self):
        self.mw = CanonicalHostMiddleware(_passthrough)
        self.factory = RequestFactory()

    def _forged_request(self):
        return self.factory.get(
            "/",
            HTTP_HOST="wrestlingdb.org",
            HTTP_X_FORWARDED_HOST="canary-rustworst-abcd1234.internal",
            secure=True,
        )

    @override_settings(ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"])
    def test_forged_forwarded_host_is_ignored(self):
        request = self._forged_request()
        self.assertEqual(request.get_host(), "wrestlingdb.org")
        response = self.mw(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"passed-through")

    @override_settings(ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"])
    def test_forged_forwarded_host_cannot_hijack_the_canonical_redirect(self):
        # The www→apex 301 builds its Location from get_host(). If the forged
        # header were trusted, an attacker could aim that redirect off-site.
        request = self.factory.get(
            "/",
            HTTP_HOST="www.wrestlingdb.org",
            HTTP_X_FORWARDED_HOST="www.attacker.example",
            secure=True,
        )
        response = self.mw(request)
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "https://wrestlingdb.org/")

    @override_settings(
        ALLOWED_HOSTS=["wrestlingdb.org", "www.wrestlingdb.org"],
        USE_X_FORWARDED_HOST=True,
    )
    def test_positive_control_trusting_the_header_reproduces_the_sentry_error(self):
        # Proves the two tests above are actually load-bearing: flip the
        # setting back and the exact production failure returns.
        with self.assertRaises(DisallowedHost):
            self.mw(self._forged_request())
