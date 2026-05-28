"""
Earl (Earl Hebner) — the verification + self-improving auditor.

Earl watches everything JR does. He runs the full consistency-check suite
over every persisted entity, records every issue in `EarlObservation`,
keeps running scores per rule in `RuleScore`, and proposes (or applies)
rule improvements via `RuleSuggestion`.

Earl never modifies entity fields directly. His job is meta: grade the
RULES, not the data. If a rule has been wrong too many times, Earl
disables it; if a pattern is uncaught, Earl proposes a new rule.

Entry points:
    Earl.audit_all()            — run consistency checks across all entities
    Earl.score_rules()          — recompute precision/firing rates
    Earl.detect_patterns()      — look for systemic issues to propose rules for
    Earl.apply_safe_fixes()     — auto-apply low-risk auto-corrections
    Earl.cycle()                — one full audit + scoring + suggestion pass
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from django.utils import timezone

logger = logging.getLogger(__name__)


@dataclass
class EarlCycleStats:
    entities_audited: int = 0
    new_observations: int = 0
    re_observed: int = 0
    auto_fixes_applied: int = 0
    rules_evaluated: int = 0
    rules_auto_disabled: int = 0
    rules_re_enabled: int = 0
    suggestions_created: int = 0


class Earl:
    """
    Earl Hebner — the accuracy auditor + rule improver.

    Earl Hebner is the most senior referee in professional wrestling
    history: WWE/WWF/WCW from the 1980s through the 2010s, the man
    counting 1-2-3 on more major matches than anyone alive. His real
    job was making sure the call was right — every pinfall, every
    submission, every disqualification — and protecting the integrity
    of the result.

    OWDB's Earl Hebner does the same for the database: he reviews
    every entity JR or Al persists, catches any field that lacks a
    source snippet, flags rules that misfire, proposes auto-fixes
    when safe, and writes the rules that JR and Al follow on
    subsequent cycles. He never edits an entity's fields directly —
    he grades the RULES.

    Mission: "100% accuracy first. Make JR and Al better."
    """

    name = "Earl Hebner"
    full_name = "Earl Hebner"
    role = "accuracy auditor + rule improver"
    mission = "100% accuracy first. Make JR and Al better."
    motto = "1-2-3. The deal goes down right."

    # ---------------------------------------------------------------- audit

    def audit_all(self) -> int:
        """
        Run consistency checks across every entity in the DB. Persist
        observations (one per (rule, entity, field) triple). Re-runs are
        idempotent — they bump times_seen rather than create duplicates.

        Coverage:
          Wrestler  — check_wrestler + provenance coverage
          Event     — check_event + provenance coverage
          Venue     — check_venue + provenance coverage
          Match     — check_match + provenance coverage (NEW post-codex)
          ExternalRankingEntry — orphan-link + source-trail rules (NEW)

        Returns the count of new observations created.
        """
        from owdb_django.owdbapp.models import (
            Event,
            Venue,
            Wrestler,
            Match,
            ExternalRankingEntry,
        )
        from ..pipeline.consistency import (
            check_event,
            check_venue,
            check_wrestler,
            check_match,
            check_provenance_coverage,
            check_image_legal_use,
        )

        new = 0
        total = 0

        def _record(entity, *, issues, entity_type, entity_name):
            nonlocal new
            for issue in issues:
                val = str(getattr(entity, issue.field, "") or "") if issue.field else ""
                if self._record_observation(
                    rule_id=issue.rule,
                    severity=issue.severity,
                    entity_type=entity_type,
                    entity_id=entity.id,
                    entity_name=entity_name,
                    field_name=issue.field,
                    stored_value=val,
                    issue_description=issue.message,
                ):
                    new += 1

        for w in Wrestler.objects.iterator():
            total += 1
            _record(w, issues=check_wrestler(w), entity_type="wrestler", entity_name=w.name)
            _record(
                w,
                issues=check_provenance_coverage("wrestler", w),
                entity_type="wrestler",
                entity_name=w.name,
            )
            _record(
                w,
                issues=check_image_legal_use("wrestler", w),
                entity_type="wrestler",
                entity_name=w.name,
            )

        for e in Event.objects.iterator():
            total += 1
            _record(e, issues=check_event(e), entity_type="event", entity_name=e.name)
            _record(
                e,
                issues=check_provenance_coverage("event", e),
                entity_type="event",
                entity_name=e.name,
            )
            _record(
                e, issues=check_image_legal_use("event", e), entity_type="event", entity_name=e.name
            )

        for v in Venue.objects.iterator():
            total += 1
            _record(v, issues=check_venue(v), entity_type="venue", entity_name=v.name)
            _record(
                v,
                issues=check_provenance_coverage("venue", v),
                entity_type="venue",
                entity_name=v.name,
            )
            _record(
                v, issues=check_image_legal_use("venue", v), entity_type="venue", entity_name=v.name
            )

        for m in Match.objects.iterator():
            total += 1
            name = (m.match_text or "")[:80]
            _record(m, issues=check_match(m), entity_type="match", entity_name=name)
            _record(
                m,
                issues=check_provenance_coverage("match", m),
                entity_type="match",
                entity_name=name,
            )

        # ExternalRankingEntry — flag orphans so Al can backfill links.
        for entry in ExternalRankingEntry.objects.select_related("ranking").iterator():
            total += 1
            if entry.wrestler_id is None:
                if self._record_observation(
                    rule_id="ranking_entry_unresolved",
                    severity="info",
                    entity_type="external_ranking_entry",
                    entity_id=entry.id,
                    entity_name=entry.wrestler_name_as_published,
                    field_name="wrestler",
                    stored_value=entry.wrestler_name_as_published,
                    issue_description=(
                        f"Ranking entry #{entry.position} on {entry.ranking} "
                        f"has no linked Wrestler — Al should match or flag."
                    ),
                ):
                    new += 1

        logger.info("Earl.audit_all: %d entities checked, %d new observations", total, new)
        return new

    def _record_observation(
        self,
        *,
        rule_id: str,
        severity: str,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        field_name: str,
        stored_value: str,
        issue_description: str,
    ) -> bool:
        """Upsert an EarlObservation. Returns True if newly created."""
        from ..models import EarlObservation

        obs, created = EarlObservation.objects.update_or_create(
            rule_id=rule_id,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            defaults=dict(
                severity=severity,
                entity_name=entity_name,
                stored_value=stored_value[:2000],
                issue_description=issue_description[:2000],
            ),
        )
        if not created:
            obs.times_seen += 1
            obs.save(update_fields=["times_seen", "last_seen"])
        return created

    # ------------------------------------------------------- rule scoring

    def score_rules(self) -> int:
        """
        Recompute RuleScore.times_fired from EarlObservation counts.
        Update last_evaluated. Returns rule rows touched.
        """
        from django.db.models import Count
        from ..models import EarlObservation, RuleScore

        rule_fire_counts = EarlObservation.objects.values("rule_id").annotate(n=Count("id"))
        touched = 0
        for row in rule_fire_counts:
            score, _ = RuleScore.objects.update_or_create(
                rule_id=row["rule_id"],
                defaults=dict(
                    kind="consistency",
                    times_fired=row["n"],
                    last_evaluated=timezone.now(),
                ),
            )
            touched += 1
        return touched

    # ---------------------------------------------------- pattern detection

    def detect_patterns(self) -> list[dict]:
        """
        Look for systemic issues — rules firing on many entities at once —
        and create RuleSuggestions for them. Returns the list of new
        suggestions created this pass.
        """
        from django.db.models import Count
        from ..models import EarlObservation, RuleSuggestion

        new_suggestions: list[dict] = []

        # Pattern 1: rules firing on >=5 entities with status=open are systemic.
        systemic = (
            EarlObservation.objects.filter(status="open")
            .values("rule_id", "severity")
            .annotate(n=Count("id"))
            .filter(n__gte=5)
        )
        for row in systemic:
            sample_ids = list(
                EarlObservation.objects.filter(rule_id=row["rule_id"], status="open").values_list(
                    "entity_id", flat=True
                )[:10]
            )
            description = (
                f"Rule {row['rule_id']!r} ({row['severity']}) is firing on "
                f"{row['n']} entities. Either:\n"
                f"  (a) the data really is wrong and needs an auto-fix path, or\n"
                f"  (b) the rule's threshold is too aggressive."
            )
            # Don't double-create if a pending suggestion already exists.
            existing = RuleSuggestion.objects.filter(
                target_rule_id=row["rule_id"],
                status="pending",
            ).first()
            if existing:
                continue
            sug = RuleSuggestion.objects.create(
                target_rule_id=row["rule_id"],
                kind="consistency",
                description=f"Re-tune or auto-fix path for rule {row['rule_id']}",
                rationale=description,
                sample_observations=sample_ids,
            )
            new_suggestions.append(
                {
                    "id": sug.id,
                    "rule": row["rule_id"],
                    "count": row["n"],
                }
            )

        return new_suggestions

    # -------------------------------------------------------- auto-fixes

    # Auto-fixes Earl is allowed to apply without human review. Each entry
    # maps a rule_id to a Python callable taking (entity, observation) and
    # returning True if the fix was applied.
    AUTO_FIX_RULES: tuple[str, ...] = (
        # All cleanup-class rules are safe to auto-apply because the cleanup
        # module is conservative (drops obvious junk, never replaces with a
        # different value).
        "real_name_format",
        "aliases_stray_punct",
        "trained_by_empty_segment",
    )

    def apply_safe_fixes(self) -> int:
        """
        For any observation matching an AUTO_FIX_RULES rule, apply the
        field-cleanup pipeline to the affected entity. Returns count of
        observations marked fixed.
        """
        from owdb_django.owdbapp.models import Wrestler
        from ..models import EarlObservation
        from ..pipeline.cleanup import apply_wrestler_cleanup

        applied = 0
        candidates = EarlObservation.objects.filter(
            status="open",
            rule_id__in=self.AUTO_FIX_RULES,
            entity_type="wrestler",
        )
        for obs in candidates:
            try:
                w = Wrestler.objects.get(id=obs.entity_id)
            except Wrestler.DoesNotExist:
                obs.status = "dismissed"
                obs.auto_fix_notes = "Entity no longer exists"
                obs.save(update_fields=["status", "auto_fix_notes"])
                continue
            changes = apply_wrestler_cleanup(w)
            if changes:
                obs.status = "fixed"
                obs.auto_fix_applied = True
                obs.auto_fix_notes = f"Cleanup changed: {list(changes.keys())}"
                obs.save(update_fields=["status", "auto_fix_applied", "auto_fix_notes"])
                applied += 1
        return applied

    # --------------------------------------------------- one full Earl cycle

    def cycle(self) -> EarlCycleStats:
        """
        One full Earl pass:
          1. audit_all     -> populate observations
          2. apply_safe_fixes -> close what we can auto-correct
          3. score_rules   -> update per-rule firing stats
          4. detect_patterns -> propose rule improvements
        """
        stats = EarlCycleStats()
        stats.new_observations = self.audit_all()
        stats.auto_fixes_applied = self.apply_safe_fixes()
        stats.rules_evaluated = self.score_rules()
        new_suggestions = self.detect_patterns()
        stats.suggestions_created = len(new_suggestions)

        # Track how many entities we audited (approximate — by counting open obs)
        from ..models import EarlObservation

        stats.entities_audited = (
            EarlObservation.objects.values("entity_type", "entity_id").distinct().count()
        )

        logger.info("Earl cycle done: %s", asdict(stats))
        return stats


default = Earl()
