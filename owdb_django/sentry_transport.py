"""Sentry transport that says why an envelope was lost.

sentry-sdk files a failed send as a lost event and only logs the cause when
`debug=True`. Sentry's stats page showed OWDB losing 1,106 error envelopes in
September 2026, each one matching a lost transaction from the same hour, and
every loss carried the client-report reason `network_error`. Nothing in the
container log said why.

This subclass changes two things:

- Every failed send logs the exception or the HTTP status and response body,
  with the envelope's item types, to the console log. The logger is excluded
  from Sentry in settings.py, so a failing Sentry can't feed itself.
- A request that raises is retried once on a fresh connection before the
  envelope is counted as lost. Sentry drops a repeated event id, so a retry
  after a response that never arrived can't duplicate an issue.

Ported from FreelancerDashboard, which lost envelopes the same way.

`_request`, `_send_request` and `_handle_response` are private SDK methods.
`owdb_django/owdbapp/tests/test_sentry_transport.py` fails if an SDK upgrade
renames them, rather than letting this go quietly inert.
"""

import logging

from sentry_sdk.transport import HttpTransport

logger = logging.getLogger(__name__)


def _item_types(envelope):
    if envelope is None:
        return []
    return [item.type for item in envelope.items]


class LoggedHttpTransport(HttpTransport):
    def _request(self, method, endpoint_type, body, headers):
        try:
            return super()._request(method, endpoint_type, body, headers)
        except Exception as exc:
            logger.warning("Sentry send raised %r, retrying once", exc)
        return super()._request(method, endpoint_type, body, headers)

    def _send_request(self, body, headers, endpoint_type, envelope=None):
        try:
            return super()._send_request(body, headers, endpoint_type, envelope)
        except Exception as exc:
            logger.warning(
                "Sentry envelope lost after retry: %r (items %s)", exc, _item_types(envelope)
            )
            raise

    def _handle_response(self, response, envelope):
        # 429 is Sentry's rate limit, recorded as its own outcome server side.
        if not 200 <= response.status < 300 and response.status != 429:
            logger.warning(
                "Sentry rejected envelope: HTTP %s (items %s) %r",
                response.status,
                _item_types(envelope),
                (getattr(response, "data", b"") or b"")[:500],
            )
        return super()._handle_response(response, envelope)
