"""
wb_earl — run one Earl (Earl Hebner) audit cycle.

Earl is the verification + self-improving auditor. He runs the consistency-
check suite, records observations, applies safe auto-fixes, scores rules
by firing rate / precision, and proposes rule improvements when systemic
issues emerge.

Use:
    python manage.py wb_earl                # full cycle (audit + auto-fix + score + suggest)
    python manage.py wb_earl --observations # just print top open observations
    python manage.py wb_earl --suggestions  # just print pending rule suggestions
"""

from __future__ import annotations

from dataclasses import asdict

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run one Earl audit cycle (verification + self-improving auditor)."

    def add_arguments(self, parser):
        parser.add_argument("--observations", action="store_true",
                            help="Just print top open observations and exit.")
        parser.add_argument("--suggestions", action="store_true",
                            help="Just print pending rule suggestions and exit.")
        parser.add_argument("--rules", action="store_true",
                            help="Just print the rule score table and exit.")

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.models import (
            EarlObservation, RuleScore, RuleSuggestion,
        )

        if options["observations"]:
            self._print_observations()
            return
        if options["suggestions"]:
            self._print_suggestions()
            return
        if options["rules"]:
            self._print_rules()
            return

        from owdb_django.wrestlebot.bots.earl import Earl
        earl = Earl()
        self.stdout.write(self.style.SUCCESS(f"\n=== {earl.name} ({earl.role}) ===\n"))
        stats = earl.cycle()
        self.stdout.write("\nResults:")
        for k, v in asdict(stats).items():
            self.stdout.write(f"  {k:<30} {v}")
        self.stdout.write("")
        self._print_observations(limit=10)
        self._print_suggestions(limit=10)

    def _print_observations(self, limit: int = 20):
        from owdb_django.wrestlebot.models import EarlObservation
        qs = EarlObservation.objects.filter(status="open").order_by(
            "-severity", "-times_seen",
        )[:limit]
        self.stdout.write(self.style.HTTP_INFO(
            f"\nTop {qs.count()} open observations:"
        ))
        for o in qs:
            color = self.style.ERROR if o.severity == "error" else self.style.WARNING
            self.stdout.write(color(
                f"  [{o.severity}] {o.rule_id:<25} {o.entity_type}#{o.entity_id} "
                f"({o.entity_name}): {o.issue_description[:80]}"
            ))

    def _print_suggestions(self, limit: int = 10):
        from owdb_django.wrestlebot.models import RuleSuggestion
        qs = RuleSuggestion.objects.filter(status="pending").order_by("-proposed_at")[:limit]
        if not qs.exists():
            return
        self.stdout.write(self.style.HTTP_INFO(
            f"\n{qs.count()} pending rule suggestions:"
        ))
        for s in qs:
            self.stdout.write(self.style.WARNING(
                f"  [#{s.id}] target={s.target_rule_id!r}: {s.description[:100]}"
            ))
            if s.rationale:
                for line in s.rationale.splitlines()[:3]:
                    self.stdout.write(f"        {line}")

    def _print_rules(self):
        from owdb_django.wrestlebot.models import RuleScore
        qs = RuleScore.objects.order_by("-times_fired")
        self.stdout.write(self.style.HTTP_INFO(
            f"\nRule scores ({qs.count()} rules):"
        ))
        for r in qs:
            enabled = "ENABLED" if r.enabled else "disabled"
            self.stdout.write(
                f"  {r.rule_id:<30} {r.kind:<12} fires={r.times_fired:<5} "
                f"precision={r.precision:.2f}  [{enabled}]"
            )
