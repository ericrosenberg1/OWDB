"""
Agent tool registry for JR and Earl.

Every tool here:
  1. Has an Anthropic-compatible JSON Schema in `input_schema`
  2. Is implemented by `handler(**kwargs)` returning a JSON-serialisable dict
  3. Wraps an existing pipeline operation — NEVER bypasses accuracy guards

Tools are deliberately small and composable: the agent decides the sequence.
Pipeline modules contain the real logic (extraction, persistence, verification);
this file is just a thin adapter between the LLM and those modules.

If a tool needs to add data to the DB, it MUST go through the existing
persist_* functions in `wrestlebot.pipeline.*` so that FieldProvenance,
classification gates, redirect detection, etc. all run as usual.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tool definition primitive
# ---------------------------------------------------------------------------


@dataclass
class AgentTool:
    name: str
    description: str
    input_schema: dict
    handler: Callable[..., dict]

    def to_anthropic(self) -> dict:
        """Convert to the dict shape Anthropic's tool_use API expects."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


def _ok(**kwargs) -> dict:
    out = {"ok": True}
    out.update(kwargs)
    return out


def _err(message: str, **kwargs) -> dict:
    out = {"ok": False, "error": message}
    out.update(kwargs)
    return out


def _truncate(s: str, n: int = 2000) -> str:
    if s is None:
        return ""
    s = str(s)
    return s if len(s) <= n else s[:n] + f"… [+{len(s) - n} chars]"


# ---------------------------------------------------------------------------
# Shared tools (both JR and Earl)
# ---------------------------------------------------------------------------


def _t_brave_search(query: str, count: int = 10, freshness: Optional[str] = None) -> dict:
    """Run a Brave Web Search."""
    from ..sources import brave_search
    hits = brave_search.search(query=query, count=count, freshness=freshness)
    if not hits and not brave_search.available():
        return _err("Brave Search API key not configured (BRAVE_SEARCH_API_KEY).")
    return _ok(hits=[h.to_dict() for h in hits], count=len(hits))


# ---------------------------------------------------------------------------
# Additional data-source tools (Commons, MusicBrainz, TMDB, Discogs, scrapers)
# ---------------------------------------------------------------------------


def _t_lookup_wrestler_image(name: str, prop: str = "P18") -> dict:
    """Wikidata-driven image lookup via Wikimedia Commons. Returns the file's
    license + attribution metadata so the agent can verify legal use before
    assigning."""
    from ..sources import commons
    if prop not in ("P18", "P154", "P109"):
        return _err(f"unknown property {prop!r}; use P18 (image), P154 (logo), or P109 (signature)")
    r = commons.fetch_image_for_wikipedia_title(name, prop=prop)
    if r is None:
        return _ok(found=False)
    # Also pull full Commons metadata so the agent can see the license.
    meta = commons.fetch_image_metadata(r["filename"])
    if meta is not None:
        r.update({
            "license_code": meta.license_code,
            "license_short": meta.license_short,
            "artist": meta.artist,
            "attribution_required": meta.attribution_required,
            "is_legally_usable": meta.is_allowed,
            "rejection_reason": meta.rejection_reason,
            "dimensions": f"{meta.width}x{meta.height}",
        })
    return _ok(found=True, **r)


def _t_assign_image_to_entity(entity_type: str, entity_id: int,
                              prop: Optional[str] = None,
                              force: bool = False) -> dict:
    """
    Assign an image to a wrestler/event/promotion/etc. through the full
    accuracy + legal gate. Refuses on:
        - License missing / not in allow-list / NC/ND/non-free
        - Required attribution missing
        - Image too small for its entity type
        - QID can't be resolved
    Writes FieldProvenance + archives prior image to ImageHistory.
    """
    from owdb_django.owdbapp import models as dm
    from ..pipeline.images import assign_image_to_entity

    model_map = {
        "wrestler": dm.Wrestler, "event": dm.Event, "venue": dm.Venue,
        "promotion": dm.Promotion, "title": dm.Title, "stable": dm.Stable,
        "tv_show": dm.TVShow,
    }
    Model = model_map.get(entity_type)
    if Model is None:
        return _err(f"unknown entity_type={entity_type!r}; valid: {sorted(model_map)}")
    try:
        ent = Model.objects.get(id=entity_id)
    except Model.DoesNotExist:
        return _err(f"{entity_type}#{entity_id} not found")

    if prop is not None and prop not in ("P18", "P154", "P109"):
        return _err(f"unknown prop {prop!r}; valid: P18 (image), P154 (logo), P109 (signature)")

    result = assign_image_to_entity(
        ent, entity_type=entity_type, prop=prop, force=force,
    )
    return _ok(**result.to_dict())


def _entity_class_for_image_sweep(entity_type: str):
    """
    Resolve `entity_type` to the Django model class used by the image
    sweep. Centralised so the agent tool, CLI command, and any future
    Celery beat task all agree on the mapping.
    """
    from owdb_django.owdbapp import models as dm
    return {
        "wrestler":   dm.Wrestler,
        "promotion":  dm.Promotion,
        "event":      dm.Event,
        "venue":      dm.Venue,
        "title":      dm.Title,
        "stable":     dm.Stable,
        "tv_show":    dm.TVShow,
        "video_game": dm.VideoGame,
        "book":       dm.Book,
    }.get(entity_type)


def _t_assign_images_for_entities_without_images(
    entity_type: str = "wrestler",
    limit: int = 10,
    dry_run: bool = False,
) -> dict:
    """
    Batch image-gap sweep for any supported entity type.

    For each entity of `entity_type` that has no image but a known
    Wikipedia URL, walks the cascade (Wikidata P18/P154 → Commons
    category → Wikipedia body images) and applies all gates:
    legal license whitelist, dimension floor, identity confidence,
    AND — for events — the promotional-art guard that refuses CC
    photos of trademarked posters / keyart / press kits.

    Promotions, stables, and TV shows use Wikidata P154 (logo) by
    default. Their `image_credit` includes a nominative fair-use
    notice on write (logos are trademarks; reference-DB use is
    protected under U.S. trademark doctrine and the EU equivalent).

    `dry_run=True` runs the full cascade and reports verdicts WITHOUT
    writing anything (good for previewing coverage before committing).
    """
    from ..pipeline.images import assign_image_to_entity

    Model = _entity_class_for_image_sweep(entity_type)
    if Model is None:
        return _err(
            f"unknown entity_type {entity_type!r}; valid: "
            f"wrestler, promotion, event, venue, title, stable, tv_show"
        )
    if limit < 1 or limit > 50:
        return _err("limit must be between 1 and 50")

    # Some models (Wrestler, Promotion, Venue) carry a `wikipedia_url`
    # field; others (Event, Title) don't and rely on the cascade falling
    # back to `name` as the Wikipedia title. Build the queryset
    # conditionally so we don't FieldError on the no-wiki-url models.
    qs = Model.objects.filter(image_url__isnull=True)
    has_wiki_url_field = any(
        f.name == "wikipedia_url" for f in Model._meta.get_fields()
    )
    if has_wiki_url_field:
        qs = qs.exclude(wikipedia_url__exact="").exclude(
            wikipedia_url__isnull=True,
        )
    order_field = "name" if any(
        f.name == "name" for f in Model._meta.get_fields()
    ) else "id"
    targets = qs.order_by(order_field)[: int(limit)]

    results = []
    assigned = refused = 0
    for ent in targets:
        ent_name = getattr(ent, "name", None) or getattr(ent, "title", None) or str(ent.id)
        try:
            r = assign_image_to_entity(ent, entity_type=entity_type, force=False)
        except Exception as e:
            logger.exception("image sweep crashed on %s#%s", entity_type, ent.id)
            results.append({
                "entity_id": ent.id, "name": ent_name,
                "success": False,
                "refusal_reason": f"crashed: {type(e).__name__}: {e}",
                "considered_count": 0,
            })
            refused += 1
            continue

        if dry_run and r.success:
            # Roll the field writes back; the cascade already wrote them
            # in-place to the entity. The transactional rollback only
            # works at a higher layer, so we explicitly null them here.
            #
            # NOTE: we keep the SourceFetch + FieldProvenance rows because
            # those are part of the audit trail — they correctly record
            # that we LOOKED at this image, which is true even in dry-run.
            ent.image_url = None
            ent.image_source_url = None
            ent.image_original_url = None
            ent.image_license = ""
            ent.image_credit = ""
            ent.image_fetched_at = None
            ent.save(update_fields=[
                "image_url", "image_source_url", "image_original_url",
                "image_license", "image_credit", "image_fetched_at",
            ])

        if r.success:
            assigned += 1
        else:
            refused += 1
        results.append({
            "entity_id": ent.id,
            "name": ent_name,
            "success": r.success,
            "source_path": r.source_path,
            "identity_confidence": r.identity_confidence,
            "image_license": r.image_license,
            "refusal_reason": r.refusal_reason,
            "considered_count": len(r.considered),
        })

    return _ok(
        entity_type=entity_type,
        sweep_size=len(results),
        assigned=assigned,
        refused=refused,
        dry_run=dry_run,
        results=results,
    )


