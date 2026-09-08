"""
wb_extract — run the extractor over already-fetched SourceFetch rows.

Pure CPU; no network I/O. Safe to re-run as the extractor evolves.

By default operates on SourceFetch rows that haven't been used yet (used_at IS NULL).
Pass --all to re-extract everything.

    python manage.py wb_extract              # process unused fetches
    python manage.py wb_extract --all        # re-extract everything
    python manage.py wb_extract --fetch 42   # extract a single SourceFetch by id
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.pipeline.extract import (
    extract_action_figure, extract_book, extract_event, extract_podcast,
    extract_promotion, extract_special, extract_stable, extract_theme_song,
    extract_title, extract_tv_show, extract_venue, extract_video_game,
    extract_wrestler,
)
from owdb_django.wrestlebot.pipeline.persist import persist_wrestler
from owdb_django.wrestlebot.pipeline.persist_event import (
    persist_event, persist_promotion, persist_venue,
)
from owdb_django.wrestlebot.pipeline.persist_media import (
    persist_action_figure, persist_book, persist_podcast,
    persist_theme_song, persist_video_game,
)
from owdb_django.wrestlebot.pipeline.persist_title import (
    persist_stable, persist_title,
)
from owdb_django.wrestlebot.pipeline.persist_show import (
    persist_special, persist_tv_show,
)


class Command(BaseCommand):
    help = "Extract structured fields from stored SourceFetch rows and persist to entities."

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            choices=["wrestler", "event", "venue", "promotion", "book",
                     "video_game", "podcast", "action_figure", "theme_song",
                     "title", "stable", "tv_show", "special", "all"],
            default="all",
            help="Filter by SourceFetch.entity_type (default: all).",
        )
        parser.add_argument(
            "--all", action="store_true",
            help="Re-extract every SourceFetch, not just unused ones.",
        )
        parser.add_argument(
            "--fetch", type=int, default=None,
            help="Extract a single SourceFetch by id.",
        )
        parser.add_argument(
            "--limit", type=int, default=100,
            help="Maximum SourceFetch rows to process (default: 100).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Print what would be extracted; do not write to DB.",
        )

    def handle(self, *args, **options):
        qs = SourceFetch.objects.filter(http_status=200)
        if options["type"] != "all":
            qs = qs.filter(entity_type=options["type"])

        if options["fetch"] is not None:
            qs = qs.filter(id=options["fetch"])
        elif not options["all"]:
            qs = qs.filter(used_at__isnull=True)

        qs = qs.order_by("fetched_at")[: options["limit"]]

        fetches = list(qs)
        self.stdout.write(f"Processing {len(fetches)} SourceFetch row(s)...")

        wrote = 0
        skipped = 0
        for fetch in fetches:
            etype = fetch.entity_type or "wrestler"
            extractor = {
                "wrestler": extract_wrestler,
                "event": extract_event,
                "venue": extract_venue,
                "promotion": extract_promotion,
                "book": extract_book,
                "video_game": extract_video_game,
                "podcast": extract_podcast,
                "action_figure": extract_action_figure,
                "theme_song": extract_theme_song,
                "title": extract_title,
                "stable": extract_stable,
                "tv_show": extract_tv_show,
                "special": extract_special,
            }.get(etype)
            persister = {
                "wrestler": persist_wrestler,
                "event": persist_event,
                "venue": persist_venue,
                "promotion": persist_promotion,
                "book": persist_book,
                "video_game": persist_video_game,
                "podcast": persist_podcast,
                "action_figure": persist_action_figure,
                "theme_song": persist_theme_song,
                "title": persist_title,
                "stable": persist_stable,
                "tv_show": persist_tv_show,
                "special": persist_special,
            }.get(etype)
            if extractor is None or persister is None:
                self.stdout.write(self.style.WARNING(
                    f"  SourceFetch#{fetch.id} ({etype}) -> no extractor/persister"
                ))
                skipped += 1
                continue

            fields = extractor(fetch)
            if fields is None:
                self.stdout.write(self.style.WARNING(
                    f"  SourceFetch#{fetch.id} [{etype}] ({fetch.candidate_name!r}) -> no extractable fields"
                ))
                skipped += 1
                continue

            populated = fields.populated_fields()
            self.stdout.write(
                f"  SourceFetch#{fetch.id} [{etype}] ({fetch.candidate_name!r}) -> "
                f"{len(populated)} field(s): {sorted(populated.keys())}"
            )

            if options["dry_run"]:
                continue

            result = persister(fetch.candidate_name, fields, fetch)
            if result is None:
                self.stdout.write(self.style.WARNING(f"    persist returned None"))
                skipped += 1
                continue

            wrote += 1
            # PersistResult shape varies by entity; describe generically.
            entity_id = (
                getattr(result, "wrestler_id", None)
                or getattr(result, "event_id", None)
                or getattr(result, "venue_id", None)
                or getattr(result, "promotion_id", None)
                or getattr(result, "book_id", None)
                or getattr(result, "video_game_id", None)
                or getattr(result, "podcast_id", None)
                or getattr(result, "action_figure_id", None)
                or getattr(result, "theme_song_id", None)
                or getattr(result, "title_id", None)
                or getattr(result, "stable_id", None)
                or getattr(result, "tv_show_id", None)
                or getattr(result, "special_id", None)
            )
            self.stdout.write(self.style.SUCCESS(
                f"    persisted {etype}#{entity_id} (created={getattr(result, 'created', '?')}, "
                f"wrote={len(getattr(result, 'fields_written', []))}, "
                f"provenance_rows={getattr(result, 'provenance_rows_created', 0)})"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Persisted {wrote}, skipped {skipped}."
        ))
