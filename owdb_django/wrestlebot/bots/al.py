"""
Al (Al Snow) — the interlinking bot.

Al's job is finding "unpolished gems" in the data and closing graph gaps.
Where JR adds wholly new entities and Earl audits existing ones, Al
specialises in connecting what's already there:

  - Mentions referenced in existing prose but not yet ingested
  - Trainers named by wrestlers but not yet wrestler entities
  - Venues mentioned in event prose but not yet venue entities
  - Mention rows that *could* resolve to existing entities but haven't been
    relinked since either side changed

Al never invents data — he uses the same fetch + classify + persist
pipeline JR uses, so every entity Al ingests has full FieldProvenance.
The accuracy guarantee is preserved.

Entry points:
    Al.cycle()                    — one full interlinking pass
    Al.discover_gaps(limit)       — preview top opportunities
    Al.close_trainer_gap()        — sweep trained-by graph
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


@dataclass
class AlCycleStats:
    mentions_resolved: int = 0
    trainer_gaps_found: int = 0
    trainer_gaps_closed: int = 0
    auto_discovered: int = 0
    auto_discovery_skipped_generic: int = 0
    auto_discovery_skipped_unclassified: int = 0


class Al:
    """
    Al Snow — the interlinking + graph-improvement bot.

    Al Snow is one of the most respected trainers in professional
    wrestling: years running Ohio Valley Wrestling's developmental
    school, a mentor on "Tough Enough," and a coach who built up
    dozens of WWE/Impact talents. His real-life job is making
    wrestlers better — finding their gaps, refining their craft,
    showing them connections they hadn't seen.

    OWDB's Al Snow does the same for the database: finds entries
    that aren't quite there yet, links them to where they belong,
    discovers new entities through the gaps that other entities
    reference, and rotates through the existing roster to keep it
    fresh. He doesn't add raw new entities the way JR does — he
    polishes what's there and connects what should already be
    connected.

    Mission: "Make every entry better. Surface every connection."
    """

    name = "Al Snow"
    full_name = "Al Snow"
    role = "interlinking + graph improvement"
    mission = "Make every entry better. Surface every connection."
    motto = "What does everybody want? Better data."

    def discover_gaps(self, limit: int = 30):
        """Top unresolved mention names (preview)."""
        from ..pipeline.auto_discovery import top_unresolved_mentions
        return top_unresolved_mentions(limit=limit)

    def close_trainer_gap(self) -> dict:
        """Sweep wrestlers, surface and link trainer references."""
        from ..pipeline.linking import link_trainers_sweep
        return link_trainers_sweep()

    def cycle(self, ingest_limit: int = 5) -> AlCycleStats:
        """
        One non-LLM Al pass:
          1. Resolve any newly-linkable mentions across all entity types.
          2. Close the trainer-gap graph.
          3. Pick the top N unresolved mentions and run the ingest pipeline.

        This is the deterministic equivalent of what `run_al` does as an agent.
        Useful as a fallback when no Claude credentials are available.
        """
        from ..pipeline.auto_discovery import auto_discover_step
        from ..pipeline.linking import link_trainers_sweep, resolve_all_mentions

        stats = AlCycleStats()

        # 1. Relink mentions to any newly-existing entities.
        resolved = resolve_all_mentions() or {}
        stats.mentions_resolved = sum(v for v in resolved.values() if isinstance(v, int))

        # 2. Trainer-gap sweep.
        trainer_sweep = link_trainers_sweep()
        stats.trainer_gaps_found = len(trainer_sweep.get("missing_names", []))
        stats.trainer_gaps_closed = trainer_sweep.get("linked", 0)

        # 3. Mention-driven ingest.
        if ingest_limit > 0:
            ad = auto_discover_step(limit=ingest_limit)
            stats.auto_discovered = ad.fetched
            stats.auto_discovery_skipped_generic = ad.skipped_generic
            stats.auto_discovery_skipped_unclassified = ad.skipped_unclassified

        logger.info("Al cycle done: %s", asdict(stats))
        return stats


default = Al()