# Back-compat shim: the old wrestler-only tool name keeps working.
def _t_assign_images_for_wrestlers_without_images(
    limit: int = 10, dry_run: bool = False,
) -> dict:
    return _t_assign_images_for_entities_without_images(
        entity_type="wrestler", limit=limit, dry_run=dry_run,
    )


def _t_musicbrainz_search(title: str, artist: Optional[str] = None,
                          limit: int = 10) -> dict:
    from ..sources import musicbrainz
    hits = musicbrainz.search_recordings(title, artist=artist, limit=limit)
    return _ok(hits=[h.to_dict() for h in hits], count=len(hits))


def _t_tmdb_search(query: str, kind: str = "wrestling", limit: int = 10) -> dict:
    from ..sources import tmdb
    if not tmdb.available():
        return _err("TMDB API key not configured (TMDB_API_KEY).")
    if kind == "tv":
        rows = tmdb.search_show(query, limit=limit)
        return _ok(tv=rows, movies=[], count=len(rows))
    if kind == "movie":
        rows = tmdb.search_movie(query, limit=limit)
        return _ok(tv=[], movies=rows, count=len(rows))
    # default: wrestling-aware combined search
    combined = tmdb.search_wrestling(query, limit=limit)
    return _ok(tv=combined.get("tv", []), movies=combined.get("movies", []),
               count=len(combined.get("tv", [])) + len(combined.get("movies", [])))


def _t_discogs_search(query: str, type: str = "release",
                     artist: Optional[str] = None,
                     year: Optional[str] = None, limit: int = 10) -> dict:
    from ..sources import discogs
    if not discogs.available():
        return _err("Discogs token not configured (DISCOGS_TOKEN).")
    hits = discogs.search(query, type=type, artist=artist, year=year, limit=limit)
    return _ok(hits=[h.to_dict() for h in hits], count=len(hits))


def _t_wrestlingdata_search(query: str, limit: int = 10) -> dict:
    """
    Search Wrestlingdata.com. NOTE: currently blocked by Cloudflare bot
    challenge — returns empty until a headless-browser fetcher is wired in.
    """
    from ..sources import wrestlingdata
    hits = wrestlingdata.search(query, limit=limit)
    return _ok(
        hits=[{"name": h.name, "url": h.url, "type": h.type} for h in hits],
        count=len(hits),
        note=("Wrestlingdata.com is Cloudflare-protected; returns empty "
              "without a headless-browser fetcher. Try profightdb_search instead.")
              if not hits else "",
    )


def _t_wrestlingdata_profile(url: str) -> dict:
    from ..sources import wrestlingdata
    prof = wrestlingdata.fetch_wrestler_profile(url)
    if prof is None:
        return _err("could not fetch (often Cloudflare-blocked)")
    return _ok(**prof.to_dict())


def _t_profightdb_search(query: str, limit: int = 10) -> dict:
    from ..sources import profightdb
    hits = profightdb.search(query, limit=limit)
    return _ok(
        hits=[{"name": h.name, "url": h.url, "promotion": h.promotion} for h in hits],
        count=len(hits),
    )


def _t_profightdb_profile(url: str) -> dict:
    from ..sources import profightdb
    prof = profightdb.fetch_wrestler_profile(url)
    if prof is None:
        return _err("could not fetch profile")
    return _ok(**prof.to_dict())


# Curated set of wrestling news + coverage domains. The news tool defaults
# to these (filtered through Tavily) so agents get focused results rather
# than general-web noise. Adding/removing domains here is the single control
# knob for "what counts as a wrestling news source".
WRESTLING_NEWS_DOMAINS = (
    # English-language wrestling news / coverage
    "espn.com",                  # general sports + occasional wrestling editorial
    "wrestlinginc.com",
    "fightful.com",
    "pwmania.com",
    "wrestlezone.com",
    "ringsidenews.com",
    "411mania.com",
    "prowrestling.net",
    "wrestlingnewsworld.com",
    "wrestlingobserver.com",     # mostly paywalled but headlines visible
    "pwinsider.com",             # premium but headlines visible
    "voicesofwrestling.com",
    "lastwordonprowrestling.com",
    "cagesideseats.com",
    "sescoops.com",
    # Official promotion sites
    "wwe.com",
    "aew.com",
    "njpw1972.com",
    "impactwrestling.com",
    "rohwrestling.com",
)


def _t_news_search(query: str, max_results: int = 8,
                  days: int = 14,
                  domains: Optional[list] = None,
                  only_wrestling_sources: bool = True) -> dict:
    """
    Wrestling-news search via Tavily's news topic.

    Defaults to recent (past 14 days) and filtered to the curated
    WRESTLING_NEWS_DOMAINS list, so results are real coverage rather
    than message-board noise. Pass only_wrestling_sources=False to
    search the open web instead.
    """
    from ..sources import tavily_search
    if only_wrestling_sources and not domains:
        domains = list(WRESTLING_NEWS_DOMAINS)
    r = tavily_search.search(
        query=query,
        max_results=max_results,
        search_depth="basic",
        topic="news",
        include_answer=True,
        include_domains=domains,
    )
    if r is None:
        return _err("Tavily not configured (TAVILY_API_KEY).")
    return _ok(
        query=r.query,
        answer=r.answer,
        days=days,
        domains=domains or [],
        hits=[h.to_dict() for h in r.hits],
        count=len(r.hits),
    )


def _t_tavily_search(query: str, max_results: int = 8,
                    search_depth: str = "basic",
                    include_answer: bool = True,
                    topic: str = "general",
                    include_domains: Optional[list] = None,
                    exclude_domains: Optional[list] = None) -> dict:
    """Run a Tavily search (LLM-tuned). Returns hits plus an optional answer hint."""
    from ..sources import tavily_search
    r = tavily_search.search(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        topic=topic,
        include_answer=include_answer,
        include_domains=include_domains,
        exclude_domains=exclude_domains,
    )
    if r is None:
        return _err("Tavily API key not configured (TAVILY_API_KEY).")
    return _ok(
        query=r.query,
        answer=r.answer,
        hits=[h.to_dict() for h in r.hits],
        count=len(r.hits),
        response_time_seconds=r.response_time_seconds,
    )


def _t_wiki_fetch(name: str, entity_type: str = "wrestler", force: bool = False) -> dict:
    """Fetch a Wikipedia page through the standard pipeline."""
    from ..pipeline import fetch as fetch_mod
    method = {
        "wrestler": fetch_mod.fetch_wrestler_candidates,
        "event": fetch_mod.fetch_event_candidates,
        "venue": fetch_mod.fetch_venue_candidates,
        "promotion": fetch_mod.fetch_promotion_candidates,
        "book": fetch_mod.fetch_book_candidates,
        "video_game": fetch_mod.fetch_video_game_candidates,
        "podcast": fetch_mod.fetch_podcast_candidates,
        "action_figure": fetch_mod.fetch_action_figure_candidates,
        "theme_song": fetch_mod.fetch_theme_song_candidates,
        "title": fetch_mod.fetch_title_candidates,
        "stable": fetch_mod.fetch_stable_candidates,
        "tv_show": fetch_mod.fetch_tv_show_candidates,
        "special": fetch_mod.fetch_special_candidates,
    }.get(entity_type)
    if method is None:
        return _err(f"unknown entity_type={entity_type!r}")
    results = method([name], force=force) or []
    summary = []
    for r in results:
        summary.append({
            "candidate_name": getattr(r, "candidate_name", None),
            "fetch_id": getattr(r, "id", None),
            "http_status": getattr(r, "http_status", None),
            "url": getattr(r, "url", None),
            "entity_type": getattr(r, "entity_type", None),
            "used_at": str(getattr(r, "used_at", "") or "") or None,
        })
    return _ok(fetched=summary, count=len(summary))


def _t_extract_and_persist(fetch_id: int) -> dict:
    """Run extract+persist on a single SourceFetch row."""
    from ..models import SourceFetch
    from ..bots.jr import JR
    try:
        fetch = SourceFetch.objects.get(id=fetch_id)
    except SourceFetch.DoesNotExist:
        return _err(f"SourceFetch#{fetch_id} not found")
    if fetch.used_at:
        return _ok(
            already_processed=True,
            entity_type=fetch.entity_type,
            candidate_name=fetch.candidate_name,
        )
    jr = JR()
    ok = jr._extract_and_persist_one(fetch)
    fetch.refresh_from_db()
    return _ok(
        persisted=bool(ok),
        entity_type=fetch.entity_type,
        candidate_name=fetch.candidate_name,
        used_at=str(fetch.used_at) if fetch.used_at else None,
    )


