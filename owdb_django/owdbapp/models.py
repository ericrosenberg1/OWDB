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


class Venue(TimeStampedModel):
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


class Promotion(TimeStampedModel):
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


class Wrestler(TimeStampedModel):
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


class Event(TimeStampedModel):
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


class Title(TimeStampedModel):
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
        """Increment usage counters."""
        self.reset_daily_count()
        self.requests_today += 1
        self.requests_total += 1
        self.last_used = timezone.now()
        self.save(update_fields=['requests_today', 'requests_total', 'last_used'])

    @property
    def rate_limit(self):
        """Return the rate limit for this key."""
        return 1000 if self.is_paid else 100

    @property
    def is_rate_limited(self):
        """Check if the key has exceeded its rate limit."""
        self.reset_daily_count()
        return self.requests_today >= self.rate_limit
