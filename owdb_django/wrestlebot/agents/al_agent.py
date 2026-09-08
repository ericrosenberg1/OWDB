"""
Al — the interlinking + graph-gap-closing agent.

Thin wrapper around `agents.runner.run_agent` that reads Al's persona,
tools, model, and default task from `agents.capabilities.AL`. See
`capabilities.py` for the source of truth — edit Al's behaviour there,
not here.
"""

from __future__ import annotations

import logging
from typing import Optional

from .capabilities import AL, assemble_system_prompt, resolve_tool_set
from .runner import AgentRunResult, run_agent

logger = logging.getLogger(__name__)


AL_MODEL = AL.model
AL_SYSTEM_PROMPT = assemble_system_prompt(AL)


def run_al(
    task: Optional[str] = None,
    *,
    max_tool_calls: int = 40,
    max_input_tokens: int = 200_000,
    max_iterations: int = 60,
    model: Optional[str] = None,
) -> AgentRunResult:
    """Run one Al agent session."""
    return run_agent(
        bot=AL.bot_key,
        task=task or AL.default_task,
        tools=resolve_tool_set(AL.tool_set),
        system_prompt=AL_SYSTEM_PROMPT,
        max_tool_calls=max_tool_calls,
        max_input_tokens=max_input_tokens,
        max_iterations=max_iterations,
        model=model or AL_MODEL,
    )
