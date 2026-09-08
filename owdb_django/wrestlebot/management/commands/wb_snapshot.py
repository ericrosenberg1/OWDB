"""
wb_snapshot — prints a one-screen accuracy/health snapshot.

Use between agent runs to verify the contract holds across cycles:

    python manage.py wb_snapshot          # full snapshot
    python manage.py wb_snapshot --tag baseline   # add a label

Reports:
    - Entity counts (Wrestler / Event / Match / Venue / Title / Stable / TVShow / Promotion)
    - verification_state distribution per entity type
    - FieldProvenance + snippet coverage
    - Open EarlObservation by rule
    - AgentSession totals (calls, tokens, cost)
    - The four critical regression-canaries: (verified_without_provenance,
      match_no_participants, ranking_entry_unresolved, candidates remaining)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from django.core.management.base import BaseCommand
from django.db.models import Count, Sum


class Command(BaseCommand):
    help = "Snapshot accuracy + agent + entity health in one block."

    def add_arguments(self, parser):
        parser.add_argument("--tag", type=str, default="",
                            help="Label this snapshot (printed at the top).")
        parser.add_argument("--json", action="store_true",
                            help="Emit machine-readable JSON instead of text.")

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import (
            Event, Match, MatchParticipant, Venue, Wrestler, Promotion,
            Title, Stable, TVShow, ExternalRankingEntry,
        )
        from owdb_django.wrestlebot.models import (
            FieldProvenance, SourceFetch, EarlObservation,
            AgentSession, AgentToolCall,
        )

        snapshot = {
            "tag": options["tag"] or "",
            "ts": datetime.now(timezone.utc).isoformat(),
            "entities": {
                "wrestler": Wrestler.objects.count(),
                "event": Event.objects.count(),
                "match": Match.objects.count(),
                "match_participant": MatchParticipant.objects.count(),
                "venue": Venue.objects.count(),
                "promotion": Promotion.objects.count(),
                "title": Title.objects.count(),
                "stable": Stable.objects.count(),
                "tv_show": TVShow.objects.count(),
                "external_ranking_entry": ExternalRankingEntry.objects.count(),
            },
            "verification_state": {},
            "provenance": {
                "total_rows": FieldProvenance.objects.count(),
                "with_snippet": FieldProvenance.objects.exclude(snippet="").count(),
                "synthetic_backfill": FieldProvenance.objects.filter(confidence__lt=100).count(),
                "by_entity_type": {},
            },
            "source_fetches": SourceFetch.objects.count(),
            "earl_observations": {
                "open": EarlObservation.objects.filter(status="open").count(),
                "by_rule": [],
            },
            "agents": {
                "sessions_total": AgentSession.objects.count(),
                "calls_total": AgentToolCall.objects.count(),
                "input_tokens_total": AgentSession.objects.aggregate(
                    s=Sum("input_tokens_used"))["s"] or 0,
                "output_tokens_total": AgentSession.objects.aggregate(
                    s=Sum("output_tokens_used"))["s"] or 0,
                "by_bot": [],
            },
            "regression_canaries": {},
        }

        for entity_type in ("event", "match", "venue", "wrestler",
                            "promotion", "title", "stable", "tv_show"):
            model = {
                "event": Event, "match": Match, "venue": Venue,
                "wrestler": Wrestler, "promotion": Promotion,
                "title": Title, "stable": Stable, "tv_show": TVShow,
            }[entity_type]
            by_state = list(
                model.objects.values("verification_state").annotate(n=Count("id"))
                .order_by("verification_state")
            )
            snapshot["verification_state"][entity_type] = {
                row["verification_state"]: row["n"] for row in by_state
            }
            snapshot["provenance"]["by_entity_type"][entity_type] = (
                FieldProvenance.objects.filter(entity_type=entity_type).count()
            )

        snapshot["earl_observations"]["by_rule"] = list(
            EarlObservation.objects.filter(status="open")
            .values("rule_id", "severity")
            .annotate(n=Count("id")).order_by("-n")[:15]
        )

        for bot in ("jr", "earl", "al"):
            agg = AgentSession.objects.filter(bot=bot).aggregate(
                n=Count("id"),
                input_t=Sum("input_tokens_used"),
                output_t=Sum("output_tokens_used"),
                calls=Sum("tool_calls_used"),
            )
            snapshot["agents"]["by_bot"].append({
                "bot": bot,
                "sessions": agg["n"] or 0,
                "calls": agg["calls"] or 0,
                "input_tokens": agg["input_t"] or 0,
                "output_tokens": agg["output_t"] or 0,
            })

        # Regression canaries — these MUST stay healthy across runs.
        snapshot["regression_canaries"]["verified_without_provenance"] = (
            EarlObservation.objects.filter(
                status="open", rule_id="verified_without_provenance",
            ).count()
        )
        snapshot["regression_canaries"]["match_no_participants"] = (
            EarlObservation.objects.filter(
                status="open", rule_id="match_no_participants",
            ).count()
        )
        snapshot["regression_canaries"]["ranking_entry_unresolved"] = (
            EarlObservation.objects.filter(
                status="open", rule_id="ranking_entry_unresolved",
            ).count()
        )
        snapshot["regression_canaries"]["events_in_candidate_state"] = (
            Event.objects.filter(verification_state="candidate").count()
        )
        snapshot["regression_canaries"]["matches_in_candidate_state"] = (
            Match.objects.filter(verification_state="candidate").count()
        )

        if options["json"]:
            self.stdout.write(json.dumps(snapshot, indent=2, default=str))
            return

        # Pretty text output.
        tag_str = f"[{snapshot['tag']}] " if snapshot["tag"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"\n=== {tag_str}OWDB snapshot @ {snapshot['ts']} ===\n"
        ))

        self.stdout.write(self.style.HTTP_INFO("Entities:"))
        for k, v in snapshot["entities"].items():
            self.stdout.write(f"  {k:<28} {v:>6}")

        self.stdout.write(self.style.HTTP_INFO("\nverification_state distribution:"))
        for et, dist in snapshot["verification_state"].items():
            if not dist:
                continue
            tail = "  ".join(f"{s}={n}" for s, n in dist.items())
            self.stdout.write(f"  {et:<18} {tail}")

        self.stdout.write(self.style.HTTP_INFO("\nProvenance:"))
        self.stdout.write(f"  total rows                  {snapshot['provenance']['total_rows']}")
        self.stdout.write(f"  with snippet                {snapshot['provenance']['with_snippet']}")
        self.stdout.write(f"  synthetic back-fill         {snapshot['provenance']['synthetic_backfill']}")
        self.stdout.write(f"  source fetches              {snapshot['source_fetches']}")

        self.stdout.write(self.style.HTTP_INFO("\nOpen Earl observations:"))
        if not snapshot["earl_observations"]["by_rule"]:
            self.stdout.write("  (none)")
        for r in snapshot["earl_observations"]["by_rule"]:
            sev = r["severity"]
            color = self.style.ERROR if sev == "error" else self.style.WARNING
            self.stdout.write(color(
                f"  {sev:<8} {r['rule_id']:<35} {r['n']}"
            ))

        self.stdout.write(self.style.HTTP_INFO("\nAgents:"))
        for row in snapshot["agents"]["by_bot"]:
            cost = (row["input_tokens"] * 3 + row["output_tokens"] * 15) / 1_000_000
            self.stdout.write(
                f"  {row['bot']:<6} sessions={row['sessions']:<3} calls={row['calls']:<4} "
                f"tokens=in:{row['input_tokens']:>6} out:{row['output_tokens']:>5} "
                f"≈${cost:.3f}"
            )

        self.stdout.write(self.style.HTTP_INFO("\nRegression canaries (lower is better):"))
        for k, v in snapshot["regression_canaries"].items():
            symbol = "✓" if v == 0 else ("·" if v < 50 else "!")
            self.stdout.write(f"  {symbol} {k:<35} {v}")

        self.stdout.write("")
