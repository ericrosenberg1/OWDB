"""
Data Cleanup Command.

Finds and removes or fixes malformed data entries.

Usage:
    python manage.py cleanup_data
    python manage.py cleanup_data --dry-run
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from owdb_django.owdbapp.models import Wrestler, Promotion, Title, Event, Match, Venue, Stable


class Command(BaseCommand):
    help = 'Clean up malformed data entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS('\n=== DATA CLEANUP ===\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made\n'))

        total_deleted = 0
        total_fixed = 0

        # Clean up wrestlers
        deleted, fixed = self.cleanup_wrestlers(dry_run)
        total_deleted += deleted
        total_fixed += fixed

        # Clean up promotions
        deleted, fixed = self.cleanup_promotions(dry_run)
        total_deleted += deleted
        total_fixed += fixed

        self.stdout.write(self.style.SUCCESS(f'\n=== CLEANUP COMPLETE ==='))
        self.stdout.write(f'Total entries deleted: {total_deleted}')
        self.stdout.write(f'Total entries fixed: {total_fixed}')

    def cleanup_wrestlers(self, dry_run):
        """Clean up malformed wrestler entries."""
        self.stdout.write('--- Cleaning Wrestlers ---')

        deleted = 0
        fixed = 0

        # Patterns to delete (garbage data)
        garbage_names = ['er', 'ido', 'man', 'The S', 'R', 'Eights', 'DQ', 'Draw', 'No Contest',
                         'Tommy Dreamer vs S', 'Ric Flair (sub for Benoit)']
        truncated_patterns = ['y Orton', 'y Savage', 'y Orton vs']

        # Match entries that should be deleted
        match_entries = [
            'A-Train vs Big Show', 'Damage CTRL vs Carter', 'Darby Allin vs Young Bucks',
            'Diamond Dallas Page vs Jeff Jarrett', 'Hangman Adam Page vs Young Bucks',
            'Hirooki Goto vs Katsuyori Shibata', 'Jazz vs Victoria', 'Kurt Angle vs Chris Jericho',
            'Lex Luger vs Konnan', 'Lucha Brothers vs Private Party', 'New Age Outlaws vs Kane',
            'Raven vs Big Show', 'Roman Reigns vs Seth Rollins', 'Sabu vs Eliminators',
            'Samoa Joe vs Christopher Daniels', 'Seth Rollins vs Roman Reigns',
            'Shane McMahon vs Vince McMahon', 'Tajiri vs Little Guido', 'Tiger Mask vs Bullet Club',
            'Triple H vs John Cena', 'Triple H vs Mankind', 'Triple H vs Shawn Michaels',
            'Young Bucks vs reDRagon'
        ]
        garbage_names.extend(match_entries)

        # Find and delete garbage entries
        for name in garbage_names:
            wrestlers = Wrestler.objects.filter(name=name)
            count = wrestlers.count()
            if count > 0:
                self.stdout.write(f'  Deleting garbage entry: {name} ({count} entries)')
                if not dry_run:
                    wrestlers.delete()
                deleted += count

        # Find and delete truncated entries
        for pattern in truncated_patterns:
            wrestlers = Wrestler.objects.filter(name__startswith=pattern)
            for w in wrestlers:
                self.stdout.write(f'  Deleting truncated entry: {w.name}')
                if not dry_run:
                    w.delete()
                deleted += 1

        # Find entries that are match results or title challenges (not real wrestlers)
        # These should be Match entries, not Wrestler entries
        match_patterns = [
            ' vs ',  # Match results stored as wrestlers
        ]

        for pattern in match_patterns:
            wrestlers = Wrestler.objects.filter(name__contains=pattern)
            for w in wrestlers:
                # Check if it's clearly a match result
                if ' - ' in w.name and 'Championship' in w.name:
                    self.stdout.write(f'  Deleting match+title entry: {w.name}')
                    if not dry_run:
                        w.delete()
                    deleted += 1
                elif w.name.count(' vs ') >= 2:
                    # Multi-person match stored as wrestler
                    self.stdout.write(f'  Deleting multi-match entry: {w.name}')
                    if not dry_run:
                        w.delete()
                    deleted += 1

        # Find title challenge entries that should be in a different table
        title_wrestlers = Wrestler.objects.filter(name__contains=' - ').filter(name__contains='Championship')
        for w in title_wrestlers:
            self.stdout.write(f'  Deleting title entry: {w.name}')
            if not dry_run:
                w.delete()
            deleted += 1

        # Delete roster entries
        roster_entries = ['AEW Roster', 'NJPW Roster', 'NOAH Roster', 'All Japan Roster',
                          'Generic Roster', 'Custom Wrestlers', 'Various', 'Various WWE Legends',
                          'Various WWE Superstars', 'Independent Wrestlers', 'Female Wrestling Cast',
                          'Hip-hop Artists']
        for name in roster_entries:
            wrestlers = Wrestler.objects.filter(name=name)
            count = wrestlers.count()
            if count > 0:
                self.stdout.write(f'  Deleting roster entry: {name}')
                if not dry_run:
                    wrestlers.delete()
                deleted += count

        # Delete battle royal participant entries
        br_entries = Wrestler.objects.filter(name__contains='Battle Royal participants')
        for w in br_entries:
            self.stdout.write(f'  Deleting battle royal entry: {w.name}')
            if not dry_run:
                w.delete()
            deleted += 1

        self.stdout.write(f'  Wrestlers deleted: {deleted}, fixed: {fixed}')
        return deleted, fixed

    def cleanup_promotions(self, dry_run):
        """Clean up malformed promotion entries."""
        self.stdout.write('--- Cleaning Promotions ---')

        deleted = 0
        fixed = 0

        # Specific malformed promotion names
        malformed_names = [
            'Lucha Libre AAA Worldwide (AAA) (2007-present)WWE (2025–present)',
            'Lucha Libre AAA Worldwide (AAA)WWE',
            'Lucha Libre AAA WorldwideWWE',
            'Marvelous That\'s Women Pro WrestlingGaea Japan',
            'NWA Mid-America (1945–1977)Continental Wrestling Association (1977–1988)',
            'Pro Wrestling Zero1Super Fireworks Pro Wrestling',
            'WWEIndependent circuit',
        ]

        for name in malformed_names:
            promotions = Promotion.objects.filter(name=name)
            count = promotions.count()
            if count > 0:
                self.stdout.write(f'  Deleting malformed promotion: {name}')
                if not dry_run:
                    promotions.delete()
                deleted += count

        # Find promotions with concatenated names (multiple promotions in one entry)
        promotions = Promotion.objects.all()
        for p in promotions:
            # Check for concatenated entries (no spaces between promotion names)
            if ')(' in p.name or ')(N' in p.name or 'New Japan' in p.name and 'Universal' in p.name:
                self.stdout.write(f'  Deleting concatenated promotion: {p.name}')
                if not dry_run:
                    p.delete()
                deleted += 1
            # Check for entries with multiple promotion names separated by nothing
            elif p.name.count('Wrestling') >= 2 and len(p.name) > 60:
                self.stdout.write(f'  Deleting multi-promotion entry: {p.name}')
                if not dry_run:
                    p.delete()
                deleted += 1

        self.stdout.write(f'  Promotions deleted: {deleted}, fixed: {fixed}')
        return deleted, fixed
