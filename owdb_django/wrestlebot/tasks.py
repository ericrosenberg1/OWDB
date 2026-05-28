"""
Celery tasks for autonomous WrestleBot v3 operation.

The main entry point is `wrestlebot_cycle` — runs the full pipeline
incrementally. Each cycle does small amounts of work in each stage:

    1. Discover ≤N new candidate names from Wikipedia categories
    2. Fetch any unfetched candidates (rate-limited by the scraper)
    3. Extract + persist any unprocessed fetches
    4. Generate + verify bios for wrestlers that don't have one
    5. Retry-with-corrections for any rejected bios

Each stage is bounded by a small batch size so a single cycle finishes in
~30s-3min depending on stage activity. Beat schedule runs this every 10
minutes (see settings.py).

All operations are idempotent — re-running the cycle picks up where the
last one left off without duplicating work.
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# Per-cycle batch sizes. Conservative defaults; can be raised once we've
# validated against rate limits and 429 risk in production.
DISCOVERY_BATCH = 5
FETCH_BATCH = 5
EXTRACT_BATCH = 20
CROSSVALIDATE_BATCH = 5  # Wikidata calls are cheap; do a handful per cycle
BIO_BATCH = 5  # Sonnet 4.6 calls cost real money + quota; cap tight


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=10 * 60,
    time_limit=12 * 60,
)
def wrestlebot_cycle(self, batch_size_override: dict = None):
    """
    One full pipeline cycle. Returns a stats dict.

    `batch_size_override` lets you tune for a single invocation, e.g.
    `{"bio_batch": 0}` to skip the LLM step on a heavy-load cycle.
    """
    overrides = batch_size_override or {}
    discovery_n = overrides.get("discovery", DISCOVERY_BATCH)
    fetch_n = overrides.get("fetch", FETCH_BATCH)
    extract_n = overrides.get("extract", EXTRACT_BATCH)
    bio_n = overrides.get("bio", BIO_BATCH)

    stats: dict = {
        "discovered": 0,
        "fetched": 0,
        "extracted": 0,
        "wikidata_crossvalidated": 0,
        "bios_attempted": 0,
        "bios_verified": 0,
        "bios_rejected": 0,
        "bios_permanently_rejected": 0,
        "promotions_linked": 0,
    }

    crossval_n = overrides.get("crossvalidate", CROSSVALIDATE_BATCH)

    try:
        if discovery_n > 0:
            stats["discovered"] = _stage_discover(discovery_n)
        if fetch_n > 0:
            stats["fetched"] = _stage_fetch(fetch_n)
        if extract_n > 0:
            stats["extracted"] = _stage_extract(extract_n)
        if crossval_n > 0:
            stats["wikidata_crossvalidated"] = _stage_crossvalidate(crossval_n)
        if bio_n > 0:
            bio_stats = _stage_generate_bios(bio_n)
            stats.update(bio_stats)
    except Exception as e:
        logger.exception("wrestlebot_cycle failed: %s", e)
        raise self.retry(exc=e)

    logger.info("wrestlebot_cycle complete: %s", stats)
    return stats


# ---------------------------------------------------------------------------
# Stage helpers — each is a thin wrapper that returns a count.
# ---------------------------------------------------------------------------


def _stage_discover(limit: int) -> int:
    """
    Find new candidate names that aren't already in SourceFetch.

    Priority order, until we've reached `limit`:
      1. Trainers named by existing wrestlers but not yet in the DB
         (closes the trained-by graph — every trainer becomes a wrestler).
      2. Notability-weighted discovery (HOF / champion categories first).
    """
    from .models import SourceFetch
    from .pipeline.discovery import discover_wrestlers
    from .pipeline.linking import link_trainers_sweep

    known_fetched = set(
        SourceFetch.objects.filter(source="wikipedia").values_list("candidate_name", flat=True)
    )

    out: list[str] = []

    # Priority 1: missing trainers
    sweep = link_trainers_sweep()
    for name in sweep.get("missing_names", []):
        if name in known_fetched or name in out:
            continue
        out.append(name)
        if len(out) >= limit:
            return len(out)

    # Priority 2: notability-weighted category discovery
    candidates = discover_wrestlers(per_category_limit=3, total_limit=limit * 5)
    for c in candidates:
        if c in known_fetched or c in out:
            continue
        out.append(c)
        if len(out) >= limit:
            break

    return len(out)


def _prioritized_candidates(limit: int) -> list[str]:
    """
    Build a candidate list in priority order:
      1. Missing trainers referenced by existing wrestlers
      2. Notability-weighted Wikipedia categories
      3. (Future: wikilink mentions that aren't yet entities)
    Already-fetched candidates are excluded.
    """
    from .models import SourceFetch
    from .pipeline.discovery import discover_wrestlers
    from .pipeline.linking import link_trainers_sweep

    fetched = set(
        SourceFetch.objects.filter(source="wikipedia").values_list("candidate_name", flat=True)
    )
    out: list[str] = []

    # Trainers first
    sweep = link_trainers_sweep()
    for name in sweep.get("missing_names", []):
        if name in fetched or name in out:
            continue
        out.append(name)
        if len(out) >= limit:
            return out

    # Notable wrestlers next
    for c in discover_wrestlers(per_category_limit=3, total_limit=limit * 5):
        if c in fetched or c in out:
            continue
        out.append(c)
        if len(out) >= limit:
            break

    return out


def _stage_fetch(limit: int) -> int:
    """Fetch the next batch of prioritised candidate wrestlers."""
    from .pipeline.fetch import fetch_wrestler_candidates

    to_fetch = _prioritized_candidates(limit)
    if not to_fetch:
        return 0
    fetches = fetch_wrestler_candidates(to_fetch)
    return len(fetches)


def _stage_extract(limit: int) -> int:
    """Extract + persist any SourceFetch rows that haven't been used yet."""
    from .models import SourceFetch
    from .pipeline.extract import extract_wrestler
    from .pipeline.persist import persist_wrestler

    pending = SourceFetch.objects.filter(
        entity_type="wrestler",
        http_status=200,
        used_at__isnull=True,
    ).order_by("fetched_at")[:limit]

    count = 0
    for fetch in pending:
        fields = extract_wrestler(fetch)
        if fields is None:
            continue
        result = persist_wrestler(fetch.candidate_name, fields, fetch)
        if result is not None:
            count += 1
    return count


def _stage_crossvalidate(limit: int) -> int:
    """
    Fetch Wikidata for wrestlers that don't yet have a wikidata SourceFetch,
    extract typed fields, persist for cross-source reconcile.
    """
    import hashlib
    from owdb_django.owdbapp.models import Wrestler
    from .models import SourceFetch
    from .pipeline.extract import extract_wrestler
    from .pipeline.persist import persist_wrestler
    from .sources.wikidata import WikidataAdapter, resolve_qid_for_wikipedia_title

    # Wrestlers with Wikipedia source but no Wikidata source yet.
    already_xv = set(
        SourceFetch.objects.filter(source="wikidata", http_status=200).values_list(
            "entity_id", flat=True
        )
    )
    candidates = (
        Wrestler.objects.exclude(wikipedia_url="")
        .exclude(wikipedia_url__isnull=True)
        .exclude(id__in=already_xv)
        .order_by("id")[:limit]
    )

    adapter = WikidataAdapter()
    done = 0
    for w in candidates:
        qid = resolve_qid_for_wikipedia_title(w.name)
        if not qid:
            continue
        result = adapter.fetch_wrestler_by_qid(qid)
        if result is None:
            continue
        fetch = SourceFetch.objects.create(
            source="wikidata",
            url=result.url,
            entity_type="wrestler",
            entity_id=w.id,
            candidate_name=w.name,
            http_status=result.http_status,
            content_hash=hashlib.sha256(result.raw_content.encode("utf-8")).hexdigest(),
            raw_content=result.raw_content,
        )
        fields = extract_wrestler(fetch)
        if fields is not None:
            persist_wrestler(w.name, fields, fetch)
        done += 1
    return done


def _stage_generate_bios(limit: int) -> dict:
    """
    Generate + verify bios for wrestlers without a verified bio yet. Uses
    the self-correcting `generate_and_verify_with_retry` path.
    """
    from owdb_django.owdbapp.models import Wrestler
    from .claude_client import ClaudeClient
    from .models import GeneratedBio
    from .pipeline.bio import generate_and_verify_with_retry

    client = ClaudeClient()
    if not client.available:
        logger.info("wrestlebot_cycle bio stage skipped: no Claude credentials")
        return {
            "bios_attempted": 0,
            "bios_verified": 0,
            "bios_rejected": 0,
            "bios_permanently_rejected": 0,
        }

    # Wrestlers already verified or permanently rejected — skip.
    handled_ids = set(
        GeneratedBio.objects.filter(
            entity_type="wrestler", status__in=["verified", "permanently_rejected"]
        ).values_list("entity_id", flat=True)
    )

    targets = Wrestler.objects.exclude(id__in=handled_ids).order_by("id")[:limit]

    attempted = 0
    verified = 0
    rejected = 0
    permanently_rejected = 0
    for w in targets:
        attempted += 1
        bio = generate_and_verify_with_retry(w, client=client)
        if bio is None:
            continue
        if bio.status == "verified":
            verified += 1
            # Promote to Wrestler.about
            try:
                w.about = bio.text
                w.save(update_fields=["about", "updated_at"])
            except Exception as e:
                logger.warning("Failed to promote bio#%d to Wrestler#%d.about: %s", bio.id, w.id, e)
        elif bio.status == "permanently_rejected":
            permanently_rejected += 1
        else:
            rejected += 1

    return {
        "bios_attempted": attempted,
        "bios_verified": verified,
        "bios_rejected": rejected,
        "bios_permanently_rejected": permanently_rejected,
    }


# ---------------------------------------------------------------------------
# Agent tasks — JR and Earl as autonomous Claude tool-use agents.
# ---------------------------------------------------------------------------


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    soft_time_limit=20 * 60,
    time_limit=25 * 60,
)
def jr_agent_cycle(self, max_tool_calls: int = 30):
    """
    Run one JR agent session. Defaults to a modest budget so an unattended
    schedule stays predictable.
    """
    from .agents.jr_agent import run_jr

    try:
        result = run_jr(max_tool_calls=max_tool_calls)
    except Exception as e:
        logger.exception("jr_agent_cycle failed: %s", e)
        raise self.retry(exc=e)
    return {
        "session_id": result.session_id,
        "outcome": result.outcome,
        "tool_calls_used": result.tool_calls_used,
        "input_tokens_used": result.input_tokens_used,
        "output_tokens_used": result.output_tokens_used,
        "final_summary": result.final_summary[:500],
    }


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    soft_time_limit=20 * 60,
    time_limit=25 * 60,
)
def al_agent_cycle(self, max_tool_calls: int = 30):
    """
    Run one Al agent session. Al closes graph gaps — links unresolved
    mentions to existing entities, ingests top unresolved references,
    and surfaces unpolished gems.
    """
    from .agents.al_agent import run_al

    try:
        result = run_al(max_tool_calls=max_tool_calls)
    except Exception as e:
        logger.exception("al_agent_cycle failed: %s", e)
        raise self.retry(exc=e)
    return {
        "session_id": result.session_id,
        "outcome": result.outcome,
        "tool_calls_used": result.tool_calls_used,
        "input_tokens_used": result.input_tokens_used,
        "output_tokens_used": result.output_tokens_used,
        "final_summary": result.final_summary[:500],
    }


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    soft_time_limit=20 * 60,
    time_limit=25 * 60,
)
def earl_agent_cycle(self, max_tool_calls: int = 30):
    """
    Run one Earl agent session. Cheaper than JR (Earl does no LLM bio gen),
    but still bounded.
    """
    from .agents.earl_agent import run_earl

    try:
        result = run_earl(max_tool_calls=max_tool_calls)
    except Exception as e:
        logger.exception("earl_agent_cycle failed: %s", e)
        raise self.retry(exc=e)
    return {
        "session_id": result.session_id,
        "outcome": result.outcome,
        "tool_calls_used": result.tool_calls_used,
        "input_tokens_used": result.input_tokens_used,
        "output_tokens_used": result.output_tokens_used,
        "final_summary": result.final_summary[:500],
    }
