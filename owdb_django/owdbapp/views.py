from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.views.generic import ListView, DetailView, TemplateView
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django import forms
from datetime import timedelta

from .models import (
    Wrestler,
    Promotion,
    Event,
    Match,
    Title,
    Venue,
    Stable,
    VideoGame,
    Podcast,
    Book,
    Special,
    APIKey,
    UserProfile,
    EmailVerificationToken,
    WrestleBotLog,
    WrestleBotConfig,
    Hot100Ranking,
    Hot100Entry,
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

        # Get stats from cache or compute fresh (cached for 15 minutes)
        stats = cache.get('homepage_stats')
        if stats is None:
            stats = {
                'wrestlers': Wrestler.objects.count(),
                'promotions': Promotion.objects.count(),
                'events': Event.objects.count(),
                'matches': Match.objects.count(),
                'titles': Title.objects.count(),
                'venues': Venue.objects.count(),
                'stables': Stable.objects.count(),
                'video_games': VideoGame.objects.count(),
                'podcasts': Podcast.objects.count(),
                'books': Book.objects.count(),
                'specials': Special.objects.count(),
            }
            stats['total'] = sum(stats.values())
            cache.set('homepage_stats', stats, 900)  # Cache for 15 minutes

        context['stats'] = stats

        # Get latest additions (wrestlers, promotions, titles)
        context['latest_wrestlers'] = Wrestler.objects.order_by('-created_at')[:10]
        context['latest_promotions'] = Promotion.objects.order_by('-created_at')[:10]
        context['latest_titles'] = Title.objects.select_related('promotion').order_by('-created_at')[:10]

        # Get recent events by date (newest first), with promotion filter options
        context['recent_events'] = Event.objects.select_related('promotion').order_by('-date')[:10]
        context['wwe_events'] = Event.objects.select_related('promotion').filter(
            promotion__name__icontains='WWE'
        ).order_by('-date')[:10]
        context['aew_events'] = Event.objects.select_related('promotion').filter(
            promotion__name__icontains='AEW'
        ).order_by('-date')[:10]

        # Get Hot 100 for homepage
        hot100_ranking = Hot100Ranking.get_current()
        if hot100_ranking:
            context['hot100_entries'] = hot100_ranking.entries.select_related('wrestler').all()[:10]
        else:
            context['hot100_entries'] = []

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
            'stables': Stable.objects.count(),
            'games': VideoGame.objects.count(),
            'books': Book.objects.count(),
            'podcasts': Podcast.objects.count(),
            'specials': Special.objects.count(),
        }
        return context


# =============================================================================
# Privacy Policy
# =============================================================================

class PrivacyView(TemplateView):
    template_name = 'privacy.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Privacy Policy'
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
        wrestler = self.object
        context['page_title'] = wrestler.name
        context['matches'] = wrestler.matches.select_related('event', 'event__promotion')[:20]

        # Interlinking: promotions, titles, rivals, record
        context['promotions'] = wrestler.get_promotions()[:10]
        context['titles_won'] = wrestler.get_titles_won()
        context['rivals'] = wrestler.get_rivals(limit=10)
        context['record'] = wrestler.get_win_loss_record()

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
        promotion = self.object
        context['page_title'] = promotion.name
        context['events'] = promotion.events.select_related('venue').order_by('-date')[:20]
        context['titles'] = promotion.titles.all()

        # Interlinking: wrestlers roster, venues, event timeline, stats
        context['all_wrestlers'] = promotion.get_all_wrestlers(limit=30)
        context['venues'] = promotion.get_venues(limit=10)
        context['timeline'] = promotion.get_event_timeline()
        context['stats'] = promotion.get_stats()

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
        event = self.object
        context['page_title'] = event.name
        context['matches'] = event.matches.prefetch_related('wrestlers').select_related('winner', 'title').order_by('match_order')

        # Interlinking: all wrestlers on card, titles defended
        context['all_wrestlers'] = event.get_all_wrestlers()
        context['titles_defended'] = event.get_titles_defended()

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
        return super().get_queryset().select_related('event', 'event__promotion', 'event__venue', 'title', 'winner').prefetch_related('wrestlers')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match = self.object
        context['page_title'] = match.match_text

        # Interlinking: participants (wrestler objects), related matches
        context['participants'] = match.get_participants()
        context['related_matches'] = match.get_related_matches(limit=5)

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
        title = self.object
        context['page_title'] = title.name
        context['title_matches'] = title.title_matches.select_related('event', 'winner')[:20]

        # Interlinking: championship history, all champions, top defenders
        context['championship_history'] = title.get_championship_history()[:20]
        context['all_champions'] = title.get_all_champions()
        context['most_defenses'] = title.get_most_defenses(limit=10)

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
        venue = self.object
        context['page_title'] = venue.name

        # Paginated events list
        from django.core.paginator import Paginator
        events = venue.events.select_related('promotion').order_by('-date')
        paginator = Paginator(events, 25)
        page = self.request.GET.get('page', 1)
        context['events'] = paginator.get_page(page)

        # Interlinking: promotions, top wrestlers, stats
        context['promotions'] = venue.get_promotions()[:10]
        context['top_wrestlers'] = venue.get_wrestlers(limit=10)
        context['stats'] = venue.get_stats()

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
    from django.utils.http import url_has_allowed_host_and_scheme

    if request.user.is_authenticated:
        return redirect('index')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, f'Welcome back, {form.get_user().username}!')
            # Prevent open redirect attacks by validating next URL
            next_url = request.GET.get('next', '')
            if not next_url or not url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                next_url = 'index'
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


