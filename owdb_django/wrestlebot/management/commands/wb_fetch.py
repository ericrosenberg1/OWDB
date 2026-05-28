"""
wb_fetch — fetch source content for a list of candidate names and persist
as SourceFetch rows.

The fetch stage is the only stage that does network I/O. It's idempotent:
re-running it within the fresh-TTL window reuses existing SourceFetch rows
instead of re-fetching.

    # Fetch a specific list:
    python manage.py wb_fetch "Bret Hart" "Shawn Michaels" "Trish Stratus"

    # Discover then fetch in one go:
    python manage.py wb_fetch --discover --total 10

    # Force refetch (ignores fresh TTL):
    python manage.py wb_fetch --discover --total 5 --force
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from owdb_django.wrestlebot.pipeline.discovery import (
    WRESTLER_CATEGORIES,
    discover_events,
    discover_venues,
    discover_wrestlers,
)
from owdb_django.wrestlebot.pipeline.fetch import (
    fetch_action_figure_candidates,
    fetch_book_candidates,
    fetch_event_candidates,
    fetch_podcast_candidates,
    fetch_promotion_candidates,
    fetch_special_candidates,
    fetch_stable_candidates,
    fetch_theme_song_candidates,
    fetch_title_candidates,
    fetch_tv_show_candidates,
    fetch_venue_candidates,
    fetch_video_game_candidates,
    fetch_wrestler_candidates,
)


class Command(BaseCommand):
    help = "Fetch source content for candidate wrestlers and persist as SourceFetch rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "names", nargs="*",
            help="Names to fetch (positional). Omit and use --discover to enumerate.",
        )
        parser.add_argument(
            "--type",
            choices=["wrestler", "event", "venue", "promotion", "book",
                     "video_game", "podcast", "action_figure", "theme_song",
                     "title", "stable", "tv_show", "special"],
            default="wrestler",
            help="Entity type to fetch (default: wrestler).",
        )
        parser.add_argument(
            "--discover", action="store_true",
            help="Run discovery first to populate the candidate list.",
        )
        parser.add_argument(
            "--total", type=int, default=10,
            help="When using --discover, max total candidates (default: 10).",
        )
        parser.add_argument(
            "--per-category", type=int, default=3,
            help="When using --discover, max per category (default: 3).",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Refetch even if a recent SourceFetch already exists.",
        )

    def handle(self, *args, **options):
        names: list[str] = list(options["names"] or [])
        entity_type: str = options["type"]

        if options["discover"]:
            if entity_type == "wrestler":
                discovered = discover_wrestlers(
                    categories=WRESTLER_CATEGORIES,
                    per_category_limit=options["per_category"],
                    total_limit=options["total"],
                )
            elif entity_type == "event":
                discovered = discover_events(
                    per_category_limit=options["per_category"],
                    total_limit=options["total"],
                )
            elif entity_type == "venue":
                discovered = discover_venues(
                    per_category_limit=options["per_category"],
                    total_limit=options["total"],
                )
            else:
                discovered = []
            self.stdout.write(self.style.SUCCESS(
                f"Discovered {len(discovered)} {entity_type} candidate(s)"
            ))
            names.extend(discovered)

        if not names:
            self.stdout.write(self.style.WARNING(
                "No names given. Pass names as args, or use --discover."
            ))
            return

        # Deduplicate while preserving order.
        seen: set[str] = set()
        unique_names = [n for n in names if not (n in seen or seen.add(n))]

        self.stdout.write(f"Fetching {len(unique_names)} {entity_type} candidate(s)...")
        if entity_type == "wrestler":
            fetches = fetch_wrestler_candidates(unique_names, force=options["force"])
        elif entity_type == "event":
            fetches = fetch_event_candidates(unique_names, force=options["force"])
        elif entity_type == "venue":
            fetches = fetch_venue_candidates(unique_names, force=options["force"])
        elif entity_type == "promotion":
            fetches = fetch_promotion_candidates(unique_names, force=options["force"])
        elif entity_type == "book":
            fetches = fetch_book_candidates(unique_names, force=options["force"])
        elif entity_type == "video_game":
            fetches = fetch_video_game_candidates(unique_names, force=options["force"])
        elif entity_type == "podcast":
            fetches = fetch_podcast_candidates(unique_names, force=options["force"])
        elif entity_type == "action_figure":
            fetches = fetch_action_figure_candidates(unique_names, force=options["force"])
        elif entity_type == "theme_song":
            fetches = fetch_theme_song_candidates(unique_names, force=options["force"])
        elif entity_type == "title":
            fetches = fetch_title_candidates(unique_names, force=options["force"])
        elif entity_type == "stable":
            fetches = fetch_stable_candidates(unique_names, force=options["force"])
        elif entity_type == "tv_show":
            fetches = fetch_tv_show_candidates(unique_names, force=options["force"])
        elif entity_type == "special":
            fetches = fetch_special_candidates(unique_names, force=options["force"])
        else:
            fetches = []

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(fetches)} SourceFetch rows ready (created or reused)."
        ))
        for f in fetches:
            self.stdout.write(
                f"  SourceFetch#{f.id}  {f.source}  {f.candidate_name!r}  "
                f"({len(f.raw_content)} bytes)"
            )
