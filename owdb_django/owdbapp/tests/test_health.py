"""Tests for the health endpoints.

ROS-1204 was a write-path outage that lasted six weeks because the health
endpoint only ever ran `SELECT 1`, which reads straight through it. ROS-1207
fixed the container healthcheck so it actually reached the view. These tests
cover the other half: making the view itself notice.
"""

import os
import sqlite3
import tempfile
import unittest
from unittest import mock

from django.db import OperationalError, connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .. import views
from ..checks import sqlite_db_directory


class HealthCheckTest(TestCase):
    """The cheap liveness probe at /health/ — what Docker hits every 30s."""

    def setUp(self):
        self.client = Client()

    def test_healthy(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        # Kept for anything already parsing the old response shape.
        self.assertEqual(data["database"], "connected")
        self.assertEqual(data["checks"]["database"], "connected")

    def test_unhealthy_when_sqlite_directory_is_not_writable(self):
        """The ROS-1204 shape: DB reads fine, DB directory rejects writes."""
        with mock.patch.object(
            views,
            "_check_sqlite_dir_writable",
            return_value=(False, "/app is not writable by uid 1000"),
        ):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 503)
        data = response.json()
        self.assertEqual(data["status"], "unhealthy")
        self.assertIn("not writable", data["error"])

    def test_does_not_write(self):
        """The liveness probe must stay cheap — no write, no lock.

        If this ever starts writing it belongs on /health/ready/ instead: the
        container healthcheck runs it every 30s, and anything that can flap
        under load becomes a restart loop the moment autoheal watches it.
        """
        with mock.patch.object(
            views, "_check_write_transaction", side_effect=AssertionError("wrote")
        ):
            response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)


@unittest.skipIf(os.getuid() == 0, "root bypasses directory permissions")
class SqliteDirectoryWritableTest(TestCase):
    """Reproduce ROS-1204 on a throwaway DB and prove each probe's verdict."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, "db.sqlite3")
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE t (x integer)")
        conn.execute("INSERT INTO t VALUES (1)")
        conn.commit()
        conn.close()

    def tearDown(self):
        os.chmod(self.tmpdir, 0o755)

    def _override(self):
        return override_settings(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": self.db_path,
                }
            }
        )

    def test_select_1_passes_through_the_failure(self):
        """Why `SELECT 1` was never enough — it succeeds on a dead write path."""
        os.chmod(self.tmpdir, 0o555)
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        try:
            self.assertEqual(conn.execute("SELECT 1").fetchone()[0], 1)
            # So does taking the write lock — SQLite only fails once it goes to
            # create the journal, so a lock-only probe is just as blind.
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("ROLLBACK")
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("INSERT INTO t VALUES (2)")
        finally:
            conn.close()

    def test_directory_check_catches_it(self):
        os.chmod(self.tmpdir, 0o555)
        with self._override():
            ok, detail = views._check_sqlite_dir_writable()
        self.assertFalse(ok)
        self.assertIn("not writable", detail)

    def test_directory_check_passes_when_writable(self):
        with self._override():
            ok, detail = views._check_sqlite_dir_writable()
        self.assertTrue(ok)
        self.assertEqual(detail, "writable")

    def test_directory_check_is_skipped_on_postgres(self):
        with override_settings(
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.postgresql",
                    "NAME": "owdb",
                }
            }
        ):
            ok, detail = views._check_sqlite_dir_writable()
        self.assertTrue(ok)
        self.assertEqual(detail, "n/a (no on-disk sqlite file)")


class SqliteDbDirectoryTest(TestCase):
    """The shared helper behind both owdbapp.E001 and /health/."""

    def test_in_memory_databases_have_no_directory(self):
        """Django's test runner uses a URI, not ``:memory:``.

        Treating ``file:memorydb_default?mode=memory&cache=shared`` as a path
        resolves it against the cwd, so owdbapp.E001 fired and aborted the
        whole suite the first time the tests ran with a read-only cwd.
        """
        for name in (
            ":memory:",
            "file:memorydb_default?mode=memory&cache=shared",
            "",
        ):
            with self.subTest(name=name):
                self.assertIsNone(
                    sqlite_db_directory({"ENGINE": "django.db.backends.sqlite3", "NAME": name})
                )

    def test_on_disk_database_returns_its_directory(self):
        self.assertEqual(
            sqlite_db_directory(
                {"ENGINE": "django.db.backends.sqlite3", "NAME": "/app/data/db.sqlite3"}
            ),
            "/app/data",
        )

    def test_non_sqlite_engine_returns_none(self):
        self.assertIsNone(
            sqlite_db_directory({"ENGINE": "django.db.backends.postgresql", "NAME": "owdb"})
        )


class HealthReadyTest(TestCase):
    """The deep readiness probe at /health/ready/ — humans and monitoring."""

    def setUp(self):
        self.client = Client()

    def test_ready(self):
        response = self.client.get(reverse("health_ready"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["checks"]["database"], "connected")
        self.assertEqual(data["checks"]["database_write"], "ok")

    def test_write_probe_leaves_nothing_behind(self):
        ok, _ = views._check_write_transaction()
        self.assertTrue(ok)
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = %s",
                [views._WRITE_PROBE_TABLE],
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_write_probe_reports_failure(self):
        with mock.patch.object(
            views.connection,
            "cursor",
            side_effect=OperationalError("attempt to write a readonly database"),
        ):
            ok, detail = views._check_write_transaction()
        self.assertFalse(ok)
        self.assertIn("readonly", detail)

    def test_busy_database_is_not_reported_unhealthy(self):
        """Lock contention means writes work — the opposite of the failure.

        Reporting it unhealthy is the false negative that makes a strict probe
        dangerous, so it is explicitly downgraded.
        """
        with mock.patch.object(
            views.connection, "cursor", side_effect=OperationalError("database is locked")
        ):
            ok, detail = views._check_write_transaction()
        self.assertTrue(ok)
        self.assertIn("busy", detail)

    def test_unhealthy_when_write_fails(self):
        with mock.patch.object(
            views,
            "_check_write_transaction",
            return_value=(False, "attempt to write a readonly database"),
        ):
            response = self.client.get(reverse("health_ready"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "unhealthy")


class HealthReadyRedirectExemptTest(TestCase):
    """/health/ready/ is reached over plain HTTP inside the network too.

    Without an exemption SecurityMiddleware 301s it before the view runs and
    the verdict never reaches the caller — the ROS-1207 failure, one path over.
    """

    def setUp(self):
        self.client = Client()

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_REDIRECT_EXEMPT=[r"^health/$", r"^health/ready/$"],
    )
    def test_health_ready_is_not_ssl_redirected(self):
        response = self.client.get("/health/ready/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    @override_settings(
        SECURE_SSL_REDIRECT=True,
        SECURE_REDIRECT_EXEMPT=[r"^health/$", r"^health/ready/$"],
    )
    def test_other_paths_still_ssl_redirect(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 301)
