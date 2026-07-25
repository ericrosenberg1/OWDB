"""Tests for which environments are allowed to report into Sentry.

ROS-1204, ROS-1206 and ROS-1212 were all `owdb` digest alerts that could not be
attributed to a host. The cause was the same each time: the production DSN was
the fallback value for `os.getenv("SENTRY_DSN")`, so any checkout anywhere —
a laptop, a bare `docker compose up`, a CI runner — reported into the
production project tagged `environment=development`.

ROS-1212 is the case that made it worth a test. The digest carried
`AttributeError: 'VideoGame' object has no attribute 'title'`, which does not
correspond to any code in `main`, in the deployed snapshot, on any branch, or
in any historical revision — and the production host had Sentry inactive. The
alert was real; the reporter was not production.

These tests pin the rule: production reports implicitly, everything else has
to opt in.
"""

from django.test import SimpleTestCase

from ...settings import PRODUCTION_SENTRY_DSN, resolve_sentry_dsn


class ResolveSentryDsnTest(SimpleTestCase):
    """`SENTRY_DSN` unset means 'production only'."""

    def test_production_gets_the_builtin_dsn(self):
        self.assertEqual(
            resolve_sentry_dsn("production", None),
            PRODUCTION_SENTRY_DSN,
        )

    def test_development_reports_nowhere(self):
        """The ROS-1212 shape: a dev checkout must not page production."""
        self.assertIsNone(resolve_sentry_dsn("development", None))

    def test_unrecognised_environments_report_nowhere(self):
        for app_env in ("", "test", "staging", "ci", "local"):
            with self.subTest(app_env=app_env):
                self.assertIsNone(resolve_sentry_dsn(app_env, None))


class ExplicitSentryDsnTest(SimpleTestCase):
    """An explicitly set `SENTRY_DSN` is authoritative in every environment."""

    def test_explicit_dsn_wins_in_development(self):
        self.assertEqual(
            resolve_sentry_dsn("development", "https://k@example.ingest.sentry.io/42"),
            "https://k@example.ingest.sentry.io/42",
        )

    def test_explicit_dsn_overrides_the_builtin_in_production(self):
        self.assertEqual(
            resolve_sentry_dsn("production", "https://k@example.ingest.sentry.io/42"),
            "https://k@example.ingest.sentry.io/42",
        )

    def test_explicit_empty_dsn_turns_reporting_off_in_production(self):
        """`SENTRY_DSN=""` is the documented kill switch — it must beat the default."""
        self.assertIsNone(resolve_sentry_dsn("production", ""))
        self.assertIsNone(resolve_sentry_dsn("production", "   "))

    def test_surrounding_whitespace_is_stripped(self):
        self.assertEqual(
            resolve_sentry_dsn("development", "  https://k@example.ingest.sentry.io/42\n"),
            "https://k@example.ingest.sentry.io/42",
        )
