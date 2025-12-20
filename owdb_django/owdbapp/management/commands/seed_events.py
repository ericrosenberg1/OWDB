"""
Comprehensive event seeding with full match cards.
Seeds historic PPV events from WWE, WCW, ECW, TNA, AEW, NJPW.

Usage:
    python manage.py seed_events --promotion=WWE --limit=50
    python manage.py seed_events --promotion=all
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Match, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic wrestling events with full match cards'

    def add_arguments(self, parser):
        parser.add_argument(
            '--promotion',
            type=str,
            default='all',
            help='Promotion to seed: WWE, WCW, ECW, TNA, AEW, NJPW, all'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum events to add per promotion'
        )

    def handle(self, *args, **options):
        promotion = options.get('promotion', 'all').upper()
        limit = options.get('limit', 1000)

        self.stdout.write(self.style.SUCCESS(f'\n=== Seeding Events ({promotion}) ===\n'))

        # Ensure we have the promotions
        self.ensure_promotions()

        if promotion in ['ALL', 'WWE']:
            self.seed_wwe_events(limit)
        if promotion in ['ALL', 'WCW']:
            self.seed_wcw_events(limit)
        if promotion in ['ALL', 'ECW']:
            self.seed_ecw_events(limit)
        if promotion in ['ALL', 'AEW']:
            self.seed_aew_events(limit)
        if promotion in ['ALL', 'NJPW']:
            self.seed_njpw_events(limit)

        self.stdout.write(self.style.SUCCESS('\n=== Event Seeding Complete ===\n'))
        self.print_stats()

    def ensure_promotions(self):
        """Ensure all required promotions exist."""
        promos = [
            {'name': 'World Wrestling Entertainment', 'abbreviation': 'WWE'},
            {'name': 'World Championship Wrestling', 'abbreviation': 'WCW'},
            {'name': 'Extreme Championship Wrestling', 'abbreviation': 'ECW'},
            {'name': 'Total Nonstop Action Wrestling', 'abbreviation': 'TNA'},
            {'name': 'All Elite Wrestling', 'abbreviation': 'AEW'},
            {'name': 'New Japan Pro-Wrestling', 'abbreviation': 'NJPW'},
        ]
        for p in promos:
            Promotion.objects.get_or_create(
                abbreviation=p['abbreviation'],
                defaults={'name': p['name']}
            )

    def print_stats(self):
        self.stdout.write(f'\nTotal Events: {Event.objects.count()}')
        self.stdout.write(f'Total Matches: {Match.objects.count()}')

    def get_or_create_wrestler(self, name):
        """Get or create a wrestler by name."""
        slug = slugify(name)
        wrestler = Wrestler.objects.filter(slug=slug).first()
        if wrestler:
            return wrestler
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if wrestler:
            return wrestler
        # Create new wrestler
        wrestler, _ = Wrestler.objects.get_or_create(
            name=name,
            defaults={'slug': slug}
        )
        return wrestler

    def get_or_create_venue(self, name, location=None):
        """Get or create a venue by name."""
        slug = slugify(name)
        venue = Venue.objects.filter(slug=slug).first()
        if venue:
            return venue
        venue, _ = Venue.objects.get_or_create(
            name=name,
            defaults={'slug': slug, 'location': location or ''}
        )
        return venue

    def get_title(self, title_name, promotion):
        """Get a title by name."""
        title = Title.objects.filter(name__iexact=title_name).first()
        if not title:
            title = Title.objects.filter(name__icontains=title_name.replace('Championship', '').strip()).first()
        return title

    def create_event_with_matches(self, promotion, event_data, matches_data):
        """Create an event with its full match card."""
        # Check if event already exists
        event_date = event_data['date']
        slug = slugify(f"{event_data['name']}-{event_date.year}")

        event = Event.objects.filter(slug=slug).first()
        if event:
            return event, False

        # Get or create venue
        venue = None
        if event_data.get('venue'):
            venue = self.get_or_create_venue(
                event_data['venue'],
                event_data.get('location')
            )

        # Create event
        event = Event.objects.create(
            name=event_data['name'],
            slug=slug,
            promotion=promotion,
            venue=venue,
            date=event_date,
            attendance=event_data.get('attendance'),
            about=event_data.get('about', '')
        )

        # Create matches
        for i, match_data in enumerate(matches_data):
            self.create_match(event, match_data, i + 1, promotion)

        return event, True

    def create_match(self, event, match_data, order, promotion):
        """Create a match with proper wrestler linking."""
        # Get wrestlers
        wrestlers = []
        for name in match_data.get('wrestlers', []):
            wrestler = self.get_or_create_wrestler(name)
            if wrestler:
                wrestlers.append(wrestler)

        # Get winner
        winner = None
        if match_data.get('winner'):
            winner = self.get_or_create_wrestler(match_data['winner'])

        # Get title if this is a title match
        title = None
        if match_data.get('title'):
            title = self.get_title(match_data['title'], promotion)

        # Create match
        match = Match.objects.create(
            event=event,
            match_text=match_data.get('match_text', ' vs '.join(match_data.get('wrestlers', []))),
            result=match_data.get('result', ''),
            winner=winner,
            match_type=match_data.get('match_type', ''),
            title=title,
            match_order=order,
            about=match_data.get('about', '')
        )

        # Add wrestlers to match
        for wrestler in wrestlers:
            match.wrestlers.add(wrestler)

        return match

    def seed_wwe_events(self, limit):
        """Seed WWE/WWF PPV events."""
        self.stdout.write('\n--- Seeding WWE/WWF Events ---\n')

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        if not wwe:
            return

        events_added = 0

        # WrestleMania I (1985)
        event_data = {
            'name': 'WrestleMania I',
            'date': date(1985, 3, 31),
            'venue': 'Madison Square Garden',
            'location': 'New York City, New York',
            'attendance': 19121,
            'about': 'The first WrestleMania, headlined by Hulk Hogan and Mr. T vs Roddy Piper and Paul Orndorff.'
        }
        matches = [
            {'wrestlers': ['Tito Santana', 'The Executioner'], 'winner': 'Tito Santana', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['King Kong Bundy', 'S.D. Jones'], 'winner': 'King Kong Bundy', 'result': 'Pinfall (9 seconds)', 'match_type': 'Singles Match'},
            {'wrestlers': ['Ricky Steamboat', 'Matt Borne'], 'winner': 'Ricky Steamboat', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Brutus Beefcake', 'David Sammartino'], 'winner': 'Draw', 'result': 'Double Disqualification', 'match_type': 'Singles Match'},
            {'wrestlers': ['Greg Valentine', 'Junkyard Dog'], 'winner': 'Junkyard Dog', 'result': 'Countout', 'title': 'WWF Intercontinental Championship', 'match_type': 'Intercontinental Title Match'},
            {'wrestlers': ['Iron Sheik', 'Nikolai Volkoff', 'U.S. Express'], 'winner': 'Iron Sheik and Nikolai Volkoff', 'result': 'Pinfall', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Andre the Giant', 'Big John Studd'], 'winner': 'Andre the Giant', 'result': 'Bodyslam', 'match_type': '$15,000 Bodyslam Match'},
            {'wrestlers': ['Wendi Richter', 'Leilani Kai'], 'winner': 'Wendi Richter', 'result': 'Pinfall', 'title': 'WWF Women\'s Championship', 'match_type': 'Women\'s Title Match'},
            {'wrestlers': ['Hulk Hogan', 'Mr. T', 'Roddy Piper', 'Paul Orndorff'], 'winner': 'Hulk Hogan and Mr. T', 'result': 'Pinfall', 'match_type': 'Tag Team Main Event', 'about': 'Special guest referee: Muhammad Ali. Jimmy Snuka and Bob Orton at ringside.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania III (1987)
        event_data = {
            'name': 'WrestleMania III',
            'date': date(1987, 3, 29),
            'venue': 'Pontiac Silverdome',
            'location': 'Pontiac, Michigan',
            'attendance': 93173,
            'about': 'Famous for Hulk Hogan vs Andre the Giant and the record-setting attendance.'
        }
        matches = [
            {'wrestlers': ['Can-Am Connection', 'Don Muraco', 'Bob Orton Jr.'], 'winner': 'Can-Am Connection', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Hercules', 'Billy Jack Haynes'], 'winner': 'Draw', 'result': 'Double Countout', 'match_type': 'Full Nelson Challenge'},
            {'wrestlers': ['King Kong Bundy', 'Hillbilly Jim'], 'winner': 'King Kong Bundy', 'match_type': 'Singles Match'},
            {'wrestlers': ['Junkyard Dog', 'King Harley Race'], 'winner': 'King Harley Race', 'result': 'Pinfall', 'match_type': 'Loser Must Bow Match'},
            {'wrestlers': ['Ricky Steamboat', 'Randy Savage'], 'winner': 'Ricky Steamboat', 'result': 'Pinfall', 'title': 'WWF Intercontinental Championship', 'match_type': 'Intercontinental Title Match', 'about': 'Considered one of the greatest matches in wrestling history.'},
            {'wrestlers': ['Jake Roberts', 'Honky Tonk Man'], 'winner': 'Honky Tonk Man', 'result': 'Countout', 'match_type': 'Singles Match'},
            {'wrestlers': ['Iron Sheik', 'Nikolai Volkoff', 'Killer Bees'], 'winner': 'Iron Sheik and Nikolai Volkoff', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Adrian Adonis', 'Roddy Piper'], 'winner': 'Roddy Piper', 'result': 'Pinfall', 'match_type': 'Hair vs Hair Match'},
            {'wrestlers': ['Hart Foundation', 'British Bulldogs'], 'winner': 'Hart Foundation', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Butch Reed', 'Koko B. Ware'], 'winner': 'Butch Reed', 'match_type': 'Singles Match'},
            {'wrestlers': ['Hulk Hogan', 'Andre the Giant'], 'winner': 'Hulk Hogan', 'result': 'Pinfall', 'title': 'WWF Championship', 'match_type': 'WWF Championship Match', 'about': 'Iconic bodyslam heard around the world. Hogan retained the WWF Championship.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania VI (1990) - Ultimate Challenge
        event_data = {
            'name': 'WrestleMania VI',
            'date': date(1990, 4, 1),
            'venue': 'SkyDome',
            'location': 'Toronto, Ontario, Canada',
            'attendance': 67678,
            'about': 'The Ultimate Challenge - Hulk Hogan vs Ultimate Warrior for both WWF and Intercontinental titles.'
        }
        matches = [
            {'wrestlers': ['Koko B. Ware', 'Rick Martel'], 'winner': 'Rick Martel', 'match_type': 'Singles Match'},
            {'wrestlers': ['Demolition', 'Colossal Connection'], 'winner': 'Demolition', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Earthquake', 'Hercules'], 'winner': 'Earthquake', 'match_type': 'Singles Match'},
            {'wrestlers': ['Brutus Beefcake', 'Mr. Perfect'], 'winner': 'Brutus Beefcake', 'match_type': 'Singles Match'},
            {'wrestlers': ['Roddy Piper', 'Bad News Brown'], 'winner': 'Draw', 'result': 'Double Countout', 'match_type': 'Singles Match'},
            {'wrestlers': ['Hart Foundation', 'Bolsheviks'], 'winner': 'Hart Foundation', 'result': 'Pinfall (19 seconds)', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Tito Santana', 'Barbarian'], 'winner': 'Barbarian', 'match_type': 'Singles Match'},
            {'wrestlers': ['Randy Savage', 'Dusty Rhodes'], 'winner': 'Randy Savage', 'match_type': 'Singles Match'},
            {'wrestlers': ['Jake Roberts', 'Ted DiBiase'], 'winner': 'Jake Roberts', 'result': 'Countout', 'match_type': 'Singles Match'},
            {'wrestlers': ['Big Boss Man', 'Akeem'], 'winner': 'Big Boss Man', 'match_type': 'Singles Match'},
            {'wrestlers': ['Rick Rude', 'Jimmy Snuka'], 'winner': 'Rick Rude', 'match_type': 'Singles Match'},
            {'wrestlers': ['Hulk Hogan', 'Ultimate Warrior'], 'winner': 'Ultimate Warrior', 'result': 'Pinfall', 'title': 'WWF Championship', 'match_type': 'Title vs Title Match', 'about': 'The Ultimate Challenge. Warrior won both the WWF Championship and retained his Intercontinental Championship.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania X (1994)
        event_data = {
            'name': 'WrestleMania X',
            'date': date(1994, 3, 20),
            'venue': 'Madison Square Garden',
            'location': 'New York City, New York',
            'attendance': 18065,
            'about': 'Return to Madison Square Garden. Featured Bret Hart vs Owen Hart and the Ladder Match.'
        }
        matches = [
            {'wrestlers': ['Bret Hart', 'Owen Hart'], 'winner': 'Owen Hart', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Owen defeated his brother Bret in the opening match.'},
            {'wrestlers': ['Lex Luger', 'Yokozuna'], 'winner': 'Yokozuna', 'result': 'Disqualification', 'title': 'WWF Championship', 'match_type': 'WWF Championship Match'},
            {'wrestlers': ['Razor Ramon', 'Shawn Michaels'], 'winner': 'Razor Ramon', 'result': 'Retrieved the titles', 'title': 'WWF Intercontinental Championship', 'match_type': 'Ladder Match', 'about': 'First WrestleMania Ladder Match. Considered a groundbreaking match.'},
            {'wrestlers': ['Randy Savage', 'Crush'], 'winner': 'Randy Savage', 'match_type': 'Falls Count Anywhere Match'},
            {'wrestlers': ['Earthquake', 'Adam Bomb'], 'winner': 'Earthquake', 'match_type': 'Singles Match'},
            {'wrestlers': ['Bret Hart', 'Yokozuna'], 'winner': 'Bret Hart', 'result': 'Pinfall', 'title': 'WWF Championship', 'match_type': 'WWF Championship Match', 'about': 'Bret Hart won his second WWF Championship after Yokozuna was distracted by Lex Luger.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania X-Seven (2001)
        event_data = {
            'name': 'WrestleMania X-Seven',
            'date': date(2001, 4, 1),
            'venue': 'Reliant Astrodome',
            'location': 'Houston, Texas',
            'attendance': 67925,
            'about': 'Often considered the greatest WrestleMania of all time. Featured Stone Cold vs The Rock in the main event.'
        }
        matches = [
            {'wrestlers': ['Chris Jericho', 'William Regal'], 'winner': 'Chris Jericho', 'title': 'WWF Intercontinental Championship', 'match_type': 'Intercontinental Title Match'},
            {'wrestlers': ['Tazz', 'Al Snow', 'APA', 'Dudley Boyz', 'Right to Censor'], 'winner': 'Dudley Boyz', 'match_type': 'APA Invitational Tag Team Battle Royal'},
            {'wrestlers': ['Kane', 'Raven', 'Big Show'], 'winner': 'Kane', 'title': 'WWF Hardcore Championship', 'match_type': 'Triple Threat Hardcore Match'},
            {'wrestlers': ['Eddie Guerrero', 'Test'], 'winner': 'Eddie Guerrero', 'title': 'WWF European Championship', 'match_type': 'European Title Match'},
            {'wrestlers': ['Kurt Angle', 'Chris Benoit'], 'winner': 'Kurt Angle', 'result': 'Submission', 'match_type': 'Singles Match', 'about': 'Technical wrestling clinic between two of the best.'},
            {'wrestlers': ['Chyna', 'Ivory'], 'winner': 'Chyna', 'title': 'WWF Women\'s Championship', 'match_type': 'Women\'s Title Match'},
            {'wrestlers': ['Shane McMahon', 'Vince McMahon'], 'winner': 'Shane McMahon', 'match_type': 'Street Fight', 'about': 'Mick Foley was special guest referee.'},
            {'wrestlers': ['Edge', 'Christian', 'Hardy Boyz', 'Dudley Boyz'], 'winner': 'Edge and Christian', 'title': 'WWF Tag Team Championship', 'match_type': 'TLC II', 'about': 'Tables, Ladders, and Chairs Match. One of the greatest tag matches ever.'},
            {'wrestlers': ['Gimmick Battle Royal participants'], 'winner': 'Iron Sheik', 'match_type': 'Gimmick Battle Royal'},
            {'wrestlers': ['Undertaker', 'Triple H'], 'winner': 'Undertaker', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Undertaker extended his WrestleMania streak to 9-0.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'The Rock'], 'winner': 'Stone Cold Steve Austin', 'result': 'Pinfall', 'title': 'WWF Championship', 'match_type': 'No Disqualification Match', 'about': 'Austin aligned with Vince McMahon to win the WWF Championship, turning heel.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania XIX (2003)
        event_data = {
            'name': 'WrestleMania XIX',
            'date': date(2003, 3, 30),
            'venue': 'Safeco Field',
            'location': 'Seattle, Washington',
            'attendance': 54097,
            'about': 'Featured Brock Lesnar vs Kurt Angle and the return of Hulk Hogan vs Vince McMahon.'
        }
        matches = [
            {'wrestlers': ['Rey Mysterio', 'Matt Hardy'], 'winner': 'Matt Hardy', 'title': 'WWE Cruiserweight Championship', 'match_type': 'Cruiserweight Title Match'},
            {'wrestlers': ['Undertaker', 'A-Train', 'Big Show'], 'winner': 'Undertaker', 'result': 'Pinfall', 'match_type': 'Handicap Match'},
            {'wrestlers': ['Trish Stratus', 'Jazz', 'Victoria'], 'winner': 'Trish Stratus', 'title': 'WWE Women\'s Championship', 'match_type': 'Triple Threat Match'},
            {'wrestlers': ['Team Angle', 'Los Guerreros'], 'winner': 'Team Angle', 'title': 'WWE Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Shawn Michaels', 'Chris Jericho'], 'winner': 'Shawn Michaels', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Excellent match between two of the best.'},
            {'wrestlers': ['Triple H', 'Booker T'], 'winner': 'Triple H', 'result': 'Pinfall', 'title': 'World Heavyweight Championship', 'match_type': 'World Title Match'},
            {'wrestlers': ['Hulk Hogan', 'Vince McMahon'], 'winner': 'Hulk Hogan', 'result': 'Pinfall', 'match_type': 'Street Fight'},
            {'wrestlers': ['The Rock', 'Stone Cold Steve Austin'], 'winner': 'The Rock', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Austin\'s final match. The Rock won in Austin\'s farewell.'},
            {'wrestlers': ['Brock Lesnar', 'Kurt Angle'], 'winner': 'Brock Lesnar', 'result': 'Pinfall', 'title': 'WWE Championship', 'match_type': 'WWE Championship Match', 'about': 'Lesnar won but botched a Shooting Star Press, legitimately injuring himself.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # WrestleMania 30 (2014)
        event_data = {
            'name': 'WrestleMania 30',
            'date': date(2014, 4, 6),
            'venue': 'Mercedes-Benz Superdome',
            'location': 'New Orleans, Louisiana',
            'attendance': 75167,
            'about': 'Featured The Streak ending and Daniel Bryan winning the WWE World Heavyweight Championship.'
        }
        matches = [
            {'wrestlers': ['Daniel Bryan', 'Triple H'], 'winner': 'Daniel Bryan', 'result': 'Submission', 'match_type': 'Singles Match', 'about': 'Bryan earned a spot in the main event by defeating Triple H.'},
            {'wrestlers': ['The Shield', 'New Age Outlaws', 'Kane'], 'winner': 'The Shield', 'result': 'Pinfall', 'match_type': 'Six-Man Tag Team Match'},
            {'wrestlers': ['Andre the Giant Memorial Battle Royal participants'], 'winner': 'Cesaro', 'match_type': 'Andre the Giant Memorial Battle Royal', 'about': 'First ever Andre the Giant Memorial Battle Royal.'},
            {'wrestlers': ['John Cena', 'Bray Wyatt'], 'winner': 'John Cena', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Brock Lesnar', 'Undertaker'], 'winner': 'Brock Lesnar', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'THE STREAK ENDS. Lesnar defeated Undertaker, ending his 21-0 WrestleMania streak.'},
            {'wrestlers': ['AJ Lee', 'Total Divas team'], 'winner': 'AJ Lee', 'title': 'WWE Divas Championship', 'match_type': 'Divas Championship Invitational'},
            {'wrestlers': ['Daniel Bryan', 'Randy Orton', 'Batista'], 'winner': 'Daniel Bryan', 'result': 'Submission', 'title': 'WWE World Heavyweight Championship', 'match_type': 'Triple Threat Match', 'about': 'YES Movement culminated in Bryan winning the unified WWE World Heavyweight Championship.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # SummerSlam 1992
        event_data = {
            'name': 'SummerSlam 1992',
            'date': date(1992, 8, 29),
            'venue': 'Wembley Stadium',
            'location': 'London, England',
            'attendance': 80355,
            'about': 'First major WWF event held in the UK. Featured Bret Hart vs British Bulldog for the IC Title.'
        }
        matches = [
            {'wrestlers': ['Legion of Doom', 'Money Inc.'], 'winner': 'Legion of Doom', 'result': 'Countout', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Nailz', 'Virgil'], 'winner': 'Nailz', 'match_type': 'Singles Match'},
            {'wrestlers': ['Shawn Michaels', 'Rick Martel'], 'winner': 'Shawn Michaels', 'match_type': 'Singles Match'},
            {'wrestlers': ['Tatanka', 'Berzerker'], 'winner': 'Tatanka', 'match_type': 'Singles Match'},
            {'wrestlers': ['Natural Disasters', 'Beverly Brothers'], 'winner': 'Natural Disasters', 'title': 'WWF Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Crush', 'Repo Man'], 'winner': 'Crush', 'match_type': 'Singles Match'},
            {'wrestlers': ['Ultimate Warrior', 'Randy Savage'], 'winner': 'Ultimate Warrior', 'result': 'Pinfall', 'title': 'WWF Championship', 'match_type': 'WWF Championship Match'},
            {'wrestlers': ['Undertaker', 'Kamala'], 'winner': 'Undertaker', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Bret Hart', 'British Bulldog'], 'winner': 'British Bulldog', 'result': 'Pinfall', 'title': 'WWF Intercontinental Championship', 'match_type': 'Intercontinental Title Match', 'about': 'Considered one of the greatest matches in WWF history. Bulldog won in front of 80,000 fans.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Royal Rumble 1992
        event_data = {
            'name': 'Royal Rumble 1992',
            'date': date(1992, 1, 19),
            'venue': 'Knickerbocker Arena',
            'location': 'Albany, New York',
            'attendance': 17000,
            'about': 'The vacant WWF Championship was on the line in the Royal Rumble match itself.'
        }
        matches = [
            {'wrestlers': ['Orient Express', 'New Foundation'], 'winner': 'Orient Express', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Mountie', 'Roddy Piper'], 'winner': 'Roddy Piper', 'result': 'Pinfall', 'title': 'WWF Intercontinental Championship', 'match_type': 'Intercontinental Title Match'},
            {'wrestlers': ['Beverly Brothers', 'Bushwhackers'], 'winner': 'Beverly Brothers', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Royal Rumble Match participants'], 'winner': 'Ric Flair', 'result': 'Last eliminated Sid Justice', 'title': 'WWF Championship', 'match_type': 'Royal Rumble Match', 'about': 'Ric Flair won the WWF Championship by lasting 60+ minutes as the #3 entrant.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Survivor Series 1997 (Montreal Screwjob)
        event_data = {
            'name': 'Survivor Series 1997',
            'date': date(1997, 11, 9),
            'venue': 'Molson Centre',
            'location': 'Montreal, Quebec, Canada',
            'attendance': 20593,
            'about': 'The infamous Montreal Screwjob occurred during the main event.'
        }
        matches = [
            {'wrestlers': ['Team USA', 'Team Canada'], 'winner': 'Team USA', 'match_type': 'Survivor Series Elimination Match'},
            {'wrestlers': ['Taka Michinoku', 'Brian Christopher'], 'winner': 'Taka Michinoku', 'title': 'WWF Light Heavyweight Championship', 'match_type': 'Light Heavyweight Title Tournament Final'},
            {'wrestlers': ['Team LOD', 'Team Nation'], 'winner': 'Team LOD', 'match_type': 'Survivor Series Elimination Match'},
            {'wrestlers': ['Kane', 'Mankind'], 'winner': 'Kane', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Stone Cold Steve Austin', 'Owen Hart', 'Team Canada', 'Team USA'], 'winner': 'Stone Cold Steve Austin (sole survivor)', 'title': 'WWF Intercontinental Championship', 'match_type': 'Survivor Series Elimination Match'},
            {'wrestlers': ['Bret Hart', 'Shawn Michaels'], 'winner': 'Shawn Michaels', 'result': 'Submission (controversial)', 'title': 'WWF Championship', 'match_type': 'WWF Championship Match', 'about': 'The Montreal Screwjob. Vince McMahon ordered the referee to ring the bell while Michaels had Hart in his own Sharpshooter.'},
        ]
        event, created = self.create_event_with_matches(wwe, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} WWE events')

    def seed_wcw_events(self, limit):
        """Seed WCW PPV events."""
        self.stdout.write('\n--- Seeding WCW Events ---\n')

        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        if not wcw:
            return

        events_added = 0

        # Starrcade 1997 (nWo vs WCW)
        event_data = {
            'name': 'Starrcade 1997',
            'date': date(1997, 12, 28),
            'venue': 'MCI Center',
            'location': 'Washington, D.C.',
            'attendance': 17500,
            'about': 'Featured Sting vs Hollywood Hogan for the WCW World Heavyweight Championship.'
        }
        matches = [
            {'wrestlers': ['Cruiserweight Battle Royal participants'], 'winner': 'Dean Malenko', 'title': 'WCW Cruiserweight Championship', 'match_type': 'Cruiserweight Battle Royal'},
            {'wrestlers': ['Perry Saturn', 'Disco Inferno'], 'winner': 'Perry Saturn', 'title': 'WCW Television Championship', 'match_type': 'Television Title Match'},
            {'wrestlers': ['Buff Bagwell', 'Lex Luger'], 'winner': 'Lex Luger', 'result': 'Submission', 'match_type': 'Singles Match'},
            {'wrestlers': ['Chris Benoit', 'Perry Saturn', 'Dean Malenko', 'Curt Hennig'], 'winner': 'Ric Flair (sub for Benoit)', 'match_type': 'Four Corners Match'},
            {'wrestlers': ['Scott Hall', 'Larry Zbyszko'], 'winner': 'Larry Zbyszko', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Eric Bischoff', 'Larry Zbyszko'], 'winner': 'Larry Zbyszko', 'match_type': 'Special Referee Match'},
            {'wrestlers': ['Sting', 'Hollywood Hogan'], 'winner': 'Sting', 'result': 'Submission', 'title': 'WCW World Heavyweight Championship', 'match_type': 'WCW Championship Match', 'about': 'Sting ended Hogan\'s 18-month reign in a controversial finish.'},
        ]
        event, created = self.create_event_with_matches(wcw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Bash at the Beach 1996 (nWo Formation)
        event_data = {
            'name': 'Bash at the Beach 1996',
            'date': date(1996, 7, 7),
            'venue': 'Ocean Center',
            'location': 'Daytona Beach, Florida',
            'attendance': 8300,
            'about': 'The night the nWo was formed. Hulk Hogan turned heel and joined Hall and Nash.'
        }
        matches = [
            {'wrestlers': ['Rey Mysterio', 'Psicosis'], 'winner': 'Rey Mysterio', 'match_type': 'Cruiserweight Match'},
            {'wrestlers': ['John Tenta', 'Big Bubba Rogers'], 'winner': 'John Tenta', 'match_type': 'Carson City Silver Dollar Match'},
            {'wrestlers': ['Dean Malenko', 'Disco Inferno'], 'winner': 'Dean Malenko', 'title': 'WCW Cruiserweight Championship', 'match_type': 'Cruiserweight Title Match'},
            {'wrestlers': ['Diamond Dallas Page', 'Hacksaw Jim Duggan'], 'winner': 'Diamond Dallas Page', 'match_type': 'Taped Fist Match'},
            {'wrestlers': ['Konnan', 'Ric Flair'], 'winner': 'Konnan', 'title': 'WCW United States Championship', 'match_type': 'US Title Match'},
            {'wrestlers': ['Outsiders', 'Sting', 'Lex Luger', 'Randy Savage'], 'winner': 'Outsiders', 'result': 'Pinfall', 'match_type': 'Six-Man Tag Team Match', 'about': 'Hulk Hogan turned heel, joining Scott Hall and Kevin Nash to form the New World Order.'},
        ]
        event, created = self.create_event_with_matches(wcw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Halloween Havoc 1997
        event_data = {
            'name': 'Halloween Havoc 1997',
            'date': date(1997, 10, 26),
            'venue': 'MGM Grand Garden Arena',
            'location': 'Las Vegas, Nevada',
            'attendance': 12457,
            'about': 'Featured Eddie Guerrero vs Rey Mysterio in a classic cruiserweight match.'
        }
        matches = [
            {'wrestlers': ['Yuji Nagata', 'Ultimo Dragon'], 'winner': 'Yuji Nagata', 'match_type': 'Singles Match'},
            {'wrestlers': ['Chris Jericho', 'Gedo'], 'winner': 'Chris Jericho', 'match_type': 'Singles Match'},
            {'wrestlers': ['Eddie Guerrero', 'Rey Mysterio'], 'winner': 'Eddie Guerrero', 'result': 'Pinfall', 'title': 'WCW Cruiserweight Championship', 'match_type': 'Title vs Mask Match', 'about': 'Rey Mysterio lost his mask in this classic encounter.'},
            {'wrestlers': ['Steve McMichael', 'Alex Wright'], 'winner': 'Steve McMichael', 'match_type': 'Singles Match'},
            {'wrestlers': ['Disco Inferno', 'Jacqueline'], 'winner': 'Disco Inferno', 'title': 'WCW Television Championship', 'match_type': 'Television Title Match'},
            {'wrestlers': ['Lex Luger', 'Scott Hall'], 'winner': 'Lex Luger', 'result': 'Submission', 'match_type': 'Steel Cage Match'},
            {'wrestlers': ['Randy Savage', 'Diamond Dallas Page'], 'winner': 'Diamond Dallas Page', 'result': 'Pinfall', 'match_type': 'Las Vegas Sudden Death Match'},
            {'wrestlers': ['Hollywood Hogan', 'Roddy Piper'], 'winner': 'Hollywood Hogan', 'result': 'Pinfall', 'match_type': 'Steel Cage Match'},
        ]
        event, created = self.create_event_with_matches(wcw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Starrcade 1983 (First Starrcade)
        event_data = {
            'name': 'Starrcade 1983',
            'date': date(1983, 11, 24),
            'venue': 'Greensboro Coliseum',
            'location': 'Greensboro, North Carolina',
            'attendance': 15447,
            'about': 'The first Starrcade, considered the first true wrestling supercard/PPV concept.'
        }
        matches = [
            {'wrestlers': ['Bugsy McGraw', 'Rufus R. Jones', 'Masked Superstar', 'Dick Slater'], 'winner': 'Bugsy McGraw and Rufus R. Jones', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Johnny Weaver', 'Scott McGhee', 'Kevin Sullivan', 'Mark Lewin'], 'winner': 'Johnny Weaver and Scott McGhee', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Carlos Colon', 'Abdullah the Butcher'], 'winner': 'Carlos Colon', 'match_type': 'Caribbean Championship Match'},
            {'wrestlers': ['Charlie Brown', 'Great Kabuki'], 'winner': 'Great Kabuki', 'match_type': 'Singles Match'},
            {'wrestlers': ['Ricky Steamboat', 'Wahoo McDaniel', 'Jay Youngblood'], 'winner': 'Ricky Steamboat', 'title': 'NWA Television Championship', 'match_type': 'TV Title Gauntlet'},
            {'wrestlers': ['Harley Race', 'Ric Flair'], 'winner': 'Ric Flair', 'result': 'Pinfall', 'title': 'NWA World Heavyweight Championship', 'match_type': 'Steel Cage Match', 'about': 'Ric Flair won the NWA World Heavyweight Championship in a steel cage.'},
        ]
        event, created = self.create_event_with_matches(wcw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} WCW events')

    def seed_ecw_events(self, limit):
        """Seed ECW PPV events."""
        self.stdout.write('\n--- Seeding ECW Events ---\n')

        ecw = Promotion.objects.filter(abbreviation='ECW').first()
        if not ecw:
            return

        events_added = 0

        # Barely Legal 1997 (First ECW PPV)
        event_data = {
            'name': 'Barely Legal 1997',
            'date': date(1997, 4, 13),
            'venue': 'ECW Arena',
            'location': 'Philadelphia, Pennsylvania',
            'attendance': 1300,
            'about': 'ECW\'s first-ever pay-per-view event. Marked their arrival on the national stage.'
        }
        matches = [
            {'wrestlers': ['Eliminators', 'Dudley Boyz'], 'winner': 'Eliminators', 'title': 'ECW World Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Lance Storm', 'Rob Van Dam'], 'winner': 'Rob Van Dam', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Michinoku Pro wrestlers'], 'winner': 'Great Sasuke', 'match_type': 'Six-Man Tag Team Match'},
            {'wrestlers': ['Shane Douglas', 'Pitbull #2'], 'winner': 'Shane Douglas', 'title': 'ECW Television Championship', 'match_type': 'Television Title Match'},
            {'wrestlers': ['Sabu', 'Taz'], 'winner': 'Sabu', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Sandman', 'Stevie Richards'], 'winner': 'Sandman', 'match_type': 'Singapore Cane Match'},
            {'wrestlers': ['Terry Funk', 'Raven'], 'winner': 'Terry Funk', 'result': 'Pinfall', 'title': 'ECW World Heavyweight Championship', 'match_type': 'ECW Championship Match', 'about': 'Terry Funk won the ECW World Championship in ECW\'s first PPV main event.'},
        ]
        event, created = self.create_event_with_matches(ecw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # One Night Stand 2005 (ECW Revival)
        event_data = {
            'name': 'ECW One Night Stand 2005',
            'date': date(2005, 6, 12),
            'venue': 'Hammerstein Ballroom',
            'location': 'New York City, New York',
            'attendance': 2500,
            'about': 'WWE\'s tribute to ECW. Featured returning ECW originals and WWE invaders.'
        }
        matches = [
            {'wrestlers': ['Lance Storm', 'Chris Jericho'], 'winner': 'Lance Storm', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Super Crazy', 'Tajiri', 'Little Guido'], 'winner': 'Super Crazy', 'result': 'Pinfall', 'match_type': 'Triple Threat Match'},
            {'wrestlers': ['Psicosis', 'Rey Mysterio'], 'winner': 'Rey Mysterio', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Rhyno', 'Sabu'], 'winner': 'Sabu', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Mike Awesome', 'Masato Tanaka'], 'winner': 'Mike Awesome', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Chris Benoit', 'Eddie Guerrero'], 'winner': 'Eddie Guerrero', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Dudley Boyz', 'Tommy Dreamer', 'Sandman'], 'winner': 'Dudley Boyz', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Tommy Dreamer', 'The Sandman', 'Beulah McGillicutty', 'Dudley Boyz', 'BWO'], 'winner': 'Tommy Dreamer and Sandman', 'match_type': 'Intergender Tag Team Match'},
        ]
        event, created = self.create_event_with_matches(ecw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} ECW events')

    def seed_aew_events(self, limit):
        """Seed AEW PPV events."""
        self.stdout.write('\n--- Seeding AEW Events ---\n')

        aew = Promotion.objects.filter(abbreviation='AEW').first()
        if not aew:
            return

        events_added = 0

        # Double or Nothing 2019 (First AEW PPV)
        event_data = {
            'name': 'Double or Nothing 2019',
            'date': date(2019, 5, 25),
            'venue': 'MGM Grand Garden Arena',
            'location': 'Las Vegas, Nevada',
            'attendance': 14129,
            'about': 'AEW\'s first-ever pay-per-view event and the beginning of the company.'
        }
        matches = [
            {'wrestlers': ['Casino Battle Royal participants'], 'winner': 'Hangman Adam Page', 'match_type': 'Casino Battle Royal', 'about': 'Winner earned a future AEW World Championship match.'},
            {'wrestlers': ['Sammy Guevara', 'Kip Sabian'], 'winner': 'Kip Sabian', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['So Cal Uncensored', 'Strong Hearts'], 'winner': 'SCU', 'result': 'Pinfall', 'match_type': 'Six-Man Tag Team Match'},
            {'wrestlers': ['Best Friends', 'Angelico', 'Jack Evans'], 'winner': 'Best Friends', 'result': 'Pinfall', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Riho', 'Hikaru Shida', 'Aja Kong', 'Yuka Sakazaki'], 'winner': 'Hikaru Shida', 'match_type': 'Fatal Four-Way Match'},
            {'wrestlers': ['Cody', 'Dustin Rhodes'], 'winner': 'Cody', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Emotional match between the Rhodes brothers.'},
            {'wrestlers': ['Young Bucks', 'Lucha Brothers'], 'winner': 'Young Bucks', 'result': 'Pinfall', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Chris Jericho', 'Kenny Omega'], 'winner': 'Chris Jericho', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'Jericho earned the right to face the first AEW World Champion.'},
        ]
        event, created = self.create_event_with_matches(aew, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # All Out 2021
        event_data = {
            'name': 'All Out 2021',
            'date': date(2021, 9, 5),
            'venue': 'NOW Arena',
            'location': 'Hoffman Estates, Illinois',
            'attendance': 10107,
            'about': 'Featured debuts of Adam Cole and Bryan Danielson. CM Punk\'s first match in 7 years.'
        }
        matches = [
            {'wrestlers': ['Casino Battle Royal participants'], 'winner': 'Ruby Soho', 'match_type': 'Casino Battle Royal', 'about': 'Ruby Soho debuted and won the battle royal.'},
            {'wrestlers': ['Miro', 'Eddie Kingston'], 'winner': 'Miro', 'result': 'Submission', 'title': 'AEW TNT Championship', 'match_type': 'TNT Championship Match'},
            {'wrestlers': ['Young Bucks', 'Lucha Brothers'], 'winner': 'Lucha Brothers', 'result': 'Pinfall', 'title': 'AEW World Tag Team Championship', 'match_type': 'Steel Cage Match'},
            {'wrestlers': ['Britt Baker', 'Kris Statlander'], 'winner': 'Britt Baker', 'result': 'Submission', 'title': 'AEW Women\'s World Championship', 'match_type': 'Women\'s Title Match'},
            {'wrestlers': ['CM Punk', 'Darby Allin'], 'winner': 'CM Punk', 'result': 'Pinfall', 'match_type': 'Singles Match', 'about': 'CM Punk\'s first match in over 7 years. His AEW in-ring debut.'},
            {'wrestlers': ['Chris Jericho', 'MJF'], 'winner': 'MJF', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Kenny Omega', 'Christian Cage'], 'winner': 'Kenny Omega', 'result': 'Pinfall', 'title': 'AEW World Championship', 'match_type': 'World Championship Match', 'about': 'Adam Cole and Bryan Danielson debuted after the match.'},
        ]
        event, created = self.create_event_with_matches(aew, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Revolution 2024
        event_data = {
            'name': 'Revolution 2024',
            'date': date(2024, 3, 3),
            'venue': 'Greensboro Coliseum',
            'location': 'Greensboro, North Carolina',
            'attendance': 9026,
            'about': 'Featured Samoa Joe vs Swerve Strickland for the AEW World Championship.'
        }
        matches = [
            {'wrestlers': ['FTR', 'Young Bucks'], 'winner': 'Young Bucks', 'result': 'Pinfall', 'title': 'AEW World Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Orange Cassidy', 'Roderick Strong'], 'winner': 'Orange Cassidy', 'title': 'AEW International Championship', 'match_type': 'International Title Match'},
            {'wrestlers': ['Willow Nightingale', 'Julia Hart'], 'winner': 'Julia Hart', 'title': 'TBS Championship', 'match_type': 'TBS Title Match'},
            {'wrestlers': ['Bryan Danielson', 'Eddie Kingston'], 'winner': 'Bryan Danielson', 'result': 'Submission', 'match_type': 'Singles Match'},
            {'wrestlers': ['Sting', 'Darby Allin', 'Young Bucks'], 'winner': 'Sting and Darby Allin', 'match_type': 'Tornado Tag Team Match', 'about': 'Sting\'s final match in a successful AEW run.'},
            {'wrestlers': ['Samoa Joe', 'Swerve Strickland'], 'winner': 'Swerve Strickland', 'result': 'Pinfall', 'title': 'AEW World Championship', 'match_type': 'World Championship Match', 'about': 'Swerve Strickland won his first AEW World Championship.'},
        ]
        event, created = self.create_event_with_matches(aew, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} AEW events')

    def seed_njpw_events(self, limit):
        """Seed NJPW major events."""
        self.stdout.write('\n--- Seeding NJPW Events ---\n')

        njpw = Promotion.objects.filter(abbreviation='NJPW').first()
        if not njpw:
            return

        events_added = 0

        # Wrestle Kingdom 9 (2015)
        event_data = {
            'name': 'Wrestle Kingdom 9',
            'date': date(2015, 1, 4),
            'venue': 'Tokyo Dome',
            'location': 'Tokyo, Japan',
            'attendance': 36000,
            'about': 'Featured Hiroshi Tanahashi vs Kazuchika Okada in the main event.'
        }
        matches = [
            {'wrestlers': ['Time Splitters', 'Young Bucks', 'reDRagon'], 'winner': 'Young Bucks', 'title': 'IWGP Junior Heavyweight Tag Team Championship', 'match_type': 'Three-Way Tag Team Match'},
            {'wrestlers': ['Tomohiro Ishii', 'Togi Makabe'], 'winner': 'Togi Makabe', 'title': 'NEVER Openweight Championship', 'match_type': 'NEVER Title Match'},
            {'wrestlers': ['Bullet Club', 'Hirooki Goto', 'Katsuyori Shibata'], 'winner': 'Hirooki Goto and Katsuyori Shibata', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['Tetsuya Naito', 'AJ Styles'], 'winner': 'AJ Styles', 'result': 'Pinfall', 'match_type': 'Singles Match'},
            {'wrestlers': ['Shinsuke Nakamura', 'Kota Ibushi'], 'winner': 'Shinsuke Nakamura', 'result': 'Pinfall', 'title': 'IWGP Intercontinental Championship', 'match_type': 'Intercontinental Title Match', 'about': 'Considered one of the best matches in wrestling history.'},
            {'wrestlers': ['Hiroshi Tanahashi', 'Kazuchika Okada'], 'winner': 'Hiroshi Tanahashi', 'result': 'Pinfall', 'title': 'IWGP Heavyweight Championship', 'match_type': 'IWGP Title Match', 'about': 'Tanahashi won his seventh IWGP Heavyweight Championship.'},
        ]
        event, created = self.create_event_with_matches(njpw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        # Dominion 2018
        event_data = {
            'name': 'Dominion 2018',
            'date': date(2018, 6, 9),
            'venue': 'Osaka-jo Hall',
            'location': 'Osaka, Japan',
            'attendance': 11027,
            'about': 'Featured Kenny Omega winning the IWGP Heavyweight Championship from Kazuchika Okada.'
        }
        matches = [
            {'wrestlers': ['Jushin Liger', 'Tiger Mask', 'Bullet Club'], 'winner': 'Jushin Liger and Tiger Mask', 'match_type': 'Tag Team Match'},
            {'wrestlers': ['SANADA', 'Zack Sabre Jr.'], 'winner': 'Zack Sabre Jr.', 'result': 'Submission', 'match_type': 'Singles Match'},
            {'wrestlers': ['Tetsuya Naito', 'Chris Jericho'], 'winner': 'Tetsuya Naito', 'result': 'Pinfall', 'title': 'IWGP Intercontinental Championship', 'match_type': 'Intercontinental Title Match', 'about': 'Naito defeated Jericho in a brutal encounter.'},
            {'wrestlers': ['Hirooki Goto', 'Juice Robinson'], 'winner': 'Juice Robinson', 'result': 'Pinfall', 'title': 'IWGP United States Championship', 'match_type': 'US Title Match'},
            {'wrestlers': ['Young Bucks', 'Los Ingobernables de Japon'], 'winner': 'Young Bucks', 'title': 'IWGP Tag Team Championship', 'match_type': 'Tag Team Title Match'},
            {'wrestlers': ['Kazuchika Okada', 'Kenny Omega'], 'winner': 'Kenny Omega', 'result': 'Pinfall', 'title': 'IWGP Heavyweight Championship', 'match_type': 'IWGP Title Match', 'about': 'Kenny Omega won the IWGP Heavyweight Championship in their historic 2-out-of-3 falls match.'},
        ]
        event, created = self.create_event_with_matches(njpw, event_data, matches)
        if created:
            self.stdout.write(f'  + {event.name}')
            events_added += 1

        self.stdout.write(f'\nAdded {events_added} NJPW events')
