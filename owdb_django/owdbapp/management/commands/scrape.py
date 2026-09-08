"""
Management command to run scrapers manually.

Usage:
    python manage.py scrape --source=wikipedia --type=wrestlers --limit=50
    python manage.py scrape --all --limit=25
    python manage.py scrape --stats
"""

from django.core.management.base import BaseCommand, CommandError

from owdb_django.owdbapp.scrapers import ScraperCoordinator


class Command(BaseCommand):
    help = "Run web scrapers to populate the wrestling database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            type=str,
            choices=["wikipedia", "cagematch", "profightdb", "all"],
            default="all",
            help="Which source to scrape (default: all)",
        )
        parser.add_argument(
            "--type",
            type=str,
            choices=["wrestlers", "promotions", "events", "all"],
            default="all",
            help="What type of data to scrape (default: all)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum items to scrape per type (default: 50)",
        )
        parser.add_argument(
            "--stats",
            action="store_true",
            help="Show scraper statistics instead of scraping",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be scraped without actually scraping",
        )

    def handle(self, *args, **options):
        coordinator = ScraperCoordinator()

        if options["stats"]:
            self.show_stats(coordinator)
            return

        source = options["source"]
        data_type = options["type"]
        limit = options["limit"]

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would scrape {data_type} from {source} (limit: {limit})"
                )
            )
            return

        self.stdout.write(
            self.style.HTTP_INFO(
                f"Starting scrape: {data_type} from {source} (limit: {limit})"
            )
        )

        try:
            results = coordinator.scrape_and_import(
                source=source,
                data_type=data_type,
                limit=limit,
            )

            self.stdout.write(self.style.SUCCESS("\nScraping complete!"))
            self.stdout.write(f"  Wrestlers: {results['wrestlers_scraped']} scraped, "
                            f"{results['wrestlers_imported']} imported")
            self.stdout.write(f"  Promotions: {results['promotions_scraped']} scraped, "
                            f"{results['promotions_imported']} imported")
            self.stdout.write(f"  Events: {results['events_scraped']} scraped, "
                            f"{results['events_imported']} imported")

        except Exception as e:
            raise CommandError(f"Scraping failed: {e}")

    def show_stats(self, coordinator):
        """Display scraper statistics."""
        self.stdout.write(self.style.HTTP_INFO("\nScraper Statistics"))
        self.stdout.write("=" * 50)

        stats = coordinator.get_stats()

        for source_name, source_stats in stats.items():
            self.stdout.write(f"\n{source_name.upper()}")
            self.stdout.write("-" * 30)

            rate_limits = source_stats.get("rate_limits", {})

            minute = rate_limits.get("minute", {})
            self.stdout.write(
                f"  Per minute: {minute.get('current', 0)}/{minute.get('limit', 0)}"
            )

            hour = rate_limits.get("hour", {})
            self.stdout.write(
                f"  Per hour:   {hour.get('current', 0)}/{hour.get('limit', 0)}"
            )

            day = rate_limits.get("day", {})
            self.stdout.write(
                f"  Per day:    {day.get('current', 0)}/{day.get('limit', 0)}"
            )

        self.stdout.write("\n")
