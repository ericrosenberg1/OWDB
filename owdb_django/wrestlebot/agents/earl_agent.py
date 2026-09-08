"""
Earl — the verification + self-improving auditor agent.

Thin wrapper around `agents.runner.run_agent` that reads Earl's persona,
tools, model, and default task from `agents.capabilities.EARL`. See
`capabilities.py` for the source of truth — edit Earl's behaviour there,
not here.
"""

from __future__ import annotations

import logging
from typing import Optional

from .capabilities import EARL, assemble_system_prompt, resolve_tool_set
from .runner import AgentRunResult, run_agent

logger = logging.getLogger(__name__)


EARL_MODEL = EARL.model
EARL_SYSTEM_PROMPT = assemble_system_prompt(EARL)


def run_earl(
    task: Optional[str] = None,
    *,
    max_tool_calls: int = 40,
    max_input_tokens: int = 200_000,
    max_iterations: int = 60,
    model: Optional[str] = None,
) -> AgentRunResult:
    """Run one Earl agent session."""
    return run_agent(
        bot=EARL.bot_key,
        task=task or EARL.default_task,
        tools=resolve_tool_set(EARL.tool_set),
        system_prompt=EARL_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
        max_input_tokens=max_input_tokens,
        max_iterations=max_iterations,
        model=model or EARL_MODEL,
    )