# =============================================================================
# WrestleBot Views
# =============================================================================

class WrestleBotView(TemplateView):
    """WrestleBot information and activity log page."""
    template_name = 'wrestlebot.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'WrestleBot'

        # Get configuration
        config = WrestleBotConfig.get_config()
        context['config'] = config

        # Get statistics
        context['stats'] = {
            'total_added': config.total_items_added,
            'added_today': config.items_added_today,
            'added_this_hour': config.items_added_this_hour,
            'total_errors': config.total_errors,
            'last_run': config.last_run,
            'enabled': config.enabled,
        }

        # Check AI availability
        try:
            from .wrestlebot import WrestleBot
            bot = WrestleBot()
            context['ai_available'] = bot.ai.is_available()
            context['ai_model'] = bot.ai.model
        except Exception:
            context['ai_available'] = False
            context['ai_model'] = None

        # Check system health
        from django.core.cache import cache
        health = {
            'redis': False,
            'celery': False,
            'ollama': context.get('ai_available', False),
        }

        # Check Redis
        try:
            cache.set('health_check', 'ok', 5)
            health['redis'] = cache.get('health_check') == 'ok'
        except Exception:
            pass

        # Check Celery (via inspect)
        try:
            from owdb_django.celery import app
            inspect = app.control.inspect(timeout=2)
            active = inspect.active()
            health['celery'] = active is not None
        except Exception:
            pass

        context['health'] = health

        # Calculate operational status
        if not config.enabled:
            context['status'] = 'paused'
            context['status_message'] = 'WrestleBot is paused'
            context['status_class'] = 'secondary'
        elif not health['redis']:
            context['status'] = 'error'
            context['status_message'] = 'Redis connection failed'
            context['status_class'] = 'danger'
        elif not health['celery']:
            context['status'] = 'warning'
            context['status_message'] = 'Celery worker not responding'
            context['status_class'] = 'warning'
        elif not health['ollama']:
            context['status'] = 'degraded'
            context['status_message'] = 'Running without AI verification'
            context['status_class'] = 'warning'
        elif config.items_added_this_hour >= config.max_items_per_hour:
            context['status'] = 'rate_limited'
            context['status_message'] = 'Hourly rate limit reached'
            context['status_class'] = 'info'
        elif config.items_added_today >= config.max_items_per_day:
            context['status'] = 'rate_limited'
            context['status_message'] = 'Daily rate limit reached'
            context['status_class'] = 'info'
        else:
            context['status'] = 'active'
            context['status_message'] = 'Running normally'
            context['status_class'] = 'success'

        # Get recent 24h activity stats from logs
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        last_24h = now - timedelta(hours=24)

        context['recent_creates_24h'] = WrestleBotLog.objects.filter(
            created_at__gte=last_24h,
            action_type='create',
            success=True
        ).count()

        context['recent_errors_24h'] = WrestleBotLog.objects.filter(
            created_at__gte=last_24h,
            action_type='error'
        ).count()

        # Check if user is staff (for showing admin controls)
        context['is_staff'] = (
            self.request.user.is_authenticated and
            self.request.user.is_staff
        )

        # Get recent activity logs (paginated)
        logs = WrestleBotLog.objects.select_related().order_by('-created_at')

        # Filter by entity type if specified
        entity_filter = self.request.GET.get('entity')
        if entity_filter and entity_filter in dict(WrestleBotLog.ENTITY_TYPES):
            logs = logs.filter(entity_type=entity_filter)
            context['current_filter'] = entity_filter

        # Filter by action type if specified
        action_filter = self.request.GET.get('action')
        if action_filter and action_filter in dict(WrestleBotLog.ACTION_TYPES):
            logs = logs.filter(action_type=action_filter)
            context['current_action'] = action_filter

        # Paginate
        from django.core.paginator import Paginator
        paginator = Paginator(logs, 50)
        page = self.request.GET.get('page', 1)
        context['logs'] = paginator.get_page(page)

        # Get counts by entity type for filter tabs (single aggregation query)
        from django.db.models import Count
        entity_counts_raw = WrestleBotLog.objects.values('entity_type').annotate(
            count=Count('id')
        )
        entity_labels = dict(WrestleBotLog.ENTITY_TYPES)
        context['entity_counts'] = {
            item['entity_type']: {
                'label': entity_labels.get(item['entity_type'], item['entity_type']),
                'count': item['count'],
            }
            for item in entity_counts_raw if item['count'] > 0
        }

        # Get counts by action type (single aggregation query)
        action_counts_raw = WrestleBotLog.objects.values('action_type').annotate(
            count=Count('id')
        )
        action_labels = dict(WrestleBotLog.ACTION_TYPES)
        context['action_counts'] = {
            item['action_type']: {
                'label': action_labels.get(item['action_type'], item['action_type']),
                'count': item['count'],
            }
            for item in action_counts_raw if item['count'] > 0
        }

        return context


