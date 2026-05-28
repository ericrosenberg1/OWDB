"""
wb_jr — run one JR (Jim Ross) cycle.

JR is the data-adding bot. He brings entities into the database by
discovering candidates, fetching source content, extracting, persisting,
and generating verified bios. Every accuracy guard already wired into the
pipeline applies; JR doesn't bypass any.

Use:
    python manage.py wb_jr                       # one full cycle (default sizes)
    python manage.py wb_jr --discovery 0 --bio 0 # extract-only pass (cheap)
    python manage.py wb_jr --auto-discover 10    # grow the graph aggressively
"""

from __future__ import annotations

from dataclasses import asdict

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run one JR cycle (data-adding bot)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--discovery", type=int, default=5, help="Discovery batch size (default 5)."
        )
        parser.add_argument("--fetch", type=int, default=5, help="Fetch batch size (default 5).")
        parser.add_argument(
            "--extract", type=int, default=20, help="Extract batch size (default 20)."
        )
        parser.add_argument(
            "--crossvalidate",
            type=int,
            default=5,
            help="Wikidata cross-validation batch (default 5).",
        )
        parser.add_argument(
            "--bio", type=int, default=5, help="Bio generation batch size (default 5)."
        )
        parser.add_argument(
            "--auto-discover",
            type=int,
            default=5,
            help="Mention-driven auto-discovery batch (default 5).",
        )

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.bots.jr import JR

        jr = JR()
        self.stdout.write(self.style.SUCCESS(f"\n=== {jr.name} ({jr.role}) ===\n"))
        stats = jr.cycle(
            discovery_limit=options["discovery"],
            fetch_limit=options["fetch"],
            extract_limit=options["extract"],
            crossvalidate_limit=options["crossvalidate"],
            bio_limit=options["bio"],
            auto_discover_limit=options["auto_discover"],
        )
        self.stdout.write("\nResults:")
        for k, v in asdict(stats).items():
            self.stdout.write(f"  {k:<40} {v}")
