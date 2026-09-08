"""
WrestleBot v3 — two named bots, two responsibilities.

JR (Jim Ross) — the ANNOUNCER. Brings the data in. JR's job is to scan
external sources (Wikipedia, Wikidata, eventually Cagematch), extract
structured facts, run them through accuracy guards, and persist verified
entities to the database. JR never silently overwrites; never invents;
defers to source.

Earl (Earl Hebner) — the REFEREE. Watches what JR did and rules on it.
Earl's job is to audit existing entries, score rule-level accuracy over
time, and propose (or apply) improvements to JR's extractors, classifier,
and consistency rules. Earl is the self-improving feedback loop.

Both bots share the same pipeline modules (discovery, fetch, extract,
persist, mention-resolution, bio generation). The bots are entry-points
that compose those modules with the right policies for their role:

  - JR composes: discover -> fetch -> extract -> persist -> bio
  - Earl composes: audit -> measure-rules -> suggest/apply rule deltas

Two different implementations answer to these same names, and it matters
which one you're reading. `wrestlebot/agents/jr_agent.py`, `al_agent.py`,
and `earl_agent.py` are genuine Claude tool-use agents with enforced
per-cycle budget caps — these are what Celery beat actually schedules for
autonomous operation, as `jr_agent_cycle` / `al_agent_cycle` /
`earl_agent_cycle` in `wrestlebot/tasks.py`. JR and Earl in *this* module
(reachable via the `wb_jr` / `wb_earl` management commands) are a
separate, deterministic pipeline with no tool-use loop and no budget cap
— not part of the autonomous beat schedule, kept on purpose for cheap,
high-volume bulk processing. One caveat: JR's optional bio-writing stage
still makes narrow, single-shot calls to Claude (via
`claude_client.ClaudeClient`, not the agent framework) to draft a
wrestler bio, and no-ops cleanly when no credentials are configured — so
"deterministic" describes this pipeline's control flow, not a strict
zero-LLM-calls guarantee for every stage.
"""
