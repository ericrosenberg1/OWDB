"""
JR (Jim Ross) — the data-adding bot.

JR is responsible for getting wrestling information INTO the database. He
runs the full ingest pipeline in priority order and respects every
accuracy guard already wired into the pipeline modules.

JR does NOT modify rules, does NOT decide whether existing data is correct,
and does NOT silently overwrite anything. Those responsibilities belong to
Earl (`wrestlebot.bots.earl`).

Entry points:
    JR.cycle()                 — one full ingest pass
    JR.fetch(names, type)      — type-specific manual fetch
    JR.discover(type, limit)   — discover candidates without fetching

JR's stages, in order:
    1. Discover missing-trainer candidates (close the trained-by graph)
    2. Discover notable-wrestler candidates from Wikipedia categories
    3. Fetch raw source content for unfetched candidates
    4. Extract + persist any unprocessed fetches (auto-classified by type)
    5. Cross-validate against Wikidata where possible
    6. Generate + verify bios (self-correcting 3-pass)
    7. Run mention-driven auto-discovery to grow the graph organically

JR returns a stats dict from every public method so Earl can score rule
performance.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class JRCycleStats:
    """One JR cycle's outcome — used by Earl to grade rule effectiveness."""
    discovered: int = 0
    fetched: int = 0
    extracted: int = 0
    crossvalidated: int = 0
    bios_attempted: int = 0
    bios_verified: int = 0
    bios_rejected: int = 0
    bios_permanently_rejected: int = 0
    auto_discovered: int = 0
    auto_discovery_skipped_generic: int = 0
    auto_discovery_skipped_unclassified: int = 0
    skipped_redirect_to_existing: int = 0
    skipped_redirect_to_different_subject: int = 0
    refused_by_classifier: int = 0
    refused_by_subject_gate: int = 0


