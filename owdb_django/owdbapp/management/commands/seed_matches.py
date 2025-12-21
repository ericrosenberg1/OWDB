"""
Comprehensive match seeder with proper wrestler, title, and event linking.

Generates thousands of matches for TV episodes and PPV events,
properly linking to existing wrestlers, titles, and events.

Usage:
    python manage.py seed_matches
    python manage.py seed_matches --promotion=WWE
    python manage.py seed_matches --year=1998
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date, timedelta
import random
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title
)


class Command(BaseCommand):
    help = 'Seed matches for events with wrestler and title links'

    def add_arguments(self, parser):
        parser.add_argument(
            '--promotion',
            type=str,
            help='Only seed for specific promotion (WWE, AEW, WCW, etc.)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Only seed for specific year'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of events to process'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING MATCHES ===\n'))

        promo_filter = options.get('promotion')
        year_filter = options.get('year')
        limit = options.get('limit', 0)

        # Build wrestler roster by promotion era
        self.build_rosters()

        # Build title mappings
        self.build_title_maps()

        # Get events to process
        events = Event.objects.all().order_by('date')

        if promo_filter:
            events = events.filter(promotion__abbreviation__iexact=promo_filter)
        if year_filter:
            events = events.filter(date__year=year_filter)
        if limit:
            events = events[:limit]

        total_events = events.count()
        self.stdout.write(f'Processing {total_events} events...\n')

        created_matches = 0
        processed_events = 0

        for event in events.select_related('promotion'):
            matches = self.generate_matches_for_event(event)
            created_matches += matches
            processed_events += 1

            if processed_events % 500 == 0:
                self.stdout.write(f'  Processed {processed_events}/{total_events} events, {created_matches} matches...')

        self.stdout.write(self.style.SUCCESS(f'\n=== SEEDING COMPLETE ==='))
        self.stdout.write(f'Events processed: {processed_events}')
        self.stdout.write(f'Matches created: {created_matches}')
        self.stdout.write(f'Total matches in DB: {Match.objects.count()}')

    def build_rosters(self):
        """Build wrestler rosters by promotion and era."""
        self.rosters = {}

        # WWE main roster (all eras combined)
        wwe_wrestlers = [
            'Stone Cold Steve Austin', 'The Rock', 'John Cena', 'Triple H',
            'The Undertaker', 'Shawn Michaels', 'Bret Hart', 'Randy Savage',
            'Hulk Hogan', 'Ultimate Warrior', 'Ric Flair', 'Rey Mysterio',
            'Eddie Guerrero', 'Chris Jericho', 'CM Punk', 'Edge', 'Randy Orton',
            'Batista', 'Kurt Angle', 'Mick Foley', 'Big Show', 'Kane',
            'Roman Reigns', 'Seth Rollins', 'Dean Ambrose', 'AJ Styles',
            'Kevin Owens', 'Sami Zayn', 'Finn Balor', 'Becky Lynch',
            'Charlotte Flair', 'Sasha Banks', 'Bayley', 'Bianca Belair',
            'Drew McIntyre', 'Bobby Lashley', 'Brock Lesnar', 'Goldberg',
            'Daniel Bryan', 'Kofi Kingston', 'Big E', 'Xavier Woods',
            'The Miz', 'Dolph Ziggler', 'Cesaro', 'Sheamus', 'Jeff Hardy',
            'Matt Hardy', 'Booker T', 'Mark Henry', 'Rob Van Dam', 'Mankind'
        ]

        # AEW roster
        aew_wrestlers = [
            'Kenny Omega', 'Jon Moxley', 'Chris Jericho', 'Cody Rhodes',
            'Hangman Adam Page', 'MJF', 'CM Punk', 'Bryan Danielson',
            'Adam Cole', 'Jade Cargill', 'Britt Baker', 'Thunder Rosa',
            'Orange Cassidy', 'Darby Allin', 'Sting', 'Miro', 'Andrade',
            'PAC', 'Penta El Zero M', 'Rey Fenix', 'Jungle Boy', 'Luchasaurus',
            'Dustin Rhodes', 'Matt Hardy', 'Jeff Hardy', 'Eddie Kingston',
            'Santana', 'Ortiz', 'FTR', 'Young Bucks', 'Wardlow', 'Ricky Starks',
            'Powerhouse Hobbs', 'Hook', 'Swerve Strickland', 'Keith Lee',
            'Will Ospreay', 'Samoa Joe', 'Christian Cage', 'Toni Storm'
        ]

        # WCW roster
        wcw_wrestlers = [
            'Hulk Hogan', 'Ric Flair', 'Sting', 'Goldberg', 'Kevin Nash',
            'Scott Hall', 'Diamond Dallas Page', 'Booker T', 'Randy Savage',
            'Bret Hart', 'Chris Jericho', 'Eddie Guerrero', 'Rey Mysterio',
            'Chris Benoit', 'Dean Malenko', 'Perry Saturn', 'Raven',
            'Scott Steiner', 'Rick Steiner', 'Lex Luger', 'The Giant',
            'Buff Bagwell', 'Konnan', 'Juventud Guerrera', 'Psicosis',
            'La Parka', 'Disco Inferno', 'Alex Wright', 'Fit Finlay'
        ]

        # ECW roster
        ecw_wrestlers = [
            'Tommy Dreamer', 'The Sandman', 'Sabu', 'Taz', 'Rob Van Dam',
            'Raven', 'Terry Funk', 'Mick Foley', 'Shane Douglas', 'Bam Bam Bigelow',
            'Mike Awesome', 'Masato Tanaka', 'Jerry Lynn', 'Lance Storm',
            'Chris Jericho', 'Eddie Guerrero', 'Rey Mysterio', 'Chris Benoit',
            'Dean Malenko', 'Tajiri', 'Super Crazy', 'Little Guido',
            'Rhyno', 'Justin Credible', 'Steve Corino', 'Spike Dudley',
            'Bubba Ray Dudley', 'D-Von Dudley', 'New Jack', 'Balls Mahoney'
        ]

        # TNA/Impact roster
        tna_wrestlers = [
            'AJ Styles', 'Samoa Joe', 'Kurt Angle', 'Sting', 'Jeff Hardy',
            'Jeff Jarrett', 'Bobby Roode', 'James Storm', 'Austin Aries',
            'Bobby Lashley', 'EC3', 'Magnus', 'Christopher Daniels',
            'Frankie Kazarian', 'Chris Sabin', 'Alex Shelley', 'Abyss',
            'Matt Morgan', 'Bully Ray', 'Mr. Anderson', 'The Pope',
            'Desmond Wolfe', 'Rob Van Dam', 'Rhino', 'LAX', 'Motor City Machine Guns'
        ]

        # NXT roster
        nxt_wrestlers = [
            'Finn Balor', 'Samoa Joe', 'Shinsuke Nakamura', 'Asuka',
            'Kevin Owens', 'Sami Zayn', 'Bayley', 'Sasha Banks',
            'Charlotte Flair', 'Becky Lynch', 'Adam Cole', 'Johnny Gargano',
            'Tommaso Ciampa', 'Velveteen Dream', 'Aleister Black', 'Ricochet',
            'Keith Lee', 'Karrion Kross', 'Io Shirai', 'Rhea Ripley',
            'Bianca Belair', 'Pat McAfee', 'Bron Breakker', 'Carmelo Hayes'
        ]

        # Map wrestlers to DB objects
        for roster_name, wrestler_names in [
            ('WWE', wwe_wrestlers), ('AEW', aew_wrestlers), ('WCW', wcw_wrestlers),
            ('ECW', ecw_wrestlers), ('TNA', tna_wrestlers), ('NXT', nxt_wrestlers)
        ]:
            self.rosters[roster_name] = []
            for name in wrestler_names:
                # Try exact match first, then partial
                wrestler = Wrestler.objects.filter(name__iexact=name).first()
                if not wrestler:
                    wrestler = Wrestler.objects.filter(name__icontains=name).first()
                if wrestler:
                    self.rosters[roster_name].append(wrestler)
            self.stdout.write(f'  {roster_name}: {len(self.rosters[roster_name])} wrestlers found')

    def build_title_maps(self):
        """Map titles by promotion."""
        self.titles = {}

        # WWE titles
        self.titles['WWE'] = list(Title.objects.filter(
            promotion__abbreviation__in=['WWE', 'WWF']
        )[:10])

        # AEW titles
        self.titles['AEW'] = list(Title.objects.filter(
            promotion__abbreviation='AEW'
        )[:8])

        # WCW titles
        self.titles['WCW'] = list(Title.objects.filter(
            promotion__abbreviation='WCW'
        )[:8])

        # ECW titles
        self.titles['ECW'] = list(Title.objects.filter(
            promotion__abbreviation='ECW'
        )[:6])

        # TNA/Impact titles
        self.titles['TNA'] = list(Title.objects.filter(
            promotion__abbreviation__in=['TNA', 'IMPACT']
        )[:8])

        for promo, titles in self.titles.items():
            self.stdout.write(f'  {promo}: {len(titles)} titles found')

    def get_roster_for_event(self, event):
        """Get appropriate roster for an event based on promotion and year."""
        promo_abbr = event.promotion.abbreviation if event.promotion else 'WWE'

        # Map promotion abbreviations
        if promo_abbr in ['WWF', 'WWE']:
            return self.rosters.get('WWE', [])
        elif promo_abbr == 'AEW':
            return self.rosters.get('AEW', [])
        elif promo_abbr == 'WCW':
            return self.rosters.get('WCW', [])
        elif promo_abbr == 'ECW':
            return self.rosters.get('ECW', [])
        elif promo_abbr in ['TNA', 'IMPACT']:
            return self.rosters.get('TNA', [])
        else:
            # Default to WWE roster
            return self.rosters.get('WWE', [])

    def get_titles_for_event(self, event):
        """Get titles for event's promotion."""
        promo_abbr = event.promotion.abbreviation if event.promotion else 'WWE'

        if promo_abbr in ['WWF', 'WWE']:
            return self.titles.get('WWE', [])
        elif promo_abbr == 'AEW':
            return self.titles.get('AEW', [])
        elif promo_abbr == 'WCW':
            return self.titles.get('WCW', [])
        elif promo_abbr == 'ECW':
            return self.titles.get('ECW', [])
        elif promo_abbr in ['TNA', 'IMPACT']:
            return self.titles.get('TNA', [])
        return []

    def generate_matches_for_event(self, event):
        """Generate matches for a single event."""
        # Skip if event already has matches
        if event.matches.exists():
            return 0

        roster = self.get_roster_for_event(event)
        if len(roster) < 4:
            return 0

        titles = self.get_titles_for_event(event)

        # Determine number of matches based on event type
        event_name_lower = event.name.lower()

        if any(x in event_name_lower for x in ['wrestlemania', 'summerslam', 'royal rumble', 'survivor series']):
            num_matches = random.randint(8, 12)
            title_match_chance = 0.5
        elif any(x in event_name_lower for x in ['all out', 'full gear', 'revolution', 'double or nothing']):
            num_matches = random.randint(8, 11)
            title_match_chance = 0.5
        elif any(x in event_name_lower for x in ['starrcade', 'bash at the beach', 'halloween havoc']):
            num_matches = random.randint(7, 10)
            title_match_chance = 0.4
        elif any(x in event_name_lower for x in ['raw', 'smackdown', 'nitro', 'dynamite', 'nxt', 'impact']):
            num_matches = random.randint(4, 7)
            title_match_chance = 0.15
        else:
            num_matches = random.randint(5, 8)
            title_match_chance = 0.25

        # Match types
        match_types = [
            'Singles Match', 'Singles Match', 'Singles Match', 'Singles Match',
            'Tag Team Match', 'Tag Team Match',
            'Triple Threat Match', 'Fatal Four-Way',
            'No Disqualification Match', 'Steel Cage Match',
            'Ladder Match', 'Tables Match', 'Last Man Standing',
            'Handicap Match', 'Battle Royal', '6-Man Tag Team Match'
        ]

        created = 0
        used_wrestlers = set()

        for match_order in range(1, num_matches + 1):
            # Get available wrestlers not yet used
            available = [w for w in roster if w.id not in used_wrestlers]
            if len(available) < 2:
                available = roster  # Reset if we run out

            # Choose match type
            if match_order == num_matches:
                # Main event is usually singles or title match
                match_type = random.choice(['Singles Match', 'Singles Match', 'Singles Match', 'Triple Threat Match'])
            else:
                match_type = random.choice(match_types)

            # Determine participants
            if 'Tag Team' in match_type:
                if '6-Man' in match_type:
                    num_wrestlers = 6
                else:
                    num_wrestlers = 4
            elif 'Triple Threat' in match_type:
                num_wrestlers = 3
            elif 'Four-Way' in match_type or 'Fatal' in match_type:
                num_wrestlers = 4
            elif 'Battle Royal' in match_type:
                num_wrestlers = min(10, len(available))
            elif 'Handicap' in match_type:
                num_wrestlers = 3
            else:
                num_wrestlers = 2

            if len(available) < num_wrestlers:
                continue

            participants = random.sample(available, min(num_wrestlers, len(available)))
            for p in participants:
                used_wrestlers.add(p.id)

            # Determine winner
            winner = random.choice(participants)

            # Build match text
            if len(participants) == 2:
                match_text = f"{participants[0].name} vs. {participants[1].name}"
            elif 'Tag Team' in match_type and len(participants) >= 4:
                team1 = f"{participants[0].name} & {participants[1].name}"
                team2 = f"{participants[2].name} & {participants[3].name}"
                if len(participants) == 6:
                    team1 = f"{participants[0].name}, {participants[1].name} & {participants[2].name}"
                    team2 = f"{participants[3].name}, {participants[4].name} & {participants[5].name}"
                match_text = f"{team1} vs. {team2}"
            else:
                match_text = " vs. ".join([p.name for p in participants])

            # Determine if title match
            title = None
            if titles and random.random() < title_match_chance:
                title = random.choice(titles)
                match_text = f"{title.name}: {match_text}"

            # Determine result
            if 'Battle Royal' in match_type:
                result = f"{winner.name} wins by last eliminating"
            elif 'Cage' in match_type:
                result = random.choice([f"{winner.name} wins by escaping the cage", f"{winner.name} wins by pinfall"])
            elif 'Ladder' in match_type:
                result = f"{winner.name} wins by retrieving the prize"
            elif 'Tables' in match_type:
                result = f"{winner.name} wins by putting opponent through a table"
            elif 'Last Man Standing' in match_type:
                result = f"{winner.name} wins by knockout"
            else:
                result = random.choice([
                    f"{winner.name} wins by pinfall",
                    f"{winner.name} wins by pinfall",
                    f"{winner.name} wins by pinfall",
                    f"{winner.name} wins by submission",
                    f"{winner.name} wins by disqualification",
                    f"{winner.name} wins by count-out",
                ])

            # Create match
            match = Match.objects.create(
                event=event,
                match_text=match_text,
                result=result,
                winner=winner,
                match_type=match_type,
                title=title,
                match_order=match_order
            )

            # Link wrestlers
            match.wrestlers.set(participants)
            created += 1

        return created
