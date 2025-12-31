"""
Seed death dates for known deceased wrestlers.

This enables WrestleBot to detect synthetic/impossible events where
deceased wrestlers are shown participating in matches after their death.

Usage:
    python manage.py seed_deceased_wrestlers
    python manage.py seed_deceased_wrestlers --dry-run
"""
from django.core.management.base import BaseCommand
from datetime import date
from owdb_django.owdbapp.models import Wrestler


class Command(BaseCommand):
    help = 'Seed death dates for known deceased wrestlers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('\n=== DRY RUN - No changes will be made ===\n'))
        else:
            self.stdout.write(self.style.SUCCESS('\n=== Seeding Deceased Wrestler Data ===\n'))

        # Notable deceased wrestlers with their death dates
        # Format: (name/aliases to search for, death_date, optional real_name for disambiguation)
        deceased_wrestlers = [
            # Golden Era / Legends
            ('Randy Savage', date(2011, 5, 20), 'Macho Man'),
            ('Macho Man Randy Savage', date(2011, 5, 20), None),
            ('Andre the Giant', date(1993, 1, 27), 'Andre Rene Roussimoff'),
            ('Roddy Piper', date(2015, 7, 31), 'Rowdy Roddy Piper'),
            ('Rowdy Roddy Piper', date(2015, 7, 31), None),
            ('Ultimate Warrior', date(2014, 4, 8), 'James Brian Hellwig'),
            ('Dusty Rhodes', date(2015, 6, 11), 'Virgil Runnels'),
            ('Gorilla Monsoon', date(1999, 10, 6), 'Robert Marella'),
            ('Big Boss Man', date(2004, 9, 22), 'Ray Traylor'),
            ('Mr. Perfect', date(2003, 2, 10), 'Curt Hennig'),
            ('Curt Hennig', date(2003, 2, 10), None),
            ('Earthquake', date(2006, 6, 7), 'John Tenta'),
            ('Yokozuna', date(2000, 10, 23), 'Rodney Anoa\'i'),
            ('Big John Studd', date(1995, 3, 20), 'John Minton'),
            ('Junkyard Dog', date(1998, 6, 1), 'Sylvester Ritter'),
            ('Hawk', date(2003, 10, 19), 'Road Warrior Hawk'),
            ('Road Warrior Hawk', date(2003, 10, 19), None),
            ('Miss Elizabeth', date(2003, 5, 1), 'Elizabeth Hulette'),
            ('Sensational Sherri', date(2007, 6, 15), 'Sherri Martel'),
            ('Sherri Martel', date(2007, 6, 15), None),
            ('Luna Vachon', date(2010, 8, 27), 'Gertrude Vachon'),
            ('Chyna', date(2016, 4, 20), 'Joan Laurer'),

            # 1990s-2000s Era
            ('Owen Hart', date(1999, 5, 23), None),
            ('Eddie Guerrero', date(2005, 11, 13), 'Eduardo Guerrero'),
            ('Chris Benoit', date(2007, 6, 24), None),
            ('Brian Pillman', date(1997, 10, 5), None),
            ('Rick Rude', date(1999, 4, 20), 'Ravishing Rick Rude'),
            ('Ravishing Rick Rude', date(1999, 4, 20), None),
            ('Test', date(2009, 3, 13), 'Andrew Martin'),
            ('Andrew Test Martin', date(2009, 3, 13), None),
            ('Crash Holly', date(2003, 11, 6), 'Mike Lockwood'),
            ('Umaga', date(2009, 12, 4), 'Edward Fatu'),
            ('Lance Cade', date(2010, 8, 13), 'Lance McNaught'),
            ('Viscera', date(2014, 2, 18), 'Nelson Frazier Jr'),
            ('Big Daddy V', date(2014, 2, 18), None),
            ('Bam Bam Bigelow', date(2007, 1, 19), 'Scott Bigelow'),
            ('Crush', date(2007, 8, 13), 'Brian Adams'),
            ('Road Warrior Animal', date(2020, 9, 22), 'Joseph Laurinaitis'),
            ('Animal', date(2020, 9, 22), None),
            ('Pat Patterson', date(2020, 12, 2), 'Pierre Clemont'),
            ('Howard Finkel', date(2020, 4, 16), None),
            ('Mean Gene Okerlund', date(2019, 1, 2), 'Eugene Okerlund'),

            # More Recent Deaths
            ('Brodie Lee', date(2020, 12, 26), 'Jonathan Huber'),
            ('Luke Harper', date(2020, 12, 26), None),
            ('Scott Hall', date(2022, 3, 14), 'Razor Ramon'),
            ('Razor Ramon', date(2022, 3, 14), None),
            ('New Jack', date(2021, 5, 14), 'Jerome Young'),
            ('Jon Huber', date(2020, 12, 26), None),
            ('Shad Gaspard', date(2020, 5, 17), 'Shad Gaspard'),
            ('Hana Kimura', date(2020, 5, 23), None),
            ('Rocky Johnson', date(2020, 1, 15), None),
            ('Daffney', date(2021, 9, 2), 'Shannon Spruill'),
            ('Jay Briscoe', date(2023, 1, 17), 'Jamin Pugh'),
            ('Bray Wyatt', date(2023, 8, 24), 'Windham Rotunda'),
            ('Windham Rotunda', date(2023, 8, 24), None),
            ('Terry Funk', date(2023, 8, 23), None),
            ('Bobby Eaton', date(2021, 8, 4), None),
            ('Tracy Smothers', date(2020, 10, 28), None),
            ('Vader', date(2018, 6, 18), 'Leon White'),
            ('Big Van Vader', date(2018, 6, 18), None),
            ('King Kong Bundy', date(2019, 3, 4), 'Christopher Pallies'),
            ('Nikolai Volkoff', date(2018, 7, 29), 'Josip Peruzovic'),
            ('Jimmy Snuka', date(2017, 1, 15), 'Superfly Jimmy Snuka'),
            ('Superfly Jimmy Snuka', date(2017, 1, 15), None),
            ('George The Animal Steele', date(2017, 2, 16), 'Jim Myers'),
            ('Bruno Sammartino', date(2018, 4, 18), None),
            ('Axl Rotten', date(2016, 2, 4), 'Brian Knighton'),
            ('Balls Mahoney', date(2016, 4, 12), 'Jonathan Rechner'),
            ('Nicole Bass', date(2017, 2, 16), None),
            ('Buddy Rogers', date(1992, 6, 26), None),
            ('Lou Thesz', date(2002, 4, 28), None),
            ('Harley Race', date(2019, 8, 1), None),
            ('Wahoo McDaniel', date(2002, 4, 18), None),
            ('Bruiser Brody', date(1988, 7, 17), 'Frank Goodish'),
            ('Adrian Adonis', date(1988, 7, 4), 'Keith Franke'),
            ('Dino Bravo', date(1993, 3, 10), 'Adolfo Bresciano'),
            ('British Bulldog', date(2002, 5, 18), 'Davey Boy Smith'),
            ('Davey Boy Smith', date(2002, 5, 18), None),
            ('Kerry Von Erich', date(1993, 2, 18), 'Kerry Adkisson'),
            ('Kevin Von Erich', None, None),  # Skip - still alive
            ('David Von Erich', date(1984, 2, 10), 'David Adkisson'),
            ('Mike Von Erich', date(1987, 4, 12), 'Michael Adkisson'),
            ('Chris Von Erich', date(1991, 9, 12), 'Christopher Adkisson'),
            ('Giant Baba', date(1999, 1, 31), 'Shohei Baba'),
            ('Dynamite Kid', date(2018, 12, 5), 'Tom Billington'),
            ('Larry Sweeney', date(2011, 4, 11), None),
            ('Chris Kanyon', date(2010, 4, 2), 'Chris Klucsarits'),
            ('Kanyon', date(2010, 4, 2), None),

            # ECW Notables
            ('Tommy Dreamer', None, None),  # Skip - still alive
            ('Sabu', None, None),  # Skip - still alive
            ('Sandman', None, None),  # Skip - still alive
            ('Mass Transit', date(2002, 11, 15), 'Eric Kulas'),
            ('Louie Spicolli', date(1998, 2, 15), 'Louis Mucciolo'),
            ('Big Dick Dudley', date(2002, 5, 16), 'Alex Rizzo'),
            ('Rocco Rock', date(2002, 9, 21), 'Ted Petty'),

            # International
            ('Giant Haystacks', date(1998, 11, 29), 'Martin Ruane'),
            ('Kenta Kobashi', None, None),  # Skip - still alive
            ('Mitsuharu Misawa', date(2009, 6, 13), None),
            ('Jumbo Tsuruta', date(2000, 5, 13), None),
            ('Stan Hansen', None, None),  # Skip - still alive
            ('Hayabusa', date(2016, 3, 3), 'Eiji Ezaki'),
        ]

        updated = 0
        not_found = []
        already_set = 0
        skipped = 0

        for wrestler_name, death_date, alt_name in deceased_wrestlers:
            # Skip entries with no death date (used to mark people as alive)
            if death_date is None:
                skipped += 1
                continue

            # Try to find the wrestler
            wrestler = None

            # Try exact name match first
            try:
                wrestler = Wrestler.objects.get(name__iexact=wrestler_name)
            except Wrestler.DoesNotExist:
                # Try case-insensitive contains match
                matches = Wrestler.objects.filter(name__icontains=wrestler_name)
                if matches.count() == 1:
                    wrestler = matches.first()
                elif matches.count() > 1 and alt_name:
                    # Try to narrow down with alt_name
                    for m in matches:
                        if alt_name.lower() in (m.real_name or '').lower() or \
                           alt_name.lower() in (m.name or '').lower():
                            wrestler = m
                            break
            except Wrestler.MultipleObjectsReturned:
                # Try to disambiguate with alt_name
                if alt_name:
                    matches = Wrestler.objects.filter(name__icontains=wrestler_name)
                    for m in matches:
                        if alt_name.lower() in (m.real_name or '').lower() or \
                           alt_name.lower() in (m.name or '').lower():
                            wrestler = m
                            break

            if wrestler is None:
                not_found.append(wrestler_name)
                continue

            # Check if death_date already set
            if wrestler.death_date:
                already_set += 1
                self.stdout.write(f"  Already set: {wrestler.name} (death: {wrestler.death_date})")
                continue

            # Update the wrestler
            if not dry_run:
                wrestler.death_date = death_date
                wrestler.save(update_fields=['death_date'])

            updated += 1
            self.stdout.write(self.style.SUCCESS(
                f"  {'Would update' if dry_run else 'Updated'}: {wrestler.name} - death date: {death_date}"
            ))

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f"\n{'Would update' if dry_run else 'Updated'}: {updated} wrestlers"))
        self.stdout.write(f"Already had death date: {already_set}")
        self.stdout.write(f"Skipped (still alive): {skipped}")

        if not_found:
            self.stdout.write(self.style.WARNING(f"\nNot found in database ({len(not_found)}):"))
            for name in not_found[:20]:  # Show first 20
                self.stdout.write(f"  - {name}")
            if len(not_found) > 20:
                self.stdout.write(f"  ... and {len(not_found) - 20} more")

        self.stdout.write('')
