"""
API keys are stored as SHA-256 digests, never in plaintext (migration 0033).

Covers the whole life of a key: an existing plaintext key surviving the
migration and still authenticating, a wrong key getting 401, the account
page showing a new key exactly once and only its prefix afterward, and no
copy of the raw key anywhere in the table.
"""

import hashlib

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from owdb_django.owdbapp.models import APIKey, UserProfile

from .proxied_client import proxied_client

BEFORE = ("owdbapp", "0032_episode_name_hyphen_separator")
AFTER = ("owdbapp", "0033_apikey_hash_at_rest")


def _sha256(raw_key):
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _apikey_columns():
    table = APIKey._meta.db_table
    with connection.cursor() as cursor:
        return {col.name for col in connection.introspection.get_table_description(cursor, table)}


def _raw_key_in_table(raw_key):
    """True when any text column of any APIKey row contains ``raw_key``."""
    table = connection.ops.quote_name(APIKey._meta.db_table)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table}")  # noqa: S608, table name is ours
        for row in cursor.fetchall():
            for value in row:
                if isinstance(value, str) and raw_key in value:
                    return True
    return False


def _migrate(target):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate([target])
    return executor.loader.project_state([target]).apps


class ApiKeyHashMigrationTest(TransactionTestCase):
    """A key issued before 0033, when it was stored in plaintext, keeps
    working after the migration hashes it, and the plaintext is gone."""

    raw_key = "0123456789abcdef0123456789abcdef01234567"

    def setUp(self):
        cache.clear()
        old_apps = _migrate(BEFORE)
        OldUser = old_apps.get_model("auth", "User")
        OldAPIKey = old_apps.get_model("owdbapp", "APIKey")
        owner = OldUser.objects.create(username="legacyowner", password="!")
        OldAPIKey.objects.create(user=owner, key=self.raw_key, name="Legacy")
        _migrate(AFTER)

    def tearDown(self):
        # Leave the schema at the latest migration for whatever runs next.
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_existing_key_is_hashed_and_plaintext_is_gone(self):
        api_key = APIKey.objects.get(name="Legacy")
        self.assertEqual(api_key.key_hash, _sha256(self.raw_key))
        self.assertEqual(api_key.prefix, self.raw_key[:8])
        self.assertNotIn("key", _apikey_columns())
        self.assertFalse(_raw_key_in_table(self.raw_key))

    def test_existing_key_still_authenticates_after_migration(self):
        client = proxied_client()
        response = client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=self.raw_key)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(APIKey.objects.get(name="Legacy").requests_total, 1)

    def test_wrong_key_gets_401_after_migration(self):
        client = proxied_client()
        # Same 8-character prefix as the real key, wrong after that.
        wrong = self.raw_key[:8] + "f" * 32
        response = client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=wrong)
        self.assertEqual(response.status_code, 401)

    def test_migration_reverses_in_schema_but_not_plaintext(self):
        """Rolling back restores the ``key`` column (NOT NULL, UNIQUE) but
        can't restore the key, so the row gets an unusable placeholder."""
        old_apps = _migrate(BEFORE)
        self.assertIn("key", _apikey_columns())
        self.assertNotIn("key_hash", _apikey_columns())
        restored = old_apps.get_model("owdbapp", "APIKey").objects.get(name="Legacy")
        self.assertTrue(restored.key.startswith("unrecoverable-"))
        self.assertNotEqual(restored.key, self.raw_key)


class ApiKeyStorageTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="hashowner", password="x")

    def test_create_key_stores_digest_and_prefix_only(self):
        api_key, raw_key = APIKey.create_key(self.user, name="CLI")
        api_key.refresh_from_db()
        self.assertEqual(api_key.key_hash, _sha256(raw_key))
        self.assertEqual(api_key.prefix, raw_key[:8])
        self.assertEqual(len(raw_key), 40)
        self.assertFalse(_raw_key_in_table(raw_key))

    def test_new_key_authenticates_and_wrong_key_gets_401(self):
        _, raw_key = APIKey.create_key(self.user)
        client = proxied_client()
        ok = client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=raw_key)
        self.assertEqual(ok.status_code, 200)
        # Presenting the stored digest itself must not work either.
        digest = client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=_sha256(raw_key))
        self.assertEqual(digest.status_code, 401)
        wrong = client.get(reverse("api-wrestler-list"), HTTP_X_API_KEY=raw_key[:-1] + "x")
        self.assertEqual(wrong.status_code, 401)


class AccountPageShowsKeyOnceTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="keyviewer", email="kv@example.com", password="testpassword123"
        )
        UserProfile.objects.create(user=self.user)
        self.client.login(username="keyviewer", password="testpassword123")

    def _create(self):
        response = self.client.post(reverse("account"), {"action": "create", "key_name": "Bot"})
        self.assertEqual(response.status_code, 200)
        return response

    def test_creation_response_shows_the_full_key_once(self):
        response = self._create()
        raw_key = response.context["new_api_key"]
        self.assertEqual(len(raw_key), 40)
        self.assertContains(response, raw_key)
        self.assertContains(response, "one time you'll see the full key")
        self.assertIn("no-store", response["Cache-Control"])
        self.assertEqual(APIKey.objects.get(user=self.user).key_hash, _sha256(raw_key))

    def test_later_views_show_only_the_prefix(self):
        raw_key = self._create().context["new_api_key"]
        response = self.client.get(reverse("account"))
        self.assertIsNone(response.context["new_api_key"])
        self.assertNotContains(response, raw_key)
        self.assertContains(response, raw_key[:8])
        # A second, unrelated POST doesn't bring the first key back either.
        response = self.client.post(reverse("account"), {"action": "create"})
        self.assertNotContains(response, raw_key)
        self.assertContains(response, raw_key[:8])

    def test_admin_list_shows_only_the_prefix_and_blocks_add(self):
        raw_key = self._create().context["new_api_key"]
        User.objects.create_superuser(username="boss", email="b@example.com", password="pw")
        self.client.login(username="boss", password="pw")
        changelist = self.client.get(reverse("admin:owdbapp_apikey_changelist"))
        self.assertEqual(changelist.status_code, 200)
        self.assertNotContains(changelist, raw_key)
        self.assertContains(changelist, raw_key[:8])
        add = self.client.get(reverse("admin:owdbapp_apikey_add"))
        self.assertEqual(add.status_code, 403)
