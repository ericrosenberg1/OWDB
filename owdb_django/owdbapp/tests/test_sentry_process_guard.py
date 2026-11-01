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

from unittest import SkipTest

from django.conf import settings as ambient_settings
from django.test import SimpleTestCase

from owdb_django.settings import _SCRATCH_DIR_PREFIXES, is_non_reporting_process

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
    # An ordinary script outside a scratch dir: argv cannot tell it from a cron
    # entry, so it must not be silenced implicitly.
    "script from the image": ["/app/scripts/backfill.py"],
    # A path under /tmp that is not a file is not a script anybody ran. These
    # must not be silenced on the strength of the prefix alone (ROS-4038).
    "nonexistent path under /tmp": ["/tmp/owdb-no-such-file.py"],
    # The prefix match carries a trailing separator on purpose, so a real
    # deploy directory whose name merely starts with a scratch dir's keeps
    # reporting. ScratchScriptResolutionTest pins the separator directly.
    "scratch lookalike dir": ["/tmpfiles/app/run.py"],
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


class ScratchScriptResolutionTest(SimpleTestCase):
    """The scratch-dir cases a static argv table cannot express (ROS-4038).

    The predicate requires argv[0] to be a real file, so these build real
    files rather than naming paths. That is deliberate: a test that asserted
    on a path which does not exist would pass for the wrong reason.
    """

    def setUp(self):
        self.scratch_dirs = [d for d in ("/tmp", "/var/tmp", "/dev/shm") if os.path.isdir(d)]
        self.assertTrue(self.scratch_dirs, "expected at least one scratch dir to exist")
        self.made = []
        for d in self.scratch_dirs:
            handle = tempfile.NamedTemporaryFile(dir=d, suffix="-ros4038.py", delete=False)
            handle.close()
            self.made.append(handle.name)
            self.addCleanup(os.unlink, handle.name)

    def test_a_real_script_in_every_scratch_dir_is_detected(self):
        for path in self.made:
            with self.subTest(path=path):
                self.assertTrue(is_non_reporting_process([path]))

    def test_a_relative_scratch_script_is_detected(self):
        """A one-off is usually run as `python ledger.py` from inside /tmp, so
        the path has to be resolved before it is classified.

        Really chdir rather than mock realpath — a mocked resolver would pass
        even if the predicate never resolved anything.
        """
        path = self.made[0]
        with chdir(os.path.dirname(path)):
            self.assertTrue(is_non_reporting_process([os.path.basename(path)]))

    def test_a_console_script_name_in_a_scratch_cwd_still_reports(self):
        """The regression this rule nearly introduced.

        `gunicorn` and `celery` are resolved from PATH, so argv[0] has no
        separator and realpath() resolves it against the cwd. A worker whose
        cwd is a scratch directory would have been read as a one-off and gone
        silent — the exact failure NON_REPORTING_COMMANDS' own comment calls
        "much the worse failure". Requiring argv[0] to be a real file is what
        keeps it reporting.
        """
        with chdir(os.path.dirname(self.made[0])):
            self.assertFalse(is_non_reporting_process(["gunicorn", "--bind", "0.0.0.0:8000"]))
            self.assertFalse(is_non_reporting_process(["celery", "-A", "owdb_django", "worker"]))

    def test_manage_py_in_a_real_scratch_checkout_still_reports(self):
        """A checkout can live in a scratch directory and a management command
        is an unattended entrypoint wherever it runs from."""
        with tempfile.TemporaryDirectory(dir=self.scratch_dirs[0]) as clone:
            manage = os.path.join(clone, "manage.py")
            with open(manage, "w"):
                pass
            self.assertFalse(is_non_reporting_process([manage, "migrate"]))
            # ...but the denylist still bites there.
            self.assertTrue(is_non_reporting_process([manage, "shell"]))

    def test_the_prefixes_carry_a_trailing_separator(self):
        """This is what stops /tmpfiles matching /tmp. Asserted directly: a
        lookalike directory cannot be created at the filesystem root."""
        for prefix in _SCRATCH_DIR_PREFIXES:
            with self.subTest(prefix=prefix):
                self.assertTrue(prefix.endswith(os.sep))

    def test_an_embedded_interpreter_in_a_scratch_cwd_still_reports(self):
        """realpath("") is the cwd, so the scratch check has to come after the
        empty-argv cases or a web server started from /tmp goes quiet."""
        with chdir(self.scratch_dirs[0]):
            self.assertFalse(is_non_reporting_process([""]))
            self.assertFalse(is_non_reporting_process([]))


class SentryEnabledSettingTest(SimpleTestCase):
    """settings.py actually consults the predicate — the guard is wired, not just defined."""

    #: Imports settings.py and prints the decision it reached. Nothing else:
    #: the point is that SENTRY_ENABLED is computed, not hardcoded.
    PROBE = "import django\nfrom django.conf import settings\nprint(settings.SENTRY_ENABLED)\n"

    @staticmethod
    def _a_non_scratch_dir():
        """A writable directory the scratch-script rule does not match.

        BASE_DIR is the natural choice but cannot be assumed: in the production
        image /app is root-owned and the app runs as appuser, and a throwaway
        clone puts BASE_DIR itself inside /tmp — which would invert the probe
        and fail for a reason that has nothing to do with the guard. Fall back
        to $HOME, then skip rather than report a misleading failure.
        """
        for candidate in (str(ambient_settings.BASE_DIR), os.path.expanduser("~")):
            resolved = os.path.realpath(candidate)
            # Compare prefixes directly. _is_scratch_script() is the wrong tool
            # here: it requires argv[0] to be an existing file, so asking it
            # about a probe path that has not been written yet always says
            # "not scratch" and would hand back a scratch directory.
            if (resolved.rstrip(os.sep) + os.sep).startswith(_SCRATCH_DIR_PREFIXES):
                continue
            if os.access(resolved, os.W_OK):
                return resolved
        raise SkipTest("no writable directory outside /tmp, /var/tmp or /dev/shm")

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

        The probe dir sits outside every scratch prefix on purpose. Until
        ROS-4038 this used tempfile's default of /tmp, which the scratch-script
        rule now reads as an operator session — the child would print False and
        this test would fail for the right reason but in a confusing place.
        """
        self.assertEqual(self._sentry_enabled_in_a_child(self._a_non_scratch_dir()), "True")

    def test_a_script_in_a_scratch_dir_disables_sentry(self):
        """The ROS-4037 shape, end to end: the same probe run from /tmp comes
        back False.

        Paired with the test above, this pins the rule rather than the probe's
        own location — one script, two directories, two answers. This is the
        assertion a static argv table cannot make: it proves the *shipped*
        settings.py silences a real scratch script in a real child process.
        """
        self.assertEqual(self._sentry_enabled_in_a_child("/tmp"), "False")
