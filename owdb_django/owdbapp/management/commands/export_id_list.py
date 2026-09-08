"""
Management command: dump a full id list per public catalog entity type to a
gzipped, newline-delimited JSON file — one file per type, mirroring TMDB's
daily ID-export pattern (https://developer.themoviedb.org/docs/daily-id-exports).
A consumer who just wants "every wrestler id that exists" can pull this
instead of paging through the whole /api/wrestlers/ list.

Deliberately NOT wired to Celery Beat or any other scheduler — Celery stays
off per current project policy (see settings.py CELERY_BEAT_SCHEDULE and
docs/DEPLOY_NUC_CLOUDFLARE.md). This is a manually-invokable command someone
can run periodically later (cron, a one-off SSH session, whatever), not an
automatic job.

Gated entities (the seven VerificationMixin models) are exported through
the same `.public()` review gate the website and the REST API use — a
`rejected` row shouldn't leak into an id export any more than it should
leak into a list endpoint. The four plain-content models have no gate to
apply and are exported as-is.

Usage:
    python manage.py export_id_list
    python manage.py export_id_list --output-dir /path/to/exports
    python manage.py export_id_list --entity wrestlers --entity matches
"""

import gzip
import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from owdb_django.owdbapp.models import (
    Book,
    Event,
    Match,
    Podcast,
    Promotion,
    Special,
    Stable,
    Title,
    Venue,
    VideoGame,
    Wrestler,
)

# (url-path-style slug, model, the field to export as "name", whether this
# model carries VerificationMixin and needs the .public() review gate).
# Slugs match the API's own path segments (api_urls.py) — "games" for
# VideoGame, not "videogames".
ENTITY_EXPORTS = [
    ("wrestlers", Wrestler, "name", True),
    ("promotions", Promotion, "name", True),
    ("events", Event, "name", True),
    ("matches", Match, "match_text", True),
    ("titles", Title, "name", True),
    ("venues", Venue, "name", True),
    ("stables", Stable, "name", True),
    ("books", Book, "title", False),
    ("games", VideoGame, "name", False),
    ("podcasts", Podcast, "name", False),
    ("specials", Special, "title", False),
]
ENTITY_SLUGS = [slug for slug, *_ in ENTITY_EXPORTS]


class Command(BaseCommand):
    help = (
        "Dump a full id list per catalog entity type to a gzipped, "
        "newline-delimited JSON file (one file per type, TMDB "
        "daily-id-export style). Manually invoked only — not scheduled."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            type=str,
            default=None,
            help="Directory to write the export files into "
            "(default: <repo root>/exports/id_lists/).",
        )
        parser.add_argument(
            "--entity",
            action="append",
            dest="entities",
            choices=ENTITY_SLUGS,
            help="Limit the export to one entity type (repeatable). Default: export every type.",
        )

    def handle(self, *args, **options):
        verbosity = options["verbosity"]
        output_dir = Path(options["output_dir"] or (settings.BASE_DIR / "exports" / "id_lists"))
        output_dir.mkdir(parents=True, exist_ok=True)

        wanted = set(options["entities"]) if options["entities"] else set(ENTITY_SLUGS)
        stamp = timezone.now().strftime("%Y_%m_%d")

        for slug, model, name_field, is_gated in ENTITY_EXPORTS:
            if slug not in wanted:
                continue

            queryset = model.objects.public() if is_gated else model.objects.all()
            rows = queryset.order_by("pk").values_list("pk", name_field).iterator()

            out_path = output_dir / f"{slug}_ids_{stamp}.json.gz"
            count = 0
            with gzip.open(out_path, "wt", encoding="utf-8") as fh:
                for pk, name in rows:
                    fh.write(json.dumps({"id": pk, "name": name}) + "\n")
                    count += 1

            if verbosity >= 1:
                self.stdout.write(self.style.SUCCESS(f"{slug}: wrote {count} ids -> {out_path}"))
