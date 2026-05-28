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
        db_table = 'owdbapp_wrestlebotactivity'  # Use existing table
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
        db_table = 'owdbapp_wrestlebotconfig'  # Use existing table
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
        db_table = 'owdbapp_wrestlebotstats'  # Use existing table
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


# =============================================================================
# Accuracy-First v3 Provenance Models
#
# Three append-only tables that together let us answer, for every field on
# every entity: where did this come from, when, and is it still trustworthy?
# =============================================================================


ENTITY_TYPE_CHOICES = [
    ('wrestler', 'Wrestler'),
    ('promotion', 'Promotion'),
    ('event', 'Event'),
    ('match', 'Match'),
    ('title', 'Title'),
    ('venue', 'Venue'),
    ('stable', 'Stable'),
    ('book', 'Book'),
    ('video_game', 'Video Game'),
    ('podcast', 'Podcast'),
    ('action_figure', 'Action Figure'),
    ('theme_song', 'Theme Song'),
    ('tv_show', 'TV Show'),
    ('special', 'Documentary/Special'),
    ('training_school', 'Training School'),
    ('external_ranking', 'External Ranking'),
]

SOURCE_CHOICES = [
    ('wikipedia', 'Wikipedia'),
    ('wikidata', 'Wikidata'),
    ('cagematch', 'Cagematch'),
    ('profightdb', 'ProFightDB'),
    ('profightdb_pwi_mirror', "ProFightDB's PWI ranking mirror"),
    ('tmdb', 'TMDB'),
    ('wikimedia_commons', 'Wikimedia Commons'),
    ('openlibrary', 'Open Library'),
]


class SourceFetch(models.Model):
    """
    Immutable audit log of every external source fetch.

    Every URL we fetch from any source lands here with timestamp, HTTP status,
    and the raw content. Downstream provenance records reference back to a
    SourceFetch to prove where a fact originated.

    Never updated — only inserted. Re-fetching the same URL creates a new row.
    """
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, db_index=True)
    url = models.URLField(max_length=1000)

    # Entity context — both nullable because fetches can precede entity creation
    # (e.g., we fetch a candidate name's Wikipedia page before deciding whether
    # to create the Wrestler row).
    entity_type = models.CharField(
        max_length=20, choices=ENTITY_TYPE_CHOICES,
        blank=True, null=True, db_index=True,
    )
    entity_id = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    candidate_name = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text="Name being looked up (used when entity_id is null)",
    )

    fetched_at = models.DateTimeField(auto_now_add=True, db_index=True)
    http_status = models.IntegerField()
    content_hash = models.CharField(
        max_length=64, db_index=True,
        help_text="SHA-256 of raw_content for change detection",
    )
    raw_content = models.TextField(
        blank=True,
        help_text="Raw fetched content. Stored verbatim so we can re-extract without re-fetching.",
    )

    # Stamp when this fetch was consumed by the extract pipeline.
    # Set on every attempt — success OR failure — so failing rows don't
    # recycle through JR's `used_at__isnull=True` queue forever. The
    # `extraction_outcome` column records what happened.
    used_at = models.DateTimeField(blank=True, null=True)

    EXTRACTION_OUTCOMES = [
        ("", "Not yet processed"),
        ("succeeded", "Extracted and persisted"),
        ("no_fields", "Extractor returned no fields (disambig / no infobox / unparseable)"),
        ("persist_refused", "Persister refused (e.g., empty canonical name, unresolved FK)"),
        ("no_handler", "No extractor or persister registered for entity_type"),
    ]
    extraction_outcome = models.CharField(
        max_length=30,
        blank=True,
        default="",
        choices=EXTRACTION_OUTCOMES,
        db_index=True,
        help_text="What the extract pipeline did with this fetch. Empty = not "
                  "yet processed. Set together with used_at so failures don't "
                  "re-queue.",
    )

    class Meta:
        ordering = ['-fetched_at']
        indexes = [
            models.Index(fields=['source', 'url']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['content_hash']),
        ]

    def __str__(self):
        return f"{self.source}: {self.url[:80]} @ {self.fetched_at:%Y-%m-%d %H:%M}"


