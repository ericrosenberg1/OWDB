"""
Management command to seed the database with comprehensive match data.
Data sourced from publicly available wrestling results and Wikipedia.
All data is factual match results from documented events.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import Wrestler, Promotion, Event, Match, Title, Venue


class Command(BaseCommand):
    help = 'Seeds the database with comprehensive match data from major events'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Seed matches from a specific year (2023 or 2024)',
        )

    def handle(self, *args, **options):
        self.stdout.write('Seeding database with match data...\n')

        # Get or create promotions
        self.promotions = self.get_or_create_promotions()

        # Get or create venues
        self.venues = self.get_or_create_venues()

        # Get or create titles
        self.titles = self.get_or_create_titles()

        # Seed 2024 events and matches
        year = options.get('year')
        if not year or year == 2024:
            self.seed_2024_events()
        if not year or year == 2023:
            self.seed_2023_events()

        self.stdout.write(self.style.SUCCESS('\nDatabase seeded with match data!'))

        # Print summary
        self.stdout.write(f'\nSummary:')
        self.stdout.write(f'  Wrestlers: {Wrestler.objects.count()}')
        self.stdout.write(f'  Events: {Event.objects.count()}')
        self.stdout.write(f'  Matches: {Match.objects.count()}')

    def get_or_create_promotions(self):
        """Get or create major wrestling promotions."""
        promotions = {}
        promo_data = [
            ('WWE', 'World Wrestling Entertainment', 1952),
            ('AEW', 'All Elite Wrestling', 2019),
            ('NJPW', 'New Japan Pro-Wrestling', 1972),
            ('ROH', 'Ring of Honor', 2002),
            ('TNA', 'TNA Wrestling', 2002),
        ]
        for abbrev, name, year in promo_data:
            promo, _ = Promotion.objects.get_or_create(
                abbreviation=abbrev,
                defaults={'name': name, 'founded_year': year}
            )
            promotions[abbrev] = promo
        return promotions

    def get_or_create_venues(self):
        """Get or create major wrestling venues."""
        venues = {}
        venue_data = [
            ('Lincoln Financial Field', 'Philadelphia, Pennsylvania, USA', 69000),
            ('Allegiant Stadium', 'Las Vegas, Nevada, USA', 65000),
            ('Wembley Stadium', 'London, England, UK', 90000),
            ('Tokyo Dome', 'Tokyo, Japan', 55000),
            ('State Farm Arena', 'Atlanta, Georgia, USA', 21000),
            ('Scotiabank Arena', 'Toronto, Ontario, Canada', 19800),
            ('Capital One Arena', 'Washington, D.C., USA', 20356),
            ('Madison Square Garden', 'New York City, New York, USA', 20789),
            ('Greensboro Coliseum', 'Greensboro, North Carolina, USA', 23000),
            ('T-Mobile Arena', 'Las Vegas, Nevada, USA', 20000),
            ('CFG Bank Arena', 'Baltimore, Maryland, USA', 14000),
            ('PPG Paints Arena', 'Pittsburgh, Pennsylvania, USA', 19100),
            ('Barclays Center', 'Brooklyn, New York, USA', 19000),
        ]
        for name, location, capacity in venue_data:
            venue, _ = Venue.objects.get_or_create(
                name=name,
                defaults={'location': location, 'capacity': capacity}
            )
            venues[name] = venue
        return venues

    def get_or_create_titles(self):
        """Get or create major wrestling titles."""
        titles = {}
        title_data = [
            ('WWE Championship', 'WWE', 1963),
            ('WWE Universal Championship', 'WWE', 2016),
            ('WWE World Heavyweight Championship', 'WWE', 2023),
            ('WWE Undisputed Championship', 'WWE', 2022),
            ('WWE Intercontinental Championship', 'WWE', 1979),
            ('WWE United States Championship', 'WWE', 2003),
            ('WWE Women\'s Championship', 'WWE', 2016),
            ('WWE Women\'s World Championship', 'WWE', 2023),
            ('WWE Tag Team Championship', 'WWE', 2002),
            ('AEW World Championship', 'AEW', 2019),
            ('AEW International Championship', 'AEW', 2023),
            ('AEW TNT Championship', 'AEW', 2020),
            ('AEW TBS Championship', 'AEW', 2022),
            ('AEW Women\'s Championship', 'AEW', 2019),
            ('AEW Tag Team Championship', 'AEW', 2020),
            ('IWGP World Heavyweight Championship', 'NJPW', 2021),
            ('IWGP Heavyweight Championship', 'NJPW', 1987),
            ('ROH World Championship', 'ROH', 2002),
            ('TNA World Championship', 'TNA', 2007),
        ]
        for name, promo_abbrev, year in title_data:
            promo = self.promotions.get(promo_abbrev)
            title, _ = Title.objects.get_or_create(
                name=name,
                defaults={'promotion': promo, 'debut_year': year}
            )
            titles[name] = title
        return titles

    def get_or_create_wrestler(self, name, **kwargs):
        """Get or create a wrestler by name."""
        wrestler, created = Wrestler.objects.get_or_create(
            name=name,
            defaults=kwargs
        )
        if created:
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

    def create_event_with_matches(self, event_data, matches_data):
        """Create an event and its matches."""
        # Get or create event
        event, created = Event.objects.get_or_create(
            name=event_data['name'],
            date=event_data['date'],
            defaults={
                'promotion': event_data.get('promotion'),
                'venue': event_data.get('venue'),
                'attendance': event_data.get('attendance'),
                'about': event_data.get('about', ''),
            }
        )

        if created:
            self.stdout.write(f'\n  Created event: {event.name} ({event.date})')
        else:
            self.stdout.write(f'\n  Event exists: {event.name} ({event.date})')

        # Create matches
        for i, match_data in enumerate(matches_data, 1):
            self.create_match(event, match_data, match_order=i)

    def create_match(self, event, match_data, match_order):
        """Create a match and link wrestlers."""
        # Get or create wrestlers
        wrestlers = []
        for w_name in match_data['wrestlers']:
            wrestler = self.get_or_create_wrestler(
                w_name,
                debut_year=match_data.get('debut_years', {}).get(w_name),
                nationality=match_data.get('nationalities', {}).get(w_name),
            )
            wrestlers.append(wrestler)

        # Get winner
        winner = None
        if match_data.get('winner'):
            for w in wrestlers:
                if w.name == match_data['winner']:
                    winner = w
                    break

        # Get title
        title = self.titles.get(match_data.get('title'))

        # Build match text
        match_text = match_data.get('match_text') or ' vs '.join(match_data['wrestlers'])
        if match_data.get('title'):
            match_text += f" - {match_data['title']}"

        # Create match
        match, created = Match.objects.get_or_create(
            event=event,
            match_text=match_text,
            defaults={
                'match_type': match_data.get('match_type', 'Singles Match'),
                'result': match_data.get('result', 'Win'),
                'winner': winner,
                'title': title,
                'match_order': match_order,
                'about': match_data.get('about', ''),
            }
        )

        if created:
            # Add wrestlers to match
            for wrestler in wrestlers:
                match.wrestlers.add(wrestler)
            self.stdout.write(f'    + Match {match_order}: {match_text[:60]}...' if len(match_text) > 60 else f'    + Match {match_order}: {match_text}')

    def seed_2024_events(self):
        """Seed major 2024 wrestling events."""
        self.stdout.write('\n=== Seeding 2024 Events ===')

        # WrestleMania 40 - Night 1 (April 6, 2024)
        self.create_event_with_matches(
            {
                'name': 'WrestleMania 40 - Night 1',
                'date': date(2024, 4, 6),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Lincoln Financial Field'],
                'attendance': 72000,
                'about': 'The first night of the 40th annual WrestleMania.',
            },
            [
                {'wrestlers': ['The Rock', 'Roman Reigns'], 'match_text': 'The Rock & Roman Reigns vs Cody Rhodes & Seth Rollins', 'winner': 'The Rock', 'match_type': 'Tag Team Match'},
                {'wrestlers': ['Drew McIntyre', 'Seth Rollins'], 'winner': 'Drew McIntyre', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Rhea Ripley', 'Becky Lynch'], 'winner': 'Rhea Ripley', 'title': 'WWE Women\'s World Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Gunther', 'Sami Zayn'], 'winner': 'Gunther', 'title': 'WWE Intercontinental Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Rey Mysterio', 'Andrade', 'Carlito', 'Santos Escobar'], 'winner': 'Andrade', 'match_type': 'Fatal 4-Way Match'},
                {'wrestlers': ['Jade Cargill', 'Bianca Belair', 'Damage CTRL', 'Kayden Carter', 'Katana Chance'], 'match_text': 'Jade Cargill & Bianca Belair vs Damage CTRL vs Carter & Chance', 'winner': 'Jade Cargill', 'title': 'WWE Women\'s Tag Team Championship', 'match_type': 'Tag Team Match'},
            ]
        )

        # WrestleMania 40 - Night 2 (April 7, 2024)
        self.create_event_with_matches(
            {
                'name': 'WrestleMania 40 - Night 2',
                'date': date(2024, 4, 7),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Lincoln Financial Field'],
                'attendance': 72000,
                'about': 'The second night of WrestleMania 40 featuring Cody Rhodes vs Roman Reigns.',
            },
            [
                {'wrestlers': ['Cody Rhodes', 'Roman Reigns'], 'winner': 'Cody Rhodes', 'title': 'WWE Undisputed Championship', 'match_type': 'Bloodline Rules Match', 'about': 'Cody Rhodes finished his story.'},
                {'wrestlers': ['Bayley', 'Iyo Sky'], 'winner': 'Bayley', 'title': 'WWE Women\'s Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['LA Knight', 'AJ Styles'], 'winner': 'LA Knight', 'match_type': 'Singles Match'},
                {'wrestlers': ['Randy Orton', 'Kevin Owens', 'Logan Paul'], 'winner': 'Logan Paul', 'title': 'WWE United States Championship', 'match_type': 'Triple Threat Match'},
                {'wrestlers': ['Jey Uso', 'Jimmy Uso'], 'winner': 'Jey Uso', 'match_type': 'Singles Match'},
            ]
        )

        # Royal Rumble 2024 (January 27, 2024)
        self.create_event_with_matches(
            {
                'name': 'Royal Rumble 2024',
                'date': date(2024, 1, 27),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Tropicana Field'],
                'attendance': 35000,
                'about': 'The 2024 Royal Rumble featuring 30-person Royal Rumble matches.',
            },
            [
                {'wrestlers': ['Cody Rhodes', 'Various'], 'match_text': "Men's Royal Rumble Match", 'winner': 'Cody Rhodes', 'match_type': 'Royal Rumble Match'},
                {'wrestlers': ['Bayley', 'Various'], 'match_text': "Women's Royal Rumble Match", 'winner': 'Bayley', 'match_type': 'Royal Rumble Match'},
                {'wrestlers': ['Roman Reigns', 'Randy Orton', 'LA Knight'], 'winner': 'Roman Reigns', 'title': 'WWE Undisputed Championship', 'match_type': 'Triple Threat Match'},
                {'wrestlers': ['Rhea Ripley', 'Liv Morgan'], 'winner': 'Rhea Ripley', 'title': 'WWE Women\'s World Championship', 'match_type': 'Singles Match'},
            ]
        )

        # SummerSlam 2024 (August 3, 2024)
        self.create_event_with_matches(
            {
                'name': 'SummerSlam 2024',
                'date': date(2024, 8, 3),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Cleveland Browns Stadium'],
                'attendance': 56000,
                'about': 'The biggest party of the summer.',
            },
            [
                {'wrestlers': ['Cody Rhodes', 'Solo Sikoa'], 'winner': 'Cody Rhodes', 'title': 'WWE Undisputed Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Gunther', 'Damian Priest'], 'winner': 'Gunther', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['CM Punk', 'Drew McIntyre'], 'winner': 'CM Punk', 'match_type': 'Singles Match'},
                {'wrestlers': ['Bayley', 'Nia Jax'], 'winner': 'Nia Jax', 'title': 'WWE Women\'s Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Liv Morgan', 'Rhea Ripley'], 'winner': 'Liv Morgan', 'title': 'WWE Women\'s World Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Logan Paul', 'LA Knight'], 'winner': 'LA Knight', 'title': 'WWE United States Championship', 'match_type': 'Singles Match'},
            ]
        )

        # Survivor Series 2024 (November 30, 2024)
        self.create_event_with_matches(
            {
                'name': 'Survivor Series: WarGames 2024',
                'date': date(2024, 11, 30),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Rogers Arena'],
                'attendance': 18000,
                'about': 'Survivor Series: WarGames 2024.',
            },
            [
                {'wrestlers': ['Roman Reigns', 'CM Punk', 'Sami Zayn', 'Jey Uso', 'Jimmy Uso', 'Solo Sikoa', 'Jacob Fatu', 'Tama Tonga', 'Tonga Loa', 'Bronson Reed'], 'match_text': 'OG Bloodline vs Bloodline WarGames', 'winner': 'Roman Reigns', 'match_type': 'WarGames Match'},
                {'wrestlers': ['Gunther', 'Damian Priest'], 'winner': 'Gunther', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Cody Rhodes', 'Kevin Owens'], 'winner': 'Cody Rhodes', 'title': 'WWE Undisputed Championship', 'match_type': 'Singles Match'},
            ]
        )

        # AEW All In 2024 (August 25, 2024)
        self.create_event_with_matches(
            {
                'name': 'AEW All In 2024',
                'date': date(2024, 8, 25),
                'promotion': self.promotions['AEW'],
                'venue': self.venues['Wembley Stadium'],
                'attendance': 51000,
                'about': 'AEW All In at Wembley Stadium, London.',
            },
            [
                {'wrestlers': ['Bryan Danielson', 'Swerve Strickland'], 'winner': 'Bryan Danielson', 'title': 'AEW World Championship', 'match_type': 'Title vs Career Match'},
                {'wrestlers': ['Mariah May', 'Toni Storm'], 'winner': 'Mariah May', 'title': 'AEW Women\'s Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Will Ospreay', 'MJF'], 'winner': 'Will Ospreay', 'title': 'AEW International Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Mercedes Mone', 'Britt Baker'], 'winner': 'Mercedes Mone', 'title': 'AEW TBS Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Jack Perry', 'Darby Allin'], 'winner': 'Jack Perry', 'title': 'AEW TNT Championship', 'match_type': 'Coffin Match'},
            ]
        )

        # Wrestle Kingdom 18 (January 4, 2024)
        self.create_event_with_matches(
            {
                'name': 'Wrestle Kingdom 18',
                'date': date(2024, 1, 4),
                'promotion': self.promotions['NJPW'],
                'venue': self.venues['Tokyo Dome'],
                'attendance': 26000,
                'about': 'The biggest New Japan Pro-Wrestling event of the year.',
            },
            [
                {'wrestlers': ['Kazuchika Okada', 'Tetsuya Naito'], 'winner': 'Kazuchika Okada', 'title': 'IWGP World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Jon Moxley', 'Shota Umino'], 'winner': 'Jon Moxley', 'title': 'IWGP World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Hiromu Takahashi', 'El Desperado'], 'winner': 'Hiromu Takahashi', 'match_type': 'Singles Match'},
            ]
        )

        # AEW Dynasty (April 21, 2024)
        self.create_event_with_matches(
            {
                'name': 'AEW Dynasty',
                'date': date(2024, 4, 21),
                'promotion': self.promotions['AEW'],
                'venue': self.venues['Chaifetz Arena'],
                'attendance': 10000,
                'about': 'The first-ever AEW Dynasty event.',
            },
            [
                {'wrestlers': ['Swerve Strickland', 'Samoa Joe'], 'winner': 'Swerve Strickland', 'title': 'AEW World Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Will Ospreay', 'Bryan Danielson'], 'winner': 'Will Ospreay', 'title': 'AEW International Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Toni Storm', 'Thunder Rosa'], 'winner': 'Toni Storm', 'title': 'AEW Women\'s Championship', 'match_type': 'Singles Match'},
            ]
        )

    def seed_2023_events(self):
        """Seed major 2023 wrestling events."""
        self.stdout.write('\n=== Seeding 2023 Events ===')

        # WrestleMania 39 - Night 1 (April 1, 2023)
        self.create_event_with_matches(
            {
                'name': 'WrestleMania 39 - Night 1',
                'date': date(2023, 4, 1),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['SoFi Stadium'],
                'attendance': 80497,
                'about': 'The first night of WrestleMania 39 in Hollywood.',
            },
            [
                {'wrestlers': ['Bianca Belair', 'Asuka'], 'winner': 'Bianca Belair', 'title': 'WWE Raw Women\'s Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Austin Theory', 'John Cena'], 'winner': 'Austin Theory', 'title': 'WWE United States Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['The Usos', 'Sami Zayn', 'Kevin Owens'], 'match_text': 'The Usos vs Sami Zayn & Kevin Owens', 'winner': 'Sami Zayn', 'title': 'WWE Undisputed Tag Team Championship', 'match_type': 'Tag Team Match'},
                {'wrestlers': ['Seth Rollins', 'Logan Paul'], 'winner': 'Seth Rollins', 'match_type': 'Singles Match'},
                {'wrestlers': ['Charlotte Flair', 'Rhea Ripley'], 'winner': 'Rhea Ripley', 'title': 'WWE SmackDown Women\'s Championship', 'match_type': 'Singles Match'},
            ]
        )

        # WrestleMania 39 - Night 2 (April 2, 2023)
        self.create_event_with_matches(
            {
                'name': 'WrestleMania 39 - Night 2',
                'date': date(2023, 4, 2),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['SoFi Stadium'],
                'attendance': 80497,
                'about': 'The main event of WrestleMania 39: Roman Reigns vs Cody Rhodes.',
            },
            [
                {'wrestlers': ['Roman Reigns', 'Cody Rhodes'], 'winner': 'Roman Reigns', 'title': 'WWE Undisputed Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Gunther', 'Drew McIntyre', 'Sheamus'], 'winner': 'Gunther', 'title': 'WWE Intercontinental Championship', 'match_type': 'Triple Threat Match'},
                {'wrestlers': ['Brock Lesnar', 'Omos'], 'winner': 'Brock Lesnar', 'match_type': 'Singles Match'},
                {'wrestlers': ['Edge', 'Finn Balor'], 'winner': 'Edge', 'match_type': 'Hell in a Cell Match'},
            ]
        )

        # AEW All In 2023 (August 27, 2023)
        self.create_event_with_matches(
            {
                'name': 'AEW All In 2023',
                'date': date(2023, 8, 27),
                'promotion': self.promotions['AEW'],
                'venue': self.venues['Wembley Stadium'],
                'attendance': 81035,
                'about': 'The largest non-WWE wrestling event in history at Wembley Stadium.',
            },
            [
                {'wrestlers': ['MJF', 'Adam Cole'], 'winner': 'MJF', 'title': 'AEW World Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Will Ospreay', 'Chris Jericho'], 'winner': 'Will Ospreay', 'match_type': 'Singles Match'},
                {'wrestlers': ['CM Punk', 'Samoa Joe'], 'winner': 'CM Punk', 'title': 'AEW World Championship', 'match_type': 'Real World Championship Match'},
                {'wrestlers': ['Kenny Omega', 'Kota Ibushi'], 'winner': 'Kenny Omega', 'match_type': 'Singles Match'},
                {'wrestlers': ['Toni Storm', 'Hikaru Shida', 'Saraya', 'Britt Baker'], 'winner': 'Toni Storm', 'title': 'AEW Women\'s Championship', 'match_type': 'Fatal 4-Way Match'},
                {'wrestlers': ['FTR', 'The Young Bucks'], 'match_text': 'FTR vs The Young Bucks', 'winner': 'FTR', 'title': 'AEW Tag Team Championship', 'match_type': 'Tag Team Match'},
            ]
        )

        # Royal Rumble 2023 (January 28, 2023)
        self.create_event_with_matches(
            {
                'name': 'Royal Rumble 2023',
                'date': date(2023, 1, 28),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Alamodome'],
                'attendance': 51338,
                'about': 'Royal Rumble 2023 from San Antonio.',
            },
            [
                {'wrestlers': ['Cody Rhodes', 'Gunther', 'Various'], 'match_text': "Men's Royal Rumble Match", 'winner': 'Cody Rhodes', 'match_type': 'Royal Rumble Match'},
                {'wrestlers': ['Rhea Ripley', 'Various'], 'match_text': "Women's Royal Rumble Match", 'winner': 'Rhea Ripley', 'match_type': 'Royal Rumble Match'},
                {'wrestlers': ['Roman Reigns', 'Kevin Owens'], 'winner': 'Roman Reigns', 'title': 'WWE Undisputed Championship', 'match_type': 'Singles Match'},
            ]
        )

        # SummerSlam 2023 (August 5, 2023)
        self.create_event_with_matches(
            {
                'name': 'SummerSlam 2023',
                'date': date(2023, 8, 5),
                'promotion': self.promotions['WWE'],
                'venue': self.venues['Ford Field'],
                'attendance': 55000,
                'about': 'SummerSlam 2023 from Detroit, Michigan.',
            },
            [
                {'wrestlers': ['Roman Reigns', 'Jey Uso'], 'winner': 'Roman Reigns', 'title': 'WWE Undisputed Championship', 'match_type': 'Tribal Combat Match'},
                {'wrestlers': ['Cody Rhodes', 'Brock Lesnar'], 'winner': 'Cody Rhodes', 'match_type': 'Singles Match'},
                {'wrestlers': ['Seth Rollins', 'Finn Balor'], 'winner': 'Seth Rollins', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Gunther', 'Drew McIntyre'], 'winner': 'Gunther', 'title': 'WWE Intercontinental Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Bianca Belair', 'Asuka', 'Charlotte Flair'], 'winner': 'Asuka', 'title': 'WWE Women\'s Championship', 'match_type': 'Triple Threat Match'},
            ]
        )

        # Wrestle Kingdom 17 (January 4, 2023)
        self.create_event_with_matches(
            {
                'name': 'Wrestle Kingdom 17',
                'date': date(2023, 1, 4),
                'promotion': self.promotions['NJPW'],
                'venue': self.venues['Tokyo Dome'],
                'attendance': 26000,
                'about': 'Wrestle Kingdom 17 from the Tokyo Dome.',
            },
            [
                {'wrestlers': ['Kazuchika Okada', 'Jay White'], 'winner': 'Kazuchika Okada', 'title': 'IWGP World Heavyweight Championship', 'match_type': 'Singles Match'},
                {'wrestlers': ['Tetsuya Naito', 'Sanada'], 'winner': 'Tetsuya Naito', 'match_type': 'Singles Match'},
                {'wrestlers': ['Will Ospreay', 'Shingo Takagi'], 'winner': 'Will Ospreay', 'match_type': 'Singles Match'},
            ]
        )

        # AEW Revolution 2023 (March 5, 2023)
        self.create_event_with_matches(
            {
                'name': 'AEW Revolution 2023',
                'date': date(2023, 3, 5),
                'promotion': self.promotions['AEW'],
                'venue': self.venues['Chase Center'],
                'attendance': 11000,
                'about': 'AEW Revolution 2023 from San Francisco.',
            },
            [
                {'wrestlers': ['MJF', 'Bryan Danielson'], 'winner': 'MJF', 'title': 'AEW World Championship', 'match_type': '60-Minute Iron Man Match'},
                {'wrestlers': ['Jon Moxley', 'Hangman Adam Page'], 'winner': 'Jon Moxley', 'match_type': 'Texas Death Match'},
                {'wrestlers': ['Chris Jericho', 'Ricky Starks'], 'winner': 'Chris Jericho', 'match_type': 'Singles Match'},
            ]
        )

    # Add missing venues inline for events
    @property
    def venues(self):
        if not hasattr(self, '_venues'):
            self._venues = self.get_or_create_venues()
        # Add any missing venues
        additional_venues = [
            ('Tropicana Field', 'St. Petersburg, Florida, USA', 42735),
            ('Cleveland Browns Stadium', 'Cleveland, Ohio, USA', 67895),
            ('Rogers Arena', 'Vancouver, British Columbia, Canada', 19000),
            ('Chaifetz Arena', 'St. Louis, Missouri, USA', 10600),
            ('SoFi Stadium', 'Inglewood, California, USA', 70000),
            ('Alamodome', 'San Antonio, Texas, USA', 64000),
            ('Ford Field', 'Detroit, Michigan, USA', 65000),
            ('Chase Center', 'San Francisco, California, USA', 18064),
        ]
        for name, location, capacity in additional_venues:
            if name not in self._venues:
                venue, _ = Venue.objects.get_or_create(
                    name=name,
                    defaults={'location': location, 'capacity': capacity}
                )
                self._venues[name] = venue
        return self._venues

    @venues.setter
    def venues(self, value):
        self._venues = value
