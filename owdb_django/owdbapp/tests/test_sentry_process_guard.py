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
from contextlib import chdir

from django.conf import settings as ambient_settings
from django.test import SimpleTestCase

from owdb_django.settings import is_non_reporting_process

# Real argv shapes, copied from what actually runs.
#   web:     Dockerfile CMD / production compose override
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
    # ROS-4038 exempts manage.py from the scratch-script rule: CI and every
    # throwaway clone put a checkout in a scratch directory, and a management
    # command is an unattended entrypoint wherever it is run from.
    "manage.py from a scratch clone": ["/tmp/owdb-clone/manage.py", "migrate"],
    "django-admin from a scratch clone": ["/tmp/owdb-clone/django-admin", "collectstatic"],
    # The prefix match carries a trailing separator on purpose, so a real
    # deploy directory whose name merely starts with a scratch dir's keeps
    # reporting.
    "scratch lookalike dir": ["/tmpfiles/app/run.py"],
    "scratch lookalike under /var": ["/var/tmpdeploy/run.py"],
    # An ordinary script outside a scratch dir: argv cannot tell it from a cron
    # entry, so it must not be silenced implicitly.
    "script from the image": ["/app/scripts/backfill.py"],
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
    # ROS-4037/ROS-4038: a one-off written to a file in a scratch directory.
    # argv[0] is a real path, so the two rules above both miss it.
    "scratch script": ["/tmp/brian-ROS-4036-ledger.py"],
    "scratch script under /var/tmp": ["/var/tmp/probe.py"],
    "scratch script on tmpfs": ["/dev/shm/one-off.py"],
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


class ScratchScriptResolutionTest(SimpleTestCase):
    """The two scratch-dir cases a static argv table cannot express."""

    def test_a_relative_scratch_script_is_detected(self):
        """A one-off is usually run as `python ledger.py` from inside /tmp, so
        the path has to be resolved before it is classified.

        Really chdir rather than mock realpath — a mocked resolver would pass
        even if the predicate never resolved anything.
        """
        with chdir("/tmp"):
            self.assertTrue(is_non_reporting_process(["ledger.py"]))

    def test_an_embedded_interpreter_in_a_scratch_cwd_still_reports(self):
        """realpath("") is the cwd, so the scratch check has to come after the
        empty-argv cases or a web server started from /tmp goes quiet."""
        with chdir("/tmp"):
            self.assertFalse(is_non_reporting_process([""]))
            self.assertFalse(is_non_reporting_process([]))


class SentryEnabledSettingTest(SimpleTestCase):
    """settings.py actually consults the predicate — the guard is wired, not just defined."""

    #: Imports settings.py and prints the decision it reached. Nothing else:
    #: the point is that SENTRY_ENABLED is computed, not hardcoded.
    PROBE = "import django\nfrom django.conf import settings\nprint(settings.SENTRY_ENABLED)\n"

    def _sentry_enabled_in_a_child(self, directory):
        """Run PROBE as a real script file under `directory`, return its output.

        argv[0] is then the script's own path, which is the whole point — it is
        the one thing the two callers vary, and the only thing the guard reads.
        """
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            script = os.path.join(tmp, "probe.py")
            with open(script, "w") as handle:
                handle.write(self.PROBE)
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
        return result.stdout.strip()

    def test_the_running_test_suite_has_sentry_disabled(self):
        """This suite runs under `manage.py test`, so the guard must have tripped here.

        If this fails, the suite is reporting its own failures into the production
        project, which is half of what ROS-1411 is about.
        """
        self.assertFalse(ambient_settings.SENTRY_ENABLED)

    def test_an_ordinary_process_enables_sentry(self):
        """End-to-end: import settings.py from a plain script and it enables Sentry.

        The predicate tests above prove the decision; this proves settings.py
        applies it, so a future refactor cannot leave SENTRY_ENABLED hardcoded.

        The probe dir sits inside the checkout on purpose. Until ROS-4038 this
        used tempfile's default of /tmp, which the scratch-script rule now
        reads as an operator session — the child would print False and this
        test would fail for the right reason but in a confusing place.
        """
        self.assertEqual(self._sentry_enabled_in_a_child(ambient_settings.BASE_DIR), "True")

    def test_a_script_in_a_scratch_dir_disables_sentry(self):
        """The ROS-4037 shape, end to end: the same probe run from /tmp comes
        back False.

        Paired with the test above, this pins the rule rather than the probe's
        own location — one script, two directories, two answers. This is the
        assertion a static argv table cannot make: it proves the *shipped*
        settings.py silences a real scratch script in a real child process.
        """
        self.assertEqual(self._sentry_enabled_in_a_child("/tmp"), "False")
