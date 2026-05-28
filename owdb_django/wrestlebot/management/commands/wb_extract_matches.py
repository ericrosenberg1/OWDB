"""
wb_extract_matches — extract Match rows from Wikipedia event Results tables.

Run across all events that have a stored Wikipedia SourceFetch but no Match
rows yet:

    python manage.py wb_extract_matches              # all unprocessed events
    python manage.py wb_extract_matches --event-id 12
    python manage.py wb_extract_matches --rerun-all  # re-extract everything
    python manage.py wb_extract_matches --limit 20   # cap batch size

Idempotent — re-runs upsert by (event, match_order).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Extract Match rows from Wikipedia event Results tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--event-id", type=int, default=None, help="Process a single Event by ID."
        )
        parser.add_argument(
            "--rerun-all",
            action="store_true",
            help="Re-extract even events that already have Match rows.",
        )
        parser.add_argument(
            "--limit", type=int, default=50, help="Max events to process this run (default 50)."
        )

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Event, Match
        from owdb_django.wrestlebot.models import SourceFetch
        from owdb_django.wrestlebot.pipeline.match_extract import persist_matches_for_event

        if options["event_id"]:
            events = Event.objects.filter(id=options["event_id"])
        else:
            event_ids = set(
                SourceFetch.objects.filter(entity_type="event", source="wikipedia", http_status=200)
                .values_list("entity_id", flat=True)
                .distinct()
            )
            if not options["rerun_all"]:
                already_done = set(Match.objects.values_list("event_id", flat=True).distinct())
                event_ids -= already_done
            events = Event.objects.filter(id__in=event_ids).order_by("id")[: options["limit"]]

        self.stdout.write(
            self.style.SUCCESS(f"\nExtracting matches for {events.count()} events:\n")
        )
        total_extracted = 0
        total_created = 0
        for ev in events:
            stats = persist_matches_for_event(ev)
            if stats.get("error"):
                self.stdout.write(
                    self.style.WARNING(f"  Event#{ev.id} {ev.name[:50]}: {stats['error']}")
                )
                continue
            total_extracted += stats["extracted"]
            total_created += stats["created"]
            unmatched_count = len(stats["unmatched_names"])
            self.stdout.write(
                f"  Event#{ev.id} {ev.name[:50]}: "
                f"{stats['created']} created, {stats['updated']} updated, "
                f"{unmatched_count} unmatched names"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {total_extracted} matches extracted, {total_created} new rows created.\n"
            )
        )
