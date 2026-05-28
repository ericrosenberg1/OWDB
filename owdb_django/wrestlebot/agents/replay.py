"""
Deterministic replay of a recorded agent session.

The audit log (`AgentSession` + `AgentToolCall`) captures every tool call
an agent made, in order, with its exact JSON arguments. That's enough to
re-execute the whole session against the *current* rules + data, which
is the missing 20% of "if Earl flags 100 entities as bad, replay the
exact JR session that created them against tightened rules."

Two modes:

  * `dry_run=True` (default) — wrap everything in a transaction that
    rolls back at the end, so the replay does not mutate the DB. You
    see every (tool, args, old_result, new_result) tuple, plus a
    summary of which calls now succeed/fail differently.

  * `dry_run=False` — actually re-run. Useful for re-applying a known-
    good session after a transient infra failure, or for backfilling
    entities after a contract rule was loosened. Use sparingly — the
    point of accuracy-first is that we usually trust the original run.

The replay does NOT call Claude — there's no model in the loop. We just
re-dispatch the recorded tool sequence. That makes replay fast (~1s/call
for cheap tools, no token cost) and deterministic.

Tools that touch external APIs (`brave_search`, `wiki_fetch`) WILL hit
the network on replay; if the upstream content changed, the new result
will diverge from the recorded one. That divergence is exactly what
Earl wants to see — Wikipedia edits since the original session.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class ReplayCallResult:
    """Outcome for one replayed tool call within a session."""
    sequence: int
    tool_name: str
    arguments: dict
    original_summary: str       # what the call returned in the original run
    original_error: str
    new_summary: str            # what the call returned now
    new_error: str
    diverged: bool              # True iff original vs new differ meaningfully
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            "sequence": self.sequence,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "diverged": self.diverged,
            "original_error": self.original_error,
            "new_error": self.new_error,
            "duration_ms": self.duration_ms,
            "original_summary_head": self.original_summary[:300],
            "new_summary_head": self.new_summary[:300],
        }


@dataclass
class ReplaySessionResult:
    """Outcome for one whole session replay."""
    session_id: int
    bot: str
    dry_run: bool
    total_calls: int
    new_errors: int               # calls that now error but didn't before
    fixed_errors: int             # calls that previously errored but now succeed
    diverged: int                 # any call where the result text changed
    calls: list[ReplayCallResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "bot": self.bot,
            "dry_run": self.dry_run,
            "total_calls": self.total_calls,
            "new_errors": self.new_errors,
            "fixed_errors": self.fixed_errors,
            "diverged": self.diverged,
            "calls": [c.to_dict() for c in self.calls],
        }


def _resolve_tool_map_for_bot(bot: str) -> dict:
    """Look up which tool registry to dispatch through based on the bot."""
    from .capabilities import CAPABILITIES, resolve_tool_set
    cap = CAPABILITIES.get(bot)
    if cap is None:
        raise ValueError(
            f"Unknown bot {bot!r}; valid: {sorted(CAPABILITIES)}"
        )
    return resolve_tool_set(cap.tool_set)


def _result_text_differs(original: str, new: str) -> bool:
    """
    Whether two result summaries are 'meaningfully different.'

    We compare on the JSON-parsed shape when possible (so whitespace /
    field-order changes don't count), falling back to string compare.
    Generated IDs and timestamps are stripped before comparison — they
    legitimately change between runs and aren't replay-relevant.
    """
    def _normalise(s: str):
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, TypeError):
            return s.strip()
        return _strip_volatile(parsed)
    return _normalise(original) != _normalise(new)


_VOLATILE_KEYS = {
    "id", "fetch_id", "session_id", "called_at", "fetched_at",
    "started_at", "finished_at", "last_verified", "last_enriched",
    "image_fetched_at", "created_at", "updated_at", "resolved_at",
}


def _strip_volatile(node):
    """Recursively drop fields whose values legitimately change between runs."""
    if isinstance(node, dict):
        return {
            k: _strip_volatile(v)
            for k, v in node.items()
            if k not in _VOLATILE_KEYS
        }
    if isinstance(node, list):
        return [_strip_volatile(x) for x in node]
    return node


def replay_session(
    session_id: int,
    *,
    dry_run: bool = True,
    skip_done: bool = True,
) -> ReplaySessionResult:
    """
    Re-dispatch every recorded tool call in `AgentSession#session_id`.

    Args:
        session_id: AgentSession PK to replay.
        dry_run: True wraps the replay in a transaction that rolls back
            at the end (no DB mutation). False actually re-applies.
        skip_done: True skips replaying the agent's terminal `done` call
            (it has no side effects but does add a row to your replay
            log). Set False if you want a strict 1:1 of the original.

    Returns a `ReplaySessionResult` summarising what changed.

    Caveats:
      * Network-touching tools (`wiki_fetch`, `brave_search`, ...) will
        hit the live upstream and may return different content. The
        divergence is real — surface it, don't hide it.
      * Tools that consume external IDs (e.g. fetch_id from a previous
        call) replay the EXACT recorded arguments; this means a replay
        may reference IDs that don't exist in a fresh DB. The replay
        does NOT rewrite IDs; if you need a fresh-DB run, regenerate
        the session via the live agent instead.
    """
    from ..models import AgentSession, AgentToolCall
    from .tools import dispatch, summarise_result

    session = AgentSession.objects.get(pk=session_id)
    tool_map = _resolve_tool_map_for_bot(session.bot)

    calls = list(
        AgentToolCall.objects
        .filter(session=session)
        .order_by("sequence")
    )

    result = ReplaySessionResult(
        session_id=session.id,
        bot=session.bot,
        dry_run=dry_run,
        total_calls=len(calls),
    )

    @transaction.atomic
    def _run_with_rollback():
        # `set_rollback(True)` at the end forces this atomic block to
        # roll back regardless of success — that's how we get dry_run
        # without polluting the DB.
        sid = transaction.savepoint()
        try:
            _run_calls()
        finally:
            transaction.savepoint_rollback(sid)

    def _run_calls():
        for call in calls:
            if skip_done and call.tool_name == "done":
                continue
            args = call.arguments if isinstance(call.arguments, dict) else {}
            t0 = time.time()
            try:
                live = dispatch(tool_map, call.tool_name, args)
                new_error = "" if live.get("ok", False) else live.get("error", "") or ""
            except Exception as e:
                logger.exception("replay: dispatch crashed on call #%s", call.sequence)
                live = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                new_error = live["error"]
            duration_ms = int((time.time() - t0) * 1000)
            new_summary = summarise_result(live, tool_name=call.tool_name)

            diverged = _result_text_differs(call.result_summary, new_summary)
            orig_had_error = bool(call.error)
            new_has_error = bool(new_error)
            if new_has_error and not orig_had_error:
                result.new_errors += 1
            if orig_had_error and not new_has_error:
                result.fixed_errors += 1
            if diverged:
                result.diverged += 1

            result.calls.append(ReplayCallResult(
                sequence=call.sequence,
                tool_name=call.tool_name,
                arguments=args,
                original_summary=call.result_summary or "",
                original_error=call.error or "",
                new_summary=new_summary,
                new_error=new_error,
                diverged=diverged,
                duration_ms=duration_ms,
            ))

    if dry_run:
        _run_with_rollback()
    else:
        _run_calls()

    logger.info(
        "Replay session #%s (%s): %d calls, %d diverged, %d new errors, "
        "%d fixed. dry_run=%s",
        session.id, session.bot, result.total_calls, result.diverged,
        result.new_errors, result.fixed_errors, dry_run,
    )

    # Annotate the source AgentSession (not in dry-run mode) so Earl's
    # audit can see which sessions have been replayed.
    if not dry_run:
        session.final_summary = (
            (session.final_summary or "")
            + f"\n\n[REPLAYED {timezone.now().isoformat()}: "
              f"{result.total_calls} calls, {result.diverged} diverged, "
              f"{result.new_errors} new errors, {result.fixed_errors} fixed]"
        )[:65_000]
        session.save(update_fields=["final_summary"])

    return result
