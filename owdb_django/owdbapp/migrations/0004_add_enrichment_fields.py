# Generated migration for enrichment and completeness fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0003_add_image_fields_to_models'),
    ]

    operations = [
        # Wrestler enrichment fields
        migrations.AddField(
            model_name='wrestler',
            name='wikipedia_url',
            field=models.URLField(blank=True, help_text='Wikipedia article URL for this wrestler', max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='last_enriched',
            field=models.DateTimeField(blank=True, help_text='When data was last enriched from external sources', null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='birth_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='height',
            field=models.CharField(blank=True, help_text="e.g., 6'2\" or 188 cm", max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='weight',
            field=models.CharField(blank=True, help_text='e.g., 250 lbs or 113 kg', max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='trained_by',
            field=models.TextField(blank=True, help_text='Comma-separated list of trainers', null=True),
        ),
        migrations.AddField(
            model_name='wrestler',
            name='signature_moves',
            field=models.TextField(blank=True, help_text='Signature moves (not finishers)', null=True),
        ),
        # Promotion enrichment fields
        migrations.AddField(
            model_name='promotion',
            name='wikipedia_url',
            field=models.URLField(blank=True, help_text='Wikipedia article URL', max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='last_enriched',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='headquarters',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='promotion',
            name='founder',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
