# Generated manually for WrestleBot app consolidation
# This migration removes WrestleBot models from owdbapp state
# without actually deleting the database tables

from django.db import migrations


class Migration(migrations.Migration):
    """
    Remove WrestleBot models from owdbapp's migration state.

    The models have been moved to the owdb_django.wrestlebot app.
    The actual database tables remain unchanged since wrestlebot app
    uses db_table to point to the same tables.

    This is a state-only operation that syncs Django's migration state
    with the new app structure.
    """

    dependencies = [
        ('owdbapp', '0015_fix_existing_m2m_fields'),
    ]

    operations = [
        # These are state-only operations - they update Django's migration
        # state without touching the actual database tables
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel(name='WrestleBotActivity'),
                migrations.DeleteModel(name='WrestleBotConfig'),
                migrations.DeleteModel(name='WrestleBotStats'),
            ],
            database_operations=[
                # No database operations - tables stay as-is
            ],
        ),
    ]
