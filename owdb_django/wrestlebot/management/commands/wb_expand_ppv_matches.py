"""
wb_expand_ppv_matches — fetch + extract matches for every PPV event in
the DB that doesn't yet have match rows.

For each PPV-type Event without matches:
  1. Best-effort lookup of its Wikipedia article (by event name + year).
  2. Fetch the page into SourceFetch with entity_id linked to the event.
  3. Run pipeline/match_extract.persist_matches_for_event on it.
  4. Report wrestlers we couldn't match — those become Al's backlog.

Use:
    python manage.py wb_expand_ppv_matches              # all PPVs without matches
    python manage.py wb_expand_ppv_matches --limit 20
    python manage.py wb_expand_ppv_matches --promotion wwe
    python manage.py wb_expand_ppv_matches --dry-run
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Ensure every PPV event has its match list extracted from Wikipedia."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50,
                            help="Max events to process per run (default 50).")
        parser.add_argument("--promotion", type=str, default="",
                            help="Limit to one promotion slug (e.g. 'wwe', 'aew').")
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would happen without writing.")
        parser.add_argument("--include-tv", action="store_true",
                            help="Also process tv_episode events (default: PPVs only).")

    def handle(self, *args, **options):
        from owdb_django.owdbapp.models import Event
        from owdb_django.wrestlebot.models import SourceFetch
        from owdb_django.wrestlebot.pipeline.fetch import fetch_event_candidates
        from owdb_django.wrestlebot.pipeline.match_extract import persist_matches_for_event

        types = ["ppv"]
        if options["include_tv"]:
            types.append("tv_episode")

        # Events without any Match rows yet.
        qs = (Event.objects
              .filter(event_type__in=types)
              .exclude(matches__isnull=False)
              .distinct()
              .select_related("promotion", "venue")
              .order_by("-date"))
        if options["promotion"]:
            qs = qs.filter(promotion__slug=options["promotion"])
        qs = qs[:max(1, options["limit"])]

        self.stdout.write(self.style.SUCCESS(
            f"\nProcessing {qs.count()} events without matches...\n"
        ))

        totals = {"events_processed": 0, "events_with_matches": 0,
                  "matches_created": 0, "unmatched_participants": 0,
                  "no_wiki_page": 0}

        import re as _re

        def _candidate_titles(event) -> list[str]:
            """
            Plausible Wikipedia titles in PRIORITY order. Year-disambiguated
            forms first — most PPVs use 'EventName (YYYY)' on Wikipedia.
            The bare base name is a last resort because it usually leads
            to the event-brand disambiguation page rather than a single
            instance (which has the Results table we need).
            """
            raw = (event.name or "").strip()
            base = _re.sub(r"\s*\[[^\]]*\]\s*", "", raw).strip()
            base = _re.sub(r"\s+", " ", base).strip()
            year = event.date.year if event.date else None
            out: list[str] = []
            if base and year:
                out.append(f"{base} ({year})")
                out.append(f"{base} {year}")
            if base:
                out.append(base)
            return out

        # Cap on matches per event — articles for event-brand disambig
        # pages can produce 100+ fake matches by reading season-summary
        # tables. A real PPV card has 5-20 matches.
        MATCHES_PER_EVENT_SANE_CAP = 30

        for event in qs:
            totals["events_processed"] += 1

            # Find or fetch the event's Wikipedia article.
            fetch = (SourceFetch.objects
                     .filter(entity_type="event", entity_id=event.id,
                             source="wikipedia", http_status=200)
                     .order_by("-fetched_at").first())
            if not fetch:
                if options["dry_run"]:
                    self.stdout.write(
                        f"  [dry-run] would try titles {_candidate_titles(event)[:3]} "
                        f"for: {event.name} ({event.date})"
                    )
                    continue
                results = []
                tried = []
                for title in _candidate_titles(event):
                    tried.append(title)
                    results = fetch_event_candidates([title], force=False)
                    if results:
                        break
                if not results:
                    self.stdout.write(self.style.WARNING(
                        f"  no Wikipedia page: Event#{event.id} {event.name[:50]}  "
                        f"(tried: {tried})"
                    ))
                    totals["no_wiki_page"] += 1
                    continue
                fresh = results[0]
                # The newly-fetched SourceFetch defaults to entity_id=0;
                # link it to this specific event so match_extract can
                # find it on subsequent runs.
                if fresh.entity_id != event.id:
                    fresh.entity_id = event.id
                    fresh.save(update_fields=["entity_id"])
                fetch = fresh

            if options["dry_run"]:
                self.stdout.write(
                    f"  [dry-run] would extract matches: {event.name} "
                    f"(SourceFetch#{fetch.id})"
                )
                continue

            # PRE-CHECK: if the Wikipedia content looks like an event-brand
            # disambig page (no "Results" table or too many rows), refuse
            # to persist matches. We'd rather have NO matches than 200
            # wrong ones.
            from owdb_django.wrestlebot.pipeline.match_extract import extract_matches
            preview = extract_matches(fetch.raw_content)
            if len(preview) > MATCHES_PER_EVENT_SANE_CAP:
                self.stdout.write(self.style.WARNING(
                    f"  REFUSED Event#{event.id} {event.name[:50]}  "
                    f"({len(preview)} matches found — likely an event-brand "
                    f"disambig page, not a single PPV)"
                ))
                # Detach the fetch so future runs don't re-find it.
                fetch.entity_id = 0
                fetch.save(update_fields=["entity_id"])
                continue

            stats = persist_matches_for_event(event, fetch=fetch)
            n_created = stats.get("created", 0)
            unmatched = stats.get("unmatched_names", []) or []
            totals["matches_created"] += n_created
            totals["unmatched_participants"] += len(unmatched)
            if n_created > 0:
                totals["events_with_matches"] += 1

            short_name = event.name[:50]
            unmatched_str = f"  [{len(unmatched)} unmatched]" if unmatched else ""
            self.stdout.write(
                f"  Event#{event.id:>5} {short_name:<55} → {n_created} matches{unmatched_str}"
            )
            if unmatched and len(unmatched) <= 5:
                self.stdout.write(self.style.WARNING(
                    f"      unmatched: {', '.join(unmatched)}"
                ))

        self.stdout.write(self.style.SUCCESS("\nDone."))
        for k, v in totals.items():
            self.stdout.write(f"  {k:<32} {v}")
