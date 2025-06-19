from django.contrib import admin
from django.urls import path, include
from owdb_django.owdbapp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('promotions/', views.promotions, name='promotions'),
    path('games/', views.games, name='games'),
    path('podcasts/', views.podcasts, name='podcasts'),
    path('books/', views.books, name='books'),
    path('specials/', views.specials, name='specials'),
    path('titles/', views.titles, name='titles'),
    path('venues/', views.venues, name='venues'),
    path('account/', views.account, name='account'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
