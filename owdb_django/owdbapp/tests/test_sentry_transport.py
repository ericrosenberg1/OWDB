"""LoggedHttpTransport: a lost Sentry envelope has to say why.

The SDK counts a failed send as a lost event and only explains it in debug
mode, which is how OWDB lost 1,106 error envelopes in September 2026 with no
trace in the container log. See owdb_django/sentry_transport.py.
"""

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import sentry_sdk
from django.conf import settings
from django.test import SimpleTestCase
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import HttpTransport

from owdb_django.sentry_transport import LoggedHttpTransport

LOGGER = "owdb_django.sentry_transport"
SETTINGS_PY = Path(__file__).resolve().parents[2] / "settings.py"


def make_transport():
    client = sentry_sdk.Client(
        dsn="https://key@o1.ingest.us.sentry.io/1", transport=LoggedHttpTransport
    )
    return client.transport


def event_envelope():
    envelope = Envelope()
    envelope.add_event({"event_id": "a" * 32, "message": "boom"})
    return envelope


def response(status, data=b""):
    resp = MagicMock()
    resp.status = status
    resp.data = data
    resp.headers = {}
    return resp


class SdkSurfaceTests(SimpleTestCase):
    """The subclass overrides private methods. If an SDK upgrade renames or
    reshapes them, fail here instead of going quietly inert."""

    def test_overridden_methods_still_exist_with_the_same_parameters(self):
        expected = {
            "_request": ["self", "method", "endpoint_type", "body", "headers"],
            "_send_request": ["self", "body", "headers", "endpoint_type", "envelope"],
            "_handle_response": ["self", "response", "envelope"],
        }
        for name, params in expected.items():
            with self.subTest(method=name):
                signature = inspect.signature(getattr(HttpTransport, name))
                self.assertEqual(list(signature.parameters), params)

    def test_the_client_uses_the_subclass(self):
        self.assertIsInstance(make_transport(), LoggedHttpTransport)


class RetryTests(SimpleTestCase):
    def test_a_dropped_connection_is_retried_once_and_delivered(self):
        transport = make_transport()
        calls = [ConnectionResetError("reset by peer"), response(200)]

        def fake_request(*args):
            result = calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with (
            patch.object(HttpTransport, "_request", side_effect=fake_request) as request,
            patch.object(transport, "record_lost_event") as lost,
            self.assertLogs(LOGGER, "WARNING") as logs,
        ):
            transport._send_request(b"{}", {}, "envelope", event_envelope())

        self.assertEqual(request.call_count, 2)
        lost.assert_not_called()
        self.assertIn("retrying once", logs.output[0])

    def test_a_second_failure_is_logged_and_still_counted_as_lost(self):
        transport = make_transport()
        with (
            patch.object(
                HttpTransport, "_request", side_effect=TimeoutError("read timed out")
            ) as request,
            patch.object(transport, "record_lost_event") as lost,
            self.assertLogs(LOGGER, "WARNING") as logs,
            self.assertRaises(TimeoutError),
        ):
            transport._send_request(b"{}", {}, "envelope", event_envelope())

        self.assertEqual(request.call_count, 2)
        lost.assert_called_once()
        self.assertEqual(lost.call_args.args[0], "network_error")
        self.assertIn("lost after retry", logs.output[-1])
        self.assertIn("['event']", logs.output[-1])


class ResponseLoggingTests(SimpleTestCase):
    def send(self, resp):
        transport = make_transport()
        with patch.object(HttpTransport, "_request", return_value=resp):
            transport._send_request(b"{}", {}, "envelope", event_envelope())

    def test_a_rejected_envelope_logs_the_status_and_body(self):
        with self.assertLogs(LOGGER, "WARNING") as logs:
            self.send(response(400, b'{"detail":"invalid envelope"}'))
        self.assertIn("HTTP 400", logs.output[0])
        self.assertIn("invalid envelope", logs.output[0])
        self.assertIn("['event']", logs.output[0])

    def test_success_and_rate_limits_log_nothing(self):
        for status in (200, 429):
            with self.subTest(status=status), self.assertNoLogs(LOGGER, "WARNING"):
                self.send(response(status))


class SentryWiringTests(SimpleTestCase):
    """The suite runs with Sentry off, so settings.py's init never executes
    here. Pin the wiring from the source instead."""

    @staticmethod
    def init_keywords():
        for node in ast.walk(ast.parse(SETTINGS_PY.read_text())):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "init"
                and getattr(node.func.value, "id", "") == "sentry_sdk"
            ):
                return {
                    k.arg: {n.id for n in ast.walk(k.value) if isinstance(n, ast.Name)}
                    for k in node.keywords
                }
        raise AssertionError("no sentry_sdk.init() call found in settings.py")

    def test_sentry_init_takes_the_logged_transport(self):
        """Without it a lost envelope leaves no trace in the log."""
        self.assertEqual(self.init_keywords()["transport"], {"LoggedHttpTransport"})

    def test_the_transport_logger_is_kept_out_of_sentry(self):
        """A failing Sentry must not try to report its own failure."""
        self.assertIn(f'ignore_logger("{LOGGER}")', SETTINGS_PY.read_text())

    def test_the_transport_logger_reaches_the_console_at_warning(self):
        config = settings.LOGGING["loggers"][LOGGER]
        self.assertEqual(config["level"], "WARNING")
        self.assertIn("console", config["handlers"])
        self.assertFalse(config["propagate"])
