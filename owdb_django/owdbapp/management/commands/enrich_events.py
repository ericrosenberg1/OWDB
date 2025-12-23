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

    def get_or_create_venue(self, name, city=None, state=None, country=None, capacity=None, about=None):
        """Get or create a venue."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.create(
                name=name,
                slug=slugify(name),
                city=city or '',
                state=state or '',
                country=country or 'USA',
                capacity=capacity,
                about=about or f'{name} is a venue that has hosted professional wrestling events.'
            )
            self.stdout.write(f'  Created venue: {name}')
        return venue

    def create_venues(self):
        """Create major wrestling venues."""
        self.stdout.write('--- Creating Major Venues ---')
        created = 0

        venues_data = [
            # WrestleMania Venues
            {'name': 'Madison Square Garden', 'city': 'New York City', 'state': 'New York', 'country': 'USA', 'capacity': 20789, 'about': 'Madison Square Garden is the world\'s most famous arena. The mecca of wrestling.'},
            {'name': 'Pontiac Silverdome', 'city': 'Pontiac', 'state': 'Michigan', 'country': 'USA', 'capacity': 93173, 'about': 'Pontiac Silverdome hosted WrestleMania III with 93,173 fans.'},
            {'name': 'Trump Plaza', 'city': 'Atlantic City', 'state': 'New Jersey', 'country': 'USA', 'capacity': 18000, 'about': 'Trump Plaza hosted WrestleMania IV and V.'},
            {'name': 'SkyDome', 'city': 'Toronto', 'state': 'Ontario', 'country': 'Canada', 'capacity': 67000, 'about': 'SkyDome (Rogers Centre) hosted WrestleMania VI and X8.'},
            {'name': 'Los Angeles Memorial Sports Arena', 'city': 'Los Angeles', 'state': 'California', 'country': 'USA', 'capacity': 16161, 'about': 'LA Sports Arena hosted WrestleMania VII.'},
            {'name': 'Hoosier Dome', 'city': 'Indianapolis', 'state': 'Indiana', 'country': 'USA', 'capacity': 62418, 'about': 'Hoosier Dome hosted WrestleMania VIII.'},
            {'name': 'Caesars Palace', 'city': 'Las Vegas', 'state': 'Nevada', 'country': 'USA', 'capacity': 16891, 'about': 'Caesars Palace outdoor venue hosted WrestleMania IX.'},
            {'name': 'Hartford Civic Center', 'city': 'Hartford', 'state': 'Connecticut', 'country': 'USA', 'capacity': 16294, 'about': 'Hartford Civic Center hosted WrestleMania XI.'},
            {'name': 'Arrowhead Pond', 'city': 'Anaheim', 'state': 'California', 'country': 'USA', 'capacity': 18336, 'about': 'Arrowhead Pond (Honda Center) hosted WrestleMania XII.'},
            {'name': 'Rosemont Horizon', 'city': 'Rosemont', 'state': 'Illinois', 'country': 'USA', 'capacity': 18500, 'about': 'Rosemont Horizon (Allstate Arena) hosted WrestleMania 13.'},
            {'name': 'FleetCenter', 'city': 'Boston', 'state': 'Massachusetts', 'country': 'USA', 'capacity': 19580, 'about': 'FleetCenter (TD Garden) hosted WrestleMania 14.'},
            {'name': 'First Union Center', 'city': 'Philadelphia', 'state': 'Pennsylvania', 'country': 'USA', 'capacity': 21600, 'about': 'First Union Center (Wells Fargo) hosted WrestleMania XV.'},
            {'name': 'Arrowhead Pond of Anaheim', 'city': 'Anaheim', 'state': 'California', 'country': 'USA', 'capacity': 18336, 'about': 'Arrowhead Pond hosted WrestleMania 2000.'},
            {'name': 'Reliant Astrodome', 'city': 'Houston', 'state': 'Texas', 'country': 'USA', 'capacity': 67925, 'about': 'Reliant Astrodome hosted WrestleMania X-Seven.'},
            {'name': 'Rogers Centre', 'city': 'Toronto', 'state': 'Ontario', 'country': 'Canada', 'capacity': 67000, 'about': 'Rogers Centre (formerly SkyDome) hosted WrestleMania X8.'},
            {'name': 'Safeco Field', 'city': 'Seattle', 'state': 'Washington', 'country': 'USA', 'capacity': 54097, 'about': 'Safeco Field hosted WrestleMania XIX.'},
            {'name': 'Staples Center', 'city': 'Los Angeles', 'state': 'California', 'country': 'USA', 'capacity': 21000, 'about': 'Staples Center (Crypto.com Arena) hosted WrestleMania 21.'},
            {'name': 'Allstate Arena', 'city': 'Rosemont', 'state': 'Illinois', 'country': 'USA', 'capacity': 18500, 'about': 'Allstate Arena hosted WrestleMania 22.'},
            {'name': 'Ford Field', 'city': 'Detroit', 'state': 'Michigan', 'country': 'USA', 'capacity': 80311, 'about': 'Ford Field hosted WrestleMania 23.'},
            {'name': 'Citrus Bowl', 'city': 'Orlando', 'state': 'Florida', 'country': 'USA', 'capacity': 74916, 'about': 'Citrus Bowl hosted WrestleMania XXIV.'},
            {'name': 'Reliant Stadium', 'city': 'Houston', 'state': 'Texas', 'country': 'USA', 'capacity': 72220, 'about': 'Reliant Stadium (NRG Stadium) hosted WrestleMania XXV.'},
            {'name': 'University of Phoenix Stadium', 'city': 'Glendale', 'state': 'Arizona', 'country': 'USA', 'capacity': 72800, 'about': 'University of Phoenix Stadium hosted WrestleMania XXVI.'},
            {'name': 'Georgia Dome', 'city': 'Atlanta', 'state': 'Georgia', 'country': 'USA', 'capacity': 71228, 'about': 'Georgia Dome hosted WrestleMania XXVII.'},
            {'name': 'Sun Life Stadium', 'city': 'Miami Gardens', 'state': 'Florida', 'country': 'USA', 'capacity': 75540, 'about': 'Sun Life Stadium hosted WrestleMania XXVIII.'},
            {'name': 'MetLife Stadium', 'city': 'East Rutherford', 'state': 'New Jersey', 'country': 'USA', 'capacity': 82500, 'about': 'MetLife Stadium hosted WrestleMania 29 and 35.'},
            {'name': 'Mercedes-Benz Superdome', 'city': 'New Orleans', 'state': 'Louisiana', 'country': 'USA', 'capacity': 73208, 'about': 'Mercedes-Benz Superdome hosted WrestleMania XXX and 34.'},
            {'name': 'Levi\'s Stadium', 'city': 'Santa Clara', 'state': 'California', 'country': 'USA', 'capacity': 75000, 'about': 'Levi\'s Stadium hosted WrestleMania 31.'},
            {'name': 'AT&T Stadium', 'city': 'Arlington', 'state': 'Texas', 'country': 'USA', 'capacity': 100000, 'about': 'AT&T Stadium hosted WrestleMania 32 and 38.'},
            {'name': 'Camping World Stadium', 'city': 'Orlando', 'state': 'Florida', 'country': 'USA', 'capacity': 65000, 'about': 'Camping World Stadium hosted WrestleMania 33.'},
            {'name': 'Raymond James Stadium', 'city': 'Tampa', 'state': 'Florida', 'country': 'USA', 'capacity': 75000, 'about': 'Raymond James Stadium hosted WrestleMania 36 and 37.'},
            {'name': 'SoFi Stadium', 'city': 'Inglewood', 'state': 'California', 'country': 'USA', 'capacity': 100240, 'about': 'SoFi Stadium hosted WrestleMania 39.'},
            {'name': 'Lincoln Financial Field', 'city': 'Philadelphia', 'state': 'Pennsylvania', 'country': 'USA', 'capacity': 69596, 'about': 'Lincoln Financial Field hosted WrestleMania 40.'},
            {'name': 'Allegiant Stadium', 'city': 'Las Vegas', 'state': 'Nevada', 'country': 'USA', 'capacity': 71835, 'about': 'Allegiant Stadium will host WrestleMania 41.'},
            # Royal Rumble Venues
            {'name': 'Copps Coliseum', 'city': 'Hamilton', 'state': 'Ontario', 'country': 'Canada', 'capacity': 17383, 'about': 'Copps Coliseum hosted the first Royal Rumble.'},
            {'name': 'The Summit', 'city': 'Houston', 'state': 'Texas', 'country': 'USA', 'capacity': 17000, 'about': 'The Summit hosted Royal Rumble 1989.'},
            {'name': 'Orlando Arena', 'city': 'Orlando', 'state': 'Florida', 'country': 'USA', 'capacity': 17519, 'about': 'Orlando Arena (Amway Arena) hosted Royal Rumble 1990.'},
            {'name': 'Miami Arena', 'city': 'Miami', 'state': 'Florida', 'country': 'USA', 'capacity': 16640, 'about': 'Miami Arena hosted Royal Rumble 1991.'},
            {'name': 'Knickerbocker Arena', 'city': 'Albany', 'state': 'New York', 'country': 'USA', 'capacity': 17500, 'about': 'Knickerbocker Arena hosted Royal Rumble 1992.'},
            {'name': 'ARCO Arena', 'city': 'Sacramento', 'state': 'California', 'country': 'USA', 'capacity': 17317, 'about': 'ARCO Arena hosted Royal Rumble 1993.'},
            {'name': 'Providence Civic Center', 'city': 'Providence', 'state': 'Rhode Island', 'country': 'USA', 'capacity': 14700, 'about': 'Providence Civic Center hosted Royal Rumble 1994.'},
            {'name': 'USF Sun Dome', 'city': 'Tampa', 'state': 'Florida', 'country': 'USA', 'capacity': 10411, 'about': 'USF Sun Dome hosted Royal Rumble 1995.'},
            {'name': 'Selland Arena', 'city': 'Fresno', 'state': 'California', 'country': 'USA', 'capacity': 10232, 'about': 'Selland Arena hosted Royal Rumble 1996.'},
            {'name': 'Alamodome', 'city': 'San Antonio', 'state': 'Texas', 'country': 'USA', 'capacity': 72000, 'about': 'Alamodome hosted Royal Rumble 1997 and 2017.'},
        ]

        for vdata in venues_data:
            name = vdata.pop('name')
            venue = Venue.objects.filter(name__iexact=name).first()
            if not venue:
                venue = Venue.objects.create(name=name, slug=slugify(name), **vdata)
                created += 1
                self.stdout.write(f'  Created: {name}')
            elif not venue.about or venue.about == '':
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
