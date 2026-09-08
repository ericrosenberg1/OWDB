"""Deploy-time system checks for OWDB.

Registered from OwdbappConfig.ready(), so they run on `manage.py check`,
`migrate`, `runserver` and the container start command.
"""

import os

from django.conf import settings
from django.core.checks import Error, register

SQLITE_DIR_NOT_WRITABLE = "owdbapp.E001"
INSECURE_SECRET_KEY_IN_PRODUCTION = "owdbapp.E002"

# Must match the hardcoded fallback in settings.py:
#   SECRET_KEY = os.getenv("APP_SECRET_KEY", "django-insecure-development-key-change-in-production")
# Kept here rather than imported from settings so this check has no import-time
# dependency on settings.py beyond the already-required `django.conf.settings`.
_DEFAULT_DEV_SECRET_KEY = "django-insecure-development-key-change-in-production"


def sqlite_db_directory(config):
    """Return the directory holding ``config``'s SQLite file, or None.

    None means "no directory to check" — a non-SQLite engine, or a database
    that does not live on disk at all.

    The in-memory cases are worth spelling out. Django's test runner does not
    use the plain ``:memory:`` name; it swaps NAME for the shared-cache URI
    ``file:memorydb_default?mode=memory&cache=shared``. That does not start
    with ":", so treating it as a path yields the *current working directory*,
    and the writability check then fails on any run whose cwd happens to be
    read-only. It fired on the first containerised test run of ROS-1209 and
    aborted the whole suite with owdbapp.E001 before a single test executed.
    """
    if "sqlite3" not in config.get("ENGINE", ""):
        return None
    name = str(config.get("NAME", ""))
    if not name or name.startswith(":") or "mode=memory" in name:
        return None
    return os.path.dirname(os.path.abspath(name))


@register()
def sqlite_directory_is_writable(app_configs, **kwargs):
    """Fail loudly when the SQLite DB sits in a directory we cannot write.

    SQLite creates a rollback journal (``<db>-journal``) *next to* the database
    file for every write transaction, and creates the database file itself if it
    is missing — both need write permission on the containing directory, not just
    on the .sqlite3 file. Get this wrong and reads keep working while every write
    fails with "attempt to write a readonly database" (or, when the file does not
    exist yet, "unable to open database file"). That is a silent, healthcheck-
    passing outage: it took six weeks to notice /signup/ was 500ing. See ROS-1204.
    """
    errors = []
    for alias, config in settings.DATABASES.items():
        directory = sqlite_db_directory(config)
        if directory is None:
            continue
        name = str(config.get("NAME", ""))
        if os.access(directory, os.W_OK):
            continue
        errors.append(
            Error(
                f"SQLite database {alias!r} is at {name}, but {directory} is not "
                f"writable by this process (uid {os.getuid()}). Every write will "
                f"fail even though reads succeed.",
                hint=(
                    "Point the database at a writable directory — set the "
                    "SQLITE_PATH env var (e.g. SQLITE_PATH=/app/data/db.sqlite3, "
                    "with ./data bind-mounted) rather than leaving it at "
                    "BASE_DIR/db.sqlite3 inside the read-only image layer."
                ),
                id=SQLITE_DIR_NOT_WRITABLE,
            )
        )
    return errors


@register()
def secret_key_is_set_in_production(app_configs, **kwargs):
    """Fail loudly when production is still running on the public dev SECRET_KEY.

    settings.py falls back to a hardcoded, well-known "django-insecure-..."
    string when the APP_SECRET_KEY env var is not set. That default is fine for
    local dev, but it is a real hole in production: SECRET_KEY signs session
    cookies, the CSRF token, and password-reset-style tokens, so a key anyone
    can read out of the open-source repo lets an attacker forge all of them.
    There was previously nothing forcing a real key to be set before the app
    booted in production.

    Gates on ``APP_ENV == "production"`` rather than ``settings.DEBUG``. They
    normally agree (settings.py derives ``DEBUG = APP_ENV != "production"``),
    but `manage.py test` unconditionally forces ``settings.DEBUG = False`` for
    the whole run (Django's own setup_test_environment(), independent of
    APP_ENV), while the test suite also never sets APP_SECRET_KEY. Gating on
    DEBUG would make this check fire, and abort, every single `manage.py
    test` invocation project-wide. APP_ENV is the one signal the test runner
    does not touch.
    """
    if getattr(settings, "APP_ENV", "development") != "production":
        return []
    if settings.SECRET_KEY != _DEFAULT_DEV_SECRET_KEY:
        return []
    return [
        Error(
            "SECRET_KEY is still the public Django dev default even though "
            "APP_ENV=production. Anyone can read this key from the "
            "open-source repo and use it to forge session cookies, CSRF "
            "tokens, and password-reset links.",
            hint=(
                "Set the APP_SECRET_KEY environment variable to a unique, "
                "randomly-generated secret before starting the app in "
                'production. Generate one with: python -c "from '
                "django.core.management.utils import get_random_secret_key; "
                'print(get_random_secret_key())"'
            ),
            id=INSECURE_SECRET_KEY_IN_PRODUCTION,
        )
    ]
