"""
Authentication against the real, user-facing APIKey model.

settings.py's REST_FRAMEWORK config lists DRF's own TokenAuthentication in
DEFAULT_AUTHENTICATION_CLASSES, and rest_framework.authtoken is installed —
but nothing has ever created a Token row. The thing real users can already
generate is owdb_django.owdbapp.models.APIKey, from the account page
(templates/account.html, views.account). This authenticator validates
against that model instead of DRF's Token, because that's the credential
that actually exists.

Header: `X-API-Key`. The account page's own copy referenced this header
before the "API is in development" disclosure patch (see the regression
test test_account_page_discloses_api_is_in_development in
tests/test_views.py, which now asserts that string is gone from the
rendered page precisely because there was nothing behind it) — so
X-API-Key is what real users were already told to expect, not a new
invention. README.md's old example (`Authorization: Bearer`) was for a
JWT flow that was never built; it's been corrected to match this.
"""

from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication

from owdb_django.owdbapp.models import APIKey

API_KEY_HEADER = "X-API-Key"


class ApiKeyAuthentication(BaseAuthentication):
    """
    Validate the `X-API-Key` header against ``APIKey.objects``.

    Returns ``None`` (not an error) when the header is absent entirely, so
    a request with no key at all falls through to anonymous access — v1's
    policy is browse-for-free / key-for-a-higher-ceiling (see
    ``AnonRateThrottle`` and ``api.throttling.APIKeyRateThrottle``), not
    key-required. This is the standard DRF convention: an authenticator's
    ``authenticate()`` returns ``None`` when this scheme simply wasn't
    attempted, versus raising when it WAS attempted and failed.

    A header that IS present but doesn't match an active key raises
    ``AuthenticationFailed`` (401 — see ``authenticate_header`` below for
    why it's 401 and not 403): the caller tried to authenticate and got it
    wrong, which is a different and worse case than not trying, and
    shouldn't be silently downgraded to anonymous-tier access (that would
    hide a typo'd or revoked key behind what looks like normal, if
    rate-limited, success).

    On success, updates the key's usage bookkeeping (``last_used``,
    ``requests_today``, ``requests_total``) via the model's own
    ``increment_usage()`` — the same atomic, race-safe update the model
    already provided but that nothing ever called, so these fields have
    been dead on every key since the account page shipped.
    """

    def authenticate(self, request):
        raw_key = request.headers.get("X-API-Key", "").strip()
        if not raw_key:
            return None

        try:
            api_key = APIKey.objects.select_related("user").get(key=raw_key, is_active=True)
        except APIKey.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid or inactive API key.")

        api_key.increment_usage()
        return (api_key.user, api_key)

    def authenticate_header(self, request):
        # Any truthy value here keeps DRF's AuthenticationFailed at its
        # default 401 instead of being silently downgraded to 403 (see
        # rest_framework.views.APIView.handle_exception, which checks
        # get_authenticate_header() and only preserves 401 when it's
        # truthy). The string doesn't need to be a registered HTTP auth
        # scheme — it's just what gets set on the WWW-Authenticate header.
        return API_KEY_HEADER
