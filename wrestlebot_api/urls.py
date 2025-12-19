"""
URL configuration for WrestleBot API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

# Create router for viewsets
router = DefaultRouter()
router.register(r'wrestlers', views.WrestlerViewSet, basename='wrestler')
router.register(r'promotions', views.PromotionViewSet, basename='promotion')
router.register(r'events', views.EventViewSet, basename='event')
router.register(r'venues', views.VenueViewSet, basename='venue')
router.register(r'stables', views.StableViewSet, basename='stable')
router.register(r'videogames', views.VideoGameViewSet, basename='videogame')
router.register(r'books', views.BookViewSet, basename='book')
router.register(r'podcasts', views.PodcastViewSet, basename='podcast')
router.register(r'specials', views.SpecialViewSet, basename='special')

# Additional endpoints
urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Custom endpoints
    path('bulk/import/', views.bulk_import, name='bulk-import'),
    path('status/', views.service_status, name='status'),
    path('health/', views.health_check, name='health'),
]
