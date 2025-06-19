from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils.crypto import get_random_string

from .models import (
    Promotion,
    VideoGame,
    Podcast,
    Book,
    Special,
    Title,
    Venue,
    APIKey,
)


def index(request):
    return render(request, 'index.html')


def promotions(request):
    return render(request, 'promotions.html', {'promotions': Promotion.objects.all()})


def games(request):
    return render(request, 'games.html', {'games': VideoGame.objects.all()})


def podcasts(request):
    return render(request, 'podcasts.html', {'podcasts': Podcast.objects.all()})


def books(request):
    return render(request, 'books.html', {'books': Book.objects.all()})


def specials(request):
    return render(request, 'specials.html', {'specials': Special.objects.all()})


def titles(request):
    return render(request, 'titles.html', {'titles': Title.objects.all()})


def venues(request):
    return render(request, 'venues.html', {'venues': Venue.objects.all()})


@login_required
def account(request):
    if request.method == 'POST':
        key = get_random_string(32)
        APIKey.objects.create(user=request.user, key=key)
    api_keys = APIKey.objects.filter(user=request.user)
    return render(request, 'account.html', {'api_keys': api_keys})


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('index')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')
