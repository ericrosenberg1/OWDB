"""
Tests for owdbapp's deploy-time system checks (owdb_django/owdbapp/checks.py).

Covers the owdbapp bug-fix sweep, item 3: settings.py falls back to Django's
well-known "django-insecure-..." dev SECRET_KEY with nothing that used to stop
the app from booting on it in production. `secret_key_is_set_in_production`
closes that gap without modifying settings.py itself, using a Django system
check registered from OwdbappConfig.ready(), the same mechanism the existing
`sqlite_directory_is_writable` (owdbapp.E001) check already uses.

Two layers, matching test_production_settings.py's approach for the same
reason: settings.py cannot be safely re-imported in this process (it calls
sentry_sdk.init() at module scope), so proving the check actually fires when
Django boots with APP_ENV=production requires a subprocess. The plain
override_settings tests below cover the check function's own logic quickly
and don't need one.
"""

import os
import subprocess
import sys
from unittest import mock

from django.conf import settings as ambient_settings
from django.test import SimpleTestCase, TestCase, override_settings

from ..checks import (
    INSECURE_SECRET_KEY_IN_PRODUCTION,
    UNRESOLVABLE_SEARCH_FIELD,
    _DEFAULT_DEV_SECRET_KEY,
    search_fields_resolve,
    secret_key_is_set_in_production,
)


class SecretKeyCheckFunctionTest(SimpleTestCase):
    """Direct tests of the check function under override_settings.

    Overrides APP_ENV, not DEBUG: the check deliberately gates on APP_ENV (see
    its docstring) precisely because `manage.py test` forces settings.DEBUG to
    False for every test in the process regardless of APP_ENV. Overriding
    DEBUG here would not even exercise the code path this check actually uses.
    """

    @override_settings(APP_ENV="production", SECRET_KEY=_DEFAULT_DEV_SECRET_KEY)
    def test_fires_when_app_env_is_production_and_key_is_still_the_dev_default(self):
        errors = secret_key_is_set_in_production(None)
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].id, INSECURE_SECRET_KEY_IN_PRODUCTION)

    @override_settings(APP_ENV="production", SECRET_KEY="a-real-randomly-generated-secret")
    def test_silent_when_app_env_is_production_and_a_real_key_is_set(self):
        self.assertEqual(secret_key_is_set_in_production(None), [])

    @override_settings(APP_ENV="development", SECRET_KEY=_DEFAULT_DEV_SECRET_KEY)
    def test_silent_in_dev_and_test_runs_even_on_the_default_key(self):
        """Normal dev/test runs (APP_ENV != production) must not be affected."""
        self.assertEqual(secret_key_is_set_in_production(None), [])


def run_manage_check(app_env, app_secret_key=None):
    """Run `manage.py check` in a subprocess under the given env; return (result, stderr).

    Runs manage.py directly rather than wrapping execute_from_command_line in a
    custom -c probe. Django's own command dispatcher catches SystemCheckError
    (a CommandError) and turns it into a plain process exit, so there is no
    exit-code plumbing to get wrong here; `result.returncode` is exactly what a
    real deploy would see from `manage.py check`.
    """
    env = {
        **os.environ,
        "APP_ENV": app_env,
        "DJANGO_SETTINGS_MODULE": "owdb_django.settings",
        # A blank DSN makes sentry_sdk.init() a no-op, same as test_production_settings.py.
        "SENTRY_DSN": "",
    }
    if app_secret_key is None:
        env.pop("APP_SECRET_KEY", None)
    else:
        env["APP_SECRET_KEY"] = app_secret_key
    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=ambient_settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result, result.stderr


