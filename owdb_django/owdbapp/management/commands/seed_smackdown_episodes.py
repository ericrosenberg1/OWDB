"""
Seed historic WWE SmackDown episodes with matches and significant moments.

Usage:
    python manage.py seed_smackdown_episodes
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic WWE SmackDown episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding WWE SmackDown Episodes ===\n'))

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        if not wwe:
            wwe = Promotion.objects.filter(abbreviation='WWF').first()

        self.seed_smackdown_1999(wwe)
        self.seed_smackdown_2000(wwe)
        self.seed_smackdown_2002(wwe)
        self.seed_smackdown_2000s(wwe)
        self.seed_smackdown_2010s(wwe)
        self.seed_smackdown_2020s(wwe)

        self.stdout.write(self.style.SUCCESS('\n=== SmackDown Seeding Complete ==='))
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

    def seed_smackdown_1999(self, wwe):
        """Seed the first SmackDown episodes from 1999."""
        self.stdout.write('\n--- 1999: SmackDown Debuts ---\n')

        # First SmackDown Ever - April 29, 1999
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(1999, 4, 29),
            'venue': 'New Haven Coliseum',
            'location': 'New Haven, CT',
            'about': 'The very first episode of SmackDown. A historic debut for what would become WWE\'s second flagship show.'
        }, [
            {'wrestlers': ['The Rock', 'Triple H'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Main event of the first SmackDown ever.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'The Undertaker'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Austin defended the WWF Championship.'},
            {'wrestlers': ['X-Pac', 'Jeff Jarrett'], 'winner': 'X-Pac',
             'match_type': 'Singles', 'about': 'DX member X-Pac in action.'},
        ])

        # SmackDown August 26, 1999 - Regular Series Begins
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(1999, 8, 26),
            'venue': 'Kemper Arena',
            'location': 'Kansas City, MO',
            'about': 'SmackDown becomes a weekly series on UPN.'
        }, [
            {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Rock and Sock connection clash.'},
            {'wrestlers': ['Triple H', 'Test'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'Triple H continued his dominance.'},
        ])

        # SmackDown December 16, 1999
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(1999, 12, 16),
            'venue': 'MCI Center',
            'location': 'Washington, DC',
            'about': 'Holiday edition of SmackDown heading into the new millennium.'
        }, [
            {'wrestlers': ['Triple H', 'Big Show'], 'winner': 'Triple H',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Triple H defended the WWF Championship.'},
            {'wrestlers': ['Chris Jericho', 'Chyna'], 'winner': 'Chris Jericho',
             'match_type': 'Singles', 'title': 'WWF Intercontinental Championship',
             'about': 'Y2J and Chyna fought for the IC title.'},
        ])

    def seed_smackdown_2000(self, wwe):
        """Seed key SmackDown episodes from 2000."""
        self.stdout.write('\n--- 2000: The Peak Year ---\n')

        # SmackDown February 24, 2000 - Cactus Jack retires
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2000, 2, 24),
            'venue': 'Gund Arena',
            'location': 'Cleveland, OH',
            'about': 'Post No Way Out fallout. Cactus Jack\'s WWF career ended.'
        }, [
            {'wrestlers': ['Triple H', 'Rikishi'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'Triple H in action after defeating Cactus Jack.'},
            {'wrestlers': ['The Rock', 'Big Show'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Rock built momentum for WrestleMania.'},
        ])

        # SmackDown May 4, 2000
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2000, 5, 4),
            'venue': 'Kiel Center',
            'location': 'St. Louis, MO',
            'about': 'Building to Judgment Day.'
        }, [
            {'wrestlers': ['The Rock', 'Triple H'], 'winner': 'No Contest',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Rock and Triple H in the main event.'},
            {'wrestlers': ['Chris Benoit', 'Chris Jericho'], 'winner': 'Chris Benoit',
             'match_type': 'Singles', 'about': 'Two of the best technical wrestlers in the world.'},
        ])

        # SmackDown - Stone Cold Returns
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2000, 10, 5),
            'venue': 'Firstar Center',
            'location': 'Cincinnati, OH',
            'about': 'Stone Cold Steve Austin returned from injury.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Rikishi'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'Austin returned and wanted revenge on the man who ran him over.'},
            {'wrestlers': ['The Rock', 'Kurt Angle'], 'winner': 'The Rock',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Rock defended against the Olympic Gold Medalist.'},
        ])

    def seed_smackdown_2002(self, wwe):
        """Seed key SmackDown episodes from 2002 - Brand Split Era."""
        self.stdout.write('\n--- 2002: Brand Split Era ---\n')

        # First SmackDown of Brand Split
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2002, 3, 28),
            'venue': 'Penn State University',
            'location': 'State College, PA',
            'about': 'First SmackDown after the brand split. The Rock is SmackDown\'s top star.'
        }, [
            {'wrestlers': ['The Rock', 'Booker T'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Rock in his first SmackDown-exclusive match.'},
            {'wrestlers': ['Edge', 'Kurt Angle'], 'winner': 'Edge',
             'match_type': 'Singles', 'about': 'Two of SmackDown\'s top drafted superstars.'},
            {'wrestlers': ['Hulk Hogan', 'Test'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hogan on SmackDown.'},
        ])

        # Brock Lesnar Dominates
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2002, 6, 27),
            'venue': 'Cow Palace',
            'location': 'San Francisco, CA',
            'about': 'Brock Lesnar continued his path of destruction through SmackDown.'
        }, [
            {'wrestlers': ['Brock Lesnar', 'Randy Orton'], 'winner': 'Brock Lesnar',
             'match_type': 'Singles', 'about': 'The Next Big Thing dominated.'},
            {'wrestlers': ['Kurt Angle', 'Chris Benoit'], 'winner': 'Kurt Angle',
             'match_type': 'Singles', 'about': 'Technical masterpiece.'},
        ])

        # SmackDown 6 Era
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2002, 10, 3),
            'venue': 'Joe Louis Arena',
            'location': 'Detroit, MI',
            'about': 'The SmackDown Six era - featuring Edge, Rey Mysterio, Kurt Angle, Chris Benoit, Eddie Guerrero, and Chavo Guerrero.'
        }, [
            {'wrestlers': ['Eddie Guerrero', 'Chris Benoit'], 'winner': 'Eddie Guerrero',
             'match_type': 'Singles', 'about': 'Los Guerreros era begins.'},
            {'wrestlers': ['Edge', 'Rey Mysterio'], 'winner': 'Edge',
             'match_type': 'Singles', 'about': 'Two of SmackDown\'s rising stars.'},
            {'wrestlers': ['Kurt Angle', 'Brock Lesnar'], 'winner': 'Kurt Angle',
             'match_type': 'Singles', 'about': 'Olympic hero vs The Next Big Thing.'},
        ])

    def seed_smackdown_2000s(self, wwe):
        """Seed key SmackDown episodes from 2003-2009."""
        self.stdout.write('\n--- 2000s: The Golden SmackDown Era ---\n')

        # Eddie Guerrero Champion
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2004, 2, 19),
            'venue': 'Cow Palace',
            'location': 'San Francisco, CA',
            'about': 'Post No Way Out. Eddie Guerrero is WWE Champion. Viva La Raza!'
        }, [
            {'wrestlers': ['Eddie Guerrero', 'Kurt Angle'], 'winner': 'Eddie Guerrero',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Eddie defended his newly won championship.'},
            {'wrestlers': ['Brock Lesnar', 'Hardcore Holly'], 'winner': 'Brock Lesnar',
             'match_type': 'Singles', 'about': 'Lesnar dealt with Holly\'s vendetta.'},
        ])

        # JBL Becomes Champion
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2004, 6, 17),
            'venue': 'Richmond Coliseum',
            'location': 'Richmond, VA',
            'about': 'Post Judgment Day. JBL is the new WWE Champion, beginning his dominant heel run.'
        }, [
            {'wrestlers': ['John Bradshaw Layfield', 'Rob Van Dam'], 'winner': 'John Bradshaw Layfield',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'JBL\'s first title defense.'},
            {'wrestlers': ['The Undertaker', 'Booker T'], 'winner': 'The Undertaker',
             'match_type': 'Singles', 'about': 'Deadman in action.'},
        ])

        # Batista Comes to SmackDown
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2005, 6, 9),
            'venue': 'Verizon Wireless Arena',
            'location': 'Manchester, NH',
            'about': 'Post Draft. Batista brought the World Heavyweight Championship to SmackDown.'
        }, [
            {'wrestlers': ['Batista', 'JBL'], 'winner': 'Batista',
             'match_type': 'Singles', 'about': 'The Animal arrived on SmackDown.'},
            {'wrestlers': ['Rey Mysterio', 'Eddie Guerrero'], 'winner': 'Eddie Guerrero',
             'match_type': 'Singles', 'about': 'Former friends turned rivals.'},
        ])

        # Eddie Guerrero Tribute
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2005, 11, 18),
            'venue': 'Target Center',
            'location': 'Minneapolis, MN',
            'about': 'A tribute to Eddie Guerrero who passed away on November 13, 2005. Viva La Raza.'
        }, [
            {'wrestlers': ['Various'], 'winner': 'Various',
             'match_type': 'Tribute', 'about': 'WWE paid tribute to Eddie Guerrero with stories and memories.'},
        ])

        # Undertaker vs Batista Feud
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2007, 4, 6),
            'venue': 'Joe Louis Arena',
            'location': 'Detroit, MI',
            'about': 'Post WrestleMania 23. Undertaker is World Heavyweight Champion.'
        }, [
            {'wrestlers': ['The Undertaker', 'Batista'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'Their legendary feud continued.'},
            {'wrestlers': ['Edge', 'Chris Benoit'], 'winner': 'Edge',
             'match_type': 'Singles', 'about': 'The Rated-R Superstar in action.'},
        ])

        # Edge Championship Run
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2008, 5, 16),
            'venue': 'Verizon Arena',
            'location': 'Little Rock, AR',
            'about': 'Edge as World Heavyweight Champion.'
        }, [
            {'wrestlers': ['Edge', 'Big Show'], 'winner': 'Edge',
             'match_type': 'Singles', 'about': 'The Ultimate Opportunist defended.'},
            {'wrestlers': ['The Undertaker', 'Vladimir Kozlov'], 'winner': 'The Undertaker',
             'match_type': 'Singles', 'about': 'Undertaker faced the Russian.'},
        ])

        # Jeff Hardy Title Win
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2008, 12, 19),
            'venue': 'Key Arena',
            'location': 'Seattle, WA',
            'about': 'Post Armageddon. Jeff Hardy is WWE Champion for the first time.'
        }, [
            {'wrestlers': ['Jeff Hardy', 'Vladimir Kozlov'], 'winner': 'Jeff Hardy',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Jeff Hardy\'s first title defense as champion.'},
            {'wrestlers': ['Triple H', 'The Brian Kendrick'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'The Game on SmackDown.'},
        ])

        # CM Punk World Champion
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown',
            'date': date(2009, 6, 12),
            'venue': 'Van Andel Arena',
            'location': 'Grand Rapids, MI',
            'about': 'CM Punk cashed in Money in the Bank to become World Heavyweight Champion.'
        }, [
            {'wrestlers': ['CM Punk', 'Umaga'], 'winner': 'CM Punk',
             'match_type': 'Singles', 'about': 'New World Heavyweight Champion in action.'},
            {'wrestlers': ['Jeff Hardy', 'Edge'], 'winner': 'Jeff Hardy',
             'match_type': 'Singles', 'about': 'Hardy sought revenge after losing the title.'},
        ])

    def seed_smackdown_2010s(self, wwe):
        """Seed key SmackDown episodes from 2010-2019."""
        self.stdout.write('\n--- 2010s: The Blue Brand ---\n')

        # SmackDown Live Era Begins
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown Live',
            'date': date(2016, 7, 19),
            'venue': 'Dunkin Donuts Center',
            'location': 'Providence, RI',
            'about': 'First episode of SmackDown Live after the 2016 brand split.'
        }, [
            {'wrestlers': ['John Cena', 'Bray Wyatt'], 'winner': 'John Cena',
             'match_type': 'Singles', 'about': 'Cena headlined the new era of SmackDown.'},
            {'wrestlers': ['Dean Ambrose', 'AJ Styles'], 'winner': 'Dean Ambrose',
             'match_type': 'Singles', 'about': 'SmackDown\'s top stars collided.'},
        ])

        # AJ Styles World Champion
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown Live',
            'date': date(2016, 9, 13),
            'venue': 'KeyArena',
            'location': 'Seattle, WA',
            'about': 'Post Backlash. AJ Styles is WWE World Champion.'
        }, [
            {'wrestlers': ['AJ Styles', 'John Cena'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'title': 'WWE World Championship',
             'about': 'Styles defended against Cena in a rematch.'},
            {'wrestlers': ['Dean Ambrose', 'Baron Corbin'], 'winner': 'Dean Ambrose',
             'match_type': 'Singles', 'about': 'Former champion in action.'},
        ])

        # Daniel Bryan Returns to Ring
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown Live',
            'date': date(2018, 3, 20),
            'venue': 'Little Caesars Arena',
            'location': 'Detroit, MI',
            'about': 'Daniel Bryan announced he was cleared to compete again.'
        }, [
            {'wrestlers': ['Daniel Bryan', 'Kevin Owens', 'Sami Zayn'], 'winner': 'Daniel Bryan',
             'match_type': 'Handicap', 'about': 'Daniel Bryan\'s return match to in-ring competition.'},
            {'wrestlers': ['AJ Styles', 'Shinsuke Nakamura'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'Dream match between two of the best.'},
        ])

        # Kofi Kingston Championship Win Build
        self.create_episode_with_matches(wwe, {
            'name': 'SmackDown Live',
            'date': date(2019, 3, 19),
            'venue': 'Nutter Center',
            'location': 'Dayton, OH',
            'about': 'Kofi Kingston\'s journey to WrestleMania continued.'
        }, [
            {'wrestlers': ['Kofi Kingston', 'Randy Orton'], 'winner': 'Kofi Kingston',
             'match_type': 'Gauntlet', 'about': 'Kofi proved he deserved a title shot at WrestleMania.'},
            {'wrestlers': ['Daniel Bryan', 'Kevin Owens'], 'winner': 'Daniel Bryan',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'The Planet\'s Champion defended.'},
        ])

        # SmackDown Moves to Fox
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2019, 10, 4),
            'venue': 'Staples Center',
            'location': 'Los Angeles, CA',
            'about': 'Historic first SmackDown on Fox. Brock Lesnar attacked Kofi Kingston.'
        }, [
            {'wrestlers': ['Brock Lesnar', 'Kofi Kingston'], 'winner': 'Brock Lesnar',
             'match_type': 'Singles', 'title': 'WWE Championship', 'title_changed': True,
             'about': 'Lesnar squashed Kofi to win the WWE Championship in seconds.'},
            {'wrestlers': ['Becky Lynch', 'Sasha Banks'], 'winner': 'Becky Lynch',
             'match_type': 'Singles', 'about': 'The Man fought The Boss.'},
            {'wrestlers': ['Roman Reigns', 'Erick Rowan'], 'winner': 'Roman Reigns',
             'match_type': 'Singles', 'about': 'Big Dog in action.'},
        ])

    def seed_smackdown_2020s(self, wwe):
        """Seed key SmackDown episodes from 2020-present."""
        self.stdout.write('\n--- 2020s: Tribal Chief Era ---\n')

        # Roman Reigns Returns - Tribal Chief Era Begins
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2020, 8, 21),
            'venue': 'Amway Center',
            'location': 'Orlando, FL',
            'about': 'Roman Reigns returned at SummerSlam and appeared on SmackDown as a heel.'
        }, [
            {'wrestlers': ['Roman Reigns', 'Various'], 'winner': 'Roman Reigns',
             'match_type': 'Segment', 'about': 'Roman Reigns aligned with Paul Heyman, beginning The Tribal Chief era.'},
            {'wrestlers': ['Big E', 'The Miz'], 'winner': 'Big E',
             'match_type': 'Singles', 'about': 'Big E in singles action.'},
        ])

        # Bloodline Acknowledges Roman
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2020, 10, 30),
            'venue': 'Amway Center',
            'location': 'Orlando, FL',
            'about': 'The Usos acknowledged Roman Reigns as the Tribal Chief, forming The Bloodline.'
        }, [
            {'wrestlers': ['Roman Reigns', 'Jey Uso'], 'winner': 'Roman Reigns',
             'match_type': 'Singles', 'about': 'Jey Uso acknowledged Roman after their feud.'},
            {'wrestlers': ['Sasha Banks', 'Bayley'], 'winner': 'Sasha Banks',
             'match_type': 'Singles', 'about': 'Former best friends battled.'},
        ])

        # The Bloodline - Sami Zayn Era
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2022, 9, 16),
            'venue': 'Spectrum Center',
            'location': 'Charlotte, NC',
            'about': 'Sami Zayn became an Honorary Uce, one of wrestling\'s best storylines.'
        }, [
            {'wrestlers': ['Sami Zayn', 'Solo Sikoa', 'Drew McIntyre', 'Kevin Owens'], 'winner': 'The Bloodline',
             'match_type': 'Tag Team', 'about': 'Sami Zayn earned his place as an Honorary Uce.'},
            {'wrestlers': ['Liv Morgan', 'Sonya Deville'], 'winner': 'Liv Morgan',
             'match_type': 'Singles', 'about': 'SmackDown Women\'s Championship defense.'},
        ])

        # Cody Rhodes Finishes Story - Post WrestleMania 40
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2024, 4, 12),
            'venue': 'Wells Fargo Center',
            'location': 'Philadelphia, PA',
            'about': 'Post WrestleMania 40. Cody Rhodes finished the story.'
        }, [
            {'wrestlers': ['Cody Rhodes', 'AJ Styles'], 'winner': 'Cody Rhodes',
             'match_type': 'Singles', 'about': 'The new champion defended.'},
            {'wrestlers': ['Roman Reigns', 'Solo Sikoa'], 'winner': 'Solo Sikoa',
             'match_type': 'Confrontation', 'about': 'Solo Sikoa claimed The Bloodline in Roman\'s absence.'},
        ])

        # SmackDown 25th Anniversary
        self.create_episode_with_matches(wwe, {
            'name': 'Friday Night SmackDown',
            'date': date(2024, 10, 4),
            'venue': 'Climate Pledge Arena',
            'location': 'Seattle, WA',
            'about': 'Celebrating 25 years of SmackDown with legends and current stars.'
        }, [
            {'wrestlers': ['Cody Rhodes', 'Various'], 'winner': 'Cody Rhodes',
             'match_type': 'Segment', 'about': 'SmackDown 25th anniversary celebration.'},
            {'wrestlers': ['The Bloodline', 'Various'], 'winner': 'The Bloodline',
             'match_type': 'Segment', 'about': 'The Bloodline storyline continued.'},
        ])
