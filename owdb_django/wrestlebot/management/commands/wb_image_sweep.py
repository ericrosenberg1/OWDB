"""
wb_image_sweep — batch image-gap sweep for wrestlers.

For every wrestler without an image but with a known Wikipedia URL, walks
the full image-discovery cascade (Wikidata P18 → Commons category →
Wikipedia body images) and assigns the first candidate that passes the
legal + identity + dimension gates.

Typical use:
    # Preview coverage on 20 wrestlers without writing anything.
    python manage.py wb_image_sweep --limit 20 --dry-run

    # Actually assign images, up to 30 wrestlers per run.
    python manage.py wb_image_sweep --limit 30

    # Output JSON for piping into jq.
    python manage.py wb_image_sweep --limit 20 --json

The dry-run mode is useful for seeing how much coverage the cascade
would add before committing. The accuracy contract is unchanged — every
assigned image still passes every legal + identity gate.
"""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Assign images to wrestlers without one via the legal-gate "
        "cascade (P18 → Commons category → Wikipedia body)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--entity-type", type=str, default="wrestler",
            choices=["wrestler", "promotion", "event", "venue",
                     "title", "stable", "tv_show",
                     "video_game", "book"],
            help=(
                "Entity type to sweep (default: wrestler). For events, an "
                "extra promotional-art guard refuses CC photos of posters / "
                "keyart / press kits (the photo may be CC but the design "
                "underneath isn't). For promotions/stables/tv_shows, the "
                "image_credit carries a nominative fair-use notice on write."
            ),
        )
        parser.add_argument(
            "--limit", type=int, default=10,
            help="Maximum entities to process this run (default 10, max 50).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help=(
                "Run the cascade and report verdicts WITHOUT writing entity "
                "fields. SourceFetch + FieldProvenance rows are still recorded "
                "so the audit log captures that we looked."
            ),
        )
        parser.add_argument(
            "--json", action="store_true",
            help="Emit results as JSON for scripting.",
        )
        parser.add_argument(
            "--verbose", action="store_true",
            help="Print every candidate considered for every entity.",
        )

    def handle(self, *args, **options):
        # Use the agent tool layer so the sweep logic stays in one place
        # — Celery / agent / CLI all converge on the same function.
        from owdb_django.wrestlebot.agents.tools import (
            _t_assign_images_for_entities_without_images,
        )

        limit = int(options["limit"])
        if limit < 1 or limit > 50:
            self.stderr.write(self.style.ERROR(
                "limit must be between 1 and 50"
            ))
            return

        result = _t_assign_images_for_entities_without_images(
            entity_type=options["entity_type"],
            limit=limit,
            dry_run=bool(options["dry_run"]),
        )

        if options["json"]:
            self.stdout.write(json.dumps(result, default=str, indent=2))
            return

        if not result.get("ok"):
            self.stderr.write(self.style.ERROR(
                f"Sweep failed: {result.get('error', '(no error message)')}"
            ))
            return

        self.stdout.write(self.style.HTTP_INFO(
            f"\n=== Image-gap sweep: {result['sweep_size']} "
            f"{options['entity_type']}s "
            f"({'dry-run' if result['dry_run'] else 'APPLY'}) ===\n"
        ))
        self.stdout.write(
            f"  assigned  {result['assigned']:>4}\n"
            f"  refused   {result['refused']:>4}\n"
        )

        if not result["results"]:
            self.stdout.write(
                f"  (no {options['entity_type']}s eligible — every one with a "
                "Wikipedia URL already has an image)"
            )
            return

        self.stdout.write(f"\nPer-{options['entity_type']} outcomes:")
        for row in result["results"]:
            if row["success"]:
                marker = self.style.SUCCESS("✓")
                line = (
                    f"{marker} {row['name']:<35}  "
                    f"id-conf={row['identity_confidence']:>3}  "
                    f"license={row['image_license']:<8}  "
                    f"via {row['source_path']}"
                )
            else:
                marker = self.style.WARNING("·")
                line = (
                    f"{marker} {row['name']:<35}  "
                    f"({row['considered_count']} candidate(s) tried)  "
                    f"{row['refusal_reason'][:120]}"
                )
            self.stdout.write(line)

        self.stdout.write("")
        if result["dry_run"]:
            self.stdout.write(self.style.NOTICE(
                "Dry-run complete. Re-run without --dry-run to apply."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Sweep applied. {result['assigned']} new image(s) assigned."
            ))
