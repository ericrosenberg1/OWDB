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

from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView, DefaultRouter

from .api import views as api_views
from .api.authentication import ApiKeyAuthentication


class PublicAPIRootView(APIRootView):
    """
    The index at ``/api/``, open to the same callers as every route it lists.

    ``DefaultRouter`` builds its root view from stock ``APIRootView``, which
    carries no ``permission_classes`` of its own and therefore inherits the
    site-wide ``IsAuthenticated`` + ``TokenAuthentication``/
    ``SessionAuthentication`` defaults from ``settings.REST_FRAMEWORK``.
    That made ``/api/`` answer 401 to everyone: to an anonymous caller, who
    can read every resource it links to, and to a valid ``X-API-Key``
    holder too, since the root view never consulted
    ``ApiKeyAuthentication``. The one URL that exists to tell a consumer
    what the API offers was the only one they could not open. These two
    attributes match ``api.views.PublicReadOnlyViewSet`` so the index is
    exactly as reachable as its contents.
    """

    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [AllowAny]


class PublicAPIRouter(DefaultRouter):
    """``DefaultRouter`` with the root index above instead of the stock one."""

    APIRootView = PublicAPIRootView


router = PublicAPIRouter()
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
