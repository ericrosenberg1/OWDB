"""
Mega seeding command for comprehensive wrestling database build-out.
Adds more WWE, WCW, ECW, TNA, NJPW, AEW events plus stables and complete profiles.

Usage:
    python manage.py seed_mega_events
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue, Stable
)


class Command(BaseCommand):
    help = 'Comprehensive seeding of events, wrestlers, stables, and titles'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== MEGA EVENT SEEDING ===\n'))

        self.ensure_promotions()
        self.ensure_titles()
        self.seed_stables()
        self.seed_wwe_events()
        self.seed_wcw_events()
        self.seed_attitude_era_events()
        self.seed_ruthless_aggression_events()
        self.seed_modern_wwe_events()

        # Print final stats
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING COMPLETE ==='))
        self.stdout.write(f'Total Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')
        self.stdout.write(f'Wrestlers: {Wrestler.objects.count()}')
        self.stdout.write(f'Promotions: {Promotion.objects.count()}')
        self.stdout.write(f'Titles: {Title.objects.count()}')
        self.stdout.write(f'Venues: {Venue.objects.count()}')
        self.stdout.write(f'Stables: {Stable.objects.count()}')

    def ensure_promotions(self):
        """Ensure all major promotions exist."""
        promotions = [
            {'name': 'World Wrestling Entertainment', 'abbreviation': 'WWE', 'founded_year': 1952},
            {'name': 'World Wrestling Federation', 'abbreviation': 'WWF', 'founded_year': 1952},
            {'name': 'World Championship Wrestling', 'abbreviation': 'WCW', 'founded_year': 1988},
            {'name': 'Extreme Championship Wrestling', 'abbreviation': 'ECW', 'founded_year': 1992},
            {'name': 'Total Nonstop Action Wrestling', 'abbreviation': 'TNA', 'founded_year': 2002},
            {'name': 'All Elite Wrestling', 'abbreviation': 'AEW', 'founded_year': 2019},
            {'name': 'New Japan Pro-Wrestling', 'abbreviation': 'NJPW', 'founded_year': 1972},
            {'name': 'National Wrestling Alliance', 'abbreviation': 'NWA', 'founded_year': 1948},
            {'name': 'Ring of Honor', 'abbreviation': 'ROH', 'founded_year': 2002},
            {'name': 'Pro Wrestling NOAH', 'abbreviation': 'NOAH', 'founded_year': 2000},
            {'name': 'All Japan Pro Wrestling', 'abbreviation': 'AJPW', 'founded_year': 1972},
            {'name': 'Impact Wrestling', 'abbreviation': 'IMPACT', 'founded_year': 2017},
        ]
        for p in promotions:
            # Check by abbreviation OR slug to avoid duplicate constraint violations
            slug = slugify(p['name'])
            existing = Promotion.objects.filter(abbreviation=p['abbreviation']).first()
            if not existing:
                existing = Promotion.objects.filter(slug=slug).first()
            if not existing:
                Promotion.objects.create(
                    name=p['name'],
                    abbreviation=p['abbreviation'],
                    founded_year=p.get('founded_year')
                )
                self.stdout.write(f'  + Created promotion: {p["name"]}')

    def ensure_titles(self):
        """Ensure major titles exist."""
        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        ecw = Promotion.objects.filter(abbreviation='ECW').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()
        tna = Promotion.objects.filter(abbreviation='TNA').first()

        titles = [
            ('WWE Championship', wwe),
            ('WWE Universal Championship', wwe),
            ('WWE Intercontinental Championship', wwe),
            ('WWE United States Championship', wwe),
            ('WWE Tag Team Championship', wwe),
            ('WWE Women\'s Championship', wwe),
            ('WWE Raw Women\'s Championship', wwe),
            ('WWE SmackDown Women\'s Championship', wwe),
            ('WWE 24/7 Championship', wwe),
            ('WCW World Heavyweight Championship', wcw),
            ('WCW United States Championship', wcw),
            ('WCW Cruiserweight Championship', wcw),
            ('WCW World Tag Team Championship', wcw),
            ('WCW Television Championship', wcw),
            ('ECW World Heavyweight Championship', ecw),
            ('ECW World Television Championship', ecw),
            ('ECW World Tag Team Championship', ecw),
            ('AEW World Championship', aew),
            ('AEW TNT Championship', aew),
            ('AEW World Tag Team Championship', aew),
            ('AEW TBS Championship', aew),
            ('AEW International Championship', aew),
            ('IWGP Heavyweight Championship', njpw),
            ('IWGP World Heavyweight Championship', njpw),
            ('IWGP Intercontinental Championship', njpw),
            ('IWGP United States Championship', njpw),
            ('IWGP Junior Heavyweight Championship', njpw),
            ('IWGP Tag Team Championship', njpw),
            ('TNA World Heavyweight Championship', tna),
            ('TNA X Division Championship', tna),
            ('TNA Tag Team Championship', tna),
            ('TNA Knockouts Championship', tna),
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

    def seed_stables(self):
        """Seed major wrestling stables/factions."""
        self.stdout.write('\n--- Seeding Stables & Factions ---\n')

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()

        stables_data = [
            # WWE/WWF Stables
            {
                'name': 'D-Generation X',
                'promotion': wwe,
                'formed_year': 1997,
                'disbanded_year': 2010,
                'members': ['Shawn Michaels', 'Triple H', 'Chyna', 'Road Dogg', 'Billy Gunn', 'X-Pac'],
                'leaders': ['Shawn Michaels', 'Triple H'],
                'about': 'One of the most influential factions in WWE history. Known for their rebellious attitude and catchphrases. Led the WWF during the Attitude Era.'
            },
            {
                'name': 'The Corporation',
                'promotion': wwe,
                'formed_year': 1998,
                'disbanded_year': 1999,
                'members': ['Vince McMahon', 'Shane McMahon', 'The Rock', 'Big Boss Man', 'Ken Shamrock', 'Test'],
                'leaders': ['Vince McMahon'],
                'about': 'Heel faction led by Vince McMahon to oppose Steve Austin. The Rock was the corporate champion.'
            },
            {
                'name': 'The Ministry of Darkness',
                'promotion': wwe,
                'formed_year': 1998,
                'disbanded_year': 1999,
                'members': ['The Undertaker', 'Paul Bearer', 'Viscera', 'Mideon', 'The Acolytes'],
                'leaders': ['The Undertaker'],
                'about': 'Dark, supernatural faction led by The Undertaker during his Lord of Darkness phase.'
            },
            {
                'name': 'The Brood',
                'promotion': wwe,
                'formed_year': 1998,
                'disbanded_year': 1999,
                'members': ['Gangrel', 'Edge', 'Christian'],
                'leaders': ['Gangrel'],
                'about': 'Vampire-themed faction that launched Edge and Christian\'s careers.'
            },
            {
                'name': 'Evolution',
                'promotion': wwe,
                'formed_year': 2003,
                'disbanded_year': 2005,
                'members': ['Triple H', 'Ric Flair', 'Randy Orton', 'Batista'],
                'leaders': ['Triple H'],
                'about': 'Past, present, and future of professional wrestling. Dominant faction during the Ruthless Aggression Era.'
            },
            {
                'name': 'The Nexus',
                'promotion': wwe,
                'formed_year': 2010,
                'disbanded_year': 2011,
                'members': ['Wade Barrett', 'Daniel Bryan', 'Heath Slater', 'Justin Gabriel', 'David Otunga', 'Skip Sheffield', 'Darren Young', 'Michael Tarver'],
                'leaders': ['Wade Barrett', 'CM Punk'],
                'about': 'NXT Season 1 rookies who invaded Raw and caused chaos. One of the most impactful debuts in WWE history.'
            },
            {
                'name': 'The Shield',
                'promotion': wwe,
                'formed_year': 2012,
                'disbanded_year': 2014,
                'members': ['Roman Reigns', 'Seth Rollins', 'Dean Ambrose'],
                'leaders': ['Roman Reigns'],
                'about': 'Three-man justice faction. All three members became world champions. One of the most successful factions ever.'
            },
            {
                'name': 'The Wyatt Family',
                'promotion': wwe,
                'formed_year': 2013,
                'disbanded_year': 2017,
                'members': ['Bray Wyatt', 'Luke Harper', 'Erick Rowan', 'Braun Strowman'],
                'leaders': ['Bray Wyatt'],
                'about': 'Cult-like faction led by the eater of worlds, Bray Wyatt. Backwoods horror gimmick.'
            },
            {
                'name': 'The Authority',
                'promotion': wwe,
                'formed_year': 2013,
                'disbanded_year': 2016,
                'members': ['Triple H', 'Stephanie McMahon', 'Kane', 'Seth Rollins', 'Randy Orton', 'Big Show', 'J&J Security'],
                'leaders': ['Triple H', 'Stephanie McMahon'],
                'about': 'Corporate heel faction that ran Raw and opposed Daniel Bryan and other fan favorites.'
            },
            {
                'name': 'The New Day',
                'promotion': wwe,
                'formed_year': 2014,
                'members': ['Kofi Kingston', 'Big E', 'Xavier Woods'],
                'leaders': ['Big E'],
                'about': 'Longest-reigning tag team champions in WWE history. Known for positivity, pancakes, and unicorn horns.'
            },
            {
                'name': 'The Bloodline',
                'promotion': wwe,
                'formed_year': 2021,
                'members': ['Roman Reigns', 'Jey Uso', 'Jimmy Uso', 'Solo Sikoa', 'Paul Heyman'],
                'leaders': ['Roman Reigns'],
                'about': 'Samoan dynasty faction led by the Tribal Chief Roman Reigns. Dominated WWE for years.'
            },
            {
                'name': 'Judgment Day',
                'promotion': wwe,
                'formed_year': 2022,
                'members': ['Finn Balor', 'Damian Priest', 'Rhea Ripley', 'Dominik Mysterio', 'JD McDonagh'],
                'leaders': ['Finn Balor'],
                'about': 'Dark faction formed by Edge, later taken over by Finn Balor. Dominant force on Raw.'
            },
            # WCW Stables
            {
                'name': 'The Four Horsemen',
                'promotion': wcw,
                'formed_year': 1985,
                'disbanded_year': 1999,
                'members': ['Ric Flair', 'Arn Anderson', 'Tully Blanchard', 'Barry Windham', 'Ole Anderson', 'Lex Luger', 'Sid Vicious', 'Brian Pillman', 'Chris Benoit', 'Dean Malenko', 'Steve McMichael'],
                'leaders': ['Ric Flair'],
                'about': 'The most legendary faction in wrestling history. Defined the standard for heel stables.'
            },
            {
                'name': 'Wolfpac',
                'promotion': wcw,
                'formed_year': 1998,
                'disbanded_year': 1999,
                'members': ['Kevin Nash', 'Scott Hall', 'Sting', 'Lex Luger', 'Konnan', 'Randy Savage'],
                'leaders': ['Kevin Nash'],
                'about': 'Red and black nWo splinter faction. Popular babyface version of the nWo.'
            },
            {
                'name': 'The Flock',
                'promotion': wcw,
                'formed_year': 1997,
                'disbanded_year': 1998,
                'members': ['Raven', 'Perry Saturn', 'Kidman', 'Lodi', 'Riggs', 'Sick Boy', 'Reese'],
                'leaders': ['Raven'],
                'about': 'Cult-like faction led by Raven in WCW.'
            },
            {
                'name': 'The Filthy Animals',
                'promotion': wcw,
                'formed_year': 1999,
                'disbanded_year': 2001,
                'members': ['Eddie Guerrero', 'Rey Mysterio', 'Konnan', 'Kidman', 'Juventud Guerrera'],
                'leaders': ['Eddie Guerrero'],
                'about': 'Latino faction featuring top cruiserweights.'
            },
            # AEW Stables
            {
                'name': 'The Inner Circle',
                'promotion': aew,
                'formed_year': 2019,
                'disbanded_year': 2022,
                'members': ['Chris Jericho', 'Jake Hager', 'Santana', 'Ortiz', 'Sammy Guevara'],
                'leaders': ['Chris Jericho'],
                'about': 'First major faction in AEW history, led by inaugural AEW Champion Chris Jericho.'
            },
            {
                'name': 'The Elite',
                'promotion': aew,
                'formed_year': 2016,
                'members': ['Kenny Omega', 'Matt Jackson', 'Nick Jackson', 'Hangman Adam Page'],
                'leaders': ['Kenny Omega'],
                'about': 'The founding faction of AEW. Started as a NJPW/ROH supergroup.'
            },
            {
                'name': 'The Jericho Appreciation Society',
                'promotion': aew,
                'formed_year': 2022,
                'disbanded_year': 2023,
                'members': ['Chris Jericho', 'Daniel Garcia', 'Matt Menard', 'Angelo Parker', 'Jake Hager'],
                'leaders': ['Chris Jericho'],
                'about': 'Sports entertainment faction led by Jericho.'
            },
            {
                'name': 'The Blackpool Combat Club',
                'promotion': aew,
                'formed_year': 2022,
                'members': ['Jon Moxley', 'Bryan Danielson', 'Claudio Castagnoli', 'Wheeler Yuta'],
                'leaders': ['Jon Moxley', 'Bryan Danielson'],
                'about': 'Violent, technical wrestling faction. Trained by William Regal.'
            },
            {
                'name': 'The House of Black',
                'promotion': aew,
                'formed_year': 2022,
                'members': ['Malakai Black', 'Brody King', 'Buddy Matthews', 'Julia Hart'],
                'leaders': ['Malakai Black'],
                'about': 'Dark, occult faction led by the former Aleister Black.'
            },
            {
                'name': 'The Mogul Embassy',
                'promotion': aew,
                'formed_year': 2022,
                'members': ['Swerve Strickland', 'Prince Nana', 'Brian Cage', 'Bishop Kaun', 'Toa Liona'],
                'leaders': ['Swerve Strickland'],
                'about': 'Faction managed by Prince Nana with Swerve as the top star.'
            },
            # NJPW Stables
            {
                'name': 'Bullet Club',
                'promotion': njpw,
                'formed_year': 2013,
                'members': ['Prince Devitt', 'Karl Anderson', 'Doc Gallows', 'AJ Styles', 'Kenny Omega', 'The Young Bucks', 'Cody Rhodes', 'Adam Cole', 'Jay White'],
                'leaders': ['Prince Devitt', 'AJ Styles', 'Kenny Omega', 'Jay White'],
                'about': 'Most influential faction of the 2010s. Spawned AEW and changed wrestling globally.'
            },
            {
                'name': 'Los Ingobernables de Japon',
                'promotion': njpw,
                'formed_year': 2015,
                'members': ['Tetsuya Naito', 'Evil', 'Sanada', 'Bushi', 'Hiromu Takahashi', 'Shingo Takagi'],
                'leaders': ['Tetsuya Naito'],
                'about': 'Japanese branch of the Mexican Los Ingobernables. Tranquilo lifestyle.'
            },
            {
                'name': 'Chaos',
                'promotion': njpw,
                'formed_year': 2009,
                'members': ['Shinsuke Nakamura', 'Kazuchika Okada', 'Tomohiro Ishii', 'Toru Yano', 'Hirooki Goto', 'Yoshi-Hashi'],
                'leaders': ['Shinsuke Nakamura', 'Kazuchika Okada'],
                'about': 'Major NJPW faction originally heel, turned face. Home of Okada.'
            },
            {
                'name': 'Suzuki-gun',
                'promotion': njpw,
                'formed_year': 2011,
                'members': ['Minoru Suzuki', 'Zack Sabre Jr.', 'Taichi', 'El Desperado', 'Yoshinobu Kanemaru'],
                'leaders': ['Minoru Suzuki'],
                'about': 'Violent heel faction led by the King, Minoru Suzuki.'
            },
        ]

        for stable_data in stables_data:
            existing = Stable.objects.filter(name=stable_data['name']).first()
            if existing:
                continue

            # Create member wrestlers first
            members = [self.get_or_create_wrestler(name) for name in stable_data.get('members', [])]
            leaders = [self.get_or_create_wrestler(name) for name in stable_data.get('leaders', [])]

            stable = Stable.objects.create(
                name=stable_data['name'],
                promotion=stable_data['promotion'],
                formed_year=stable_data.get('formed_year'),
                disbanded_year=stable_data.get('disbanded_year'),
                about=stable_data.get('about', '')
            )
            stable.members.set(members)
            stable.leaders.set(leaders)
            self.stdout.write(f'  Created stable: {stable_data["name"]} ({len(members)} members)')

    def seed_wwe_events(self):
        """Seed more historic WWE events."""
        self.stdout.write('\n--- Seeding Additional WWE Events ---\n')
        wwe = Promotion.objects.filter(abbreviation='WWE').first()

        # SummerSlam events
        events = [
            # SummerSlam 1988
            ({
                'name': 'SummerSlam 1988',
                'date': date(1988, 8, 29),
                'venue': 'Madison Square Garden',
                'location': 'New York City, NY',
                'attendance': 20000,
                'about': 'The inaugural SummerSlam event.'
            }, [
                {'wrestlers': ['Ultimate Warrior', 'The Honky Tonk Man'], 'winner': 'Ultimate Warrior',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Warrior won the IC title in 31 seconds.'},
                {'wrestlers': ['Mega Powers', 'Mega Bucks'], 'winner': 'Mega Powers',
                 'match_type': 'Tag Team', 'about': 'Hulk Hogan and Randy Savage defeated Ted DiBiase and Andre the Giant.'},
            ]),
            # SummerSlam 1991
            ({
                'name': 'SummerSlam 1991',
                'date': date(1991, 8, 26),
                'venue': 'Madison Square Garden',
                'location': 'New York City, NY',
                'attendance': 20000,
                'about': 'A Wedding Reception main event.'
            }, [
                {'wrestlers': ['Bret Hart', 'Mr. Perfect'], 'winner': 'Bret Hart',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Bret Hart won his first singles title.'},
                {'wrestlers': ['Hulk Hogan', 'Sgt. Slaughter', 'Ultimate Warrior'], 'winner': 'Hulk Hogan',
                 'match_type': 'Handicap', 'title': 'WWF Championship', 'about': 'Match Made in Hell.'},
            ]),
            # SummerSlam 1997
            ({
                'name': 'SummerSlam 1997',
                'date': date(1997, 8, 3),
                'venue': 'Continental Airlines Arena',
                'location': 'East Rutherford, NJ',
                'attendance': 20012,
                'about': 'Steve Austin broke his neck in the main event.'
            }, [
                {'wrestlers': ['Bret Hart', 'The Undertaker'], 'winner': 'Bret Hart',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Guest referee Shawn Michaels.'},
                {'wrestlers': ['Stone Cold Steve Austin', 'Owen Hart'], 'winner': 'Owen Hart',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Austin suffered a broken neck from piledriver.'},
                {'wrestlers': ['Hunter Hearst Helmsley', 'Mankind'], 'winner': 'Hunter Hearst Helmsley',
                 'match_type': 'Cage Match', 'about': 'Cage match with Chyna interference.'},
            ]),
            # SummerSlam 2000
            ({
                'name': 'SummerSlam 2000',
                'date': date(2000, 8, 27),
                'venue': 'Raleigh Entertainment & Sports Arena',
                'location': 'Raleigh, NC',
                'attendance': 18810,
                'about': 'TLC match steals the show.'
            }, [
                {'wrestlers': ['The Rock', 'Triple H', 'Kurt Angle'], 'winner': 'The Rock',
                 'match_type': 'Triple Threat', 'title': 'WWF Championship', 'about': 'Triple threat for the WWF Championship.'},
                {'wrestlers': ['Edge', 'Christian', 'The Hardy Boyz', 'The Dudley Boyz'], 'winner': 'Edge and Christian',
                 'match_type': 'TLC', 'title': 'Tag Team', 'about': 'First ever TLC match. Groundbreaking.'},
                {'wrestlers': ['Chris Jericho', 'Chris Benoit'], 'winner': 'Chris Benoit',
                 'match_type': '2 out of 3 Falls', 'title': 'Intercontinental', 'about': 'Classic technical wrestling match.'},
            ]),
            # SummerSlam 2001
            ({
                'name': 'SummerSlam 2001',
                'date': date(2001, 8, 19),
                'venue': 'Compaq Center',
                'location': 'San Jose, CA',
                'attendance': 16695,
                'about': 'During the Invasion storyline.'
            }, [
                {'wrestlers': ['The Rock', 'Booker T'], 'winner': 'The Rock',
                 'match_type': 'Singles', 'title': 'WCW Championship', 'about': 'WCW Championship match during Invasion.'},
                {'wrestlers': ['Stone Cold Steve Austin', 'Kurt Angle'], 'winner': 'Kurt Angle',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Angle won the WWF Championship.'},
                {'wrestlers': ['Edge', 'Lance Storm'], 'winner': 'Edge',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Edge defended against WCW\'s Storm.'},
            ]),
            # SummerSlam 2005
            ({
                'name': 'SummerSlam 2005',
                'date': date(2005, 8, 21),
                'venue': 'MCI Center',
                'location': 'Washington, D.C.',
                'attendance': 18156,
                'about': 'Hulk Hogan vs Shawn Michaels dream match.'
            }, [
                {'wrestlers': ['Hulk Hogan', 'Shawn Michaels'], 'winner': 'Hulk Hogan',
                 'match_type': 'Singles', 'about': 'Legend vs Legend match. HBK oversold everything.'},
                {'wrestlers': ['Batista', 'John Bradshaw Layfield'], 'winner': 'Batista',
                 'match_type': 'No Holds Barred', 'title': 'World Heavyweight', 'about': 'Batista retained in a brutal match.'},
                {'wrestlers': ['Eddie Guerrero', 'Rey Mysterio'], 'winner': 'Rey Mysterio',
                 'match_type': 'Ladder Match', 'about': 'Custody of Dominick ladder match.'},
            ]),
            # SummerSlam 2013
            ({
                'name': 'SummerSlam 2013',
                'date': date(2013, 8, 18),
                'venue': 'Staples Center',
                'location': 'Los Angeles, CA',
                'attendance': 14407,
                'about': 'Daniel Bryan\'s short-lived title win.'
            }, [
                {'wrestlers': ['Daniel Bryan', 'John Cena'], 'winner': 'Daniel Bryan',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Bryan won his first WWE Championship cleanly over Cena.'},
                {'wrestlers': ['Randy Orton', 'Daniel Bryan'], 'winner': 'Randy Orton',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Orton cashed in MITB with Triple H\'s help.'},
                {'wrestlers': ['CM Punk', 'Brock Lesnar'], 'winner': 'Brock Lesnar',
                 'match_type': 'No DQ', 'about': 'Best vs Beast. Paul Heyman betrayed Punk.'},
            ]),
            # SummerSlam 2015
            ({
                'name': 'SummerSlam 2015',
                'date': date(2015, 8, 23),
                'venue': 'Barclays Center',
                'location': 'Brooklyn, NY',
                'attendance': 15526,
                'about': 'Biggest SummerSlam ever at the time.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'The Undertaker'], 'winner': 'The Undertaker',
                 'match_type': 'Singles', 'about': 'Undertaker won with a low blow in the rematch from WrestleMania 30.'},
                {'wrestlers': ['Seth Rollins', 'John Cena'], 'winner': 'Seth Rollins',
                 'match_type': 'Title vs Title', 'title': 'WWE Championship', 'about': 'Rollins won both titles with Jon Stewart\'s help.'},
                {'wrestlers': ['Roman Reigns', 'Bray Wyatt'], 'winner': 'Roman Reigns',
                 'match_type': 'Singles', 'about': 'Reigns overcame the Wyatt Family.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(wwe, event_data, matches)

    def seed_wcw_events(self):
        """Seed more WCW events."""
        self.stdout.write('\n--- Seeding Additional WCW Events ---\n')
        wcw = Promotion.objects.filter(abbreviation='WCW').first()

        events = [
            # Beach Blast 1992
            ({
                'name': 'Beach Blast 1992',
                'date': date(1992, 6, 20),
                'venue': 'Mobile Civic Center',
                'location': 'Mobile, AL',
                'about': 'Iron Man match main event.'
            }, [
                {'wrestlers': ['Sting', 'Cactus Jack'], 'winner': 'Sting',
                 'match_type': 'Falls Count Anywhere', 'about': 'Brutal falls count anywhere match.'},
                {'wrestlers': ['Ricky Steamboat', 'Rick Rude'], 'winner': 'Rick Rude',
                 'match_type': 'Iron Man', 'title': 'United States', 'about': '30 minute Iron Man match for the US title.'},
            ]),
            # SuperBrawl III
            ({
                'name': 'SuperBrawl III',
                'date': date(1993, 2, 21),
                'venue': 'Asheville Civic Center',
                'location': 'Asheville, NC',
                'about': 'Sting defends against Vader.'
            }, [
                {'wrestlers': ['Sting', 'Big Van Vader'], 'winner': 'Sting',
                 'match_type': 'White Castle of Fear Strap Match', 'title': 'WCW World', 'about': 'Sting retained in a unique strap match.'},
                {'wrestlers': ['Barry Windham', 'Dustin Rhodes'], 'winner': 'Barry Windham',
                 'match_type': 'Singles', 'title': 'United States', 'about': 'Windham captured the US title.'},
            ]),
            # Slamboree 1996
            ({
                'name': 'Slamboree 1996',
                'date': date(1996, 5, 19),
                'venue': 'Riverside Centroplex',
                'location': 'Baton Rouge, LA',
                'about': 'Lethal Lottery format event.'
            }, [
                {'wrestlers': ['The Giant', 'Sting'], 'winner': 'The Giant',
                 'match_type': 'Singles', 'title': 'WCW World', 'about': 'Giant retained the WCW World Title.'},
                {'wrestlers': ['Eddie Guerrero', 'Ric Flair'], 'winner': 'Eddie Guerrero',
                 'match_type': 'Singles', 'about': 'Eddie defeated the legendary Flair.'},
            ]),
            # Uncensored 1996
            ({
                'name': 'Uncensored 1996',
                'date': date(1996, 3, 24),
                'venue': 'Tupelo Coliseum',
                'location': 'Tupelo, MS',
                'about': 'Doomsday Cage Match main event.'
            }, [
                {'wrestlers': ['Hulk Hogan', 'Randy Savage', 'Ric Flair', 'Arn Anderson', 'Lex Luger', 'Kevin Sullivan', 'Z-Gangsta', 'The Ultimate Solution'],
                 'winner': 'Hulk Hogan', 'match_type': 'Doomsday Cage', 'about': 'Bizarre multi-tiered cage match.'},
            ]),
            # Fall Brawl 1996
            ({
                'name': 'Fall Brawl 1996',
                'date': date(1996, 9, 15),
                'venue': 'Lawrence Joel Veterans Memorial Coliseum',
                'location': 'Winston-Salem, NC',
                'about': 'War Games with the nWo.'
            }, [
                {'wrestlers': ['Team WCW', 'Team nWo'], 'winner': 'Team nWo',
                 'match_type': 'War Games', 'about': 'The nWo won the first War Games against WCW.'},
            ]),
            # Souled Out 1997
            ({
                'name': 'Souled Out 1997',
                'date': date(1997, 1, 25),
                'venue': 'Cedar Rapids Ice Arena',
                'location': 'Cedar Rapids, IA',
                'about': 'First nWo-themed PPV.'
            }, [
                {'wrestlers': ['Hollywood Hogan', 'The Giant'], 'winner': 'Hollywood Hogan',
                 'match_type': 'Singles', 'title': 'WCW World', 'about': 'nWo\'s first PPV main event.'},
                {'wrestlers': ['Eddie Guerrero', 'Syxx'], 'winner': 'Syxx',
                 'match_type': 'Ladder Match', 'title': 'Cruiserweight', 'about': 'Ladder match for the Cruiserweight title.'},
            ]),
            # Road Wild 1997
            ({
                'name': 'Road Wild 1997',
                'date': date(1997, 8, 9),
                'venue': 'Sturgis Rally',
                'location': 'Sturgis, SD',
                'about': 'Annual motorcycle rally event.'
            }, [
                {'wrestlers': ['Hollywood Hogan', 'Lex Luger'], 'winner': 'Lex Luger',
                 'match_type': 'Singles', 'title': 'WCW World', 'about': 'Luger shocked the world by winning the title.'},
                {'wrestlers': ['Randy Savage', 'Diamond Dallas Page'], 'winner': 'Randy Savage',
                 'match_type': 'No DQ', 'about': 'Savage and DDP continued their feud.'},
            ]),
            # SuperBrawl VIII
            ({
                'name': 'SuperBrawl VIII',
                'date': date(1998, 2, 22),
                'venue': 'Cow Palace',
                'location': 'Daly City, CA',
                'attendance': 12620,
                'about': 'Sting loses title after winning at Starrcade.'
            }, [
                {'wrestlers': ['Hollywood Hogan', 'Sting'], 'winner': 'Hollywood Hogan',
                 'match_type': 'Singles', 'title': 'WCW World', 'about': 'Hogan regained the title from Sting.'},
                {'wrestlers': ['Chris Jericho', 'Juventud Guerrera'], 'winner': 'Chris Jericho',
                 'match_type': 'Singles', 'title': 'Cruiserweight', 'about': 'Jericho defended the Cruiserweight title.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(wcw, event_data, matches)

    def seed_attitude_era_events(self):
        """Seed Attitude Era events (1997-2002)."""
        self.stdout.write('\n--- Seeding Attitude Era Events ---\n')
        wwe = Promotion.objects.filter(abbreviation='WWE').first()

        events = [
            # In Your House: D-Generation X
            ({
                'name': 'In Your House: D-Generation X',
                'date': date(1997, 12, 7),
                'venue': 'Springfield Civic Center',
                'location': 'Springfield, MA',
                'about': 'The birth of DX as a dominant faction.'
            }, [
                {'wrestlers': ['Shawn Michaels', 'Ken Shamrock'], 'winner': 'Shawn Michaels',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'HBK retained by DQ.'},
                {'wrestlers': ['The Undertaker', 'Jeff Jarrett'], 'winner': 'The Undertaker',
                 'match_type': 'Singles', 'about': 'Taker destroyed Jarrett.'},
            ]),
            # Royal Rumble 1998
            ({
                'name': 'Royal Rumble 1998',
                'date': date(1998, 1, 18),
                'venue': 'San Jose Arena',
                'location': 'San Jose, CA',
                'attendance': 18542,
                'about': 'Stone Cold wins his first Rumble.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Royal Rumble', 'about': 'Austin won the Royal Rumble match.'},
                {'wrestlers': ['Shawn Michaels', 'The Undertaker'], 'winner': 'Shawn Michaels',
                 'match_type': 'Casket Match', 'title': 'WWF Championship', 'about': 'HBK retained in a casket match. Kane debuted helping Taker.'},
            ]),
            # No Way Out 1998
            ({
                'name': 'No Way Out of Texas',
                'date': date(1998, 2, 15),
                'venue': 'Compaq Center',
                'location': 'Houston, TX',
                'about': 'Austin vs Michaels build to WrestleMania.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'Dude Love'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Singles', 'about': 'Austin defeated Foley in his Dude Love persona.'},
                {'wrestlers': ['The Undertaker', 'Vader'], 'winner': 'The Undertaker',
                 'match_type': 'Singles', 'about': 'Taker defeated Vader.'},
            ]),
            # Unforgiven 1998
            ({
                'name': 'Unforgiven 1998',
                'date': date(1998, 4, 26),
                'venue': 'Greensboro Coliseum',
                'location': 'Greensboro, NC',
                'about': 'In Your House: Unforgiven'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'Dude Love'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Austin retained against Foley.'},
                {'wrestlers': ['Ken Shamrock', 'The Rock'], 'winner': 'Ken Shamrock',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Shamrock won but reversed due to DQ.'},
            ]),
            # King of the Ring 1998
            ({
                'name': 'King of the Ring 1998',
                'date': date(1998, 6, 28),
                'venue': 'Civic Arena',
                'location': 'Pittsburgh, PA',
                'attendance': 15894,
                'about': 'The Hell in a Cell match that defined wrestling.'
            }, [
                {'wrestlers': ['The Undertaker', 'Mankind'], 'winner': 'The Undertaker',
                 'match_type': 'Hell in a Cell', 'about': 'Legendary match. Mankind thrown off the cell twice. AS GOD AS MY WITNESS HE IS BROKEN IN HALF!'},
                {'wrestlers': ['Stone Cold Steve Austin', 'Kane'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'First Blood', 'title': 'WWF Championship', 'about': 'Austin retained the WWF Championship.'},
                {'wrestlers': ['Ken Shamrock'], 'winner': 'Ken Shamrock',
                 'match_type': 'Tournament', 'about': 'Shamrock won the King of the Ring tournament.'},
            ]),
            # Fully Loaded 1998
            ({
                'name': 'Fully Loaded 1998',
                'date': date(1998, 7, 26),
                'venue': 'Selland Arena',
                'location': 'Fresno, CA',
                'about': 'Austin vs Undertaker main event.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'The Undertaker'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Austin retained by DQ.'},
                {'wrestlers': ['Triple H', 'The Rock'], 'winner': 'Triple H',
                 'match_type': '2 out of 3 Falls', 'about': 'Beginning of their legendary rivalry.'},
            ]),
            # SummerSlam 1998
            ({
                'name': 'SummerSlam 1998',
                'date': date(1998, 8, 30),
                'venue': 'Madison Square Garden',
                'location': 'New York City, NY',
                'attendance': 21485,
                'about': 'Highway to Hell - Austin vs Undertaker main event.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'The Undertaker'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Austin retained the WWF Championship.'},
                {'wrestlers': ['Triple H', 'The Rock'], 'winner': 'The Rock',
                 'match_type': 'Ladder Match', 'title': 'Intercontinental', 'about': 'Rock won the IC title in a ladder match.'},
                {'wrestlers': ['Mankind', 'The New Age Outlaws'], 'winner': 'Mankind',
                 'match_type': 'Handicap', 'title': 'Tag Team', 'about': 'Mankind won the tag titles by himself.'},
            ]),
            # Survivor Series 1998
            ({
                'name': 'Survivor Series 1998',
                'date': date(1998, 11, 15),
                'venue': 'Kiel Center',
                'location': 'St. Louis, MO',
                'attendance': 21563,
                'about': 'The Rock wins his first WWF Championship via Montreal Screwjob reenactment.'
            }, [
                {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
                 'match_type': 'Tournament Finals', 'title': 'WWF Championship', 'about': 'Rock turned heel and won his first WWF Championship.'},
                {'wrestlers': ['Stone Cold Steve Austin', 'Mankind'], 'winner': 'Mankind',
                 'match_type': 'Tournament', 'about': 'Mankind advanced by defeating Austin.'},
            ]),
            # Rock Bottom 1998
            ({
                'name': 'Rock Bottom 1998',
                'date': date(1998, 12, 13),
                'venue': 'General Motors Place',
                'location': 'Vancouver, BC',
                'about': 'The Rock defends against Mankind.'
            }, [
                {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
                 'match_type': 'Singles', 'title': 'WWF Championship', 'about': 'Rock retained the WWF Championship.'},
                {'wrestlers': ['Stone Cold Steve Austin', 'The Undertaker'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Buried Alive', 'about': 'Austin won the Buried Alive match.'},
            ]),
            # Royal Rumble 1999
            ({
                'name': 'Royal Rumble 1999',
                'date': date(1999, 1, 24),
                'venue': 'Arrowhead Pond',
                'location': 'Anaheim, CA',
                'attendance': 14816,
                'about': 'Vince McMahon wins the Royal Rumble.'
            }, [
                {'wrestlers': ['Vince McMahon', 'Stone Cold Steve Austin'], 'winner': 'Vince McMahon',
                 'match_type': 'Royal Rumble', 'about': 'McMahon won the Rumble with Austin entering at #1.'},
                {'wrestlers': ['Mankind', 'The Rock'], 'winner': 'Mankind',
                 'match_type': 'I Quit', 'title': 'WWF Championship', 'about': 'Mankind won his first WWF Championship.'},
            ]),
            # No Way Out 1999
            ({
                'name': 'St. Valentines Day Massacre',
                'date': date(1999, 2, 14),
                'venue': 'The Pyramid',
                'location': 'Memphis, TN',
                'about': 'Austin vs McMahon in a steel cage.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'Vince McMahon'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'Steel Cage', 'about': 'Austin won after Big Show debuted through the ring.'},
                {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
                 'match_type': 'Last Man Standing', 'title': 'WWF Championship', 'about': 'Rock regained the title.'},
            ]),
            # Backlash 1999
            ({
                'name': 'Backlash 1999',
                'date': date(1999, 4, 25),
                'venue': 'Providence Civic Center',
                'location': 'Providence, RI',
                'about': 'Austin defends against The Rock.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'The Rock'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'No DQ', 'title': 'WWF Championship', 'about': 'Austin retained the WWF Championship.'},
                {'wrestlers': ['Triple H', 'X-Pac'], 'winner': 'X-Pac',
                 'match_type': 'Singles', 'about': 'DX explodes.'},
            ]),
            # No Mercy 1999
            ({
                'name': 'No Mercy 1999',
                'date': date(1999, 10, 17),
                'venue': 'Gund Arena',
                'location': 'Cleveland, OH',
                'about': 'Six pack challenge main event.'
            }, [
                {'wrestlers': ['Triple H', 'Stone Cold Steve Austin', 'The Rock', 'Mankind', 'British Bulldog', 'Big Show'],
                 'winner': 'Triple H', 'match_type': 'Six Pack Challenge', 'title': 'WWF Championship', 'about': 'Triple H won his first WWF Championship.'},
            ]),
            # Armageddon 1999
            ({
                'name': 'Armageddon 1999',
                'date': date(1999, 12, 12),
                'venue': 'Broward County Civic Center',
                'location': 'Fort Lauderdale, FL',
                'about': 'McMahon-Helmsley Era begins.'
            }, [
                {'wrestlers': ['Triple H', 'Vince McMahon'], 'winner': 'Triple H',
                 'match_type': 'No Holds Barred', 'title': 'WWF Championship', 'about': 'McMahon-Helmsley Era began. Stephanie turned heel.'},
                {'wrestlers': ['The Rock', 'Big Show'], 'winner': 'Big Show',
                 'match_type': 'Singles', 'about': 'Big Show defeated Rock.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(wwe, event_data, matches)

    def seed_ruthless_aggression_events(self):
        """Seed Ruthless Aggression Era events (2002-2008)."""
        self.stdout.write('\n--- Seeding Ruthless Aggression Era Events ---\n')
        wwe = Promotion.objects.filter(abbreviation='WWE').first()

        events = [
            # Vengeance 2002
            ({
                'name': 'Vengeance 2002',
                'date': date(2002, 7, 21),
                'venue': 'Joe Louis Arena',
                'location': 'Detroit, MI',
                'about': 'First Undisputed Champion crowned.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'Rob Van Dam'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'title': 'Intercontinental', 'about': 'Lesnar captured the IC title.'},
                {'wrestlers': ['The Undertaker', 'Kurt Angle', 'The Rock'], 'winner': 'The Rock',
                 'match_type': 'Triple Threat', 'title': 'Undisputed', 'about': 'Rock won the Undisputed Championship.'},
            ]),
            # Unforgiven 2002
            ({
                'name': 'Unforgiven 2002',
                'date': date(2002, 9, 22),
                'venue': 'Staples Center',
                'location': 'Los Angeles, CA',
                'about': 'Triple H returns.'
            }, [
                {'wrestlers': ['Triple H', 'Rob Van Dam'], 'winner': 'Triple H',
                 'match_type': 'Singles', 'title': 'World Heavyweight', 'about': 'HHH returned and won the new World Heavyweight Championship.'},
                {'wrestlers': ['Brock Lesnar', 'The Undertaker'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Lesnar retained the WWE Championship.'},
            ]),
            # No Mercy 2002
            ({
                'name': 'No Mercy 2002',
                'date': date(2002, 10, 20),
                'venue': 'Alltel Arena',
                'location': 'Little Rock, AR',
                'about': 'Hell in a Cell main event.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'The Undertaker'], 'winner': 'Brock Lesnar',
                 'match_type': 'Hell in a Cell', 'title': 'WWE Championship', 'about': 'Brutal Hell in a Cell match.'},
                {'wrestlers': ['Triple H', 'Kane'], 'winner': 'Triple H',
                 'match_type': 'Singles', 'title': 'World Heavyweight', 'about': 'HHH retained against Kane.'},
            ]),
            # Survivor Series 2002
            ({
                'name': 'Survivor Series 2002',
                'date': date(2002, 11, 17),
                'venue': 'Madison Square Garden',
                'location': 'New York City, NY',
                'attendance': 17930,
                'about': 'First Elimination Chamber match.'
            }, [
                {'wrestlers': ['Shawn Michaels', 'Triple H', 'Rob Van Dam', 'Kane', 'Chris Jericho', 'Booker T'],
                 'winner': 'Shawn Michaels', 'match_type': 'Elimination Chamber', 'title': 'World Heavyweight',
                 'about': 'First ever Elimination Chamber match. HBK won the World title.'},
                {'wrestlers': ['Brock Lesnar', 'Big Show'], 'winner': 'Big Show',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Paul Heyman betrayed Lesnar.'},
            ]),
            # Armageddon 2002
            ({
                'name': 'Armageddon 2002',
                'date': date(2002, 12, 15),
                'venue': 'Office Depot Center',
                'location': 'Fort Lauderdale, FL',
                'about': 'Triple threat main event.'
            }, [
                {'wrestlers': ['Shawn Michaels', 'Triple H', 'Kane'], 'winner': 'Triple H',
                 'match_type': 'Three Stages of Hell', 'title': 'World Heavyweight', 'about': 'Three Stages of Hell for the World title.'},
                {'wrestlers': ['Kurt Angle', 'Big Show'], 'winner': 'Kurt Angle',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Angle won the WWE Championship.'},
            ]),
            # Royal Rumble 2003
            ({
                'name': 'Royal Rumble 2003',
                'date': date(2003, 1, 19),
                'venue': 'Fleet Center',
                'location': 'Boston, MA',
                'attendance': 16048,
                'about': 'Brock Lesnar wins the Rumble.'
            }, [
                {'wrestlers': ['Brock Lesnar'], 'winner': 'Brock Lesnar',
                 'match_type': 'Royal Rumble', 'about': 'Lesnar won the Royal Rumble match.'},
                {'wrestlers': ['Kurt Angle', 'Chris Benoit'], 'winner': 'Kurt Angle',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Angle retained in a classic.'},
                {'wrestlers': ['Triple H', 'Scott Steiner'], 'winner': 'Triple H',
                 'match_type': 'Singles', 'title': 'World Heavyweight', 'about': 'Disappointing main event.'},
            ]),
            # Backlash 2003
            ({
                'name': 'Backlash 2003',
                'date': date(2003, 4, 27),
                'venue': 'Worcester Centrum',
                'location': 'Worcester, MA',
                'about': 'Goldberg debuts.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'John Cena'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Lesnar retained against the rising Cena.'},
                {'wrestlers': ['Triple H', 'Kevin Nash'], 'winner': 'Triple H',
                 'match_type': 'Singles', 'title': 'World Heavyweight', 'about': 'HHH retained the World title.'},
                {'wrestlers': ['The Rock', 'Goldberg'], 'winner': 'Goldberg',
                 'match_type': 'Singles', 'about': 'Goldberg\'s WWE debut match.'},
            ]),
            # Bad Blood 2003
            ({
                'name': 'Bad Blood 2003',
                'date': date(2003, 6, 15),
                'venue': 'Compaq Center',
                'location': 'Houston, TX',
                'about': 'Hell in a Cell main event.'
            }, [
                {'wrestlers': ['Triple H', 'Kevin Nash'], 'winner': 'Triple H',
                 'match_type': 'Hell in a Cell', 'title': 'World Heavyweight', 'about': 'Mick Foley was the referee.'},
                {'wrestlers': ['Goldberg', 'Chris Jericho'], 'winner': 'Goldberg',
                 'match_type': 'Singles', 'about': 'Goldberg dominated Jericho.'},
                {'wrestlers': ['Shawn Michaels', 'Ric Flair'], 'winner': 'Shawn Michaels',
                 'match_type': 'Singles', 'about': 'Legend vs Legend match.'},
            ]),
            # Vengeance 2003
            ({
                'name': 'Vengeance 2003',
                'date': date(2003, 7, 27),
                'venue': 'Pepsi Center',
                'location': 'Denver, CO',
                'about': 'Brock vs Big Show, Kurt vs Lesnar for the belt.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'Kurt Angle', 'Big Show'], 'winner': 'Brock Lesnar',
                 'match_type': 'Triple Threat', 'title': 'WWE Championship', 'about': 'Lesnar won the WWE Championship.'},
                {'wrestlers': ['Eddie Guerrero', 'Chris Benoit'], 'winner': 'Eddie Guerrero',
                 'match_type': 'Singles', 'title': 'United States', 'about': 'Eddie won the newly revived US title.'},
            ]),
            # SummerSlam 2003
            ({
                'name': 'SummerSlam 2003',
                'date': date(2003, 8, 24),
                'venue': 'America West Arena',
                'location': 'Phoenix, AZ',
                'attendance': 15127,
                'about': 'Elimination Chamber and huge main events.'
            }, [
                {'wrestlers': ['Triple H', 'Goldberg', 'Kevin Nash', 'Chris Jericho', 'Randy Orton', 'Shawn Michaels'],
                 'winner': 'Triple H', 'match_type': 'Elimination Chamber', 'title': 'World Heavyweight',
                 'about': 'Elimination Chamber for the World title.'},
                {'wrestlers': ['Brock Lesnar', 'Kurt Angle'], 'winner': 'Kurt Angle',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Angle won the WWE Championship.'},
                {'wrestlers': ['Kane', 'Rob Van Dam'], 'winner': 'Kane',
                 'match_type': 'No Holds Barred', 'about': 'Kane destroyed RVD after unmasking.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(wwe, event_data, matches)

    def seed_modern_wwe_events(self):
        """Seed Modern WWE events (2016-2024)."""
        self.stdout.write('\n--- Seeding Modern WWE Events ---\n')
        wwe = Promotion.objects.filter(abbreviation='WWE').first()

        events = [
            # Clash of Champions 2016
            ({
                'name': 'Clash of Champions 2016',
                'date': date(2016, 9, 25),
                'venue': 'Bankers Life Fieldhouse',
                'location': 'Indianapolis, IN',
                'about': 'First post-brand split Raw PPV.'
            }, [
                {'wrestlers': ['Kevin Owens', 'Seth Rollins'], 'winner': 'Kevin Owens',
                 'match_type': 'Singles', 'title': 'Universal', 'about': 'Owens retained via Triple H interference.'},
                {'wrestlers': ['Charlotte Flair', 'Bayley', 'Sasha Banks'], 'winner': 'Charlotte Flair',
                 'match_type': 'Triple Threat', 'title': 'Raw Women', 'about': 'Charlotte retained the Raw Women\'s title.'},
            ]),
            # Hell in a Cell 2016
            ({
                'name': 'Hell in a Cell 2016',
                'date': date(2016, 10, 30),
                'venue': 'TD Garden',
                'location': 'Boston, MA',
                'about': 'First women\'s Hell in a Cell match.'
            }, [
                {'wrestlers': ['Sasha Banks', 'Charlotte Flair'], 'winner': 'Charlotte Flair',
                 'match_type': 'Hell in a Cell', 'title': 'Raw Women', 'about': 'First ever women\'s HIAC match.'},
                {'wrestlers': ['Kevin Owens', 'Seth Rollins'], 'winner': 'Kevin Owens',
                 'match_type': 'Hell in a Cell', 'title': 'Universal', 'about': 'Owens retained inside the cell.'},
                {'wrestlers': ['Roman Reigns', 'Rusev'], 'winner': 'Roman Reigns',
                 'match_type': 'Hell in a Cell', 'title': 'United States', 'about': 'Reigns won inside the cell.'},
            ]),
            # WrestleMania 33
            ({
                'name': 'WrestleMania 33',
                'date': date(2017, 4, 2),
                'venue': 'Camping World Stadium',
                'location': 'Orlando, FL',
                'attendance': 75245,
                'about': 'Undertaker\'s farewell match.'
            }, [
                {'wrestlers': ['Roman Reigns', 'The Undertaker'], 'winner': 'Roman Reigns',
                 'match_type': 'No Holds Barred', 'about': 'Undertaker\'s apparent retirement match.'},
                {'wrestlers': ['Brock Lesnar', 'Goldberg'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'title': 'Universal', 'about': 'Lesnar won his second Universal title.'},
                {'wrestlers': ['Randy Orton', 'Bray Wyatt'], 'winner': 'Randy Orton',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Orton won the WWE Championship.'},
                {'wrestlers': ['Bayley', 'Charlotte Flair', 'Sasha Banks', 'Nia Jax'], 'winner': 'Bayley',
                 'match_type': 'Fatal 4-Way Elimination', 'title': 'Raw Women', 'about': 'Bayley retained in the elimination match.'},
                {'wrestlers': ['AJ Styles', 'Shane McMahon'], 'winner': 'AJ Styles',
                 'match_type': 'Singles', 'about': 'AJ Styles defeated the owner\'s son.'},
                {'wrestlers': ['The Hardy Boyz', 'Gallows and Anderson', 'Sheamus and Cesaro', 'Enzo and Cass'],
                 'winner': 'The Hardy Boyz', 'match_type': 'Ladder Match', 'title': 'Raw Tag Team', 'about': 'Hardy Boyz made a surprise return!'},
            ]),
            # WrestleMania 34
            ({
                'name': 'WrestleMania 34',
                'date': date(2018, 4, 8),
                'venue': 'Mercedes-Benz Superdome',
                'location': 'New Orleans, LA',
                'attendance': 78133,
                'about': 'Ronda Rousey\'s in-ring debut.'
            }, [
                {'wrestlers': ['Brock Lesnar', 'Roman Reigns'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'title': 'Universal', 'about': 'Lesnar retained in a bloody match.'},
                {'wrestlers': ['AJ Styles', 'Shinsuke Nakamura'], 'winner': 'AJ Styles',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Dream match between two NJPW legends.'},
                {'wrestlers': ['Ronda Rousey', 'Kurt Angle', 'Triple H', 'Stephanie McMahon'], 'winner': 'Ronda Rousey',
                 'match_type': 'Mixed Tag', 'about': 'Rousey\'s WrestleMania debut. She pinned Stephanie.'},
                {'wrestlers': ['Daniel Bryan', 'Shane McMahon', 'Sami Zayn', 'Kevin Owens'], 'winner': 'Daniel Bryan',
                 'match_type': 'Tag Team', 'about': 'Daniel Bryan\'s in-ring return!'},
                {'wrestlers': ['Charlotte Flair', 'Asuka'], 'winner': 'Charlotte Flair',
                 'match_type': 'Singles', 'title': 'SmackDown Women', 'about': 'Charlotte ended Asuka\'s undefeated streak.'},
            ]),
            # WrestleMania 35
            ({
                'name': 'WrestleMania 35',
                'date': date(2019, 4, 7),
                'venue': 'MetLife Stadium',
                'location': 'East Rutherford, NJ',
                'attendance': 82265,
                'about': 'First women\'s main event at WrestleMania.'
            }, [
                {'wrestlers': ['Becky Lynch', 'Ronda Rousey', 'Charlotte Flair'], 'winner': 'Becky Lynch',
                 'match_type': 'Triple Threat', 'title': 'Raw Women', 'about': 'First ever women\'s WrestleMania main event. Becky became double champion.'},
                {'wrestlers': ['Seth Rollins', 'Brock Lesnar'], 'winner': 'Seth Rollins',
                 'match_type': 'Singles', 'title': 'Universal', 'about': 'Rollins slayed the beast.'},
                {'wrestlers': ['Kofi Kingston', 'Daniel Bryan'], 'winner': 'Kofi Kingston',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Kofi realized his 11-year dream.'},
                {'wrestlers': ['Triple H', 'Batista'], 'winner': 'Triple H',
                 'match_type': 'No Holds Barred', 'about': 'Batista\'s retirement match.'},
            ]),
            # WrestleMania 37 Night 1
            ({
                'name': 'WrestleMania 37 Night 1',
                'date': date(2021, 4, 10),
                'venue': 'Raymond James Stadium',
                'location': 'Tampa, FL',
                'attendance': 25675,
                'about': 'First WrestleMania with fans since pandemic.'
            }, [
                {'wrestlers': ['Bobby Lashley', 'Drew McIntyre'], 'winner': 'Bobby Lashley',
                 'match_type': 'Singles', 'title': 'WWE Championship', 'about': 'Lashley retained the WWE Championship.'},
                {'wrestlers': ['Bianca Belair', 'Sasha Banks'], 'winner': 'Bianca Belair',
                 'match_type': 'Singles', 'title': 'SmackDown Women', 'about': 'Historic main event. Bianca\'s crowning moment.'},
                {'wrestlers': ['Cesaro', 'Seth Rollins'], 'winner': 'Cesaro',
                 'match_type': 'Singles', 'about': 'Cesaro got his WrestleMania moment.'},
            ]),
            # WrestleMania 37 Night 2
            ({
                'name': 'WrestleMania 37 Night 2',
                'date': date(2021, 4, 11),
                'venue': 'Raymond James Stadium',
                'location': 'Tampa, FL',
                'attendance': 25675,
                'about': 'Roman vs Edge vs Bryan main event.'
            }, [
                {'wrestlers': ['Roman Reigns', 'Edge', 'Daniel Bryan'], 'winner': 'Roman Reigns',
                 'match_type': 'Triple Threat', 'title': 'Universal', 'about': 'Roman pinned both Edge and Bryan simultaneously.'},
                {'wrestlers': ['Rhea Ripley', 'Asuka'], 'winner': 'Rhea Ripley',
                 'match_type': 'Singles', 'title': 'Raw Women', 'about': 'Ripley won her first main roster title.'},
                {'wrestlers': ['Kevin Owens', 'Sami Zayn'], 'winner': 'Kevin Owens',
                 'match_type': 'Singles', 'about': 'Longtime rivals clashed at Mania.'},
            ]),
            # WrestleMania 38 Night 1
            ({
                'name': 'WrestleMania 38 Saturday',
                'date': date(2022, 4, 2),
                'venue': 'AT&T Stadium',
                'location': 'Arlington, TX',
                'attendance': 77899,
                'about': 'Steve Austin returns.'
            }, [
                {'wrestlers': ['Stone Cold Steve Austin', 'Kevin Owens'], 'winner': 'Stone Cold Steve Austin',
                 'match_type': 'No Holds Barred', 'about': 'Austin\'s first match in 19 years!'},
                {'wrestlers': ['Bianca Belair', 'Becky Lynch'], 'winner': 'Bianca Belair',
                 'match_type': 'Singles', 'title': 'Raw Women', 'about': 'Bianca got her revenge for SummerSlam.'},
                {'wrestlers': ['The Usos', 'Shinsuke Nakamura', 'Rick Boogs'], 'winner': 'The Usos',
                 'match_type': 'Tag Team', 'title': 'SmackDown Tag', 'about': 'Usos retained the tag titles.'},
            ]),
            # WrestleMania 38 Night 2
            ({
                'name': 'WrestleMania 38 Sunday',
                'date': date(2022, 4, 3),
                'venue': 'AT&T Stadium',
                'location': 'Arlington, TX',
                'attendance': 78453,
                'about': 'Title unification main event.'
            }, [
                {'wrestlers': ['Roman Reigns', 'Brock Lesnar'], 'winner': 'Roman Reigns',
                 'match_type': 'Title Unification', 'title': 'WWE Championship', 'about': 'Roman became Undisputed WWE Universal Champion.'},
                {'wrestlers': ['Edge', 'AJ Styles'], 'winner': 'Edge',
                 'match_type': 'Singles', 'about': 'Dream match between two legends.'},
                {'wrestlers': ['Pat McAfee', 'Austin Theory'], 'winner': 'Pat McAfee',
                 'match_type': 'Singles', 'about': 'McAfee impressed in his WrestleMania debut.'},
            ]),
            # WrestleMania 39 Night 1
            ({
                'name': 'WrestleMania 39 Saturday',
                'date': date(2023, 4, 1),
                'venue': 'SoFi Stadium',
                'location': 'Inglewood, CA',
                'attendance': 80497,
                'about': 'Hollywood WrestleMania.'
            }, [
                {'wrestlers': ['Kevin Owens', 'Austin Theory'], 'winner': 'Kevin Owens',
                 'match_type': 'Singles', 'title': 'United States', 'about': 'Owens won the US title.'},
                {'wrestlers': ['Charlotte Flair', 'Rhea Ripley'], 'winner': 'Rhea Ripley',
                 'match_type': 'Singles', 'title': 'SmackDown Women', 'about': 'Rhea won the SmackDown Women\'s title.'},
                {'wrestlers': ['Bianca Belair', 'Asuka'], 'winner': 'Bianca Belair',
                 'match_type': 'Singles', 'title': 'Raw Women', 'about': 'Bianca retained against Asuka.'},
            ]),
            # WrestleMania 39 Night 2
            ({
                'name': 'WrestleMania 39 Sunday',
                'date': date(2023, 4, 2),
                'venue': 'SoFi Stadium',
                'location': 'Inglewood, CA',
                'attendance': 80497,
                'about': 'Roman\'s record reign continues.'
            }, [
                {'wrestlers': ['Roman Reigns', 'Cody Rhodes'], 'winner': 'Roman Reigns',
                 'match_type': 'Singles', 'title': 'Undisputed WWE Universal', 'about': 'Roman retained despite the entire arena wanting Cody to win.'},
                {'wrestlers': ['Brock Lesnar', 'Omos'], 'winner': 'Brock Lesnar',
                 'match_type': 'Singles', 'about': 'Lesnar suplexed the giant.'},
                {'wrestlers': ['Rey Mysterio', 'Dominik Mysterio'], 'winner': 'Rey Mysterio',
                 'match_type': 'Singles', 'about': 'Father defeated son.'},
            ]),
            # WrestleMania 40 Night 1
            ({
                'name': 'WrestleMania 40 Night 1',
                'date': date(2024, 4, 6),
                'venue': 'Lincoln Financial Field',
                'location': 'Philadelphia, PA',
                'attendance': 72000,
                'about': 'The Rock returns as a villain.'
            }, [
                {'wrestlers': ['Roman Reigns', 'The Rock', 'Cody Rhodes', 'Seth Rollins'], 'winner': 'Roman Reigns',
                 'match_type': 'Tag Team', 'about': 'Bloodline Rules tag match. Rock and Roman won.'},
                {'wrestlers': ['Bayley', 'Iyo Sky'], 'winner': 'Bayley',
                 'match_type': 'Singles', 'title': 'WWE Women', 'about': 'Bayley won the newly created WWE Women\'s Championship.'},
                {'wrestlers': ['Rhea Ripley', 'Becky Lynch'], 'winner': 'Rhea Ripley',
                 'match_type': 'Singles', 'title': 'World Women', 'about': 'Rhea retained the World Women\'s Championship.'},
            ]),
            # WrestleMania 40 Night 2
            ({
                'name': 'WrestleMania 40 Night 2',
                'date': date(2024, 4, 7),
                'venue': 'Lincoln Financial Field',
                'location': 'Philadelphia, PA',
                'attendance': 72000,
                'about': 'Cody Rhodes finishes his story.'
            }, [
                {'wrestlers': ['Cody Rhodes', 'Roman Reigns'], 'winner': 'Cody Rhodes',
                 'match_type': 'Bloodline Rules', 'title': 'Undisputed WWE', 'about': 'Cody finished his story and won the title!'},
                {'wrestlers': ['Drew McIntyre', 'Seth Rollins'], 'winner': 'Drew McIntyre',
                 'match_type': 'Singles', 'title': 'World Heavyweight', 'about': 'Drew won but CM Punk returned to cost him.'},
                {'wrestlers': ['LA Knight', 'AJ Styles'], 'winner': 'LA Knight',
                 'match_type': 'Singles', 'about': 'Knight got his WrestleMania moment.'},
            ]),
        ]

        for event_data, matches in events:
            self.create_event_with_matches(wwe, event_data, matches)
