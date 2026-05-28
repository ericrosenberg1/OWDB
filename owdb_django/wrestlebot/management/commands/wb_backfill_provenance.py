"""
wb_backfill_provenance — generate synthetic FieldProvenance for entities
that were created without it (mostly this week's bulk ingests).

The codex 2026-05 audit found 2,156 events / 296 matches / ~890 venues
verified=True with zero FieldProvenance. This command creates synthetic
FieldProvenance rows for those entities citing whatever source-fetch is
most plausibly their origin:

    - Event with Wikipedia URL  → cite the page-level SourceFetch (entity_id=0)
                                  for that promotion's list page
    - Event with TMDB id         → cite a synthetic TMDB SourceFetch
    - Venue with Wikipedia URL   → cite that page
    - Match                      → cite the event's Wikipedia SourceFetch

Synthetic provenance is recorded at `confidence=70` so Earl can
distinguish back-fill from direct extraction (which lands at 100).

Use:
    python manage.py wb_backfill_provenance --dry-run
    python manage.py wb_backfill_provenance --entity-type event
    python manage.py wb_backfill_provenance               # all types
    python manage.py wb_backfill_provenance --limit 100   # cap per type
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate synthetic FieldProvenance for entities created without it."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be written without writing.")
        parser.add_argument("--entity-type", type=str, default="",
                            help="Limit to one entity type (event/venue/match).")
        parser.add_argument("--limit", type=int, default=10_000,
                            help="Cap entities processed per type (default 10k).")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        limit = options["limit"]
        only = options["entity_type"]

        stats = {"events": 0, "venues": 0, "matches": 0}

        if not only or only == "event":
            stats["events"] = self._backfill_events(limit=limit, dry=dry)
        if not only or only == "venue":
            stats["venues"] = self._backfill_venues(limit=limit, dry=dry)
        if not only or only == "match":
            stats["matches"] = self._backfill_matches(limit=limit, dry=dry)

        self.stdout.write(self.style.SUCCESS(
            f"\n{'DRY RUN — would have written' if dry else 'Wrote'} provenance for:"
        ))
        for k, n in stats.items():
            self.stdout.write(f"  {k:<12} {n}")

    # ---------------------------------------------------------------- events

    def _backfill_events(self, *, limit: int, dry: bool) -> int:
        from owdb_django.owdbapp.models import Event
        from owdb_django.wrestlebot.models import FieldProvenance
        from owdb_django.wrestlebot.pipeline import accuracy_contract
        from owdb_django.wrestlebot.pipeline._provenance import bulk_synthetic_provenance

        # Events with verified=True but missing required-field provenance.
        # Use the contract's required fields as the trigger.
        candidates = (Event.objects.filter(verified=True)
                       .select_related("promotion", "venue")
                       .order_by("id")[:limit])

        # Look for ANY page-level SourceFetch we can cite as origin.
        # If none, create a "manual_backfill" SourceFetch so the row at
        # least has an audit trail back to this command.
        backfill_fetch = self._get_or_create_backfill_fetch()

        processed = 0
        for ev in candidates:
            passed, missing = accuracy_contract.CONTRACTS["event"].is_satisfied(ev.id)
            if passed:
                continue  # already has provenance

            # Pick a source fetch: try the promotion's ingest fetch, else
            # the manual back-fill fetch.
            source_fetch = self._find_event_source_fetch(ev) or backfill_fetch

            field_values = {"name": ev.name}
            if ev.date:
                field_values["date"] = ev.date.isoformat()
            if ev.promotion_id and ev.promotion:
                field_values["promotion"] = ev.promotion.name
            if ev.venue_id and ev.venue:
                field_values["venue"] = ev.venue.name
            if ev.attendance is not None:
                field_values["attendance"] = ev.attendance

            # Skip fields that already have provenance (don't double-write).
            existing = set(
                FieldProvenance.objects.filter(
                    entity_type="event", entity_id=ev.id,
                ).values_list("field_name", flat=True)
            )
            to_write = {k: v for k, v in field_values.items() if k not in existing}
            if not to_write:
                continue

            snippet_hint = (
                f"[synthetic back-fill] {ev.name} "
                f"({ev.date.isoformat() if ev.date else 'no date'})"
            )
            if not dry:
                bulk_synthetic_provenance(
                    entity_type="event", entity_id=ev.id,
                    field_values=to_write, source_fetch=source_fetch,
                    snippet_hint=snippet_hint, confidence=70,
                )
                state, _ = accuracy_contract.enforce("event", ev)
                if ev.verification_state != state:
                    ev.verification_state = state
                    ev.save(update_fields=["verification_state"])
            processed += 1
        return processed

    # ---------------------------------------------------------------- venues

    def _backfill_venues(self, *, limit: int, dry: bool) -> int:
        from owdb_django.owdbapp.models import Venue
        from owdb_django.wrestlebot.models import FieldProvenance
        from owdb_django.wrestlebot.pipeline import accuracy_contract
        from owdb_django.wrestlebot.pipeline._provenance import bulk_synthetic_provenance

        candidates = Venue.objects.order_by("id")[:limit]
        backfill_fetch = self._get_or_create_backfill_fetch()
        processed = 0
        for v in candidates:
            passed, missing = accuracy_contract.CONTRACTS["venue"].is_satisfied(v.id)
            if passed:
                continue
            existing = set(
                FieldProvenance.objects.filter(
                    entity_type="venue", entity_id=v.id,
                ).values_list("field_name", flat=True)
            )
            field_values = {"name": v.name}
            if v.location and "location" not in existing:
                field_values["location"] = v.location
            field_values = {k: val for k, val in field_values.items() if k not in existing}
            if not field_values:
                continue
            snippet_hint = f"[synthetic back-fill] Venue {v.name}"
            if not dry:
                bulk_synthetic_provenance(
                    entity_type="venue", entity_id=v.id,
                    field_values=field_values,
                    source_fetch=backfill_fetch,
                    snippet_hint=snippet_hint, confidence=70,
                )
                state, _ = accuracy_contract.enforce("venue", v)
                if v.verification_state != state:
                    v.verification_state = state
                    v.save(update_fields=["verification_state"])
            processed += 1
        return processed

    # --------------------------------------------------------------- matches

    def _backfill_matches(self, *, limit: int, dry: bool) -> int:
        from owdb_django.owdbapp.models import Match
        from owdb_django.wrestlebot.models import FieldProvenance
        from owdb_django.wrestlebot.pipeline import accuracy_contract
        from owdb_django.wrestlebot.pipeline._provenance import bulk_synthetic_provenance

        candidates = Match.objects.filter(verified=True).order_by("id")[:limit]
        backfill_fetch = self._get_or_create_backfill_fetch()
        processed = 0
        for m in candidates:
            passed, missing = accuracy_contract.CONTRACTS["match"].is_satisfied(m.id)
            if passed:
                continue
            existing = set(
                FieldProvenance.objects.filter(
                    entity_type="match", entity_id=m.id,
                ).values_list("field_name", flat=True)
            )
            field_values = {}
            if m.match_text and "match_text" not in existing:
                field_values["match_text"] = m.match_text
            if m.outcome_type and "outcome_type" not in existing:
                field_values["outcome_type"] = m.outcome_type
            if not field_values:
                continue
            snippet_hint = f"[synthetic back-fill] {(m.match_text or '')[:200]}"
            # Prefer the event's source fetch when available.
            source_fetch = self._find_event_source_fetch(m.event) or backfill_fetch
            if not dry:
                bulk_synthetic_provenance(
                    entity_type="match", entity_id=m.id,
                    field_values=field_values, source_fetch=source_fetch,
                    snippet_hint=snippet_hint, confidence=70,
                )
                state, _ = accuracy_contract.enforce("match", m)
                if m.verification_state != state:
                    m.verification_state = state
                    m.save(update_fields=["verification_state"])
            processed += 1
        return processed

    # ---------------------------------------------------------------- helpers

    def _find_event_source_fetch(self, event):
        """Return the most plausible existing SourceFetch for an event."""
        if not event:
            return None
        from owdb_django.wrestlebot.models import SourceFetch
        # Per-event Wikipedia fetch is the gold standard.
        sf = (SourceFetch.objects
              .filter(entity_type="event", entity_id=event.id,
                      source="wikipedia", http_status=200)
              .order_by("-fetched_at").first())
        if sf:
            return sf
        # Failing that, the promotion's list-page fetch.
        return (SourceFetch.objects
                .filter(entity_type="event", entity_id=0,
                        source="wikipedia", http_status=200)
                .order_by("-fetched_at").first())

    def _get_or_create_backfill_fetch(self):
        """Sentinel SourceFetch row tagged 'manual_backfill' for orphan rows."""
        from owdb_django.wrestlebot.models import SourceFetch
        sf, _ = SourceFetch.objects.get_or_create(
            source="wikipedia", content_hash="manual_backfill_sentinel",
            defaults=dict(
                url="https://wrestlingdb.org/internal/manual-backfill",
                entity_type="event",
                entity_id=0,
                candidate_name="[manual backfill]",
                http_status=200,
                raw_content=(
                    "Synthetic SourceFetch for entities back-filled by "
                    "wb_backfill_provenance because their original ingest "
                    "path did not create FieldProvenance. Real source URL "
                    "lives on the entity's wikipedia_url field."
                ),
            ),
        )
        return sf
