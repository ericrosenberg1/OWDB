from django.contrib import admin
from django.utils.html import format_html
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
    UserProfile,
    EmailVerificationToken,
    TVShow,
)


# =============================================================================
# Admin Site Configuration
# =============================================================================

admin.site.site_header = "WrestlingDB Admin"
admin.site.site_title = "WrestlingDB"
admin.site.index_title = "Database Administration"


# =============================================================================
# Review-gate actions — the "someone can review it" half of the gate.
#
# VerificationQuerySet.public() (owdbapp/models.py) is the "before data goes
# live" half: it keeps `rejected` entities out of public views. Neither that
# nor Django Admin's own changelist (which intentionally still shows every
# state, including rejected, via the unfiltered `.objects` manager) gives a
# human any way to actually change `verification_state`. These three bulk
# actions are that mechanism — mixed into every ModelAdmin for a
# VerificationMixin model so staff can work through the `candidate`
# backlog, promote `provisional` rows once they're double-checked, or
# reject a bad row (and just as easily undo a wrong rejection) straight
# from the changelist, without opening each record individually.
# =============================================================================


class VerificationActionsMixin:
    """Shared bulk `verification_state` actions for VerificationMixin models."""

    @admin.action(description="Mark selected as verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(verification_state="verified")
        self.message_user(request, f"Marked {updated} record(s) as verified.")

    @admin.action(description="Mark selected as provisional")
    def mark_provisional(self, request, queryset):
        updated = queryset.update(verification_state="provisional")
        self.message_user(request, f"Marked {updated} record(s) as provisional.")

    @admin.action(description="Mark selected as rejected")
    def mark_rejected(self, request, queryset):
        updated = queryset.update(verification_state="rejected")
        self.message_user(request, f"Marked {updated} record(s) as rejected.")


VERIFICATION_ACTIONS = ["mark_verified", "mark_provisional", "mark_rejected"]


# =============================================================================
# Model Admins
# =============================================================================


@admin.register(Wrestler)
class WrestlerAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "real_name",
        "hometown",
        "nationality",
        "verification_state",
        "created_at",
    ]
    list_filter = ["verification_state", "nationality", "created_at"]
    search_fields = ["name", "real_name", "aliases", "hometown"]
    prepopulated_fields = {"slug": ("name",)}
    date_hierarchy = "created_at"
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS


@admin.register(Promotion)
class PromotionAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "abbreviation",
        "founded_year",
        "closed_year",
        "verification_state",
        "created_at",
    ]
    list_filter = ["verification_state", "created_at"]
    search_fields = ["name", "abbreviation", "nicknames"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS


@admin.register(TVShow)
class TVShowAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "promotion",
        "show_type",
        "network",
        "air_day",
        "is_active_display",
        "episode_count",
        "tmdb_status",
        "verification_state",
        "created_at",
    ]
    list_filter = ["verification_state", "show_type", "promotion", "finale_date", "created_at"]
    search_fields = ["name", "promotion__name", "network"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["promotion"]
    readonly_fields = ["episode_count"]
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS
    fieldsets = (
        (None, {"fields": ("name", "slug", "promotion", "show_type", "about")}),
        ("Broadcast Info", {"fields": ("network", "air_day", "premiere_date", "finale_date")}),
        ("Verification", {"fields": ("verification_state",)}),
        (
            "External IDs",
            {"fields": ("tmdb_id", "cagematch_id", "wikipedia_url"), "classes": ("collapse",)},
        ),
        (
            "Image",
            {
                "fields": ("image_url", "image_source_url", "image_license", "image_credit"),
                "classes": ("collapse",),
            },
        ),
    )

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#28a745;">Active</span>')
        return format_html('<span style="color:#6c757d;">Ended</span>')

    is_active_display.short_description = "Status"

    def tmdb_status(self, obj):
        if obj.tmdb_id:
            return format_html('<span style="color:#28a745;">&#10004; {}</span>', obj.tmdb_id)
        return format_html('<span style="color:#dc3545;">No ID</span>')

    tmdb_status.short_description = "TMDB"


@admin.register(Event)
class EventAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "promotion",
        "venue",
        "date",
        "event_type",
        "tv_show",
        "episode_number",
        "verification_state",
        "verified_status",
        "created_at",
    ]
    list_filter = [
        "verification_state",
        "promotion",
        "event_type",
        "tv_show",
        "verified",
        "date",
        "created_at",
    ]
    search_fields = ["name", "promotion__name", "venue__name", "tv_show__name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["promotion", "venue", "tv_show"]
    date_hierarchy = "date"
    ordering = ["-date"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS
    fieldsets = (
        (None, {"fields": ("name", "slug", "promotion", "venue", "date", "event_type", "about")}),
        (
            "TV Episode Info",
            {"fields": ("tv_show", "episode_number", "season_number"), "classes": ("collapse",)},
        ),
        (
            "External IDs",
            {"fields": ("tmdb_episode_id", "cagematch_event_id"), "classes": ("collapse",)},
        ),
        (
            "Verification",
            {
                "fields": (
                    "verification_state",
                    "verified",
                    "verification_source",
                    "last_verified",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Image",
            {
                "fields": ("image_url", "image_source_url", "image_license", "image_credit"),
                "classes": ("collapse",),
            },
        ),
    )

    def verified_status(self, obj):
        if obj.verified:
            return format_html(
                '<span style="color:#28a745;">&#10004; {}</span>', obj.verification_source or "Yes"
            )
        return ""

    verified_status.short_description = "Verified"


class MatchParticipantInline(admin.TabularInline):
    from .models import MatchParticipant

    model = MatchParticipant
    extra = 0
    autocomplete_fields = ["wrestler"]
    fields = ("wrestler", "side", "role", "is_winner", "entrance_order")


@admin.register(Match)
class MatchAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "match_text",
        "event",
        "match_type",
        "winner",
        "cagematch_rating",
        "title_changed",
        "verification_state",
        "created_at",
    ]
    list_filter = [
        "verification_state",
        "match_type",
        "title_changed",
        "outcome_type",
        "created_at",
    ]
    search_fields = ["match_text", "event__name", "wrestlers__name"]
    autocomplete_fields = ["event", "winner", "title"]
    inlines = [MatchParticipantInline]
    ordering = ["-created_at"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS


@admin.register(Title)
class TitleAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "promotion",
        "debut_year",
        "retirement_year",
        "verification_state",
        "created_at",
    ]
    list_filter = ["verification_state", "promotion", "created_at"]
    search_fields = ["name", "promotion__name"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["promotion"]
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS


@admin.register(Venue)
class VenueAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = ["name", "location", "capacity", "verification_state", "created_at"]
    list_filter = ["verification_state", "created_at"]
    search_fields = ["name", "location"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS


@admin.register(Stable)
class StableAdmin(VerificationActionsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "promotion",
        "formed_year",
        "disbanded_year",
        "get_member_count",
        "verification_state",
        "created_at",
    ]
    list_filter = ["verification_state", "promotion", "formed_year", "disbanded_year", "created_at"]
    search_fields = ["name", "manager", "about"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["promotion"]
    filter_horizontal = ["members", "leaders"]
    ordering = ["name"]
    list_editable = ["verification_state"]
    actions = VERIFICATION_ACTIONS

    def get_member_count(self, obj):
        return obj.members.count()

    get_member_count.short_description = "Members"


@admin.register(VideoGame)
class VideoGameAdmin(admin.ModelAdmin):
    list_display = ["name", "release_year", "systems", "developer", "publisher"]
    list_filter = ["release_year", "developer", "publisher"]
    search_fields = ["name", "systems", "developer", "publisher"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["promotions"]
    ordering = ["-release_year", "name"]


@admin.register(Podcast)
class PodcastAdmin(admin.ModelAdmin):
    list_display = ["name", "hosts", "launch_year", "end_year", "created_at"]
    list_filter = ["launch_year", "created_at"]
    search_fields = ["name", "hosts"]
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ["related_wrestlers"]
    ordering = ["name"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "publication_year", "isbn", "created_at"]
    list_filter = ["publication_year", "created_at"]
    search_fields = ["title", "author", "isbn"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["related_wrestlers"]
    ordering = ["-publication_year", "title"]


@admin.register(Special)
class SpecialAdmin(admin.ModelAdmin):
    list_display = ["title", "type", "release_year", "created_at"]
    list_filter = ["type", "release_year", "created_at"]
    search_fields = ["title", "type"]
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ["related_wrestlers"]
    ordering = ["-release_year", "title"]


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = [
        "key_display",
        "user",
        "name",
        "is_active",
        "is_paid",
        "requests_today",
        "created_at",
    ]
    list_filter = ["is_active", "is_paid", "created_at"]
    search_fields = ["key", "user__username", "name"]
    readonly_fields = ["key", "requests_today", "requests_total", "last_used", "created_at"]
    ordering = ["-created_at"]

    def key_display(self, obj):
        return f"{obj.key[:8]}..."

    key_display.short_description = "API Key"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "email_verified", "can_contribute", "created_at"]
    list_filter = ["email_verified", "can_contribute", "created_at"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token_display", "expires_at", "used", "created_at"]
    list_filter = ["used", "created_at"]
    search_fields = ["user__username", "user__email", "token"]
    readonly_fields = ["token", "created_at"]

    def token_display(self, obj):
        return f"{obj.token[:8]}..."

    token_display.short_description = "Token"


# WrestleBot admin is now in owdb_django.wrestlebot.admin
