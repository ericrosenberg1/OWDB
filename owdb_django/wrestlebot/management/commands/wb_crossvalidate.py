"""
wb_crossvalidate — fetch Wikidata for each wrestler that already has a
Wikipedia source, extract typed fields, persist as a second FieldProvenance,
and run cross-source reconciliation.

Wikidata is structured, separately-edited, CC0, and accessible — making it
the right second source for accuracy cross-checking now that Cagematch's
infrastructure blocks programmatic access.

    python manage.py wb_crossvalidate                  # all wrestlers
    python manage.py wb_crossvalidate --wrestler 17    # one
    python manage.py wb_crossvalidate --limit 5
"""

from __future__ import annotations

import hashlib
import logging

from django.core.management.base import BaseCommand

from owdb_django.wrestlebot.models import SourceFetch
from owdb_django.wrestlebot.pipeline.extract import extract_wrestler
from owdb_django.wrestlebot.pipeline.persist import persist_wrestler
from owdb_django.wrestlebot.pipeline.reconcile_sources import reconcile_field_provenance
from owdb_django.wrestlebot.sources.wikidata import (
    WikidataAdapter,
    resolve_qid_for_wikipedia_title,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Cross-validate existing wrestlers against Wikidata (CC0, structured)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wrestler",
            type=int,
            default=None,
            help="Cross-validate one wrestler by id.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=30,
            help="Max wrestlers to process per invocation (default 30).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Refetch Wikidata even if we already have a wikidata SourceFetch.",
        )

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Wrestler

        if options["wrestler"]:
            wrestlers = Wrestler.objects.filter(id=options["wrestler"])
        else:
            wrestlers = (
                Wrestler.objects.exclude(wikipedia_url="")
                .exclude(wikipedia_url__isnull=True)
                .order_by("id")
            )
            wrestlers = wrestlers[: options["limit"]]

        adapter = WikidataAdapter()
        fetched = 0
        agreements_total = 0
        disagreements_total = 0
        no_qid = 0

        self.stdout.write(
            self.style.SUCCESS(f"\n=== wb_crossvalidate ({len(list(wrestlers))} wrestler(s)) ===")
        )
        wrestlers = list(wrestlers)  # materialise to allow re-iteration

        for w in wrestlers:
            self.stdout.write(f"  Wrestler#{w.id} {w.name!r}...")

            # 1. Skip if we already have a wikidata fetch and not --force
            if not options["force"]:
                existing = (
                    SourceFetch.objects.filter(
                        source="wikidata",
                        entity_type="wrestler",
                        entity_id=w.id,
                        http_status=200,
                    )
                    .order_by("-fetched_at")
                    .first()
                )
                if existing is not None:
                    fetch = existing
                    self.stdout.write(f"    reusing existing wikidata fetch SourceFetch#{fetch.id}")
                else:
                    fetch = self._fetch_and_persist(w, adapter)
            else:
                fetch = self._fetch_and_persist(w, adapter)

            if fetch is None:
                no_qid += 1
                continue
            fetched += 1

            # 2. Extract typed fields from Wikidata
            fields = extract_wrestler(fetch)
            if fields is None:
                self.stdout.write(self.style.WARNING("    no extractable fields"))
                continue

            populated = fields.populated_fields()
            self.stdout.write(self.style.SUCCESS(f"    extracted: {sorted(populated.keys())}"))

            # 3. Persist — this won't overwrite existing values (first-write-wins)
            #    but will write FieldProvenance rows for cross-source tracking.
            persist_wrestler(w.name, fields, fetch)

            # 4. Reconcile — compare values across sources.
            rec = reconcile_field_provenance("wrestler", w.id)
            agreements = len(rec["agreements"])
            disagreements = len(rec["disagreements"])
            agreements_total += agreements
            disagreements_total += disagreements

            if agreements:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"    AGREEMENTS ({agreements}): "
                        + ", ".join(
                            f"{a.field_name}={a.values[0]!r:.30}" for a in rec["agreements"]
                        )
                    )
                )
            if disagreements:
                self.stdout.write(self.style.ERROR(f"    DISAGREEMENTS ({disagreements}):"))
                for d in rec["disagreements"]:
                    pairs = "; ".join(f"{s}={v!r:.40}" for s, v in zip(d.sources, d.values))
                    self.stdout.write(self.style.ERROR(f"      {d.field_name}: {pairs}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {fetched} fetched / {no_qid} no QID, "
                f"{agreements_total} field agreement(s), "
                f"{disagreements_total} disagreement(s)."
            )
        )

    def _fetch_and_persist(self, wrestler, adapter: WikidataAdapter):
        """Fetch Wikidata for a wrestler and persist a SourceFetch row."""
        # Use the wrestler's name (which equals its Wikipedia page title)
        qid = resolve_qid_for_wikipedia_title(wrestler.name)
        if not qid:
            self.stdout.write(self.style.WARNING("    no Wikidata QID found"))
            return None

        result = adapter.fetch_wrestler_by_qid(qid)
        if result is None:
            self.stdout.write(self.style.WARNING(f"    Wikidata entity {qid} not retrievable"))
            return None

        fetch = SourceFetch.objects.create(
            source="wikidata",
            url=result.url,
            entity_type="wrestler",
            entity_id=wrestler.id,
            candidate_name=wrestler.name,
            http_status=result.http_status,
            content_hash=hashlib.sha256(result.raw_content.encode("utf-8")).hexdigest(),
            raw_content=result.raw_content,
        )
        self.stdout.write(
            f"    fetched {qid} -> SourceFetch#{fetch.id} ({len(result.raw_content):,} bytes)"
        )
        return fetch
