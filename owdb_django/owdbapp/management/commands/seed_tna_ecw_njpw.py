"""
Seed TNA/Impact, ECW, and NJPW historic events with full match cards.

Usage:
    python manage.py seed_tna_ecw_njpw
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed TNA/Impact, ECW, and NJPW historic events'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding TNA/ECW/NJPW Events ===\n'))

        self.ensure_promotions()
        self.seed_tna_events()
        self.seed_ecw_events()
        self.seed_njpw_events()

        # Print stats
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')
        self.stdout.write(f'Wrestlers: {Wrestler.objects.count()}')

    def ensure_promotions(self):
        """Ensure required promotions exist."""
        promotions = [
            {'name': 'Total Nonstop Action Wrestling', 'abbreviation': 'TNA', 'founded_year': 2002},
            {'name': 'Impact Wrestling', 'abbreviation': 'IMPACT', 'founded_year': 2017},
            {'name': 'Extreme Championship Wrestling', 'abbreviation': 'ECW', 'founded_year': 1992},
            {'name': 'New Japan Pro-Wrestling', 'abbreviation': 'NJPW', 'founded_year': 1972},
        ]
        for p in promotions:
            existing = Promotion.objects.filter(abbreviation=p['abbreviation']).first()
            if not existing:
                Promotion.objects.create(
                    name=p['name'],
                    abbreviation=p['abbreviation'],
                    founded_year=p.get('founded_year')
                )

    def get_or_create_wrestler(self, name, **kwargs):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(name=name, **kwargs)
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

    def get_or_create_title(self, name, promotion):
        """Get or create a title."""
        title = Title.objects.filter(name__iexact=name).first()
        if not title:
            title = Title.objects.create(name=name, promotion=promotion)
            self.stdout.write(f'  + Created title: {name}')
        return title

    def get_or_create_venue(self, name, location=None):
        """Get or create a venue."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.create(name=name, location=location)
        return venue

    def create_event_with_matches(self, promotion, event_data, matches_data):
        """Create an event with its matches."""
        event_date = event_data['date']
        slug = slugify(f"{event_data['name']}-{event_date.year}")

        event = Event.objects.filter(slug=slug).first()
        if event:
            self.stdout.write(f'  Event exists: {event_data["name"]} ({event_date.year})')
            return event, False

        venue = None
        if 'venue' in event_data:
            venue = self.get_or_create_venue(
                event_data['venue'],
                event_data.get('location')
            )

        event = Event.objects.create(
            name=event_data['name'],
            slug=slug,
            date=event_date,
            promotion=promotion,
            venue=venue,
            location=event_data.get('location'),
            attendance=event_data.get('attendance'),
            about=event_data.get('about', '')
        )

        for i, match_data in enumerate(matches_data, 1):
            self.create_match(event, match_data, i)

        self.stdout.write(self.style.SUCCESS(
            f'  Created: {event_data["name"]} ({event_date.year}) - {len(matches_data)} matches'
        ))
        return event, True

    def create_match(self, event, match_data, order):
        """Create a match for an event."""
        wrestlers = [self.get_or_create_wrestler(name) for name in match_data['wrestlers']]
        winner = None
        if match_data.get('winner'):
            winner = self.get_or_create_wrestler(match_data['winner'])

        title = None
        if match_data.get('title'):
            title = Title.objects.filter(name__icontains=match_data['title']).first()

        match = Match.objects.create(
            event=event,
            match_order=order,
            match_type=match_data.get('match_type', 'Singles'),
            winner=winner,
            result=match_data.get('result', ''),
            title=title,
            about=match_data.get('about', '')
        )
        match.wrestlers.set(wrestlers)
        return match

    def seed_tna_events(self):
        """Seed TNA/Impact Wrestling events."""
        self.stdout.write('\n--- Seeding TNA/Impact Events ---\n')
        tna = Promotion.objects.filter(abbreviation='TNA').first()

        # Bound for Glory 2005
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2005',
            'date': date(2005, 10, 23),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'The first Bound for Glory PPV, TNA\'s biggest annual event.'
        }, [
            {'wrestlers': ['Austin Aries', 'Roderick Strong'], 'winner': 'Austin Aries',
             'match_type': 'Singles', 'about': 'Opening match showcasing X Division talent.'},
            {'wrestlers': ['Samoa Joe', 'Jushin Thunder Liger'], 'winner': 'Samoa Joe',
             'match_type': 'Singles', 'about': 'Dream match between two legends.'},
            {'wrestlers': ['AJ Styles', 'Christopher Daniels', 'Samoa Joe'], 'winner': 'AJ Styles',
             'match_type': 'Triple Threat', 'title': 'X Division', 'about': 'Classic three-way for the X Division Championship.'},
            {'wrestlers': ['Rhino', 'Jeff Jarrett'], 'winner': 'Rhino',
             'match_type': 'Monster\'s Ball', 'title': 'NWA World', 'about': 'Rhino captured the NWA World Heavyweight Championship.'},
        ])

        # Bound for Glory 2006
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2006',
            'date': date(2006, 10, 22),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'TNA\'s second annual Bound for Glory event.'
        }, [
            {'wrestlers': ['Senshi', 'Austin Aries', 'Sonjay Dutt', 'Shark Boy', 'Alex Shelley', 'Jay Lethal'],
             'winner': 'Senshi', 'match_type': 'Ultimate X', 'title': 'X Division',
             'about': 'Six-man Ultimate X match for the X Division Championship.'},
            {'wrestlers': ['Christian Cage', 'Rhino'], 'winner': 'Christian Cage',
             'match_type': 'Cage Match', 'about': 'Steel cage match between former tag partners.'},
            {'wrestlers': ['Sting', 'Jeff Jarrett'], 'winner': 'Sting',
             'match_type': 'Singles', 'title': 'NWA World', 'about': 'Sting captured the NWA World Heavyweight Championship.'},
        ])

        # Bound for Glory 2007
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2007',
            'date': date(2007, 10, 14),
            'venue': 'Gwinnett Center',
            'location': 'Duluth, GA',
            'attendance': 7000,
            'about': 'First TNA PPV held outside the Impact Zone.'
        }, [
            {'wrestlers': ['Jay Lethal', 'Christopher Daniels'], 'winner': 'Jay Lethal',
             'match_type': 'Singles', 'title': 'X Division', 'about': 'Jay Lethal defended the X Division Championship.'},
            {'wrestlers': ['Kurt Angle', 'Sting'], 'winner': 'Kurt Angle',
             'match_type': 'Singles', 'title': 'TNA World', 'about': 'Kurt Angle won the TNA World Heavyweight Championship.'},
        ])

        # Bound for Glory 2008
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2008',
            'date': date(2008, 10, 12),
            'venue': 'Sears Centre',
            'location': 'Hoffman Estates, IL',
            'attendance': 8100,
            'about': 'TNA\'s fourth annual Bound for Glory.'
        }, [
            {'wrestlers': ['Sting', 'Samoa Joe'], 'winner': 'Sting',
             'match_type': 'Singles', 'title': 'TNA World', 'about': 'Sting won the TNA World Heavyweight Championship.'},
            {'wrestlers': ['AJ Styles', 'Frank Trigg'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'AJ Styles faced MMA fighter Frank Trigg.'},
            {'wrestlers': ['Kurt Angle', 'Jeff Jarrett'], 'winner': 'Kurt Angle',
             'match_type': 'Singles', 'about': 'Personal grudge match.'},
        ])

        # Bound for Glory 2009
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2009',
            'date': date(2009, 10, 18),
            'venue': 'Irvine Spectrum',
            'location': 'Irvine, CA',
            'about': 'Fifth annual Bound for Glory event.'
        }, [
            {'wrestlers': ['AJ Styles', 'Sting'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'title': 'TNA World', 'about': 'AJ Styles won the TNA World Heavyweight Championship for the first time.'},
            {'wrestlers': ['Bobby Lashley', 'Samoa Joe'], 'winner': 'Bobby Lashley',
             'match_type': 'Singles', 'about': 'Lashley defeated Samoa Joe in his TNA debut.'},
            {'wrestlers': ['Kurt Angle', 'Matt Morgan'], 'winner': 'Kurt Angle',
             'match_type': 'Singles', 'about': 'Angle faced the rising Matt Morgan.'},
        ])

        # Bound for Glory 2010
        self.create_event_with_matches(tna, {
            'name': 'Bound for Glory 2010',
            'date': date(2010, 10, 10),
            'venue': 'Ocean Center',
            'location': 'Daytona Beach, FL',
            'about': 'The debut of Immortal faction.'
        }, [
            {'wrestlers': ['Jeff Hardy', 'Kurt Angle', 'Mr. Anderson'], 'winner': 'Jeff Hardy',
             'match_type': 'Triple Threat', 'title': 'TNA World', 'about': 'Jeff Hardy turned heel and won the TNA World Championship with help from Hulk Hogan and Eric Bischoff, forming Immortal.'},
            {'wrestlers': ['RVD', 'Abyss'], 'winner': 'Abyss',
             'match_type': 'Monster\'s Ball', 'about': 'Hardcore match between RVD and Abyss.'},
        ])

        # Slammiversary 2005
        self.create_event_with_matches(tna, {
            'name': 'Slammiversary 2005',
            'date': date(2005, 6, 19),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'TNA\'s third anniversary celebration PPV.'
        }, [
            {'wrestlers': ['AJ Styles', 'Christopher Daniels', 'Samoa Joe'], 'winner': 'AJ Styles',
             'match_type': 'Triple Threat', 'title': 'X Division', 'about': 'Classic triple threat for the X Division title.'},
            {'wrestlers': ['Jeff Jarrett', 'Raven'], 'winner': 'Jeff Jarrett',
             'match_type': 'King of the Mountain', 'title': 'NWA World', 'about': 'King of the Mountain match for the NWA World Heavyweight Championship.'},
        ])

        # Slammiversary 2006
        self.create_event_with_matches(tna, {
            'name': 'Slammiversary 2006',
            'date': date(2006, 6, 18),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'TNA\'s fourth anniversary PPV.'
        }, [
            {'wrestlers': ['Jeff Jarrett', 'Sting', 'Christian Cage', 'Abyss', 'Ron Killings'],
             'winner': 'Jeff Jarrett', 'match_type': 'King of the Mountain', 'title': 'NWA World',
             'about': 'King of the Mountain match.'},
            {'wrestlers': ['Samoa Joe', 'Scott Steiner'], 'winner': 'Samoa Joe',
             'match_type': 'Singles', 'about': 'Samoa Joe faced Scott Steiner.'},
        ])

        # Lockdown 2005
        self.create_event_with_matches(tna, {
            'name': 'Lockdown 2005',
            'date': date(2005, 4, 24),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'First TNA Lockdown PPV - all matches inside Six Sides of Steel.'
        }, [
            {'wrestlers': ['Jeff Jarrett', 'Kevin Nash', 'Diamond Dallas Page', 'Sean Waltman'],
             'winner': 'Jeff Jarrett', 'match_type': 'Lethal Lockdown', 'title': 'NWA World',
             'about': 'First ever Lethal Lockdown match.'},
            {'wrestlers': ['AJ Styles', 'Abyss'], 'winner': 'Abyss',
             'match_type': 'Six Sides of Steel', 'about': 'Steel cage match.'},
        ])

        # Lockdown 2008
        self.create_event_with_matches(tna, {
            'name': 'Lockdown 2008',
            'date': date(2008, 4, 13),
            'venue': 'Tsongas Center',
            'location': 'Lowell, MA',
            'about': 'Every match inside Six Sides of Steel.'
        }, [
            {'wrestlers': ['Samoa Joe', 'Kurt Angle'], 'winner': 'Samoa Joe',
             'match_type': 'Six Sides of Steel', 'title': 'TNA World', 'about': 'Samoa Joe won the TNA World Heavyweight Championship.'},
            {'wrestlers': ['Team Cage', 'Team Tomko'], 'winner': 'Team Cage',
             'match_type': 'Lethal Lockdown', 'about': 'Lethal Lockdown match.'},
        ])

        # Genesis 2005
        self.create_event_with_matches(tna, {
            'name': 'Genesis 2005',
            'date': date(2005, 11, 13),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'First TNA Genesis PPV.'
        }, [
            {'wrestlers': ['Jeff Jarrett', 'Rhino'], 'winner': 'Jeff Jarrett',
             'match_type': 'Singles', 'title': 'NWA World', 'about': 'Jarrett recaptured the NWA World Heavyweight Championship.'},
            {'wrestlers': ['Samoa Joe', 'AJ Styles'], 'winner': 'Samoa Joe',
             'match_type': 'Singles', 'about': 'Samoa Joe defeated AJ Styles.'},
        ])

        # Sacrifice 2005
        self.create_event_with_matches(tna, {
            'name': 'Sacrifice 2005',
            'date': date(2005, 5, 14),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'First TNA Sacrifice PPV.'
        }, [
            {'wrestlers': ['AJ Styles', 'Abyss'], 'winner': 'AJ Styles',
             'match_type': 'Tables Match', 'about': 'AJ Styles defeated Abyss in a tables match.'},
            {'wrestlers': ['Jeff Jarrett', 'Raven'], 'winner': 'Jeff Jarrett',
             'match_type': 'Singles', 'title': 'NWA World', 'about': 'Jarrett retained the NWA World Heavyweight Championship.'},
        ])

    def seed_ecw_events(self):
        """Seed ECW events."""
        self.stdout.write('\n--- Seeding ECW Events ---\n')
        ecw = Promotion.objects.filter(abbreviation='ECW').first()

        # Heatwave 1998
        self.create_event_with_matches(ecw, {
            'name': 'Heatwave 1998',
            'date': date(1998, 8, 2),
            'venue': 'Lost Battalion Hall',
            'location': 'Queens, NY',
            'about': 'One of ECW\'s most critically acclaimed PPVs.'
        }, [
            {'wrestlers': ['Taz', 'Bam Bam Bigelow'], 'winner': 'Taz',
             'match_type': 'Singles', 'title': 'FTW', 'about': 'FTW Championship match.'},
            {'wrestlers': ['Rob Van Dam', 'Sabu'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'Classic ECW match between two high-flyers.'},
            {'wrestlers': ['Shane Douglas', 'Al Snow'], 'winner': 'Shane Douglas',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'ECW World Heavyweight Championship match.'},
            {'wrestlers': ['Tommy Dreamer', 'Jerry Lawler', 'Justin Credible', 'The Sandman'],
             'winner': 'Tommy Dreamer', 'match_type': 'Tag Team', 'about': 'ECW vs WWE invasion match.'},
        ])

        # November to Remember 1997
        self.create_event_with_matches(ecw, {
            'name': 'November to Remember 1997',
            'date': date(1997, 11, 30),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, PA',
            'about': 'ECW\'s annual November event.'
        }, [
            {'wrestlers': ['Bam Bam Bigelow', 'Shane Douglas'], 'winner': 'Bam Bam Bigelow',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'Bam Bam Bigelow won the ECW World Heavyweight Championship.'},
            {'wrestlers': ['Taz', 'Pitbull #2'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz in singles action.'},
            {'wrestlers': ['Rob Van Dam', 'Tommy Dreamer'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'RVD defended the Television Championship.'},
        ])

        # November to Remember 1998
        self.create_event_with_matches(ecw, {
            'name': 'November to Remember 1998',
            'date': date(1998, 11, 1),
            'venue': 'Lakefront Arena',
            'location': 'New Orleans, LA',
            'about': 'Annual November event.'
        }, [
            {'wrestlers': ['Shane Douglas', 'Taz'], 'winner': 'Shane Douglas',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'ECW World Championship main event.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'Classic RVD vs Lynn match.'},
            {'wrestlers': ['The Dudley Boyz', 'The Sandman', 'Tommy Dreamer'],
             'winner': 'The Dudley Boyz', 'match_type': 'Tag Team', 'about': 'Tag team main event.'},
        ])

        # November to Remember 1999
        self.create_event_with_matches(ecw, {
            'name': 'November to Remember 1999',
            'date': date(1999, 11, 7),
            'venue': 'Burt Flickinger Center',
            'location': 'Buffalo, NY',
            'about': 'Another edition of the annual November event.'
        }, [
            {'wrestlers': ['Mike Awesome', 'Masato Tanaka'], 'winner': 'Mike Awesome',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'Brutal ECW World Championship match.'},
            {'wrestlers': ['Taz', 'Yoshihiro Tajiri'], 'winner': 'Taz',
             'match_type': 'Singles', 'about': 'Taz faced the Japanese Buzzsaw.'},
            {'wrestlers': ['Rob Van Dam', 'Sabu'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'RVD vs Sabu in a rematch.'},
        ])

        # Living Dangerously 1998
        self.create_event_with_matches(ecw, {
            'name': 'Living Dangerously 1998',
            'date': date(1998, 3, 1),
            'venue': 'Asbury Park Convention Hall',
            'location': 'Asbury Park, NJ',
            'about': 'ECW PPV from New Jersey.'
        }, [
            {'wrestlers': ['Shane Douglas', 'Al Snow'], 'winner': 'Shane Douglas',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'ECW World Championship defense.'},
            {'wrestlers': ['Rob Van Dam', 'Sabu', '2 Cold Scorpio'], 'winner': 'Rob Van Dam',
             'match_type': 'Triple Threat', 'title': 'ECW Television', 'about': 'Triple threat TV title match.'},
            {'wrestlers': ['Bam Bam Bigelow', 'Taz'], 'winner': 'Draw',
             'match_type': 'Singles', 'about': 'Hardcore brawl ended in a double countout.'},
        ])

        # Living Dangerously 1999
        self.create_event_with_matches(ecw, {
            'name': 'Living Dangerously 1999',
            'date': date(1999, 3, 21),
            'venue': 'Asbury Park Convention Hall',
            'location': 'Asbury Park, NJ',
            'about': 'Featured the infamous scaffold dive.'
        }, [
            {'wrestlers': ['Taz', 'Sabu'], 'winner': 'Taz',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'Taz won the ECW World Heavyweight Championship.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'Classic match between two of the best.'},
            {'wrestlers': ['New Jack', 'Vic Grimes'], 'winner': 'New Jack',
             'match_type': 'Scaffold Match', 'about': 'Infamous scaffold match.'},
        ])

        # Anarchy Rulz 1999
        self.create_event_with_matches(ecw, {
            'name': 'Anarchy Rulz 1999',
            'date': date(1999, 9, 19),
            'venue': 'Odeum',
            'location': 'Villa Park, IL',
            'about': 'First Anarchy Rulz PPV.'
        }, [
            {'wrestlers': ['Taz', 'Mike Awesome'], 'winner': 'Mike Awesome',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'Mike Awesome won the ECW World Heavyweight Championship.'},
            {'wrestlers': ['Rob Van Dam', 'Jerry Lynn'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'Another classic in their legendary series.'},
            {'wrestlers': ['Tommy Dreamer', 'Lance Storm'], 'winner': 'Tommy Dreamer',
             'match_type': 'Singles', 'about': 'Dreamer faced the Canadian legend.'},
        ])

        # Guilty as Charged 1999
        self.create_event_with_matches(ecw, {
            'name': 'Guilty as Charged 1999',
            'date': date(1999, 1, 10),
            'venue': 'Millenium Theatre',
            'location': 'Kissimmee, FL',
            'about': 'ECW\'s first PPV of 1999.'
        }, [
            {'wrestlers': ['Shane Douglas', 'Taz'], 'winner': 'Taz',
             'match_type': 'Singles', 'title': 'ECW World', 'about': 'Taz won the ECW World Heavyweight Championship.'},
            {'wrestlers': ['Rob Van Dam', 'Lance Storm'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'ECW Television', 'about': 'RVD defended against Storm.'},
        ])

        # Guilty as Charged 2001
        self.create_event_with_matches(ecw, {
            'name': 'Guilty as Charged 2001',
            'date': date(2001, 1, 7),
            'venue': 'Hammerstein Ballroom',
            'location': 'New York City, NY',
            'about': 'The final ECW PPV before the company closed.'
        }, [
            {'wrestlers': ['The Sandman', 'Rhino', 'Steve Corino'], 'winner': 'The Sandman',
             'match_type': 'Triple Threat', 'title': 'ECW World', 'about': 'Triple threat for the ECW World Championship.'},
            {'wrestlers': ['Jerry Lynn', 'Cyrus'], 'winner': 'Jerry Lynn',
             'match_type': 'Singles', 'about': 'Jerry Lynn faced Cyrus.'},
            {'wrestlers': ['Tommy Dreamer', 'CW Anderson'], 'winner': 'Tommy Dreamer',
             'match_type': 'Singles', 'about': 'Tommy Dreamer in one of the final ECW matches.'},
        ])

    def seed_njpw_events(self):
        """Seed New Japan Pro-Wrestling events."""
        self.stdout.write('\n--- Seeding NJPW Events ---\n')
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()

        # Wrestle Kingdom 10
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 10',
            'date': date(2016, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 25204,
            'about': 'NJPW\'s premiere event featuring the crowning of a new ace.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Hiroshi Tanahashi'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Okada defeated Tanahashi to win the IWGP Heavyweight Championship.'},
            {'wrestlers': ['Shinsuke Nakamura', 'AJ Styles'], 'winner': 'Shinsuke Nakamura',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Nakamura\'s final NJPW match before departing for WWE.'},
            {'wrestlers': ['Tetsuya Naito', 'Hirooki Goto'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'about': 'Naito faced Goto.'},
            {'wrestlers': ['The Young Bucks', 'reDRagon', 'Roppongi Vice', 'Ricochet', 'Matt Sydal'],
             'winner': 'The Young Bucks', 'match_type': 'Four-Way Tag', 'title': 'IWGP Junior Heavyweight Tag',
             'about': 'Four-way match for the junior tag titles.'},
        ])

        # Wrestle Kingdom 11
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 11',
            'date': date(2017, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 26192,
            'about': 'NJPW\'s premier Tokyo Dome event.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Kenny Omega'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': '6-star classic match. Omega challenged Okada for the IWGP Heavyweight Championship in an instant classic.'},
            {'wrestlers': ['Tetsuya Naito', 'Hiroshi Tanahashi'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito defeated Tanahashi for the IC title.'},
            {'wrestlers': ['Hiromu Takahashi', 'Kushida'], 'winner': 'Hiromu Takahashi',
             'match_type': 'Singles', 'title': 'IWGP Junior Heavyweight', 'about': 'Time bomb Takahashi won the junior title.'},
        ])

        # Wrestle Kingdom 12
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 12',
            'date': date(2018, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 34995,
            'about': 'Record-setting attendance for NJPW.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Tetsuya Naito'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Okada retained against the leader of LIJ.'},
            {'wrestlers': ['Kenny Omega', 'Chris Jericho'], 'winner': 'Kenny Omega',
             'match_type': 'No DQ', 'title': 'IWGP US Heavyweight', 'about': 'Alpha vs Omega match. Omega defeated Jericho for the US title.'},
            {'wrestlers': ['Hiroshi Tanahashi', 'Jay White'], 'winner': 'Hiroshi Tanahashi',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Tanahashi defeated the Switchblade.'},
        ])

        # Wrestle Kingdom 13
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 13',
            'date': date(2019, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 38162,
            'about': 'One of the highest attended wrestling events in Japanese history.'
        }, [
            {'wrestlers': ['Hiroshi Tanahashi', 'Kenny Omega'], 'winner': 'Hiroshi Tanahashi',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Tanahashi defeated Omega to win the IWGP Heavyweight Championship. Omega\'s last NJPW match.'},
            {'wrestlers': ['Jay White', 'Kazuchika Okada'], 'winner': 'Jay White',
             'match_type': 'Singles', 'about': 'Switchblade shocked the world by defeating Okada.'},
            {'wrestlers': ['Tetsuya Naito', 'Chris Jericho'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito won the IC title from Jericho.'},
        ])

        # Wrestle Kingdom 14 Night 1
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 14 Night 1',
            'date': date(2020, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 40008,
            'about': 'First night of the two-night Wrestle Kingdom.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Kota Ibushi'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Okada retained against his former partner.'},
            {'wrestlers': ['Tetsuya Naito', 'Jay White'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito won the IC title.'},
            {'wrestlers': ['Will Ospreay', 'Hiromu Takahashi'], 'winner': 'Will Ospreay',
             'match_type': 'Singles', 'title': 'IWGP Junior Heavyweight', 'about': 'Show-stealing junior heavyweight match.'},
        ])

        # Wrestle Kingdom 14 Night 2
        self.create_event_with_matches(njpw, {
            'name': 'Wrestle Kingdom 14 Night 2',
            'date': date(2020, 1, 5),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 40008,
            'about': 'Historic double title unification match.'
        }, [
            {'wrestlers': ['Tetsuya Naito', 'Kazuchika Okada'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Naito finally won the IWGP Heavyweight Championship, becoming double champion. Historic title unification match.'},
            {'wrestlers': ['Jon Moxley', 'Juice Robinson'], 'winner': 'Jon Moxley',
             'match_type': 'Texas Death Match', 'title': 'IWGP US Heavyweight', 'about': 'Moxley retained the US title in a brutal match.'},
        ])

        # G1 Climax 29 Finals
        self.create_event_with_matches(njpw, {
            'name': 'G1 Climax 29 Finals',
            'date': date(2019, 8, 12),
            'venue': 'Nippon Budokan',
            'location': 'Tokyo, Japan',
            'attendance': 12000,
            'about': 'Finals of the prestigious G1 Climax tournament.'
        }, [
            {'wrestlers': ['Kota Ibushi', 'Jay White'], 'winner': 'Kota Ibushi',
             'match_type': 'Singles', 'about': 'Ibushi won the G1 Climax 29 tournament, earning a title shot at Wrestle Kingdom.'},
            {'wrestlers': ['Kazuchika Okada', 'Sanada'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'about': 'Block finals match.'},
        ])

        # G1 Climax 28 Finals
        self.create_event_with_matches(njpw, {
            'name': 'G1 Climax 28 Finals',
            'date': date(2018, 8, 12),
            'venue': 'Nippon Budokan',
            'location': 'Tokyo, Japan',
            'attendance': 12000,
            'about': 'Finals of the G1 Climax 28 tournament.'
        }, [
            {'wrestlers': ['Hiroshi Tanahashi', 'Kota Ibushi'], 'winner': 'Hiroshi Tanahashi',
             'match_type': 'Singles', 'about': 'Tanahashi won the G1 Climax 28 tournament.'},
            {'wrestlers': ['Kenny Omega', 'Tomohiro Ishii'], 'winner': 'Kenny Omega',
             'match_type': 'Singles', 'about': 'Omega vs Ishii in a brutal match.'},
        ])

        # Dominion 2019
        self.create_event_with_matches(njpw, {
            'name': 'Dominion 6.9 in Osaka-jo Hall',
            'date': date(2019, 6, 9),
            'venue': 'Osaka-jo Hall',
            'location': 'Osaka, Japan',
            'attendance': 12000,
            'about': 'NJPW\'s second biggest annual event.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Chris Jericho'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Okada defeated Jericho to retain the IWGP Heavyweight Championship.'},
            {'wrestlers': ['Jon Moxley', 'Shota Umino'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'about': 'Moxley\'s NJPW debut match.'},
            {'wrestlers': ['Tetsuya Naito', 'Kota Ibushi'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito defended the IC title.'},
        ])

        # Dominion 2017
        self.create_event_with_matches(njpw, {
            'name': 'Dominion 6.11 in Osaka-jo Hall',
            'date': date(2017, 6, 11),
            'venue': 'Osaka-jo Hall',
            'location': 'Osaka, Japan',
            'attendance': 12000,
            'about': 'Featured another Okada vs Omega classic.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Kenny Omega'], 'winner': 'Draw',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': '60-minute draw. Another 6-star classic in their legendary series.'},
            {'wrestlers': ['Tetsuya Naito', 'Hiroshi Tanahashi'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito retained the IC title.'},
            {'wrestlers': ['Hiromu Takahashi', 'Kushida'], 'winner': 'Hiromu Takahashi',
             'match_type': 'Singles', 'title': 'IWGP Junior Heavyweight', 'about': 'Takahashi retained the junior title.'},
        ])

        # Sakura Genesis 2017
        self.create_event_with_matches(njpw, {
            'name': 'Sakura Genesis 2017',
            'date': date(2017, 4, 9),
            'venue': 'Ryogoku Kokugikan',
            'location': 'Tokyo, Japan',
            'about': 'Spring\'s biggest NJPW event.'
        }, [
            {'wrestlers': ['Kazuchika Okada', 'Katsuyori Shibata'], 'winner': 'Kazuchika Okada',
             'match_type': 'Singles', 'title': 'IWGP Heavyweight', 'about': 'Brutal match that led to Shibata\'s career-ending injury.'},
            {'wrestlers': ['Tetsuya Naito', 'Hirooki Goto'], 'winner': 'Tetsuya Naito',
             'match_type': 'Singles', 'title': 'IWGP Intercontinental', 'about': 'Naito defended the IC title.'},
        ])
