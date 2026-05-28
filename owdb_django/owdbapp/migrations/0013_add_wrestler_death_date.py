# Migration to add death_date field to Wrestler model
# This enables detection of synthetic events with deceased wrestlers

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0012_initialize_wrestlebot_config'),
    ]

    operations = [
        migrations.AddField(
            model_name='wrestler',
            name='death_date',
            field=models.DateField(blank=True, help_text='Date of death if deceased', null=True),
        ),
    ]
