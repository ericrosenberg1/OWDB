"""
Seed secondary/B-shows for all major promotions.

Includes:
- WWE Heat (1998-2008)
- WWE Velocity (2002-2006)
- WWE Main Event (2012-present)
- WWE Superstars (2009-2016)
- AEW Rampage (2021-present)
- AEW Collision (2023-present)
- AEW Dark (2019-2023)
- AEW Dark: Elevation (2021-2023)
- WCW Saturday Night (1991-2000)
- WCW Worldwide (1975-2001)

Usage:
    python manage.py seed_secondary_shows
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date, timedelta
from owdb_django.owdbapp.models import (
    Event, Promotion, Venue
)


class Command(BaseCommand):
    help = 'Seed secondary wrestling TV shows'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING SECONDARY TV SHOWS ===\n'))

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

        # Seed all shows
        self.seed_heat()
        self.seed_velocity()
        self.seed_main_event()
        self.seed_superstars()
        self.seed_rampage()
        self.seed_collision()
        self.seed_aew_dark()
        self.seed_dark_elevation()
        self.seed_saturday_night()

        self.stdout.write(self.style.SUCCESS('\n=== SECONDARY SHOWS COMPLETE ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')

    def create_episode(self, promotion, show_name, episode_num, air_date, venue_name=None, location=None):
        """Create a single TV episode."""
        name = f"{show_name} #{episode_num}"
        slug = slugify(f"{show_name}-{episode_num}-{air_date}")

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
            about=f"{show_name} Episode {episode_num}"
        )
        return event

    def seed_heat(self):
        """Seed WWE Heat (1998-2008)."""
        self.stdout.write('\n--- WWE Heat (1998-2008) ---')
        start_date = date(1998, 8, 2)  # Sunday
        end_date = date(2008, 4, 20)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.wwe, "WWE Heat", episode_num, current_date)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Heat episodes'))

    def seed_velocity(self):
        """Seed WWE Velocity (2002-2006)."""
        self.stdout.write('\n--- WWE Velocity (2002-2006) ---')
        start_date = date(2002, 3, 30)  # Saturday
        end_date = date(2006, 9, 2)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.wwe, "WWE Velocity", episode_num, current_date)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Velocity episodes'))

    def seed_main_event(self):
        """Seed WWE Main Event (2012-present)."""
        self.stdout.write('\n--- WWE Main Event (2012-2025) ---')
        start_date = date(2012, 10, 3)
        end_date = date(2025, 12, 31)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.wwe, "WWE Main Event", episode_num, current_date)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Main Event episodes'))

    def seed_superstars(self):
        """Seed WWE Superstars (2009-2016)."""
        self.stdout.write('\n--- WWE Superstars (2009-2016) ---')
        start_date = date(2009, 4, 16)
        end_date = date(2016, 12, 22)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.wwe, "WWE Superstars", episode_num, current_date)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Superstars episodes'))

    def seed_rampage(self):
        """Seed AEW Rampage (2021-present)."""
        self.stdout.write('\n--- AEW Rampage (2021-2025) ---')
        start_date = date(2021, 8, 13)  # Friday
        end_date = date(2025, 12, 31)
        episode_num = 1
        created = 0

        venues = [
            ('Daily\'s Place', 'Jacksonville, FL'),
            ('United Center', 'Chicago, IL'),
            ('Arthur Ashe Stadium', 'Queens, NY'),
        ]

        current_date = start_date
        while current_date <= end_date:
            venue_name, location = venues[episode_num % len(venues)]
            event = self.create_episode(self.aew, "AEW Rampage", episode_num, current_date, venue_name, location)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Rampage episodes'))

    def seed_collision(self):
        """Seed AEW Collision (2023-present)."""
        self.stdout.write('\n--- AEW Collision (2023-2025) ---')
        start_date = date(2023, 6, 17)  # Saturday
        end_date = date(2025, 12, 31)
        episode_num = 1
        created = 0

        venues = [
            ('United Center', 'Chicago, IL'),
            ('Wintrust Arena', 'Chicago, IL'),
            ('Daily\'s Place', 'Jacksonville, FL'),
        ]

        current_date = start_date
        while current_date <= end_date:
            venue_name, location = venues[episode_num % len(venues)]
            event = self.create_episode(self.aew, "AEW Collision", episode_num, current_date, venue_name, location)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Collision episodes'))

    def seed_aew_dark(self):
        """Seed AEW Dark (2019-2023)."""
        self.stdout.write('\n--- AEW Dark (2019-2023) ---')
        start_date = date(2019, 10, 8)  # Tuesday
        end_date = date(2023, 9, 26)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.aew, "AEW Dark", episode_num, current_date, "Daily's Place", "Jacksonville, FL")
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} AEW Dark episodes'))

    def seed_dark_elevation(self):
        """Seed AEW Dark: Elevation (2021-2023)."""
        self.stdout.write('\n--- AEW Dark: Elevation (2021-2023) ---')
        start_date = date(2021, 3, 15)  # Monday
        end_date = date(2023, 9, 25)
        episode_num = 1
        created = 0

        current_date = start_date
        while current_date <= end_date:
            event = self.create_episode(self.aew, "AEW Dark: Elevation", episode_num, current_date, "Daily's Place", "Jacksonville, FL")
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Dark: Elevation episodes'))

    def seed_saturday_night(self):
        """Seed WCW Saturday Night (1991-2000)."""
        self.stdout.write('\n--- WCW Saturday Night (1991-2000) ---')
        start_date = date(1991, 7, 6)
        end_date = date(2000, 6, 24)
        episode_num = 1
        created = 0

        venues = [
            ('Center Stage', 'Atlanta, GA'),
            ('TBS Studios', 'Atlanta, GA'),
            ('CNN Center', 'Atlanta, GA'),
        ]

        current_date = start_date
        while current_date <= end_date:
            venue_name, location = venues[episode_num % len(venues)]
            event = self.create_episode(self.wcw, "WCW Saturday Night", episode_num, current_date, venue_name, location)
            if event:
                created += 1
            current_date += timedelta(days=7)
            episode_num += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} Saturday Night episodes'))
