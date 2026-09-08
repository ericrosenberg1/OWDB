"""
Serializers for the v1 REST API.

Shape philosophy (deliberately similar to, but simpler than, TMDB's
`append_to_response`): a detail or list response should answer the obvious
first question about a row without a second round-trip — a Match should
show wrestler *names*, not bare ids — but nesting stops at one level.
Every relation below is represented by one of the small "*LiteSerializer"
classes (id/name/slug, at most a couple more fields), never a full nested
serializer, so a Match never drags in its Event's Promotion's whole
row, etc. Deeper, opt-in expansion (an actual `append_to_response`-style
mechanism) is a reasonable v2, not built here.

Every serializer here is read-only in practice — each is only ever used
from a ReadOnlyModelViewSet (api/views.py) — so the nested serializers on
M2M/FK fields below need no `create`/`update` support.
"""

from rest_framework import serializers

from owdb_django.owdbapp.models import (
    Book,
    Event,
    Match,
    Podcast,
    Promotion,
    Special,
    Stable,
    Title,
    Venue,
    VideoGame,
    Wrestler,
)

# =============================================================================
# "Lite" nested serializers — the one level of nesting every other
# serializer below is allowed to use for a related object.
# =============================================================================


class WrestlerLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wrestler
        fields = ["id", "name", "slug"]


class PromotionLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = ["id", "name", "slug", "abbreviation"]


class VenueLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = ["id", "name", "slug", "location"]


class EventLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ["id", "name", "slug", "date"]


class TitleLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Title
        fields = ["id", "name", "slug"]


# =============================================================================
# Full serializers — one per resource, used for both list and detail.
# =============================================================================


class WrestlerSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()
    is_deceased = serializers.ReadOnlyField()

    class Meta:
        model = Wrestler
        fields = [
            "id",
            "name",
            "slug",
            "real_name",
            "aliases",
            "finishers",
            "about",
            "hometown",
            "nationality",
            "debut_year",
            "retirement_year",
            "birth_date",
            "death_date",
            "height",
            "weight",
            "roles",
            "is_active",
            "is_deceased",
            "verification_state",
            "image_url",
            "wikipedia_url",
        ]


class PromotionSerializer(serializers.ModelSerializer):
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Promotion
        fields = [
            "id",
            "name",
            "slug",
            "abbreviation",
            "nicknames",
            "founded_year",
            "closed_year",
            "is_active",
            "website",
            "about",
            "headquarters",
            "founder",
            "verification_state",
            "image_url",
        ]


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = [
            "id",
            "name",
            "slug",
            "location",
            "city",
            "country",
            "capacity",
            "opened_year",
            "about",
            "verification_state",
            "image_url",
        ]


class EventSerializer(serializers.ModelSerializer):
    promotion = PromotionLiteSerializer(read_only=True)
    venue = VenueLiteSerializer(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "name",
            "slug",
            "promotion",
            "venue",
            "date",
            "attendance",
            "event_type",
            "about",
            "verification_state",
            "image_url",
        ]


class TitleSerializer(serializers.ModelSerializer):
    promotion = PromotionLiteSerializer(read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Title
        fields = [
            "id",
            "name",
            "slug",
            "promotion",
            "title_type",
            "debut_year",
            "retirement_year",
            "is_active",
            "about",
            "verification_state",
            "image_url",
        ]


class MatchSerializer(serializers.ModelSerializer):
    event = EventLiteSerializer(read_only=True)
    wrestlers = WrestlerLiteSerializer(many=True, read_only=True)
    winner = WrestlerLiteSerializer(read_only=True)
    title = TitleLiteSerializer(read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "event",
            "wrestlers",
            "match_text",
            "result",
            "winner",
            "winning_side",
            "match_type",
            "outcome_type",
            "duration_seconds",
            "title",
            "title_changed",
            "match_order",
            "about",
            "cagematch_rating",
            "cagematch_rating_count",
            "observer_stars",
            "verification_state",
        ]


class StableSerializer(serializers.ModelSerializer):
    promotion = PromotionLiteSerializer(read_only=True)
    members = WrestlerLiteSerializer(many=True, read_only=True)
    leaders = WrestlerLiteSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Stable
        fields = [
            "id",
            "name",
            "slug",
            "promotion",
            "members",
            "leaders",
            "formed_year",
            "disbanded_year",
            "is_active",
            "about",
            "manager",
            "verification_state",
            "image_url",
        ]


# =============================================================================
# Plain content — no VerificationMixin / verification_state on these four,
# so nothing to gate: exposed exactly as stored.
# =============================================================================


class BookSerializer(serializers.ModelSerializer):
    related_wrestlers = WrestlerLiteSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "title",
            "slug",
            "author",
            "related_wrestlers",
            "publication_year",
            "isbn",
            "publisher",
            "about",
            "image_url",
        ]


class VideoGameSerializer(serializers.ModelSerializer):
    wrestlers = WrestlerLiteSerializer(many=True, read_only=True)
    promotions = PromotionLiteSerializer(many=True, read_only=True)

    class Meta:
        model = VideoGame
        fields = [
            "id",
            "name",
            "slug",
            "wrestlers",
            "promotions",
            "release_year",
            "systems",
            "developer",
            "publisher",
            "about",
            "image_url",
        ]


class PodcastSerializer(serializers.ModelSerializer):
    host_wrestlers = WrestlerLiteSerializer(many=True, read_only=True)
    is_active = serializers.ReadOnlyField()

    class Meta:
        model = Podcast
        fields = [
            "id",
            "name",
            "slug",
            "hosts",
            "host_wrestlers",
            "launch_year",
            "end_year",
            "is_active",
            "url",
            "rss_feed_url",
            "about",
        ]


class SpecialSerializer(serializers.ModelSerializer):
    related_wrestlers = WrestlerLiteSerializer(many=True, read_only=True)

    class Meta:
        model = Special
        fields = [
            "id",
            "title",
            "slug",
            "release_year",
            "type",
            "director",
            "related_wrestlers",
            "about",
        ]
