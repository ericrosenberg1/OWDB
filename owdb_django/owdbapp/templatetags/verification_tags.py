"""
Template tags that surface WrestleBot v3 verification provenance on entity
detail pages.

The public-facing stamp deliberately avoids naming proprietary databases by
trademark, per the project's accuracy-first-and-respectful stance. Sources
with permissive licensing (Wikipedia CC BY-SA, Wikidata CC0) are named and
linked. Others are referred to generically as "external wrestling database"
with a link to the canonical URL when available.
"""

from __future__ import annotations

from typing import Optional

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


# Per-source public display config. `name` is the visible label on the
# verification stamp; `homepage` is what the label links to (or None to
# suppress the link entirely).
#
# Trademarked third-party databases use a generic "external wrestling
# database" label per project policy — no name, no logo.
SOURCE_DISPLAY = {
    "wikipedia": {"name": "Wikipedia", "homepage": "https://en.wikipedia.org/"},
    "wikidata": {"name": "Wikidata", "homepage": "https://www.wikidata.org/"},
    "cagematch": {"name": "External wrestling database", "homepage": None},
    "profightdb": {"name": "External wrestling database", "homepage": None},
    "tmdb": {"name": "TMDB", "homepage": "https://www.themoviedb.org/"},
    "wikimedia_commons": {"name": "Wikimedia Commons", "homepage": "https://commons.wikimedia.org/"},
}


def _entity_type_for(obj) -> Optional[str]:
    cls = obj.__class__.__name__.lower()
    if cls in {"wrestler", "promotion", "event", "match", "title", "venue", "stable"}:
        return cls
    return None


@register.inclusion_tag("partials/verification_stamp.html")
def verification_stamp(entity):
    """
    Render the "Verified from" footer for an entity detail page.

    Pulls every source we have direct evidence for — either a successful
    SourceFetch row, or a stored profile URL on the entity itself. Trademarked
    databases get a generic display name; everything else is named & linked.
    """
    entity_type = _entity_type_for(entity)
    if entity_type is None:
        return {"sources": [], "total": 0}

    # Late import to avoid top-level wrestlebot dependency in owdbapp.
    try:
        from owdb_django.wrestlebot.models import SourceFetch
    except Exception:
        return {"sources": [], "total": 0}

    fetches = (
        SourceFetch.objects
        .filter(entity_type=entity_type, entity_id=entity.id, http_status=200)
        .order_by("source", "-fetched_at")
    )
    # One entry per source (the latest successful fetch).
    by_source: dict[str, dict] = {}
    for f in fetches:
        if f.source in by_source:
            continue
        display = SOURCE_DISPLAY.get(f.source, {"name": "External source", "homepage": None})
        by_source[f.source] = {
            "source": f.source,
            "display_name": display["name"],
            "homepage": display["homepage"],
            "url": f.url,
            "fetched_at": f.fetched_at,
            "kind": "verified",
        }

    # Also surface URLs we have on the entity but haven't fetched (e.g.,
    # cagematch_url scraped from Wikipedia external links). These count as
    # "linked" — we point users at the source even if we haven't pulled it
    # ourselves yet.
    if entity_type in {"wrestler", "promotion"}:
        for attr, source_key in (
            ("wikipedia_url", "wikipedia"),
            ("cagematch_url", "cagematch"),
            ("profightdb_url", "profightdb"),
        ):
            url = getattr(entity, attr, None)
            if url and source_key not in by_source:
                display = SOURCE_DISPLAY.get(source_key, {"name": "External source", "homepage": None})
                by_source[source_key] = {
                    "source": source_key,
                    "display_name": display["name"],
                    "homepage": display["homepage"],
                    "url": url,
                    "fetched_at": None,
                    "kind": "linked",
                }

    # Render order: verified first (alphabetised), then linked-only.
    ordered = sorted(
        by_source.values(),
        key=lambda s: (0 if s["kind"] == "verified" else 1, s["display_name"]),
    )

    verified_count = sum(1 for s in ordered if s["kind"] == "verified")
    return {
        "sources": ordered,
        "total": len(ordered),
        "verified_count": verified_count,
        "linked_count": len(ordered) - verified_count,
    }


@register.simple_tag
def verification_short(entity) -> str:
    """One-liner version for places where the inclusion tag is too heavy."""
    data = verification_stamp(entity)
    n = data["total"]
    if n == 0:
        return ""
    return mark_safe(f"<small class='verification-short'>Verified from {n} source"
                     f"{'s' if n != 1 else ''}</small>")
