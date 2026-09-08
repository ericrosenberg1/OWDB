"""
Tests for the import_podcast_rss management command's date parsing.

Regression coverage for the owdbapp bug-fix sweep, item 6:
Command.parse_date()'s RFC-2822 attempt used to swallow every exception with
a bare ``except Exception: pass``, so a malformed or unexpected date string
from a podcast feed's RSS could never be diagnosed from the logs. It now logs
at debug level when the RFC-2822 parse fails, without changing what
parse_date returns. Plain ISO-8601 feeds hit this on every episode, which is
routine, not a bug, so debug (not warning) avoids spamming logs on a normal
import run while still making failures visible if someone raises the log
level to debug the command.
"""

from django.test import SimpleTestCase

from ..management.commands.import_podcast_rss import Command

_LOGGER_NAME = "owdb_django.owdbapp.management.commands.import_podcast_rss"


class ParseDateTest(SimpleTestCase):
    def setUp(self):
        self.command = Command()

    def test_rfc_2822_date_parses_without_logging(self):
        """The common RSS case: no fallback needed, nothing logged."""
        with self.assertNoLogs(_LOGGER_NAME, level="DEBUG"):
            result = self.command.parse_date("Mon, 15 Jan 2024 10:30:00 +0000")
        self.assertIsNotNone(result)
        self.assertEqual((result.year, result.month, result.day), (2024, 1, 15))

    def test_iso_date_falls_back_and_logs_the_rfc_2822_miss(self):
        """ISO 8601 (common in real feeds) fails RFC 2822 first, then succeeds
        via the ISO branch. Must log the miss for troubleshooting but still
        return the parsed date. Control flow is unchanged by the fix."""
        with self.assertLogs(_LOGGER_NAME, level="DEBUG") as cm:
            result = self.command.parse_date("2024-01-15T10:30:00Z")
        self.assertIsNotNone(result)
        self.assertEqual((result.year, result.month, result.day), (2024, 1, 15))
        self.assertTrue(any("isn't RFC 2822" in message for message in cm.output))

    def test_date_only_iso_format_falls_back_and_logs(self):
        with self.assertLogs(_LOGGER_NAME, level="DEBUG") as cm:
            result = self.command.parse_date("2024-01-15")
        self.assertIsNotNone(result)
        self.assertEqual((result.year, result.month, result.day), (2024, 1, 15))
        self.assertTrue(any("isn't RFC 2822" in message for message in cm.output))

    def test_completely_unparseable_date_returns_none(self):
        """Behavior for a string that matches no known format is unchanged: None."""
        with self.assertLogs(_LOGGER_NAME, level="DEBUG"):
            result = self.command.parse_date("not a date at all")
        self.assertIsNone(result)

    def test_empty_or_missing_date_returns_none_without_attempting_to_parse(self):
        with self.assertNoLogs(_LOGGER_NAME, level="DEBUG"):
            self.assertIsNone(self.command.parse_date(""))
            self.assertIsNone(self.command.parse_date(None))
