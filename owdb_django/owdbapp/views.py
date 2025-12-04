from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django import forms
from datetime import timedelta

from .models import (
    Wrestler,
    Promotion,
    Event,
    Match,
    Title,
    Venue,
    VideoGame,
    Podcast,
    Book,
    Special,
    APIKey,
    UserProfile,
    EmailVerificationToken,
)


# =============================================================================
# Custom Forms
# =============================================================================

class SignupForm(forms.Form):
    """Custom signup form with email requirement."""
    username = forms.CharField(
        max_length=150,
        min_length=3,
        help_text='Required. 3-150 characters. Letters, digits and @/./+/-/_ only.'
    )
    email = forms.EmailField(
        help_text='Required. A valid email address for verification.'
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput,
        min_length=8,
        help_text='At least 8 characters.'
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput,
        help_text='Enter the same password again.'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        return cleaned_data


class PaginatedListView(ListView):
    """Base class for paginated list views with search support."""
    paginate_by = 25
    search_fields = []

    def get_paginate_by(self, queryset):
        """Allow per_page parameter to override default pagination."""
        per_page = self.request.GET.get('per_page')
        if per_page and per_page.isdigit() and int(per_page) in [25, 50, 100]:
            return int(per_page)
        return self.paginate_by

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': query})
            queryset = queryset.filter(q_objects)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_placeholder'] = getattr(self, 'search_placeholder', self.model.__name__.lower() + 's')
        return context


# =============================================================================
# Homepage
# =============================================================================

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Home'
        context['stats'] = {
            'wrestlers': Wrestler.objects.count(),
            'promotions': Promotion.objects.count(),
            'events': Event.objects.count(),
            'matches': Match.objects.count(),
            'titles': Title.objects.count(),
            'venues': Venue.objects.count(),
        }
        # Get recent additions
        context['recent_wrestlers'] = Wrestler.objects.order_by('-created_at')[:10]
        context['recent_events'] = Event.objects.select_related('promotion').order_by('-created_at')[:10]
        return context


# =============================================================================
# About Page
# =============================================================================

class AboutView(TemplateView):
    template_name = 'about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'About OWDB'
        context['stats'] = {
            'wrestlers': Wrestler.objects.count(),
            'promotions': Promotion.objects.count(),
            'events': Event.objects.count(),
            'matches': Match.objects.count(),
            'titles': Title.objects.count(),
            'venues': Venue.objects.count(),
            'games': VideoGame.objects.count(),
            'books': Book.objects.count(),
            'podcasts': Podcast.objects.count(),
            'specials': Special.objects.count(),
        }
        return context


# =============================================================================
# Wrestler Views
# =============================================================================

class WrestlerListView(PaginatedListView):
    model = Wrestler
    template_name = 'wrestlers.html'
    context_object_name = 'wrestlers'
    search_fields = ['name', 'real_name', 'aliases', 'hometown', 'nationality']
    search_placeholder = 'wrestlers by name, alias, hometown...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Wrestlers'
        return context


class WrestlerDetailView(DetailView):
    model = Wrestler
    template_name = 'wrestler_detail.html'
    context_object_name = 'wrestler'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['matches'] = self.object.matches.select_related('event', 'event__promotion')[:20]
        return context


# =============================================================================
# Promotion Views
# =============================================================================

class PromotionListView(PaginatedListView):
    model = Promotion
    template_name = 'promotions.html'
    context_object_name = 'promotions'
    search_fields = ['name', 'abbreviation', 'nicknames']
    search_placeholder = 'promotions by name or abbreviation...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Promotions'
        return context


class PromotionDetailView(DetailView):
    model = Promotion
    template_name = 'promotion_detail.html'
    context_object_name = 'promotion'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['events'] = self.object.events.order_by('-date')[:20]
        context['titles'] = self.object.titles.all()
        return context


# =============================================================================
# Event Views
# =============================================================================

class EventListView(PaginatedListView):
    model = Event
    template_name = 'events.html'
    context_object_name = 'events'
    search_fields = ['name', 'promotion__name', 'venue__name']
    search_placeholder = 'events by name, promotion, or venue...'

    def get_queryset(self):
        return super().get_queryset().select_related('promotion', 'venue')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Events'
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return super().get_queryset().select_related('promotion', 'venue')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['matches'] = self.object.matches.prefetch_related('wrestlers').order_by('match_order')
        return context


# =============================================================================
# Match Views
# =============================================================================

class MatchListView(PaginatedListView):
    model = Match
    template_name = 'matches.html'
    context_object_name = 'matches'
    search_fields = ['match_text', 'event__name', 'match_type']
    search_placeholder = 'matches by description, event, or type...'

    def get_queryset(self):
        return super().get_queryset().select_related('event', 'event__promotion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Matches'
        return context


class MatchDetailView(DetailView):
    model = Match
    template_name = 'match_detail.html'
    context_object_name = 'match'

    def get_queryset(self):
        return super().get_queryset().select_related('event', 'event__promotion', 'title', 'winner').prefetch_related('wrestlers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.match_text
        return context


# =============================================================================
# Title Views
# =============================================================================

class TitleListView(PaginatedListView):
    model = Title
    template_name = 'titles.html'
    context_object_name = 'titles'
    search_fields = ['name', 'promotion__name']
    search_placeholder = 'titles by name or promotion...'

    def get_queryset(self):
        return super().get_queryset().select_related('promotion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Titles'
        return context


class TitleDetailView(DetailView):
    model = Title
    template_name = 'title_detail.html'
    context_object_name = 'title'

    def get_queryset(self):
        return super().get_queryset().select_related('promotion')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['title_matches'] = self.object.title_matches.select_related('event')[:20]
        return context


# =============================================================================
# Venue Views
# =============================================================================

class VenueListView(PaginatedListView):
    model = Venue
    template_name = 'venues.html'
    context_object_name = 'venues'
    search_fields = ['name', 'location']
    search_placeholder = 'venues by name or location...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Venues'
        return context


class VenueDetailView(DetailView):
    model = Venue
    template_name = 'venue_detail.html'
    context_object_name = 'venue'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        context['events'] = self.object.events.select_related('promotion').order_by('-date')[:20]
        return context


# =============================================================================
# Video Game Views
# =============================================================================

class VideoGameListView(PaginatedListView):
    model = VideoGame
    template_name = 'games.html'
    context_object_name = 'games'
    search_fields = ['name', 'systems', 'developer', 'publisher']
    search_placeholder = 'games by name, system, developer...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Video Games'
        return context


class VideoGameDetailView(DetailView):
    model = VideoGame
    template_name = 'game_detail.html'
    context_object_name = 'game'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('promotions')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        return context


# =============================================================================
# Podcast Views
# =============================================================================

class PodcastListView(PaginatedListView):
    model = Podcast
    template_name = 'podcasts.html'
    context_object_name = 'podcasts'
    search_fields = ['name', 'hosts']
    search_placeholder = 'podcasts by name or host...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Podcasts'
        return context


class PodcastDetailView(DetailView):
    model = Podcast
    template_name = 'podcast_detail.html'
    context_object_name = 'podcast'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('related_wrestlers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.name
        return context


# =============================================================================
# Book Views
# =============================================================================

class BookListView(PaginatedListView):
    model = Book
    template_name = 'books.html'
    context_object_name = 'books'
    search_fields = ['title', 'author', 'isbn']
    search_placeholder = 'books by title, author, or ISBN...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Books'
        return context


class BookDetailView(DetailView):
    model = Book
    template_name = 'book_detail.html'
    context_object_name = 'book'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('related_wrestlers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.title
        return context


# =============================================================================
# Special Views
# =============================================================================

class SpecialListView(PaginatedListView):
    model = Special
    template_name = 'specials.html'
    context_object_name = 'specials'
    search_fields = ['title', 'type']
    search_placeholder = 'specials by title or type...'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Specials & Movies'
        return context


class SpecialDetailView(DetailView):
    model = Special
    template_name = 'special_detail.html'
    context_object_name = 'special'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('related_wrestlers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.title
        return context


# =============================================================================
# Authentication Views
# =============================================================================

def signup(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            # Create user
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password1']
            )
            # Create user profile (email not verified yet)
            UserProfile.objects.create(user=user, email_verified=False, can_contribute=False)

            # Create verification token
            token = EmailVerificationToken.generate_token()
            expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)
            EmailVerificationToken.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timedelta(hours=expiry_hours)
            )

            # Send verification email
            verification_url = request.build_absolute_uri(f'/verify-email/{token}/')
            try:
                send_mail(
                    subject='Verify your OWDB account',
                    message=f'''Welcome to OWDB - The Open Wrestling Database!

Please click the link below to verify your email address:

{verification_url}

This link will expire in {expiry_hours} hours.

If you didn't create an account on OWDB, you can ignore this email.

And that's the bottom line, 'cause OWDB said so!
''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                messages.success(request, 'Account created! Please check your email to verify your account.')
            except Exception as e:
                messages.warning(request, 'Account created, but we could not send verification email. Please contact support.')

            # Log user in but they won't be able to contribute until verified
            login(request, user)
            return redirect('verification_pending')
    else:
        form = SignupForm()
    return render(request, 'signup.html', {
        'form': form,
        'page_title': 'Sign Up'
    })


def verify_email(request, token):
    """Handle email verification link clicks."""
    try:
        verification = EmailVerificationToken.objects.get(token=token)
        if not verification.is_valid:
            if verification.used:
                messages.info(request, 'This verification link has already been used.')
            else:
                messages.error(request, 'This verification link has expired. Please request a new one.')
            return redirect('login')

        # Mark token as used
        verification.used = True
        verification.save()

        # Update user profile
        profile, created = UserProfile.objects.get_or_create(user=verification.user)
        profile.email_verified = True
        profile.can_contribute = True
        profile.save()

        messages.success(request, 'Email verified! You can now contribute to OWDB. Welcome to the community!')

        # Log the user in if not already
        if not request.user.is_authenticated:
            login(request, verification.user)

        return redirect('index')

    except EmailVerificationToken.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('login')


def verification_pending(request):
    """Show verification pending page."""
    return render(request, 'verification_pending.html', {
        'page_title': 'Verify Your Email'
    })


@login_required
def resend_verification(request):
    """Resend verification email."""
    try:
        profile = request.user.profile
        if profile.email_verified:
            messages.info(request, 'Your email is already verified!')
            return redirect('account')
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=request.user, email_verified=False, can_contribute=False)

    # Invalidate old tokens
    EmailVerificationToken.objects.filter(user=request.user, used=False).update(used=True)

    # Create new token
    token = EmailVerificationToken.generate_token()
    expiry_hours = getattr(settings, 'EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24)
    EmailVerificationToken.objects.create(
        user=request.user,
        token=token,
        expires_at=timezone.now() + timedelta(hours=expiry_hours)
    )

    # Send email
    verification_url = request.build_absolute_uri(f'/verify-email/{token}/')
    try:
        send_mail(
            subject='Verify your OWDB account',
            message=f'''Hi {request.user.username},

Please click the link below to verify your email address:

{verification_url}

This link will expire in {expiry_hours} hours.

And that's the bottom line, 'cause OWDB said so!
''',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=False,
        )
        messages.success(request, 'Verification email sent! Please check your inbox.')
    except Exception as e:
        messages.error(request, 'Failed to send verification email. Please try again later.')

    return redirect('verification_pending')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'Welcome back, {form.get_user().username}!')
            next_url = request.GET.get('next', 'index')
            return redirect(next_url)
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {
        'form': form,
        'page_title': 'Login'
    })


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


# =============================================================================
# Account & API Key Management
# =============================================================================

@login_required
def account(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            # Limit to 5 API keys per user
            if APIKey.objects.filter(user=request.user).count() >= 5:
                messages.error(request, 'You can only have up to 5 API keys.')
            else:
                key = APIKey.generate_key()
                name = request.POST.get('key_name', '').strip() or None
                APIKey.objects.create(user=request.user, key=key, name=name)
                messages.success(request, f'API key created: {key[:8]}...')
        elif action == 'delete':
            key_id = request.POST.get('key_id')
            try:
                api_key = APIKey.objects.get(id=key_id, user=request.user)
                api_key.delete()
                messages.success(request, 'API key deleted.')
            except APIKey.DoesNotExist:
                messages.error(request, 'API key not found.')
        elif action == 'toggle':
            key_id = request.POST.get('key_id')
            try:
                api_key = APIKey.objects.get(id=key_id, user=request.user)
                api_key.is_active = not api_key.is_active
                api_key.save()
                status = 'activated' if api_key.is_active else 'deactivated'
                messages.success(request, f'API key {status}.')
            except APIKey.DoesNotExist:
                messages.error(request, 'API key not found.')

    api_keys = APIKey.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'account.html', {
        'api_keys': api_keys,
        'page_title': 'Account'
    })


# =============================================================================
# Health Check (for Docker/Load Balancers)
# =============================================================================

from django.http import JsonResponse
from django.db import connection


def health_check(request):
    """Health check endpoint for Docker and load balancers."""
    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=503)