def _t_list_recent_fetches(limit: int = 20, entity_type: Optional[str] = None,
                          only_unprocessed: bool = False) -> dict:
    from ..models import SourceFetch
    qs = SourceFetch.objects.order_by("-fetched_at")
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if only_unprocessed:
        qs = qs.filter(used_at__isnull=True, http_status=200)
    qs = qs[:max(1, min(limit, 100))]
    rows = [{
        "id": f.id,
        "candidate_name": f.candidate_name,
        "entity_type": f.entity_type,
        "http_status": f.http_status,
        "fetched_at": str(f.fetched_at),
        "used_at": str(f.used_at) if f.used_at else None,
        "url": f.url,
    } for f in qs]
    return _ok(rows=rows, count=len(rows))


def _t_get_entity_summary(entity_type: str, entity_id: int) -> dict:
    """Read back an entity's fields + provenance."""
    from owdb_django.owdbapp import models as dm
    from ..models import FieldProvenance

    model_map = {
        "wrestler": dm.Wrestler,
        "event": dm.Event,
        "venue": dm.Venue,
        "promotion": dm.Promotion,
        "book": getattr(dm, "Book", None),
        "video_game": getattr(dm, "VideoGame", None),
        "podcast": getattr(dm, "Podcast", None),
        "action_figure": getattr(dm, "ActionFigure", None),
        "theme_song": getattr(dm, "ThemeSong", None),
        "title": getattr(dm, "Title", None),
        "stable": getattr(dm, "Stable", None),
        "tv_show": getattr(dm, "TVShow", None),
        "special": getattr(dm, "Special", None),
        "training_school": getattr(dm, "TrainingSchool", None),
    }
    Model = model_map.get(entity_type)
    if Model is None:
        return _err(f"unknown entity_type={entity_type!r}")
    try:
        obj = Model.objects.get(id=entity_id)
    except Model.DoesNotExist:
        return _err(f"{entity_type}#{entity_id} not found")

    # Pull a curated subset of fields rather than __dict__ (which leaks _state).
    fields = {}
    for f in obj._meta.fields:
        v = getattr(obj, f.name, None)
        if hasattr(v, "isoformat"):
            v = v.isoformat()
        fields[f.name] = v

    # Provenance rows for this entity.
    prov_qs = FieldProvenance.objects.filter(
        entity_type=entity_type, entity_id=entity_id,
    ).select_related("source_fetch")[:50]
    provenance = [{
        "field": p.field_name,
        "value": _truncate(p.value, 300),
        "source": p.source_fetch.source if p.source_fetch else None,
        "source_url": p.source_fetch.url if p.source_fetch else None,
        "snippet": _truncate(p.snippet, 300),
        "confidence": p.confidence,
    } for p in prov_qs]

    return _ok(entity_type=entity_type, entity_id=entity_id,
               fields=fields, provenance=provenance)


def _t_note_finding(note: str, tag: str = "") -> dict:
    """Free-form journal entry. Logged to the session for later review."""
    logger.info("AGENT NOTE [%s]: %s", tag or "-", _truncate(note, 500))
    return _ok(recorded=True, length=len(note))


# ---------------------------------------------------------------------------
# JR-specific tools
# ---------------------------------------------------------------------------


def _t_discover_missing_trainers() -> dict:
    from ..pipeline.linking import link_trainers_sweep
    result = link_trainers_sweep()
    return _ok(
        missing_trainer_names=result.get("missing_names", []),
        linked_count=result.get("linked", 0),
    )


def _t_discover_notable_wrestlers(limit: int = 20) -> dict:
    from ..pipeline.discovery import discover_wrestlers
    names = discover_wrestlers(per_category_limit=3, total_limit=max(1, min(limit, 50)))
    return _ok(candidates=names, count=len(names))


def _t_discover_notable_events(limit: int = 20) -> dict:
    from ..pipeline.discovery import discover_events
    names = discover_events(per_category_limit=3, total_limit=max(1, min(limit, 50)))
    return _ok(candidates=names, count=len(names))


def _t_discover_notable_promotions(limit: int = 30) -> dict:
    from ..pipeline.discovery import discover_promotions
    names = discover_promotions(per_category_limit=3, total_limit=max(1, min(limit, 100)))
    return _ok(candidates=names, count=len(names))


def _t_discover_notable_podcasts(limit: int = 30) -> dict:
    from ..pipeline.discovery import discover_podcasts
    names = discover_podcasts(per_category_limit=5, total_limit=max(1, min(limit, 100)))
    return _ok(candidates=names, count=len(names))


def _t_ingest_ppv_list(promotion_key: str) -> dict:
    """Bulk-ingest all PPVs for a promotion from its Wikipedia list page."""
    from ..pipeline.event_lists import ingest_ppv_list
    return _ok(**ingest_ppv_list(promotion_key))


def _t_ingest_episode_list(show_key: str) -> dict:
    """Bulk-ingest TV episodes for a show from its Wikipedia list page."""
    from ..pipeline.event_lists import ingest_episode_list
    return _ok(**ingest_episode_list(show_key))


def _t_discover_notable_venues(limit: int = 20) -> dict:
    from ..pipeline.discovery import discover_venues
    names = discover_venues(per_category_limit=3, total_limit=max(1, min(limit, 50)))
    return _ok(candidates=names, count=len(names))


def _t_discover_top_mentions(limit: int = 30) -> dict:
    from ..pipeline.auto_discovery import top_unresolved_mentions
    rows = top_unresolved_mentions(limit=max(1, min(limit, 200)))
    return _ok(mentions=[{"name": n, "count": c} for n, c in rows], count=len(rows))


def _t_auto_discover_mentions(limit: int = 5) -> dict:
    from ..pipeline.auto_discovery import auto_discover_step
    stats = auto_discover_step(limit=max(1, min(limit, 20)))
    return _ok(
        fetched=stats.fetched,
        skipped_generic=stats.skipped_generic,
        skipped_unclassified=stats.skipped_unclassified,
    )


def _t_generate_bio(wrestler_id: int) -> dict:
    """Generate + verify a wrestler bio. Saves only if verified."""
    from owdb_django.owdbapp.models import Wrestler
    from ..claude_client import ClaudeClient
    from ..pipeline.bio import generate_and_verify_with_retry
    try:
        w = Wrestler.objects.get(id=wrestler_id)
    except Wrestler.DoesNotExist:
        return _err(f"Wrestler#{wrestler_id} not found")
    client = ClaudeClient()
    if not client.available:
        return _err("No Claude credentials available for bio generation.")
    bio = generate_and_verify_with_retry(w, client=client)
    if bio is None:
        return _err("bio generation returned None (transient failure)")
    if bio.status == "verified":
        # Persist to wrestler.about same way the bot does.
        w.about = bio.text
        w.save(update_fields=["about", "updated_at"])
    return _ok(
        wrestler_id=wrestler_id,
        wrestler_name=w.name,
        bio_status=bio.status,
        bio_preview=_truncate(bio.text, 400),
        attempts=bio.attempts,
    )


def _t_crossvalidate_wikidata(limit: int = 5) -> dict:
    from ..bots.jr import JR
    n = JR()._stage_crossvalidate(max(1, min(limit, 20)))
    return _ok(crossvalidated=n)


def _t_run_jr_cycle(discovery: int = 5, fetch: int = 5, extract: int = 20,
                   crossvalidate: int = 5, bio: int = 5, auto_discover: int = 5) -> dict:
    """Run one full legacy JR cycle (escape hatch / catch-up)."""
    from ..bots.jr import JR
    stats = JR().cycle(
        discovery_limit=discovery, fetch_limit=fetch, extract_limit=extract,
        crossvalidate_limit=crossvalidate, bio_limit=bio,
        auto_discover_limit=auto_discover,
    )
    from dataclasses import asdict
    return _ok(stats=asdict(stats))


# ---------------------------------------------------------------------------
# Earl-specific tools
# ---------------------------------------------------------------------------


def _t_audit_all() -> dict:
    from ..bots.earl import Earl
    n = Earl().audit_all()
    return _ok(new_observations=n)


def _t_apply_safe_fixes() -> dict:
    from ..bots.earl import Earl
    n = Earl().apply_safe_fixes()
    return _ok(auto_fixes_applied=n)


def _t_score_rules() -> dict:
    from ..bots.earl import Earl
    n = Earl().score_rules()
    return _ok(rules_evaluated=n)


def _t_detect_patterns() -> dict:
    from ..bots.earl import Earl
    new = Earl().detect_patterns()
    return _ok(new_suggestions=new, count=len(new))


