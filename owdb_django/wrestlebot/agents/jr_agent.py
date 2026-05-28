"""
JR — the data-adding agent.

Thin wrapper around `agents.runner.run_agent` that resolves JR's persona
+ tools + model from the shared `agents.capabilities` registry. The
entire system prompt, mission, motto, model selection, and default task
live in ONE place (`capabilities.py:JR`). Edit it there.

The old version of this file kept ~130 lines of system prompt inline —
which inevitably drifted from its Al/Earl siblings whenever the
universal accuracy rules changed. The new pattern keeps the agent
modules at ~30 lines so drift is impossible.
"""

from __future__ import annotations

import logging
from typing import Optional

from .capabilities import JR, assemble_system_prompt, resolve_tool_set
from .runner import AgentRunResult, run_agent

logger = logging.getLogger(__name__)


# Re-exported for back-compat: callers that imported JR_MODEL / JR_SYSTEM_PROMPT
# from this module historically still work.
JR_MODEL = JR.model
JR_SYSTEM_PROMPT = assemble_system_prompt(JR)


def run_jr(
    task: Optional[str] = None,
    *,
    max_tool_calls: int = 40,
    max_input_tokens: int = 200_000,
    max_iterations: int = 60,
    model: Optional[str] = None,
) -> AgentRunResult:
    """
    Run one JR agent session.

    `task` is the goal statement seeded into the first user message.
    If None, the registry's default task is used.
    """
    return run_agent(
        bot=JR.bot_key,
        task=task or JR.default_task,
        tools=resolve_tool_set(JR.tool_set),
        system_prompt=JR_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
        max_input_tokens=max_input_tokens,
        max_iterations=max_iterations,
        model=model or JR_MODEL,
    )
