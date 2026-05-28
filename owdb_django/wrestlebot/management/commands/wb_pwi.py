"""
wb_pwi — ingest PWI ranking lists for one or more years.

The PWI 500 (and Female 50/100/150) are pulled from ProFightDB's mirror,
which maintains complete annual tables. Each list_kind × year becomes one
ExternalRanking with up to 500 ExternalRankingEntry rows.

Use:
    python manage.py wb_pwi --year 2024
    python manage.py wb_pwi --year 2024 --list pwi_500
    python manage.py wb_pwi --year 2020-2024            # range
    python manage.py wb_pwi --all-years                 # 1991..current
"""

from __future__ import annotations

from datetime import date
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ingest PWI ranking lists from ProFightDB."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=str,
            default=str(date.today().year - 1),
            help="Year or year range (e.g. 2024 or 2020-2024).",
        )
        parser.add_argument(
            "--list",
            type=str,
            default="all",
            choices=["all", "pwi_500", "pwi_female_50", "pwi_female_100", "pwi_female_150"],
            help="Which list kind (default: all).",
        )
        parser.add_argument(
            "--all-years",
            action="store_true",
            help="Ingest 1991..current year (PWI 500 started 1991).",
        )

    def handle(self, *args, **options):
        from owdb_django.wrestlebot.pipeline.pwi import ingest_pwi_list, PFDB_PWI_URLS

        if options["all_years"]:
            years = list(range(1991, date.today().year + 1))
        else:
            spec = options["year"].strip()
            if "-" in spec:
                lo, hi = spec.split("-", 1)
                years = list(range(int(lo), int(hi) + 1))
            else:
                years = [int(spec)]

        list_kinds = list(PFDB_PWI_URLS.keys()) if options["list"] == "all" else [options["list"]]

        self.stdout.write(
            self.style.SUCCESS(
                f"\nIngesting PWI lists: {list_kinds} for years {years[0]}..{years[-1]}\n"
            )
        )
        total_entries = 0
        for lk in list_kinds:
            for y in years:
                stats = ingest_pwi_list(lk, y)
                if stats.get("entries_created", 0):
                    self.stdout.write(
                        f"  {lk} {y}: {stats['entries_created']} entries, "
                        f"{stats['matched_wrestlers']} matched"
                    )
                    total_entries += stats["entries_created"]
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {lk} {y}: no entries ({stats.get('error', 'empty')})"
                        )
                    )
        self.stdout.write(self.style.SUCCESS(f"\nTotal entries ingested: {total_entries}\n"))
