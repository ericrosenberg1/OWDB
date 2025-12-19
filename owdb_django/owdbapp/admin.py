from django.contrib import admin
from .models import (
    Promotion,
    VideoGame,
    Podcast,
    Book,
    Special,
    Title,
    Venue,
    Wrestler,
    Stable,
    Event,
    Match,
    APIKey,
    WrestleBotLog,
    WrestleBotConfig,
    UserProfile,
    EmailVerificationToken,
)


# =============================================================================
# Admin Site Configuration
# =============================================================================

admin.site.site_header = 'WrestlingDB Admin'
admin.site.site_title = 'WrestlingDB'
admin.site.index_title = 'Database Administration'


# =============================================================================
# Model Admins
# =============================================================================

@admin.register(Wrestler)
class WrestlerAdmin(admin.ModelAdmin):
    list_display = ['name', 'real_name', 'hometown', 'nationality', 'created_at']
    list_filter = ['nationality', 'created_at']
    search_fields = ['name', 'real_name', 'aliases', 'hometown']
    prepopulated_fields = {'slug': ('name',)}
    date_hierarchy = 'created_at'
    ordering = ['name']


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'abbreviation', 'founded_year', 'closed_year', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'abbreviation', 'nicknames']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ['name', 'promotion', 'venue', 'date', 'created_at']
    list_filter = ['promotion', 'date', 'created_at']
    search_fields = ['name', 'promotion__name', 'venue__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['promotion', 'venue']
    date_hierarchy = 'date'
    ordering = ['-date']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['match_text', 'event', 'match_type', 'winner', 'created_at']
    list_filter = ['match_type', 'created_at']
    search_fields = ['match_text', 'event__name', 'wrestlers__name']
    autocomplete_fields = ['event', 'winner', 'title']
    filter_horizontal = ['wrestlers']
    ordering = ['-created_at']


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ['name', 'promotion', 'debut_year', 'retirement_year', 'created_at']
    list_filter = ['promotion', 'created_at']
    search_fields = ['name', 'promotion__name']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['promotion']
    ordering = ['name']


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'capacity', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'location']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['name']


@admin.register(Stable)
class StableAdmin(admin.ModelAdmin):
    list_display = ['name', 'promotion', 'formed_year', 'disbanded_year', 'get_member_count', 'created_at']
    list_filter = ['promotion', 'formed_year', 'disbanded_year', 'created_at']
    search_fields = ['name', 'manager', 'about']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['promotion']
    filter_horizontal = ['members', 'leaders']
    ordering = ['name']

    def get_member_count(self, obj):
        return obj.members.count()
    get_member_count.short_description = 'Members'


@admin.register(VideoGame)
class VideoGameAdmin(admin.ModelAdmin):
    list_display = ['name', 'release_year', 'systems', 'developer', 'publisher']
    list_filter = ['release_year', 'developer', 'publisher']
    search_fields = ['name', 'systems', 'developer', 'publisher']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['promotions']
    ordering = ['-release_year', 'name']


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ['name', 'hosts', 'launch_year', 'end_year', 'created_at']
    list_filter = ['launch_year', 'created_at']
    search_fields = ['name', 'hosts']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['related_wrestlers']
    ordering = ['name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'publication_year', 'isbn', 'created_at']
    list_filter = ['publication_year', 'created_at']
    search_fields = ['title', 'author', 'isbn']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_wrestlers']
    ordering = ['-publication_year', 'title']


@admin.register(Special)
class SpecialAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'release_year', 'created_at']
    list_filter = ['type', 'release_year', 'created_at']
    search_fields = ['title', 'type']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['related_wrestlers']
    ordering = ['-release_year', 'title']


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['key_display', 'user', 'name', 'is_active', 'is_paid', 'requests_today', 'created_at']
    list_filter = ['is_active', 'is_paid', 'created_at']
    search_fields = ['key', 'user__username', 'name']
    readonly_fields = ['key', 'requests_today', 'requests_total', 'last_used', 'created_at']
    ordering = ['-created_at']

    def key_display(self, obj):
        return f'{obj.key[:8]}...'
    key_display.short_description = 'API Key'


# =============================================================================
# WrestleBot Admin
# =============================================================================

@admin.register(WrestleBotLog)
class WrestleBotLogAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'action_type', 'entity_type', 'entity_name',
        'ai_confidence', 'success'
    ]
    list_filter = ['action_type', 'entity_type', 'success', 'created_at']
    search_fields = ['entity_name', 'source_title', 'ai_reasoning']
    readonly_fields = [
        'created_at', 'action_type', 'entity_type', 'entity_name',
        'entity_id', 'source_url', 'source_title', 'data_extracted',
        'ai_model', 'ai_confidence', 'ai_reasoning', 'task_id', 'batch_id',
        'success', 'error_message'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def has_add_permission(self, request):
        return False  # Logs are created by the bot, not manually

    def has_change_permission(self, request, obj=None):
        return False  # Logs should be immutable


@admin.register(WrestleBotConfig)
class WrestleBotConfigAdmin(admin.ModelAdmin):
    list_display = [
        'enabled', 'ai_model_name', 'max_items_per_hour', 'max_items_per_day',
        'total_items_added', 'last_run'
    ]
    readonly_fields = [
        'items_added_today', 'items_added_this_hour', 'last_run',
        'last_reset_date', 'last_reset_hour', 'total_items_added', 'total_errors'
    ]
    fieldsets = (
        ('Status', {
            'fields': ('enabled', 'last_run', 'total_items_added', 'total_errors')
        }),
        ('Rate Limiting', {
            'fields': (
                'max_items_per_hour', 'max_items_per_day', 'cooldown_minutes',
                'items_added_this_hour', 'items_added_today'
            )
        }),
        ('AI Settings', {
            'fields': (
                'ai_model_name', 'ai_temperature', 'min_confidence_threshold'
            )
        }),
        ('Data Quality', {
            'fields': ('min_data_fields', 'require_verification')
        }),
        ('Focus Areas', {
            'fields': (
                'focus_wrestlers', 'focus_promotions', 'focus_events',
                'focus_titles', 'focus_matches'
            )
        }),
    )

    def has_add_permission(self, request):
        # Only allow one config instance
        return not WrestleBotConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deleting the config


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'email_verified', 'can_contribute', 'created_at']
    list_filter = ['email_verified', 'can_contribute', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'token_display', 'expires_at', 'used', 'created_at']
    list_filter = ['used', 'created_at']
    search_fields = ['user__username', 'user__email', 'token']
    readonly_fields = ['token', 'created_at']

    def token_display(self, obj):
        return f'{obj.token[:8]}...'
    token_display.short_description = 'Token'
