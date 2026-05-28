"""
Custom middleware for OWDB.
"""
from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostMiddleware:
    """
    Enforce `wrestlingdb.org` as the canonical host: 301-redirect every
    `www.*` request to its bare-domain equivalent.

    Cloudflare's Single Redirect / Page Rules features would do this at
    the edge without an origin round-trip, but the cloudflared-issued
    zone token only grants DNS edit — not Rulesets / Page Rules. Doing
    it at the Django layer is one extra hop for www traffic (which is
    tiny relative to apex), and keeps the redirect rule in version
    control next to the rest of the routing logic.

    Lives BEFORE SecurityMiddleware in the MIDDLEWARE list so it short-
    circuits the rest of the stack with a 301 — saves the cost of
    session lookup, CSRF parsing, etc. on what is by definition a
    throwaway request.
    """

    _WWW_PREFIX = "www."

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().lower()
        # `get_host()` strips the port for production hosts; in dev it
        # may include `:8000`. Either way, only redirect when the host
        # part starts with `www.`.
        host_only = host.split(":", 1)[0]
        if host_only.startswith(self._WWW_PREFIX):
            canonical = host_only[len(self._WWW_PREFIX):]
            # Preserve scheme, path, and query string.
            scheme = "https" if request.is_secure() else "http"
            target = f"{scheme}://{canonical}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class ContentSecurityPolicyMiddleware:
    """
    Middleware to add Content-Security-Policy headers.

    CSP helps prevent XSS attacks by specifying which sources of content
    are allowed to be loaded by the browser.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Skip CSP for admin (TinyMCE and other admin JS needs more permissive policy)
        if request.path.startswith('/admin/'):
            return response

        # Build CSP directives
        csp_directives = [
            # Default: only allow same-origin
            "default-src 'self'",

            # Scripts: self + inline for Bootstrap/dark mode toggle
            # Note: 'unsafe-inline' is needed for Bootstrap and some inline handlers
            # In a stricter setup, use nonces or hashes instead
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net",

            # Styles: self + inline (for Bootstrap and inline styles)
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com",

            # Fonts: Google Fonts and self
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net",

            # Images: self + R2 CDN + Wikimedia (for wrestler images)
            "img-src 'self' data: https://images.wrestlingdb.org https://*.wikimedia.org https://upload.wikimedia.org",

            # Connect: API calls to self only
            "connect-src 'self'",

            # Frames: deny all
            "frame-src 'none'",

            # Object/embed: deny all
            "object-src 'none'",

            # Base URI: self only
            "base-uri 'self'",

            # Form actions: self only
            "form-action 'self'",

            # Frame ancestors: none (same as X-Frame-Options: DENY)
            "frame-ancestors 'none'",

            # Upgrade insecure requests in production
            "upgrade-insecure-requests" if not settings.DEBUG else "",
        ]

        # Filter out empty directives and join
        csp_value = "; ".join(d for d in csp_directives if d)

        # Add CSP header
        # Use Content-Security-Policy for enforcement
        # Use Content-Security-Policy-Report-Only for testing
        response['Content-Security-Policy'] = csp_value

        # Add additional security headers
        response['Permissions-Policy'] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Referrer policy - send origin for same-origin, nothing for cross-origin
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response
