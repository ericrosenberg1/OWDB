"""
wb_ingest_event_lists — bulk-ingest event history from Wikipedia.

Two flavours:
    --ppvs           Ingest PPV/supercard history (WWE/WCW/ECW/AEW/TNA/NJPW/ROH/...).
    --episodes       Ingest TV episode lists (AEW Dynamite supported via Wikipedia).
                     Raw/SmackDown/Nitro/NXT episodes flow through TMDB —
                     run `poll_tv_episodes` or `backfill_show_episodes`.
    --all            Run both PPV + episode passes.
    --promotion KEY  Limit to one promotion (wwe/wcw/ecw/aew/tna/njpw/ajpw/roh/noah).
    --show KEY       Limit to one show (raw/smackdown/nitro/ecw_tv/dynamite/collision/nxt/impact).

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
            help="Ingest the TV episode list pages (limited coverage; "
            "Raw/SmackDown/Nitro go via TMDB).",
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
            keys = [options["show"]] if options["show"] else list(EPISODE_LIST_PAGES.keys())
            self.stdout.write(self.style.SUCCESS("\n=== TV episode lists ===\n"))
            grand_total = 0
            for k in keys:
                if k not in EPISODE_LIST_PAGES:
                    self.stdout.write(self.style.WARNING(f"  unknown show: {k}"))
                    continue
                stats = ingest_episode_list(k)
                if stats.get("error"):
                    self.stdout.write(self.style.WARNING(f"  {k}: {stats['error']}"))
                    continue
                self.stdout.write(
                    f"  {k:<10} {stats.get('resolved_title', '?')[:50]:<52} "
                    f"extracted={stats['extracted']:>4}  created={stats['created']:>4}  "
                    f"updated={stats['updated']:>3}"
                )
                grand_total += stats["created"]
            self.stdout.write(self.style.SUCCESS(f"\n  Episodes created this run: {grand_total}\n"))
            self.stdout.write(
                "  Note: Raw/SmackDown/Nitro/NXT episode coverage flows through "
                "the existing TMDB pipeline (poll_tv_episodes / backfill_show_episodes). "
                "Set TMDB_API_KEY + TVShow.tmdb_id to enable.\n"
            )
