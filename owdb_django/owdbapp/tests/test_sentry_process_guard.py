"""Sentry does not initialise for interactive/one-off sessions (ROS-1411).

Four of the six "new issues" in the Jul 25–Aug 1 Sentry digest were self-inflicted.
Two were an operator mistyping an import inside `manage.py shell` on a throwaway
verification container; the stack tail was unambiguous:

    django/core/management/commands/shell.py:247 in handle
    <string>:2 in <module>

Those opened production issues. This pins the guard that stops it, and — just as
important — pins that ordinary processes are *not* silenced. The failure mode this
test exists to catch is not "the shell reported again", it is "somebody widened the
denylist and production went quiet".
"""

import os
import subprocess
import sys
import tempfile

from django.conf import settings as ambient_settings
from django.test import SimpleTestCase

from owdb_django.settings import is_non_reporting_process

# Real argv shapes, copied from what actually runs.
#   web:     Dockerfile CMD / docker-compose.nuc.yml
#   boot:    the migrate + collectstatic steps before gunicorn is exec'd
#   worker:  docker-compose.yml celery service
REPORTING_ARGV = {
    "gunicorn": ["gunicorn", "--bind", "0.0.0.0:8000", "owdb_django.wsgi:application"],
    "celery worker": ["celery", "-A", "owdb_django", "worker", "--beat"],
    "migrate": ["manage.py", "migrate", "--noinput"],
    "collectstatic": ["manage.py", "collectstatic", "--noinput", "--clear"],
    "runserver": ["manage.py", "runserver"],
    "scrape": ["manage.py", "scrape"],
    "import_podcast_rss": ["manage.py", "import_podcast_rss"],
    "setup_celery_schedule": ["manage.py", "setup_celery_schedule"],
    # A real path, not a bare name — this is how the container invokes it.
    "absolute manage.py": ["/app/manage.py", "migrate"],
    # An embedded interpreter (mod_wsgi and friends) leaves argv[0] empty. It is
    # a web server, so it must keep reporting.
    "embedded interpreter": [""],
    "empty argv": [],
    # argv[1] matches the denylist but the process is not a management command.
    "gunicorn with a colliding arg": ["gunicorn", "test"],
}

NON_REPORTING_ARGV = {
    "shell": ["manage.py", "shell"],
    # The exact invocation behind the two noisy issues.
    "shell -c": ["manage.py", "shell", "-c", "import owdbapp"],
    "dbshell": ["manage.py", "dbshell"],
    "test": ["manage.py", "test"],
    "test with a label": ["manage.py", "test", "owdbapp.tests.test_views"],
    "absolute manage.py shell": ["/app/manage.py", "shell"],
    "django-admin shell": ["django-admin", "shell"],
    "django-admin.py shell": ["django-admin.py", "dbshell"],
    "python -c": ["-c", "import owdb_django.settings"],
}


class NonReportingProcessTest(SimpleTestCase):
    """The predicate itself, against argv shapes taken from the real deployment."""

    def test_server_and_worker_processes_still_report(self):
        """Do not silence production. This is the assertion that matters most."""
        silenced = {
            name: argv for name, argv in REPORTING_ARGV.items() if is_non_reporting_process(argv)
        }
        self.assertEqual(silenced, {}, "these processes must keep reporting to Sentry")

    def test_interactive_and_one_off_sessions_do_not_report(self):
        reporting = {
            name: argv
            for name, argv in NON_REPORTING_ARGV.items()
            if not is_non_reporting_process(argv)
        }
        self.assertEqual(reporting, {}, "these sessions must not open production issues")


class SentryEnabledSettingTest(SimpleTestCase):
    """settings.py actually consults the predicate — the guard is wired, not just defined."""

    def test_the_running_test_suite_has_sentry_disabled(self):
        """This suite runs under `manage.py test`, so the guard must have tripped here.

        If this fails, the suite is reporting its own failures into the production
        project, which is half of what ROS-1411 is about.
        """
        self.assertFalse(ambient_settings.SENTRY_ENABLED)

    def test_an_ordinary_process_enables_sentry(self):
        """End-to-end: import settings.py from a plain script and it enables Sentry.

        The predicate test above proves the decision; this proves settings.py
        applies it, so a future refactor cannot leave SENTRY_ENABLED hardcoded.
        """
        probe = "import django\nfrom django.conf import settings\nprint(settings.SENTRY_ENABLED)\n"
        with tempfile.TemporaryDirectory() as tmp:
            script = os.path.join(tmp, "probe.py")
            with open(script, "w") as handle:
                handle.write(probe)
            result = subprocess.run(
                [sys.executable, script],
                cwd=ambient_settings.BASE_DIR,
                env={
                    **os.environ,
                    "DJANGO_SETTINGS_MODULE": "owdb_django.settings",
                    # Running a script file puts the *script's* directory on
                    # sys.path, not cwd, so the project has to be named
                    # explicitly. (`python -c` would inherit cwd — but that is
                    # the one shape the guard deliberately treats as a session.)
                    "PYTHONPATH": str(ambient_settings.BASE_DIR),
                    # A blank DSN makes sentry_sdk.init() a no-op. Without it this
                    # child picks up the hardcoded production DSN and registers
                    # itself as a live prod client.
                    "SENTRY_DSN": "",
                },
                capture_output=True,
                text=True,
                timeout=120,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")
