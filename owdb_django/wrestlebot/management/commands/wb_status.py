"""
wb_status — print a snapshot of the WrestleBot v3 pipeline state.

Shows counts, latest activity, and a few sample wrestlers with their
field provenance so you can sanity-check that everything in the DB has
a real source.

    python manage.py wb_status
    python manage.py wb_status --sample 5
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from owdb_django.wrestlebot.models import (
    FieldProvenance,
    GeneratedBio,
    SourceFetch,
)


class Command(BaseCommand):
    help = "Show WrestleBot v3 pipeline status: counts, latest activity, sample provenance."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sample", type=int, default=3,
            help="How many sample wrestlers to expand with provenance (default: 3).",
        )

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Wrestler, Promotion, Event, Match

        # Late import to avoid app-loading issues at command-listing time.
        sample_count = options["sample"]

        self.stdout.write(self.style.SUCCESS("\n=== WrestleBot v3 Pipeline Status ===\n"))

        self.stdout.write("Entity counts:")
        self.stdout.write(f"  Wrestlers : {Wrestler.objects.count():>6}  "
                          f"(verified={Wrestler.objects.filter(verified=True).count()})")
        self.stdout.write(f"  Promotions: {Promotion.objects.count():>6}  "
                          f"(verified={Promotion.objects.filter(verified=True).count()})")
        self.stdout.write(f"  Events    : {Event.objects.count():>6}  "
                          f"(verified={Event.objects.filter(verified=True).count()})")
        self.stdout.write(f"  Matches   : {Match.objects.count():>6}  "
                          f"(verified={Match.objects.filter(verified=True).count()})")

        self.stdout.write("\nPipeline tables:")
        self.stdout.write(f"  SourceFetch     : {SourceFetch.objects.count():>6}")
        self.stdout.write(f"  FieldProvenance : {FieldProvenance.objects.count():>6}")
        self.stdout.write(f"  GeneratedBio    : {GeneratedBio.objects.count():>6}")

        # Sources breakdown
        source_counts = (
            SourceFetch.objects.values("source")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        if source_counts:
            self.stdout.write("\nSourceFetch by source:")
            for row in source_counts:
                self.stdout.write(f"  {row['source']:<20} {row['n']}")

        # Sample wrestlers with provenance
        if sample_count > 0 and Wrestler.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                f"\nSample wrestlers (newest {sample_count}):\n"
            ))
            for w in Wrestler.objects.order_by("-id")[:sample_count]:
                self.stdout.write(
                    f"  [{w.id}] {w.name}  (verified={w.verified}, "
                    f"source={w.verification_source or '-'})"
                )
                provs = (
                    FieldProvenance.objects
                    .filter(entity_type="wrestler", entity_id=w.id)
                    .select_related("source_fetch")
                    .order_by("field_name", "-extracted_at")
                )
                # Collapse to latest per field
                seen_fields: set[str] = set()
                for p in provs:
                    if p.field_name in seen_fields:
                        continue
                    seen_fields.add(p.field_name)
                    self.stdout.write(
                        f"      .{p.field_name:<18} = {p.value!r:<50.50}  "
                        f"(from {p.source_fetch.source})"
                    )
                self.stdout.write("")
