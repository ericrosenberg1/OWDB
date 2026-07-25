"""Deploy-time system checks for OWDB.

Registered from OwdbappConfig.ready(), so they run on `manage.py check`,
`migrate`, `runserver` and the container start command.
"""

import os

from django.conf import settings
from django.core.checks import Error, register

SQLITE_DIR_NOT_WRITABLE = "owdbapp.E001"


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
        if "sqlite3" not in config.get("ENGINE", ""):
            continue
        name = str(config.get("NAME", ""))
        # :memory: and other special names have no directory to check.
        if not name or name.startswith(":"):
            continue
        directory = os.path.dirname(os.path.abspath(name))
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
