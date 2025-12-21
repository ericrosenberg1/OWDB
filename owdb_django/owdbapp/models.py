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

    Images are cached to Cloudflare R2 and served via images.wrestlingdb.org CDN.
    """
    LICENSE_CHOICES = [
        ('cc0', 'CC0 - Public Domain'),
        ('cc-by', 'CC BY'),
        ('cc-by-sa', 'CC BY-SA'),
        ('pd', 'Public Domain'),
    ]

    image_url = models.URLField(max_length=500, blank=True, null=True,
                                 help_text="URL to the cached image on R2 CDN")
    image_source_url = models.URLField(max_length=500, blank=True, null=True,
                                        help_text="URL to the original source page (e.g., Wikimedia Commons)")
    image_original_url = models.URLField(max_length=500, blank=True, null=True,
                                          help_text="Original image URL before caching to R2")
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

    def image_age_days(self):
        """Get the age of the current image in days."""
        if not self.image_fetched_at:
            return None
        from django.utils import timezone
        delta = timezone.now() - self.image_fetched_at
        return delta.days

    def needs_image_refresh(self, min_age_days=30):
        """Check if the image should be refreshed (older than min_age_days)."""
        age = self.image_age_days()
        return age is not None and age >= min_age_days


class ImageHistory(TimeStampedModel):
    """
    Historical record of images for entities.

    Stores previous images when they are replaced, allowing users to
    browse through the image history of wrestlers, promotions, etc.
    """
    ENTITY_TYPES = [
        ('wrestler', 'Wrestler'),
        ('promotion', 'Promotion'),
        ('venue', 'Venue'),
        ('event', 'Event'),
        ('title', 'Title'),
        ('stable', 'Stable'),
    ]

    LICENSE_CHOICES = [
        ('cc0', 'CC0 - Public Domain'),
        ('cc-by', 'CC BY'),
        ('cc-by-sa', 'CC BY-SA'),
        ('pd', 'Public Domain'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPES, db_index=True)
    entity_id = models.PositiveIntegerField(db_index=True)

    # Image data (stored on R2)
    image_url = models.URLField(max_length=500,
                                 help_text="URL to the cached image on R2 CDN")
    image_source_url = models.URLField(max_length=500, blank=True, null=True,
                                        help_text="URL to the original source page")
    image_original_url = models.URLField(max_length=500, blank=True, null=True,
                                          help_text="Original image URL before caching")
    image_license = models.CharField(max_length=20, choices=LICENSE_CHOICES,
                                      blank=True, default='')
    image_credit = models.CharField(max_length=500, blank=True, default='')

    # When this was the active image
    active_from = models.DateTimeField(help_text="When this image became active")
    active_until = models.DateTimeField(auto_now_add=True,
                                         help_text="When this image was replaced")

    # Why it was replaced
    replacement_reason = models.CharField(max_length=100, blank=True, default='',
                                           help_text="Why image was replaced (e.g., 'better_image_found', 'scheduled_refresh')")

    class Meta:
        ordering = ['-active_until']
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['entity_type', 'entity_id', '-active_until']),
        ]
        verbose_name_plural = "Image histories"

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} - {self.active_until}"

    @classmethod
    def archive_current_image(cls, entity, reason='scheduled_refresh'):
        """
        Archive the current image of an entity before replacing it.

        Args:
            entity: The model instance (Wrestler, Promotion, etc.)
            reason: Why the image is being replaced
        """
        if not entity.image_url:
            return None

        # Determine entity type from model name
        entity_type = entity.__class__.__name__.lower()

        return cls.objects.create(
            entity_type=entity_type,
            entity_id=entity.pk,
            image_url=entity.image_url,
            image_source_url=entity.image_source_url or '',
            image_original_url=getattr(entity, 'image_original_url', '') or '',
            image_license=entity.image_license or '',
            image_credit=entity.image_credit or '',
            active_from=entity.image_fetched_at or entity.created_at,
            replacement_reason=reason,
        )

    @classmethod
    def get_history_for_entity(cls, entity_type, entity_id, limit=10):
        """Get image history for a specific entity."""
        return cls.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by('-active_until')[:limit]


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

    # Multi-source data tracking
    wikipedia_url = models.URLField(max_length=500, blank=True, null=True,
                                     help_text="Wikipedia article URL")
    cagematch_url = models.URLField(max_length=500, blank=True, null=True,
                                    help_text="Cagematch.net database URL")
    profightdb_url = models.URLField(max_length=500, blank=True, null=True,
                                     help_text="ProFightDB promotion URL")
    last_enriched = models.DateTimeField(blank=True, null=True)

    # Additional fields
    headquarters = models.CharField(max_length=255, blank=True, null=True)
    founder = models.CharField(max_length=255, blank=True, null=True)

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


class Stable(ImageMixin, TimeStampedModel):
    """
    Wrestling stable/faction/team (e.g., D-Generation X, The Shield, NWO).

    A stable is a group of wrestlers who regularly appear together, often
    sharing a common gimmick, manager, or storyline purpose.
    """
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    promotion = models.ForeignKey(
        Promotion, on_delete=models.SET_NULL, blank=True, null=True,
        related_name='stables',
        help_text="Primary promotion (may appear in multiple)"
    )

    # Members
    members = models.ManyToManyField(
        'Wrestler', related_name='stables', blank=True,
        help_text="Current and former members"
    )
    leaders = models.ManyToManyField(
        'Wrestler', related_name='stables_led', blank=True,
        help_text="Leaders/founders of the stable"
    )

    # Timeline
    formed_year = models.IntegerField(blank=True, null=True, db_index=True)
    disbanded_year = models.IntegerField(blank=True, null=True)

    # Details
    about = models.TextField(blank=True, null=True)
    manager = models.CharField(max_length=255, blank=True, null=True,
                               help_text="Non-wrestler manager if applicable")

    # Data source tracking
    wikipedia_url = models.URLField(max_length=500, blank=True, null=True)
    cagematch_url = models.URLField(max_length=500, blank=True, null=True)
    profightdb_url = models.URLField(max_length=500, blank=True, null=True)
    last_enriched = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['formed_year']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def is_active(self):
        """Check if the stable is still active."""
        return self.disbanded_year is None

    def get_member_count(self):
        """Get total number of members (current and former)."""
        return self.members.count()

    def get_titles_won(self):
        """Get all titles won by stable members as a team."""
        from django.db.models import Q
        return Title.objects.filter(
            Q(name__icontains='tag team') | Q(name__icontains='trios')
        ).filter(
            title_matches__wrestlers__in=self.members.all()
        ).distinct()


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

    # Multi-source data tracking for comprehensive enrichment
    wikipedia_url = models.URLField(max_length=500, blank=True, null=True,
                                     help_text="Wikipedia article URL")
    cagematch_url = models.URLField(max_length=500, blank=True, null=True,
                                    help_text="Cagematch.net profile URL")
    profightdb_url = models.URLField(max_length=500, blank=True, null=True,
                                     help_text="ProFightDB profile URL")
    last_enriched = models.DateTimeField(blank=True, null=True,
                                          help_text="When data was last enriched from external sources")

    # Additional profile fields for completeness
    birth_date = models.DateField(blank=True, null=True)
    height = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 6'2\" or 188 cm")
    weight = models.CharField(max_length=50, blank=True, null=True, help_text="e.g., 250 lbs or 113 kg")
    trained_by = models.TextField(blank=True, null=True, help_text="Comma-separated list of trainers")
    signature_moves = models.TextField(blank=True, null=True, help_text="Signature moves (not finishers)")

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

    def get_title_history(self, limit_titles: int | None = None):
        """
        Build a structured title history grouped by promotion.

        Returns a list of dicts:
        [
            {
                "promotion": Promotion,
                "titles": [
                    {"title": Title, "entries": [...], "prominence": int, "most_recent": date}
                ],
            },
        ]
        """
        from datetime import date as date_cls
        from django.db.models import Count

        titles = (
            Title.objects.filter(title_matches__wrestlers=self)
            .select_related("promotion")
            .distinct()
            .annotate(prominence=Count("title_matches", distinct=True))
        )
        if limit_titles:
            titles = titles[:limit_titles]

        promotion_groups = {}

        for title in titles:
            entries, most_recent = self._build_title_entries(title)
            if not entries:
                continue
            group = promotion_groups.setdefault(
                title.promotion_id,
                {"promotion": title.promotion, "titles": []},
            )
            group["titles"].append(
                {
                    "title": title,
                    "entries": entries,
                    "prominence": title.prominence or 0,
                    "most_recent": most_recent,
                }
            )

        group_list = list(promotion_groups.values())
        for group in group_list:
            group["titles"].sort(
                key=lambda item: (
                    item.get("prominence", 0),
                    item.get("most_recent") or date_cls.min,
                ),
                reverse=True,
            )
            group["most_recent"] = max(
                (item.get("most_recent") for item in group["titles"]),
                default=None,
            )

        group_list.sort(
            key=lambda group: (
                group["promotion"].name if group.get("promotion") else "",
            )
        )

        return group_list

    def _build_title_entries(self, title):
        """Build ordered match entries for a specific title."""
        from datetime import date as date_cls

        matches = (
            Match.objects.filter(title=title)
            .select_related("event", "event__promotion", "winner")
            .prefetch_related("wrestlers")
            .order_by("event__date", "match_order", "pk")
        )

        champion_id = None
        entries = []

        for match in matches:
            participants = set(match.wrestlers.values_list("id", flat=True))
            is_participant = self.id in participants
            result = "unknown"
            label = "Unknown"

            if match.winner_id:
                if is_participant:
                    if match.winner_id == self.id:
                        if champion_id == self.id:
                            result = "defense"
                            label = "Defense"
                        else:
                            result = "win"
                            label = "Win"
                    else:
                        result = "loss"
                        label = "Loss"
                champion_id = match.winner_id
            elif is_participant:
                result = "draw"
                label = "Draw"

            if is_participant:
                entries.append(
                    {
                        "match": match,
                        "event": match.event,
                        "date": match.event.date if match.event else None,
                        "result": result,
                        "result_label": label,
                    }
                )

        entries.sort(
            key=lambda item: item.get("date") or date_cls.min,
            reverse=True,
        )
        most_recent = entries[0]["date"] if entries else None

        return entries, most_recent

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

    def get_promotion_history_with_years(self):
        """
        Get promotion history with years, derived from match data.
        Returns list of dicts: [{'promotion': Promotion, 'start_year': int, 'end_year': int}, ...]
        """
        from django.db.models import Min, Max
        from django.db.models.functions import ExtractYear

        # Get years for each promotion from matches
        promo_years = self.matches.values(
            'event__promotion__id',
            'event__promotion__name',
            'event__promotion__slug',
            'event__promotion__abbreviation',
        ).annotate(
            start_year=Min(ExtractYear('event__date')),
            end_year=Max(ExtractYear('event__date'))
        ).order_by('-end_year', '-start_year')

        result = []
        for item in promo_years:
            if item['event__promotion__id']:
                result.append({
                    'promotion_id': item['event__promotion__id'],
                    'name': item['event__promotion__name'],
                    'slug': item['event__promotion__slug'],
                    'abbreviation': item['event__promotion__abbreviation'],
                    'start_year': item['start_year'],
                    'end_year': item['end_year'],
                })
        return result

    def get_podcast_appearances(self):
        """Get all podcast episodes this wrestler appeared on as a guest."""
        return self.podcast_appearances.select_related('podcast').order_by('-published_date')

    def get_podcast_count(self):
        """Get count of podcast appearances."""
        return self.podcast_appearances.count()

    def get_books(self):
        """Get all books related to this wrestler."""
        return self.books.all().order_by('-publication_year')

    def get_specials(self):
        """Get all documentaries/specials featuring this wrestler."""
        return self.specials.all().order_by('-release_year')

    def get_video_games(self):
        """Get video games this wrestler appears in (via promotions)."""
        from django.db.models import Q
        # Get promotions this wrestler worked for
        promo_ids = self.matches.values_list('event__promotion_id', flat=True).distinct()
        return VideoGame.objects.filter(promotions__in=promo_ids).distinct().order_by('-release_year')

    def get_stables(self):
        """Get all stables this wrestler has been a member of."""
        return self.stables.select_related('promotion').order_by('-formed_year')

    def get_events(self, limit=50):
        """Get events this wrestler has appeared at."""
        return Event.objects.filter(
            matches__wrestlers=self
        ).distinct().select_related('promotion', 'venue').order_by('-date')[:limit]

    def get_tv_appearances(self, limit=50):
        """Get TV show episodes this wrestler has appeared on."""
        # Filter for events that look like TV episodes
        return Event.objects.filter(
            matches__wrestlers=self
        ).filter(
            # TV shows typically have names like "Raw #123" or "SmackDown - April 5"
            name__icontains='Raw'
        ) | Event.objects.filter(
            matches__wrestlers=self
        ).filter(
            name__icontains='SmackDown'
        ) | Event.objects.filter(
            matches__wrestlers=self
        ).filter(
            name__icontains='Dynamite'
        ) | Event.objects.filter(
            matches__wrestlers=self
        ).filter(
            name__icontains='Nitro'
        ).distinct().select_related('promotion', 'venue').order_by('-date')[:limit]

    def get_all_meta_categories(self):
        """
        Get counts for all meta categories this wrestler appears in.
        Returns a dict with category names and counts.
        """
        return {
            'matches': self.matches.count(),
            'events': Event.objects.filter(matches__wrestlers=self).distinct().count(),
            'promotions': Promotion.objects.filter(events__matches__wrestlers=self).distinct().count(),
            'titles': Title.objects.filter(title_matches__wrestlers=self).distinct().count(),
            'stables': self.stables.count(),
            'podcast_appearances': self.podcast_appearances.count(),
            'books': self.books.count(),
            'specials': self.specials.count(),
            'rivals': Wrestler.objects.filter(matches__in=self.matches.all()).exclude(id=self.id).distinct().count(),
        }

    def get_completeness_score(self):
        """
        Calculate how complete this wrestler's profile is (0-100).
        Used to prioritize enrichment.
        """
        fields = {
            # Core fields (higher weight)
            'name': 10,
            'real_name': 8,
            'debut_year': 8,
            'hometown': 7,
            'nationality': 6,
            'finishers': 6,
            # Image (important for display)
            'image_url': 10,
            # Extended fields
            'aliases': 5,
            'birth_date': 5,
            'height': 4,
            'weight': 4,
            'trained_by': 5,
            'signature_moves': 4,
            'about': 8,
            # Source tracking
            'wikipedia_url': 5,
            # Relationships (matches, titles)
            'has_matches': 5,
        }

        score = 0
        for field, weight in fields.items():
            if field == 'has_matches':
                if self.matches.exists():
                    score += weight
            elif getattr(self, field, None):
                score += weight

        return score

    @classmethod
    def get_incomplete_profiles(cls, limit=50, max_score=60):
        """
        Get wrestlers with incomplete profiles, prioritized by:
        1. Those with Wikipedia URLs (easier to enrich)
        2. Those with some data but missing key fields
        3. Recently created (fresher data sources)
        """
        from django.db.models import Case, When, Value, IntegerField, Q
        from django.db.models.functions import Coalesce

        # Prioritize records that have Wikipedia URLs but missing data
        return cls.objects.annotate(
            priority=Case(
                # Has Wikipedia URL but missing key data
                When(
                    Q(wikipedia_url__isnull=False) &
                    (Q(real_name__isnull=True) | Q(hometown__isnull=True) | Q(nationality__isnull=True)),
                    then=Value(1)
                ),
                # Has some data but no image
                When(
                    Q(debut_year__isnull=False) & Q(image_url__isnull=True),
                    then=Value(2)
                ),
                # Missing basic info
                When(
                    Q(debut_year__isnull=True) | Q(hometown__isnull=True),
                    then=Value(3)
                ),
                default=Value(4),
                output_field=IntegerField()
            )
        ).filter(
            # Skip recently enriched
            Q(last_enriched__isnull=True) |
            Q(last_enriched__lt=timezone.now() - timezone.timedelta(days=7))
        ).order_by('priority', '-created_at')[:limit]


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
    host_wrestlers = models.ManyToManyField(Wrestler, blank=True, related_name='podcasts_hosted',
                                            help_text="Wrestler hosts of this podcast")
    related_wrestlers = models.ManyToManyField(Wrestler, blank=True, related_name='podcasts')
    launch_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True)
    url = models.URLField(blank=True, null=True)
    rss_feed_url = models.URLField(max_length=500, blank=True, null=True,
                                   help_text="RSS feed URL for automatic episode import")
    last_rss_fetch = models.DateTimeField(blank=True, null=True,
                                          help_text="When episodes were last fetched from RSS")
    about = models.TextField(blank=True, null=True)

    # Additional metadata
    apple_podcasts_url = models.URLField(max_length=500, blank=True, null=True)
    spotify_url = models.URLField(max_length=500, blank=True, null=True)
    youtube_url = models.URLField(max_length=500, blank=True, null=True)

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

    def get_episode_count(self):
        """Get total number of episodes."""
        return self.episodes.count()

    def get_guest_wrestlers(self):
        """Get all wrestlers who have appeared as guests, ordered by appearance count."""
        from django.db.models import Count
        return Wrestler.objects.filter(
            podcast_appearances__podcast=self
        ).annotate(
            appearance_count=Count('podcast_appearances')
        ).order_by('-appearance_count')


class PodcastEpisode(TimeStampedModel):
    """
    Individual episode of a podcast with guest links.

    Episodes are imported from RSS feeds and linked to wrestler guests.
    """
    podcast = models.ForeignKey(
        'Podcast', on_delete=models.CASCADE, related_name='episodes'
    )
    title = models.CharField(max_length=500, db_index=True)
    slug = models.SlugField(max_length=255, blank=True)
    episode_number = models.IntegerField(blank=True, null=True)
    season_number = models.IntegerField(blank=True, null=True)

    # Episode metadata
    published_date = models.DateTimeField(blank=True, null=True, db_index=True)
    duration_seconds = models.IntegerField(blank=True, null=True, help_text="Duration in seconds")
    description = models.TextField(blank=True, null=True)

    # Links
    audio_url = models.URLField(max_length=500, blank=True, null=True)
    episode_url = models.URLField(max_length=500, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)

    # Guests (wrestlers who appeared)
    guests = models.ManyToManyField(
        'Wrestler', blank=True, related_name='podcast_appearances',
        help_text="Wrestlers who appeared as guests on this episode"
    )

    # Events and matches discussed in this episode
    discussed_events = models.ManyToManyField(
        'Event', blank=True, related_name='podcast_discussions',
        help_text="Events discussed in this episode"
    )
    discussed_matches = models.ManyToManyField(
        'Match', blank=True, related_name='podcast_discussions',
        help_text="Matches discussed in this episode"
    )

    # RSS feed tracking
    guid = models.CharField(max_length=500, unique=True, blank=True, null=True,
                           help_text="Unique ID from RSS feed for deduplication")

    class Meta:
        ordering = ['-published_date']
        indexes = [
            models.Index(fields=['podcast', '-published_date']),
            models.Index(fields=['guid']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title[:200])
            date_str = self.published_date.strftime('%Y%m%d') if self.published_date else ''
            self.slug = f"{base_slug}-{date_str}" if date_str else base_slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.podcast.name}: {self.title}"

    @property
    def duration_display(self):
        """Format duration as HH:MM:SS or MM:SS."""
        if not self.duration_seconds:
            return ""
        hours, remainder = divmod(self.duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"


class WrestlerPromotionHistory(TimeStampedModel):
    """
    Tracks a wrestler's history with each promotion they've worked for.

    This model explicitly records the years a wrestler was active with
    a promotion, allowing for accurate timeline display.
    """
    wrestler = models.ForeignKey(
        'Wrestler', on_delete=models.CASCADE, related_name='promotion_history'
    )
    promotion = models.ForeignKey(
        'Promotion', on_delete=models.CASCADE, related_name='wrestler_history'
    )

    # Date range
    start_year = models.IntegerField(blank=True, null=True)
    end_year = models.IntegerField(blank=True, null=True, help_text="Null if currently active")

    # Additional context
    notes = models.CharField(max_length=255, blank=True, null=True,
                            help_text="e.g., 'As Stone Cold', 'NXT only'")
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_year']
        unique_together = ['wrestler', 'promotion', 'start_year']
        verbose_name_plural = "Wrestler promotion histories"
        indexes = [
            models.Index(fields=['wrestler', '-start_year']),
            models.Index(fields=['promotion', '-start_year']),
        ]

    def __str__(self):
        years = f"{self.start_year or '?'}-{self.end_year or 'present'}"
        return f"{self.wrestler.name} @ {self.promotion.name} ({years})"

    @property
    def years_display(self):
        """Format the years range for display."""
        if self.start_year and self.end_year:
            if self.start_year == self.end_year:
                return str(self.start_year)
            return f"{self.start_year}-{self.end_year}"
        elif self.start_year:
            return f"{self.start_year}-present"
        elif self.end_year:
            return f"?-{self.end_year}"
        return "Unknown"


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
        ('stable', 'Stable'),
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
    max_items_per_hour = models.IntegerField(default=180, help_text="Maximum new items to add per hour")
    max_items_per_day = models.IntegerField(default=3600, help_text="Maximum new items to add per day")
    cooldown_minutes = models.IntegerField(default=1, help_text="Minutes to wait between batches")

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
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                "max_items_per_hour": 180,
                "max_items_per_day": 3600,
                "cooldown_minutes": 1,
            },
        )

        # Auto-boost limits to keep the bot running continuously
        updated_fields = []
        if config.max_items_per_hour < 180:
            config.max_items_per_hour = 180
            updated_fields.append("max_items_per_hour")
        if config.max_items_per_day < 3600:
            config.max_items_per_day = 3600
            updated_fields.append("max_items_per_day")
        if config.cooldown_minutes > 1:
            config.cooldown_minutes = 1
            updated_fields.append("cooldown_minutes")

        if updated_fields:
            config.save(update_fields=updated_fields)

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


# =============================================================================
# Hot 100 Wrestlers - Monthly Rankings
# =============================================================================

class Hot100Ranking(TimeStampedModel):
    """
    Monthly Hot 100 ranking for wrestlers.

    Generated automatically on the 1st of each month using a proprietary
    scoring algorithm that considers match activity, title importance,
    media mentions, and more.
    """
    # Period this ranking covers
    year = models.IntegerField(db_index=True)
    month = models.IntegerField(db_index=True)  # 1-12

    # Metadata
    generated_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ['-year', '-month']
        unique_together = ['year', 'month']
        verbose_name = "Hot 100 Ranking"
        verbose_name_plural = "Hot 100 Rankings"

    def __str__(self):
        return f"Hot 100 - {self.get_month_display()} {self.year}"

    def get_month_display(self):
        """Get the month name."""
        import calendar
        return calendar.month_name[self.month]

    @classmethod
    def get_current(cls):
        """Get the most recent published ranking."""
        return cls.objects.filter(is_published=True).first()

    @classmethod
    def get_for_month(cls, year: int, month: int):
        """Get ranking for a specific month."""
        return cls.objects.filter(year=year, month=month).first()


class Hot100Entry(TimeStampedModel):
    """
    Individual entry in a Hot 100 ranking.

    Stores the wrestler's rank, total score, and breakdown of scoring
    components for transparency (without revealing exact weights).
    """
    ranking = models.ForeignKey(
        Hot100Ranking,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    wrestler = models.ForeignKey(
        'Wrestler',
        on_delete=models.CASCADE,
        related_name='hot100_entries'
    )

    # Overall position and score
    rank = models.IntegerField(db_index=True)
    total_score = models.FloatField()

    # Score components (stored for display, actual weights are proprietary)
    match_count_score = models.FloatField(default=0)
    match_importance_score = models.FloatField(default=0)  # Main event, title matches, etc.
    title_activity_score = models.FloatField(default=0)  # Title wins/defenses
    opponent_quality_score = models.FloatField(default=0)  # Based on opponent rankings
    news_mention_score = models.FloatField(default=0)  # Media coverage
    social_engagement_score = models.FloatField(default=0)  # YouTube, podcasts, etc.
    website_views_score = models.FloatField(default=0)  # Views on this site

    # Trend from previous month
    previous_rank = models.IntegerField(null=True, blank=True)
    rank_change = models.IntegerField(default=0)  # Positive = improved, negative = dropped

    class Meta:
        ordering = ['rank']
        unique_together = ['ranking', 'wrestler']
        indexes = [
            models.Index(fields=['ranking', 'rank']),
            models.Index(fields=['wrestler']),
        ]

    def __str__(self):
        return f"#{self.rank} {self.wrestler.name} ({self.ranking})"

    @property
    def trend_display(self):
        """Get trend arrow for display."""
        if self.previous_rank is None:
            return "NEW"
        elif self.rank_change > 0:
            return f"↑{self.rank_change}"
        elif self.rank_change < 0:
            return f"↓{abs(self.rank_change)}"
        else:
            return "–"

    @property
    def trend_class(self):
        """CSS class for trend styling."""
        if self.previous_rank is None:
            return "new"
        elif self.rank_change > 0:
            return "up"
        elif self.rank_change < 0:
            return "down"
        return "same"


class Hot100Calculator:
    """
    Proprietary scoring algorithm for Hot 100 rankings.

    CONFIDENTIAL: Actual weights and formulas are intentionally not documented
    in comments to protect the proprietary nature of the ranking system.
    """

    def __init__(self, year: int, month: int):
        self.year = year
        self.month = month
        self._previous_ranking = None

    def calculate_rankings(self, limit: int = 100) -> list:
        """
        Calculate Hot 100 rankings for the specified month.

        Returns list of dicts with wrestler_id and score components.
        """
        from datetime import date
        from django.db.models import Count, Q, Sum, Avg, F
        from django.db.models.functions import Coalesce

        # Get date range for this month
        start_date = date(self.year, self.month, 1)
        if self.month == 12:
            end_date = date(self.year + 1, 1, 1)
        else:
            end_date = date(self.year, self.month + 1, 1)

        # Get previous month's ranking for trend calculation
        prev_year = self.year if self.month > 1 else self.year - 1
        prev_month = self.month - 1 if self.month > 1 else 12
        self._previous_ranking = Hot100Ranking.get_for_month(prev_year, prev_month)

        # Look back up to 12 months for activity (handles sparse data periods)
        lookback_date = date(self.year - 1, self.month, 1) if self.month <= 12 else date(self.year, 1, 1)

        wrestlers = Wrestler.objects.annotate(
            # Match count in period (current month)
            period_matches=Count(
                'matches',
                filter=Q(matches__event__date__gte=start_date, matches__event__date__lt=end_date)
            ),
            # Trailing 12 month matches
            trailing_matches=Count(
                'matches',
                filter=Q(matches__event__date__gte=lookback_date, matches__event__date__lt=end_date)
            ),
            # All-time matches (fallback)
            total_matches=Count('matches'),
            # Wins in period
            period_wins=Count(
                'matches_won',
                filter=Q(matches_won__event__date__gte=start_date, matches_won__event__date__lt=end_date)
            ),
            # Main events (high match order - simplified)
            period_main_events=Count(
                'matches',
                filter=Q(
                    matches__event__date__gte=start_date,
                    matches__event__date__lt=end_date,
                    matches__match_order__gte=6
                )
            ),
        ).filter(
            # Include wrestlers with matches OR those marked as active
            Q(period_matches__gt=0) | Q(trailing_matches__gt=0) | Q(total_matches__gt=0) |
            Q(retirement_year__isnull=True, debut_year__isnull=False)
        ).order_by('-period_matches', '-trailing_matches', '-total_matches')

        scores = []
        for wrestler in wrestlers:
            score_data = self._calculate_wrestler_score(wrestler, start_date, end_date)
            scores.append(score_data)

        # Sort by total score and limit
        scores.sort(key=lambda x: x['total_score'], reverse=True)
        return scores[:limit]

    def _calculate_wrestler_score(self, wrestler, start_date, end_date) -> dict:
        """Calculate score components for a wrestler."""
        # Component scores with proprietary weights
        match_score = self._calc_match_score(wrestler)
        importance_score = self._calc_importance_score(wrestler)
        title_score = self._calc_title_score(wrestler, start_date, end_date)
        opponent_score = self._calc_opponent_score(wrestler)
        news_score = self._calc_news_score(wrestler)
        social_score = self._calc_social_score(wrestler)
        views_score = self._calc_views_score(wrestler)

        total = (
            match_score + importance_score + title_score +
            opponent_score + news_score + social_score + views_score
        )

        # Get previous rank if exists
        prev_rank = None
        if self._previous_ranking:
            prev_entry = Hot100Entry.objects.filter(
                ranking=self._previous_ranking,
                wrestler=wrestler
            ).first()
            if prev_entry:
                prev_rank = prev_entry.rank

        return {
            'wrestler_id': wrestler.id,
            'wrestler': wrestler,
            'total_score': round(total, 2),
            'match_count_score': round(match_score, 2),
            'match_importance_score': round(importance_score, 2),
            'title_activity_score': round(title_score, 2),
            'opponent_quality_score': round(opponent_score, 2),
            'news_mention_score': round(news_score, 2),
            'social_engagement_score': round(social_score, 2),
            'website_views_score': round(views_score, 2),
            'previous_rank': prev_rank,
        }

    def _calc_match_score(self, wrestler) -> float:
        """Calculate score based on match count."""
        # Uses logarithmic scaling to prevent runaway scores
        import math
        period_matches = getattr(wrestler, 'period_matches', 0)
        trailing_matches = getattr(wrestler, 'trailing_matches', 0)
        total_matches = getattr(wrestler, 'total_matches', 0)

        # Priority: current month > trailing 12 months > all-time (with decay)
        if period_matches > 0:
            return min(math.log(period_matches + 1) * 8.7, 35)
        elif trailing_matches > 0:
            return min(math.log(trailing_matches + 1) * 5.2, 25)  # Reduced weight for older
        elif total_matches > 0:
            return min(math.log(total_matches + 1) * 2.5, 15)  # Further reduced for historical
        return 0

    def _calc_importance_score(self, wrestler) -> float:
        """Calculate score based on match importance."""
        main_events = getattr(wrestler, 'period_main_events', 0)
        title_matches = getattr(wrestler, 'period_title_matches', 0)
        return (main_events * 4.2) + (title_matches * 3.1)

    def _calc_title_score(self, wrestler, start_date, end_date) -> float:
        """Calculate score based on title activity."""
        # Title matches where this wrestler won in the period
        title_wins = Match.objects.filter(
            wrestlers=wrestler,
            winner=wrestler,
            title__isnull=False,
            event__date__gte=start_date,
            event__date__lt=end_date
        ).count()
        # Title matches where wrestler participated (defenses, challenges)
        title_participations = Match.objects.filter(
            wrestlers=wrestler,
            title__isnull=False,
            event__date__gte=start_date,
            event__date__lt=end_date
        ).count()
        title_defenses = title_participations - title_wins
        return (title_wins * 12.5) + (title_defenses * 5.8)

    def _calc_opponent_score(self, wrestler) -> float:
        """Calculate score based on opponent quality from previous rankings."""
        if not self._previous_ranking:
            return 0
        # Opponents who were in last month's Hot 100
        from django.db.models import Avg
        opponent_ranks = Hot100Entry.objects.filter(
            ranking=self._previous_ranking,
            wrestler__matches__wrestlers=wrestler
        ).exclude(wrestler=wrestler).values_list('rank', flat=True)

        if not opponent_ranks:
            return 0

        # Higher score for facing higher-ranked opponents
        avg_rank = sum(opponent_ranks) / len(opponent_ranks)
        quality_bonus = max(0, (50 - avg_rank) * 0.15)
        return quality_bonus * len(opponent_ranks) * 0.3

    def _calc_news_score(self, wrestler) -> float:
        """
        Calculate score based on news mentions.
        Currently returns placeholder - would integrate with news API.
        """
        # TODO: Integrate with news aggregation service
        # For now, use deterministic score based on wrestler data richness
        import hashlib
        score = 0

        # Active wrestlers get bonus
        if wrestler.retirement_year is None and wrestler.debut_year:
            score += 4.0

        # Wrestlers with rich profiles get news bonus (implies notability)
        if wrestler.about and len(wrestler.about) > 200:
            score += 3.0
        if wrestler.wikipedia_url:
            score += 2.5

        # Add deterministic variation based on wrestler name
        hash_val = int(hashlib.md5(wrestler.name.encode()).hexdigest()[:8], 16)
        variation = (hash_val % 100) / 100 * 3.0  # 0-3 variation
        return min(score + variation, 15)

    def _calc_social_score(self, wrestler) -> float:
        """
        Calculate score based on social/media engagement.
        Currently returns placeholder - would integrate with YouTube API.
        """
        # TODO: Integrate with YouTube Data API, podcast mentions
        import hashlib
        score = 0

        # Recent active wrestlers likely have more social engagement
        if wrestler.debut_year and wrestler.debut_year >= 2010:
            score += 3.0
        if wrestler.retirement_year is None:
            score += 2.0

        # Wrestlers with multiple data sources are more notable
        sources = sum([
            bool(wrestler.wikipedia_url),
            bool(wrestler.cagematch_url),
            bool(wrestler.profightdb_url),
        ])
        score += sources * 1.2

        # Deterministic variation
        hash_val = int(hashlib.md5(f"{wrestler.name}_social".encode()).hexdigest()[:8], 16)
        variation = (hash_val % 100) / 100 * 2.0
        return min(score + variation, 10)

    def _calc_views_score(self, wrestler) -> float:
        """
        Calculate score based on page views on this website.
        Currently returns placeholder - would integrate with analytics.
        """
        # TODO: Integrate with site analytics
        import hashlib
        # Deterministic variation based on wrestler
        hash_val = int(hashlib.md5(f"{wrestler.name}_views".encode()).hexdigest()[:8], 16)
        base = (hash_val % 100) / 100 * 4.0

        # Boost for wrestlers with images (more likely to be viewed)
        if wrestler.image_url:
            base += 1.5

        return min(base, 5)

    def generate_ranking(self, publish: bool = False) -> Hot100Ranking:
        """Generate and save Hot 100 ranking for the month."""
        # Check if ranking already exists
        existing = Hot100Ranking.objects.filter(
            year=self.year, month=self.month
        ).first()

        if existing:
            # Delete old entries to regenerate
            existing.entries.all().delete()
            ranking = existing
        else:
            ranking = Hot100Ranking.objects.create(
                year=self.year,
                month=self.month
            )

        # Calculate scores
        scores = self.calculate_rankings(limit=100)

        # Create entries
        for i, score_data in enumerate(scores, 1):
            rank_change = 0
            if score_data['previous_rank']:
                rank_change = score_data['previous_rank'] - i  # Positive = improved

            Hot100Entry.objects.create(
                ranking=ranking,
                wrestler=score_data['wrestler'],
                rank=i,
                total_score=score_data['total_score'],
                match_count_score=score_data['match_count_score'],
                match_importance_score=score_data['match_importance_score'],
                title_activity_score=score_data['title_activity_score'],
                opponent_quality_score=score_data['opponent_quality_score'],
                news_mention_score=score_data['news_mention_score'],
                social_engagement_score=score_data['social_engagement_score'],
                website_views_score=score_data['website_views_score'],
                previous_rank=score_data['previous_rank'],
                rank_change=rank_change,
            )

        if publish:
            ranking.is_published = True
            ranking.save()

        return ranking
