"""
REST API v1 URL routes.

Every route under /api/ is registered here, via a single DRF
``DefaultRouter``. ``owdb_django/urls.py`` pulls this whole module in with
one ``include()`` — see the comment there. Keeping every API route in this
one file, instead of scattering ``path()`` entries through the main
urlconf, is what keeps that ``include()`` a single, low-conflict line for
anything else in the app to grow around.

Path segments match the equivalent website section
(owdb_django/owdbapp/views.py + owdb_django/urls.py) — "games" for
VideoGame, not "videogames" — so the API's vocabulary matches the site's.
"""

from rest_framework.routers import DefaultRouter

from .api import views as api_views

router = DefaultRouter()
router.register(r"wrestlers", api_views.WrestlerViewSet, basename="api-wrestler")
router.register(r"promotions", api_views.PromotionViewSet, basename="api-promotion")
router.register(r"events", api_views.EventViewSet, basename="api-event")
router.register(r"matches", api_views.MatchViewSet, basename="api-match")
router.register(r"titles", api_views.TitleViewSet, basename="api-title")
router.register(r"venues", api_views.VenueViewSet, basename="api-venue")
router.register(r"stables", api_views.StableViewSet, basename="api-stable")
router.register(r"books", api_views.BookViewSet, basename="api-book")
router.register(r"games", api_views.VideoGameViewSet, basename="api-videogame")
router.register(r"podcasts", api_views.PodcastViewSet, basename="api-podcast")
router.register(r"specials", api_views.SpecialViewSet, basename="api-special")

urlpatterns = router.urls
