# Data migration to initialize WrestleBot config defaults

from django.db import migrations


def initialize_config_defaults(apps, schema_editor):
    """Create default WrestleBot configuration entries."""
    WrestleBotConfig = apps.get_model('owdbapp', 'WrestleBotConfig')

    defaults = {
        'enabled': {
            'value': True,
            'description': 'Whether WrestleBot is enabled',
        },
        'max_operations_per_hour': {
            'value': 50,
            'description': 'Maximum database operations per hour',
        },
        'ai_enabled': {
            'value': False,
            'description': 'Whether to use Claude API for AI enhancement',
        },
        'ai_max_calls_per_day': {
            'value': 100,
            'description': 'Maximum Claude API calls per day',
        },
        'priority_entities': {
            'value': ['wrestler', 'event', 'promotion'],
            'description': 'Entity types to prioritize (in order)',
        },
        'min_completeness_score': {
            'value': 40,
            'description': 'Minimum completeness score before enrichment',
        },
        'discovery_batch_size': {
            'value': 5,
            'description': 'Number of entities to discover per cycle',
        },
        'enrichment_batch_size': {
            'value': 10,
            'description': 'Number of entities to enrich per cycle',
        },
        'image_batch_size': {
            'value': 10,
            'description': 'Number of images to fetch per cycle',
        },
        'pause_between_operations_ms': {
            'value': 500,
            'description': 'Milliseconds to pause between operations',
        },
    }

    for key, data in defaults.items():
        WrestleBotConfig.objects.get_or_create(
            key=key,
            defaults={
                'value': data['value'],
                'description': data.get('description', ''),
            }
        )


def reverse_config_defaults(apps, schema_editor):
    """Remove default config entries (for reverse migration)."""
    WrestleBotConfig = apps.get_model('owdbapp', 'WrestleBotConfig')
    WrestleBotConfig.objects.filter(key__in=[
        'enabled', 'max_operations_per_hour', 'ai_enabled',
        'ai_max_calls_per_day', 'priority_entities', 'min_completeness_score',
        'discovery_batch_size', 'enrichment_batch_size', 'image_batch_size',
        'pause_between_operations_ms',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('owdbapp', '0011_wrestlebot_v2'),
    ]

    operations = [
        migrations.RunPython(
            initialize_config_defaults,
            reverse_config_defaults,
        ),
    ]
