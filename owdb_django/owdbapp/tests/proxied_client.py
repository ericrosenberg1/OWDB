"""A test client whose requests arrive the way production traffic does.

Production sets ``SECURE_SSL_REDIRECT = True`` (settings.py, the ``if not DEBUG``
block), so SecurityMiddleware answers any request that does not look like HTTPS
with a 301 before the view runs. Real traffic never sees that redirect: it comes
through the Cloudflare tunnel, which sets ``X-Forwarded-Proto``, and
``SECURE_PROXY_SSL_HEADER`` tells Django to trust it.

The Django test client speaks plain HTTP, so under ``APP_ENV=production`` every
request 301s and each assertion silently checks the redirect instead of the thing
it names. That is how 34 tests across test_security.py and test_views.py came to
be red without anyone noticing a real regression (ROS-1210).

Two details that are easy to get wrong:

* Passing ``secure=True`` per request is not enough. ``assertRedirects`` re-fetches
  the redirect target with ``secure`` derived from the Location scheme, and our
  Locations are relative, so the follow-up request 301s anyway. Setting the headers
  on the client covers the request under test *and* every request the assertion
  helpers make on its behalf.
* ``X-Forwarded-Port`` is not optional. Settings enables ``USE_X_FORWARDED_PORT``,
  so without it ``request.get_host()`` reports ``testserver:80`` on a request Django
  considers secure. That breaks host-matching checks — CSRF Referer/Origin
  validation and the login view's open-redirect guard — in a way no real request
  ever would.

Tests that deliberately exercise the unproxied, plain-HTTP path (the container
healthcheck reaching /health/, or asserting that non-exempt paths still redirect)
should keep using a bare ``Client()``.
"""

from django.test import Client

# What the reverse proxy puts in front of every real production request.
PROXIED_HTTPS = {"X-Forwarded-Proto": "https", "X-Forwarded-Port": "443"}


def proxied_client(*, headers=None, **kwargs):
    """Return a test ``Client`` that looks like it came through the production proxy.

    Extra ``headers`` are merged on top of the proxy headers; any other keyword
    argument is passed straight through to ``Client`` (e.g. ``enforce_csrf_checks``).
    """
    return Client(headers={**PROXIED_HTTPS, **(headers or {})}, **kwargs)
