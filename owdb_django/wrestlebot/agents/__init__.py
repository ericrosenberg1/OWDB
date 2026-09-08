"""
WrestleBot agents — JR and Earl as Anthropic tool-use agents.

JR (data-adding) and Earl (verification + self-improving auditor) both run
as Claude agents that decide which pipeline operation to invoke next. The
pipeline modules contain the actual accuracy guards; the agents are a
strategic decision layer on top.

Layout:
    tools.py        — registry of tool definitions (Anthropic schemas + Python handlers)
    runner.py       — generic agent loop with budget caps and session logging
    jr_agent.py     — JR-specific system prompt + tool palette
    earl_agent.py   — Earl-specific system prompt + tool palette
"""
