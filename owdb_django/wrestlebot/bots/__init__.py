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
"""
