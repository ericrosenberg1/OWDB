# Generated manually for WrestleBot app consolidation
# This migration is marked as applied since tables already exist under owdbapp

from django.db import migrations


class Migration(migrations.Migration):
    """
    This is a fake initial migration for the wrestlebot app.

    The tables already exist in the database from owdbapp migrations.
    We use db_table in the models to point to the existing tables:
    - owdbapp_wrestlebotactivity
    - owdbapp_wrestlebotconfig
    - owdbapp_wrestlebotstats

    Run: python manage.py migrate wrestlebot --fake
    """

    initial = True

    dependencies = [
        ('owdbapp', '0014_add_tvshow_model_and_event_episode_fields'),
    ]

    operations = [
        # No operations - tables already exist
        # Models use db_table to point to existing owdbapp tables
    ]
