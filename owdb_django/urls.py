from django.contrib import admin
from django.urls import path, include
from owdb_django.owdbapp import views

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Homepage
    path('', views.IndexView.as_view(), name='index'),

    # About & Legal
    path('about/', views.AboutView.as_view(), name='about'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),

    # Wrestlers
    path('wrestlers/', views.WrestlerListView.as_view(), name='wrestlers'),
    path('wrestlers/<int:pk>/', views.WrestlerDetailView.as_view(), name='wrestler_detail'),
    path('wrestlers/<slug:slug>/', views.WrestlerDetailView.as_view(), name='wrestler_detail_slug'),

    # Promotions
    path('promotions/', views.PromotionListView.as_view(), name='promotions'),
    path('promotions/<int:pk>/', views.PromotionDetailView.as_view(), name='promotion_detail'),
    path('promotions/<slug:slug>/', views.PromotionDetailView.as_view(), name='promotion_detail_slug'),

    # Events
    path('events/', views.EventListView.as_view(), name='events'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<slug:slug>/', views.EventDetailView.as_view(), name='event_detail_slug'),

    # Matches
    path('matches/', views.MatchListView.as_view(), name='matches'),
    path('matches/<int:pk>/', views.MatchDetailView.as_view(), name='match_detail'),

    # Titles
    path('titles/', views.TitleListView.as_view(), name='titles'),
    path('titles/<int:pk>/', views.TitleDetailView.as_view(), name='title_detail'),
    path('titles/<slug:slug>/', views.TitleDetailView.as_view(), name='title_detail_slug'),

    # Venues
    path('venues/', views.VenueListView.as_view(), name='venues'),
    path('venues/<int:pk>/', views.VenueDetailView.as_view(), name='venue_detail'),
    path('venues/<slug:slug>/', views.VenueDetailView.as_view(), name='venue_detail_slug'),

    # Video Games
    path('games/', views.VideoGameListView.as_view(), name='games'),
    path('games/<int:pk>/', views.VideoGameDetailView.as_view(), name='game_detail'),
    path('games/<slug:slug>/', views.VideoGameDetailView.as_view(), name='game_detail_slug'),

    # Podcasts
    path('podcasts/', views.PodcastListView.as_view(), name='podcasts'),
    path('podcasts/<int:pk>/', views.PodcastDetailView.as_view(), name='podcast_detail'),
    path('podcasts/<slug:slug>/', views.PodcastDetailView.as_view(), name='podcast_detail_slug'),

    # Books
    path('books/', views.BookListView.as_view(), name='books'),
    path('books/<int:pk>/', views.BookDetailView.as_view(), name='book_detail'),
    path('books/<slug:slug>/', views.BookDetailView.as_view(), name='book_detail_slug'),

    # Specials
    path('specials/', views.SpecialListView.as_view(), name='specials'),
    path('specials/<int:pk>/', views.SpecialDetailView.as_view(), name='special_detail'),
    path('specials/<slug:slug>/', views.SpecialDetailView.as_view(), name='special_detail_slug'),

    # Stables & Factions
    path('stables/', views.StableListView.as_view(), name='stables'),
    path('stables/<int:pk>/', views.StableDetailView.as_view(), name='stable_detail'),
    path('stables/<slug:slug>/', views.StableDetailView.as_view(), name='stable_detail_slug'),

    # Podcast Episodes
    path('episodes/<int:pk>/', views.PodcastEpisodeDetailView.as_view(), name='episode_detail'),
    path('episodes/<slug:slug>/', views.PodcastEpisodeDetailView.as_view(), name='episode_detail_slug'),

    # Hot 100 Rankings
    path('hot100/', views.Hot100View.as_view(), name='hot100'),
    path('hot100/<int:year>/<int:month>/', views.Hot100View.as_view(), name='hot100_month'),
    path('hot100/history/', views.Hot100HistoryView.as_view(), name='hot100_history'),

    # Authentication
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Email Verification
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('verification-pending/', views.verification_pending, name='verification_pending'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Account
    path('account/', views.account, name='account'),

    # Health check for Docker/load balancers
    path('health/', views.health_check, name='health'),
]
