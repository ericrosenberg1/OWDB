from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify
import secrets


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ImageMixin(models.Model):
    """
    Mixin for CC-licensed image storage with proper attribution.

    Only stores images from Creative Commons sources:
    - CC0 (Public Domain Dedication)
    - CC BY (Attribution)
    - CC BY-SA (Attribution-ShareAlike)
    - Public Domain
    """
    LICENSE_CHOICES = [
        ('cc0', 'CC0 - Public Domain'),
        ('cc-by', 'CC BY'),
        ('cc-by-sa', 'CC BY-SA'),
        ('pd', 'Public Domain'),
    ]

    image_url = models.URLField(max_length=500, blank=True, null=True,
                                 help_text="URL to the image file")
    image_source_url = models.URLField(max_length=500, blank=True, null=True,
                                        help_text="URL to the original source page (e.g., Wikimedia Commons)")
    image_license = models.CharField(max_length=20, choices=LICENSE_CHOICES,
                                      blank=True, default='',
                                      help_text="Creative Commons license type")
    image_credit = models.CharField(max_length=500, blank=True, default='',
                                     help_text="Attribution text for license compliance")
    image_fetched_at = models.DateTimeField(blank=True, null=True,
                                             help_text="When the image was fetched")

    class Meta:
        abstract = True

    def has_image(self):
        """Check if this entity has an image."""
        return bool(self.image_url)


