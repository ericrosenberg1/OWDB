"""
WrestleBot Admin Interface

Provides admin views for monitoring bot activity, configuration, and statistics.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    WrestleBotActivity,
    WrestleBotConfig,
    WrestleBotStats,
    SourceFetch,
    FieldProvenance,
    GeneratedBio,
)


@admin.register(WrestleBotActivity)
class WrestleBotActivityAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "action_badge",
        "entity_type",
        "entity_link",
        "source",
        "status_badge",
        "duration_display",
        "ai_badge",
    ]
    list_filter = ["action_type", "entity_type", "source", "success", "ai_assisted", "created_at"]
    search_fields = ["entity_name", "source", "error_message"]
    readonly_fields = [
        "created_at",
        "action_type",
        "entity_type",
        "entity_id",
        "entity_name",
        "source",
        "details",
        "ai_assisted",
        "success",
        "error_message",
        "duration_ms",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50

    def action_badge(self, obj):
        """Show action type with colored badge."""
        colors = {
            "discover": "#28a745",  # green
            "enrich": "#17a2b8",  # blue
            "verify": "#6f42c1",  # purple
            "image": "#fd7e14",  # orange
            "error": "#dc3545",  # red
        }
        color = colors.get(obj.action_type, "#6c757d")
        return format_html(
            '<span style="background-color:{}; color:white; padding:3px 8px; '
            'border-radius:3px; font-size:11px;">{}</span>',
            color,
            obj.action_type.upper(),
        )

    action_badge.short_description = "Action"
    action_badge.admin_order_field = "action_type"

    def entity_link(self, obj):
        """Link to the entity in admin."""
        entity_admin_map = {
            "wrestler": "owdbapp_wrestler_change",
            "promotion": "owdbapp_promotion_change",
            "event": "owdbapp_event_change",
            "title": "owdbapp_title_change",
            "venue": "owdbapp_venue_change",
            "match": "owdbapp_match_change",
            "videogame": "owdbapp_videogame_change",
            "podcast": "owdbapp_podcast_change",
            "book": "owdbapp_book_change",
            "special": "owdbapp_special_change",
        }
        try:
            url_name = entity_admin_map.get(obj.entity_type)
            if url_name and obj.entity_id:
                url = reverse(f"admin:{url_name}", args=[obj.entity_id])
                return format_html('<a href="{}">{}</a>', url, obj.entity_name)
        except Exception:
            pass
        return obj.entity_name

    entity_link.short_description = "Entity"
    entity_link.admin_order_field = "entity_name"

    def status_badge(self, obj):
        """Show success/failure with colored indicator."""
        if obj.success:
            return format_html('<span style="color:#28a745;">&#10004;</span>')
        else:
            return format_html(
                '<span style="color:#dc3545;" title="{}">&#10008;</span>',
                obj.error_message[:100] if obj.error_message else "Failed",
            )

    status_badge.short_description = "Status"
    status_badge.admin_order_field = "success"

    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.duration_ms is None:
            return "-"
        if obj.duration_ms < 1000:
            return f"{obj.duration_ms}ms"
        return f"{obj.duration_ms / 1000:.1f}s"

    duration_display.short_description = "Duration"
    duration_display.admin_order_field = "duration_ms"

    def ai_badge(self, obj):
        """Show AI indicator."""
        if obj.ai_assisted:
            return format_html(
                '<span style="background-color:#6f42c1; color:white; padding:2px 6px; '
                'border-radius:3px; font-size:10px;">AI</span>'
            )
        return ""

    ai_badge.short_description = "AI"
    ai_badge.admin_order_field = "ai_assisted"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(WrestleBotConfig)
class WrestleBotConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value_display", "description", "updated_at"]
    search_fields = ["key", "description"]
    readonly_fields = ["updated_at"]
    ordering = ["key"]

    def value_display(self, obj):
        """Format value for display."""
        value = obj.value
        if isinstance(value, bool):
            if value:
                return format_html('<span style="color:#28a745;">&#10004; Enabled</span>')
            return format_html('<span style="color:#dc3545;">&#10008; Disabled</span>')
        elif isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return str(value)

    value_display.short_description = "Value"


@admin.register(WrestleBotStats)
class WrestleBotStatsAdmin(admin.ModelAdmin):
    list_display = [
        "date",
        "discoveries_display",
        "enrichments_display",
        "images_display",
        "errors_display",
        "api_calls_display",
    ]
    list_filter = ["date"]
    readonly_fields = [
        "date",
        "discoveries",
        "enrichments",
        "images_added",
        "verifications",
        "errors",
        "wikipedia_calls",
        "cagematch_calls",
        "wikimedia_calls",
        "claude_api_calls",
        "total_duration_ms",
        "average_score_improvement",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "date"
    ordering = ["-date"]

    def discoveries_display(self, obj):
        """Show discoveries with styling."""
        if obj.discoveries > 0:
            return format_html(
                '<span style="color:#28a745; font-weight:bold;">+{}</span>', obj.discoveries
            )
        return "0"

    discoveries_display.short_description = "Discoveries"
    discoveries_display.admin_order_field = "discoveries"

    def enrichments_display(self, obj):
        """Show enrichments with styling."""
        if obj.enrichments > 0:
            return format_html(
                '<span style="color:#17a2b8; font-weight:bold;">{}</span>', obj.enrichments
            )
        return "0"

    enrichments_display.short_description = "Enrichments"
    enrichments_display.admin_order_field = "enrichments"

    def images_display(self, obj):
        """Show images added with styling."""
        if obj.images_added > 0:
            return format_html(
                '<span style="color:#fd7e14; font-weight:bold;">{}</span>', obj.images_added
            )
        return "0"

    images_display.short_description = "Images"
    images_display.admin_order_field = "images_added"

    def errors_display(self, obj):
        """Show errors with warning styling."""
        if obj.errors > 0:
            return format_html(
                '<span style="color:#dc3545; font-weight:bold;">{}</span>', obj.errors
            )
        return format_html('<span style="color:#28a745;">0</span>')

    errors_display.short_description = "Errors"
    errors_display.admin_order_field = "errors"

    def api_calls_display(self, obj):
        """Show total API calls."""
        total = obj.wikipedia_calls + obj.cagematch_calls + obj.wikimedia_calls
        ai = obj.claude_api_calls
        if ai > 0:
            return format_html('{} <span style="color:#6f42c1;">(+{} AI)</span>', total, ai)
        return str(total)

    api_calls_display.short_description = "API Calls"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# =============================================================================
# Accuracy-first v3 provenance admin
# =============================================================================


@admin.register(SourceFetch)
class SourceFetchAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "source",
        "candidate_name",
        "entity_type",
        "entity_id",
        "http_status",
        "content_length",
        "fetched_at",
        "used_at",
    ]
    list_filter = ["source", "entity_type", "http_status", "fetched_at"]
    search_fields = ["candidate_name", "url", "content_hash"]
    readonly_fields = [
        "fetched_at",
        "content_hash",
        "raw_content",
        "url",
        "source",
        "entity_type",
        "entity_id",
        "candidate_name",
        "http_status",
    ]
    date_hierarchy = "fetched_at"
    ordering = ["-fetched_at"]
    list_per_page = 50

    def content_length(self, obj):
        return f"{len(obj.raw_content):,} bytes"

    content_length.short_description = "Size"

    def has_add_permission(self, request):
        return False


@admin.register(FieldProvenance)
class FieldProvenanceAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "entity_type",
        "entity_id",
        "field_name",
        "value_preview",
        "source_name",
        "confidence",
        "extracted_at",
    ]
    list_filter = ["entity_type", "field_name", "extracted_at"]
    search_fields = ["value", "field_name"]
    readonly_fields = [
        "entity_type",
        "entity_id",
        "field_name",
        "value",
        "source_fetch",
        "confidence",
        "extracted_at",
    ]
    date_hierarchy = "extracted_at"
    ordering = ["-extracted_at"]
    list_per_page = 100

    def value_preview(self, obj):
        v = obj.value
        return v[:80] + ("..." if len(v) > 80 else "")

    value_preview.short_description = "Value"

    def source_name(self, obj):
        return obj.source_fetch.source

    source_name.short_description = "Source"
    source_name.admin_order_field = "source_fetch__source"

    def has_add_permission(self, request):
        return False


@admin.register(GeneratedBio)
class GeneratedBioAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "entity_type",
        "entity_id",
        "model",
        "status",
        "claims_total",
        "claims_verified",
        "generated_at",
    ]
    list_filter = ["status", "model", "entity_type", "generated_at"]
    search_fields = ["text"]
    readonly_fields = [
        "entity_type",
        "entity_id",
        "text",
        "model",
        "generated_at",
        "source_fetches",
        "claims_total",
        "claims_verified",
        "claims_unsupported",
        "input_tokens",
        "output_tokens",
    ]
    date_hierarchy = "generated_at"
    ordering = ["-generated_at"]
    list_per_page = 50

    def has_add_permission(self, request):
        return False
