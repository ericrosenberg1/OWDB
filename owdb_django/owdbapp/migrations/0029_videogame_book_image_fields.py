"""Add cover-image fields to VideoGame and Book.

Until this migration both models lacked the standard image_* group used by
Wrestler / Promotion / Event / etc. — so the cascade in wrestlebot.pipeline.images
couldn't be wired to them. Adding the fields is non-destructive (ADD COLUMN on
SQLite + Postgres) so it's safe to run while other writes are in flight.

Same six-field shape as Wrestler so the cascade + Earl rules + ImageCacheService
work uniformly:

  image_url           — the displayable URL (CDN or upstream)
  image_source_url    — Commons file-page URL for the legal-review trail
  image_original_url  — full-resolution upstream URL (preserved verbatim)
  image_license       — normalized OWDB code: cc0 / pd / cc-by / cc-by-sa
  image_credit        — attribution + Commons file-page URL + fair-use notice
                        (for promotion-class entities; not applied here)
  image_fetched_at    — when the cascade last successfully assigned

All nullable / blank so the schema change requires no data backfill.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("owdbapp", "0028_event_verification_state_match_verification_state_and_more"),
    ]

    operations = [
        # ---- VideoGame ------------------------------------------------------
        migrations.AddField(
            model_name="videogame",
            name="image_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="videogame",
            name="image_source_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                null=True,
                help_text="Commons file-page URL (legal trail).",
            ),
        ),
        migrations.AddField(
            model_name="videogame",
            name="image_original_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="videogame",
            name="image_license",
            field=models.CharField(
                blank=True, max_length=50, null=True, help_text="Normalized OWDB license code."
            ),
        ),
        migrations.AddField(
            model_name="videogame",
            name="image_credit",
            field=models.CharField(
                blank=True, max_length=500, null=True, help_text="Attribution + Commons file URL."
            ),
        ),
        migrations.AddField(
            model_name="videogame",
            name="image_fetched_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        # ---- Book ----------------------------------------------------------
        migrations.AddField(
            model_name="book",
            name="image_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="image_source_url",
            field=models.URLField(
                blank=True,
                max_length=500,
                null=True,
                help_text="Commons file-page URL (legal trail).",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="image_original_url",
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name="book",
            name="image_license",
            field=models.CharField(
                blank=True, max_length=50, null=True, help_text="Normalized OWDB license code."
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="image_credit",
            field=models.CharField(
                blank=True, max_length=500, null=True, help_text="Attribution + Commons file URL."
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="image_fetched_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