class FieldProvenance(models.Model):
    """
    Per-field source attribution.

    Append-only log: when a field is (re-)written, a new row is inserted.
    To find the current source of a field, query the latest row for
    (entity_type, entity_id, field_name).
    """
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)
    field_name = models.CharField(max_length=100, db_index=True)
    value = models.TextField(help_text="String repr of the value written to the entity")

    # The actual substring of the source content that supported `value`.
    # This is the structural backbone of the accuracy guarantee — a human
    # (or Earl) can read the snippet and verify the extracted value matches.
    #
    # Originally the FieldSnippet dataclass carried this in memory but the
    # schema dropped it; codex audit 2026-05 surfaced the lie. Now persisted.
    snippet = models.TextField(
        blank=True, default="",
        help_text="The raw source-text fragment that supports `value`. "
                  "Empty only for back-filled / synthetic provenance.",
    )

    source_fetch = models.ForeignKey(
        SourceFetch, on_delete=models.PROTECT, related_name='field_provenances',
    )

    confidence = models.IntegerField(
        default=100,
        help_text="0-100. 100 = direct from infobox. Lower if derived/inferred. "
                  "Synthetic / back-filled provenance lives at 70-85.",
    )
    # `extracted_at` is the canonical name. Some legacy callers used
    # `captured_at`; we expose it as a property for backward compatibility.
    extracted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-extracted_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['entity_type', 'entity_id', 'field_name']),
        ]

    @property
    def captured_at(self):
        """Back-compat alias — was used by older agent inspection tools."""
        return self.extracted_at

    def __str__(self):
        return f"{self.entity_type}#{self.entity_id}.{self.field_name} <- {self.source_fetch.source}"