class Venue(ImageMixin, TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    capacity = models.IntegerField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['location']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_event_count(self):
        """Get total number of events at this venue."""
        return self.events.count()

    def get_promotions(self):
        """Get all promotions that have held events here, ordered by event count."""
        from django.db.models import Count, Q
        return Promotion.objects.filter(
            events__venue=self
        ).distinct().annotate(
            event_count=Count('events', filter=Q(events__venue=self))
        ).order_by('-event_count')

    def get_wrestlers(self, limit=20):
        """Get wrestlers who have performed at this venue, ordered by appearance count."""
        from django.db.models import Count, Q
        return Wrestler.objects.filter(
            matches__event__venue=self
        ).distinct().annotate(
            appearance_count=Count('matches', filter=Q(matches__event__venue=self))
        ).order_by('-appearance_count')[:limit]

    def get_stats(self):
        """Get venue statistics."""
        from django.db.models import Sum, Avg, Count
        stats = self.events.aggregate(
            total_events=Count('id'),
            total_attendance=Sum('attendance'),
            avg_attendance=Avg('attendance')
        )
        return stats


class Promotion(ImageMixin, TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    abbreviation = models.CharField(max_length=50, blank=True, null=True)
    nicknames = models.CharField(max_length=255, blank=True, null=True)
    founded_year = models.IntegerField(blank=True, null=True, db_index=True)
    closed_year = models.IntegerField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['abbreviation']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.abbreviation:
            return f"{self.name} ({self.abbreviation})"
        return self.name

    @property
    def is_active(self):
        return self.closed_year is None

    def get_all_wrestlers(self, limit=50):
        """Get all wrestlers who have appeared for this promotion, ordered by match count."""
        from django.db.models import Count, Q
        return Wrestler.objects.filter(
            matches__event__promotion=self
        ).distinct().annotate(
            match_count=Count('matches', filter=Q(matches__event__promotion=self))
        ).order_by('-match_count')[:limit]

    def get_venues(self, limit=20):
        """Get venues where this promotion has held events, ordered by event count."""
        from django.db.models import Count, Q
        return Venue.objects.filter(
            events__promotion=self
        ).distinct().annotate(
            event_count=Count('events', filter=Q(events__promotion=self))
        ).order_by('-event_count')[:limit]

    def get_event_timeline(self):
        """Get events grouped by year for timeline display."""
        from django.db.models.functions import ExtractYear
        from django.db.models import Count
        return self.events.annotate(
            year=ExtractYear('date')
        ).values('year').annotate(
            count=Count('id')
        ).order_by('-year')

    def get_stats(self):
        """Get promotion statistics."""
        return {
            'total_events': self.events.count(),
            'total_titles': self.titles.count(),
            'active_titles': self.titles.filter(retirement_year__isnull=True).count(),
            'total_wrestlers': Wrestler.objects.filter(
                matches__event__promotion=self
            ).distinct().count(),
        }


class Wrestler(ImageMixin, TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    real_name = models.CharField(max_length=255, blank=True, null=True)
    aliases = models.TextField(blank=True, null=True, help_text="Comma-separated list of aliases")
    debut_year = models.IntegerField(blank=True, null=True, db_index=True)
    retirement_year = models.IntegerField(blank=True, null=True)
    hometown = models.CharField(max_length=255, blank=True, null=True)
    nationality = models.CharField(max_length=255, blank=True, null=True)
    finishers = models.TextField(blank=True, null=True, help_text="Comma-separated list of finishing moves")
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'wrestlers'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['debut_year']),
            models.Index(fields=['nationality']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.retirement_year is None

    def get_aliases_list(self):
        if self.aliases:
            return [a.strip() for a in self.aliases.split(',')]
        return []

    def get_finishers_list(self):
        if self.finishers:
            return [f.strip() for f in self.finishers.split(',')]
        return []

    def get_promotions(self):
        """Get all promotions this wrestler has appeared for, ordered by match count."""
        from django.db.models import Count, Q
        return Promotion.objects.filter(
            events__matches__wrestlers=self
        ).distinct().annotate(
            match_count=Count('events__matches', filter=Q(events__matches__wrestlers=self))
        ).order_by('-match_count')

    def get_titles_won(self):
        """Get all titles this wrestler has won (matches where they were the winner)."""
        return Title.objects.filter(
            title_matches__winner=self
        ).distinct()

    def get_rivals(self, limit=10):
        """Get wrestlers this person has faced most often."""
        from django.db.models import Count
        # Get all matches this wrestler was in
        my_matches = self.matches.all()
        # Find other wrestlers in those matches, counted by frequency
        return Wrestler.objects.filter(
            matches__in=my_matches
        ).exclude(
            id=self.id
        ).annotate(
            encounter_count=Count('id')
        ).order_by('-encounter_count')[:limit]

    def get_win_loss_record(self):
        """Get win/loss/draw record for this wrestler."""
        total_matches = self.matches.count()
        wins = self.matches_won.count()
        # Losses = matches participated in minus wins (simplified)
        losses = total_matches - wins
        return {
            'wins': wins,
            'losses': losses,
            'total': total_matches,
            'win_percentage': round((wins / total_matches * 100), 1) if total_matches > 0 else 0
        }


class Event(ImageMixin, TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name='events'
    )
    venue = models.ForeignKey(
        Venue, on_delete=models.SET_NULL, blank=True, null=True, related_name='events'
    )
    date = models.DateField(db_index=True)
    attendance = models.IntegerField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-date']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['date']),
            models.Index(fields=['promotion', 'date']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            date_str = self.date.strftime('%Y') if self.date else ''
            self.slug = slugify(f"{self.name}-{date_str}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.date.year if self.date else 'TBD'})"

    def get_all_wrestlers(self):
        """Get all wrestlers who competed at this event."""
        return Wrestler.objects.filter(
            matches__event=self
        ).distinct().order_by('name')

    def get_titles_defended(self):
        """Get all titles that were defended/contested at this event."""
        return Title.objects.filter(
            title_matches__event=self
        ).distinct()


class Title(ImageMixin, TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.CASCADE, related_name='titles'
    )
    debut_year = models.IntegerField(blank=True, null=True)
    retirement_year = models.IntegerField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['promotion']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.promotion.abbreviation or self.promotion.name})"

    @property
    def is_active(self):
        return self.retirement_year is None

    def get_championship_history(self):
        """Get chronological history of title changes (matches where title changed hands)."""
        return self.title_matches.filter(
            winner__isnull=False
        ).select_related('winner', 'event').order_by('event__date')

    def get_all_champions(self):
        """Get all wrestlers who have held this title."""
        return Wrestler.objects.filter(
            matches_won__title=self
        ).distinct()

    def get_most_defenses(self, limit=10):
        """Get wrestlers with the most title defenses."""
        from django.db.models import Count
        return Wrestler.objects.filter(
            matches_won__title=self
        ).annotate(
            defense_count=Count('matches_won')
        ).order_by('-defense_count')[:limit]


class Match(TimeStampedModel):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='matches'
    )
    wrestlers = models.ManyToManyField(Wrestler, related_name='matches')
    match_text = models.TextField(help_text="Description like 'The Rock vs Stone Cold'")
    result = models.CharField(max_length=255, blank=True, null=True)
    winner = models.ForeignKey(
        Wrestler, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='matches_won'
    )
    match_type = models.CharField(max_length=255, blank=True, null=True)
    title = models.ForeignKey(
        Title, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='title_matches'
    )
    match_order = models.PositiveIntegerField(default=0, help_text="Order on the card")
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['event', 'match_order']
        verbose_name_plural = 'matches'
        indexes = [
            models.Index(fields=['event']),
            models.Index(fields=['match_type']),
        ]

    def __str__(self):
        return f"{self.match_text} @ {self.event.name}"

    def get_participants(self):
        """Get all wrestler objects who participated in this match."""
        return self.wrestlers.all().order_by('name')

    def get_related_matches(self, limit=5):
        """Get matches featuring the same wrestlers (excluding this match)."""
        participant_ids = self.wrestlers.values_list('id', flat=True)
        return Match.objects.filter(
            wrestlers__in=participant_ids
        ).exclude(
            id=self.id
        ).distinct().select_related('event')[:limit]


class VideoGame(TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    promotions = models.ManyToManyField(Promotion, blank=True, related_name='video_games')
    release_year = models.IntegerField(blank=True, null=True, db_index=True)
    systems = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., PS5, Xbox, PC")
    developer = models.CharField(max_length=255, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-release_year', 'name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['release_year']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.release_year or 'TBD'})"


class Podcast(TimeStampedModel):
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    hosts = models.TextField(blank=True, null=True, help_text="Comma-separated list of hosts")
    related_wrestlers = models.ManyToManyField(Wrestler, blank=True, related_name='podcasts')
    launch_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        return self.end_year is None


class Book(TimeStampedModel):
    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    author = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    related_wrestlers = models.ManyToManyField(Wrestler, blank=True, related_name='books')
    publication_year = models.IntegerField(blank=True, null=True)
    isbn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    publisher = models.CharField(max_length=255, blank=True, null=True)
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-publication_year', 'title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['author']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.author or 'Unknown'}"


class Special(TimeStampedModel):
    SPECIAL_TYPES = [
        ('documentary', 'Documentary'),
        ('movie', 'Movie'),
        ('tv_special', 'TV Special'),
        ('series', 'Series'),
        ('other', 'Other'),
    ]

    title = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    release_year = models.IntegerField(blank=True, null=True)
    related_wrestlers = models.ManyToManyField(Wrestler, blank=True, related_name='specials')
    type = models.CharField(max_length=50, choices=SPECIAL_TYPES, default='other')
    about = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-release_year', 'title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['type']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.release_year or 'TBD'})"


