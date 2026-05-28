# Generated manually to sync Django state with existing database tables
# These M2M tables were created outside of migrations and need to be registered

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0014_add_tvshow_model_and_event_episode_fields'),
    ]

    # These operations are NO-OPS since the tables already exist
    # We're just telling Django that these fields exist in the database
    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='podcastepisode',
                    name='discussed_events',
                    field=models.ManyToManyField(
                        blank=True,
                        help_text='Events discussed in this episode',
                        related_name='podcast_discussions',
                        to='owdbapp.event'
                    ),
                ),
            ],
            database_operations=[],  # Table already exists
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='podcastepisode',
                    name='discussed_matches',
                    field=models.ManyToManyField(
                        blank=True,
                        help_text='Matches discussed in this episode',
                        related_name='podcast_discussions',
                        to='owdbapp.match'
                    ),
                ),
            ],
            database_operations=[],  # Table already exists
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='videogame',
                    name='wrestlers',
                    field=models.ManyToManyField(
                        blank=True,
                        help_text="Wrestlers featured in this game's roster",
                        related_name='video_games',
                        to='owdbapp.wrestler'
                    ),
                ),
            ],
            database_operations=[],  # Table already exists
        ),
    ]