def _t_list_observations(rule_id: Optional[str] = None,
                        severity: Optional[str] = None,
                        status: str = "open",
                        limit: int = 20) -> dict:
    from ..models import EarlObservation
    qs = EarlObservation.objects.all()
    if status:
        qs = qs.filter(status=status)
    if rule_id:
        qs = qs.filter(rule_id=rule_id)
    if severity:
        qs = qs.filter(severity=severity)
    qs = qs.order_by("-severity", "-times_seen")[:max(1, min(limit, 100))]
    rows = [{
        "id": o.id,
        "rule_id": o.rule_id,
        "severity": o.severity,
        "entity_type": o.entity_type,
        "entity_id": o.entity_id,
        "entity_name": o.entity_name,
        "field": o.field_name,
        "value": _truncate(o.stored_value, 200),
        "issue": _truncate(o.issue_description, 300),
        "times_seen": o.times_seen,
        "status": o.status,
    } for o in qs]
    return _ok(rows=rows, count=len(rows))


def _t_list_suggestions(status: str = "pending", limit: int = 20) -> dict:
    from ..models import RuleSuggestion
    qs = RuleSuggestion.objects.filter(status=status).order_by("-proposed_at")
    qs = qs[:max(1, min(limit, 50))]
    rows = [{
        "id": s.id,
        "target_rule_id": s.target_rule_id,
        "kind": s.kind,
        "description": _truncate(s.description, 300),
        "rationale": _truncate(s.rationale, 500),
        "status": s.status,
    } for s in qs]
    return _ok(rows=rows, count=len(rows))


def _t_list_rule_scores(limit: int = 50) -> dict:
    from ..models import RuleScore
    qs = RuleScore.objects.order_by("-times_fired")[:max(1, min(limit, 200))]
    rows = [{
        "rule_id": r.rule_id, "kind": r.kind, "enabled": r.enabled,
        "times_fired": r.times_fired, "precision": float(r.precision),
        "last_evaluated": str(r.last_evaluated) if r.last_evaluated else None,
    } for r in qs]
    return _ok(rows=rows, count=len(rows))


def _t_update_observation(observation_id: int, status: str, notes: str = "") -> dict:
    """Mark an observation fixed/dismissed/false_positive."""
    from ..models import EarlObservation
    if status not in {"open", "fixed", "dismissed", "false_positive"}:
        return _err(f"invalid status={status!r}")
    try:
        obs = EarlObservation.objects.get(id=observation_id)
    except EarlObservation.DoesNotExist:
        return _err(f"EarlObservation#{observation_id} not found")
    obs.status = status
    if notes:
        obs.auto_fix_notes = (obs.auto_fix_notes + "\n" + notes).strip() if obs.auto_fix_notes else notes
    obs.save(update_fields=["status", "auto_fix_notes"])
    return _ok(updated=True, observation_id=observation_id, new_status=status)


def _t_inspect_provenance(entity_type: str, entity_id: int, field_name: str = "") -> dict:
    from ..models import FieldProvenance
    qs = FieldProvenance.objects.filter(entity_type=entity_type, entity_id=entity_id)
    if field_name:
        qs = qs.filter(field_name=field_name)
    rows = [{
        "field": p.field_name,
        "value": _truncate(p.value, 400),
        "source": p.source_fetch.source if p.source_fetch else None,
        "source_url": p.source_fetch.url if p.source_fetch else None,
        "snippet": _truncate(p.snippet, 400),
        "confidence": p.confidence,
        "captured_at": str(p.captured_at) if p.captured_at else None,
    } for p in qs[:50]]
    return _ok(rows=rows, count=len(rows))


def _t_extract_matches_for_event(event_id: int) -> dict:
    """Extract Match rows from a stored Wikipedia event fetch."""
    from owdb_django.owdbapp.models import Event
    from ..pipeline.match_extract import persist_matches_for_event
    try:
        ev = Event.objects.get(id=event_id)
    except Event.DoesNotExist:
        return _err(f"Event#{event_id} not found")
    return _ok(event_id=event_id, event_name=ev.name,
               **persist_matches_for_event(ev))


def _t_ingest_pwi(list_kind: str = "pwi_500", year: int = 2024) -> dict:
    """Ingest one PWI ranking list (year + kind) from ProFightDB."""
    from ..pipeline.pwi import ingest_pwi_list, PFDB_PWI_URLS
    if list_kind not in PFDB_PWI_URLS:
        return _err(f"unknown list_kind={list_kind!r}; valid: {sorted(PFDB_PWI_URLS)}")
    return _ok(list_kind=list_kind, year=year,
               **ingest_pwi_list(list_kind, year))


def _t_done(summary: str = "") -> dict:
    """
    Agent declares the task complete. The runner watches for this tool and
    exits the loop once it sees it.
    """
    return _ok(done=True, summary=_truncate(summary, 2000))


# ---------------------------------------------------------------------------
# Al-specific tools (interlinking + graph-gap closing)
# ---------------------------------------------------------------------------


def _t_list_unresolved_mentions(source_entity_type: Optional[str] = None,
                                limit: int = 30) -> dict:
    """
    Top unresolved mention targets. Optionally filter by where the mention
    was found (e.g., source_entity_type='venue' to focus on mentions inside
    venue prose).
    """
    from collections import Counter
    from ..models import EntityMention, SourceFetch
    from ..pipeline.classifier import is_generic_wiki_title
    from ..pipeline.auto_discovery import _existing_entity_wiki_titles

    qs = EntityMention.objects.filter(resolved_entity_id__isnull=True)
    if source_entity_type:
        qs = qs.filter(source_entity_type=source_entity_type)

    fetched_names = set(
        SourceFetch.objects.filter(source="wikipedia")
        .values_list("candidate_name", flat=True).distinct()
    )
    existing = _existing_entity_wiki_titles()

    counts: Counter = Counter()
    sample_sources: dict[str, list[dict]] = {}
    for m in qs.values("wiki_link", "mention_text",
                        "source_entity_type", "source_entity_id")[:5000]:
        link = m["wiki_link"]
        if not link or is_generic_wiki_title(link):
            continue
        if link in fetched_names or link in existing:
            continue
        counts[link] += 1
        if link not in sample_sources:
            sample_sources[link] = []
        if len(sample_sources[link]) < 3:
            sample_sources[link].append({
                "source_type": m["source_entity_type"],
                "source_id": m["source_entity_id"],
                "as_text": m["mention_text"],
            })

    rows = []
    for link, n in counts.most_common(max(1, min(limit, 200))):
        rows.append({
            "wiki_link": link,
            "count": n,
            "sampled_from": sample_sources.get(link, []),
        })
    return _ok(rows=rows, count=len(rows))


def _t_resolve_all_mentions() -> dict:
    """Re-run the mention-resolver across all entity types."""
    from ..pipeline.linking import resolve_all_mentions
    result = resolve_all_mentions()
    return _ok(linked=result)


def _t_link_trainers_sweep() -> dict:
    """Close the trained-by graph: link wrestlers to trainer entities."""
    from ..pipeline.linking import link_trainers_sweep
    result = link_trainers_sweep()
    return _ok(
        linked=result.get("linked", 0),
        missing_names=result.get("missing_names", []),
    )


def _t_link_wrestler_promotions(wrestler_id: int) -> dict:
    """Scan a wrestler's stored Wikipedia content for promotion mentions
    and create WrestlerPromotionHistory links. Conservative: requires ≥2
    Wikipedia link hits before creating a link."""
    from owdb_django.owdbapp.models import Wrestler
    from ..pipeline.wrestler_linking import link_wrestler_promotions
    try:
        w = Wrestler.objects.get(id=wrestler_id)
    except Wrestler.DoesNotExist:
        return _err(f"Wrestler#{wrestler_id} not found")
    report = link_wrestler_promotions(w)
    return _ok(**report.to_dict())


def _t_link_all_unlinked_wrestlers(limit: int = 20) -> dict:
    """Bulk version: process all wrestlers with <2 promotion links."""
    from ..pipeline.wrestler_linking import link_all_unlinked_wrestlers
    return _ok(**link_all_unlinked_wrestlers(limit=max(1, min(limit, 100))))


def _t_wrestlers_due_for_review(days_since_review: int = 14,
                                limit: int = 20) -> dict:
    """Living-database rotation: surface wrestlers whose data hasn't been
    refreshed in N days. Incomplete entries (no bio / no image / no
    promotion links) come first."""
    from ..pipeline.wrestler_linking import wrestlers_due_for_review
    rows = wrestlers_due_for_review(
        days_since_review=max(1, days_since_review),
        limit=max(1, min(limit, 200)),
    )
    return _ok(
        count=len(rows),
        wrestlers=[{
            "id": w.id, "name": w.name,
            "updated_at": str(w.updated_at),
            "has_bio": bool(w.about),
            "has_image": bool(w.image_url),
            "promotion_count": w.promotion_history.count(),
        } for w in rows],
    )


