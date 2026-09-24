"""Store API keys as SHA-256 digests and drop the plaintext column.

Forward: add ``key_hash`` and ``prefix``, hash every existing key into
``key_hash``, copy its first 8 characters into ``prefix``, null the
plaintext, then drop the ``key`` column and its index. Every key a user
already holds keeps working, because authentication now hashes the
``X-API-Key`` header and looks the digest up.

Reverse: the schema comes back (``key`` column and index restored,
``key_hash`` and ``prefix`` dropped), but the plaintext keys do NOT. A
SHA-256 digest can't be turned back into the key. Each row gets a fresh,
random, never-shown placeholder in ``key`` so the old NOT NULL and UNIQUE
constraints hold, which means every existing key stops working on a
rollback and its owner has to create a new one from the account page.
Restoring the old keys takes a database backup from before this migration.
"""

import hashlib
import secrets

from django.db import migrations, models


def hash_existing_keys(apps, schema_editor):
    APIKey = apps.get_model("owdbapp", "APIKey")
    for api_key in APIKey.objects.exclude(key__isnull=True).iterator():
        raw_key = api_key.key
        api_key.key_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        api_key.prefix = raw_key[:8]
        api_key.key = None
        api_key.save(update_fields=["key_hash", "prefix", "key"])


def refill_placeholder_keys(apps, schema_editor):
    # The plaintext is gone for good. Fill the restored column with random
    # values nobody holds so the schema's NOT NULL / UNIQUE constraints are
    # satisfied again. See the module docstring.
    APIKey = apps.get_model("owdbapp", "APIKey")
    for api_key in APIKey.objects.filter(key__isnull=True).iterator():
        api_key.key = "unrecoverable-" + secrets.token_hex(20)
        api_key.save(update_fields=["key"])


class Migration(migrations.Migration):
    dependencies = [
        ("owdbapp", "0032_episode_name_hyphen_separator"),
    ]

    operations = [
        migrations.AddField(
            model_name="apikey",
            name="key_hash",
            field=models.CharField(
                help_text="SHA-256 hex digest of the key",
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="prefix",
            field=models.CharField(
                blank=True, default="", help_text="First characters, for display", max_length=8
            ),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="key",
            field=models.CharField(db_index=True, max_length=64, null=True, unique=True),
        ),
        migrations.RunPython(hash_existing_keys, refill_placeholder_keys),
        migrations.AlterField(
            model_name="apikey",
            name="key_hash",
            field=models.CharField(
                help_text="SHA-256 hex digest of the key", max_length=64, unique=True
            ),
        ),
        migrations.RemoveIndex(
            model_name="apikey",
            name="owdbapp_api_key_c57e64_idx",
        ),
        migrations.RemoveField(
            model_name="apikey",
            name="key",
        ),
    ]