class UserProfile(TimeStampedModel):
    """Extended user profile with email verification status."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    email_verified = models.BooleanField(default=False)
    can_contribute = models.BooleanField(default=False, help_text="Can add/edit content after email verification")

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"Profile for {self.user.username}"


class EmailVerificationToken(TimeStampedModel):
    """Token for email verification."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Email Verification Token'
        verbose_name_plural = 'Email Verification Tokens'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Verification token for {self.user.username}"

    @classmethod
    def generate_token(cls):
        """Generate a secure verification token."""
        return secrets.token_urlsafe(32)

    @property
    def is_valid(self):
        """Check if the token is still valid (not expired and not used)."""
        return not self.used and self.expires_at > timezone.now()


class APIKey(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, blank=True, null=True, help_text="Optional name for this key")
    is_paid = models.BooleanField(default=False)
    requests_today = models.IntegerField(default=0)
    requests_total = models.IntegerField(default=0)
    last_used = models.DateTimeField(blank=True, null=True)
    last_reset = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"API Key for {self.user.username}"

    @classmethod
    def generate_key(cls):
        """Generate a secure API key."""
        return secrets.token_urlsafe(32)

    def reset_daily_count(self):
        """Reset the daily request count."""
        today = timezone.now().date()
        if self.last_reset < today:
            self.requests_today = 0
            self.last_reset = today
            self.save(update_fields=['requests_today', 'last_reset'])

    def increment_usage(self):
        """Increment usage counters atomically to prevent race conditions."""
        from django.db.models import F
        self.reset_daily_count()
        # Use F() expressions for atomic increment
        APIKey.objects.filter(pk=self.pk).update(
            requests_today=F('requests_today') + 1,
            requests_total=F('requests_total') + 1,
            last_used=timezone.now(),
        )
        self.refresh_from_db()

    @property
    def rate_limit(self):
        """Return the rate limit for this key."""
        return 1000 if self.is_paid else 100

    @property
    def is_rate_limited(self):
        """Check if the key has exceeded its rate limit."""
        self.reset_daily_count()
        return self.requests_today >= self.rate_limit


