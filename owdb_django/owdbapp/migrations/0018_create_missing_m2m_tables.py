"""
Create three M2M tables that migration 0015 marked as "table already exists"
because they did exist in the legacy production postgres database. On a fresh
SQLite (or any clean install), those tables don't exist and Django queries
that touch them crash.

This migration creates them if missing. Idempotent via IF NOT EXISTS — safe
to run on environments where they already exist.
"""

from django.db import migrations


CREATE_PODCASTEPISODE_DISCUSSED_EVENTS = """
CREATE TABLE IF NOT EXISTS "owdbapp_podcastepisode_discussed_events" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "podcastepisode_id" bigint NOT NULL REFERENCES "owdbapp_podcastepisode" ("id") DEFERRABLE INITIALLY DEFERRED,
    "event_id" bigint NOT NULL REFERENCES "owdbapp_event" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("podcastepisode_id", "event_id")
);
"""

CREATE_PODCASTEPISODE_DISCUSSED_MATCHES = """
CREATE TABLE IF NOT EXISTS "owdbapp_podcastepisode_discussed_matches" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "podcastepisode_id" bigint NOT NULL REFERENCES "owdbapp_podcastepisode" ("id") DEFERRABLE INITIALLY DEFERRED,
    "match_id" bigint NOT NULL REFERENCES "owdbapp_match" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("podcastepisode_id", "match_id")
);
"""

CREATE_VIDEOGAME_WRESTLERS = """
CREATE TABLE IF NOT EXISTS "owdbapp_videogame_wrestlers" (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "videogame_id" bigint NOT NULL REFERENCES "owdbapp_videogame" ("id") DEFERRABLE INITIALLY DEFERRED,
    "wrestler_id" bigint NOT NULL REFERENCES "owdbapp_wrestler" ("id") DEFERRABLE INITIALLY DEFERRED,
    UNIQUE ("videogame_id", "wrestler_id")
);
"""

REVERSE_NOOP = "SELECT 1"


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0017_match_cagematch_match_id_match_last_verified_and_more'),
    ]

    operations = [
        migrations.RunSQL(CREATE_PODCASTEPISODE_DISCUSSED_EVENTS, REVERSE_NOOP),
        migrations.RunSQL(CREATE_PODCASTEPISODE_DISCUSSED_MATCHES, REVERSE_NOOP),
        migrations.RunSQL(CREATE_VIDEOGAME_WRESTLERS, REVERSE_NOOP),
    ]
