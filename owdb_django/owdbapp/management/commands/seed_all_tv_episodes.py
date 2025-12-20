"""
Comprehensive seeder for all major wrestling TV shows.

This generates thousands of episodes for Raw, SmackDown, Nitro, Dynamite, NXT, etc.
Episodes are generated programmatically with episode numbers and dates.

Usage:
    python manage.py seed_all_tv_episodes
    python manage.py seed_all_tv_episodes --show=raw
    python manage.py seed_all_tv_episodes --year=1998
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date, timedelta
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed all major wrestling TV show episodes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show',
            type=str,
            help='Only seed specific show (raw, smackdown, nitro, dynamite, nxt, thunder, ecw, impact)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Only seed specific year'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== COMPREHENSIVE TV EPISODE SEEDING ===\n'))

        show = options.get('show')
        year = options.get('year')

        # Get promotions
        self.wwe = Promotion.objects.filter(abbreviation='WWE').first()
        if not self.wwe:
            self.wwe = Promotion.objects.filter(abbreviation='WWF').first()
        if not self.wwe:
            self.wwe = Promotion.objects.create(name='World Wrestling Entertainment', abbreviation='WWE')

        self.wcw = Promotion.objects.filter(abbreviation='WCW').first()
        if not self.wcw:
            self.wcw = Promotion.objects.create(name='World Championship Wrestling', abbreviation='WCW')

        self.aew = Promotion.objects.filter(abbreviation='AEW').first()
        if not self.aew:
            self.aew = Promotion.objects.create(name='All Elite Wrestling', abbreviation='AEW')

        self.ecw = Promotion.objects.filter(abbreviation='ECW').first()
        if not self.ecw:
            self.ecw = Promotion.objects.create(name='Extreme Championship Wrestling', abbreviation='ECW')

        self.tna = Promotion.objects.filter(abbreviation='TNA').first()
        if not self.tna:
            self.tna = Promotion.objects.filter(abbreviation='IMPACT').first()
        if not self.tna:
            self.tna = Promotion.objects.create(name='Total Nonstop Action Wrestling', abbreviation='TNA')

        # Seed shows based on options
        if show is None or show == 'raw':
            self.seed_raw(year)
        if show is None or show == 'smackdown':
            self.seed_smackdown(year)
        if show is None or show == 'nitro':
            self.seed_nitro(year)
        if show is None or show == 'thunder':
            self.seed_thunder(year)
        if show is None or show == 'dynamite':
            self.seed_dynamite(year)
        if show is None or show == 'nxt':
            self.seed_nxt(year)
        if show is None or show == 'ecw':
            self.seed_ecw_tv(year)
        if show is None or show == 'impact':
            self.seed_impact(year)

        self.stdout.write(self.style.SUCCESS('\n=== SEEDING COMPLETE ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')

    def create_episode(self, promotion, show_name, episode_num, air_date, venue_name=None, location=None):
        """Create a single TV episode."""
        name = f"{show_name} #{episode_num}"
        slug = slugify(f"{show_name}-{episode_num}-{air_date}")

        # Check if exists
        if Event.objects.filter(slug=slug).exists():
            return None

        venue = None
        if venue_name:
            venue, _ = Venue.objects.get_or_create(
                name=venue_name,
                defaults={'location': location or ''}
            )

        event = Event.objects.create(
            name=name,
            slug=slug,
            date=air_date,
            promotion=promotion,
            venue=venue,
            about=f"{show_name} Episode {episode_num}, aired {air_date.strftime('%B %d, %Y')}"
        )
        return event

    def seed_raw(self, filter_year=None):
        """Seed WWE Raw episodes (1993-2025)."""
        self.stdout.write('\n--- Seeding WWE Raw (1993-2025) ---')

        # Raw started January 11, 1993 (Monday)
        # Find first Monday of 1993
        start_date = date(1993, 1, 11)
        episode_num = 1
        created = 0

        # Raw venues by era
        venues = [
            ('Manhattan Center', 'New York City, NY'),
            ('Hammerstein Ballroom', 'New York City, NY'),
            ('TD Garden', 'Boston, MA'),
            ('Staples Center', 'Los Angeles, CA'),
            ('United Center', 'Chicago, IL'),
            ('Madison Square Garden', 'New York City, NY'),
            ('Wells Fargo Center', 'Philadelphia, PA'),
            ('Barclays Center', 'Brooklyn, NY'),
            ('American Airlines Arena', 'Miami, FL'),
            ('Allstate Arena', 'Rosemont, IL'),
        ]

        current_date = start_date
        end_date = date(2025, 12, 31)

        while current_date <= end_date:
            year = current_date.year

            # Skip if filtering by year
            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            # Pick a venue (rotate)
            venue_name, location = venues[episode_num % len(venues)]

            # Determine show name by era
            if year < 1997:
                show_name = "Monday Night Raw"
            elif year < 2002:
                show_name = "Raw is War"
            elif year < 2012:
                show_name = "Monday Night Raw"
            else:
                show_name = "WWE Raw"

            event = self.create_episode(
                self.wwe, show_name, episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            # Move to next Monday
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Raw episodes (Episode #{episode_num - 1} total)'))

    def seed_smackdown(self, filter_year=None):
        """Seed WWE SmackDown episodes (1999-2025)."""
        self.stdout.write('\n--- Seeding WWE SmackDown (1999-2025) ---')

        # SmackDown pilot April 29, 1999, regular series August 26, 1999 (Thursday)
        # Moved to Friday in 2005, back to Thursday briefly, then Friday again
        start_date = date(1999, 8, 26)
        episode_num = 1
        created = 0

        venues = [
            ('Staples Center', 'Los Angeles, CA'),
            ('TD Garden', 'Boston, MA'),
            ('Madison Square Garden', 'New York City, NY'),
            ('American Airlines Center', 'Dallas, TX'),
            ('Toyota Center', 'Houston, TX'),
            ('Amway Center', 'Orlando, FL'),
            ('KeyBank Center', 'Buffalo, NY'),
            ('Capital One Arena', 'Washington, DC'),
        ]

        current_date = start_date
        end_date = date(2025, 12, 31)

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            # Show name by era
            if year < 2016:
                show_name = "WWE SmackDown"
            else:
                show_name = "WWE SmackDown Live"

            event = self.create_episode(
                self.wwe, show_name, episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} SmackDown episodes'))

    def seed_nitro(self, filter_year=None):
        """Seed WCW Monday Nitro episodes (1995-2001)."""
        self.stdout.write('\n--- Seeding WCW Monday Nitro (1995-2001) ---')

        # Nitro started September 4, 1995 (Monday)
        start_date = date(1995, 9, 4)
        end_date = date(2001, 3, 26)  # Final Nitro
        episode_num = 1
        created = 0

        venues = [
            ('Mall of America', 'Bloomington, MN'),
            ('Georgia Dome', 'Atlanta, GA'),
            ('United Center', 'Chicago, IL'),
            ('America West Arena', 'Phoenix, AZ'),
            ('Thomas & Mack Center', 'Las Vegas, NV'),
            ('Omni Coliseum', 'Atlanta, GA'),
            ('Baltimore Arena', 'Baltimore, MD'),
            ('Philadelphia Spectrum', 'Philadelphia, PA'),
        ]

        current_date = start_date

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            event = self.create_episode(
                self.wcw, "WCW Monday Nitro", episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Nitro episodes'))

    def seed_thunder(self, filter_year=None):
        """Seed WCW Thunder episodes (1998-2001)."""
        self.stdout.write('\n--- Seeding WCW Thunder (1998-2001) ---')

        # Thunder started January 8, 1998 (Thursday)
        start_date = date(1998, 1, 8)
        end_date = date(2001, 3, 21)
        episode_num = 1
        created = 0

        venues = [
            ('UTC Arena', 'Chattanooga, TN'),
            ('Mobile Civic Center', 'Mobile, AL'),
            ('Mississippi Coast Coliseum', 'Biloxi, MS'),
            ('Von Braun Center', 'Huntsville, AL'),
            ('Birmingham-Jefferson Civic Center', 'Birmingham, AL'),
        ]

        current_date = start_date

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            event = self.create_episode(
                self.wcw, "WCW Thunder", episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Thunder episodes'))

    def seed_dynamite(self, filter_year=None):
        """Seed AEW Dynamite episodes (2019-2025)."""
        self.stdout.write('\n--- Seeding AEW Dynamite (2019-2025) ---')

        # Dynamite started October 2, 2019 (Wednesday)
        start_date = date(2019, 10, 2)
        episode_num = 1
        created = 0

        venues = [
            ('Daily\'s Place', 'Jacksonville, FL'),
            ('Sears Centre', 'Hoffman Estates, IL'),
            ('Agganis Arena', 'Boston, MA'),
            ('Chesapeake Energy Arena', 'Oklahoma City, OK'),
            ('Target Center', 'Minneapolis, MN'),
            ('CFG Bank Arena', 'Baltimore, MD'),
            ('NOW Arena', 'Hoffman Estates, IL'),
            ('UBS Arena', 'Elmont, NY'),
        ]

        current_date = start_date
        end_date = date(2025, 12, 31)

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            event = self.create_episode(
                self.aew, "AEW Dynamite", episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Dynamite episodes'))

    def seed_nxt(self, filter_year=None):
        """Seed WWE NXT episodes (2010-2025)."""
        self.stdout.write('\n--- Seeding WWE NXT (2010-2025) ---')

        # NXT started February 23, 2010 (Tuesday), later moved to Wednesday
        start_date = date(2010, 2, 23)
        episode_num = 1
        created = 0

        venues = [
            ('Full Sail University', 'Winter Park, FL'),
            ('Capitol Wrestling Center', 'Orlando, FL'),
            ('NXT Arena', 'Orlando, FL'),
            ('Performance Center', 'Orlando, FL'),
        ]

        current_date = start_date
        end_date = date(2025, 12, 31)

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            # Show name by era
            if year < 2021:
                show_name = "WWE NXT"
            else:
                show_name = "NXT 2.0" if year < 2023 else "WWE NXT"

            event = self.create_episode(
                self.wwe, show_name, episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} NXT episodes'))

    def seed_ecw_tv(self, filter_year=None):
        """Seed ECW Hardcore TV episodes (1993-2001)."""
        self.stdout.write('\n--- Seeding ECW Hardcore TV (1993-2001) ---')

        # ECW TV started in 1993
        start_date = date(1993, 4, 6)
        end_date = date(2001, 1, 13)
        episode_num = 1
        created = 0

        venues = [
            ('ECW Arena', 'Philadelphia, PA'),
            ('Lost Battalion Hall', 'Queens, NY'),
            ('Elks Lodge', 'Queens, NY'),
            ('Madhouse of Extreme', 'Philadelphia, PA'),
        ]

        current_date = start_date

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            event = self.create_episode(
                self.ecw, "ECW Hardcore TV", episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} ECW TV episodes'))

    def seed_impact(self, filter_year=None):
        """Seed TNA/Impact Wrestling episodes (2004-2025)."""
        self.stdout.write('\n--- Seeding TNA/Impact Wrestling (2004-2025) ---')

        # Impact started June 4, 2004 (Friday on Fox Sports Net)
        start_date = date(2004, 6, 4)
        episode_num = 1
        created = 0

        venues = [
            ('TNA Asylum', 'Nashville, TN'),
            ('Universal Studios', 'Orlando, FL'),
            ('Impact Zone', 'Orlando, FL'),
            ('Impact Wrestling Zone', 'Orlando, FL'),
            ('Sam\'s Town Hotel', 'Las Vegas, NV'),
        ]

        current_date = start_date
        end_date = date(2025, 12, 31)

        while current_date <= end_date:
            year = current_date.year

            if filter_year and year != filter_year:
                current_date += timedelta(days=7)
                episode_num += 1
                continue

            venue_name, location = venues[episode_num % len(venues)]

            # Show name by era
            if year < 2011:
                show_name = "TNA iMPACT!"
            elif year < 2017:
                show_name = "Impact Wrestling"
            else:
                show_name = "IMPACT!"

            event = self.create_episode(
                self.tna, show_name, episode_num, current_date, venue_name, location
            )
            if event:
                created += 1

            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Impact episodes'))
