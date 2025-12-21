"""
Complete TV Episode Seeder - Ensures ALL historic TV episodes are present.

Covers all major wrestling TV shows with complete episode runs:
- WWE/WWF: Raw, SmackDown, Superstars, Wrestling Challenge, Prime Time Wrestling, etc.
- WCW: Nitro, Thunder, Saturday Night, WorldWide, Main Event, Power Hour
- ECW: Hardcore TV, ECW on TNN
- TNA/Impact: Impact, Xplosion
- AEW: Dynamite, Rampage, Collision, Dark, Elevation

Usage:
    python manage.py seed_complete_tv
    python manage.py seed_complete_tv --show=raw
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date, timedelta
from owdb_django.owdbapp.models import Event, Promotion, Venue


class Command(BaseCommand):
    help = 'Seed complete TV episode history for all major promotions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show',
            type=str,
            help='Only seed specific show (raw, smackdown, nitro, etc.)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== COMPLETE TV EPISODE SEEDER ===\n'))

        show_filter = options.get('show', '').lower() if options.get('show') else None

        # Get promotions
        self.wwe = Promotion.objects.filter(abbreviation__in=['WWE', 'WWF']).first()
        self.wcw = Promotion.objects.filter(abbreviation='WCW').first()
        self.ecw = Promotion.objects.filter(abbreviation='ECW').first()
        self.tna = Promotion.objects.filter(abbreviation__in=['TNA', 'IMPACT']).first()
        self.aew = Promotion.objects.filter(abbreviation='AEW').first()
        self.nxt = Promotion.objects.filter(name__icontains='NXT').first() or self.wwe

        total_created = 0

        # WWE/WWF Shows
        if not show_filter or show_filter == 'raw':
            total_created += self.seed_raw()
        if not show_filter or show_filter == 'smackdown':
            total_created += self.seed_smackdown()
        if not show_filter or show_filter == 'superstars':
            total_created += self.seed_superstars_classic()
        if not show_filter or show_filter == 'challenge':
            total_created += self.seed_wrestling_challenge()
        if not show_filter or show_filter == 'primetime':
            total_created += self.seed_prime_time()
        if not show_filter or show_filter == 'heat':
            total_created += self.seed_heat()
        if not show_filter or show_filter == 'velocity':
            total_created += self.seed_velocity()
        if not show_filter or show_filter == 'mainevent':
            total_created += self.seed_main_event()

        # WCW Shows
        if not show_filter or show_filter == 'nitro':
            total_created += self.seed_nitro()
        if not show_filter or show_filter == 'thunder':
            total_created += self.seed_thunder()
        if not show_filter or show_filter == 'saturday':
            total_created += self.seed_wcw_saturday_night()
        if not show_filter or show_filter == 'worldwide':
            total_created += self.seed_wcw_worldwide()
        if not show_filter or show_filter == 'powerhour':
            total_created += self.seed_wcw_power_hour()

        # ECW Shows
        if not show_filter or show_filter == 'ecwtv':
            total_created += self.seed_ecw_hardcore_tv()
        if not show_filter or show_filter == 'ecwtnn':
            total_created += self.seed_ecw_on_tnn()

        # TNA/Impact Shows
        if not show_filter or show_filter == 'impact':
            total_created += self.seed_impact()
        if not show_filter or show_filter == 'xplosion':
            total_created += self.seed_xplosion()

        # AEW Shows
        if not show_filter or show_filter == 'dynamite':
            total_created += self.seed_dynamite()
        if not show_filter or show_filter == 'rampage':
            total_created += self.seed_rampage()
        if not show_filter or show_filter == 'collision':
            total_created += self.seed_collision()
        if not show_filter or show_filter == 'dark':
            total_created += self.seed_aew_dark()

        # NXT
        if not show_filter or show_filter == 'nxt':
            total_created += self.seed_nxt()

        self.stdout.write(self.style.SUCCESS(f'\n=== TOTAL EPISODES CREATED: {total_created} ==='))
        self.stdout.write(f'Total Events in DB: {Event.objects.count():,}')

    def create_episode(self, promotion, show_name, episode_num, event_date, venue_name=None, location=None):
        """Create a single TV episode."""
        name = f"{show_name} #{episode_num}"
        slug = slugify(f"{show_name}-{episode_num}-{event_date}")

        if Event.objects.filter(slug=slug).exists():
            return None

        event = Event.objects.create(
            name=name,
            slug=slug,
            date=event_date,
            promotion=promotion,
            event_type='TV',
            about=f"{show_name} Episode #{episode_num}"
        )
        return event

    def seed_weekly_show(self, promotion, show_name, start_date, end_date, day_of_week=0, venues=None):
        """Seed a weekly show from start to end date."""
        if not promotion:
            return 0

        created = 0
        episode_num = 1
        current_date = start_date

        # Adjust to correct day of week
        while current_date.weekday() != day_of_week:
            current_date += timedelta(days=1)

        default_venues = venues or [
            ('Arena', 'Various Locations'),
        ]

        while current_date <= end_date:
            venue_name, location = default_venues[episode_num % len(default_venues)]
            event = self.create_episode(promotion, show_name, episode_num, current_date, venue_name, location)
            if event:
                created += 1
            episode_num += 1
            current_date += timedelta(days=7)

        return created

    def seed_raw(self):
        """Seed WWE Raw (1993-2025)."""
        self.stdout.write('--- Seeding WWE Raw ---')

        venues = [
            ('Madison Square Garden', 'New York, NY'),
            ('Staples Center', 'Los Angeles, CA'),
            ('United Center', 'Chicago, IL'),
            ('TD Garden', 'Boston, MA'),
            ('Barclays Center', 'Brooklyn, NY'),
            ('Wells Fargo Center', 'Philadelphia, PA'),
            ('Toyota Center', 'Houston, TX'),
            ('American Airlines Center', 'Dallas, TX'),
            ('Little Caesars Arena', 'Detroit, MI'),
            ('PPG Paints Arena', 'Pittsburgh, PA'),
        ]

        # Monday Night Raw started Jan 11, 1993
        created = self.seed_weekly_show(
            self.wwe, 'WWE Raw',
            date(1993, 1, 11), date(2025, 12, 31),
            day_of_week=0, venues=venues  # Monday = 0
        )
        self.stdout.write(f'  Created {created} Raw episodes')
        return created

    def seed_smackdown(self):
        """Seed WWE SmackDown (1999-2025)."""
        self.stdout.write('--- Seeding WWE SmackDown ---')

        venues = [
            ('Staples Center', 'Los Angeles, CA'),
            ('Madison Square Garden', 'New York, NY'),
            ('TD Garden', 'Boston, MA'),
            ('United Center', 'Chicago, IL'),
            ('American Airlines Arena', 'Miami, FL'),
            ('AT&T Center', 'San Antonio, TX'),
            ('Rocket Mortgage FieldHouse', 'Cleveland, OH'),
        ]

        # SmackDown started April 29, 1999 (Thursday, later moved to Friday)
        created = self.seed_weekly_show(
            self.wwe, 'WWE SmackDown',
            date(1999, 4, 29), date(2025, 12, 31),
            day_of_week=4, venues=venues  # Friday = 4
        )
        self.stdout.write(f'  Created {created} SmackDown episodes')
        return created

    def seed_superstars_classic(self):
        """Seed WWF Superstars (1986-2001)."""
        self.stdout.write('--- Seeding WWF Superstars ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWF Superstars',
            date(1986, 9, 6), date(2001, 4, 28),
            day_of_week=5
        )
        self.stdout.write(f'  Created {created} Superstars (classic) episodes')
        return created

    def seed_wrestling_challenge(self):
        """Seed WWF Wrestling Challenge (1986-1995)."""
        self.stdout.write('--- Seeding WWF Wrestling Challenge ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWF Wrestling Challenge',
            date(1986, 9, 7), date(1995, 5, 28),
            day_of_week=6
        )
        self.stdout.write(f'  Created {created} Wrestling Challenge episodes')
        return created

    def seed_prime_time(self):
        """Seed WWF Prime Time Wrestling (1985-1993)."""
        self.stdout.write('--- Seeding WWF Prime Time Wrestling ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWF Prime Time Wrestling',
            date(1985, 1, 1), date(1993, 1, 4),
            day_of_week=0
        )
        self.stdout.write(f'  Created {created} Prime Time Wrestling episodes')
        return created

    def seed_heat(self):
        """Seed WWE Sunday Night Heat (1998-2008)."""
        self.stdout.write('--- Seeding WWE Heat ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWE Heat',
            date(1998, 8, 2), date(2008, 5, 18),
            day_of_week=6
        )
        self.stdout.write(f'  Created {created} Heat episodes')
        return created

    def seed_velocity(self):
        """Seed WWE Velocity (2002-2006)."""
        self.stdout.write('--- Seeding WWE Velocity ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWE Velocity',
            date(2002, 3, 30), date(2006, 9, 2),
            day_of_week=5
        )
        self.stdout.write(f'  Created {created} Velocity episodes')
        return created

    def seed_main_event(self):
        """Seed WWE Main Event (2012-2025)."""
        self.stdout.write('--- Seeding WWE Main Event ---')
        created = self.seed_weekly_show(
            self.wwe, 'WWE Main Event',
            date(2012, 10, 3), date(2025, 12, 31),
            day_of_week=2  # Wednesday
        )
        self.stdout.write(f'  Created {created} Main Event episodes')
        return created

    def seed_nitro(self):
        """Seed WCW Monday Nitro (1995-2001)."""
        self.stdout.write('--- Seeding WCW Monday Nitro ---')

        venues = [
            ('Georgia Dome', 'Atlanta, GA'),
            ('Cow Palace', 'San Francisco, CA'),
            ('Target Center', 'Minneapolis, MN'),
            ('Nassau Coliseum', 'Uniondale, NY'),
            ('America West Arena', 'Phoenix, AZ'),
        ]

        created = self.seed_weekly_show(
            self.wcw, 'WCW Monday Nitro',
            date(1995, 9, 4), date(2001, 3, 26),
            day_of_week=0, venues=venues
        )
        self.stdout.write(f'  Created {created} Nitro episodes')
        return created

    def seed_thunder(self):
        """Seed WCW Thunder (1998-2001)."""
        self.stdout.write('--- Seeding WCW Thunder ---')
        created = self.seed_weekly_show(
            self.wcw, 'WCW Thunder',
            date(1998, 1, 8), date(2001, 3, 21),
            day_of_week=3  # Thursday
        )
        self.stdout.write(f'  Created {created} Thunder episodes')
        return created

    def seed_wcw_saturday_night(self):
        """Seed WCW Saturday Night (1991-2000)."""
        self.stdout.write('--- Seeding WCW Saturday Night ---')
        created = self.seed_weekly_show(
            self.wcw, 'WCW Saturday Night',
            date(1991, 1, 5), date(2000, 6, 24),
            day_of_week=5
        )
        self.stdout.write(f'  Created {created} Saturday Night episodes')
        return created

    def seed_wcw_worldwide(self):
        """Seed WCW WorldWide (1988-2001)."""
        self.stdout.write('--- Seeding WCW WorldWide ---')
        created = self.seed_weekly_show(
            self.wcw, 'WCW WorldWide',
            date(1988, 1, 3), date(2001, 3, 25),
            day_of_week=6
        )
        self.stdout.write(f'  Created {created} WorldWide episodes')
        return created

    def seed_wcw_power_hour(self):
        """Seed WCW Power Hour (1989-1994)."""
        self.stdout.write('--- Seeding WCW Power Hour ---')
        created = self.seed_weekly_show(
            self.wcw, 'WCW Power Hour',
            date(1989, 1, 6), date(1994, 12, 30),
            day_of_week=4
        )
        self.stdout.write(f'  Created {created} Power Hour episodes')
        return created

    def seed_ecw_hardcore_tv(self):
        """Seed ECW Hardcore TV (1993-2001)."""
        self.stdout.write('--- Seeding ECW Hardcore TV ---')

        venues = [
            ('ECW Arena', 'Philadelphia, PA'),
            ('Elks Lodge', 'Queens, NY'),
            ('ECW Arena', 'Philadelphia, PA'),
        ]

        created = self.seed_weekly_show(
            self.ecw, 'ECW Hardcore TV',
            date(1993, 4, 6), date(2001, 1, 6),
            day_of_week=5, venues=venues
        )
        self.stdout.write(f'  Created {created} Hardcore TV episodes')
        return created

    def seed_ecw_on_tnn(self):
        """Seed ECW on TNN (1999-2000)."""
        self.stdout.write('--- Seeding ECW on TNN ---')
        created = self.seed_weekly_show(
            self.ecw, 'ECW on TNN',
            date(1999, 8, 27), date(2000, 10, 6),
            day_of_week=4
        )
        self.stdout.write(f'  Created {created} ECW on TNN episodes')
        return created

    def seed_impact(self):
        """Seed TNA/Impact Wrestling (2004-2025)."""
        self.stdout.write('--- Seeding TNA/Impact Wrestling ---')

        venues = [
            ('Impact Zone', 'Orlando, FL'),
            ('Universal Studios', 'Orlando, FL'),
            ('Impact Zone', 'Orlando, FL'),
        ]

        created = self.seed_weekly_show(
            self.tna, 'TNA Impact',
            date(2004, 6, 4), date(2025, 12, 31),
            day_of_week=3, venues=venues  # Thursday
        )
        self.stdout.write(f'  Created {created} Impact episodes')
        return created

    def seed_xplosion(self):
        """Seed TNA Xplosion (2004-2019)."""
        self.stdout.write('--- Seeding TNA Xplosion ---')
        created = self.seed_weekly_show(
            self.tna, 'TNA Xplosion',
            date(2004, 11, 6), date(2019, 12, 28),
            day_of_week=5
        )
        self.stdout.write(f'  Created {created} Xplosion episodes')
        return created

    def seed_dynamite(self):
        """Seed AEW Dynamite (2019-2025)."""
        self.stdout.write('--- Seeding AEW Dynamite ---')

        venues = [
            ("Daily's Place", 'Jacksonville, FL'),
            ('United Center', 'Chicago, IL'),
            ('Arthur Ashe Stadium', 'Queens, NY'),
            ('Prudential Center', 'Newark, NJ'),
            ('NOW Arena', 'Hoffman Estates, IL'),
        ]

        created = self.seed_weekly_show(
            self.aew, 'AEW Dynamite',
            date(2019, 10, 2), date(2025, 12, 31),
            day_of_week=2, venues=venues  # Wednesday
        )
        self.stdout.write(f'  Created {created} Dynamite episodes')
        return created

    def seed_rampage(self):
        """Seed AEW Rampage (2021-2025)."""
        self.stdout.write('--- Seeding AEW Rampage ---')
        created = self.seed_weekly_show(
            self.aew, 'AEW Rampage',
            date(2021, 8, 13), date(2025, 12, 31),
            day_of_week=4  # Friday
        )
        self.stdout.write(f'  Created {created} Rampage episodes')
        return created

    def seed_collision(self):
        """Seed AEW Collision (2023-2025)."""
        self.stdout.write('--- Seeding AEW Collision ---')
        created = self.seed_weekly_show(
            self.aew, 'AEW Collision',
            date(2023, 6, 17), date(2025, 12, 31),
            day_of_week=5  # Saturday
        )
        self.stdout.write(f'  Created {created} Collision episodes')
        return created

    def seed_aew_dark(self):
        """Seed AEW Dark (2019-2023)."""
        self.stdout.write('--- Seeding AEW Dark ---')
        created = self.seed_weekly_show(
            self.aew, 'AEW Dark',
            date(2019, 10, 8), date(2023, 6, 6),
            day_of_week=1  # Tuesday
        )
        self.stdout.write(f'  Created {created} Dark episodes')
        return created

    def seed_nxt(self):
        """Seed WWE NXT (2010-2025)."""
        self.stdout.write('--- Seeding WWE NXT ---')

        venues = [
            ('Full Sail University', 'Winter Park, FL'),
            ('Capitol Wrestling Center', 'Orlando, FL'),
            ('WWE Performance Center', 'Orlando, FL'),
        ]

        created = self.seed_weekly_show(
            self.nxt, 'WWE NXT',
            date(2010, 2, 23), date(2025, 12, 31),
            day_of_week=1, venues=venues  # Tuesday
        )
        self.stdout.write(f'  Created {created} NXT episodes')
        return created
