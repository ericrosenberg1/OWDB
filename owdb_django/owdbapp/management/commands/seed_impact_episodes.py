"""
Seed historic TNA/Impact Wrestling TV episodes with matches and significant moments.

Usage:
    python manage.py seed_impact_episodes
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic TNA/Impact Wrestling TV episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding TNA/Impact Wrestling Episodes ===\n'))

        tna = Promotion.objects.filter(abbreviation='TNA').first()
        if not tna:
            tna = Promotion.objects.create(
                name='Total Nonstop Action Wrestling',
                abbreviation='TNA',
                founded_year=2002
            )
            self.stdout.write('  + Created TNA promotion')

        self.seed_tna_2002_2004(tna)
        self.seed_tna_2005_2007(tna)
        self.seed_tna_2008_2010(tna)
        self.seed_impact_2011_2015(tna)
        self.seed_impact_2016_2020(tna)
        self.seed_impact_2021_present(tna)

        self.stdout.write(self.style.SUCCESS('\n=== Impact Seeding Complete ==='))
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

        wrestler_names = match_data.get('wrestlers', [])
        match_text = ' vs '.join(wrestler_names) if wrestler_names else 'Match'

        match = Match.objects.create(
            event=event,
            match_text=match_text,
            match_type=match_data.get('match_type', 'Singles'),
            winner=winner,
            title=title,
            match_order=order,
            about=match_data.get('about', '')
        )
        match.wrestlers.set(wrestlers)
        return match

    def seed_tna_2002_2004(self, tna):
        """Seed TNA Weekly PPV episodes from 2002-2004."""
        self.stdout.write('\n--- 2002-2004: The Weekly PPV Era ---\n')

        # First TNA Show Ever - June 19, 2002
        self.create_episode_with_matches(tna, {
            'name': 'TNA Weekly PPV',
            'date': date(2002, 6, 19),
            'venue': 'Von Braun Center',
            'location': 'Huntsville, AL',
            'about': 'The very first TNA show ever. The promotion that would challenge WWE was born.'
        }, [
            {'wrestlers': ['AJ Styles', 'Low Ki', 'Jerry Lynn', 'Psicosis', 'Ace Steel', 'Flying Elvis'],
             'winner': 'AJ Styles', 'match_type': 'X Division Gauntlet',
             'title': 'TNA X Division Championship', 'title_changed': True,
             'about': 'AJ Styles won the first X Division Championship in TNA history.'},
            {'wrestlers': ['Ken Shamrock', 'Malice'], 'winner': 'Ken Shamrock',
             'match_type': 'Singles', 'title': 'NWA World Heavyweight Championship',
             'about': 'Ken Shamrock won the NWA World Heavyweight Championship.'},
            {'wrestlers': ['Jeff Jarrett', 'Scott Hall', 'Brian Christopher', 'K-Krush'],
             'winner': 'Jeff Jarrett', 'match_type': 'Gauntlet for the Gold',
             'about': 'The main event of the first TNA show.'},
        ])

        # AJ Styles Rise
        self.create_episode_with_matches(tna, {
            'name': 'TNA Weekly PPV',
            'date': date(2002, 8, 7),
            'venue': 'Tennessee State Fairgrounds',
            'location': 'Nashville, TN',
            'about': 'AJ Styles continued his rise as the face of TNA.'
        }, [
            {'wrestlers': ['AJ Styles', 'Jerry Lynn'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'title': 'TNA X Division Championship',
             'about': 'AJ defended the X Division title.'},
            {'wrestlers': ['Jeff Jarrett', 'Ron Killings'], 'winner': 'Jeff Jarrett',
             'match_type': 'Singles', 'title': 'NWA World Heavyweight Championship',
             'about': 'Jarrett defended the NWA title.'},
        ])

        # Raven Arrives
        self.create_episode_with_matches(tna, {
            'name': 'TNA Weekly PPV',
            'date': date(2003, 6, 11),
            'venue': 'Tennessee State Fairgrounds',
            'location': 'Nashville, TN',
            'about': 'Raven arrived in TNA.'
        }, [
            {'wrestlers': ['Raven', 'Jeff Jarrett'], 'winner': 'Raven',
             'match_type': 'Singles', 'title': 'NWA World Heavyweight Championship', 'title_changed': True,
             'about': 'Raven won the NWA World Heavyweight Championship!'},
            {'wrestlers': ['AJ Styles', 'D-Lo Brown'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'AJ continued his excellence.'},
        ])

    def seed_tna_2005_2007(self, tna):
        """Seed TNA Impact episodes from 2005-2007."""
        self.stdout.write('\n--- 2005-2007: The Spike TV Era Begins ---\n')

        # First Impact on Spike TV - October 1, 2005
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2005, 10, 1),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'TNA Impact debuts on Spike TV. A new era begins.'
        }, [
            {'wrestlers': ['AJ Styles', 'Samoa Joe', 'Christopher Daniels'], 'winner': 'AJ Styles',
             'match_type': 'Triple Threat', 'title': 'TNA X Division Championship',
             'about': 'The legendary trio battled on national TV.'},
            {'wrestlers': ['Jeff Jarrett', 'Rhino'], 'winner': 'Jeff Jarrett',
             'match_type': 'Singles', 'title': 'NWA World Heavyweight Championship',
             'about': 'Main event of the Spike TV debut.'},
        ])

        # Samoa Joe Undefeated Streak
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2006, 3, 2),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Samoa Joe continued his legendary undefeated streak.'
        }, [
            {'wrestlers': ['Samoa Joe', 'Sonjay Dutt'], 'winner': 'Samoa Joe',
             'match_type': 'Singles', 'about': 'Joe\'s undefeated streak continued.'},
            {'wrestlers': ['Christian Cage', 'Monty Brown'], 'winner': 'Christian Cage',
             'match_type': 'Singles', 'title': 'NWA World Heavyweight Championship',
             'about': 'Christian Cage as NWA Champion.'},
        ])

        # Kurt Angle Debut
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2006, 10, 19),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Kurt Angle made his TNA debut.'
        }, [
            {'wrestlers': ['Kurt Angle', 'Samoa Joe'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'Kurt Angle arrived and brawled with Samoa Joe.'},
            {'wrestlers': ['AJ Styles', 'Christopher Daniels'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'Two of TNA\'s best squared off.'},
        ])

        # Sting in TNA
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2006, 5, 18),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Sting continued his TNA run as a top star.'
        }, [
            {'wrestlers': ['Sting', 'Jeff Jarrett'], 'winner': 'Sting',
             'match_type': 'Singles', 'about': 'The Icon faced Double J.'},
            {'wrestlers': ['AJ Styles', 'Petey Williams'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'title': 'TNA X Division Championship',
             'about': 'X Division excellence.'},
        ])

    def seed_tna_2008_2010(self, tna):
        """Seed TNA Impact episodes from 2008-2010."""
        self.stdout.write('\n--- 2008-2010: The Main Event Mafia Era ---\n')

        # Main Event Mafia Forms
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2008, 10, 23),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'The Main Event Mafia was formed with Sting, Kurt Angle, Booker T, Kevin Nash, and Scott Steiner.'
        }, [
            {'wrestlers': ['Main Event Mafia', 'TNA Frontline'], 'winner': 'Main Event Mafia',
             'match_type': 'Brawl', 'about': 'The legendary stable was born.'},
            {'wrestlers': ['AJ Styles', 'Booker T'], 'winner': 'Booker T',
             'match_type': 'Singles', 'about': 'MEM dominated the homegrown TNA talent.'},
        ])

        # Hulk Hogan Arrives - January 4, 2010
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2010, 1, 4),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Hulk Hogan debuted in TNA on the same night as Raw. The Monday Night War revival.'
        }, [
            {'wrestlers': ['Hulk Hogan', 'Various'], 'winner': 'Hulk Hogan',
             'match_type': 'Debut', 'about': 'Hulkamania arrived in TNA!'},
            {'wrestlers': ['AJ Styles', 'Kurt Angle'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'title': 'TNA World Heavyweight Championship',
             'about': 'AJ Styles as TNA World Champion.'},
            {'wrestlers': ['Jeff Hardy', 'Various'], 'winner': 'Jeff Hardy',
             'match_type': 'Debut', 'about': 'Jeff Hardy appeared on the historic show.'},
        ])

        # Ric Flair Arrives
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2010, 1, 18),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Ric Flair arrived in TNA and aligned with AJ Styles.'
        }, [
            {'wrestlers': ['AJ Styles', 'Ric Flair'], 'winner': 'AJ Styles',
             'match_type': 'Alliance', 'about': 'Flair became AJ\'s manager and mentor.'},
            {'wrestlers': ['Beer Money', 'Motor City Machine Guns'], 'winner': 'Beer Money',
             'match_type': 'Tag Team', 'about': 'Classic TNA tag team rivalry.'},
        ])

        # They/Immortal Saga
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2010, 10, 14),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Bound for Glory fallout. Jeff Hardy turned heel and Immortal was born.'
        }, [
            {'wrestlers': ['Jeff Hardy', 'Mr. Anderson'], 'winner': 'Jeff Hardy',
             'match_type': 'Singles', 'title': 'TNA World Heavyweight Championship',
             'about': 'Heel Jeff Hardy as TNA Champion.'},
            {'wrestlers': ['Hulk Hogan', 'Eric Bischoff'], 'winner': 'Immortal',
             'match_type': 'Segment', 'about': 'Immortal took control of TNA.'},
        ])

    def seed_impact_2011_2015(self, tna):
        """Seed TNA Impact episodes from 2011-2015."""
        self.stdout.write('\n--- 2011-2015: The Aces and Eights Era ---\n')

        # Sting World Champion
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2011, 3, 3),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'Sting won the TNA World Heavyweight Championship from Jeff Hardy.'
        }, [
            {'wrestlers': ['Sting', 'Jeff Hardy'], 'winner': 'Sting',
             'match_type': 'Singles', 'title': 'TNA World Heavyweight Championship', 'title_changed': True,
             'about': 'The Icon captured the World Title!'},
            {'wrestlers': ['AJ Styles', 'Rob Van Dam'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'Two incredible athletes.'},
        ])

        # Aces and Eights Debut
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2012, 6, 14),
            'venue': 'Impact Zone',
            'location': 'Orlando, FL',
            'about': 'The mysterious Aces and Eights motorcycle gang invaded TNA.'
        }, [
            {'wrestlers': ['Aces and Eights', 'Various'], 'winner': 'Aces and Eights',
             'match_type': 'Attack', 'about': 'The biker gang attacked TNA roster members.'},
            {'wrestlers': ['Bobby Roode', 'Austin Aries'], 'winner': 'Austin Aries',
             'match_type': 'Singles', 'title': 'TNA World Heavyweight Championship',
             'about': 'The greatest man that ever lived.'},
        ])

        # Bully Ray Revealed as Aces and Eights President
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2013, 3, 14),
            'venue': 'Sears Centre',
            'location': 'Hoffman Estates, IL',
            'about': 'Bully Ray was revealed as the president of Aces and Eights at Lockdown.'
        }, [
            {'wrestlers': ['Bully Ray', 'Jeff Hardy'], 'winner': 'Bully Ray',
             'match_type': 'Singles', 'title': 'TNA World Heavyweight Championship',
             'about': 'Bully Ray as World Champion and Aces and Eights leader.'},
            {'wrestlers': ['Sting', 'Kurt Angle'], 'winner': 'Sting',
             'match_type': 'Tag Team', 'about': 'Legends fought against the gang.'},
        ])

        # TNA Leaves Impact Zone
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2013, 5, 9),
            'venue': 'Von Braun Center',
            'location': 'Huntsville, AL',
            'about': 'TNA went back on the road after years in the Impact Zone.'
        }, [
            {'wrestlers': ['AJ Styles', 'Various'], 'winner': 'AJ Styles',
             'match_type': 'Singles', 'about': 'AJ Styles on the road.'},
            {'wrestlers': ['Magnus', 'Samoa Joe'], 'winner': 'Magnus',
             'match_type': 'Singles', 'about': 'British stars rising.'},
        ])

    def seed_impact_2016_2020(self, tna):
        """Seed Impact Wrestling episodes from 2016-2020."""
        self.stdout.write('\n--- 2016-2020: The Rebranding Era ---\n')

        # Broken Matt Hardy
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2016, 3, 15),
            'venue': 'Universal Studios',
            'location': 'Orlando, FL',
            'about': 'The Broken Matt Hardy character was developing.'
        }, [
            {'wrestlers': ['Matt Hardy', 'Jeff Hardy'], 'winner': 'Matt Hardy',
             'match_type': 'Singles', 'about': 'The transformation to Broken Matt began.'},
            {'wrestlers': ['Lashley', 'Drew Galloway'], 'winner': 'Lashley',
             'match_type': 'Singles', 'about': 'Two future WWE main eventers.'},
        ])

        # Final Deletion
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2016, 7, 5),
            'venue': 'Hardy Compound',
            'location': 'Cameron, NC',
            'about': 'The Final Deletion - the most creative match in TNA history aired.'
        }, [
            {'wrestlers': ['Broken Matt Hardy', 'Jeff Hardy'], 'winner': 'Broken Matt Hardy',
             'match_type': 'Final Deletion', 'about': 'DELETE! DELETE! DELETE! The match that changed wrestling.'},
        ])

        # Impact Wrestling Rebranding
        self.create_episode_with_matches(tna, {
            'name': 'Impact Wrestling',
            'date': date(2017, 3, 2),
            'venue': 'Universal Studios',
            'location': 'Orlando, FL',
            'about': 'TNA officially rebranded to Impact Wrestling.'
        }, [
            {'wrestlers': ['Alberto El Patron', 'Bobby Lashley'], 'winner': 'Alberto El Patron',
             'match_type': 'Singles', 'title': 'Impact World Championship',
             'about': 'New era, new branding.'},
            {'wrestlers': ['LAX', 'Decay'], 'winner': 'LAX',
             'match_type': 'Tag Team', 'about': 'Tag team action.'},
        ])

        # Tessa Blanchard World Champion
        self.create_episode_with_matches(tna, {
            'name': 'Impact Wrestling',
            'date': date(2020, 1, 16),
            'venue': 'Fronton Mexico',
            'location': 'Mexico City, Mexico',
            'about': 'Tessa Blanchard became the first woman to win a major men\'s world championship.'
        }, [
            {'wrestlers': ['Tessa Blanchard', 'Sami Callihan'], 'winner': 'Tessa Blanchard',
             'match_type': 'Singles', 'title': 'Impact World Championship', 'title_changed': True,
             'about': 'Historic moment as Tessa became Impact World Champion.'},
        ])

    def seed_impact_2021_present(self, tna):
        """Seed Impact Wrestling episodes from 2021-present."""
        self.stdout.write('\n--- 2021-Present: The Modern Era ---\n')

        # Kenny Omega as Impact Champion
        self.create_episode_with_matches(tna, {
            'name': 'Impact Wrestling',
            'date': date(2021, 4, 8),
            'venue': 'Skyway Studios',
            'location': 'Nashville, TN',
            'about': 'Kenny Omega as Impact World Champion - the Forbidden Door era.'
        }, [
            {'wrestlers': ['Kenny Omega', 'Rich Swann'], 'winner': 'Kenny Omega',
             'match_type': 'Singles', 'title': 'Impact World Championship',
             'about': 'AEW Champion was also Impact Champion.'},
            {'wrestlers': ['The Good Brothers', 'FinJuice'], 'winner': 'The Good Brothers',
             'match_type': 'Tag Team', 'about': 'Tag team main event.'},
        ])

        # Josh Alexander Era
        self.create_episode_with_matches(tna, {
            'name': 'Impact Wrestling',
            'date': date(2022, 4, 28),
            'venue': 'Sam\'s Town Live',
            'location': 'Las Vegas, NV',
            'about': 'Josh Alexander established himself as the ace of Impact.'
        }, [
            {'wrestlers': ['Josh Alexander', 'Moose'], 'winner': 'Josh Alexander',
             'match_type': 'Singles', 'title': 'Impact World Championship',
             'about': 'The Walking Weapon defended his title.'},
            {'wrestlers': ['Jordynne Grace', 'Tasha Steelz'], 'winner': 'Jordynne Grace',
             'match_type': 'Singles', 'title': 'Impact Knockouts Championship',
             'about': 'Thicc Mama Pump in action.'},
        ])

        # TNA Returns - The Rebranding
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2024, 1, 4),
            'venue': 'TNA Studios',
            'location': 'Atlanta, GA',
            'about': 'Impact Wrestling rebranded back to TNA Wrestling.'
        }, [
            {'wrestlers': ['Nic Nemeth', 'Moose'], 'winner': 'Nic Nemeth',
             'match_type': 'Singles', 'about': 'Former WWE star as a TNA main eventer.'},
            {'wrestlers': ['Joe Hendry', 'Various'], 'winner': 'Joe Hendry',
             'match_type': 'Singles', 'about': 'Joe Hendry\'s rise to fame. We believe!'},
        ])

        # Joe Hendry Becomes Star
        self.create_episode_with_matches(tna, {
            'name': 'TNA iMPACT!',
            'date': date(2024, 8, 8),
            'venue': 'Cicero Stadium',
            'location': 'Chicago, IL',
            'about': 'Joe Hendry continued his meteoric rise.'
        }, [
            {'wrestlers': ['Joe Hendry', 'Frankie Kazarian'], 'winner': 'Joe Hendry',
             'match_type': 'Singles', 'about': 'I SAY JOE, YOU SAY HENDRY! Joe! Hendry!'},
            {'wrestlers': ['Jordynne Grace', 'Masha Slamovich'], 'winner': 'Jordynne Grace',
             'match_type': 'Singles', 'title': 'TNA Knockouts World Championship',
             'about': 'The workhorse of the Knockouts division.'},
        ])
