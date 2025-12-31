# Generated manually for WrestleBot app consolidation
# This migration adds WrestleBot models to wrestlebot app state
# without creating new database tables (they already exist)

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add WrestleBot models to wrestlebot app's migration state.

    The models were moved from owdbapp to wrestlebot app.
    The actual database tables already exist (owdbapp_wrestlebot*).
    We use db_table in the models to point to these existing tables.

    This is a state-only operation that syncs Django's migration state
    with the new app structure.
    """

    dependencies = [
        ('wrestlebot', '0001_initial'),
        ('owdbapp', '0016_remove_wrestlebot_from_owdbapp'),
    ]

    operations = [
        # These are state-only operations - they update Django's migration
        # state without touching the actual database tables
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='WrestleBotActivity',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                        ('action_type', models.CharField(choices=[('discover', 'Discovered new entry'), ('enrich', 'Enriched existing entry'), ('verify', 'Verified data accuracy'), ('image', 'Added/updated image'), ('error', 'Error occurred')], db_index=True, max_length=20)),
                        ('entity_type', models.CharField(choices=[('wrestler', 'Wrestler'), ('promotion', 'Promotion'), ('event', 'Event'), ('title', 'Title'), ('venue', 'Venue'), ('match', 'Match'), ('videogame', 'Video Game'), ('podcast', 'Podcast'), ('book', 'Book'), ('special', 'Special')], db_index=True, max_length=50)),
                        ('entity_id', models.PositiveIntegerField(db_index=True)),
                        ('entity_name', models.CharField(max_length=255)),
                        ('source', models.CharField(help_text='Data source (e.g., wikipedia, cagematch, claude_api)', max_length=100)),
                        ('details', models.JSONField(default=dict, help_text='Details of what was added/changed')),
                        ('ai_assisted', models.BooleanField(default=False, help_text='Whether Claude API was used')),
                        ('success', models.BooleanField(default=True)),
                        ('error_message', models.TextField(blank=True, default='')),
                        ('duration_ms', models.PositiveIntegerField(blank=True, help_text='How long the operation took in milliseconds', null=True)),
                    ],
                    options={
                        'verbose_name': 'WrestleBot Activity',
                        'verbose_name_plural': 'WrestleBot Activities',
                        'db_table': 'owdbapp_wrestlebotactivity',
                        'ordering': ['-created_at'],
                    },
                ),
                migrations.CreateModel(
                    name='WrestleBotConfig',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('key', models.CharField(db_index=True, max_length=100, unique=True)),
                        ('value', models.JSONField(help_text='Configuration value (JSON)')),
                        ('description', models.TextField(blank=True, default='')),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'verbose_name': 'WrestleBot Config',
                        'verbose_name_plural': 'WrestleBot Configs',
                        'db_table': 'owdbapp_wrestlebotconfig',
                        'ordering': ['key'],
                    },
                ),
                migrations.CreateModel(
                    name='WrestleBotStats',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('date', models.DateField(db_index=True, unique=True)),
                        ('discoveries', models.PositiveIntegerField(default=0)),
                        ('enrichments', models.PositiveIntegerField(default=0)),
                        ('images_added', models.PositiveIntegerField(default=0)),
                        ('verifications', models.PositiveIntegerField(default=0)),
                        ('errors', models.PositiveIntegerField(default=0)),
                        ('wikipedia_calls', models.PositiveIntegerField(default=0)),
                        ('cagematch_calls', models.PositiveIntegerField(default=0)),
                        ('wikimedia_calls', models.PositiveIntegerField(default=0)),
                        ('claude_api_calls', models.PositiveIntegerField(default=0)),
                        ('total_duration_ms', models.PositiveIntegerField(default=0)),
                        ('average_score_improvement', models.FloatField(default=0.0)),
                        ('created_at', models.DateTimeField(auto_now_add=True)),
                        ('updated_at', models.DateTimeField(auto_now=True)),
                    ],
                    options={
                        'verbose_name': 'WrestleBot Daily Stats',
                        'verbose_name_plural': 'WrestleBot Daily Stats',
                        'db_table': 'owdbapp_wrestlebotstats',
                        'ordering': ['-date'],
                    },
                ),
            ],
            database_operations=[
                # No database operations - tables already exist
            ],
        ),
    ]
