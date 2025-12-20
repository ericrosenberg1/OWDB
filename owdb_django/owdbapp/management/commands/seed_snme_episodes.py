"""
Seed historic Saturday Night's Main Event episodes with matches and significant moments.

Usage:
    python manage.py seed_snme_episodes
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic Saturday Night\'s Main Event episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Saturday Night\'s Main Event ===\n'))

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        if not wwe:
            wwe = Promotion.objects.filter(abbreviation='WWF').first()

        self.seed_snme_1985_1992(wwe)
        self.seed_snme_2006_2008(wwe)
        self.seed_snme_2024(wwe)

        self.stdout.write(self.style.SUCCESS('\n=== SNME Seeding Complete ==='))
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

    def seed_snme_1985_1992(self, wwe):
        """Seed the original SNME episodes from 1985-1992."""
        self.stdout.write('\n--- 1985-1992: The Original Era ---\n')

        # SNME #1 - May 11, 1985
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event I',
            'date': date(1985, 5, 11),
            'venue': 'Nassau Coliseum',
            'location': 'Uniondale, NY',
            'about': 'The very first Saturday Night\'s Main Event. WWF on NBC in primetime.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Bob Orton'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hulk Hogan in the main event.'},
            {'wrestlers': ['Wendi Richter', 'Fabulous Moolah'], 'winner': 'Wendi Richter',
             'match_type': 'Singles', 'title': 'WWF Women\'s Championship',
             'about': 'Women\'s Championship match.'},
            {'wrestlers': ['Junkyard Dog', 'Pete Doherty'], 'winner': 'Junkyard Dog',
             'match_type': 'Singles', 'about': 'JYD in squash action.'},
        ])

        # SNME #2 - October 3, 1985
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event II',
            'date': date(1985, 10, 3),
            'venue': 'Hulman Civic-University Center',
            'location': 'Terre Haute, IN',
            'about': 'Second SNME featuring Hulk Hogan and Andre the Giant as partners.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Andre the Giant', 'Big John Studd', 'King Kong Bundy'],
             'winner': 'Hulk Hogan', 'match_type': 'Tag Team',
             'about': 'Hogan and Andre teamed up.'},
            {'wrestlers': ['Paul Orndorff', 'Roddy Piper'], 'winner': 'Paul Orndorff',
             'match_type': 'Singles', 'about': 'Mr. Wonderful faced Piper.'},
        ])

        # SNME #3 - November 2, 1985
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event III',
            'date': date(1985, 11, 2),
            'venue': 'Hersheypark Arena',
            'location': 'Hershey, PA',
            'about': 'Third SNME in the heart of Pennsylvania.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Terry Funk'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Hogan defended against the Funker.'},
            {'wrestlers': ['Randy Savage', 'Tito Santana'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'title': 'WWF Intercontinental Championship', 'title_changed': True,
             'about': 'Macho Man won the IC Title!'},
        ])

        # SNME - March 1, 1986
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event V',
            'date': date(1986, 3, 1),
            'venue': 'Reunion Arena',
            'location': 'Dallas, TX',
            'about': 'SNME from Texas with WrestleMania 2 build.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Don Muraco'], 'winner': 'Hulk Hogan',
             'match_type': 'Steel Cage', 'title': 'WWF Championship',
             'about': 'Hogan defended in a steel cage.'},
            {'wrestlers': ['King Kong Bundy', 'Uncle Elmer'], 'winner': 'King Kong Bundy',
             'match_type': 'Singles', 'about': 'Bundy dominated before WrestleMania.'},
        ])

        # SNME - May 3, 1986
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event VI',
            'date': date(1986, 5, 3),
            'venue': 'Providence Civic Center',
            'location': 'Providence, RI',
            'about': 'Post-WrestleMania 2 fallout.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'King Kong Bundy'], 'winner': 'Hulk Hogan',
             'match_type': 'Steel Cage', 'title': 'WWF Championship',
             'about': 'Rematch from WrestleMania 2 in a cage.'},
            {'wrestlers': ['British Bulldogs', 'Dream Team'], 'winner': 'British Bulldogs',
             'match_type': 'Tag Team', 'title': 'WWF Tag Team Championship',
             'about': 'Tag title defense by the Bulldogs.'},
        ])

        # SNME - October 4, 1986
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event VII',
            'date': date(1986, 10, 4),
            'venue': 'Richfield Coliseum',
            'location': 'Richfield, OH',
            'about': 'Fall edition of SNME.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Paul Orndorff'], 'winner': 'No Contest',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Their feud continued to rage.'},
            {'wrestlers': ['Randy Savage', 'Jake Roberts'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'about': 'Macho Man faced the Snake.'},
        ])

        # SNME - November 29, 1986
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event VIII',
            'date': date(1986, 11, 29),
            'venue': 'Los Angeles Sports Arena',
            'location': 'Los Angeles, CA',
            'about': 'SNME from the West Coast.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Hercules'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Hogan defended against Hercules.'},
            {'wrestlers': ['Randy Savage', 'Bruno Sammartino'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'about': 'Macho Man faced the Living Legend.'},
        ])

        # SNME - January 3, 1987
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event IX',
            'date': date(1987, 1, 3),
            'venue': 'Hartford Civic Center',
            'location': 'Hartford, CT',
            'about': 'New Year edition of SNME leading to WrestleMania III.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Paul Orndorff'], 'winner': 'Hulk Hogan',
             'match_type': 'Steel Cage', 'title': 'WWF Championship',
             'about': 'Cage match ended their legendary feud.'},
            {'wrestlers': ['Randy Savage', 'George Steele'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'about': 'Savage dealt with the Animal.'},
        ])

        # SNME - March 14, 1987
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event X',
            'date': date(1987, 3, 14),
            'venue': 'Joe Louis Arena',
            'location': 'Detroit, MI',
            'about': 'WrestleMania III buildup. Andre challenges Hogan.'
        }, [
            {'wrestlers': ['Andre the Giant', 'Hulk Hogan'], 'winner': 'Andre the Giant',
             'match_type': 'Contract Signing', 'about': 'The contract signing for WrestleMania III. Andre turned on Hogan.'},
            {'wrestlers': ['Randy Savage', 'George Steele'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'about': 'Savage continued his IC title reign.'},
        ])

        # SNME - October 3, 1987
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XII',
            'date': date(1987, 10, 3),
            'venue': 'Hersheypark Arena',
            'location': 'Hershey, PA',
            'about': 'Post-WrestleMania III, the fallout continued.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'King Kong Bundy'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Hogan defended his title.'},
            {'wrestlers': ['Honky Tonk Man', 'Randy Savage'], 'winner': 'Honky Tonk Man',
             'match_type': 'Singles', 'title': 'WWF Intercontinental Championship',
             'about': 'Honky Tonk Man retained via countout.'},
        ])

        # SNME - November 28, 1987 - Mega Powers Form
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XIII',
            'date': date(1987, 11, 28),
            'venue': 'Seattle Center Coliseum',
            'location': 'Seattle, WA',
            'about': 'The Mega Powers were born as Hogan saved Elizabeth and Savage.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'King Kong Bundy'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Hogan defended against Bundy.'},
            {'wrestlers': ['Honky Tonk Man', 'Randy Savage'], 'winner': 'DQ',
             'match_type': 'Singles', 'title': 'WWF Intercontinental Championship',
             'about': 'Hogan came to save Savage, forming the Mega Powers.'},
        ])

        # SNME - February 5, 1988 - Main Event I (The Rematch)
        self.create_episode_with_matches(wwe, {
            'name': 'The Main Event I',
            'date': date(1988, 2, 5),
            'venue': 'Market Square Arena',
            'location': 'Indianapolis, IN',
            'about': 'Primetime special. Andre the Giant defeated Hulk Hogan for the WWF Championship in the most-watched wrestling match in American history.'
        }, [
            {'wrestlers': ['Andre the Giant', 'Hulk Hogan'], 'winner': 'Andre the Giant',
             'match_type': 'Singles', 'title': 'WWF Championship', 'title_changed': True,
             'about': '33 million viewers. The Million Dollar Man bought the title from Andre. Evil referee Dave Hebner.'},
        ])

        # SNME - March 12, 1988
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XV',
            'date': date(1988, 3, 12),
            'venue': 'Nashville Municipal Auditorium',
            'location': 'Nashville, TN',
            'about': 'WrestleMania IV build with the tournament announced.'
        }, [
            {'wrestlers': ['Strike Force', 'Demolition'], 'winner': 'Strike Force',
             'match_type': 'Tag Team', 'title': 'WWF Tag Team Championship',
             'about': 'Tag team title defense before WrestleMania.'},
            {'wrestlers': ['Hulk Hogan', 'Andre the Giant', 'Ted DiBiase'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'Chaos between Hogan, Andre, and DiBiase.'},
        ])

        # SNME - April 30, 1988
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XVI',
            'date': date(1988, 4, 30),
            'venue': 'Springfield Civic Center',
            'location': 'Springfield, MA',
            'about': 'Post-WrestleMania IV. Randy Savage is WWF Champion.'
        }, [
            {'wrestlers': ['Randy Savage', 'Ted DiBiase'], 'winner': 'Randy Savage',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'New champion Savage defended against the Million Dollar Man.'},
            {'wrestlers': ['Demolition', 'Strike Force'], 'winner': 'Demolition',
             'match_type': 'Tag Team', 'title': 'WWF Tag Team Championship',
             'about': 'Tag title rematch.'},
        ])

        # SNME - October 29, 1988
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XVIII',
            'date': date(1988, 10, 29),
            'venue': 'Baltimore Arena',
            'location': 'Baltimore, MD',
            'about': 'Mega Powers continue to dominate.'
        }, [
            {'wrestlers': ['Mega Powers', 'Twin Towers'], 'winner': 'Mega Powers',
             'match_type': 'Tag Team', 'about': 'Hogan and Savage as the Mega Powers.'},
            {'wrestlers': ['Ultimate Warrior', 'Honky Tonk Man'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'about': 'Warrior continued his dominance.'},
        ])

        # SNME - February 3, 1989 - Main Event II - Mega Powers Explode
        self.create_episode_with_matches(wwe, {
            'name': 'The Main Event II',
            'date': date(1989, 2, 3),
            'venue': 'Bradley Center',
            'location': 'Milwaukee, WI',
            'about': 'The Mega Powers exploded! Randy Savage turned on Hulk Hogan.'
        }, [
            {'wrestlers': ['Mega Powers', 'Twin Towers'], 'winner': 'No Contest',
             'match_type': 'Tag Team', 'about': 'MEGA POWERS EXPLODE! Savage attacked Hogan, jealous over Elizabeth. The greatest angle of the 1980s.'},
        ])

        # SNME - April 15, 1989
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XX',
            'date': date(1989, 4, 15),
            'venue': 'Veterans Memorial Coliseum',
            'location': 'Phoenix, AZ',
            'about': 'WrestleMania V fallout. Hulk Hogan defeated Savage to regain the title.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Bad News Brown'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'New champion Hogan in action.'},
            {'wrestlers': ['Ultimate Warrior', 'Honky Tonk Man'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'title': 'WWF Intercontinental Championship',
             'about': 'Warrior defended the IC Title.'},
        ])

        # SNME - July 29, 1989
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXII',
            'date': date(1989, 7, 29),
            'venue': 'Worcester Centrum',
            'location': 'Worcester, MA',
            'about': 'Summer SNME edition.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Honky Tonk Man'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Hogan defended against the Honky Tonk Man.'},
            {'wrestlers': ['Demolition', 'Brain Busters'], 'winner': 'Brain Busters',
             'match_type': 'Tag Team', 'title': 'WWF Tag Team Championship', 'title_changed': True,
             'about': 'Brain Busters won the tag titles.'},
        ])

        # SNME - November 25, 1989
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXIV',
            'date': date(1989, 11, 25),
            'venue': 'Topeka Expo Centre',
            'location': 'Topeka, KS',
            'about': 'Thanksgiving SNME.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'The Genius'], 'winner': 'The Genius',
             'match_type': 'Singles', 'about': 'Mr. Perfect interfered to cost Hogan.'},
            {'wrestlers': ['Ultimate Warrior', 'Andre the Giant'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'about': 'Warrior faced the Giant.'},
        ])

        # SNME - January 27, 1990
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXV',
            'date': date(1990, 1, 27),
            'venue': 'UTC Arena',
            'location': 'Chattanooga, TN',
            'about': 'Royal Rumble fallout. Hogan vs Warrior builds.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Randy Savage'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hogan faced his former partner again.'},
            {'wrestlers': ['Ultimate Warrior', 'Dino Bravo'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Warrior defending the title.'},
        ])

        # SNME - April 28, 1990
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXVI',
            'date': date(1990, 4, 28),
            'venue': 'Austin Frank Erwin Center',
            'location': 'Austin, TX',
            'about': 'Post-WrestleMania VI. Ultimate Warrior is WWF Champion.'
        }, [
            {'wrestlers': ['Ultimate Warrior', 'Haku'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'New champion Warrior defended.'},
            {'wrestlers': ['Hulk Hogan', 'Mr. Perfect'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hogan in non-title action.'},
        ])

        # SNME - July 28, 1990
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXVII',
            'date': date(1990, 7, 28),
            'venue': 'Omaha Civic Auditorium',
            'location': 'Omaha, NE',
            'about': 'Summer SNME with SummerSlam build.'
        }, [
            {'wrestlers': ['Ultimate Warrior', 'Rick Rude'], 'winner': 'Ultimate Warrior',
             'match_type': 'Steel Cage', 'title': 'WWF Championship',
             'about': 'Warrior defended in a cage against Rude.'},
        ])

        # SNME - November 24, 1990
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event XXVIII',
            'date': date(1990, 11, 24),
            'venue': 'Indianapolis Convention Center',
            'location': 'Indianapolis, IN',
            'about': 'Thanksgiving SNME. Building to Survivor Series.'
        }, [
            {'wrestlers': ['Ultimate Warrior', 'Ted DiBiase'], 'winner': 'Ultimate Warrior',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Warrior defended against the Million Dollar Man.'},
            {'wrestlers': ['Hulk Hogan', 'Earthquake'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hogan faced Earthquake again.'},
        ])

    def seed_snme_2006_2008(self, wwe):
        """Seed the revived SNME episodes from 2006-2008."""
        self.stdout.write('\n--- 2006-2008: The Revival Era ---\n')

        # SNME Revival - March 18, 2006
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event',
            'date': date(2006, 3, 18),
            'venue': 'Cobo Arena',
            'location': 'Detroit, MI',
            'about': 'SNME returns after 14 years. WrestleMania 22 build.'
        }, [
            {'wrestlers': ['John Cena', 'Triple H'], 'winner': 'John Cena',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Cena defended against Triple H before WrestleMania.'},
            {'wrestlers': ['Shawn Michaels', 'Shane McMahon', 'Vince McMahon'], 'winner': 'Shawn Michaels',
             'match_type': 'Handicap', 'about': 'HBK faced the McMahons.'},
        ])

        # SNME - July 15, 2006
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event',
            'date': date(2006, 7, 15),
            'venue': 'American Airlines Center',
            'location': 'Dallas, TX',
            'about': 'Summer SNME with DX reunion in full swing.'
        }, [
            {'wrestlers': ['D-Generation X', 'Spirit Squad'], 'winner': 'D-Generation X',
             'match_type': 'Elimination', 'about': 'DX dominated the Spirit Squad.'},
            {'wrestlers': ['John Cena', 'Edge'], 'winner': 'Edge',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Edge and Cena battled for the title.'},
        ])

        # SNME - August 18, 2007
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event',
            'date': date(2007, 8, 18),
            'venue': 'Madison Square Garden',
            'location': 'New York City, NY',
            'about': 'SNME from the World\'s Most Famous Arena.'
        }, [
            {'wrestlers': ['John Cena', 'King Booker'], 'winner': 'John Cena',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Cena defended against King Booker at MSG.'},
            {'wrestlers': ['Triple H', 'King Booker'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'The Game in action.'},
        ])

        # SNME - May 31, 2008
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event',
            'date': date(2008, 5, 31),
            'venue': 'Nassau Coliseum',
            'location': 'Uniondale, NY',
            'about': 'The last SNME of the 2000s revival.'
        }, [
            {'wrestlers': ['Triple H', 'Randy Orton'], 'winner': 'Triple H',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Triple H defended against Orton.'},
            {'wrestlers': ['Shawn Michaels', 'Chris Jericho'], 'winner': 'Shawn Michaels',
             'match_type': 'Singles', 'about': 'Two of the best in action.'},
        ])

    def seed_snme_2024(self, wwe):
        """Seed the modern SNME episodes from 2024-present."""
        self.stdout.write('\n--- 2024-Present: The New Era ---\n')

        # SNME December 14, 2024
        self.create_episode_with_matches(wwe, {
            'name': 'Saturday Night\'s Main Event',
            'date': date(2024, 12, 14),
            'venue': 'Nassau Coliseum',
            'location': 'Uniondale, NY',
            'about': 'NBC returns SNME for the first time since 2008. A new era begins.'
        }, [
            {'wrestlers': ['Gunther', 'Damian Priest'], 'winner': 'Gunther',
             'match_type': 'Singles', 'title': 'World Heavyweight Championship',
             'about': 'The Ring General defended his title.'},
            {'wrestlers': ['Cody Rhodes', 'Kevin Owens'], 'winner': 'No Contest',
             'match_type': 'Singles', 'title': 'Undisputed WWE Championship',
             'about': 'Their feud continued after chaos.'},
            {'wrestlers': ['Drew McIntyre', 'Sami Zayn'], 'winner': 'Sami Zayn',
             'match_type': 'Singles', 'about': 'Zayn got a measure of revenge on McIntyre.'},
        ])
