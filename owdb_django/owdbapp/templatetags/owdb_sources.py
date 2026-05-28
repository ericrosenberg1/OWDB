"""
Template tag: render the list of distinct sources used to verify an entity.

Reads `FieldProvenance.source_fetch.source` for the entity, collapses to
the distinct set of human-readable source names. Used at the bottom of
every entity detail page so visitors can see exactly which sources back
the data — no hyperlinks per OWDB's editorial policy.
"""

from __future__ import annotations

from django import template

register = template.Library()


# Mapping from internal source slugs to the display name we want users
# to see on the page. Keeps the editorial voice consistent regardless
# of which internal scraper slug recorded the provenance.
SOURCE_DISPLAY_NAMES = {
    "wikipedia": "Wikipedia",
    "wikidata": "Wikidata",
    "wikimedia_commons": "Wikimedia Commons",
    "cagematch": "Cagematch",
    "profightdb": "ProFightDB",
    "profightdb_pwi_mirror": "ProFightDB (PWI ranking mirror)",
    "tmdb": "TMDB",
    "openlibrary": "Open Library",
}


@register.simple_tag
def sources_used_for(entity_type, entity_id):
    """
    Return the sorted list of distinct human-readable source names that
    contributed FieldProvenance rows for this entity.

    Usage in a template:

        {% load owdb_sources %}
        {% sources_used_for "wrestler" wrestler.id as srcs %}
        {% if srcs %}
          <h4>Sources used for verification</h4>
          <ul class="sources-list">
            {% for s in srcs %}<li>{{ s }}</li>{% endfor %}
          </ul>
        {% endif %}
    """
    from owdb_django.wrestlebot.models import FieldProvenance

    raw = (
        FieldProvenance.objects.filter(entity_type=entity_type, entity_id=entity_id)
        .values_list("source_fetch__source", flat=True)
        .distinct()
    )
    seen: set[str] = set()
    out: list[str] = []
    for src in raw:
        if not src:
            continue
        display = SOURCE_DISPLAY_NAMES.get(src, src.replace("_", " ").title())
        if display in seen:
            continue
        seen.add(display)
        out.append(display)
    out.sort()
    return out


@register.simple_tag
def field_provenance_count(entity_type, entity_id):
    """Total FieldProvenance rows for this entity. Useful for debug bars."""
    from owdb_django.wrestlebot.models import FieldProvenance

    return FieldProvenance.objects.filter(
        entity_type=entity_type,
        entity_id=entity_id,
    ).count()