def _t_find_incomplete_wrestlers(limit: int = 20) -> dict:
    """JR's completion-focus tool: return wrestlers ranked by how MUCH
    they're missing (bio + image + promotions + matches). Prioritises
    completion over new ingest."""
    from django.db.models import Count
    from owdb_django.owdbapp.models import Wrestler
    qs = (Wrestler.objects
          .annotate(n_matches=Count("matches", distinct=True),
                    n_promos=Count("promotion_history", distinct=True))
          .order_by("id"))
    scored = []
    for w in qs.iterator():
        score = 0
        missing: list[str] = []
        if not w.about:
            score += 4; missing.append("about")
        if not w.image_url:
            score += 3; missing.append("image")
        if w.n_promos == 0:
            score += 2; missing.append("promotion_history")
        elif w.n_promos < 2:
            score += 1; missing.append("promotion_history<2")
        if w.n_matches == 0:
            score += 2; missing.append("matches")
        if not getattr(w, "birth_date", None):
            score += 1; missing.append("birth_date")
        if score >= 2:
            scored.append((score, w, missing))
    scored.sort(key=lambda t: -t[0])
    rows = [{
        "id": w.id, "name": w.name, "incompleteness_score": s,
        "missing": miss,
    } for s, w, miss in scored[:max(1, min(limit, 100))]]
    return _ok(count=len(rows), wrestlers=rows)


def _t_ingest_title_history(title_slug: Optional[str] = None,
                           max_unknown_to_queue: int = 15) -> dict:
    """Discover wrestlers from a Wikipedia 'List of X Champions' article.
    Queues unknown champions for ingest via the standard fetch path."""
    from ..pipeline.title_history import (
        ingest_title_history_discovery, TITLE_HISTORY_PAGES,
    )
    if title_slug and title_slug not in TITLE_HISTORY_PAGES:
        return _err(
            f"Unknown title_slug={title_slug!r}; valid: {sorted(TITLE_HISTORY_PAGES)}"
        )
    return _ok(**ingest_title_history_discovery(
        title_slug=title_slug,
        max_unknown_to_queue=max(1, min(max_unknown_to_queue, 50)),
    ))


def _t_mentions_for_entity(entity_type: str, entity_id: int,
                          only_unresolved: bool = False, limit: int = 50) -> dict:
    """
    Show what an entity's source content references. Useful for finding
    'unpolished gems' — names this entity mentions that aren't yet in the DB.
    """
    from ..models import EntityMention
    qs = EntityMention.objects.filter(
        source_entity_type=entity_type, source_entity_id=entity_id,
    )
    if only_unresolved:
        qs = qs.filter(resolved_entity_id__isnull=True)
    qs = qs.order_by("-extracted_at")[:max(1, min(limit, 200))]
    rows = [{
        "id": m.id,
        "mention_text": m.mention_text,
        "wiki_link": m.wiki_link,
        "resolved": bool(m.resolved_entity_id),
        "resolved_entity_type": m.resolved_entity_type,
        "resolved_entity_id": m.resolved_entity_id,
    } for m in qs]
    return _ok(rows=rows, count=len(rows))


def _t_rescan_entity_for_mentions(entity_type: str, entity_id: int) -> dict:
    """
    Re-extract mentions from an entity's latest stored source fetch. Useful
    when the extractor was improved after a fetch was processed.
    """
    from ..models import SourceFetch
    from ..pipeline.mentions import persist_mentions_for_entity
    fetch = (SourceFetch.objects
             .filter(entity_type=entity_type, entity_id=entity_id,
                     source="wikipedia", http_status=200)
             .order_by("-fetched_at").first())
    if fetch is None:
        return _err(f"no wikipedia SourceFetch found for {entity_type}#{entity_id}")
    # persist_mentions_for_entity's real signature is
    # (entity_type, entity_id, fetch) — positional. The earlier kwarg
    # names (`source_entity_type=` / `source_entity_id=`) referred to
    # EntityMention column names and would always raise TypeError.
    try:
        n = persist_mentions_for_entity(entity_type, entity_id, fetch)
    except Exception as e:
        logger.exception("persist_mentions_for_entity crashed")
        return _err(f"rescan failed: {type(e).__name__}: {e}")
    return _ok(mentions_persisted=n, fetch_id=fetch.id)


def _t_list_entities_with_unresolved_mentions(entity_type: str = "wrestler",
                                              min_count: int = 3,
                                              limit: int = 20) -> dict:
    """
    Find entities whose own prose references many unresolved targets. These
    are the highest-value sources of 'unpolished gems' for Al to focus on.
    """
    from django.db.models import Count
    from ..models import EntityMention
    qs = (EntityMention.objects
          .filter(resolved_entity_id__isnull=True,
                  source_entity_type=entity_type)
          .values("source_entity_id")
          .annotate(n=Count("id"))
          .filter(n__gte=min_count)
          .order_by("-n"))[:max(1, min(limit, 100))]
    rows = [{"entity_type": entity_type, "entity_id": r["source_entity_id"],
              "unresolved_mention_count": r["n"]} for r in qs]
    return _ok(rows=rows, count=len(rows))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


