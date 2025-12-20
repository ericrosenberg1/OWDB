"""
Seed AEW and ROH historic events with full match cards.

Usage:
    python manage.py seed_aew_roh
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed AEW and ROH historic events'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding AEW & ROH Events ===\n'))

        self.ensure_promotions()
        self.ensure_titles()
        self.seed_aew_events()
        self.seed_roh_events()

        # Print stats
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')
        self.stdout.write(f'Wrestlers: {Wrestler.objects.count()}')

    def ensure_promotions(self):
        """Ensure required promotions exist."""
        promotions = [
            {'name': 'All Elite Wrestling', 'abbreviation': 'AEW', 'founded_year': 2019},
            {'name': 'Ring of Honor', 'abbreviation': 'ROH', 'founded_year': 2002},
        ]
        for p in promotions:
            existing = Promotion.objects.filter(abbreviation=p['abbreviation']).first()
            if not existing:
                Promotion.objects.create(
                    name=p['name'],
                    abbreviation=p['abbreviation'],
                    founded_year=p.get('founded_year')
                )

    def ensure_titles(self):
        """Ensure AEW and ROH titles exist."""
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        roh = Promotion.objects.filter(abbreviation='ROH').first()

        titles = [
            ('AEW World Championship', aew),
            ('AEW TNT Championship', aew),
            ('AEW TBS Championship', aew),
            ('AEW International Championship', aew),
            ('AEW World Tag Team Championship', aew),
            ('AEW Women\'s World Championship', aew),
            ('AEW All-Atlantic Championship', aew),
            ('AEW World Trios Championship', aew),
            ('ROH World Championship', roh),
            ('ROH World Television Championship', roh),
            ('ROH World Tag Team Championship', roh),
            ('ROH Women\'s World Championship', roh),
            ('ROH Pure Championship', roh),
            ('ROH World Six-Man Tag Team Championship', roh),
        ]
        for name, promotion in titles:
            if promotion:
                existing = Title.objects.filter(name=name).first()
                if not existing:
                    Title.objects.create(name=name, promotion=promotion)
                    self.stdout.write(f'  + Created title: {name}')

    def get_or_create_wrestler(self, name, **kwargs):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(name=name, **kwargs)
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

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

    def seed_aew_events(self):
        """Seed AEW events."""
        self.stdout.write('\n--- Seeding AEW Events ---\n')
        aew = Promotion.objects.filter(abbreviation='AEW').first()

        events = [
            # Double or Nothing 2020
            ({
                'name': 'Double or Nothing 2020',
                'date': date(2020, 5, 23),
                'venue': 'Daily\'s Place',
                'location': 'Jacksonville, FL',
                'about': 'First major AEW event during the pandemic.'
            }, [
                {'wrestlers': ['Jon Moxley', 'Brodie Lee'], 'winner': 'Jon Moxley',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Moxley defended against Brodie Lee.'},
                {'wrestlers': ['Cody', 'Lance Archer'], 'winner': 'Cody',
                 'match_type': 'Singles', 'title': 'TNT', 'about': 'Cody became the first TNT Champion.'},
                {'wrestlers': ['MJF', 'Jungle Boy'], 'winner': 'MJF',
                 'match_type': 'Singles', 'about': 'MJF defeated the rising Jungle Boy.'},
                {'wrestlers': ['Stadium Stampede'], 'winner': 'The Elite',
                 'match_type': 'Stadium Stampede', 'about': 'Cinematic match at TIAA Bank Field.'},
            ]),
            # All Out 2020
            ({
                'name': 'All Out 2020',
                'date': date(2020, 9, 5),
                'venue': 'Daily\'s Place',
                'location': 'Jacksonville, FL',
                'about': 'Annual AEW September event.'
            }, [
                {'wrestlers': ['Jon Moxley', 'MJF'], 'winner': 'Jon Moxley',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Moxley retained against MJF.'},
                {'wrestlers': ['FTR', 'Kenny Omega', 'Hangman Adam Page'], 'winner': 'FTR',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'FTR won the tag titles.'},
                {'wrestlers': ['Hikaru Shida', 'Thunder Rosa'], 'winner': 'Hikaru Shida',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Shida retained against Thunder Rosa.'},
                {'wrestlers': ['Matt Hardy', 'Sammy Guevara'], 'winner': 'Matt Hardy',
                 'match_type': 'Broken Rules', 'about': 'Controversial match ending.'},
            ]),
            # Full Gear 2020
            ({
                'name': 'Full Gear 2020',
                'date': date(2020, 11, 7),
                'venue': 'Daily\'s Place',
                'location': 'Jacksonville, FL',
                'about': 'Jon Moxley vs Eddie Kingston main event.'
            }, [
                {'wrestlers': ['Jon Moxley', 'Eddie Kingston'], 'winner': 'Jon Moxley',
                 'match_type': 'I Quit', 'title': 'AEW World', 'about': 'Brutal I Quit match.'},
                {'wrestlers': ['Kenny Omega', 'Hangman Adam Page'], 'winner': 'Kenny Omega',
                 'match_type': 'Singles', 'about': 'Omega defeated his former partner, earning a title shot.'},
                {'wrestlers': ['Cody', 'Darby Allin'], 'winner': 'Darby Allin',
                 'match_type': 'Singles', 'title': 'TNT', 'about': 'Darby won the TNT Championship.'},
                {'wrestlers': ['Young Bucks', 'FTR'], 'winner': 'Young Bucks',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'Dream tag team match.'},
            ]),
            # Revolution 2021
            ({
                'name': 'Revolution 2021',
                'date': date(2021, 3, 7),
                'venue': 'Daily\'s Place',
                'location': 'Jacksonville, FL',
                'about': 'Exploding Barbed Wire Deathmatch main event.'
            }, [
                {'wrestlers': ['Kenny Omega', 'Jon Moxley'], 'winner': 'Kenny Omega',
                 'match_type': 'Exploding Barbed Wire Deathmatch', 'title': 'AEW World',
                 'about': 'Omega retained in the infamous exploding ring match.'},
                {'wrestlers': ['Sting', 'Darby Allin', 'Brian Cage', 'Ricky Starks'], 'winner': 'Sting',
                 'match_type': 'Street Fight Tag', 'about': 'Sting\'s first match since 2015.'},
                {'wrestlers': ['Young Bucks', 'Chris Jericho', 'MJF'], 'winner': 'Young Bucks',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'Young Bucks retained.'},
            ]),
            # Double or Nothing 2021
            ({
                'name': 'Double or Nothing 2021',
                'date': date(2021, 5, 30),
                'venue': 'Daily\'s Place',
                'location': 'Jacksonville, FL',
                'attendance': 5000,
                'about': 'First AEW event with full capacity fans during pandemic.'
            }, [
                {'wrestlers': ['Kenny Omega', 'Orange Cassidy', 'PAC'], 'winner': 'Kenny Omega',
                 'match_type': 'Triple Threat', 'title': 'AEW World', 'about': 'Omega retained in a three-way.'},
                {'wrestlers': ['Dr. Britt Baker', 'Hikaru Shida'], 'winner': 'Dr. Britt Baker',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Britt Baker became Women\'s Champion.'},
                {'wrestlers': ['Miro', 'Lance Archer'], 'winner': 'Miro',
                 'match_type': 'Singles', 'title': 'TNT', 'about': 'Miro won the TNT Championship.'},
                {'wrestlers': ['Stadium Stampede'], 'winner': 'The Pinnacle',
                 'match_type': 'Stadium Stampede', 'about': 'Inner Circle vs The Pinnacle.'},
            ]),
            # All Out 2022
            ({
                'name': 'All Out 2022',
                'date': date(2022, 9, 4),
                'venue': 'NOW Arena',
                'location': 'Hoffman Estates, IL',
                'attendance': 11575,
                'about': 'CM Punk returns from injury. Backstage brawl afterward.'
            }, [
                {'wrestlers': ['CM Punk', 'Jon Moxley'], 'winner': 'CM Punk',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Punk won the unified title.'},
                {'wrestlers': ['Toni Storm', 'Dr. Britt Baker', 'Hikaru Shida', 'Jamie Hayter'],
                 'winner': 'Toni Storm', 'match_type': 'Fatal 4-Way', 'title': 'AEW Women', 'about': 'Storm won the women\'s title.'},
                {'wrestlers': ['Swerve Strickland', 'Keith Lee', 'The Acclaimed'], 'winner': 'The Acclaimed',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'The Acclaimed became tag champions.'},
                {'wrestlers': ['MJF'], 'winner': 'MJF',
                 'match_type': 'Casino Ladder Match', 'about': 'MJF won the Casino Ladder Match.'},
            ]),
            # Full Gear 2022
            ({
                'name': 'Full Gear 2022',
                'date': date(2022, 11, 19),
                'venue': 'Prudential Center',
                'location': 'Newark, NJ',
                'attendance': 12500,
                'about': 'MJF wins the AEW World Championship.'
            }, [
                {'wrestlers': ['MJF', 'Jon Moxley'], 'winner': 'MJF',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'MJF won his first AEW World Championship.'},
                {'wrestlers': ['Jade Cargill', 'Nyla Rose'], 'winner': 'Jade Cargill',
                 'match_type': 'Singles', 'title': 'TBS', 'about': 'Jade continued her undefeated streak.'},
                {'wrestlers': ['Chris Jericho', 'Bryan Danielson', 'Claudio Castagnoli', 'Sammy Guevara'],
                 'winner': 'Chris Jericho', 'match_type': 'ROH World', 'title': 'ROH World', 'about': 'Jericho won the ROH World title.'},
                {'wrestlers': ['The Acclaimed', 'Swerve in Our Glory'], 'winner': 'The Acclaimed',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'The Acclaimed retained.'},
            ]),
            # Revolution 2023
            ({
                'name': 'Revolution 2023',
                'date': date(2023, 3, 5),
                'venue': 'Chase Center',
                'location': 'San Francisco, CA',
                'attendance': 7200,
                'about': 'MJF defends against Bryan Danielson.'
            }, [
                {'wrestlers': ['MJF', 'Bryan Danielson'], 'winner': 'MJF',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'MJF retained in a 60-minute draw turned sudden death.'},
                {'wrestlers': ['Jamie Hayter', 'Saraya'], 'winner': 'Jamie Hayter',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Hayter retained the Women\'s title.'},
                {'wrestlers': ['Jon Moxley', 'Hangman Adam Page'], 'winner': 'Jon Moxley',
                 'match_type': 'Texas Death Match', 'about': 'Brutal Texas Death Match.'},
            ]),
            # Double or Nothing 2023
            ({
                'name': 'Double or Nothing 2023',
                'date': date(2023, 5, 28),
                'venue': 'T-Mobile Arena',
                'location': 'Las Vegas, NV',
                'attendance': 13764,
                'about': 'MJF\'s first Las Vegas title defense.'
            }, [
                {'wrestlers': ['MJF', 'Sammy Guevara'], 'winner': 'MJF',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'MJF retained against Sammy.'},
                {'wrestlers': ['Toni Storm', 'Ruby Soho'], 'winner': 'Toni Storm',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Storm retained the Women\'s title.'},
                {'wrestlers': ['Sting', 'Darby Allin', 'The Blackpool Combat Club'],
                 'winner': 'Sting', 'match_type': 'Anarchy in the Arena', 'about': 'Wild brawl through the arena.'},
                {'wrestlers': ['FTR', 'Jay Briscoe', 'Mark Briscoe'], 'winner': 'FTR',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'FTR retained the ROH Tag titles.'},
            ]),
            # All Out 2023
            ({
                'name': 'All Out 2023',
                'date': date(2023, 9, 3),
                'venue': 'United Center',
                'location': 'Chicago, IL',
                'attendance': 16000,
                'about': 'MJF vs Adam Cole main event.'
            }, [
                {'wrestlers': ['MJF', 'Adam Cole'], 'winner': 'MJF',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'MJF retained in a shocking turn.'},
                {'wrestlers': ['Sting', 'Darby Allin', 'Christian Cage', 'Luchasaurus'],
                 'winner': 'Sting', 'match_type': 'Tag Team', 'about': 'Sting and Darby won the battle.'},
                {'wrestlers': ['Hikaru Shida', 'Dr. Britt Baker'], 'winner': 'Hikaru Shida',
                 'match_type': 'Singles', 'about': 'Shida defeated her rival Baker.'},
            ]),
            # Full Gear 2023
            ({
                'name': 'Full Gear 2023',
                'date': date(2023, 11, 18),
                'venue': 'Kia Forum',
                'location': 'Inglewood, CA',
                'attendance': 12000,
                'about': 'MJF defends against Jay Briscoe.'
            }, [
                {'wrestlers': ['MJF', 'Jay Briscoe'], 'winner': 'MJF',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'MJF retained in an emotional match.'},
                {'wrestlers': ['Eddie Kingston', 'Jon Moxley'], 'winner': 'Eddie Kingston',
                 'match_type': 'Singles', 'about': 'Kingston defeated his blood brother Moxley.'},
                {'wrestlers': ['Sting', 'Darby Allin', 'Ricky Starks', 'Big Bill'], 'winner': 'Sting',
                 'match_type': 'Tag Team', 'about': 'Sting and Darby continued their winning ways.'},
            ]),
            # Worlds End 2023
            ({
                'name': 'Worlds End 2023',
                'date': date(2023, 12, 30),
                'venue': 'Nassau Coliseum',
                'location': 'Uniondale, NY',
                'attendance': 10000,
                'about': 'End of year showcase with title changes.'
            }, [
                {'wrestlers': ['Samoa Joe', 'MJF'], 'winner': 'Samoa Joe',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Samoa Joe won the AEW World Championship!'},
                {'wrestlers': ['Julia Hart', 'Abadon'], 'winner': 'Julia Hart',
                 'match_type': 'Singles', 'title': 'TBS', 'about': 'Julia Hart retained the TBS title.'},
                {'wrestlers': ['Toni Storm', 'Riho'], 'winner': 'Toni Storm',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Toni Storm retained.'},
            ]),
            # Revolution 2024
            ({
                'name': 'Revolution 2024',
                'date': date(2024, 3, 3),
                'venue': 'Greensboro Coliseum',
                'location': 'Greensboro, NC',
                'attendance': 9000,
                'about': 'Samoa Joe defends against Eddie Kingston.'
            }, [
                {'wrestlers': ['Samoa Joe', 'Hangman Adam Page', 'Swerve Strickland'],
                 'winner': 'Samoa Joe', 'match_type': 'Triple Threat', 'title': 'AEW World',
                 'about': 'Joe retained in a three-way.'},
                {'wrestlers': ['Toni Storm', 'Deonna Purrazzo'], 'winner': 'Toni Storm',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Storm continued her reign.'},
                {'wrestlers': ['Sting', 'Darby Allin', 'The Young Bucks'], 'winner': 'Sting',
                 'match_type': 'Tag Team', 'about': 'Sting\'s last PPV match.'},
            ]),
            # Dynasty 2024
            ({
                'name': 'Dynasty 2024',
                'date': date(2024, 4, 21),
                'venue': 'Chaifetz Arena',
                'location': 'St. Louis, MO',
                'attendance': 8500,
                'about': 'Swerve Strickland becomes AEW World Champion.'
            }, [
                {'wrestlers': ['Swerve Strickland', 'Samoa Joe'], 'winner': 'Swerve Strickland',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Swerve became AEW World Champion!'},
                {'wrestlers': ['Toni Storm', 'Thunder Rosa'], 'winner': 'Toni Storm',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Storm retained.'},
                {'wrestlers': ['Will Ospreay', 'Bryan Danielson'], 'winner': 'Will Ospreay',
                 'match_type': 'Singles', 'about': 'Dream match in Ospreay\'s AEW debut.'},
            ]),
            # Double or Nothing 2024
            ({
                'name': 'Double or Nothing 2024',
                'date': date(2024, 5, 26),
                'venue': 'MGM Grand Garden Arena',
                'location': 'Las Vegas, NV',
                'attendance': 14000,
                'about': 'Swerve defends against Christian Cage.'
            }, [
                {'wrestlers': ['Swerve Strickland', 'Christian Cage'], 'winner': 'Swerve Strickland',
                 'match_type': 'Singles', 'title': 'AEW World', 'about': 'Swerve retained in Las Vegas.'},
                {'wrestlers': ['Toni Storm', 'Mariah May'], 'winner': 'Toni Storm',
                 'match_type': 'Singles', 'title': 'AEW Women', 'about': 'Storm defended against her protege.'},
                {'wrestlers': ['Will Ospreay', 'Roderick Strong'], 'winner': 'Will Ospreay',
                 'match_type': 'Singles', 'title': 'International', 'about': 'Ospreay retained the International title.'},
                {'wrestlers': ['The Young Bucks', 'FTR'], 'winner': 'The Young Bucks',
                 'match_type': 'Tag Team', 'title': 'AEW Tag Team', 'about': 'EVPs retained the tag titles.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(aew, event_data, matches)

    def seed_roh_events(self):
        """Seed Ring of Honor events."""
        self.stdout.write('\n--- Seeding ROH Events ---\n')
        roh = Promotion.objects.filter(abbreviation='ROH').first()

        events = [
            # Supercard of Honor 2006
            ({
                'name': 'Supercard of Honor 2006',
                'date': date(2006, 3, 31),
                'venue': 'Edison High School',
                'location': 'Edison, NJ',
                'about': 'First Supercard of Honor event.'
            }, [
                {'wrestlers': ['Bryan Danielson', 'Roderick Strong'], 'winner': 'Bryan Danielson',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Danielson defended the ROH World title.'},
                {'wrestlers': ['Samoa Joe', 'Christopher Daniels'], 'winner': 'Samoa Joe',
                 'match_type': 'Singles', 'about': 'Dream match between two legends.'},
            ]),
            # Death Before Dishonor IV
            ({
                'name': 'Death Before Dishonor IV',
                'date': date(2006, 7, 15),
                'venue': 'The Arena',
                'location': 'Philadelphia, PA',
                'about': 'Annual DBD event.'
            }, [
                {'wrestlers': ['Bryan Danielson', 'Colt Cabana'], 'winner': 'Bryan Danielson',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Danielson retained the ROH World title.'},
                {'wrestlers': ['KENTA', 'Roderick Strong'], 'winner': 'KENTA',
                 'match_type': 'Singles', 'about': 'KENTA showcased his striking.'},
            ]),
            # Final Battle 2006
            ({
                'name': 'Final Battle 2006',
                'date': date(2006, 12, 23),
                'venue': 'Manhattan Center',
                'location': 'New York, NY',
                'about': 'End of year showcase.'
            }, [
                {'wrestlers': ['Takeshi Morishima', 'Homicide'], 'winner': 'Homicide',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Homicide won the ROH World title.'},
                {'wrestlers': ['Bryan Danielson', 'Jimmy Rave'], 'winner': 'Bryan Danielson',
                 'match_type': 'Singles', 'about': 'Danielson defeated Rave.'},
            ]),
            # Manhattan Mayhem II
            ({
                'name': 'Manhattan Mayhem II',
                'date': date(2007, 3, 17),
                'venue': 'Manhattan Center',
                'location': 'New York, NY',
                'about': 'Second Manhattan Mayhem event.'
            }, [
                {'wrestlers': ['Takeshi Morishima', 'Nigel McGuinness'], 'winner': 'Takeshi Morishima',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Morishima retained the ROH World title.'},
                {'wrestlers': ['Bryan Danielson', 'KENTA'], 'winner': 'KENTA',
                 'match_type': 'Singles', 'about': 'Rematch from their legendary match.'},
            ]),
            # Final Battle 2007
            ({
                'name': 'Final Battle 2007',
                'date': date(2007, 12, 30),
                'venue': 'Manhattan Center',
                'location': 'New York, NY',
                'about': 'Year-end showcase.'
            }, [
                {'wrestlers': ['Nigel McGuinness', 'Bryan Danielson'], 'winner': 'Nigel McGuinness',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'McGuinness defended the ROH World title.'},
                {'wrestlers': ['Tyler Black', 'Jimmy Jacobs'], 'winner': 'Tyler Black',
                 'match_type': 'Singles', 'about': 'Age of the Fall explodes.'},
            ]),
            # Supercard of Honor III
            ({
                'name': 'Supercard of Honor III',
                'date': date(2008, 3, 29),
                'venue': 'Palumbo Center',
                'location': 'Pittsburgh, PA',
                'about': 'Third Supercard of Honor.'
            }, [
                {'wrestlers': ['Nigel McGuinness', 'Bryan Danielson'], 'winner': 'Nigel McGuinness',
                 'match_type': 'Two out of Three Falls', 'title': 'ROH World', 'about': 'Classic match for the ROH World title.'},
                {'wrestlers': ['Kevin Steen', 'El Generico'], 'winner': 'Steenerico',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'Steenerico retained the tag titles.'},
            ]),
            # Final Battle 2009
            ({
                'name': 'Final Battle 2009',
                'date': date(2009, 12, 19),
                'venue': 'Manhattan Center',
                'location': 'New York, NY',
                'about': 'Year-end event with historic title change.'
            }, [
                {'wrestlers': ['Tyler Black', 'Austin Aries'], 'winner': 'Tyler Black',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Tyler Black won the ROH World title.'},
                {'wrestlers': ['The Briscoe Brothers', 'Kevin Steen', 'El Generico'],
                 'winner': 'The Briscoe Brothers', 'match_type': 'Ladder War', 'title': 'ROH Tag Team',
                 'about': 'Brutal ladder match for the tag titles.'},
            ]),
            # Final Battle 2010
            ({
                'name': 'Final Battle 2010',
                'date': date(2010, 12, 18),
                'venue': 'Manhattan Center',
                'location': 'New York, NY',
                'about': 'Homicide returns, El Generico wins the title.'
            }, [
                {'wrestlers': ['Roderick Strong', 'El Generico'], 'winner': 'El Generico',
                 'match_type': 'Ladder Match', 'title': 'ROH World', 'about': 'El Generico won the ROH World title!'},
                {'wrestlers': ['Kevin Steen', 'Homicide'], 'winner': 'Kevin Steen',
                 'match_type': 'Fight Without Honor', 'about': 'Brutal match.'},
            ]),
            # Best in the World 2011
            ({
                'name': 'Best in the World 2011',
                'date': date(2011, 6, 26),
                'venue': 'Hammerstein Ballroom',
                'location': 'New York, NY',
                'about': 'iPPV debut event.'
            }, [
                {'wrestlers': ['Eddie Edwards', 'Davey Richards'], 'winner': 'Davey Richards',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Richards won the ROH World title.'},
                {'wrestlers': ['Michael Elgin', 'Roderick Strong'], 'winner': 'Michael Elgin',
                 'match_type': 'Singles', 'about': 'Elgin\'s breakout performance.'},
            ]),
            # Final Battle 2012
            ({
                'name': 'Final Battle 2012',
                'date': date(2012, 12, 16),
                'venue': 'Hammerstein Ballroom',
                'location': 'New York, NY',
                'about': 'Kevin Steen\'s reign continues.'
            }, [
                {'wrestlers': ['Kevin Steen', 'El Generico'], 'winner': 'Kevin Steen',
                 'match_type': 'Ladder Match', 'title': 'ROH World', 'about': 'Steen retained in Generico\'s final ROH match.'},
                {'wrestlers': ['The Briscoe Brothers', 'Steve Corino', 'Jimmy Jacobs'],
                 'winner': 'The Briscoe Brothers', 'match_type': 'Tag Team', 'title': 'ROH Tag Team',
                 'about': 'Briscoes retained the tag titles.'},
            ]),
            # Supercard of Honor VIII
            ({
                'name': 'Supercard of Honor VIII',
                'date': date(2014, 4, 4),
                'venue': 'Louisiana Superdome',
                'location': 'New Orleans, LA',
                'about': 'WrestleMania weekend showcase.'
            }, [
                {'wrestlers': ['Adam Cole', 'Jay Briscoe'], 'winner': 'Adam Cole',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Cole retained the ROH World title.'},
                {'wrestlers': ['Kevin Steen', 'Shinsuke Nakamura'], 'winner': 'Shinsuke Nakamura',
                 'match_type': 'Singles', 'about': 'Dream match.'},
                {'wrestlers': ['AJ Styles', 'Roderick Strong'], 'winner': 'AJ Styles',
                 'match_type': 'Singles', 'about': 'Former champions clash.'},
            ]),
            # Final Battle 2014
            ({
                'name': 'Final Battle 2014',
                'date': date(2014, 12, 7),
                'venue': 'Terminal 5',
                'location': 'New York, NY',
                'about': 'Jay Briscoe recaptures the title.'
            }, [
                {'wrestlers': ['Jay Briscoe', 'Michael Elgin', 'Adam Cole', 'Tommaso Ciampa'],
                 'winner': 'Jay Briscoe', 'match_type': 'Four Corner Survival', 'title': 'ROH World',
                 'about': 'Jay Briscoe won his third ROH World title.'},
                {'wrestlers': ['The Young Bucks', 'reDRagon'], 'winner': 'The Young Bucks',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'Young Bucks won the tag titles.'},
            ]),
            # Supercard of Honor XI
            ({
                'name': 'Supercard of Honor XI',
                'date': date(2017, 4, 1),
                'venue': 'Lakeland Center',
                'location': 'Lakeland, FL',
                'about': 'WrestleMania weekend showcase.'
            }, [
                {'wrestlers': ['Christopher Daniels', 'Adam Cole'], 'winner': 'Christopher Daniels',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Daniels won his first ROH World title at 46!'},
                {'wrestlers': ['The Young Bucks', 'The Hardys'], 'winner': 'The Young Bucks',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'Legends vs new generation.'},
            ]),
            # Final Battle 2018
            ({
                'name': 'Final Battle 2018',
                'date': date(2018, 12, 14),
                'venue': 'Hammerstein Ballroom',
                'location': 'New York, NY',
                'about': 'Jay Lethal\'s reign continues.'
            }, [
                {'wrestlers': ['Jay Lethal', 'Cody'], 'winner': 'Jay Lethal',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Lethal retained against Cody.'},
                {'wrestlers': ['The Briscoe Brothers', 'SCU'], 'winner': 'The Briscoe Brothers',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'Briscoes retained.'},
            ]),
            # Supercard of Honor XV (AEW Era)
            ({
                'name': 'Supercard of Honor XV',
                'date': date(2022, 4, 1),
                'venue': 'Curtis Culwell Center',
                'location': 'Garland, TX',
                'attendance': 3500,
                'about': 'First ROH show under AEW ownership.'
            }, [
                {'wrestlers': ['Jonathan Gresham', 'Bandido'], 'winner': 'Jonathan Gresham',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Unified ROH World title match.'},
                {'wrestlers': ['Wheeler Yuta', 'Josh Woods'], 'winner': 'Wheeler Yuta',
                 'match_type': 'Singles', 'title': 'ROH Pure', 'about': 'Yuta won the Pure Championship.'},
                {'wrestlers': ['FTR', 'The Briscoe Brothers'], 'winner': 'FTR',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'FTR won the ROH Tag Team titles.'},
                {'wrestlers': ['Mercedes Martinez', 'Deonna Purrazzo'], 'winner': 'Mercedes Martinez',
                 'match_type': 'Singles', 'title': 'ROH Women', 'about': 'Martinez won the Women\'s title.'},
            ]),
            # Death Before Dishonor 2022
            ({
                'name': 'Death Before Dishonor 2022',
                'date': date(2022, 7, 23),
                'venue': 'Tsongas Center',
                'location': 'Lowell, MA',
                'attendance': 4500,
                'about': 'First DBD under AEW.'
            }, [
                {'wrestlers': ['Claudio Castagnoli', 'Jonathan Gresham'], 'winner': 'Claudio Castagnoli',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Claudio won the ROH World title!'},
                {'wrestlers': ['FTR', 'The Briscoe Brothers'], 'winner': 'FTR',
                 'match_type': '2 out of 3 Falls', 'title': 'ROH Tag Team', 'about': 'Classic tag team match.'},
                {'wrestlers': ['Daniel Garcia', 'Wheeler Yuta'], 'winner': 'Daniel Garcia',
                 'match_type': 'Singles', 'title': 'ROH Pure', 'about': 'Garcia won the Pure title.'},
            ]),
            # Final Battle 2022
            ({
                'name': 'Final Battle 2022',
                'date': date(2022, 12, 10),
                'venue': 'College Park Center',
                'location': 'Arlington, TX',
                'about': 'Year-end ROH showcase.'
            }, [
                {'wrestlers': ['Claudio Castagnoli', 'Chris Jericho'], 'winner': 'Chris Jericho',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Jericho won the ROH World title.'},
                {'wrestlers': ['Athena', 'Mercedes Martinez'], 'winner': 'Athena',
                 'match_type': 'Singles', 'title': 'ROH Women', 'about': 'Athena began her historic reign.'},
                {'wrestlers': ['FTR', 'Shane Taylor Promotions'], 'winner': 'FTR',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'FTR retained the tag titles.'},
            ]),
            # Supercard of Honor 2023
            ({
                'name': 'Supercard of Honor 2023',
                'date': date(2023, 3, 31),
                'venue': 'Wintrust Arena',
                'location': 'Chicago, IL',
                'attendance': 5000,
                'about': 'WrestleMania weekend event.'
            }, [
                {'wrestlers': ['Claudio Castagnoli', 'Eddie Kingston'], 'winner': 'Eddie Kingston',
                 'match_type': 'Singles', 'title': 'ROH World', 'about': 'Eddie Kingston finally won the ROH World title!'},
                {'wrestlers': ['Athena', 'Yuka Sakazaki'], 'winner': 'Athena',
                 'match_type': 'Singles', 'title': 'ROH Women', 'about': 'Athena\'s reign continued.'},
                {'wrestlers': ['The Lucha Brothers', 'FTR'], 'winner': 'The Lucha Brothers',
                 'match_type': 'Tag Team', 'title': 'ROH Tag Team', 'about': 'Lucha Brothers won the tag titles.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(roh, event_data, matches)