class GeneratedBio(models.Model):
    """
    Audit trail for every LLM-generated bio.

    A bio is only shown on the entity page once status='verified' — meaning
    every factual claim in the bio was matched back to a source snippet that
    was fed to the LLM.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending verification'),
        ('verified', 'Verified (all claims supported)'),
        ('rejected', 'Rejected (unsupported claims)'),
        ('superseded', 'Superseded by a newer bio'),
        ('permanently_rejected', 'Permanently rejected (max retries exhausted)'),
    ]

    GENERATION_MODES = [
        ('standard', 'Standard prompt'),
        ('strict', 'Strict prompt (no inferred combinations)'),
        ('trim', 'Trimmed: dropped unsupported sentences from a prior attempt'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)

    text = models.TextField()
    model = models.CharField(max_length=100, help_text="e.g., claude-sonnet-4-6")
    generated_at = models.DateTimeField(auto_now_add=True, db_index=True)

    # The exact source fetches that were shown to the LLM as grounding.
    source_fetches = models.ManyToManyField(SourceFetch, related_name='generated_bios')

    # Claim verification results
    claims_total = models.IntegerField(default=0)
    claims_verified = models.IntegerField(default=0)
    claims_unsupported = models.JSONField(
        default=list, blank=True,
        help_text="List of claim strings that could not be matched to a source",
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True,
    )
    rejection_reason = models.TextField(blank=True, null=True)

    # Self-correction tracking (v3.1)
    attempt_number = models.PositiveIntegerField(
        default=1,
        help_text="1-based: how many bios have been generated for this entity so far",
    )
    generation_mode = models.CharField(
        max_length=20, choices=GENERATION_MODES, default='standard',
        help_text="Which prompt variant produced this bio",
    )
    parent_bio = models.ForeignKey(
        'self', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='children',
        help_text="The previous-attempt bio this one is retrying, if any",
    )

    # Cost tracking
    input_tokens = models.IntegerField(blank=True, null=True)
    output_tokens = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id', 'status']),
            models.Index(fields=['status', 'generated_at']),
        ]

    def __str__(self):
        return f"Bio({self.entity_type}#{self.entity_id}, {self.status}, attempt {self.attempt_number})"


class EntityMention(models.Model):
    """
    A reference to another entity found inside source content.

    Wikipedia source paragraphs contain `<a href="/wiki/X">Y</a>` links —
    every one is a candidate cross-link. This table captures them all so
    the pipeline can later (a) auto-discover linked entities to fetch,
    (b) resolve mentions to persisted entities, and (c) build the wrestler-
    promotion-venue graph organically without a curator.

    Resolution is a separate step; rows start unresolved.
    """
    MENTION_CONTEXTS = [
        ("wrestler_about", "Wrestler bio source"),
        ("promotion_about", "Promotion bio source"),
        ("event_about", "Event description"),
    ]

    # Where this mention was found.
    source_fetch = models.ForeignKey(
        SourceFetch, on_delete=models.CASCADE, related_name='entity_mentions',
    )
    source_entity_type = models.CharField(
        max_length=20, choices=ENTITY_TYPE_CHOICES, db_index=True,
        help_text="The entity whose source text contained the mention.",
    )
    source_entity_id = models.PositiveIntegerField(db_index=True)

    # The mention itself.
    mention_text = models.CharField(
        max_length=255,
        help_text="The visible text of the link (e.g. 'Stampede Wrestling').",
    )
    wiki_link = models.CharField(
        max_length=500, db_index=True,
        help_text="The /wiki/X target (URL-decoded), e.g. 'Stampede_Wrestling'.",
    )
    context = models.CharField(
        max_length=30, choices=MENTION_CONTEXTS, default="wrestler_about",
    )

    # Resolution (set when the linked entity is identified).
    resolved_entity_type = models.CharField(
        max_length=20, choices=ENTITY_TYPE_CHOICES, blank=True, null=True, db_index=True,
    )
    resolved_entity_id = models.PositiveIntegerField(blank=True, null=True, db_index=True)
    resolved_at = models.DateTimeField(blank=True, null=True)

    extracted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-extracted_at']
        indexes = [
            models.Index(fields=['source_entity_type', 'source_entity_id']),
            models.Index(fields=['wiki_link']),
            models.Index(fields=['resolved_entity_type', 'resolved_entity_id']),
        ]
        unique_together = [
            ('source_fetch', 'wiki_link'),
        ]

    def __str__(self):
        suffix = "(resolved)" if self.resolved_entity_id else "(unresolved)"
        return f"{self.mention_text} -> {self.wiki_link} {suffix}"


# =============================================================================
# Earl — verification + self-improving auditor models
# =============================================================================


class EarlObservation(models.Model):
    """
    One thing Earl noticed during an audit pass.

    Earl runs the full consistency-check suite over every entity in the DB
    and records each issue he finds here. Pattern-detection later groups
    these by `rule_id` to spot systemic issues vs one-off flukes.

    Status moves: open -> investigating -> fixed | dismissed | escalated.
    """
    STATUS_CHOICES = [
        ("open", "Open — not yet investigated"),
        ("investigating", "Earl looking at it"),
        ("fixed", "Resolved (either auto-fix applied or human edited)"),
        ("dismissed", "Earl decided it's a false positive"),
        ("escalated", "Needs human review"),
    ]

    rule_id = models.CharField(max_length=100, db_index=True,
                               help_text="e.g. 'attendance_too_high', 'trained_by_prose_fragment'")
    severity = models.CharField(max_length=20, db_index=True,
                                help_text="warning | error")
    entity_type = models.CharField(max_length=20, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)
    entity_name = models.CharField(max_length=255, blank=True, default="")
    field_name = models.CharField(max_length=100, blank=True, default="")
    stored_value = models.TextField(blank=True, default="")
    issue_description = models.TextField(blank=True, default="")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default="open", db_index=True)
    auto_fix_applied = models.BooleanField(default=False)
    auto_fix_notes = models.TextField(blank=True, default="")

    first_seen = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(auto_now=True)
    times_seen = models.PositiveIntegerField(default=1,
                                             help_text="Increments each audit that sees this same issue")

    class Meta:
        ordering = ["-last_seen"]
        indexes = [
            models.Index(fields=["rule_id", "status"]),
            models.Index(fields=["entity_type", "entity_id", "rule_id"]),
        ]
        unique_together = [("rule_id", "entity_type", "entity_id", "field_name")]

    def __str__(self):
        return f"[{self.severity}] {self.rule_id}: {self.entity_type}#{self.entity_id}"


class RuleScore(models.Model):
    """
    Earl's running score for each rule in JR's pipeline.

    Tracks how often a rule has fired and (for rules that gate persistence)
    how often it agreed with later human review. Earl uses these scores to
    decide which rules to keep, tune, or disable.

    Rule kinds:
      - guard:        accuracy gate (e.g., subject-pattern, redirect-dedup)
      - extractor:    field extraction (e.g., wrestler.real_name)
      - cleanup:      post-extract field cleaner
      - consistency:  audit-time consistency check
    """
    KIND_CHOICES = [
        ("guard", "Accuracy guard"),
        ("extractor", "Field extractor"),
        ("cleanup", "Cleanup pass"),
        ("consistency", "Consistency rule"),
    ]

    rule_id = models.CharField(max_length=100, unique=True, db_index=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, db_index=True)
    description = models.TextField(blank=True, default="")

    times_evaluated = models.PositiveIntegerField(default=0)
    times_fired = models.PositiveIntegerField(default=0,
                                              help_text="Rule produced a non-default result")
    true_positives = models.PositiveIntegerField(default=0,
                                                  help_text="Fired and the call was correct")
    false_positives = models.PositiveIntegerField(default=0,
                                                   help_text="Fired but the call was wrong")

    enabled = models.BooleanField(default=True, db_index=True,
                                  help_text="False = Earl disabled this rule (Earl can re-enable)")
    auto_disable_threshold = models.PositiveIntegerField(default=10,
                                                         help_text="Earl auto-disables a rule that has >=N false positives unless overridden")

    last_evaluated = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, default="",
                             help_text="Earl's free-text notes about this rule")

    class Meta:
        ordering = ["rule_id"]

    @property
    def precision(self) -> float:
        fp = self.false_positives
        tp = self.true_positives
        if (tp + fp) == 0:
            return 1.0
        return tp / (tp + fp)

    def __str__(self):
        return f"{self.rule_id} ({self.kind}, {self.times_fired} fires, precision={self.precision:.2f})"


class RuleSuggestion(models.Model):
    """
    A suggested rule change Earl wants a human (or another Earl pass) to consider.

    Earl creates these when he detects a systemic pattern that current rules
    don't catch, or when a rule has high false-positive rate. Human review
    decides whether to accept and apply.
    """
    STATUS_CHOICES = [
        ("pending", "Pending human review"),
        ("accepted", "Accepted (applied or queued for apply)"),
        ("rejected", "Rejected — kept current rule"),
        ("applied", "Applied automatically"),
    ]

    target_rule_id = models.CharField(max_length=100, blank=True, default="",
                                      help_text="Existing rule to modify, or '' for a new rule")
    kind = models.CharField(max_length=20, blank=True, default="",
                            help_text="guard | extractor | cleanup | consistency")
    description = models.TextField()
    rationale = models.TextField(blank=True, default="",
                                 help_text="Why Earl thinks this change is needed (with sample observations)")
    sample_observations = models.JSONField(default=list, blank=True,
                                            help_text="EntityIDs / values that motivated the suggestion")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default="pending", db_index=True)
    proposed_at = models.DateTimeField(auto_now_add=True, db_index=True)
    resolved_at = models.DateTimeField(blank=True, null=True)
    resolution_note = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-proposed_at"]

    def __str__(self):
        return f"[{self.status}] {self.target_rule_id or 'NEW'}: {self.description[:80]}"


# =============================================================================
# Agent session logging
#
# Every agent run (JR or Earl) creates one AgentSession row. Every tool call
# the agent makes creates an AgentToolCall row. This gives complete
# transparency: we can replay any agent's decisions and reasoning.
# =============================================================================


class AgentSession(models.Model):
    """One agent run. Tracks budget, outcome, and reasoning trail."""

    BOT_CHOICES = [
        ("jr",   "Good Ol' JR — data-adding agent (Jim Ross)"),
        ("earl", "Earl Hebner — accuracy auditor + rule improver"),
        ("al",   "Al Snow — interlinking + graph improvement"),
    ]
    OUTCOME_CHOICES = [
        ("running", "In progress"),
        ("completed", "Completed successfully"),
        ("budget_exceeded", "Hit budget cap"),
        ("error", "Errored out"),
        ("stopped", "Stopped early by caller"),
    ]

    bot = models.CharField(max_length=20, choices=BOT_CHOICES, db_index=True)
    task = models.TextField(help_text="Human-readable goal for this session")
    model = models.CharField(max_length=100, default="claude-sonnet-4-6")

    started_at = models.DateTimeField(auto_now_add=True, db_index=True)
    finished_at = models.DateTimeField(blank=True, null=True)

    # Budget accounting
    max_tool_calls = models.PositiveIntegerField(default=50)
    max_input_tokens = models.PositiveIntegerField(default=200_000)
    tool_calls_used = models.PositiveIntegerField(default=0)
    input_tokens_used = models.PositiveIntegerField(default=0)
    output_tokens_used = models.PositiveIntegerField(default=0)

    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES,
                               default="running", db_index=True)
    final_summary = models.TextField(blank=True, default="",
                                     help_text="Agent's own summary of what it accomplished")

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["bot", "outcome"]),
            models.Index(fields=["-started_at"]),
        ]

    @property
    def cost_estimate_usd(self) -> float:
        """
        Approximate per-session cost. Per-model pricing as of late-2025:
            Haiku  4.5:  $1/M in, $5/M out
            Sonnet 4.6:  $3/M in, $15/M out
            Opus   4.5: $15/M in, $75/M out
        Unknown models fall back to Sonnet pricing.
        """
        m = (self.model or "").lower()
        if "opus" in m:
            in_rate, out_rate = 15, 75
        elif "haiku" in m:
            in_rate, out_rate = 1, 5
        else:
            in_rate, out_rate = 3, 15
        return (self.input_tokens_used * in_rate
                + self.output_tokens_used * out_rate) / 1_000_000

    def __str__(self):
        return f"{self.bot} session #{self.id} ({self.outcome}): {self.task[:60]}"


class AgentToolCall(models.Model):
    """One tool invocation within an AgentSession. Immutable audit log."""
    session = models.ForeignKey(
        AgentSession, on_delete=models.CASCADE, related_name="tool_calls",
    )
    sequence = models.PositiveIntegerField(help_text="0-based call order within session")
    tool_name = models.CharField(max_length=100, db_index=True)
    arguments = models.JSONField(default=dict, blank=True)
    result_summary = models.TextField(blank=True, default="",
                                      help_text="Truncated result text for human inspection")
    error = models.TextField(blank=True, default="")
    duration_ms = models.PositiveIntegerField(default=0)
    called_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["session", "sequence"]
        unique_together = [("session", "sequence")]
        indexes = [
            models.Index(fields=["tool_name"]),
            models.Index(fields=["session", "sequence"]),
        ]

    def __str__(self):
        return f"{self.session.bot}/{self.session_id} #{self.sequence}: {self.tool_name}"
