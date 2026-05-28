"""
Backfill historical TV episodes from TMDB.

This command fetches episode data from TMDB for TV shows and creates
Event records for each episode. This is used for initial setup and
to fill in any missing historical data.

Usage:
    python manage.py backfill_tv_episodes
    python manage.py backfill_tv_episodes --show "WWE Raw"
    python manage.py backfill_tv_episodes --show "WWE Raw" --year 2024
    python manage.py backfill_tv_episodes --all
    python manage.py backfill_tv_episodes --verify
"""
from datetime import date

from django.core.management.base import BaseCommand

from owdb_django.owdbapp.models import TVShow
from owdb_django.owdbapp.scrapers.tv_episodes import TVEpisodeScraper


class Command(BaseCommand):
    help = 'Backfill historical TV episodes from TMDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show',
            type=str,
            help='Show name to backfill (partial match supported)',
        )
        parser.add_argument(
            '--show-id',
            type=int,
            help='Show ID to backfill',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Specific year to backfill',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Backfill all shows with TMDB IDs',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Verify episode counts against TMDB without backfilling',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=500,
            help='Maximum episodes to process per show (default: 500)',
        )
        parser.add_argument(
            '--weekly-only',
            action='store_true',
            help='Only process weekly TV shows (not PPVs)',
        )

    def handle(self, *args, **options):
        scraper = TVEpisodeScraper()

        # Get shows to process
        if options.get('show_id'):
            shows = TVShow.objects.filter(id=options['show_id'])
        elif options.get('show'):
            shows = TVShow.objects.filter(name__icontains=options['show'])
        elif options.get('all'):
            shows = TVShow.objects.filter(tmdb_id__isnull=False)
        else:
            self.stdout.write(
                self.style.ERROR('Specify --show, --show-id, or --all')
            )
            return

        # Apply weekly-only filter
        if options.get('weekly_only'):
            shows = shows.filter(show_type='weekly')

        if not shows.exists():
            self.stdout.write(self.style.WARNING('No shows found matching criteria'))
            return

        # Verify mode - just check episode counts
        if options.get('verify'):
            self._verify_shows(shows, scraper)
            return

        # Backfill mode
        total_created = 0
        total_updated = 0
        total_errors = 0

        for show in shows:
            if not show.tmdb_id:
                self.stdout.write(
                    self.style.WARNING(f"Skipping {show.name}: no TMDB ID")
                )
                continue

            self.stdout.write(f"\nBackfilling: {show.name}")
            self.stdout.write(f"  TMDB ID: {show.tmdb_id}")

            try:
                if options.get('year'):
                    results = scraper.backfill_show_by_year(show, options['year'])
                else:
                    # Use date range from premiere to today
                    start_date = show.premiere_date
                    end_date = show.finale_date or date.today()

                    results = scraper.scrape_show_episodes(
                        show,
                        start_date=start_date,
                        end_date=end_date,
                        limit=options['limit'],
                    )

                total_created += results.get('created', 0)
                total_updated += results.get('updated', 0)
                total_errors += results.get('errors', 0)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created: {results.get('created', 0)}, "
                        f"Updated: {results.get('updated', 0)}, "
                        f"Errors: {results.get('errors', 0)}"
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  Error: {e}")
                )
                total_errors += 1

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(self.style.SUCCESS('Backfill Complete'))
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f"  Shows processed: {shows.count()}")
        self.stdout.write(f"  Episodes created: {total_created}")
        self.stdout.write(f"  Episodes updated: {total_updated}")
        self.stdout.write(f"  Errors: {total_errors}")

    def _verify_shows(self, shows, scraper):
        """Verify episode counts against TMDB."""
        self.stdout.write(self.style.SUCCESS('Verifying episode counts...'))
        self.stdout.write('')

        complete = 0
        incomplete = []

        for show in shows:
            if not show.tmdb_id:
                self.stdout.write(f"  {show.name}: No TMDB ID")
                continue

            try:
                results = scraper.verify_episode_count(show)

                if results.get('error'):
                    self.stdout.write(
                        self.style.ERROR(f"  {show.name}: {results['error']}")
                    )
                    continue

                tmdb_count = results['tmdb_count']
                db_count = results['db_count']
                difference = results['difference']

                if results['complete']:
                    complete += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  {show.name}: COMPLETE ({db_count} episodes)"
                        )
                    )
                else:
                    incomplete.append({
                        'show': show,
                        'tmdb_count': tmdb_count,
                        'db_count': db_count,
                        'missing': difference,
                    })
                    self.stdout.write(
                        self.style.WARNING(
                            f"  {show.name}: MISSING {difference} episodes "
                            f"(TMDB: {tmdb_count}, DB: {db_count})"
                        )
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  {show.name}: Error - {e}")
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write('Verification Summary')
        self.stdout.write(self.style.SUCCESS('='*50))
        self.stdout.write(f"  Complete: {complete}")
        self.stdout.write(f"  Incomplete: {len(incomplete)}")

        if incomplete:
            self.stdout.write('')
            self.stdout.write('Shows needing backfill:')
            for item in incomplete:
                self.stdout.write(
                    f"  - {item['show'].name} (missing {item['missing']} episodes)"
                )
            self.stdout.write('')
            self.stdout.write(
                'Run with --all to backfill missing episodes'
            )
