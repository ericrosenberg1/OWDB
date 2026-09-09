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
    "wikimedia_commons": {
        "name": "Wikimedia Commons",
        "homepage": "https://commons.wikimedia.org/",
    },
}


# Honesty copy for entities that aren't fully verified yet — the review-gate's
# UI half. The query-level gate (VerificationQuerySet.public() in models.py)
# only ever hides "rejected"; "candidate" and "provisional" stay visible on
# purpose (see the policy note there), so this is how a reader is told not to
# take the page at face value. "verified" and "rejected" are intentionally
# absent: a verified entity gets no extra badge (the sources panel below
# already makes the case), and a rejected entity never reaches a template in
# the first place. Keyed by VerificationMixin.verification_state.
VERIFICATION_STATE_DISPLAY = {
    "candidate": {
        "label": "Unverified — pending review",
        "modifier": "candidate",
        "detail": (
            "This entry exists because we found a reference to it, but nobody has "
            "confirmed the details against a source yet. Treat it as a lead, not a fact."
        ),
    },
    "provisional": {
        "label": "Provisional",
        "modifier": "provisional",
        "detail": (
            "This entry has structured data on file, but is still missing "
            "source-by-source confirmation for one or more fields."
        ),
    },
}


# Lowercased model class name to the `entity_type` string the wrestlebot
# writes on SourceFetch rows (wrestlebot/models.py ENTITY_TYPE_CHOICES).
# Most match one-to-one. TVShow does not: the pipeline stores "tv_show", so
# a bare lowercased class name ("tvshow") would never find a show's fetches.
_ENTITY_TYPE_BY_CLASS = {
    "wrestler": "wrestler",
    "promotion": "promotion",
    "event": "event",
    "match": "match",
    "title": "title",
    "venue": "venue",
    "stable": "stable",
    "tvshow": "tv_show",
}


def _entity_type_for(obj) -> Optional[str]:
    return _ENTITY_TYPE_BY_CLASS.get(obj.__class__.__name__.lower())


@register.inclusion_tag("partials/verification_state_badge.html")
def verification_state_badge(entity):
    """
    Small honesty pill for `candidate` / `provisional` entities.

    Reuses the same `.status-badge` visual language already shown for
    Active/Retired state near a detail page's title (see styles.css), so
    list rows and detail headers can drop in the same indicator. Renders
    nothing for `verified` (the sources panel below speaks for it) or for
    any other/blank state — this is a UI nicety, not the security boundary
    (that's VerificationQuerySet.public() in models.py; a rejected entity
    never reaches a template that could call this).
    """
    state = getattr(entity, "verification_state", None)
    return {"state_display": VERIFICATION_STATE_DISPLAY.get(state)}


@register.inclusion_tag("partials/verification_stamp.html")
def verification_stamp(entity):
    """
    Render the "Verified from" footer for an entity detail page.

    Pulls every source we have direct evidence for — either a successful
    SourceFetch row, or a stored profile URL on the entity itself. Trademarked
    databases get a generic display name; everything else is named & linked.
    Also carries `state_display` (see VERIFICATION_STATE_DISPLAY) so the same
    panel can lead with an honest "unverified" / "provisional" note instead
    of just going quiet when an entity has zero sources on file — which is
    the common case for a `candidate` row.
    """
    state_display = VERIFICATION_STATE_DISPLAY.get(getattr(entity, "verification_state", None))
    empty = {"sources": [], "total": 0, "verified_count": 0, "linked_count": 0}

    entity_type = _entity_type_for(entity)
    if entity_type is None:
        return {**empty, "state_display": state_display}

    # Late import to avoid top-level wrestlebot dependency in owdbapp.
    try:
        from owdb_django.wrestlebot.models import SourceFetch
    except Exception:
        return {**empty, "state_display": state_display}

    fetches = SourceFetch.objects.filter(
        entity_type=entity_type, entity_id=entity.id, http_status=200
    ).order_by("source", "-fetched_at")
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
                display = SOURCE_DISPLAY.get(
                    source_key, {"name": "External source", "homepage": None}
                )
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
        "state_display": state_display,
    }


@register.simple_tag
def verification_short(entity) -> str:
    """One-liner version for places where the inclusion tag is too heavy."""
    data = verification_stamp(entity)
    n = data["total"]
    if n == 0:
        return ""
    return mark_safe(
        f"<small class='verification-short'>Verified from {n} source{'s' if n != 1 else ''}</small>"
    )
