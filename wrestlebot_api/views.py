"""
Views for WrestleBot REST API.

These views provide endpoints for the standalone WrestleBot service
to create, update, and manage wrestling database content.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import connection

from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Venue,
    VideoGame, Book, Podcast, Special
)

from .serializers import (
    WrestlerSerializer, PromotionSerializer, EventSerializer,
    VenueSerializer, VideoGameSerializer,
    BookSerializer, PodcastSerializer, SpecialSerializer,
    BulkImportSerializer, StatusSerializer
)
from .permissions import IsWrestleBot


class WrestlerViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing wrestlers.

    Supports:
    - GET /wrestlers/ - List all wrestlers
    - POST /wrestlers/ - Create new wrestler
    - GET /wrestlers/{id}/ - Get wrestler detail
    - PUT /wrestlers/{id}/ - Update wrestler
    - PATCH /wrestlers/{id}/ - Partial update
    - DELETE /wrestlers/{id}/ - Delete wrestler
    """

    queryset = Wrestler.objects.all()
    serializer_class = WrestlerSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'

    def create(self, request, *args, **kwargs):
        """Create or update wrestler if already exists."""
        slug = request.data.get('slug')

        if slug:
            try:
                wrestler = Wrestler.objects.get(slug=slug)
                serializer = self.get_serializer(wrestler, data=request.data, partial=False)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Wrestler.DoesNotExist:
                pass

        return super().create(request, *args, **kwargs)


class PromotionViewSet(viewsets.ModelViewSet):
    """API endpoint for managing promotions."""

    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'

    def create(self, request, *args, **kwargs):
        """Create or update promotion if already exists."""
        slug = request.data.get('slug')

        if slug:
            try:
                promotion = Promotion.objects.get(slug=slug)
                serializer = self.get_serializer(promotion, data=request.data, partial=False)
                serializer.is_valid(raise_exception=True)
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Promotion.DoesNotExist:
                pass

        return super().create(request, *args, **kwargs)


class EventViewSet(viewsets.ModelViewSet):
    """API endpoint for managing events."""

    queryset = Event.objects.all()
    serializer_class = EventSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


class VenueViewSet(viewsets.ModelViewSet):
    """API endpoint for managing venues."""

    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


class VideoGameViewSet(viewsets.ModelViewSet):
    """API endpoint for managing video games."""

    queryset = VideoGame.objects.all()
    serializer_class = VideoGameSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


class BookViewSet(viewsets.ModelViewSet):
    """API endpoint for managing books."""

    queryset = Book.objects.all()
    serializer_class = BookSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


class PodcastViewSet(viewsets.ModelViewSet):
    """API endpoint for managing podcasts."""

    queryset = Podcast.objects.all()
    serializer_class = PodcastSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


class SpecialViewSet(viewsets.ModelViewSet):
    """API endpoint for managing specials (movies/TV)."""

    queryset = Special.objects.all()
    serializer_class = SpecialSerializer
    permission_classes = [IsWrestleBot]
    lookup_field = 'slug'


@api_view(['POST'])
@permission_classes([IsWrestleBot])
def bulk_import(request):
    """
    Bulk import multiple entity types at once.

    POST /api/wrestlebot/bulk/import/

    Body:
    {
        "wrestlers": [...],
        "promotions": [...],
        "events": [...],
        "articles": [...]
    }

    Returns:
    {
        "wrestlers": {"created": 10, "updated": 5, "errors": []},
        "promotions": {"created": 3, "updated": 2, "errors": []},
        ...
    }
    """
    serializer = BulkImportSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    results = serializer.save()
    return Response(results, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsWrestleBot])
def service_status(request):
    """
    Get service status and statistics.

    GET /api/wrestlebot/status/

    Returns:
    {
        "status": "healthy",
        "version": "2.0.0",
        "timestamp": "2025-12-18T12:00:00Z",
        "database_connected": true,
        "total_wrestlers": 1234,
        "total_promotions": 45,
        "total_events": 567,
        "total_articles": 890
    }
    """
    # Check database connection
    db_connected = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_connected = True
    except Exception:
        pass

    data = {
        'status': 'healthy' if db_connected else 'degraded',
        'version': '2.0.0',
        'timestamp': timezone.now(),
        'database_connected': db_connected,
        'total_wrestlers': Wrestler.objects.count(),
        'total_promotions': Promotion.objects.count(),
        'total_events': Event.objects.count(),
    }

    serializer = StatusSerializer(data)
    return Response(serializer.data)


@api_view(['GET'])
def health_check(request):
    """
    Public health check endpoint (no authentication required).

    GET /api/wrestlebot/health/

    Returns:
    {
        "status": "ok",
        "timestamp": "2025-12-18T12:00:00Z"
    }
    """
    return Response({
        'status': 'ok',
        'timestamp': timezone.now()
    })
