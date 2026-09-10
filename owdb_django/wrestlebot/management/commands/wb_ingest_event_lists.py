"""
wb_ingest_event_lists — bulk-ingest event history from Wikipedia.

Two flavours:
    --ppvs           Ingest PPV/supercard history (WWE/WCW/ECW/AEW/TNA/NJPW/ROH/...).
    --episodes       Ingest TV episode lists from Wikipedia. Shows with a full
                     numbered list (AEW Dynamite, AEW Collision) get their whole
                     run. Shows Wikipedia only covers as "special episodes"
                     (WWE Raw, WWE SmackDown) get those instead.
    --all            Run both PPV + episode passes.
    --promotion KEY  Limit to one promotion (wwe/wcw/ecw/aew/tna/njpw/ajpw/roh/noah/nwa/mlw/aaa).
    --show KEY       Limit to one show (raw/smackdown/nitro/ecw_tv/dynamite/collision/nxt/impact/
                     njpw_strong/nwa_powerrr).

Idempotent — re-runs upsert events by (name, date).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ingest event-history list pages from Wikipedia (PPVs + selected episode lists)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--ppvs", action="store_true", help="Ingest the PPV/supercard list pages."
        )
        parser.add_argument(
            "--episodes",
            action="store_true",
            help="Ingest the TV episode list pages (numbered lists where "
            "Wikipedia has one, special-episode lists otherwise).",
        )
        parser.add_argument("--all", action="store_true", help="Run both PPV and episode passes.")
        parser.add_argument("--promotion", type=str, default="", help="Limit to one promotion key.")
        parser.add_argument("--show", type=str, default="", help="Limit to one show key.")

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.pipeline.event_lists import (
            ingest_ppv_list,
            ingest_episode_list,
            PPV_LIST_PAGES,
            EPISODE_LIST_PAGES,
            SPECIAL_EPISODE_LIST_PAGES,
        )

        # A show is ingestible if either registry has a page for it. Shows
        # in both are tried numbered-first inside `ingest_episode_list`.
        known_shows = list(
            dict.fromkeys(list(EPISODE_LIST_PAGES) + list(SPECIAL_EPISODE_LIST_PAGES))
        )

        do_ppvs = options["all"] or options["ppvs"] or not options["episodes"]
        do_episodes = options["all"] or options["episodes"]

        if do_ppvs:
            keys = [options["promotion"]] if options["promotion"] else list(PPV_LIST_PAGES.keys())
            self.stdout.write(self.style.SUCCESS("\n=== PPV / supercard lists ===\n"))
            grand_total = 0
            for k in keys:
                if k not in PPV_LIST_PAGES:
                    self.stdout.write(self.style.WARNING(f"  unknown promotion: {k}"))
                    continue
                stats = ingest_ppv_list(k)
                if stats.get("error"):
                    self.stdout.write(self.style.WARNING(f"  {k}: {stats['error']}"))
                    continue
                self.stdout.write(
                    f"  {k:<6} {stats.get('resolved_title', '?')[:50]:<55} "
                    f"extracted={stats['extracted']:>4}  created={stats['created']:>4}  "
                    f"updated={stats['updated']:>3}"
                )
                grand_total += stats["created"]
            self.stdout.write(self.style.SUCCESS(f"\n  PPVs created this run: {grand_total}\n"))

        if do_episodes:
            keys = [options["show"]] if options["show"] else known_shows
            self.stdout.write(self.style.SUCCESS("\n=== TV episode lists ===\n"))
            grand_total = 0
            for k in keys:
                if k not in known_shows:
                    self.stdout.write(self.style.WARNING(f"  unknown show: {k}"))
                    continue
                stats = ingest_episode_list(k)
                if stats.get("error"):
                    self.stdout.write(self.style.WARNING(f"  {k}: {stats['error']}"))
                    continue
                self.stdout.write(
                    f"  {k:<10} {stats.get('resolved_title', '?')[:44]:<46} "
                    f"{stats.get('list_kind', '?'):<9} "
                    f"extracted={stats['extracted']:>4}  created={stats['created']:>4}  "
                    f"updated={stats['updated']:>3}"
                )
                grand_total += stats["created"]
            self.stdout.write(self.style.SUCCESS(f"\n  Episodes created this run: {grand_total}\n"))
            self.stdout.write(
                "  Note: a 'special' list_kind means Wikipedia carries only that "
                "show's notable episodes, not its full weekly run. Wider coverage "
                "needs the TMDB pipeline (poll_tv_episodes / backfill_show_episodes), "
                "which wants TMDB_API_KEY and a TVShow.tmdb_id.\n"
            )
