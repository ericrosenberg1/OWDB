"""
wb_grow — run one round of mention-driven auto-discovery.

For every persisted entity, the pipeline captures every /wiki/X link found
in its source paragraphs as an EntityMention. This command:
  1. Ranks unresolved mentions by frequency.
  2. Fetches the top candidates from Wikipedia.
  3. Classifies each fetched page (wrestler / event / venue / promotion).
  4. Routes to the appropriate typed persist pipeline.

Anything that can't be classified confidently is skipped (accuracy-first).

    python manage.py wb_grow --limit 5
    python manage.py wb_grow --limit 20 --dry-run    # preview only
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run one round of mention-driven auto-discovery (graph follows links)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=5,
                            help="Max candidates to actually fetch this round (default: 5).")
        parser.add_argument("--dry-run", action="store_true",
                            help="Print top candidates without fetching anything.")

    def handle(self, *args, **options):
        limit = options["limit"]
        if options["dry_run"]:
            from owdb_django.wrestlebot.pipeline.auto_discovery import top_unresolved_mentions
            candidates = top_unresolved_mentions(limit=limit * 5)
            self.stdout.write(self.style.SUCCESS(
                f"\nTop {len(candidates)} unresolved mentions (dry-run):"
            ))
            for link, n in candidates:
                self.stdout.write(f"  {n:>3}x  {link}")
            return

        from owdb_django.wrestlebot.pipeline.auto_discovery import auto_discover_step
        stats = auto_discover_step(limit=limit)

        self.stdout.write(self.style.SUCCESS(
            f"\n=== Auto-discovery (limit={limit}) ===\n"
        ))
        self.stdout.write(f"  candidates considered: {stats.candidates_considered}")
        self.stdout.write(f"  fetched              : {stats.fetched}")
        self.stdout.write(self.style.SUCCESS(
            f"    wrestlers persisted: {stats.wrestler_persisted}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"    events persisted   : {stats.event_persisted}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"    venues persisted   : {stats.venue_persisted}"
        ))
        if stats.promotion_persisted:
            self.stdout.write(self.style.SUCCESS(
                f"    promotions persisted: {stats.promotion_persisted}"
            ))
        self.stdout.write(self.style.WARNING(
            f"  skipped generic       : {stats.skipped_generic}"
        ))
        self.stdout.write(self.style.WARNING(
            f"  skipped unclassified  : {stats.skipped_unclassified}"
        ))
        self.stdout.write(self.style.WARNING(
            f"  skipped no-content    : {stats.skipped_no_content}"
        ))
        self.stdout.write(self.style.WARNING(
            f"  skipped extract-fail  : {stats.skipped_extract_failed}"
        ))

        if stats.candidates:
            self.stdout.write("\nAttempted candidates:")
            for link, count, classification in stats.candidates:
                self.stdout.write(f"  {count:>3}x  {classification:<14}  {link}")