SHARED_TOOLS: dict[str, AgentTool] = {
    "brave_search": AgentTool(
        name="brave_search",
        description=(
            "Run a Brave Web Search. Best for: broad discovery, finding "
            "official sites, current news, and 'what's out there' queries. "
            "Returns URLs, titles, and snippets — no synthesized answer. "
            "Prefer this when you want a wider view of the result space. "
            "You must still re-fetch any fact you decide to use through "
            "wiki_fetch (or another structured source) — Brave snippets are "
            "not treated as ground truth."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "count": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
                "freshness": {
                    "type": "string",
                    "enum": ["pd", "pw", "pm", "py"],
                    "description": "Optional time filter: pd=day, pw=week, pm=month, py=year.",
                },
            },
            "required": ["query"],
        },
        handler=_t_brave_search,
    ),
    "news_search": AgentTool(
        name="news_search",
        description=(
            "Search recent wrestling news. Wrapped over Tavily news mode, "
            "with results filtered to a curated set of wrestling-coverage "
            "domains (ESPN's wrestling editorial, Fightful, WrestlingInc, "
            "Ringside News, 411mania, PWInsider, official promotion sites, "
            "etc.). Returns hit titles, URLs, snippets, and a synthesized "
            "`answer` summary (HINT only — verify via wiki_fetch if you "
            "intend to persist anything from it). Pass "
            "only_wrestling_sources=false to search the wider news web."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "News query, e.g. 'WrestleMania 41 results'."},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 14,
                          "description": "How many days back to consider (advisory; Tavily news mode is recency-biased)."},
                "domains": {"type": "array", "items": {"type": "string"},
                             "description": "Override the curated wrestling-domain filter."},
                "only_wrestling_sources": {"type": "boolean", "default": True,
                                            "description": "If true, restrict to wrestling-coverage domains."},
            },
            "required": ["query"],
        },
        handler=_t_news_search,
    ),
    "tavily_search": AgentTool(
        name="tavily_search",
        description=(
            "Run a Tavily search (LLM-tuned). Best for: focused factual "
            "lookups ('when did X happen', 'who founded Y'), disambiguation, "
            "and fact-checking specific claims. Returns hits PLUS an optional "
            "LLM-synthesized `answer` summary that is a HINT only — never "
            "ground truth. Confirm any fact via wiki_fetch before persisting. "
            "Use search_depth='advanced' for harder lookups (costs more). "
            "Use include_domains=['en.wikipedia.org'] to constrain to Wikipedia."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query."},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                "search_depth": {
                    "type": "string", "enum": ["basic", "advanced"], "default": "basic",
                    "description": "'advanced' costs more but searches harder.",
                },
                "topic": {
                    "type": "string", "enum": ["general", "news"], "default": "general",
                },
                "include_answer": {"type": "boolean", "default": True},
                "include_domains": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Restrict results to these domains.",
                },
                "exclude_domains": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Drop results from these domains.",
                },
            },
            "required": ["query"],
        },
        handler=_t_tavily_search,
    ),
    "wiki_fetch": AgentTool(
        name="wiki_fetch",
        description=(
            "Fetch a Wikipedia page for a candidate name and run the full ingest "
            "pipeline (classifier, redirect detection, subject gate, content hash "
            "dedup). Returns a list with one fetch summary (id, http_status, url, "
            "entity_type). If fetched successfully, follow up with extract_and_persist "
            "passing the fetch_id."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Wikipedia page title or candidate name."},
                "entity_type": {
                    "type": "string",
                    "enum": ["wrestler", "event", "venue", "promotion", "book",
                              "video_game", "podcast", "action_figure", "theme_song",
                              "title", "stable", "tv_show", "special"],
                    "default": "wrestler",
                },
                "force": {"type": "boolean", "default": False,
                          "description": "Re-fetch even if a cached row exists."},
            },
            "required": ["name"],
        },
        handler=_t_wiki_fetch,
    ),
    "extract_and_persist": AgentTool(
        name="extract_and_persist",
        description=(
            "Run extract+persist on a previously fetched SourceFetch row. This "
            "creates / updates the DB entity (wrestler/event/etc.) with full "
            "FieldProvenance. Skipped if the fetch was already processed."
        ),
        input_schema={
            "type": "object",
            "properties": {"fetch_id": {"type": "integer"}},
            "required": ["fetch_id"],
        },
        handler=_t_extract_and_persist,
    ),
    "list_recent_fetches": AgentTool(
        name="list_recent_fetches",
        description="List recent SourceFetch rows. Useful for finding extraction backlog.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "entity_type": {"type": "string"},
                "only_unprocessed": {"type": "boolean", "default": False},
            },
        },
        handler=_t_list_recent_fetches,
    ),
    "get_entity_summary": AgentTool(
        name="get_entity_summary",
        description=(
            "Read a database entity's current fields plus per-field provenance "
            "(source URL + snippet). Use this to inspect data before deciding to "
            "act on it."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["wrestler", "event", "venue", "promotion", "book",
                              "video_game", "podcast", "action_figure", "theme_song",
                              "title", "stable", "tv_show", "special", "training_school"],
                },
                "entity_id": {"type": "integer"},
            },
            "required": ["entity_type", "entity_id"],
        },
        handler=_t_get_entity_summary,
    ),
    "note_finding": AgentTool(
        name="note_finding",
        description=(
            "Record a free-form note about what you found or decided. Useful for "
            "explaining why you took an action. Logged to the agent session."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "note": {"type": "string"},
                "tag": {"type": "string", "description": "Optional category tag."},
            },
            "required": ["note"],
        },
        handler=_t_note_finding,
    ),
    "extract_matches_for_event": AgentTool(
        name="extract_matches_for_event",
        description=(
            "Parse the Wikipedia 'Results' table on an Event's stored "
            "SourceFetch and create Match + MatchParticipant rows. Idempotent "
            "— re-runs upsert by (event, card_position). Reports unmatched "
            "wrestler names so you can decide which to ingest next."
        ),
        input_schema={
            "type": "object",
            "properties": {"event_id": {"type": "integer"}},
            "required": ["event_id"],
        },
        handler=_t_extract_matches_for_event,
    ),
    "ingest_pwi": AgentTool(
        name="ingest_pwi",
        description=(
            "Ingest a published PWI ranking list (PWI 500, PWI Female 50/100/150) "
            "for a given year from ProFightDB's mirror. Creates an "
            "ExternalRanking and up to 500 ranked entries; matches positions "
            "to existing Wrestler rows where names align."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "list_kind": {"type": "string",
                              "enum": ["pwi_500", "pwi_female_50",
                                       "pwi_female_100", "pwi_female_150"],
                              "default": "pwi_500"},
                "year": {"type": "integer", "minimum": 1991, "maximum": 2099},
            },
            "required": ["year"],
        },
        handler=_t_ingest_pwi,
    ),
    "done": AgentTool(
        name="done",
        description=(
            "Declare the task complete. Call this once you've achieved (or "
            "cannot further progress) the goal. Include a one-paragraph summary."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Short summary of what was accomplished."},
            },
        },
        handler=_t_done,
    ),
    # ----- Additional data-source tools ------------------------------------
    "lookup_wrestler_image": AgentTool(
        name="lookup_wrestler_image",
        description=(
            "Resolve a Wikipedia title to its Wikimedia Commons image URL "
            "via Wikidata's P18 (image) property. Returns the full-size URL, "
            "a 400px thumbnail, AND the license + attribution metadata so "
            "you can verify legal use BEFORE calling assign_image_to_entity. "
            "Sets prop=P154 for organisation logos or P109 for signatures."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Wikipedia page title."},
                "prop": {
                    "type": "string", "enum": ["P18", "P154", "P109"], "default": "P18",
                    "description": "P18=image (default), P154=logo, P109=signature.",
                },
            },
            "required": ["name"],
        },
        handler=_t_lookup_wrestler_image,
    ),
    "assign_image_to_entity": AgentTool(
        name="assign_image_to_entity",
        description=(
            "Assign a verified Wikimedia Commons image to an OWDB entity. "
            "Walks a cascade: Wikidata P18 → Commons category (P373) → "
            "Wikipedia body images. Refuses on: license not in "
            "CC0/PD/CC-BY/CC-BY-SA, missing attribution where required, "
            "image too small, identity confidence below the per-entity-type "
            "floor (wrestlers require ≥ 75), or QID resolution failure. "
            "Writes the four image fields + FieldProvenance for each, "
            "archives the previous image to ImageHistory. The returned "
            "`considered` list shows every candidate tried + why it was "
            "accepted/rejected — useful for diagnosing why a wrestler "
            "still has no image."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["wrestler", "event", "venue", "promotion",
                              "title", "stable", "tv_show"],
                },
                "entity_id": {"type": "integer"},
                "prop": {
                    "type": "string", "enum": ["P18", "P154", "P109"],
                    "description": "Wikidata property; defaults per entity_type.",
                },
                "force": {"type": "boolean", "default": False,
                          "description": "Replace existing image if entity already has one."},
            },
            "required": ["entity_type", "entity_id"],
        },
        handler=_t_assign_image_to_entity,
    ),
    "assign_images_for_wrestlers_without_images": AgentTool(
        name="assign_images_for_wrestlers_without_images",
        description=(
            "Batch image-gap sweep. Picks up to `limit` wrestlers with "
            "no image but a known Wikipedia URL, walks each through the "
            "full cascade (P18 → Commons category → Wikipedia body), and "
            "reports per-wrestler outcome (which candidate was accepted, "
            "or why none passed). Use this for completion-mode sessions "
            "where JR's job is to close image gaps. `dry_run=True` "
            "previews coverage without writing entity fields (provenance "
            "rows are kept for audit). Refusals are NOT errors — they "
            "mean no Commons-hosted image of this wrestler exists yet."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
        handler=_t_assign_images_for_wrestlers_without_images,
    ),
    "assign_images_for_entities_without_images": AgentTool(
        name="assign_images_for_entities_without_images",
        description=(
            "Generic image-gap sweep — works for wrestlers, promotions, "
            "events, venues, titles, stables, and TV shows. Walks each "
            "matching entity through the cascade (Wikidata P18/P154 → "
            "Commons category → Wikipedia body images) and applies the "
            "same legal + identity + dimension gates as the wrestler "
            "sweep. For events specifically, an extra promotional-art "
            "guard refuses CC-licensed photos of trademarked posters / "
            "keyart / press kits — the photo itself may be cleared but "
            "the design underneath isn't. Promotion / stable / tv_show "
            "logos get a nominative fair-use notice appended to "
            "image_credit on write. Use this in place of the wrestler-"
            "only variant when you need to backfill non-wrestler images."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {
                    "type": "string",
                    "enum": ["wrestler", "promotion", "event", "venue",
                              "title", "stable", "tv_show",
                              "video_game", "book"],
                    "default": "wrestler",
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
        handler=_t_assign_images_for_entities_without_images,
    ),
    "musicbrainz_search": AgentTool(
        name="musicbrainz_search",
        description=(
            "Search MusicBrainz for a recording by title (and optional "
            "artist). Returns structured metadata: MBID, artist, first "
            "release date, length, ISRCs, and release titles. Use for "
            "verifying ThemeSong artist/release-year claims."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "artist": {"type": "string", "description": "Optional artist filter."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            },
            "required": ["title"],
        },
        handler=_t_musicbrainz_search,
    ),
    "tmdb_search": AgentTool(
        name="tmdb_search",
        description=(
            "Search TMDB (The Movie Database) for TV shows or films. "
            "kind='tv' for shows, 'movie' for films, 'wrestling' (default) "
            "for the wrestling-aware combined search. Returns title, "
            "release/air dates, poster URLs, and TMDB IDs. Use for "
            "verifying TVShow / Special entities."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "kind": {"type": "string", "enum": ["tv", "movie", "wrestling"], "default": "wrestling"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 10},
            },
            "required": ["query"],
        },
        handler=_t_tmdb_search,
    ),
    "discogs_search": AgentTool(
        name="discogs_search",
        description=(
            "Search Discogs for releases, masters, or artists. Best for "
            "wrestler theme-song albums (e.g. 'WWE: The Music Vol. 1') and "
            "verifying release years / labels."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "type": {"type": "string",
                          "enum": ["release", "master", "artist", "label"],
                          "default": "release"},
                "artist": {"type": "string"},
                "year": {"type": "string", "description": "Release year filter."},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
            },
            "required": ["query"],
        },
        handler=_t_discogs_search,
    ),
    "wrestlingdata_search": AgentTool(
        name="wrestlingdata_search",
        description=(
            "Search wrestlingdata.com. Note: the site is Cloudflare-protected "
            "and will return empty results from headless scraping until a "
            "browser-based fetcher is wired up. Prefer profightdb_search "
            "for now."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            },
            "required": ["query"],
        },
        handler=_t_wrestlingdata_search,
    ),
    "wrestlingdata_profile": AgentTool(
        name="wrestlingdata_profile",
        description=(
            "Fetch a wrestlingdata.com wrestler profile (currently "
            "Cloudflare-blocked — see wrestlingdata_search)."
        ),
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        handler=_t_wrestlingdata_profile,
    ),
    "profightdb_search": AgentTool(
        name="profightdb_search",
        description=(
            "Search ProFightDB (Internet Wrestling Database) for wrestlers "
            "by name. Returns hits with current-promotion tags and URLs."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
            },
            "required": ["query"],
        },
        handler=_t_profightdb_search,
    ),
    "profightdb_profile": AgentTool(
        name="profightdb_profile",
        description=(
            "Fetch a ProFightDB wrestler profile by URL. Returns birth date, "
            "place of birth, total match count, ring names, and championship "
            "history. Use as a cross-validation source against Wikipedia + "
            "Cagematch — never treat as primary unless those lack the field."
        ),
        input_schema={
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
        handler=_t_profightdb_profile,
    ),
}


