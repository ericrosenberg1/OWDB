"""
Generic agent loop for JR and Earl.

Both agents share the same loop structure:
    1. Send conversation to Claude with the available tools.
    2. Loop over each content block in the response:
        - text → captured into the running narrative
        - tool_use → dispatch to the tool registry, then append a
                     tool_result block to the next user turn
    3. Stop when the model:
        - returns stop_reason == "end_turn" (no further tool calls), OR
        - calls the `done` tool, OR
        - hits a budget cap (tool calls, input tokens), OR
        - errors irrecoverably.
    4. Persist every step to AgentSession + AgentToolCall for replay/audit.

The runner does NOT inspect tool results to make decisions — that's the
agent's job. The runner just transports the call/response round-trips
and enforces budgets.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Optional

from django.utils import timezone

from ..claude_client import ClaudeClient
from .tools import AgentTool, build_anthropic_tools, dispatch, summarise_result

logger = logging.getLogger(__name__)


def _compact_tool_result_content(content) -> str:
    """Shrink a single tool_result content blob to a short placeholder.

    Preserves top-level scalar fields (ok/count/* numeric stats) so the agent
    still sees what happened — just without the per-row lists that dominate
    context after many calls.
    """
    if isinstance(content, list):
        # Anthropic SDK sometimes models content as [{"type":"text","text":...}]
        text = "".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    elif isinstance(content, str):
        text = content
    else:
        text = str(content)

    if len(text) <= 120:
        return text  # already short — nothing useful to gain by rewriting

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        snippet = text[:100].replace("\n", " ")
        return f"<truncated: {snippet}…>"

    if isinstance(data, dict):
        scalars = {
            k: v
            for k, v in data.items()
            if isinstance(v, bool)
            or isinstance(v, (int, float))
            or (isinstance(v, str) and len(v) < 40)
        }
        if scalars:
            return f"<truncated: {json.dumps(scalars)[:200]}>"

    snippet = text[:100].replace("\n", " ")
    return f"<truncated: {snippet}…>"


def _compact_old_tool_results(conversation: list[dict], keep_last_n: int = 3) -> int:
    """In-place: keep the most recent `keep_last_n` tool_result blocks at full
    fidelity; replace earlier ones with short scalar-only placeholders.

    tool_use_id is preserved on every placeholder so the assistant/tool_use ↔
    user/tool_result pairing the API requires stays valid.

    Returns the number of tool_results that were compacted (for logging).
    """
    seen = 0
    compacted = 0
    for msg in reversed(conversation):
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            seen += 1
            if seen <= keep_last_n:
                continue
            orig = block.get("content")
            placeholder = _compact_tool_result_content(orig)
            if placeholder != orig:
                block["content"] = placeholder
                compacted += 1
    return compacted


@dataclass
class AgentRunResult:
    session_id: int
    outcome: str
    final_summary: str
    tool_calls_used: int
    input_tokens_used: int
    output_tokens_used: int


def run_agent(
    *,
    bot: str,  # "jr" or "earl"
    task: str,  # the goal for this run
    tools: dict[str, AgentTool],  # JR_TOOLS or EARL_TOOLS
    system_prompt: str,
    max_tool_calls: int = 50,
    max_input_tokens: int = 200_000,
    max_iterations: int = 60,
    model: Optional[str] = None,
    client: Optional[ClaudeClient] = None,
) -> AgentRunResult:
    """
    Run one agent session to completion.

    Always returns an AgentRunResult and always closes out the AgentSession
    row with an outcome — even on errors.
    """
    from ..models import AgentSession, AgentToolCall

    if client is None:
        client = ClaudeClient(model=model) if model else ClaudeClient()

    session = AgentSession.objects.create(
        bot=bot,
        task=task,
        model=client.model,
        max_tool_calls=max_tool_calls,
        max_input_tokens=max_input_tokens,
        outcome="running",
    )
    logger.info("Agent session #%d started: bot=%s task=%r", session.id, bot, task[:80])

    if not client.available:
        session.outcome = "error"
        session.final_summary = "No Claude credentials available; agent cannot run."
        session.finished_at = timezone.now()
        session.save()
        return AgentRunResult(
            session_id=session.id,
            outcome="error",
            final_summary=session.final_summary,
            tool_calls_used=0,
            input_tokens_used=0,
            output_tokens_used=0,
        )

    anthropic_tools = build_anthropic_tools(tools)
    conversation: list[dict] = [{"role": "user", "content": task}]

    sequence = 0
    final_summary = ""
    outcome = "completed"

    # All iteration work is wrapped in try/finally so that a crash (network
    # blip, tool dispatch bug, SDK exception) always closes the AgentSession
    # row. Without this guarantee, sessions stay outcome='running' forever
    # and Earl's audit thinks they're still in flight.
    try:
        for iteration in range(max_iterations):
            # Budget checks before each model turn.
            if session.tool_calls_used >= max_tool_calls:
                outcome = "budget_exceeded"
                final_summary = f"Hit tool-call cap ({max_tool_calls})."
                break
            if session.input_tokens_used >= max_input_tokens:
                outcome = "budget_exceeded"
                final_summary = f"Hit input-token cap ({max_input_tokens})."
                break

            # Compact older tool results so a long session doesn't blow
            # past the input-token budget. The 3 most recent results stay
            # full-fidelity; everything earlier collapses to a short
            # placeholder that preserves only scalar counters. The
            # AgentToolCall.result_summary rows already persisted to the DB
            # keep the full audit trail — this only trims what we re-send.
            _compact_old_tool_results(conversation, keep_last_n=3)

            resp = client.create_message(
                system=system_prompt,
                messages=conversation,
                tools=anthropic_tools,
                max_tokens=4096,
                temperature=0.2,
            )
            if resp is None:
                outcome = "error"
                final_summary = "create_message returned None (API failure)"
                break

            # Update token usage.
            usage = getattr(resp, "usage", None)
            if usage is not None:
                session.input_tokens_used += int(getattr(usage, "input_tokens", 0) or 0)
                session.output_tokens_used += int(getattr(usage, "output_tokens", 0) or 0)

            # Collect any text content into final_summary (last text block wins).
            tool_uses: list = []
            any_text = ""
            for block in resp.content:
                btype = getattr(block, "type", None)
                if btype == "text":
                    any_text = block.text or any_text
                elif btype == "tool_use":
                    tool_uses.append(block)

            # Persist the assistant turn into the conversation.
            # Anthropic SDK message objects serialise via .model_dump() (pydantic v2).
            try:
                assistant_content = [b.model_dump(exclude_unset=False) for b in resp.content]
            except Exception:
                # Fallback for older SDKs that return dicts already.
                assistant_content = list(resp.content)
            conversation.append({"role": "assistant", "content": assistant_content})

            stop_reason = getattr(resp, "stop_reason", None)

            # If there were no tool_use blocks, the model is finished.
            if not tool_uses:
                if any_text:
                    final_summary = any_text
                outcome = "completed"
                break

            # Run each tool call, capture results, and prepare next user turn.
            next_user_blocks: list[dict] = []
            for tu in tool_uses:
                sequence += 1
                tool_name = getattr(tu, "name", "") or ""
                tool_input = getattr(tu, "input", {}) or {}
                tool_use_id = getattr(tu, "id", "") or ""

                t0 = time.time()
                try:
                    result = dispatch(tools, tool_name, tool_input)
                    # Default to False so an opaque dict (missing "ok") is
                    # treated as an error, matching the is_error flag below.
                    error_text = "" if result.get("ok", False) else result.get("error", "")
                except Exception as e:  # paranoia — dispatch already wraps
                    logger.exception("Unhandled tool dispatch error")
                    result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                    error_text = result["error"]
                duration_ms = int((time.time() - t0) * 1000)

                result_text = summarise_result(result, tool_name=tool_name)

                # Persist tool call.
                AgentToolCall.objects.create(
                    session=session,
                    sequence=sequence,
                    tool_name=tool_name,
                    arguments=tool_input if isinstance(tool_input, dict) else {},
                    result_summary=result_text,
                    error=error_text,
                    duration_ms=duration_ms,
                )
                session.tool_calls_used = sequence

                next_user_blocks.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result_text,
                        # Match the error_text branch above: opaque dicts (no
                        # "ok" key) count as errors so the model sees them as
                        # such on the next turn.
                        "is_error": not result.get("ok", False),
                    }
                )

                if tool_name == "done":
                    final_summary = result.get("summary") or any_text or final_summary
                    outcome = "completed"

            # Save updated counters between iterations.
            session.save(
                update_fields=[
                    "tool_calls_used",
                    "input_tokens_used",
                    "output_tokens_used",
                ]
            )

            # If `done` was called, exit BEFORE sending another model turn.
            if outcome == "completed" and any(
                getattr(tu, "name", "") == "done" for tu in tool_uses
            ):
                break

            conversation.append({"role": "user", "content": next_user_blocks})

            # Honor explicit non-tool stop_reasons.
            if stop_reason and stop_reason not in ("tool_use", None):
                # The SDK gave us a definitive stop reason but also tool_use; loop
                # already ran them, so we're done unless the model wants to keep
                # talking next round. Continue iterating.
                pass
        else:
            outcome = "budget_exceeded"
            final_summary = f"Hit iteration cap ({max_iterations})."
    except Exception as e:
        # A crashed run still needs a finished session row. We log the
        # stack but do NOT re-raise — the AgentRunResult below is what
        # callers (the management commands) inspect for failure.
        logger.exception("Agent session #%d crashed", session.id)
        outcome = "error"
        final_summary = (
            f"Crash: {type(e).__name__}: {e}\n"
            f"(See logs for full traceback; session #{session.id} closed.)"
        )

    session.outcome = outcome
    session.final_summary = final_summary or session.final_summary
    session.finished_at = timezone.now()
    session.save()

    logger.info(
        "Agent session #%d finished: outcome=%s calls=%d tokens=in:%d out:%d",
        session.id,
        outcome,
        session.tool_calls_used,
        session.input_tokens_used,
        session.output_tokens_used,
    )

    return AgentRunResult(
        session_id=session.id,
        outcome=outcome,
        final_summary=session.final_summary,
        tool_calls_used=session.tool_calls_used,
        input_tokens_used=session.input_tokens_used,
        output_tokens_used=session.output_tokens_used,
    )