class SecretKeyCheckIntegrationTest(SimpleTestCase):
    """Prove the check is actually wired up: OwdbappConfig.ready() -> checks.py ->
    Django's check framework -> `manage.py check` aborting with a real, immediate
    error. Not just that the bare function returns the right thing in isolation.
    """

    def test_manage_check_fails_in_production_without_app_secret_key(self):
        result, stderr = run_manage_check("production", app_secret_key=None)
        self.assertNotEqual(result.returncode, 0, msg=f"stderr was:\n{stderr}")
        self.assertIn(INSECURE_SECRET_KEY_IN_PRODUCTION, stderr)

    def test_manage_check_passes_in_production_with_a_real_app_secret_key(self):
        result, stderr = run_manage_check(
            "production", app_secret_key="a-real-randomly-generated-secret-key-value"
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr was:\n{stderr}")
        self.assertNotIn(INSECURE_SECRET_KEY_IN_PRODUCTION, stderr)

    def test_manage_check_passes_in_dev_without_app_secret_key(self):
        """The default dev/test path (APP_ENV != production) is unaffected."""
        result, stderr = run_manage_check("development", app_secret_key=None)
        self.assertEqual(result.returncode, 0, msg=f"stderr was:\n{stderr}")
        self.assertNotIn(INSECURE_SECRET_KEY_IN_PRODUCTION, stderr)


class SearchFieldsResolveCheckTest(SimpleTestCase):
    """Tests for `search_fields_resolve` (owdbapp.E003), added for ROS-3608.

    StableListView searched a "aliases" field that exists on Wrestler but not on
    Stable. PaginatedListView only resolves those names when a request supplies
    ?q=, so it 500'd for real visitors while importing and linting cleanly.
    """

    def test_the_shipped_views_all_resolve(self):
        """The real assertion: no list view in views.py searches a missing field.

        This is the check that would have failed before the ROS-3608 fix, and it
        fails again the moment someone adds another bad field name.
        """
        self.assertEqual(search_fields_resolve(None), [])

    def test_fires_on_a_field_the_model_does_not_have(self):
        from ..models import Stable
        from ..views import StableListView

        with mock.patch.object(StableListView, "search_fields", ["name", "aliases"]):
            errors = search_fields_resolve(None)

        self.assertEqual(len(errors), 1, msg=f"got {errors}")
        self.assertEqual(errors[0].id, UNRESOLVABLE_SEARCH_FIELD)
        self.assertIn("StableListView", errors[0].msg)
        self.assertIn("aliases", errors[0].msg)
        self.assertIn(Stable.__name__, errors[0].msg)

    def test_accepts_a_valid_related_lookup(self):
        """`promotion__name` style traversal must not be reported as missing."""
        from ..views import StableListView

        with mock.patch.object(StableListView, "search_fields", ["name", "promotion__name"]):
            self.assertEqual(search_fields_resolve(None), [])

    def test_fires_on_a_broken_related_lookup(self):
        from ..views import StableListView

        with mock.patch.object(StableListView, "search_fields", ["promotion__nope"]):
            errors = search_fields_resolve(None)

        self.assertEqual(len(errors), 1, msg=f"got {errors}")
        self.assertEqual(errors[0].id, UNRESOLVABLE_SEARCH_FIELD)

    def test_reports_every_bad_field_not_just_the_first(self):
        from ..views import StableListView

        with mock.patch.object(StableListView, "search_fields", ["nope_one", "nope_two"]):
            errors = search_fields_resolve(None)

        self.assertEqual(len(errors), 2, msg=f"got {errors}")
        self.assertEqual({e.id for e in errors}, {UNRESOLVABLE_SEARCH_FIELD})


class SearchFieldsResolveIssuesNoQueriesTest(TestCase):
    """The check must not query the database.

    Deploy checks run independently of the database being reachable, so
    resolving field names has to stay lazy: `.filter()` raises FieldError while
    *building* the query, which is why this works with Postgres down. Verified
    directly against the production image during ROS-3608 (no connection was
    opened at all).

    Asserting "no connection is open" does not port to the test harness —
    Django's SQLite backend deliberately makes close() a no-op for the
    in-memory test database, so a connection object is always present here
    regardless of what the check does. Query count is the portable signal, and
    it is the property that actually matters: zero queries cannot require a
    reachable database. Pinned so a future rewrite that evaluates the queryset
    (e.g. adding .exists()) fails loudly.

    The sibling SimpleTestCase class above is a second, independent guard: it
    declares no databases, so any query at all would error there.
    """

    def test_runs_without_issuing_a_single_query(self):
        with self.assertNumQueries(0):
            errors = search_fields_resolve(None)
        self.assertEqual(errors, [])


class SearchFieldsCheckIntegrationTest(SimpleTestCase):
    """Prove E003 is wired into `manage.py check`, not just callable."""

    def test_manage_check_passes_with_the_shipped_search_fields(self):
        result, stderr = run_manage_check(
            "production", app_secret_key="a-real-randomly-generated-secret-key-value"
        )
        self.assertEqual(result.returncode, 0, msg=f"stderr was:\n{stderr}")
        self.assertNotIn(UNRESOLVABLE_SEARCH_FIELD, stderr)
