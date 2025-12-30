"""
WrestleBot 2.0 Models - Activity Tracking and Configuration

These models track all WrestleBot actions for auditing and provide
runtime configuration without requiring restarts.
"""

from django.db import models
from django.utils import timezone


class WrestleBotActivity(models.Model):
    """
    Tracks all WrestleBot actions for auditing and statistics.

    Every discovery, enrichment, and verification action is logged here
    so administrators can see what the bot is doing and revert if needed.
    """
    ACTION_TYPES = [
        ('discover', 'Discovered new entry'),
        ('enrich', 'Enriched existing entry'),
        ('verify', 'Verified data accuracy'),
        ('image', 'Added/updated image'),
        ('error', 'Error occurred'),
    ]

    ENTITY_TYPES = [
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
    ]

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, db_index=True)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPES, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)
    entity_name = models.CharField(max_length=255)

    # Source of the data
    source = models.CharField(
        max_length=100,
        help_text="Data source (e.g., wikipedia, cagematch, claude_api)"
    )

    # What was changed - stored as JSON
    details = models.JSONField(
        default=dict,
        help_text="Details of what was added/changed"
    )

    # Tracking
    ai_assisted = models.BooleanField(
        default=False,
        help_text="Whether Claude API was used"
    )
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default='')

    # Performance tracking
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="How long the operation took in milliseconds"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action_type', 'created_at']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['source', 'created_at']),
            models.Index(fields=['ai_assisted', 'created_at']),
        ]
        verbose_name = "WrestleBot Activity"
        verbose_name_plural = "WrestleBot Activities"

    def __str__(self):
        return f"{self.action_type}: {self.entity_type} #{self.entity_id} ({self.entity_name})"

    @classmethod
    def log_activity(
        cls,
        action_type: str,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        source: str,
        details: dict = None,
        ai_assisted: bool = False,
        success: bool = True,
        error_message: str = '',
        duration_ms: int = None,
    ) -> 'WrestleBotActivity':
        """
        Convenience method to log an activity.

        Example:
            WrestleBotActivity.log_activity(
                action_type='enrich',
                entity_type='wrestler',
                entity_id=123,
                entity_name='John Cena',
                source='wikipedia',
                details={'added_fields': ['bio', 'hometown']},
            )
        """
        return cls.objects.create(
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            source=source,
            details=details or {},
            ai_assisted=ai_assisted,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    @classmethod
    def get_stats(cls, hours: int = 24) -> dict:
        """Get activity statistics for the last N hours."""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        activities = cls.objects.filter(created_at__gte=cutoff)

        return {
            'total': activities.count(),
            'by_action': dict(
                activities.values('action_type')
                .annotate(count=models.Count('id'))
                .values_list('action_type', 'count')
            ),
            'by_entity': dict(
                activities.values('entity_type')
                .annotate(count=models.Count('id'))
                .values_list('entity_type', 'count')
            ),
            'by_source': dict(
                activities.values('source')
                .annotate(count=models.Count('id'))
                .values_list('source', 'count')
            ),
            'success_rate': (
                activities.filter(success=True).count() / activities.count() * 100
                if activities.exists() else 100
            ),
            'ai_assisted_count': activities.filter(ai_assisted=True).count(),
        }


class WrestleBotConfig(models.Model):
    """
    Runtime configuration for WrestleBot.

    Allows administrators to change bot behavior without restarts.
    Settings are stored as key-value pairs with JSON values.
    """
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.JSONField(help_text="Configuration value (JSON)")
    description = models.TextField(blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['key']
        verbose_name = "WrestleBot Config"
        verbose_name_plural = "WrestleBot Configs"

    def __str__(self):
        return f"{self.key} = {self.value}"

    # Default configuration values
    DEFAULTS = {
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

    @classmethod
    def get(cls, key: str, default=None):
        """
        Get a configuration value by key.

        If the key doesn't exist, returns the default from DEFAULTS
        or the provided default parameter.
        """
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            if key in cls.DEFAULTS:
                return cls.DEFAULTS[key]['value']
            return default

    @classmethod
    def set(cls, key: str, value, description: str = None):
        """Set a configuration value."""
        config, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description or cls.DEFAULTS.get(key, {}).get('description', ''),
            }
        )
        return config

    @classmethod
    def get_all(cls) -> dict:
        """Get all configuration values with defaults filled in."""
        config = {}

        # Start with defaults
        for key, data in cls.DEFAULTS.items():
            config[key] = data['value']

        # Override with database values
        for obj in cls.objects.all():
            config[obj.key] = obj.value

        return config

    @classmethod
    def is_enabled(cls) -> bool:
        """Quick check if WrestleBot is enabled."""
        return cls.get('enabled', True)

    @classmethod
    def is_ai_enabled(cls) -> bool:
        """Quick check if AI enhancement is enabled."""
        return cls.get('ai_enabled', False)

    @classmethod
    def initialize_defaults(cls):
        """
        Initialize all default configuration values in the database.

        Call this from a migration or management command.
        """
        for key, data in cls.DEFAULTS.items():
            cls.objects.get_or_create(
                key=key,
                defaults={
                    'value': data['value'],
                    'description': data.get('description', ''),
                }
            )


class WrestleBotStats(models.Model):
    """
    Daily statistics snapshot for WrestleBot.

    Captures daily metrics for tracking bot performance over time.
    """
    date = models.DateField(unique=True, db_index=True)

    # Activity counts
    discoveries = models.PositiveIntegerField(default=0)
    enrichments = models.PositiveIntegerField(default=0)
    images_added = models.PositiveIntegerField(default=0)
    verifications = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)

    # API usage
    wikipedia_calls = models.PositiveIntegerField(default=0)
    cagematch_calls = models.PositiveIntegerField(default=0)
    wikimedia_calls = models.PositiveIntegerField(default=0)
    claude_api_calls = models.PositiveIntegerField(default=0)

    # Performance
    total_duration_ms = models.PositiveIntegerField(default=0)
    average_score_improvement = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date']
        verbose_name = "WrestleBot Daily Stats"
        verbose_name_plural = "WrestleBot Daily Stats"

    def __str__(self):
        return f"WrestleBot Stats {self.date}"

    @classmethod
    def get_or_create_today(cls) -> 'WrestleBotStats':
        """Get or create today's stats record."""
        today = timezone.now().date()
        stats, _ = cls.objects.get_or_create(date=today)
        return stats

    def increment(self, field: str, amount: int = 1):
        """Increment a counter field."""
        current = getattr(self, field, 0)
        setattr(self, field, current + amount)
        self.save(update_fields=[field, 'updated_at'])
