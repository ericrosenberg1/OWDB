"""
wb_discover — enumerate candidate wrestler names from Wikipedia categories.

Discovery is read-only and does not write to the DB. Use the output as input
to `wb_fetch` (which will fetch + persist content).

    python manage.py wb_discover --total 20 --per-category 5
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from owdb_django.wrestlebot.pipeline.discovery import (
    WRESTLER_CATEGORIES,
    discover_wrestlers,
)


class Command(BaseCommand):
    help = "Discover candidate wrestler names from Wikipedia categories (read-only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=20,
            help="Maximum total candidates to return (default: 20).",
        )
        parser.add_argument(
            "--per-category",
            type=int,
            default=5,
            help="Maximum candidates per category (default: 5).",
        )
        parser.add_argument(
            "--category",
            action="append",
            default=None,
            help="Restrict to a specific category (may be passed multiple times).",
        )

    def handle(self, *args, **options):
        cats = options["category"] or list(WRESTLER_CATEGORIES)
        candidates = discover_wrestlers(
            categories=cats,
            per_category_limit=options["per_category"],
            total_limit=options["total"],
        )

        self.stdout.write(self.style.SUCCESS(f"Found {len(candidates)} candidates:"))
        for c in candidates:
            self.stdout.write(f"  {c}")
