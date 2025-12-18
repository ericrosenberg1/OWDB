"""
Serializers for WrestleBot REST API.

These serializers handle data validation and transformation
between JSON and Django models for the WrestleBot service.
"""

from rest_framework import serializers
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Match, Venue,
    Article, VideoGame, Book, Podcast, Special
)


class WrestlerSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating wrestlers via API."""

    class Meta:
        model = Wrestler
        fields = [
            'id', 'name', 'slug', 'real_name', 'aliases',
            'hometown', 'nationality', 'birth_date', 'death_date',
            'debut_year', 'retirement_year', 'finishers',
            'image_url', 'image_source_url', 'image_license', 'image_credit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Ensure name is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Name cannot be empty")
        return value.strip()


class PromotionSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating promotions via API."""

    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'slug', 'abbreviation',
            'founded_year', 'closed_year', 'website',
            'image_url', 'image_source_url', 'image_license', 'image_credit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating venues via API."""

    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'slug', 'location', 'capacity',
            'image_url', 'image_source_url', 'image_license', 'image_credit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MatchSerializer(serializers.ModelSerializer):
    """Serializer for creating matches."""

    class Meta:
        model = Match
        fields = [
            'id', 'event', 'match_text', 'result',
            'match_type', 'match_order', 'rating',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating events via API."""

    matches = MatchSerializer(many=True, required=False)
    venue_name = serializers.CharField(write_only=True, required=False)
    venue_location = serializers.CharField(write_only=True, required=False)
    promotion_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Event
        fields = [
            'id', 'name', 'slug', 'date', 'venue', 'promotion',
            'venue_name', 'venue_location', 'promotion_name',
            'attendance', 'matches',
            'image_url', 'image_source_url', 'image_license', 'image_credit',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'venue', 'promotion', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create event with venue and promotion lookup/creation."""
        matches_data = validated_data.pop('matches', [])
        venue_name = validated_data.pop('venue_name', None)
        venue_location = validated_data.pop('venue_location', None)
        promotion_name = validated_data.pop('promotion_name', None)

        # Handle venue
        venue = None
        if venue_name:
            from django.utils.text import slugify
            venue, _ = Venue.objects.get_or_create(
                name=venue_name,
                defaults={
                    'slug': slugify(venue_name),
                    'location': venue_location or ''
                }
            )

        # Handle promotion
        promotion = None
        if promotion_name:
            from django.utils.text import slugify
            promotion, _ = Promotion.objects.get_or_create(
                name=promotion_name,
                defaults={'slug': slugify(promotion_name)}
            )

        validated_data['venue'] = venue
        validated_data['promotion'] = promotion

        event = Event.objects.create(**validated_data)

        # Create matches
        for match_data in matches_data:
            Match.objects.create(event=event, **match_data)

        return event


class ArticleSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating articles via API."""

    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Article
        fields = [
            'id', 'title', 'slug', 'content', 'summary',
            'category', 'tags', 'author', 'source_url',
            'published_date', 'created_at', 'updated_at', 'is_published'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        """Create article with tags."""
        tags = validated_data.pop('tags', [])
        article = Article.objects.create(**validated_data)

        # Add tags if provided
        if tags:
            article.tags = ','.join(tags)
            article.save()

        return article

    def update(self, instance, validated_data):
        """Update article with tags."""
        tags = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if tags is not None:
            instance.tags = ','.join(tags)

        instance.save()
        return instance


class VideoGameSerializer(serializers.ModelSerializer):
    """Serializer for video games."""

    class Meta:
        model = VideoGame
        fields = [
            'id', 'name', 'slug', 'release_year', 'systems',
            'developer', 'publisher', 'about',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BookSerializer(serializers.ModelSerializer):
    """Serializer for books."""

    class Meta:
        model = Book
        fields = [
            'id', 'title', 'slug', 'author', 'publication_year',
            'isbn', 'publisher', 'about',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PodcastSerializer(serializers.ModelSerializer):
    """Serializer for podcasts."""

    class Meta:
        model = Podcast
        fields = [
            'id', 'name', 'slug', 'hosts', 'launch_year',
            'end_year', 'url', 'about',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SpecialSerializer(serializers.ModelSerializer):
    """Serializer for specials (movies/TV)."""

    class Meta:
        model = Special
        fields = [
            'id', 'title', 'slug', 'release_year', 'type',
            'about', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class BulkImportSerializer(serializers.Serializer):
    """Serializer for bulk import operations."""

    wrestlers = WrestlerSerializer(many=True, required=False)
    promotions = PromotionSerializer(many=True, required=False)
    events = EventSerializer(many=True, required=False)
    articles = ArticleSerializer(many=True, required=False)
    videogames = VideoGameSerializer(many=True, required=False)
    books = BookSerializer(many=True, required=False)
    podcasts = PodcastSerializer(many=True, required=False)
    specials = SpecialSerializer(many=True, required=False)

    def create(self, validated_data):
        """Process bulk import."""
        results = {
            'wrestlers': {'created': 0, 'updated': 0, 'errors': []},
            'promotions': {'created': 0, 'updated': 0, 'errors': []},
            'events': {'created': 0, 'updated': 0, 'errors': []},
            'articles': {'created': 0, 'updated': 0, 'errors': []},
            'videogames': {'created': 0, 'updated': 0, 'errors': []},
            'books': {'created': 0, 'updated': 0, 'errors': []},
            'podcasts': {'created': 0, 'updated': 0, 'errors': []},
            'specials': {'created': 0, 'updated': 0, 'errors': []},
        }

        # Import wrestlers
        for wrestler_data in validated_data.get('wrestlers', []):
            try:
                wrestler, created = Wrestler.objects.update_or_create(
                    slug=wrestler_data['slug'],
                    defaults=wrestler_data
                )
                if created:
                    results['wrestlers']['created'] += 1
                else:
                    results['wrestlers']['updated'] += 1
            except Exception as e:
                results['wrestlers']['errors'].append(str(e))

        # Import promotions
        for promotion_data in validated_data.get('promotions', []):
            try:
                promotion, created = Promotion.objects.update_or_create(
                    slug=promotion_data['slug'],
                    defaults=promotion_data
                )
                if created:
                    results['promotions']['created'] += 1
                else:
                    results['promotions']['updated'] += 1
            except Exception as e:
                results['promotions']['errors'].append(str(e))

        # Similar for other entity types...

        return results


class StatusSerializer(serializers.Serializer):
    """Serializer for service status."""

    status = serializers.CharField()
    version = serializers.CharField()
    timestamp = serializers.DateTimeField()
    database_connected = serializers.BooleanField()
    total_wrestlers = serializers.IntegerField()
    total_promotions = serializers.IntegerField()
    total_events = serializers.IntegerField()
    total_articles = serializers.IntegerField()
