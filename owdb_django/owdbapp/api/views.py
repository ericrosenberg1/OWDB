"""
Read-only ViewSets for the v1 REST API.

Every gated resource's ``get_queryset()`` calls ``.public()`` — the same
``VerificationQuerySet.public()`` review gate the website's own views use
(see owdb_django/owdbapp/views.py, e.g. ``WrestlerListView``/
``WrestlerDetailView``) — so a ``rejected`` row is exactly as invisible
through the API as it already is on the site: absent from the list,
404 on direct ``/api/<resource>/<id>/`` access (DRF's ``get_object()``
calls ``get_queryset()`` too, via ``generics.GenericAPIView``, so the
gate applies to both list and detail for free).

``select_related``/``prefetch_related`` choices below mirror the
equivalent website view (or the fields the serializer actually nests,
for the four plain-content models that have no website-view precedent),
so listing a page of results doesn't N+1 per row.
"""

from rest_framework import viewsets
from rest_framework.permissions import AllowAny

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

from . import serializers as api_serializers
from .authentication import ApiKeyAuthentication


class PublicReadOnlyViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Shared base for every v1 resource.

    ``AllowAny`` overrides the site-wide ``IsAuthenticated`` default from
    ``settings.REST_FRAMEWORK`` so a GET works with no credentials at all,
    at the anonymous throttle tier — v1 is browse-for-free, key-for-a-
    higher-ceiling (TMDB's model), never key-required, and it's read-only
    besides, so there's nothing here worth gating behind a login.
    ``ApiKeyAuthentication`` is the only authenticator: this deliberately
    does NOT fall back to DRF's TokenAuthentication or SessionAuthentication
    (both still in the site-wide default), so a logged-in website session
    cookie never silently grants API access without a key, and an
    ``Authorization: Token ...`` header (unused — see authentication.py)
    is simply ignored rather than accepted.
    """

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [AllowAny]


class WrestlerViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.WrestlerSerializer

    def get_queryset(self):
        # Meta.ordering (["name"]) applies automatically; no explicit
        # order_by needed, matching WrestlerListView/WrestlerDetailView.
        return Wrestler.objects.public()


class PromotionViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.PromotionSerializer

    def get_queryset(self):
        return Promotion.objects.public()


class VenueViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.VenueSerializer

    def get_queryset(self):
        return Venue.objects.public()


class EventViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.EventSerializer

    def get_queryset(self):
        # select_related matches EventListView/EventDetailView; Meta.ordering
        # (["-date"]) applies automatically.
        return Event.objects.public().select_related("promotion", "venue")


class TitleViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.TitleSerializer

    def get_queryset(self):
        # select_related matches TitleListView/TitleDetailView.
        return Title.objects.public().select_related("promotion")


class MatchViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.MatchSerializer

    def get_queryset(self):
        # select_related/prefetch_related mirrors what MatchSerializer
        # actually nests (event, title, winner, wrestlers); Meta.ordering
        # (["event", "match_order"]) applies automatically.
        return (
            Match.objects.public()
            .select_related("event", "title", "winner")
            .prefetch_related("wrestlers")
        )


class StableViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.StableSerializer

    def get_queryset(self):
        # select_related/prefetch_related matches StableListView/StableDetailView.
        return (
            Stable.objects.public()
            .select_related("promotion")
            .prefetch_related("members", "leaders")
        )


# =============================================================================
# Plain content — no VerificationMixin, so no .public() gate to apply;
# exposed exactly as stored, same as their website ListView/DetailView.
# =============================================================================


class BookViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.BookSerializer

    def get_queryset(self):
        return Book.objects.prefetch_related("related_wrestlers")


class VideoGameViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.VideoGameSerializer

    def get_queryset(self):
        return VideoGame.objects.prefetch_related("wrestlers", "promotions")


class PodcastViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.PodcastSerializer

    def get_queryset(self):
        return Podcast.objects.prefetch_related("host_wrestlers")


class SpecialViewSet(PublicReadOnlyViewSet):
    serializer_class = api_serializers.SpecialSerializer

    def get_queryset(self):
        return Special.objects.prefetch_related("related_wrestlers")
