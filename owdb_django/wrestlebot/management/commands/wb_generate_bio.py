"""
wb_generate_bio — generate and verify Sonnet 4.6 bios for wrestlers.

Two phases:
  1. Generate: Sonnet writes a bio strictly grounded in fetched source text.
  2. Verify:   A separate LLM pass checks every sentence against the source.

A bio is only marked status='verified' (and thus eligible to display) when
every sentence is supported. Otherwise it's stored with status='rejected'
and the unsupported claims are recorded.

    # Generate + verify for all wrestlers that don't have a verified bio:
    python manage.py wb_generate_bio

    # Specific wrestlers by id:
    python manage.py wb_generate_bio --wrestler 1 --wrestler 2

    # Just verify existing pending bios (no new generation):
    python manage.py wb_generate_bio --verify-only

    # Don't write to the entity 'about' field even when verified:
    python manage.py wb_generate_bio --no-promote
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from owdb_django.wrestlebot.claude_client import ClaudeClient
from owdb_django.wrestlebot.models import GeneratedBio
from owdb_django.wrestlebot.pipeline.bio import (
    generate_and_verify_for_event,
    generate_and_verify_for_promotion,
    generate_and_verify_for_venue,
    generate_and_verify_with_retry,
    generate_bio_for_wrestler,
)
from owdb_django.wrestlebot.pipeline.verify import verify_bio


class Command(BaseCommand):
    help = "Generate + verify Sonnet 4.6 bios for wrestlers (accuracy-first)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wrestler", type=int, action="append", default=None,
            help="Wrestler id(s) to process. Repeat for multiple. Omit = all eligible.",
        )
        parser.add_argument(
            "--limit", type=int, default=10,
            help="Max wrestlers to process when --wrestler is not given (default: 10).",
        )
        parser.add_argument(
            "--verify-only", action="store_true",
            help="Skip generation; only verify existing pending bios.",
        )
        parser.add_argument(
            "--no-promote", action="store_true",
            help="When verified, do NOT copy the bio text to Wrestler.about.",
        )
        parser.add_argument(
            "--no-retry", action="store_true",
            help="Disable the 3-pass self-correction loop (single attempt only).",
        )
        parser.add_argument(
            "--max-attempts", type=int, default=3,
            help="Max self-correction attempts per wrestler (default: 3).",
        )
        parser.add_argument(
            "--type",
            choices=["wrestler", "event", "venue", "promotion", "book", "video_game", "podcast"],
            default="wrestler",
            help="Entity type to generate bios for (default: wrestler).",
        )

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Wrestler

        client = ClaudeClient()
        if not client.available:
            self.stdout.write(self.style.ERROR(
                "Claude credentials missing. Set CLAUDE_CODE_OAUTH_TOKEN or "
                "ANTHROPIC_API_KEY in .env, then re-run."
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"Using Claude with {client.credential.source} "
            f"(oauth={client.credential.is_oauth}), model={client.model}\n"
        ))

        if options["verify_only"]:
            # Just re-verify whatever pending bios exist (manual path).
            pending_qs = GeneratedBio.objects.filter(status="pending", entity_type="wrestler")
            if options["wrestler"]:
                pending_qs = pending_qs.filter(entity_id__in=options["wrestler"])
            pending = list(pending_qs.order_by("id"))
            self.stdout.write(self.style.HTTP_INFO(
                f"\n=== verify-only ({len(pending)} bio(s)) ===\n"
            ))
            v = r = 0
            for bio in pending:
                vr = verify_bio(bio, client=client)
                if vr is None:
                    continue
                if vr.verified:
                    v += 1
                    if not options["no_promote"]:
                        self._promote(vr.bio)
                else:
                    r += 1
            self.stdout.write(self.style.SUCCESS(f"\nDone. Verified={v}, Rejected={r}."))
            return

        entity_type = options["type"]
        if entity_type != "wrestler":
            self._handle_non_wrestler(entity_type, options, client)
            return

        # Normal path: self-correcting per-wrestler loop.
        wrestler_ids = options["wrestler"]
        if wrestler_ids:
            wrestlers_qs = Wrestler.objects.filter(id__in=wrestler_ids)
        else:
            # All wrestlers without a verified bio AND not permanently rejected.
            handled_ids = GeneratedBio.objects.filter(
                entity_type="wrestler",
                status__in=["verified", "permanently_rejected"],
            ).values_list("entity_id", flat=True)
            wrestlers_qs = (
                Wrestler.objects.exclude(id__in=handled_ids).order_by("id")
            )
            wrestlers_qs = wrestlers_qs[: options["limit"]]

        wrestlers = list(wrestlers_qs)
        max_attempts = 1 if options["no_retry"] else options["max_attempts"]
        self.stdout.write(self.style.HTTP_INFO(
            f"\n=== Self-correcting bio pipeline ({len(wrestlers)} wrestler(s), "
            f"max {max_attempts} attempts each) ===\n"
        ))

        verified_count = 0
        rejected_count = 0
        permanent_count = 0
        for w in wrestlers:
            self.stdout.write(f"  Wrestler#{w.id} {w.name!r}...")
            bio = generate_and_verify_with_retry(w, client=client, max_attempts=max_attempts)
            if bio is None:
                self.stdout.write(self.style.WARNING("    skipped (no source / no Claude)"))
                continue
            if bio.status == "verified":
                verified_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f"    VERIFIED in {bio.attempt_number} attempt(s) "
                    f"(mode={bio.generation_mode}, {bio.claims_verified}/{bio.claims_total} claims)"
                ))
                if not options["no_promote"]:
                    self._promote(bio)
            elif bio.status == "permanently_rejected":
                permanent_count += 1
                self.stdout.write(self.style.ERROR(
                    f"    PERMANENTLY REJECTED after {bio.attempt_number} attempt(s)"
                ))
            else:
                rejected_count += 1
                self.stdout.write(self.style.WARNING(
                    f"    rejected (status={bio.status})"
                ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Verified={verified_count}, "
            f"Rejected={rejected_count}, Permanent={permanent_count}."
        ))

    @staticmethod
    def _promote(bio: GeneratedBio) -> None:
        """Copy a verified bio onto the entity's about field."""
        from owdb_django.owdbapp.models import Event, Venue, Wrestler

        if bio.entity_type == "wrestler":
            try:
                w = Wrestler.objects.get(id=bio.entity_id)
            except Wrestler.DoesNotExist:
                return
            w.about = bio.text
            w.save(update_fields=["about", "updated_at"])
        elif bio.entity_type == "event":
            try:
                e = Event.objects.get(id=bio.entity_id)
            except Event.DoesNotExist:
                return
            e.about = bio.text
            e.save(update_fields=["about", "updated_at"])
        elif bio.entity_type == "venue":
            try:
                v = Venue.objects.get(id=bio.entity_id)
            except Venue.DoesNotExist:
                return
            v.about = bio.text
            v.save(update_fields=["about", "updated_at"])
        elif bio.entity_type == "promotion":
            from owdb_django.owdbapp.models import Promotion
            try:
                p = Promotion.objects.get(id=bio.entity_id)
            except Promotion.DoesNotExist:
                return
            p.about = bio.text
            p.save(update_fields=["about", "updated_at"])

    def _handle_non_wrestler(self, entity_type: str, options: dict, client: ClaudeClient) -> None:
        """Bio gen + verify for events / venues / promotions. Single-attempt for v3.0."""
        from owdb_django.owdbapp.models import Event, Promotion, Venue

        if entity_type == "event":
            Model = Event
            generator = generate_and_verify_for_event
        elif entity_type == "venue":
            Model = Venue
            generator = generate_and_verify_for_venue
        elif entity_type == "promotion":
            Model = Promotion
            generator = generate_and_verify_for_promotion
        else:
            self.stdout.write(self.style.ERROR(f"Unsupported type {entity_type!r}"))
            return

        # Filter to entities that have a Wikipedia SourceFetch but no verified bio yet.
        handled_ids = GeneratedBio.objects.filter(
            entity_type=entity_type,
            status__in=["verified", "permanently_rejected"],
        ).values_list("entity_id", flat=True)
        qs = Model.objects.exclude(id__in=handled_ids).order_by("id")
        if options["wrestler"]:
            # --wrestler doubles as a generic entity-id filter when --type changes.
            qs = qs.filter(id__in=options["wrestler"])
        else:
            qs = qs[: options["limit"]]

        targets = list(qs)
        self.stdout.write(self.style.HTTP_INFO(
            f"\n=== Bio pipeline ({len(targets)} {entity_type}(s)) ===\n"
        ))

        verified = 0
        rejected = 0
        for ent in targets:
            self.stdout.write(f"  {entity_type.title()}#{ent.id} {ent.name!r}...")
            bio = generator(ent, client=client)
            if bio is None:
                self.stdout.write(self.style.WARNING("    skipped (no source / no Claude)"))
                continue
            if bio.status == "verified":
                verified += 1
                self.stdout.write(self.style.SUCCESS(
                    f"    VERIFIED ({bio.claims_verified}/{bio.claims_total} claims)"
                ))
                if not options["no_promote"]:
                    self._promote(bio)
            else:
                rejected += 1
                self.stdout.write(self.style.WARNING(f"    {bio.status}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Verified={verified}, Rejected={rejected}."
        ))
