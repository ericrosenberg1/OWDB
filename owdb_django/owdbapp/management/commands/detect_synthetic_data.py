"""
Detect and delete synthetic/impossible event data.

This command finds events that are clearly fabricated:
- Future events with deceased wrestlers (e.g., Randy Savage in 2025)
- Events with impossible era combinations
- Far-future events with suspicious name patterns

Usage:
    # Dry run (show what would be deleted)
    python manage.py detect_synthetic_data

    # Actually delete synthetic events
    python manage.py detect_synthetic_data --delete

    # Include name pattern detection
    python manage.py detect_synthetic_data --delete --include-patterns
"""
from django.core.management.base import BaseCommand
from owdb_django.owdbapp.wrestlebot.quality import DataCleaner


class Command(BaseCommand):
    help = 'Detect and delete synthetic/impossible event data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Actually delete synthetic events (default is dry run)',
        )
        parser.add_argument(
            '--include-patterns',
            action='store_true',
            help='Also delete events matching suspicious name patterns (e.g., WWE Raw #NNNN in far future)',
        )
        parser.add_argument(
            '--all-events',
            action='store_true',
            help='Check all events (not just future events) - use with caution',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output for each event',
        )

    def handle(self, *args, **options):
        dry_run = not options['delete']
        include_patterns = options['include_patterns']
        all_events = options['all_events']
        verbose = options['verbose']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No changes will be made ===\n'))
        else:
            self.stdout.write(self.style.ERROR('\n=== LIVE MODE - Events will be DELETED ===\n'))

        cleaner = DataCleaner()

        # First, detect and optionally delete synthetic events (deceased wrestlers, era issues)
        self.stdout.write(self.style.SUCCESS('=== Detecting Synthetic Events (Deceased Wrestlers, Era Issues) ===\n'))

        results = cleaner.find_and_delete_synthetic_events(
            dry_run=dry_run,
            include_future_only=not all_events
        )

        self.stdout.write(f"Events checked: {results['events_checked']}")
        self.stdout.write(f"Synthetic events found: {results['synthetic_found']}")

        if dry_run:
            self.stdout.write(f"Would delete: {results['synthetic_found']} events")
        else:
            self.stdout.write(self.style.SUCCESS(f"Deleted: {results['events_deleted']} events, {results['matches_deleted']} matches"))

        if verbose and results['deleted_events']:
            self.stdout.write('\nEvents to delete:')
            for event in results['deleted_events'][:20]:  # Limit output
                self.stdout.write(f"  - {event['name']} ({event['date']})")
                for issue in event.get('issues', []):
                    self.stdout.write(f"    Issue: {issue}")

            if len(results['deleted_events']) > 20:
                self.stdout.write(f"  ... and {len(results['deleted_events']) - 20} more")

        # Optionally, also detect by name pattern
        if include_patterns:
            self.stdout.write(self.style.SUCCESS('\n=== Detecting Suspicious Name Patterns in Future ===\n'))

            pattern_results = cleaner.detect_synthetic_by_name_pattern(dry_run=dry_run)

            self.stdout.write(f"Events checked: {pattern_results['events_checked']}")
            self.stdout.write(f"Suspicious events found: {pattern_results['suspicious_found']}")

            if dry_run:
                self.stdout.write(f"Would delete: {pattern_results['suspicious_found']} events")
            else:
                self.stdout.write(self.style.SUCCESS(
                    f"Deleted: {pattern_results['events_deleted']} events, {pattern_results['matches_deleted']} matches"
                ))

            if verbose and pattern_results['deleted_events']:
                self.stdout.write('\nEvents to delete:')
                for event in pattern_results['deleted_events'][:20]:
                    self.stdout.write(f"  - {event['name']} ({event['date']})")

                if len(pattern_results['deleted_events']) > 20:
                    self.stdout.write(f"  ... and {len(pattern_results['deleted_events']) - 20} more")

        # Summary
        self.stdout.write('\n' + '=' * 50)

        total_found = results['synthetic_found']
        total_deleted = results['events_deleted']
        if include_patterns:
            total_found += pattern_results['suspicious_found']
            total_deleted += pattern_results['events_deleted']

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f'\nDRY RUN COMPLETE: Would delete {total_found} synthetic events'
            ))
            self.stdout.write(self.style.WARNING(
                'Run with --delete to actually remove these events'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f'\nDELETION COMPLETE: Removed {total_deleted} synthetic events'))

        self.stdout.write('')
