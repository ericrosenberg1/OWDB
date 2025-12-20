"""
Seed historic AEW Dynamite and Rampage episodes with matches and significant moments.

Usage:
    python manage.py seed_aew_tv
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic AEW Dynamite and Rampage episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding AEW TV Episodes ===\n'))

        aew = Promotion.objects.filter(abbreviation='AEW').first()
        if not aew:
            aew = Promotion.objects.create(
                name='All Elite Wrestling',
                abbreviation='AEW',
                founded_year=2019
            )
            self.stdout.write('  + Created AEW promotion')

        self.seed_dynamite_2019(aew)
        self.seed_dynamite_2020(aew)
        self.seed_dynamite_2021(aew)
        self.seed_dynamite_2022(aew)
        self.seed_dynamite_2023(aew)
        self.seed_dynamite_2024(aew)
        self.seed_rampage(aew)
        self.seed_collision(aew)

        self.stdout.write(self.style.SUCCESS('\n=== AEW TV Seeding Complete ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')

    def get_or_create_wrestler(self, name):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            slug = slugify(name)
            wrestler = Wrestler.objects.filter(slug=slug).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(name=name)
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

    def get_or_create_venue(self, name, location=None):
        """Get or create a venue."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.create(name=name, location=location)
        return venue

    def get_or_create_title(self, name, promotion):
        """Get or create a title."""
        title = Title.objects.filter(name__iexact=name).first()
        if not title:
            title = Title.objects.create(name=name, promotion=promotion)
            self.stdout.write(f'  + Created title: {name}')
        return title

    def create_episode_with_matches(self, promotion, episode_data, matches_data):
        """Create a TV episode with its matches."""
        episode_date = episode_data['date']
        slug = slugify(f"{episode_data['name']}-{episode_date}")

        event = Event.objects.filter(slug=slug).first()
        if event:
            return event, False

        venue = None
        if 'venue' in episode_data:
            venue = self.get_or_create_venue(
                episode_data['venue'],
                episode_data.get('location')
            )

        event = Event.objects.create(
            name=episode_data['name'],
            slug=slug,
            date=episode_date,
            promotion=promotion,
            venue=venue,
            
            about=episode_data.get('about', '')
        )

        for i, match_data in enumerate(matches_data, 1):
            self.create_match(event, match_data, i, promotion)

        self.stdout.write(self.style.SUCCESS(
            f'  Created: {episode_data["name"]} ({episode_date}) - {len(matches_data)} matches'
        ))
        return event, True

    def create_match(self, event, match_data, order, promotion):
        """Create a match for an event."""
        wrestlers = []
        for wrestler_name in match_data.get('wrestlers', []):
            wrestler = self.get_or_create_wrestler(wrestler_name)
            wrestlers.append(wrestler)

        winner = None
        if match_data.get('winner'):
            winner = self.get_or_create_wrestler(match_data['winner'])

        title = None
        if match_data.get('title'):
            title = self.get_or_create_title(match_data['title'], promotion)

        match = Match.objects.create(
            event=event,
            match_type=match_data.get('match_type', 'Singles'),
            winner=winner,
            title=title,
            order=order,
            title_changed=match_data.get('title_changed', False),
            about=match_data.get('about', '')
        )
        match.wrestlers.set(wrestlers)
        return match

    def seed_dynamite_2019(self, aew):
        """Seed the first AEW Dynamite episodes from 2019."""
        self.stdout.write('\n--- 2019: AEW Dynamite Debuts ---\n')

        # First Dynamite Ever - October 2, 2019
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2019, 10, 2),
            'venue': 'Capital One Arena',
            'location': 'Washington, DC',
            'about': 'The very first episode of AEW Dynamite. A new era in professional wrestling begins.'
        }, [
            {'wrestlers': ['Cody', 'Sammy Guevara'], 'winner': 'Cody',
             'match_type': 'Singles', 'about': 'The first match in AEW Dynamite history.'},
            {'wrestlers': ['The Young Bucks', 'Private Party'], 'winner': 'Private Party',
             'match_type': 'Tag Team', 'about': 'Shocking upset as Private Party defeated The Young Bucks.'},
            {'wrestlers': ['Pac', 'Adam Page'], 'winner': 'Pac',
             'match_type': 'Singles', 'about': 'The Bastard defeated the Anxious Millennial Cowboy.'},
            {'wrestlers': ['Chris Jericho', 'Adam Page'], 'winner': 'No Contest',
             'match_type': 'Segment', 'about': 'Jericho attacked Page and the Inner Circle was revealed.'},
        ])

        # Jericho as First Champion
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2019, 10, 16),
            'venue': 'Agganis Arena',
            'location': 'Boston, MA',
            'about': 'Chris Jericho celebrated as AEW World Champion with The Inner Circle.'
        }, [
            {'wrestlers': ['Chris Jericho', 'Dustin Rhodes'], 'winner': 'Chris Jericho',
             'match_type': 'Singles', 'title': 'AEW World Championship',
             'about': 'Le Champion defended his title.'},
            {'wrestlers': ['Jon Moxley', 'Shawn Spears'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'about': 'Moxley established himself as a main eventer.'},
        ])

        # Full Gear Build
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2019, 11, 6),
            'venue': 'Chesapeake Energy Arena',
            'location': 'Oklahoma City, OK',
            'about': 'Building to the Full Gear PPV.'
        }, [
            {'wrestlers': ['Cody', 'Chris Jericho'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'Cody and Jericho brawled before their title match.'},
            {'wrestlers': ['Kenny Omega', 'Joey Janela'], 'winner': 'Kenny Omega',
             'match_type': 'Lights Out', 'about': 'Omega in a brutal unsanctioned match.'},
        ])

    def seed_dynamite_2020(self, aew):
        """Seed key AEW Dynamite episodes from 2020."""
        self.stdout.write('\n--- 2020: The Pandemic Era ---\n')

        # Revolution Build
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2020, 2, 26),
            'venue': 'Wintrust Arena',
            'location': 'Chicago, IL',
            'about': 'Final Dynamite before Revolution 2020.'
        }, [
            {'wrestlers': ['Jon Moxley', 'Chris Jericho'], 'winner': 'Jon Moxley',
             'match_type': 'Segment', 'about': 'Moxley and Jericho faced off before their title match.'},
            {'wrestlers': ['The Young Bucks', 'Lucha Brothers'], 'winner': 'The Young Bucks',
             'match_type': 'Tag Team', 'about': 'Elite tag team action.'},
        ])

        # Pandemic Era Begins - First Empty Arena Show
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2020, 3, 18),
            'venue': 'Daily\'s Place',
            'location': 'Jacksonville, FL',
            'about': 'First Dynamite with no fans due to COVID-19 pandemic.'
        }, [
            {'wrestlers': ['Cody', 'Jimmy Havoc'], 'winner': 'Cody',
             'match_type': 'Singles', 'about': 'AEW continued during the pandemic.'},
            {'wrestlers': ['Jon Moxley', 'Pac'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'title': 'AEW World Championship',
             'about': 'Moxley defended in an empty arena.'},
        ])

        # Stadium Stampede Fallout
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2020, 5, 27),
            'venue': 'Daily\'s Place',
            'location': 'Jacksonville, FL',
            'about': 'Post-Double or Nothing with Stadium Stampede fallout.'
        }, [
            {'wrestlers': ['The Elite', 'Inner Circle'], 'winner': 'The Elite',
             'match_type': 'Segment', 'about': 'Fallout from the iconic Stadium Stampede match.'},
            {'wrestlers': ['Cody', 'Jungle Boy'], 'winner': 'Cody',
             'match_type': 'Singles', 'about': 'Cody faced the rising star.'},
        ])

        # Brodie Lee Tribute Show
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite: Brodie Lee Celebration of Life',
            'date': date(2020, 12, 30),
            'venue': 'Daily\'s Place',
            'location': 'Jacksonville, FL',
            'about': 'Tribute show for the late Brodie Lee. One of the most emotional nights in wrestling history.'
        }, [
            {'wrestlers': ['Various'], 'winner': 'Various',
             'match_type': 'Tribute', 'about': 'The entire show was dedicated to Brodie Lee\'s memory.'},
            {'wrestlers': ['Brodie Lee Jr.', 'AEW Roster'], 'winner': 'Brodie Lee Jr.',
             'match_type': 'Segment', 'about': 'Brodie\'s son was given an AEW contract and the TNT Championship.'},
        ])

    def seed_dynamite_2021(self, aew):
        """Seed key AEW Dynamite episodes from 2021."""
        self.stdout.write('\n--- 2021: CM Punk and Bryan Danielson ---\n')

        # Kenny Omega as Champion
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2021, 1, 6),
            'venue': 'Daily\'s Place',
            'location': 'Jacksonville, FL',
            'about': 'Kenny Omega continued his reign as AEW World Champion.'
        }, [
            {'wrestlers': ['Kenny Omega', 'Rey Fenix'], 'winner': 'Kenny Omega',
             'match_type': 'Singles', 'title': 'AEW World Championship',
             'about': 'Omega vs Fenix in an instant classic.'},
            {'wrestlers': ['The Young Bucks', 'SCU'], 'winner': 'The Young Bucks',
             'match_type': 'Tag Team', 'title': 'AEW World Tag Team Championship',
             'about': 'The Bucks defended.'},
        ])

        # First Dance - CM PUNK RETURNS
        self.create_episode_with_matches(aew, {
            'name': 'AEW Rampage: The First Dance',
            'date': date(2021, 8, 20),
            'venue': 'United Center',
            'location': 'Chicago, IL',
            'about': 'CM PUNK RETURNED TO WRESTLING AFTER 7 YEARS! The most anticipated return in wrestling history.'
        }, [
            {'wrestlers': ['CM Punk', 'Various'], 'winner': 'CM Punk',
             'match_type': 'Return', 'about': 'CM PUNK IS ALL ELITE! Chicago exploded.'},
            {'wrestlers': ['The Young Bucks', 'Lucha Brothers'], 'winner': 'Lucha Brothers',
             'match_type': 'Tag Team', 'title': 'AEW World Tag Team Championship', 'title_changed': True,
             'about': 'Lucha Brothers won the tag titles in an incredible match.'},
        ])

        # Bryan Danielson Debuts - All Out Fallout
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite: Grand Slam',
            'date': date(2021, 9, 22),
            'venue': 'Arthur Ashe Stadium',
            'location': 'Queens, NY',
            'about': 'First Dynamite at Arthur Ashe Stadium with over 20,000 fans.'
        }, [
            {'wrestlers': ['Bryan Danielson', 'Kenny Omega'], 'winner': 'Draw',
             'match_type': 'Singles', 'about': '30-minute draw in an instant classic.'},
            {'wrestlers': ['Malakai Black', 'Cody'], 'winner': 'Malakai Black',
             'match_type': 'Singles', 'about': 'The House of Black continued.'},
            {'wrestlers': ['Ruby Soho', 'Dr. Britt Baker'], 'winner': 'Dr. Britt Baker',
             'match_type': 'Singles', 'title': 'AEW Women\'s World Championship',
             'about': 'The DMD defended her title.'},
        ])

    def seed_dynamite_2022(self, aew):
        """Seed key AEW Dynamite episodes from 2022."""
        self.stdout.write('\n--- 2022: MJF Year ---\n')

        # CM Punk Becomes Champion
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2022, 3, 9),
            'venue': 'Freeman Coliseum',
            'location': 'San Antonio, TX',
            'about': 'Building to Revolution 2022.'
        }, [
            {'wrestlers': ['CM Punk', 'Wardlow'], 'winner': 'CM Punk',
             'match_type': 'Steel Cage', 'about': 'CM Punk escaped the cage.'},
            {'wrestlers': ['Chris Jericho', 'Eddie Kingston'], 'winner': 'Eddie Kingston',
             'match_type': 'Singles', 'about': 'Kingston got revenge on Jericho.'},
        ])

        # Forbidden Door Build
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2022, 6, 22),
            'venue': 'Addition Financial Arena',
            'location': 'Orlando, FL',
            'about': 'Final build to Forbidden Door with NJPW stars.'
        }, [
            {'wrestlers': ['Jon Moxley', 'Hiroshi Tanahashi'], 'winner': 'No Contest',
             'match_type': 'Segment', 'about': 'Mox and Tanahashi faced off before Forbidden Door.'},
            {'wrestlers': ['Kazuchika Okada', 'Adam Cole'], 'winner': 'No Contest',
             'match_type': 'Segment', 'about': 'The Rainmaker appeared.'},
        ])

        # All Out 2022 Fallout - The Media Scrum Aftermath
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2022, 9, 7),
            'venue': 'KeyBank Center',
            'location': 'Buffalo, NY',
            'about': 'Dynamite after All Out. CM Punk and The Elite were stripped of titles after backstage incident.'
        }, [
            {'wrestlers': ['Jon Moxley', 'Various'], 'winner': 'Jon Moxley',
             'match_type': 'Tournament', 'title': 'AEW World Championship',
             'about': 'Mox won tournament final for the vacated world title.'},
            {'wrestlers': ['Chris Jericho', 'Various'], 'winner': 'Chris Jericho',
             'match_type': 'Segment', 'about': 'JAS continued their dominance.'},
        ])

        # MJF Returns as The Devil
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2022, 11, 16),
            'venue': 'Prudential Center',
            'location': 'Newark, NJ',
            'about': 'MJF returned after months away and won the World Title.'
        }, [
            {'wrestlers': ['MJF', 'Jon Moxley'], 'winner': 'MJF',
             'match_type': 'Singles', 'title': 'AEW World Championship', 'title_changed': True,
             'about': 'MJF won the AEW World Championship! The Salt of the Earth became champion.'},
        ])

    def seed_dynamite_2023(self, aew):
        """Seed key AEW Dynamite episodes from 2023."""
        self.stdout.write('\n--- 2023: New Champions Rise ---\n')

        # MJF Reign Continues
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2023, 2, 8),
            'venue': 'Simmons Bank Arena',
            'location': 'North Little Rock, AR',
            'about': 'MJF\'s reign as a babyface champion continued.'
        }, [
            {'wrestlers': ['MJF', 'Bryan Danielson'], 'winner': 'MJF',
             'match_type': 'Singles', 'title': 'AEW World Championship',
             'about': 'MJF vs Bryan in a classic.'},
            {'wrestlers': ['Jon Moxley', 'Brian Cage'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'about': 'Mox in action.'},
        ])

        # Samoa Joe Wins ROH TV Title
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2023, 4, 12),
            'venue': 'MVP Arena',
            'location': 'Albany, NY',
            'about': 'Samoa Joe continued collecting titles.'
        }, [
            {'wrestlers': ['Samoa Joe', 'Wardlow'], 'winner': 'Samoa Joe',
             'match_type': 'Singles', 'about': 'The submission machine.'},
            {'wrestlers': ['The Acclaimed', 'Various'], 'winner': 'The Acclaimed',
             'match_type': 'Tag Team', 'about': 'Scissor me, Daddy Ass!'},
        ])

        # All In London Build
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2023, 8, 23),
            'venue': 'Simmons Bank Arena',
            'location': 'North Little Rock, AR',
            'about': 'Final Dynamite before the historic All In at Wembley Stadium.'
        }, [
            {'wrestlers': ['MJF', 'Adam Cole'], 'winner': 'MJF',
             'match_type': 'Segment', 'about': 'The buildup to All In at Wembley.'},
            {'wrestlers': ['FTR', 'The Young Bucks'], 'winner': 'FTR',
             'match_type': 'Tag Team', 'about': 'Classic tag team action.'},
        ])

    def seed_dynamite_2024(self, aew):
        """Seed key AEW Dynamite episodes from 2024."""
        self.stdout.write('\n--- 2024: Dynasty Era ---\n')

        # 5 Year Anniversary
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite: 5th Anniversary',
            'date': date(2024, 10, 2),
            'venue': 'Petersen Events Center',
            'location': 'Pittsburgh, PA',
            'about': 'Celebrating 5 years of AEW Dynamite.'
        }, [
            {'wrestlers': ['Bryan Danielson', 'Jon Moxley'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'title': 'AEW World Championship', 'title_changed': True,
             'about': 'Moxley won the title on the 5th anniversary.'},
            {'wrestlers': ['Will Ospreay', 'Ricochet'], 'winner': 'Will Ospreay',
             'match_type': 'Singles', 'about': 'High-flying dream match.'},
        ])

        # Swerve Strickland Era
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2024, 5, 1),
            'venue': 'Heritage Bank Center',
            'location': 'Cincinnati, OH',
            'about': 'Post Dynasty. Swerve Strickland as AEW World Champion.'
        }, [
            {'wrestlers': ['Swerve Strickland', 'Killswitch'], 'winner': 'Swerve Strickland',
             'match_type': 'Singles', 'title': 'AEW World Championship',
             'about': 'Swerve\'s House defended his title.'},
            {'wrestlers': ['Will Ospreay', 'Konosuke Takeshita'], 'winner': 'Will Ospreay',
             'match_type': 'Singles', 'title': 'AEW International Championship',
             'about': 'The Aerial Assassin defended.'},
        ])

        # Bryan Danielson Final Run
        self.create_episode_with_matches(aew, {
            'name': 'AEW Dynamite',
            'date': date(2024, 8, 28),
            'venue': 'NOW Arena',
            'location': 'Hoffman Estates, IL',
            'about': 'Bryan Danielson\'s final full-time run continued.'
        }, [
            {'wrestlers': ['Bryan Danielson', 'Jeff Jarrett'], 'winner': 'Bryan Danielson',
             'match_type': 'Singles', 'about': 'The American Dragon in his final stretch.'},
            {'wrestlers': ['The Acclaimed', 'Private Party'], 'winner': 'Private Party',
             'match_type': 'Tag Team', 'title': 'AEW World Tag Team Championship', 'title_changed': True,
             'about': 'Private Party won the tag titles.'},
        ])

    def seed_rampage(self, aew):
        """Seed key AEW Rampage episodes."""
        self.stdout.write('\n--- AEW Rampage ---\n')

        # First Rampage
        self.create_episode_with_matches(aew, {
            'name': 'AEW Rampage',
            'date': date(2021, 8, 13),
            'venue': 'Petersen Events Center',
            'location': 'Pittsburgh, PA',
            'about': 'The very first episode of AEW Rampage on TNT.'
        }, [
            {'wrestlers': ['Jon Moxley', 'Daniel Garcia'], 'winner': 'Jon Moxley',
             'match_type': 'Singles', 'about': 'First match in Rampage history.'},
            {'wrestlers': ['Dr. Britt Baker', 'Red Velvet'], 'winner': 'Dr. Britt Baker',
             'match_type': 'Singles', 'title': 'AEW Women\'s World Championship',
             'about': 'The DMD defended her title.'},
        ])

        # Rampage Grand Slam
        self.create_episode_with_matches(aew, {
            'name': 'AEW Rampage: Grand Slam',
            'date': date(2022, 9, 23),
            'venue': 'Arthur Ashe Stadium',
            'location': 'Queens, NY',
            'about': 'Rampage Grand Slam with a massive NYC crowd.'
        }, [
            {'wrestlers': ['Wardlow', 'Samoa Joe'], 'winner': 'Wardlow',
             'match_type': 'Singles', 'title': 'TNT Championship',
             'about': 'Wardlow defended against Joe.'},
            {'wrestlers': ['Lucha Brothers', 'Private Party'], 'winner': 'Lucha Brothers',
             'match_type': 'Tag Team', 'about': 'High-flying tag team action.'},
        ])

    def seed_collision(self, aew):
        """Seed key AEW Collision episodes."""
        self.stdout.write('\n--- AEW Collision ---\n')

        # First Collision
        self.create_episode_with_matches(aew, {
            'name': 'AEW Collision',
            'date': date(2023, 6, 17),
            'venue': 'United Center',
            'location': 'Chicago, IL',
            'about': 'The premiere of AEW Collision on TNT. CM Punk\'s show.'
        }, [
            {'wrestlers': ['CM Punk', 'Various'], 'winner': 'CM Punk',
             'match_type': 'Segment', 'about': 'CM Punk opened the first Collision.'},
            {'wrestlers': ['FTR', 'The Gunns'], 'winner': 'FTR',
             'match_type': 'Tag Team', 'title': 'AEW World Tag Team Championship',
             'about': 'FTR defended in the main event.'},
        ])

        # Collision Grand Slam
        self.create_episode_with_matches(aew, {
            'name': 'AEW Collision: Grand Slam',
            'date': date(2023, 9, 23),
            'venue': 'Arthur Ashe Stadium',
            'location': 'Queens, NY',
            'about': 'Collision Grand Slam at Arthur Ashe Stadium.'
        }, [
            {'wrestlers': ['Ricky Starks', 'Aaron Solo'], 'winner': 'Ricky Starks',
             'match_type': 'Singles', 'about': 'Absolute Ricky Starks.'},
            {'wrestlers': ['Miro', 'Andrade El Idolo'], 'winner': 'Miro',
             'match_type': 'Singles', 'about': 'The Redeemer in action.'},
        ])
