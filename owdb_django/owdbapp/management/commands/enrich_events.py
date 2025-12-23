"""
Event and Venue Enrichment Command.

Adds venues to events and ensures proper interlinking.

Usage:
    python manage.py enrich_events
    python manage.py enrich_events --type=wrestlemania
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdb_django.owdbapp.models import Event, Venue, Promotion


class Command(BaseCommand):
    help = 'Enrich events with venues and proper data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            help='Event type to enrich (wrestlemania, royalrumble, ppv, raw, smackdown)',
            default='all'
        )

    def handle(self, *args, **options):
        event_type = options.get('type', 'all')

        self.stdout.write(self.style.SUCCESS('\n=== EVENT ENRICHMENT ===\n'))

        total_updated = 0

        if event_type in ['all', 'venues']:
            total_updated += self.create_venues()

        if event_type in ['all', 'wrestlemania']:
            total_updated += self.enrich_wrestlemania()

        if event_type in ['all', 'royalrumble']:
            total_updated += self.enrich_royal_rumble()

        if event_type in ['all', 'summerslam']:
            total_updated += self.enrich_summerslam()

        if event_type in ['all', 'survivorseries']:
            total_updated += self.enrich_survivor_series()

        self.stdout.write(self.style.SUCCESS(f'\n=== ENRICHMENT COMPLETE ==='))
        self.stdout.write(f'Total events updated: {total_updated}')

    def get_or_create_venue(self, name, location=None, capacity=None):
        """Get or create a venue."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.create(
                name=name,
                slug=slugify(name),
                location=location or '',
                capacity=capacity
            )
            self.stdout.write(f'  Created venue: {name}')
        return venue

    def create_venues(self):
        """Create major wrestling venues."""
        self.stdout.write('--- Creating Major Venues ---')
        created = 0

        venues_data = [
            # WrestleMania Venues
            {'name': 'Madison Square Garden', 'location': 'New York City, New York', 'capacity': 20789},
            {'name': 'Pontiac Silverdome', 'location': 'Pontiac, Michigan', 'capacity': 93173},
            {'name': 'Trump Plaza', 'location': 'Atlantic City, New Jersey', 'capacity': 18000},
            {'name': 'SkyDome', 'location': 'Toronto, Ontario, Canada', 'capacity': 67000},
            {'name': 'Los Angeles Memorial Sports Arena', 'location': 'Los Angeles, California', 'capacity': 16161},
            {'name': 'Hoosier Dome', 'location': 'Indianapolis, Indiana', 'capacity': 62418},
            {'name': 'Caesars Palace', 'location': 'Las Vegas, Nevada', 'capacity': 16891},
            {'name': 'Hartford Civic Center', 'location': 'Hartford, Connecticut', 'capacity': 16294},
            {'name': 'Arrowhead Pond', 'location': 'Anaheim, California', 'capacity': 18336},
            {'name': 'Rosemont Horizon', 'location': 'Rosemont, Illinois', 'capacity': 18500},
            {'name': 'FleetCenter', 'location': 'Boston, Massachusetts', 'capacity': 19580},
            {'name': 'First Union Center', 'location': 'Philadelphia, Pennsylvania', 'capacity': 21600},
            {'name': 'Arrowhead Pond of Anaheim', 'location': 'Anaheim, California', 'capacity': 18336},
            {'name': 'Reliant Astrodome', 'location': 'Houston, Texas', 'capacity': 67925},
            {'name': 'Rogers Centre', 'location': 'Toronto, Ontario, Canada', 'capacity': 67000},
            {'name': 'Safeco Field', 'location': 'Seattle, Washington', 'capacity': 54097},
            {'name': 'Staples Center', 'location': 'Los Angeles, California', 'capacity': 21000},
            {'name': 'Allstate Arena', 'location': 'Rosemont, Illinois', 'capacity': 18500},
            {'name': 'Ford Field', 'location': 'Detroit, Michigan', 'capacity': 80311},
            {'name': 'Citrus Bowl', 'location': 'Orlando, Florida', 'capacity': 74916},
            {'name': 'Reliant Stadium', 'location': 'Houston, Texas', 'capacity': 72220},
            {'name': 'University of Phoenix Stadium', 'location': 'Glendale, Arizona', 'capacity': 72800},
            {'name': 'Georgia Dome', 'location': 'Atlanta, Georgia', 'capacity': 71228},
            {'name': 'Sun Life Stadium', 'location': 'Miami Gardens, Florida', 'capacity': 75540},
            {'name': 'MetLife Stadium', 'location': 'East Rutherford, New Jersey', 'capacity': 82500},
            {'name': 'Mercedes-Benz Superdome', 'location': 'New Orleans, Louisiana', 'capacity': 73208},
            {'name': 'Levi\'s Stadium', 'location': 'Santa Clara, California', 'capacity': 75000},
            {'name': 'AT&T Stadium', 'location': 'Arlington, Texas', 'capacity': 100000},
            {'name': 'Camping World Stadium', 'location': 'Orlando, Florida', 'capacity': 65000},
            {'name': 'Raymond James Stadium', 'location': 'Tampa, Florida', 'capacity': 75000},
            {'name': 'SoFi Stadium', 'location': 'Inglewood, California', 'capacity': 100240},
            {'name': 'Lincoln Financial Field', 'location': 'Philadelphia, Pennsylvania', 'capacity': 69596},
            {'name': 'Allegiant Stadium', 'location': 'Las Vegas, Nevada', 'capacity': 71835},
            # Royal Rumble Venues
            {'name': 'Copps Coliseum', 'location': 'Hamilton, Ontario, Canada', 'capacity': 17383},
            {'name': 'The Summit', 'location': 'Houston, Texas', 'capacity': 17000},
            {'name': 'Orlando Arena', 'location': 'Orlando, Florida', 'capacity': 17519},
            {'name': 'Miami Arena', 'location': 'Miami, Florida', 'capacity': 16640},
            {'name': 'Knickerbocker Arena', 'location': 'Albany, New York', 'capacity': 17500},
            {'name': 'ARCO Arena', 'location': 'Sacramento, California', 'capacity': 17317},
            {'name': 'Providence Civic Center', 'location': 'Providence, Rhode Island', 'capacity': 14700},
            {'name': 'USF Sun Dome', 'location': 'Tampa, Florida', 'capacity': 10411},
            {'name': 'Selland Arena', 'location': 'Fresno, California', 'capacity': 10232},
            {'name': 'Alamodome', 'location': 'San Antonio, Texas', 'capacity': 72000},
        ]

        for vdata in venues_data:
            name = vdata.pop('name')
            venue = Venue.objects.filter(name__iexact=name).first()
            if not venue:
                venue = Venue.objects.create(name=name, slug=slugify(name), **vdata)
                created += 1
                self.stdout.write(f'  Created: {name}')
            elif not venue.location or venue.location == '':
                for field, value in vdata.items():
                    if value:
                        setattr(venue, field, value)
                venue.save()
                self.stdout.write(f'  Updated: {name}')

        self.stdout.write(f'  Created {created} venues')
        return created

    def enrich_wrestlemania(self):
        """Add venues to WrestleMania events."""
        self.stdout.write('--- Enriching WrestleMania Events ---')
        updated = 0

        # WrestleMania venue mappings
        wm_venues = {
            'WrestleMania': ('Madison Square Garden', '1985-03-31'),
            'WrestleMania 1': ('Madison Square Garden', None),
            'WrestleMania I': ('Madison Square Garden', None),
            'WrestleMania 2': ('Multiple Venues', None),
            'WrestleMania II': ('Multiple Venues', None),
            'WrestleMania 3': ('Pontiac Silverdome', None),
            'WrestleMania III': ('Pontiac Silverdome', None),
            'WrestleMania 4': ('Trump Plaza', None),
            'WrestleMania IV': ('Trump Plaza', None),
            'WrestleMania 5': ('Trump Plaza', None),
            'WrestleMania V': ('Trump Plaza', None),
            'WrestleMania 6': ('SkyDome', None),
            'WrestleMania VI': ('SkyDome', None),
            'WrestleMania 7': ('Los Angeles Memorial Sports Arena', None),
            'WrestleMania VII': ('Los Angeles Memorial Sports Arena', None),
            'WrestleMania 8': ('Hoosier Dome', None),
            'WrestleMania VIII': ('Hoosier Dome', None),
            'WrestleMania 9': ('Caesars Palace', None),
            'WrestleMania IX': ('Caesars Palace', None),
            'WrestleMania 10': ('Madison Square Garden', None),
            'WrestleMania X': ('Madison Square Garden', None),
            'WrestleMania 11': ('Hartford Civic Center', None),
            'WrestleMania XI': ('Hartford Civic Center', None),
            'WrestleMania 12': ('Arrowhead Pond', None),
            'WrestleMania XII': ('Arrowhead Pond', None),
            'WrestleMania 13': ('Rosemont Horizon', None),
            'WrestleMania 14': ('FleetCenter', None),
            'WrestleMania XIV': ('FleetCenter', None),
            'WrestleMania 15': ('First Union Center', None),
            'WrestleMania XV': ('First Union Center', None),
            'WrestleMania 16': ('Arrowhead Pond of Anaheim', None),
            'WrestleMania 2000': ('Arrowhead Pond of Anaheim', None),
            'WrestleMania 17': ('Reliant Astrodome', None),
            'WrestleMania X-Seven': ('Reliant Astrodome', None),
            'WrestleMania 18': ('Rogers Centre', None),
            'WrestleMania X8': ('Rogers Centre', None),
            'WrestleMania 19': ('Safeco Field', None),
            'WrestleMania XIX': ('Safeco Field', None),
            'WrestleMania 20': ('Madison Square Garden', None),
            'WrestleMania XX': ('Madison Square Garden', None),
            'WrestleMania 21': ('Staples Center', None),
            'WrestleMania 22': ('Allstate Arena', None),
            'WrestleMania 23': ('Ford Field', None),
            'WrestleMania 24': ('Citrus Bowl', None),
            'WrestleMania XXIV': ('Citrus Bowl', None),
            'WrestleMania 25': ('Reliant Stadium', None),
            'WrestleMania XXV': ('Reliant Stadium', None),
            'WrestleMania 26': ('University of Phoenix Stadium', None),
            'WrestleMania XXVI': ('University of Phoenix Stadium', None),
            'WrestleMania 27': ('Georgia Dome', None),
            'WrestleMania XXVII': ('Georgia Dome', None),
            'WrestleMania 28': ('Sun Life Stadium', None),
            'WrestleMania XXVIII': ('Sun Life Stadium', None),
            'WrestleMania 29': ('MetLife Stadium', None),
            'WrestleMania 30': ('Mercedes-Benz Superdome', None),
            'WrestleMania XXX': ('Mercedes-Benz Superdome', None),
            'WrestleMania 31': ('Levi\'s Stadium', None),
            'WrestleMania 32': ('AT&T Stadium', None),
            'WrestleMania 33': ('Camping World Stadium', None),
            'WrestleMania 34': ('Mercedes-Benz Superdome', None),
            'WrestleMania 35': ('MetLife Stadium', None),
            'WrestleMania 36': ('Raymond James Stadium', None),
            'WrestleMania 37': ('Raymond James Stadium', None),
            'WrestleMania 38': ('AT&T Stadium', None),
            'WrestleMania 39': ('SoFi Stadium', None),
            'WrestleMania 40': ('Lincoln Financial Field', None),
            'WrestleMania 41': ('Allegiant Stadium', None),
        }

        for event_name, (venue_name, date) in wm_venues.items():
            events = Event.objects.filter(name__iexact=event_name)
            if not events.exists():
                events = Event.objects.filter(name__icontains=event_name)

            venue = Venue.objects.filter(name__iexact=venue_name).first()
            if not venue:
                venue = Venue.objects.filter(name__icontains=venue_name).first()

            for event in events:
                if venue and not event.venue:
                    event.venue = venue
                    event.save()
                    updated += 1
                    self.stdout.write(f'  Linked {event.name} to {venue.name}')

        self.stdout.write(f'  Updated {updated} WrestleMania events')
        return updated

    def enrich_royal_rumble(self):
        """Add venues to Royal Rumble events."""
        self.stdout.write('--- Enriching Royal Rumble Events ---')
        updated = 0

        rr_venues = {
            'Royal Rumble 1988': 'Copps Coliseum',
            'Royal Rumble (1988)': 'Copps Coliseum',
            'Royal Rumble 1989': 'The Summit',
            'Royal Rumble (1989)': 'The Summit',
            'Royal Rumble 1990': 'Orlando Arena',
            'Royal Rumble (1990)': 'Orlando Arena',
            'Royal Rumble 1991': 'Miami Arena',
            'Royal Rumble (1991)': 'Miami Arena',
            'Royal Rumble 1992': 'Knickerbocker Arena',
            'Royal Rumble (1992)': 'Knickerbocker Arena',
            'Royal Rumble 1993': 'ARCO Arena',
            'Royal Rumble (1993)': 'ARCO Arena',
            'Royal Rumble 1994': 'Providence Civic Center',
            'Royal Rumble (1994)': 'Providence Civic Center',
            'Royal Rumble 1995': 'USF Sun Dome',
            'Royal Rumble (1995)': 'USF Sun Dome',
            'Royal Rumble 1996': 'Selland Arena',
            'Royal Rumble (1996)': 'Selland Arena',
            'Royal Rumble 1997': 'Alamodome',
            'Royal Rumble (1997)': 'Alamodome',
            'Royal Rumble 2017': 'Alamodome',
            'Royal Rumble (2017)': 'Alamodome',
        }

        for event_name, venue_name in rr_venues.items():
            events = Event.objects.filter(name__iexact=event_name)
            if not events.exists():
                events = Event.objects.filter(name__icontains=event_name.replace('(', '').replace(')', ''))

            venue = Venue.objects.filter(name__iexact=venue_name).first()
            if not venue:
                venue = Venue.objects.filter(name__icontains=venue_name).first()

            for event in events:
                if venue and not event.venue:
                    event.venue = venue
                    event.save()
                    updated += 1
                    self.stdout.write(f'  Linked {event.name} to {venue.name}')

        self.stdout.write(f'  Updated {updated} Royal Rumble events')
        return updated

    def enrich_summerslam(self):
        """Add venues to SummerSlam events."""
        self.stdout.write('--- Enriching SummerSlam Events ---')
        updated = 0
        # Will implement in next batch
        self.stdout.write(f'  Updated {updated} SummerSlam events')
        return updated

    def enrich_survivor_series(self):
        """Add venues to Survivor Series events."""
        self.stdout.write('--- Enriching Survivor Series Events ---')
        updated = 0
        # Will implement in next batch
        self.stdout.write(f'  Updated {updated} Survivor Series events')
        return updated