class WrestleBotLog(TimeStampedModel):
    """
    Tracks WrestleBot AI activity and data imports.

    This model logs every action taken by WrestleBot, providing
    transparency and allowing users to see exactly what was added
    and from which Wikipedia sources.
    """
    ACTION_TYPES = [
        ('discover', 'Discovered New Entity'),
        ('create', 'Created Record'),
        ('update', 'Updated Record'),
        ('link', 'Linked Records'),
        ('enrich', 'Enriched Data'),
        ('verify', 'Verified Data'),
        ('skip', 'Skipped (Duplicate/Invalid)'),
        ('error', 'Error'),
    ]

    ENTITY_TYPES = [
        ('wrestler', 'Wrestler'),
        ('promotion', 'Promotion'),
        ('event', 'Event'),
        ('match', 'Match'),
        ('title', 'Title'),
        ('venue', 'Venue'),
        ('videogame', 'Video Game'),
        ('podcast', 'Podcast'),
        ('book', 'Book'),
        ('special', 'Special'),
    ]

    action_type = models.CharField(max_length=20, choices=ACTION_TYPES, db_index=True)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES, db_index=True)
    entity_name = models.CharField(max_length=255)
    entity_id = models.IntegerField(blank=True, null=True, help_text="ID of the affected record")

    # Source tracking for copyright compliance
    source_url = models.URLField(max_length=500, blank=True, null=True, help_text="Wikipedia article URL")
    source_title = models.CharField(max_length=255, blank=True, null=True, help_text="Wikipedia article title")

    # What was extracted (only factual, non-copyrightable data)
    data_extracted = models.JSONField(
        default=dict,
        blank=True,
        help_text="Factual data extracted (names, dates, numbers - no prose)"
    )

    # AI processing details
    ai_model = models.CharField(max_length=100, blank=True, null=True, help_text="AI model used (e.g., llama3.2)")
    ai_confidence = models.FloatField(blank=True, null=True, help_text="AI confidence score 0.0-1.0")
    ai_reasoning = models.TextField(blank=True, null=True, help_text="AI's reasoning for the action")

    # Task tracking
    task_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    batch_id = models.CharField(max_length=100, blank=True, null=True, db_index=True, help_text="Groups related operations")

    # Success/failure
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'WrestleBot Log'
        verbose_name_plural = 'WrestleBot Logs'
        indexes = [
            models.Index(fields=['action_type', 'entity_type']),
            models.Index(fields=['created_at']),
            models.Index(fields=['batch_id']),
            models.Index(fields=['success']),
        ]

    def __str__(self):
        return f"[{self.get_action_type_display()}] {self.entity_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class WrestleBotConfig(TimeStampedModel):
    """
    Configuration for WrestleBot AI operations.

    Singleton model to store runtime configuration that can be
    adjusted without redeploying the application.
    """
    # Enable/disable the bot
    enabled = models.BooleanField(default=True, help_text="Master switch for WrestleBot")

    # Rate limiting
    max_items_per_hour = models.IntegerField(default=50, help_text="Maximum new items to add per hour")
    max_items_per_day = models.IntegerField(default=500, help_text="Maximum new items to add per day")
    cooldown_minutes = models.IntegerField(default=5, help_text="Minutes to wait between batches")

    # AI model settings
    ai_model_name = models.CharField(max_length=100, default="llama3.2", help_text="Ollama model to use")
    ai_temperature = models.FloatField(default=0.3, help_text="AI temperature (lower = more deterministic)")
    min_confidence_threshold = models.FloatField(default=0.7, help_text="Minimum AI confidence to accept data")

    # Content quality settings
    min_data_fields = models.IntegerField(default=3, help_text="Minimum fields required to create a record")
    require_verification = models.BooleanField(default=True, help_text="Require AI verification before import")

    # Focus areas (which categories to prioritize)
    focus_wrestlers = models.BooleanField(default=True)
    focus_promotions = models.BooleanField(default=True)
    focus_events = models.BooleanField(default=True)
    focus_titles = models.BooleanField(default=True)
    focus_matches = models.BooleanField(default=False, help_text="Matches require more complex parsing")

    # Statistics
    items_added_today = models.IntegerField(default=0)
    items_added_this_hour = models.IntegerField(default=0)
    last_run = models.DateTimeField(blank=True, null=True)
    last_reset_date = models.DateField(blank=True, null=True)
    last_reset_hour = models.IntegerField(default=0)
    total_items_added = models.IntegerField(default=0)
    total_errors = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'WrestleBot Configuration'
        verbose_name_plural = 'WrestleBot Configuration'

    def __str__(self):
        status = "Enabled" if self.enabled else "Disabled"
        return f"WrestleBot Config ({status})"

    def save(self, *args, **kwargs):
        # Ensure only one config exists
        if not self.pk and WrestleBotConfig.objects.exists():
            raise ValueError("Only one WrestleBotConfig can exist")
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """Get or create the singleton config."""
        config, created = cls.objects.get_or_create(pk=1)
        return config

    def reset_hourly_count(self):
        """Reset the hourly item count if needed."""
        from django.utils import timezone
        now = timezone.now()
        if self.last_reset_hour != now.hour:
            self.items_added_this_hour = 0
            self.last_reset_hour = now.hour
            self.save(update_fields=['items_added_this_hour', 'last_reset_hour'])

    def reset_daily_count(self):
        """Reset the daily item count if needed."""
        from django.utils import timezone
        today = timezone.now().date()
        if self.last_reset_date != today:
            self.items_added_today = 0
            self.last_reset_date = today
            self.save(update_fields=['items_added_today', 'last_reset_date'])

    def can_add_items(self, count: int = 1) -> bool:
        """Check if we can add more items within rate limits."""
        self.reset_hourly_count()
        self.reset_daily_count()
        return (
            self.enabled and
            self.items_added_this_hour + count <= self.max_items_per_hour and
            self.items_added_today + count <= self.max_items_per_day
        )

    def record_items_added(self, count: int = 1):
        """Record that items were added atomically to prevent race conditions."""
        from django.db.models import F
        WrestleBotConfig.objects.filter(pk=self.pk).update(
            items_added_this_hour=F('items_added_this_hour') + count,
            items_added_today=F('items_added_today') + count,
            total_items_added=F('total_items_added') + count,
            last_run=timezone.now(),
        )
        self.refresh_from_db()