JR_ONLY_TOOLS: dict[str, AgentTool] = {
    "discover_missing_trainers": AgentTool(
        name="discover_missing_trainers",
        description="Find trainer names referenced by wrestlers but absent from the DB.",
        input_schema={"type": "object", "properties": {}},
        handler=_t_discover_missing_trainers,
    ),
    "discover_notable_wrestlers": AgentTool(
        name="discover_notable_wrestlers",
        description="Discover notable wrestler candidates from Wikipedia categories.",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}},
        },
        handler=_t_discover_notable_wrestlers,
    ),
    "discover_notable_events": AgentTool(
        name="discover_notable_events",
        description="Discover notable event candidates from Wikipedia categories.",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}},
        },
        handler=_t_discover_notable_events,
    ),
    "discover_notable_promotions": AgentTool(
        name="discover_notable_promotions",
        description=(
            "Discover notable promotion candidates from Wikipedia categories. "
            "Covers WWE family (incl. NXT, AAA partnership), AEW, ROH, TNA, "
            "NJPW/AJPW/NOAH, lucha (AAA/CMLL), and independents (GCW, MLW, "
            "NWA, OVW, PWG, etc.)."
        ),
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30}},
        },
        handler=_t_discover_notable_promotions,
    ),
    "discover_notable_podcasts": AgentTool(
        name="discover_notable_podcasts",
        description=(
            "Discover notable wrestling-podcast candidates from a curated seed "
            "(Conrad Thompson, Jericho, Stone Cold, JR/Bischoff, Observer Radio, "
            "Busted Open, AEW Unrestricted, etc.) + Wikipedia podcast categories. "
            "Podcasts are a high-leverage source of wrestler/event/title "
            "mentions that grow the graph indirectly."
        ),
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 30}},
        },
        handler=_t_discover_notable_podcasts,
    ),
    "ingest_ppv_list": AgentTool(
        name="ingest_ppv_list",
        description=(
            "Bulk-ingest a promotion's PPV/supercard history from its "
            "Wikipedia list article. Creates Event rows with date, venue, "
            "and attendance for each entry. Idempotent — upserts by (name, "
            "date). Supported promotion_keys: wwe, wcw, ecw, aew, tna, njpw, "
            "ajpw, roh, noah."
        ),
        input_schema={
            "type": "object",
            "properties": {"promotion_key": {"type": "string"}},
            "required": ["promotion_key"],
        },
        handler=_t_ingest_ppv_list,
    ),
    "ingest_episode_list": AgentTool(
        name="ingest_episode_list",
        description=(
            "Bulk-ingest a TV show's episodes from its Wikipedia list article. "
            "Creates Event rows with event_type=tv_episode. Best coverage: "
            "AEW Dynamite. For Raw/SmackDown/Nitro/NXT, prefer the existing "
            "TMDB pipeline (poll_tv_episodes Celery task)."
        ),
        input_schema={
            "type": "object",
            "properties": {"show_key": {"type": "string"}},
            "required": ["show_key"],
        },
        handler=_t_ingest_episode_list,
    ),
    "discover_notable_venues": AgentTool(
        name="discover_notable_venues",
        description="Discover notable venue candidates from Wikipedia categories.",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20}},
        },
        handler=_t_discover_notable_venues,
    ),
    "discover_top_mentions": AgentTool(
        name="discover_top_mentions",
        description=(
            "Return the most-mentioned but unresolved entities in the graph "
            "(things other entities reference but we don't have DB rows for)."
        ),
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 30}},
        },
        handler=_t_discover_top_mentions,
    ),
    "auto_discover_mentions": AgentTool(
        name="auto_discover_mentions",
        description=(
            "Pick up to N top unresolved mentions and run the full fetch+classify "
            "pipeline on them. Grows the graph organically."
        ),
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}},
        },
        handler=_t_auto_discover_mentions,
    ),
    "generate_bio": AgentTool(
        name="generate_bio",
        description=(
            "Generate and verify an encyclopedic bio for a wrestler. Uses the "
            "3-pass self-correcting pipeline (standard → strict → trim). Only "
            "verified bios are saved."
        ),
        input_schema={
            "type": "object",
            "properties": {"wrestler_id": {"type": "integer"}},
            "required": ["wrestler_id"],
        },
        handler=_t_generate_bio,
    ),
    "find_incomplete_wrestlers": AgentTool(
        name="find_incomplete_wrestlers",
        description=(
            "Rank wrestlers by how MUCH they're missing (bio, image, "
            "promotion-links, matches, birth date). Returns the top N most-"
            "incomplete entries so JR can focus on COMPLETION rather than "
            "ADDING new ones. Pair with re-fetching their Wikipedia page + "
            "extract_and_persist to fill gaps."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
        handler=_t_find_incomplete_wrestlers,
    ),
    "ingest_title_history": AgentTool(
        name="ingest_title_history",
        description=(
            "Discover wrestlers from a Wikipedia 'List of X Champions' "
            "article. Queues unknown champions for ingest via the standard "
            "fetch path — each gets a SourceFetch + FieldProvenance trail. "
            "Pass title_slug to target one title, omit for all. Valid slugs "
            "include: wwe_championship, wcw_world_heavyweight, "
            "aew_world, nwa_world_heavyweight, iwgp_heavyweight, "
            "wwe_intercontinental, wwe_womens, tna_world, ecw_world, "
            "roh_world, etc."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "title_slug": {"type": "string"},
                "max_unknown_to_queue": {
                    "type": "integer", "minimum": 1, "maximum": 50, "default": 15,
                },
            },
        },
        handler=_t_ingest_title_history,
    ),
    "crossvalidate_wikidata": AgentTool(
        name="crossvalidate_wikidata",
        description="Pull Wikidata facts for wrestlers and reconcile against stored values.",
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}},
        },
        handler=_t_crossvalidate_wikidata,
    ),
    "run_jr_cycle": AgentTool(
        name="run_jr_cycle",
        description=(
            "Escape hatch: run one full legacy JR cycle (discover → fetch → extract "
            "→ crossvalidate → bios → auto-discover). Use only when you want the "
            "default heuristic pipeline rather than a targeted action."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "discovery": {"type": "integer", "minimum": 0, "maximum": 50, "default": 5},
                "fetch": {"type": "integer", "minimum": 0, "maximum": 50, "default": 5},
                "extract": {"type": "integer", "minimum": 0, "maximum": 100, "default": 20},
                "crossvalidate": {"type": "integer", "minimum": 0, "maximum": 50, "default": 5},
                "bio": {"type": "integer", "minimum": 0, "maximum": 20, "default": 5},
                "auto_discover": {"type": "integer", "minimum": 0, "maximum": 20, "default": 5},
            },
        },
        handler=_t_run_jr_cycle,
    ),
}


