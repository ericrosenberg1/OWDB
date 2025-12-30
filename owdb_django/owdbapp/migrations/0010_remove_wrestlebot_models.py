"""
Migration to remove WrestleBot models.

This removes the WrestleBotLog and WrestleBotConfig models that are no longer used.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0009_podcast_episodes_and_promotion_history'),
    ]

    operations = [
        migrations.DeleteModel(
            name='WrestleBotLog',
        ),
        migrations.DeleteModel(
            name='WrestleBotConfig',
        ),
    ]