def wrestlebot_api(request):
    """JSON API endpoint for WrestleBot live stats and recent activity."""
    from django.http import JsonResponse
    from django.utils import timezone
    from django.utils.timesince import timesince
    from django.core.cache import cache
    import redis

    try:
        config = WrestleBotConfig.get_config()

        # Get recent logs (last 20)
        logs = WrestleBotLog.objects.select_related().order_by('-created_at')[:20]
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'created_at': log.created_at.strftime('%b %d, %H:%M'),
                'action_type': log.action_type,
                'entity_type': log.entity_type,
                'entity_name': log.entity_name,
                'ai_reasoning': log.ai_reasoning[:60] + '...' if log.ai_reasoning and len(log.ai_reasoning) > 60 else log.ai_reasoning,
                'ai_confidence': log.ai_confidence,
                'source_url': log.source_url,
                'success': log.success,
            })

        # Check AI status
        ai_available = False
        ai_model = None
        ai_error = None
        try:
            from .wrestlebot import WrestleBot
            bot = WrestleBot()
            ai_available = bot.ai.is_available()
            ai_model = bot.ai.model
        except Exception as e:
            ai_error = str(e)

        # Check system health
        health = {
            'redis': False,
            'celery': False,
            'ollama': ai_available,
        }

        # Check Redis
        try:
            cache.set('health_check', 'ok', 5)
            health['redis'] = cache.get('health_check') == 'ok'
        except Exception:
            pass

        # Check Celery (via inspect)
        try:
            from owdb_django.celery import app
            inspect = app.control.inspect(timeout=2)
            active = inspect.active()
            health['celery'] = active is not None
        except Exception:
            pass

        # Get recent activity stats
        from datetime import timedelta
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_hour = now - timedelta(hours=1)

        recent_creates = WrestleBotLog.objects.filter(
            created_at__gte=last_24h,
            action_type='create',
            success=True
        ).count()

        recent_errors = WrestleBotLog.objects.filter(
            created_at__gte=last_24h,
            action_type='error'
        ).count()

        hourly_creates = WrestleBotLog.objects.filter(
            created_at__gte=last_hour,
            action_type='create',
            success=True
        ).count()

        # Calculate operational status
        if not config.enabled:
            status = 'paused'
            status_message = 'WrestleBot is paused'
        elif not health['redis']:
            status = 'error'
            status_message = 'Redis connection failed'
        elif not health['celery']:
            status = 'warning'
            status_message = 'Celery worker not responding'
        elif not health['ollama']:
            status = 'degraded'
            status_message = 'Running without AI verification'
        elif config.items_added_this_hour >= config.max_items_per_hour:
            status = 'rate_limited'
            status_message = 'Hourly rate limit reached'
        elif config.items_added_today >= config.max_items_per_day:
            status = 'rate_limited'
            status_message = 'Daily rate limit reached'
        else:
            status = 'active'
            status_message = 'Running normally'

        return JsonResponse({
            'status': status,
            'status_message': status_message,
            'stats': {
                'total_added': config.total_items_added,
                'added_today': config.items_added_today,
                'added_this_hour': config.items_added_this_hour,
                'total_errors': config.total_errors,
                'last_run': timesince(config.last_run) + ' ago' if config.last_run else None,
                'enabled': config.enabled,
                'recent_creates_24h': recent_creates,
                'recent_errors_24h': recent_errors,
                'hourly_creates': hourly_creates,
            },
            'config': {
                'max_items_per_hour': config.max_items_per_hour,
                'max_items_per_day': config.max_items_per_day,
            },
            'health': health,
            'ai': {
                'available': ai_available,
                'model': ai_model,
                'error': ai_error,
            },
            'logs': logs_data,
            'timestamp': timezone.now().isoformat(),
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
def wrestlebot_trigger(request):
    """
    Manually trigger a WrestleBot discovery cycle.
    Requires staff authentication.
    """
    from django.http import JsonResponse
    from django.views.decorators.csrf import csrf_exempt

    # Check if user is authenticated and is staff
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'error': 'Staff authentication required'
        }, status=403)

    try:
        from .tasks import wrestlebot_discovery_cycle

        # Get config to check if we can run
        config = WrestleBotConfig.get_config()

        if not config.enabled:
            return JsonResponse({
                'success': False,
                'error': 'WrestleBot is currently disabled'
            })

        if not config.can_add_items():
            return JsonResponse({
                'success': False,
                'error': 'Rate limit reached. Try again later.'
            })

        # Trigger the task asynchronously
        max_items = int(request.POST.get('max_items', 10))
        max_items = min(max_items, 50)  # Cap at 50 items

        task = wrestlebot_discovery_cycle.delay(max_items=max_items)

        return JsonResponse({
            'success': True,
            'message': f'Discovery cycle triggered with max {max_items} items',
            'task_id': str(task.id)
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =============================================================================
# Hot 100 Rankings Views
# =============================================================================

class Hot100View(TemplateView):
    """Display the current Hot 100 wrestler rankings."""
    template_name = 'hot100.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get year/month from URL or use current
        year = self.kwargs.get('year')
        month = self.kwargs.get('month')

        if year and month:
            ranking = Hot100Ranking.get_for_month(int(year), int(month))
        else:
            ranking = Hot100Ranking.get_current()

        context['ranking'] = ranking
        context['entries'] = ranking.entries.select_related('wrestler').all() if ranking else []

        # Get available months for navigation
        context['available_rankings'] = Hot100Ranking.objects.filter(
            is_published=True
        ).values('year', 'month').order_by('-year', '-month')[:12]

        return context


class Hot100HistoryView(ListView):
    """List all available Hot 100 rankings."""
    model = Hot100Ranking
    template_name = 'hot100_history.html'
    context_object_name = 'rankings'
    paginate_by = 12

    def get_queryset(self):
        return Hot100Ranking.objects.filter(is_published=True).order_by('-year', '-month')
