"""
Custom DRF throttle for the two API-key tiers.

settings.py's REST_FRAMEWORK.DEFAULT_THROTTLE_CLASSES already includes
``rest_framework.throttling.AnonRateThrottle`` — that one is used exactly
as DRF ships it, keyed by IP, scope "anon", and needs no changes: it
already does the right thing for a request with no API key, because
``ApiKeyAuthentication`` leaves ``request.user`` as ``AnonymousUser`` in
that case (see ``AnonRateThrottle.get_cache_key``, which only skips
requests where ``request.user.is_authenticated``).

This module covers the other half: a request that DOES carry a valid
``X-API-Key`` (``ApiKeyAuthentication`` sets ``request.auth`` to the
``APIKey`` instance) needs one of two different rates depending on
``APIKey.is_paid`` — "authenticated" (1,000/hour) or "paid" (10,000/hour).
A single static ``scope`` class attribute — what DRF's stock
``UserRateThrottle`` uses — can't express a rate that depends on request
data, so the scope is resolved per-request instead, the same trick DRF's
own ``ScopedRateThrottle`` uses to defer scope resolution until
``allow_request()`` actually has a request to look at.
"""

from rest_framework.throttling import SimpleRateThrottle


class APIKeyRateThrottle(SimpleRateThrottle):
    """
    1,000 requests/hour for a free (authenticated, non-paid) key, 10,000/hour
    once ``APIKey.is_paid`` is set. The rates themselves live in
    ``settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]`` under the
    ``"user"`` and ``"paid"`` scopes — see README.md's Rate Limits table for
    the numbers as published to API consumers.
    """

    def __init__(self):
        # Deliberately skip SimpleRateThrottle.__init__: it resolves
        # self.rate from self.scope immediately at construction time, but
        # which scope applies here depends on request.auth, which doesn't
        # exist yet when DRF builds the throttle instances for a view.
        pass

    def allow_request(self, request, view):
        api_key = getattr(request, "auth", None)
        if api_key is None:
            # No valid API key on this request — anonymous, and
            # AnonRateThrottle is the one that applies instead.
            return True
        self.scope = "paid" if api_key.is_paid else "user"
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_cache_key(self, request, view):
        api_key = getattr(request, "auth", None)
        if api_key is None:
            return None
        # Keyed on the APIKey row's own id, not the secret key string
        # itself — no reason to put the raw credential into cache keys.
        return self.cache_format % {"scope": self.scope, "ident": api_key.pk}
