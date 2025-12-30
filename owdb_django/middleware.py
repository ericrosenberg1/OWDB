"""
Custom middleware for OWDB.
"""
from django.conf import settings


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