class JR:
    """
    Good Ol' JR — the data-adding bot, named for Jim Ross.

    Jim Ross is the encyclopedic voice of professional wrestling: 35+ years
    of calling matches, an Oklahoma drawl that knows every wrestler, every
    territory, every story. The real JR's instinct is to remember and
    contextualise everything in pro wrestling history.

    OWDB's JR has the same instinct, in code form: he is on a mission to
    assemble the most comprehensive wrestling database ever built. Every
    cycle he runs, the graph grows — more wrestlers, more events, more
    titles — and every entry that's already there gets more complete.

    Mission: "Build the most comprehensive wrestling database ever assembled."
    """

    name = "Good Ol' JR"
    full_name = "Good Ol' JR (Jim Ross)"
    role = "data-adding bot"
    mission = "Build the most comprehensive wrestling database ever assembled."
    motto = "Business is about to pick up."

    def __init__(self):
        self._stats = JRCycleStats()

    # ------------------------------------------------------------- discovery

    def discover_missing_trainers(self) -> list[str]:
        """Names of trainers referenced by existing wrestlers but absent from DB."""
        from ..pipeline.linking import link_trainers_sweep
        result = link_trainers_sweep()
        return result.get("missing_names", []) or []

    def discover_notable_wrestlers(self, limit: int = 20) -> list[str]:
        from ..pipeline.discovery import discover_wrestlers
        return discover_wrestlers(per_category_limit=3, total_limit=limit)

    def discover_top_unresolved_mentions(self, limit: int = 30) -> list[tuple[str, int]]:
        from ..pipeline.auto_discovery import top_unresolved_mentions
        return top_unresolved_mentions(limit=limit)

    # ----------------------------------------------------------------- fetch

    def fetch(
        self,
        names: Iterable[str],
        entity_type: str = "wrestler",
        force: bool = False,
    ) -> list:
        """Fetch source content for a list of candidate names."""
        from ..pipeline import fetch as fetch_mod
        method = {
            "wrestler": fetch_mod.fetch_wrestler_candidates,
            "event": fetch_mod.fetch_event_candidates,
            "venue": fetch_mod.fetch_venue_candidates,
            "promotion": fetch_mod.fetch_promotion_candidates,
            "book": fetch_mod.fetch_book_candidates,
            "video_game": fetch_mod.fetch_video_game_candidates,
            "podcast": fetch_mod.fetch_podcast_candidates,
            "action_figure": fetch_mod.fetch_action_figure_candidates,
            "theme_song": fetch_mod.fetch_theme_song_candidates,
            "title": fetch_mod.fetch_title_candidates,
            "stable": fetch_mod.fetch_stable_candidates,
            "tv_show": fetch_mod.fetch_tv_show_candidates,
            "special": fetch_mod.fetch_special_candidates,
        }.get(entity_type)
        if method is None:
            raise ValueError(f"JR doesn't know how to fetch entity_type={entity_type!r}")
        return method(list(names), force=force)

    # ------------------------------------------------------- one full cycle

    def cycle(
        self,
        discovery_limit: int = 5,
        fetch_limit: int = 5,
        extract_limit: int = 20,
        crossvalidate_limit: int = 5,
        bio_limit: int = 5,
        auto_discover_limit: int = 5,
    ) -> JRCycleStats:
        """
        Run one full JR cycle: discover -> fetch -> extract -> crossvalidate
        -> bio gen -> auto-discover via mentions.

        Each stage is bounded so a single cycle finishes in 30s-3min.
        Stats are returned for Earl to grade rule effectiveness.
        """
        stats = self._stats = JRCycleStats()

        try:
            if discovery_limit > 0 and fetch_limit > 0:
                stats.discovered = self._stage_discover_and_fetch(
                    discovery_limit, fetch_limit,
                )
            if extract_limit > 0:
                stats.extracted = self._stage_extract(extract_limit)
            if crossvalidate_limit > 0:
                stats.crossvalidated = self._stage_crossvalidate(crossvalidate_limit)
            if bio_limit > 0:
                bio_stats = self._stage_bios(bio_limit)
                for k, v in bio_stats.items():
                    setattr(stats, k, v)
            if auto_discover_limit > 0:
                auto_stats = self._stage_auto_discover(auto_discover_limit)
                for k, v in auto_stats.items():
                    setattr(stats, k, v)
        except Exception as e:
            logger.exception("JR.cycle failed: %s", e)
            raise

        logger.info("JR cycle done: %s", asdict(stats))
        return stats

    # ------------------------------------------------------- internal stages

    def _stage_discover_and_fetch(self, disc_limit: int, fetch_limit: int) -> int:
        from ..models import SourceFetch
        fetched = set(
            SourceFetch.objects.filter(source="wikipedia")
            .values_list("candidate_name", flat=True)
        )
        out: list[str] = []
        # Priority 1: missing trainers
        for name in self.discover_missing_trainers():
            if name in fetched or name in out:
                continue
            out.append(name)
            if len(out) >= disc_limit:
                break
        # Priority 2: notable wrestlers
        if len(out) < disc_limit:
            for c in self.discover_notable_wrestlers(disc_limit * 5):
                if c in fetched or c in out:
                    continue
                out.append(c)
                if len(out) >= disc_limit:
                    break

        # Fetch the candidates we found
        to_fetch = out[:fetch_limit]
        if not to_fetch:
            return 0
        self.fetch(to_fetch, entity_type="wrestler")
        return len(to_fetch)

    def _stage_extract(self, limit: int) -> int:
        """Process unhandled SourceFetch rows across all entity types."""
        from ..models import SourceFetch
        pending = SourceFetch.objects.filter(
            http_status=200, used_at__isnull=True,
        ).order_by("fetched_at")[:limit]
        count = 0
        for fetch in pending:
            if self._extract_and_persist_one(fetch):
                count += 1
        return count

    def _extract_and_persist_one(self, fetch) -> bool:
        from django.utils import timezone
        from ..pipeline import extract as extract_mod
        from ..pipeline import persist as persist_mod
        from ..pipeline import persist_event as persist_event_mod
        from ..pipeline import persist_media as persist_media_mod
        from ..pipeline import persist_title as persist_title_mod
        from ..pipeline import persist_show as persist_show_mod

        etype = fetch.entity_type or "wrestler"
        extractor = {
            "wrestler": extract_mod.extract_wrestler,
            "event": extract_mod.extract_event,
            "venue": extract_mod.extract_venue,
            "promotion": extract_mod.extract_promotion,
            "book": extract_mod.extract_book,
            "video_game": extract_mod.extract_video_game,
            "podcast": extract_mod.extract_podcast,
            "action_figure": extract_mod.extract_action_figure,
            "theme_song": extract_mod.extract_theme_song,
            "title": extract_mod.extract_title,
            "stable": extract_mod.extract_stable,
            "tv_show": extract_mod.extract_tv_show,
            "special": extract_mod.extract_special,
        }.get(etype)
        persister = {
            "wrestler": persist_mod.persist_wrestler,
            "event": persist_event_mod.persist_event,
            "venue": persist_event_mod.persist_venue,
            "promotion": persist_event_mod.persist_promotion,
            "book": persist_media_mod.persist_book,
            "video_game": persist_media_mod.persist_video_game,
            "podcast": persist_media_mod.persist_podcast,
            "action_figure": persist_media_mod.persist_action_figure,
            "theme_song": persist_media_mod.persist_theme_song,
            "title": persist_title_mod.persist_title,
            "stable": persist_title_mod.persist_stable,
            "training_school": persist_title_mod.persist_training_school,
            "tv_show": persist_show_mod.persist_tv_show,
            "special": persist_show_mod.persist_special,
        }.get(etype)

        outcome = "succeeded"
        success = False
        try:
            if extractor is None or persister is None:
                outcome = "no_handler"
            else:
                fields = extractor(fetch)
                if fields is None:
                    outcome = "no_fields"
                else:
                    result = persister(fetch.candidate_name, fields, fetch)
                    if result is None:
                        outcome = "persist_refused"
                    else:
                        success = True
        finally:
            # Always stamp used_at + outcome so failing fetches don't recycle
            # through the `used_at__isnull=True` queue on every cycle.
            fetch.used_at = timezone.now()
            fetch.extraction_outcome = outcome
            fetch.save(update_fields=["used_at", "extraction_outcome"])
        return success

    def _stage_crossvalidate(self, limit: int) -> int:
        """Pull Wikidata for wrestlers without a Wikidata source fetch yet."""
        try:
            # Optional path — Wikidata module may not be present in all builds.
            from .. import tasks
            return tasks._stage_crossvalidate(limit)  # type: ignore[attr-defined]
        except Exception as e:
            logger.debug("JR cross-validation step unavailable: %s", e)
            return 0

    def _stage_bios(self, limit: int) -> dict:
        from owdb_django.owdbapp.models import Wrestler
        from ..claude_client import ClaudeClient
        from ..models import GeneratedBio
        from ..pipeline.bio import generate_and_verify_with_retry

        client = ClaudeClient()
        if not client.available:
            logger.info("JR bio stage skipped: no Claude credentials")
            return {
                "bios_attempted": 0, "bios_verified": 0,
                "bios_rejected": 0, "bios_permanently_rejected": 0,
            }

        handled = set(
            GeneratedBio.objects
            .filter(entity_type="wrestler",
                    status__in=["verified", "permanently_rejected"])
            .values_list("entity_id", flat=True)
        )
        targets = (
            Wrestler.objects.exclude(id__in=handled).order_by("id")[:limit]
        )
        attempted = verified = rejected = permanent = 0
        for w in targets:
            attempted += 1
            bio = generate_and_verify_with_retry(w, client=client)
            if bio is None:
                continue
            if bio.status == "verified":
                verified += 1
                w.about = bio.text
                w.save(update_fields=["about", "updated_at"])
            elif bio.status == "permanently_rejected":
                permanent += 1
            else:
                rejected += 1
        return {
            "bios_attempted": attempted,
            "bios_verified": verified,
            "bios_rejected": rejected,
            "bios_permanently_rejected": permanent,
        }

    def _stage_auto_discover(self, limit: int) -> dict:
        from ..pipeline.auto_discovery import auto_discover_step
        stats = auto_discover_step(limit=limit)
        return {
            "auto_discovered": stats.fetched,
            "auto_discovery_skipped_generic": stats.skipped_generic,
            "auto_discovery_skipped_unclassified": stats.skipped_unclassified,
        }


# Convenience singleton for callers that don't need explicit state.
default = JR()
