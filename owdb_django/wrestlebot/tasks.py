"""
Celery tasks for autonomous WrestleBot v3 operation.

Live tasks (all three are wired into settings.CELERY_BEAT_SCHEDULE, but
only actually run when a Celery worker + beat process are up — see
docker-compose.nuc.yml, which zeroes the `celery` service's replicas in
production, so today these only fire via a manual `python manage.py
wb_*_agent` invocation):

    - jr_agent_cycle    — one Good Ol' JR agent session (data-adding)
    - al_agent_cycle    — one Al Snow agent session (interlinking)
    - earl_agent_cycle  — one Earl Hebner agent session (accuracy audit)

`_stage_crossvalidate` is a plain helper (no @shared_task — it isn't a
Celery entry point on its own), kept here because `bots/jr.py::JR`
reuses it for the non-agent `wb_jr` cycle's Wikidata cross-validation
stage.

The original entry point here, `wrestlebot_cycle` (a single task running
discover -> fetch -> extract -> persist -> generate -> verify end to end),
was retired 2026-05 in favor of Good Ol' JR owning that whole job with the
accuracy-contract gate the legacy path lacked (see the now-removed
`CELERY_BEAT_SCHEDULE["wrestlebot-cycle"]` entry, commented out in
settings.py). It and its five now-unreachable stage helpers
(`_stage_discover`, `_prioritized_candidates`, `_stage_fetch`,
`_stage_extract`, `_stage_generate_bios`) were deleted here since nothing
called them (confirmed: zero `.delay()`/`.apply_async()` references
anywhere in the repo, and the only schedule entry pointing at
`wrestlebot_cycle` was already commented out).
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# How much bigger a pool to pull from Wrestler.get_incomplete_profiles()
# than the final candidate count we need. That classmethod's priority
# ordering already puts "has wikipedia_url but missing key fields" first,
# but its lower-priority buckets include wrestlers with NO wikipedia_url
# at all (which we can't resolve a Wikidata QID for) — so we can't just
# slice the first `limit` rows and use them directly. Pulling a wider pool
# and filtering in Python keeps this to one query instead of duplicating
# get_incomplete_profiles()'s Case/When priority logic here.
_CROSSVALIDATE_POOL_MULTIPLIER = 20
_CROSSVALIDATE_POOL_MIN = 100


def _crossvalidate_candidates(limit: int) -> list:
    """
    Select which wrestlers JR should spend this cycle's Wikidata budget on.

    Delegates to `Wrestler.get_incomplete_profiles()` for prioritization
    (Wikipedia URL but missing key fields ranked first, recently-enriched
    wrestlers skipped — see owdbapp/models.py), then narrows to wrestlers
    that actually have a Wikipedia URL (required to resolve a Wikidata
    QID) and haven't already been cross-validated. Extracted from
    `_stage_crossvalidate` so the selection order is unit-testable without
    mocking network calls.
    """
    from owdb_django.owdbapp.models import Wrestler
    from .models import SourceFetch

    if limit <= 0:
        return []

    # Wrestlers with a Wikidata source already fetched.
    already_xv = set(
        SourceFetch.objects.filter(source="wikidata", http_status=200).values_list(
            "entity_id", flat=True
        )
    )
    pool_size = max(limit * _CROSSVALIDATE_POOL_MULTIPLIER, _CROSSVALIDATE_POOL_MIN)
    pool = Wrestler.get_incomplete_profiles(limit=pool_size)

    out = []
    for w in pool:
        if not w.wikipedia_url:
            continue
        if w.id in already_xv:
            continue
        out.append(w)
        if len(out) >= limit:
            break
    return out


def _stage_crossvalidate(limit: int) -> int:
    """
    Fetch Wikidata for wrestlers that don't yet have a wikidata SourceFetch,
    extract typed fields, persist for cross-source reconcile.

    Candidates come from `_crossvalidate_candidates()`, which prioritizes
    incomplete profiles (via `Wrestler.get_incomplete_profiles()`) instead
    of plain creation order, so this scarce, rate-limited Wikidata budget
    goes to the wrestlers most worth enriching first.
    """
    import hashlib
    from .models import SourceFetch
    from .pipeline.extract import extract_wrestler
    from .pipeline.persist import persist_wrestler
    from .sources.wikidata import WikidataAdapter, resolve_qid_for_wikipedia_title

    candidates = _crossvalidate_candidates(limit)

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
