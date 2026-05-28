"""
wb_audit — run all accuracy guards across every entity in the DB.

Reports:
  - Consistency issues per wrestler (field-level rule violations)
  - Field-cleanup pending changes (artifacts that should be cleaned)
  - Stale-source candidates (wrestlers whose primary fetch is > 30 days old)
  - Mention resolution coverage (% mentions resolved)

Read-only by default. Pass --fix to apply field-cleanup changes (the only
safe auto-fix). Other issues are surfaced as warnings.

    python manage.py wb_audit
    python manage.py wb_audit --fix
    python manage.py wb_audit --wrestler 17  # single subject
"""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Run accuracy guards across the DB and report issues."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wrestler", type=int, default=None,
            help="Audit only one wrestler by id.",
        )
        parser.add_argument(
            "--fix", action="store_true",
            help="Apply safe auto-fixes (field cleanup). Default is dry-run.",
        )
        parser.add_argument(
            "--stale-days", type=int, default=30,
            help="A SourceFetch older than this is flagged stale (default: 30).",
        )

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Wrestler
        from owdb_django.wrestlebot.models import (
            EntityMention, GeneratedBio, SourceFetch,
        )
        from owdb_django.wrestlebot.pipeline.cleanup import (
            apply_wrestler_cleanup, clean_wrestler_fields,
        )
        from owdb_django.wrestlebot.pipeline.consistency import check_wrestler

        wrestler_id: Optional[int] = options["wrestler"]
        apply_fixes: bool = options["fix"]
        stale_days: int = options["stale_days"]

        wrestlers_qs = Wrestler.objects.all().order_by("id")
        if wrestler_id is not None:
            wrestlers_qs = wrestlers_qs.filter(id=wrestler_id)

        wrestlers = list(wrestlers_qs)
        if not wrestlers:
            self.stdout.write(self.style.WARNING("No wrestlers found."))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\n=== wb_audit — {len(wrestlers)} wrestler(s) ({'fix' if apply_fixes else 'dry-run'}) ==="
        ))

        # Aggregates
        consistency_issues = 0
        consistency_wrestlers = 0
        cleanup_pending = 0
        cleanup_fields = 0
        stale_fetches = 0
        missing_bio = 0

        stale_cutoff = timezone.now() - timedelta(days=stale_days)

        for w in wrestlers:
            issues_for_this = check_wrestler(w)
            cleanup_changes = clean_wrestler_fields(w)
            primary_fetch = (
                SourceFetch.objects
                .filter(entity_type="wrestler", entity_id=w.id, source="wikipedia")
                .order_by("-fetched_at").first()
            )
            stale = bool(primary_fetch and primary_fetch.fetched_at < stale_cutoff)
            bio = (
                GeneratedBio.objects
                .filter(entity_type="wrestler", entity_id=w.id, status="verified")
                .exists()
            )

            interesting = bool(issues_for_this or cleanup_changes or stale or not bio)
            if not interesting:
                continue

            self.stdout.write(f"\n  [{w.id}] {w.name}")

            if issues_for_this:
                consistency_wrestlers += 1
                consistency_issues += len(issues_for_this)
                for issue in issues_for_this:
                    color = self.style.ERROR if issue.severity == "error" else self.style.WARNING
                    self.stdout.write(color(
                        f"      [{issue.severity}] {issue.rule}: {issue.message}"
                    ))

            if cleanup_changes:
                cleanup_pending += 1
                cleanup_fields += len(cleanup_changes)
                for field, new_value in cleanup_changes.items():
                    old = getattr(w, field, "")
                    self.stdout.write(self.style.WARNING(
                        f"      [cleanup] {field}: {(old or '')[:60]!r} -> {(new_value or '')[:60]!r}"
                    ))
                if apply_fixes:
                    apply_wrestler_cleanup(w)
                    self.stdout.write(self.style.SUCCESS("      -> applied"))

            if stale and primary_fetch:
                stale_fetches += 1
                age_days = (timezone.now() - primary_fetch.fetched_at).days
                self.stdout.write(self.style.WARNING(
                    f"      [stale] primary Wikipedia fetch is {age_days}d old "
                    f"(SourceFetch#{primary_fetch.id})"
                ))

            if not bio:
                missing_bio += 1
                self.stdout.write(self.style.WARNING("      [no-bio] no verified bio"))

        # Cross-entity consistency: events + venues
        from owdb_django.owdbapp.models import Event, Venue
        from owdb_django.wrestlebot.pipeline.consistency import check_event, check_venue
        event_issues = 0
        venue_issues = 0
        for e in Event.objects.all():
            for issue in check_event(e):
                event_issues += 1
                color = self.style.ERROR if issue.severity == "error" else self.style.WARNING
                self.stdout.write(color(
                    f"  [event#{e.id}] {e.name}: {issue.rule}: {issue.message}"
                ))
        for v in Venue.objects.all():
            for issue in check_venue(v):
                venue_issues += 1
                color = self.style.ERROR if issue.severity == "error" else self.style.WARNING
                self.stdout.write(color(
                    f"  [venue#{v.id}] {v.name}: {issue.rule}: {issue.message}"
                ))

        # Cross-cutting stats
        mention_total = EntityMention.objects.count()
        mention_resolved = EntityMention.objects.filter(resolved_entity_id__isnull=False).count()
        mention_pct = (100.0 * mention_resolved / mention_total) if mention_total else 0.0

        # Source drift events (Wikipedia changed under us)
        from owdb_django.wrestlebot.models import WrestleBotActivity
        drift_events = WrestleBotActivity.objects.filter(source="source_drift")
        if wrestler_id is not None:
            drift_events = drift_events.filter(entity_id=wrestler_id)
        drift_count = drift_events.count()

        # Cross-source disagreements
        xs_disagree = WrestleBotActivity.objects.filter(source="cross_source_disagreement").count()

        if drift_count:
            self.stdout.write(self.style.WARNING(
                f"\n  Source drift events ({drift_count} — Wikipedia changed after our extract):"
            ))
            for ev in drift_events.order_by("-created_at")[:5]:
                d = ev.details or {}
                self.stdout.write(self.style.WARNING(
                    f"    [{ev.entity_type}#{ev.entity_id}] {ev.entity_name}  "
                    f"{d.get('field')}: stored={d.get('stored_value', '')!r:.40} -> new={d.get('new_source_value', '')!r:.40}"
                ))

        if xs_disagree:
            self.stdout.write(self.style.ERROR(
                f"\n  Cross-source disagreements: {xs_disagree} — review WrestleBotActivity for details"
            ))

        self.stdout.write(self.style.SUCCESS("\n=== summary ==="))
        self.stdout.write(
            f"  consistency (wrestlers): {consistency_issues} issue(s) across {consistency_wrestlers} wrestler(s)"
        )
        self.stdout.write(f"  consistency (events):    {event_issues} issue(s)")
        self.stdout.write(f"  consistency (venues):    {venue_issues} issue(s)")
        self.stdout.write(
            f"  cleanup:            {cleanup_fields} field change(s) across {cleanup_pending} wrestler(s)"
            + (" — APPLIED" if apply_fixes else " — dry-run (re-run with --fix)")
        )
        self.stdout.write(f"  stale fetches:      {stale_fetches} wrestler(s) need re-fetch (>{stale_days}d)")
        self.stdout.write(f"  source drift:       {drift_count} field change(s) flagged for review")
        self.stdout.write(f"  cross-source dis:   {xs_disagree} disagreement(s) between sources")
        self.stdout.write(f"  no-bio:             {missing_bio} wrestler(s) without a verified bio")
        self.stdout.write(
            f"  mentions:           {mention_resolved:,}/{mention_total:,} resolved ({mention_pct:.1f}%)"
        )