EARL_ONLY_TOOLS: dict[str, AgentTool] = {
    "audit_all": AgentTool(
        name="audit_all",
        description=(
            "Run the consistency-check suite across every entity (wrestler, event, "
            "venue). Records EarlObservations. Idempotent — re-runs bump times_seen."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_t_audit_all,
    ),
    "apply_safe_fixes": AgentTool(
        name="apply_safe_fixes",
        description=(
            "For observations matching a known safe-to-auto-fix rule, apply the "
            "field cleanup pipeline. Marks the observation 'fixed'."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_t_apply_safe_fixes,
    ),
    "score_rules": AgentTool(
        name="score_rules",
        description="Recompute RuleScore.times_fired from recent observations.",
        input_schema={"type": "object", "properties": {}},
        handler=_t_score_rules,
    ),
    "detect_patterns": AgentTool(
        name="detect_patterns",
        description=(
            "Find systemic issues (a rule firing on many entities) and create "
            "RuleSuggestion rows describing the pattern."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_t_detect_patterns,
    ),
    "list_observations": AgentTool(
        name="list_observations",
        description="Query EarlObservation rows, optionally filtered by rule_id, severity, or status.",
        input_schema={
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                "status": {"type": "string",
                            "enum": ["open", "fixed", "dismissed", "false_positive"],
                            "default": "open"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
        handler=_t_list_observations,
    ),
    "list_suggestions": AgentTool(
        name="list_suggestions",
        description="List RuleSuggestion rows by status.",
        input_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string",
                            "enum": ["pending", "accepted", "rejected", "applied"],
                            "default": "pending"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            },
        },
        handler=_t_list_suggestions,
    ),
    "list_rule_scores": AgentTool(
        name="list_rule_scores",
        description="Show per-rule firing counts and precision scores.",
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
        },
        handler=_t_list_rule_scores,
    ),
    "update_observation": AgentTool(
        name="update_observation",
        description=(
            "Set an observation's status to fixed / dismissed / false_positive / open. "
            "Use 'false_positive' when investigation shows the rule misfired."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "observation_id": {"type": "integer"},
                "status": {"type": "string",
                            "enum": ["open", "fixed", "dismissed", "false_positive"]},
                "notes": {"type": "string"},
            },
            "required": ["observation_id", "status"],
        },
        handler=_t_update_observation,
    ),
    "inspect_provenance": AgentTool(
        name="inspect_provenance",
        description=(
            "Show FieldProvenance rows for an entity (optionally one field). "
            "Earl uses this to verify whether a flagged value is supported by its "
            "source snippet before deciding to fix or dismiss."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "integer"},
                "field_name": {"type": "string"},
            },
            "required": ["entity_type", "entity_id"],
        },
        handler=_t_inspect_provenance,
    ),
}


AL_ONLY_TOOLS: dict[str, AgentTool] = {
    "list_unresolved_mentions": AgentTool(
        name="list_unresolved_mentions",
        description=(
            "Top wiki-link mention targets that don't yet correspond to a DB "
            "entity. Optionally filter by source_entity_type (where the "
            "mention was found). Returns the link name, count, and up to 3 "
            "sample source entities that mention it — so you can decide whether "
            "the mention is worth ingesting."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "source_entity_type": {
                    "type": "string",
                    "enum": ["wrestler", "event", "venue", "promotion", "book",
                              "video_game", "podcast", "action_figure", "theme_song",
                              "title", "stable", "tv_show", "special"],
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 30},
            },
        },
        handler=_t_list_unresolved_mentions,
    ),
    "list_entities_with_unresolved_mentions": AgentTool(
        name="list_entities_with_unresolved_mentions",
        description=(
            "Find entities whose own prose references many unresolved targets. "
            "These are the highest-value sources of unpolished gems — closing "
            "their gaps grows the graph fastest."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {"type": "string", "default": "wrestler"},
                "min_count": {"type": "integer", "minimum": 1, "default": 3},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
        handler=_t_list_entities_with_unresolved_mentions,
    ),
    "mentions_for_entity": AgentTool(
        name="mentions_for_entity",
        description=(
            "List all mention rows belonging to one entity's source content. "
            "Useful for auditing an entity's references before ingesting them."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "integer"},
                "only_unresolved": {"type": "boolean", "default": False},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 50},
            },
            "required": ["entity_type", "entity_id"],
        },
        handler=_t_mentions_for_entity,
    ),
    "rescan_entity_for_mentions": AgentTool(
        name="rescan_entity_for_mentions",
        description=(
            "Re-extract mention rows from an entity's most recent stored "
            "Wikipedia fetch. Use after extractor improvements, or when you "
            "suspect mentions were missed."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "entity_type": {"type": "string"},
                "entity_id": {"type": "integer"},
            },
            "required": ["entity_type", "entity_id"],
        },
        handler=_t_rescan_entity_for_mentions,
    ),
    "resolve_all_mentions": AgentTool(
        name="resolve_all_mentions",
        description=(
            "Sweep over all unresolved mention rows and link those whose "
            "wiki_link matches an existing DB entity. Cheap and idempotent — "
            "call this whenever you've added entities and want to re-check "
            "the graph for newly-closeable gaps."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_t_resolve_all_mentions,
    ),
    "link_trainers_sweep": AgentTool(
        name="link_trainers_sweep",
        description=(
            "Close the trained-by graph. Returns names of trainers referenced "
            "by wrestlers but not yet in the DB — perfect candidates for "
            "wiki_fetch + extract_and_persist."
        ),
        input_schema={"type": "object", "properties": {}},
        handler=_t_link_trainers_sweep,
    ),
    "link_wrestler_promotions": AgentTool(
        name="link_wrestler_promotions",
        description=(
            "Scan one wrestler's stored Wikipedia content for promotion "
            "mentions (e.g. links to /wiki/WWE, /wiki/WCW, /wiki/AEW) and "
            "create WrestlerPromotionHistory rows for any promotions that "
            "appear at least twice as wiki-link targets. Conservative — "
            "single passing mentions don't create a link. Returns the "
            "promotions added + the hit-count map for inspection."
        ),
        input_schema={
            "type": "object",
            "properties": {"wrestler_id": {"type": "integer"}},
            "required": ["wrestler_id"],
        },
        handler=_t_link_wrestler_promotions,
    ),
    "link_all_unlinked_wrestlers": AgentTool(
        name="link_all_unlinked_wrestlers",
        description=(
            "Bulk: run promotion-link discovery for every wrestler with "
            "fewer than 2 existing promotion links AND a stored Wikipedia "
            "fetch. Idempotent — no duplicate rows. Great Al-cycle warmup."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
        handler=_t_link_all_unlinked_wrestlers,
    ),
    "wrestlers_due_for_review": AgentTool(
        name="wrestlers_due_for_review",
        description=(
            "Rotating-review queue. Returns wrestlers whose data hasn't "
            "been updated in `days_since_review` days, prioritising those "
            "missing bio / image / promotion-links. Use this to keep the "
            "living database fresh — Al rotates through everyone."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "days_since_review": {"type": "integer", "minimum": 1, "default": 14},
                "limit": {"type": "integer", "minimum": 1, "maximum": 200, "default": 20},
            },
        },
        handler=_t_wrestlers_due_for_review,
    ),
    "auto_discover_mentions": AgentTool(
        name="auto_discover_mentions",
        description=(
            "Pick the top N unresolved mentions and run the full fetch + "
            "classify pipeline on them. Use this after deciding (via "
            "list_unresolved_mentions) that the top candidates look real."
        ),
        input_schema={
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}},
        },
        handler=_t_auto_discover_mentions,
    ),
}


# Public assemblies used by the agent runners.

JR_TOOLS: dict[str, AgentTool] = {**SHARED_TOOLS, **JR_ONLY_TOOLS}
EARL_TOOLS: dict[str, AgentTool] = {**SHARED_TOOLS, **EARL_ONLY_TOOLS}
AL_TOOLS: dict[str, AgentTool] = {**SHARED_TOOLS, **AL_ONLY_TOOLS}


def build_anthropic_tools(tool_map: dict[str, AgentTool]) -> list[dict]:
    """Return the list shape Anthropic's `tools=` parameter expects."""
    return [t.to_anthropic() for t in tool_map.values()]


def dispatch(tool_map: dict[str, AgentTool], name: str, arguments: dict) -> dict:
    """Run one tool call; never raises — always returns a result dict."""
    tool = tool_map.get(name)
    if tool is None:
        return _err(f"unknown tool {name!r}")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return _err(f"tool {name!r} arguments must be a JSON object")
    try:
        return tool.handler(**arguments)
    except TypeError as e:
        return _err(f"tool {name!r} argument error: {e}")
    except Exception as e:
        logger.exception("tool %s failed", name)
        return _err(f"tool {name!r} raised {type(e).__name__}: {e}")


# Tools whose returns are stat-heavy (high-level counters plus optional
# per-row lists). The agent only needs the top-level counts to decide what
# to do next — the per-row noise accumulates across many calls and drowns
# productive context. Cap these aggressively so a 20-call bulk-ingest
# session stays well under the input-token budget.
STAT_ONLY_TOOLS = frozenset({
    "run_jr_cycle",
    "ingest_title_history",
    "ingest_episode_list",
    "ingest_ppv_list",
    "auto_discover_mentions",
    "resolve_all_mentions",
    "link_all_unlinked_wrestlers",
    "link_trainers_sweep",
})


def summarise_result(result: dict, max_chars: int = 2500,
                     tool_name: Optional[str] = None) -> str:
    """Pretty-print a result for AgentToolCall.result_summary (truncated JSON).

    For tools listed in STAT_ONLY_TOOLS, cap the summary at 200 chars — the
    agent needs the counts, not the per-row details, and those results
    repeat many times per bulk-ingest session.
    """
    if tool_name in STAT_ONLY_TOOLS:
        max_chars = 200
    try:
        s = json.dumps(result, default=str, indent=None)
    except Exception:
        s = str(result)
    if len(s) > max_chars:
        s = s[:max_chars] + f"… [+{len(s) - max_chars} chars]"
    return s
