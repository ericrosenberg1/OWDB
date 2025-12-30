# Generated migration for WrestleBot 2.0

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0010_remove_wrestlebot_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='WrestleBotActivity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('action_type', models.CharField(
                    choices=[
                        ('discover', 'Discovered new entry'),
                        ('enrich', 'Enriched existing entry'),
                        ('verify', 'Verified data accuracy'),
                        ('image', 'Added/updated image'),
                        ('error', 'Error occurred'),
                    ],
                    db_index=True,
                    max_length=20
                )),
                ('entity_type', models.CharField(
                    choices=[
                        ('wrestler', 'Wrestler'),
                        ('promotion', 'Promotion'),
                        ('event', 'Event'),
                        ('title', 'Title'),
                        ('venue', 'Venue'),
                        ('match', 'Match'),
                        ('videogame', 'Video Game'),
                        ('podcast', 'Podcast'),
                        ('book', 'Book'),
                        ('special', 'Special'),
                    ],
                    db_index=True,
                    max_length=50
                )),
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
                'ordering': ['-date'],
            },
        ),
        migrations.AddIndex(
            model_name='wrestlebotactivity',
            index=models.Index(fields=['action_type', 'created_at'], name='owdbapp_wre_action__a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='wrestlebotactivity',
            index=models.Index(fields=['entity_type', 'entity_id'], name='owdbapp_wre_entity__d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='wrestlebotactivity',
            index=models.Index(fields=['source', 'created_at'], name='owdbapp_wre_source__g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='wrestlebotactivity',
            index=models.Index(fields=['ai_assisted', 'created_at'], name='owdbapp_wre_ai_assi_j0k1l2_idx'),
        ),
    ]
