"""What settings.py hands production, checked from a suite that does not run it.

`DEBUG = APP_ENV != "production"` gates a whole block of security settings, and
the suite runs with `APP_ENV=test` (.github/workflows/ci.yml), so that block is
skipped everywhere it is normally checked. Nothing gated it: the production
config could lose HSTS, the secure-cookie flags or the /health/ redirect
exemption and every test would stay green (ROS-1214).

The behavioural half of this lives in test_security.py, which pins the
production *values* under `override_settings` so the assertions survive any
APP_ENV. This file pins the other half — that settings.py actually chooses those
values when APP_ENV=production.

It has to import settings a second time to do that, and settings.py is not
re-importable in place: it calls `sentry_sdk.init()` at module scope, which would
replace the running process's Sentry client. So each check runs in a subprocess
with a clean environment, and with SENTRY_DSN blanked so the child cannot pick up
the hardcoded production DSN and register itself as a live prod client.
"""

import json
import os
import subprocess
import sys

from django.conf import settings as ambient_settings
from django.test import SimpleTestCase

# Everything settings.py's `if not DEBUG` block is responsible for, plus the two
# proxy settings it depends on. SECURE_PROXY_SSL_HEADER is outside the block but
# belongs here: without it every proxied request looks insecure, SECURE_SSL_REDIRECT
# 301s it, and production redirect-loops.
EXPECTED_PRODUCTION_SETTINGS = {
    "DEBUG": False,
    "SECURE_BROWSER_XSS_FILTER": True,
    "SECURE_CONTENT_TYPE_NOSNIFF": True,
    "X_FRAME_OPTIONS": "DENY",
    "SECURE_HSTS_SECONDS": 31536000,
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
    "SECURE_HSTS_PRELOAD": True,
    "SESSION_COOKIE_SECURE": True,
    "CSRF_COOKIE_SECURE": True,
    "SESSION_COOKIE_HTTPONLY": True,
    "CSRF_COOKIE_HTTPONLY": True,
    "SESSION_COOKIE_SAMESITE": "Lax",
    "CSRF_COOKIE_SAMESITE": "Lax",
    "SECURE_SSL_REDIRECT": True,
    # json turns the tuple into a list on the way back.
    "SECURE_PROXY_SSL_HEADER": ["HTTP_X_FORWARDED_PROTO", "https"],
    "SECURE_REDIRECT_EXEMPT": ["^health/$", "^health/ready/$"],
}

_PROBE = (
    "import json, sys\n"
    "from django.conf import settings\n"
    "print(json.dumps({n: getattr(settings, n, None) for n in json.loads(sys.argv[1])}, default=str))\n"
)


def settings_under_app_env(app_env, names):
    """Import settings.py in a subprocess with APP_ENV=app_env; return the values."""
    env = {
        **os.environ,
        "APP_ENV": app_env,
        "DJANGO_SETTINGS_MODULE": "owdb_django.settings",
        # A blank DSN makes sentry_sdk.init() a no-op. Without it the child would
        # fall back to the hardcoded production DSN in settings.py.
        "SENTRY_DSN": "",
    }
    result = subprocess.run(
        [sys.executable, "-c", _PROBE, json.dumps(list(names))],
        cwd=ambient_settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"importing settings with APP_ENV={app_env!r} failed "
            f"(exit {result.returncode}):\n{result.stderr}"
        )
    return json.loads(result.stdout)


class ProductionSecuritySettingsTest(SimpleTestCase):
    """APP_ENV=production still turns on everything it is supposed to."""

    # The failure message is the whole point of this test — show the full diff
    # rather than unittest's truncated "[366 chars]".
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.production = settings_under_app_env("production", EXPECTED_PRODUCTION_SETTINGS.keys())

    def test_production_security_settings(self):
        """Assert the whole block at once so a removal shows up as a diff, not a hunt."""
        self.assertEqual(self.production, EXPECTED_PRODUCTION_SETTINGS)


class NonProductionAppEnvTest(SimpleTestCase):
    """Why the test above needs a subprocess at all.

    The suite's own APP_ENV is not production, so the security block does not run
    in this process and reading `django.conf.settings` here would prove nothing.
    Pinning that keeps the gap visible: if CI is ever pointed at APP_ENV=production
    this test fails loudly rather than the coverage question going quiet again.
    """

    def test_test_env_does_not_enable_the_production_block(self):
        values = settings_under_app_env("test", ["DEBUG", "SECURE_SSL_REDIRECT"])
        self.assertTrue(values["DEBUG"])
        self.assertFalse(values["SECURE_SSL_REDIRECT"])
