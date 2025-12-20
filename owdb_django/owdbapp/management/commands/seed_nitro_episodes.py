"""
Seed historic WCW Monday Nitro episodes with matches and significant moments.

Usage:
    python manage.py seed_nitro_episodes
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic WCW Monday Nitro episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding WCW Monday Nitro Episodes ===\n'))

        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        if not wcw:
            wcw = Promotion.objects.create(
                name='World Championship Wrestling',
                abbreviation='WCW',
                founded_year=1988
            )
            self.stdout.write('  + Created WCW promotion')

        self.seed_nitro_1995(wcw)
        self.seed_nitro_1996(wcw)
        self.seed_nitro_1997(wcw)
        self.seed_nitro_1998(wcw)
        self.seed_nitro_1999(wcw)
        self.seed_nitro_2000(wcw)
        self.seed_nitro_2001(wcw)

        self.stdout.write(self.style.SUCCESS('\n=== Nitro Seeding Complete ==='))
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

    def seed_nitro_1995(self, wcw):
        """Seed the first Nitro episodes from 1995."""
        self.stdout.write('\n--- 1995: The Monday Night Wars Begin ---\n')

        # First Nitro Ever - September 4, 1995
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1995, 9, 4),
            'venue': 'Mall of America',
            'location': 'Minneapolis, MN',
            'about': 'The very first episode of Monday Nitro. The Monday Night Wars officially began. Lex Luger shocked the world by appearing.'
        }, [
            {'wrestlers': ['Jushin Thunder Liger', 'Brian Pillman'], 'winner': 'Brian Pillman',
             'match_type': 'Singles', 'about': 'First match in Nitro history.'},
            {'wrestlers': ['Sting', 'Ric Flair'], 'winner': 'Ric Flair',
             'match_type': 'Singles', 'about': 'Classic WCW main event rivalry.'},
            {'wrestlers': ['Hulk Hogan', 'Big Bubba Rogers'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship',
             'about': 'Hogan defended the title while Lex Luger made his shocking debut.'},
        ])

        # Nitro September 11, 1995
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1995, 9, 11),
            'venue': 'Augusta Civic Center',
            'location': 'Augusta, GA',
            'about': 'Second episode of Nitro as WCW built momentum.'
        }, [
            {'wrestlers': ['Sabu', 'Alex Wright'], 'winner': 'Sabu',
             'match_type': 'Singles', 'about': 'Sabu made his WCW debut.'},
            {'wrestlers': ['Lex Luger', 'Randy Savage'], 'winner': 'Lex Luger',
             'match_type': 'Singles', 'about': 'The Total Package faced Macho Man.'},
        ])

        # Nitro November 20, 1995
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1995, 11, 20),
            'venue': 'Florence Civic Center',
            'location': 'Florence, SC',
            'about': 'Nitro building toward World War 3.'
        }, [
            {'wrestlers': ['Ric Flair', 'Eddie Guerrero'], 'winner': 'Ric Flair',
             'match_type': 'Singles', 'about': 'The Nature Boy in action.'},
            {'wrestlers': ['Hulk Hogan', 'The Giant'], 'winner': 'Hulk Hogan',
             'match_type': 'Singles', 'about': 'Hogan vs The Giant continued their feud.'},
        ])

    def seed_nitro_1996(self, wcw):
        """Seed key Nitro episodes from 1996 - The nWo Year."""
        self.stdout.write('\n--- 1996: The nWo Takes Over ---\n')

        # Scott Hall Arrives - May 27, 1996
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1996, 5, 27),
            'venue': 'Macon Coliseum',
            'location': 'Macon, GA',
            'about': 'Scott Hall invaded Nitro through the crowd. "You want a war?"'
        }, [
            {'wrestlers': ['Scott Hall', 'Various'], 'winner': 'Scott Hall',
             'match_type': 'Invasion', 'about': 'The Outsider arrived, challenging WCW.'},
            {'wrestlers': ['Sting', 'Ric Flair'], 'winner': 'Sting',
             'match_type': 'Singles', 'about': 'WCW icons battled amidst the invasion.'},
        ])

        # Kevin Nash Arrives - June 10, 1996
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1996, 6, 10),
            'venue': 'Wheeling Civic Center',
            'location': 'Wheeling, WV',
            'about': 'Kevin Nash arrived to join Scott Hall. The Outsiders were formed.'
        }, [
            {'wrestlers': ['Scott Hall', 'Kevin Nash'], 'winner': 'The Outsiders',
             'match_type': 'Invasion', 'about': 'Big Daddy Cool arrived to join Razor.'},
            {'wrestlers': ['Ric Flair', 'Eddie Guerrero'], 'winner': 'Ric Flair',
             'match_type': 'Singles', 'about': 'WCW tried to maintain order.'},
        ])

        # Post Bash at the Beach - Hogan Turns - July 8, 1996
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1996, 7, 8),
            'venue': 'Disney-MGM Studios',
            'location': 'Orlando, FL',
            'about': 'The fallout from Bash at the Beach. Hulk Hogan turned heel and formed the New World Order.'
        }, [
            {'wrestlers': ['Hollywood Hulk Hogan', 'The Giant'], 'winner': 'Hollywood Hulk Hogan',
             'match_type': 'Segment', 'about': 'Hollywood Hogan and the nWo were born.'},
            {'wrestlers': ['Sting', 'Scott Hall'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'nWo chaos ensued.'},
        ])

        # Sting Goes Silent - October 14, 1996
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1996, 10, 14),
            'venue': 'UTC Arena',
            'location': 'Chattanooga, TN',
            'about': 'After being accused of joining the nWo, Sting went to the rafters in black and white.'
        }, [
            {'wrestlers': ['Sting', 'Various'], 'winner': 'Sting',
             'match_type': 'Segment', 'about': 'Sting descended from the rafters and began his silent vigil.'},
            {'wrestlers': ['Rey Mysterio Jr.', 'Dean Malenko'], 'winner': 'Rey Mysterio Jr.',
             'match_type': 'Singles', 'title': 'WCW Cruiserweight Championship',
             'about': 'Cruiserweight excellence while the nWo loomed.'},
        ])

    def seed_nitro_1997(self, wcw):
        """Seed key Nitro episodes from 1997 - nWo Dominance."""
        self.stdout.write('\n--- 1997: nWo Dominance ---\n')

        # Sting Returns to Challenge Hogan
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1997, 3, 17),
            'venue': 'Bayfront Arena',
            'location': 'Pensacola, FL',
            'about': 'Sting continued his vigilante crusade against the nWo.'
        }, [
            {'wrestlers': ['Sting', 'nWo'], 'winner': 'Sting',
             'match_type': 'Attack', 'about': 'The Crow Sting appeared to take out nWo members.'},
            {'wrestlers': ['Dean Malenko', 'Eddie Guerrero'], 'winner': 'Dean Malenko',
             'match_type': 'Singles', 'title': 'WCW Cruiserweight Championship',
             'about': 'Classic cruiserweight action.'},
        ])

        # Nitro at the Georgia Dome
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1997, 7, 7),
            'venue': 'Georgia Dome',
            'location': 'Atlanta, GA',
            'about': 'Nitro drew over 40,000 fans to the Georgia Dome.'
        }, [
            {'wrestlers': ['Lex Luger', 'Hollywood Hulk Hogan'], 'winner': 'Lex Luger',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship', 'title_changed': True,
             'about': 'Lex Luger shocked the world by defeating Hogan for the World Title!'},
            {'wrestlers': ['Ric Flair', 'Roddy Piper'], 'winner': 'Ric Flair',
             'match_type': 'Singles', 'about': 'Two legends battled.'},
            {'wrestlers': ['Chris Benoit', 'Kevin Sullivan'], 'winner': 'Chris Benoit',
             'match_type': 'Singles', 'about': 'Bitter rivalry continued.'},
        ])

        # Goldberg Debut Streak Begins
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1997, 9, 22),
            'venue': 'UTC Arena',
            'location': 'Chattanooga, TN',
            'about': 'Goldberg\'s early streak matches as he rose through WCW.'
        }, [
            {'wrestlers': ['Goldberg', 'Scotty Riggs'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg\'s streak continued to grow.'},
            {'wrestlers': ['Diamond Dallas Page', 'Curt Hennig'], 'winner': 'Diamond Dallas Page',
             'match_type': 'Singles', 'about': 'DDP continued his rise.'},
        ])

    def seed_nitro_1998(self, wcw):
        """Seed key Nitro episodes from 1998 - Goldberg and nWo Civil War."""
        self.stdout.write('\n--- 1998: Goldberg\'s Year ---\n')

        # Post Starrcade 97
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1998, 1, 5),
            'venue': 'Georgia Dome',
            'location': 'Atlanta, GA',
            'about': 'Fallout from the controversial Starrcade 97 Sting vs Hogan match.'
        }, [
            {'wrestlers': ['Sting', 'Hollywood Hulk Hogan'], 'winner': 'Sting',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship',
             'about': 'Sting finally got his clean victory over Hogan.'},
            {'wrestlers': ['Bret Hart', 'Ric Flair'], 'winner': 'Bret Hart',
             'match_type': 'Singles', 'about': 'The Hitman in WCW action.'},
        ])

        # Goldberg Beats Raven for US Title
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1998, 4, 20),
            'venue': 'Colorado Springs World Arena',
            'location': 'Colorado Springs, CO',
            'about': 'Goldberg won his first championship, the US Title from Raven.'
        }, [
            {'wrestlers': ['Goldberg', 'Raven'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'title': 'WCW United States Championship', 'title_changed': True,
             'about': 'Goldberg won the US Championship with a Jackhammer.'},
            {'wrestlers': ['Chris Jericho', 'Juventud Guerrera'], 'winner': 'Chris Jericho',
             'match_type': 'Singles', 'title': 'WCW Cruiserweight Championship',
             'about': 'Jericho continued his cruiserweight reign.'},
        ])

        # GOLDBERG WINS WORLD TITLE - July 6, 1998
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1998, 7, 6),
            'venue': 'Georgia Dome',
            'location': 'Atlanta, GA',
            'about': 'The biggest Nitro ever. Goldberg defeated Hollywood Hulk Hogan for the WCW World Heavyweight Championship in front of 41,412 fans!'
        }, [
            {'wrestlers': ['Goldberg', 'Hollywood Hulk Hogan'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship', 'title_changed': True,
             'about': 'WHO\'S NEXT? GOLDBERG defeated Hogan to become WCW World Heavyweight Champion. 173-0.'},
            {'wrestlers': ['Diamond Dallas Page', 'Curt Hennig'], 'winner': 'Diamond Dallas Page',
             'match_type': 'Singles', 'about': 'DDP in action on the historic night.'},
        ])

        # nWo Civil War
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1998, 5, 4),
            'venue': 'Convention Center',
            'location': 'Hartford, CT',
            'about': 'The nWo split into nWo Hollywood and nWo Wolfpac.'
        }, [
            {'wrestlers': ['Kevin Nash', 'Hollywood Hulk Hogan'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'The nWo civil war exploded.'},
            {'wrestlers': ['Sting', 'The Giant'], 'winner': 'Sting',
             'match_type': 'Singles', 'about': 'Sting was torn between the factions.'},
        ])

        # Wolfpac Forms
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1998, 5, 11),
            'venue': 'The Centrum',
            'location': 'Worcester, MA',
            'about': 'The nWo Wolfpac with Kevin Nash, Konnan, and Lex Luger formed.'
        }, [
            {'wrestlers': ['Kevin Nash', 'Lex Luger', 'Konnan'], 'winner': 'nWo Wolfpac',
             'match_type': 'Formation', 'about': 'The red and black Wolfpac was born.'},
            {'wrestlers': ['Goldberg', 'Saturn'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg\'s streak continued.'},
        ])

    def seed_nitro_1999(self, wcw):
        """Seed key Nitro episodes from 1999 - The Decline Begins."""
        self.stdout.write('\n--- 1999: Finger Poke of Doom ---\n')

        # FINGER POKE OF DOOM - January 4, 1999
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1999, 1, 4),
            'venue': 'Georgia Dome',
            'location': 'Atlanta, GA',
            'about': 'The infamous Finger Poke of Doom. Tony Schiavone told fans Mick Foley would win the WWF Championship. "That\'ll put butts in seats." Fans switched channels. Meanwhile, Hogan poked Nash and won the title.'
        }, [
            {'wrestlers': ['Hollywood Hulk Hogan', 'Kevin Nash'], 'winner': 'Hollywood Hulk Hogan',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship', 'title_changed': True,
             'about': 'The Finger Poke of Doom. Hogan poked Nash, Nash laid down, nWo reunited. The moment that signaled WCW\'s decline.'},
            {'wrestlers': ['Goldberg', 'Scott Hall'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg was tasered and his streak ended at Starrcade.'},
        ])

        # Ric Flair Returns
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(1999, 2, 22),
            'venue': 'Oakland Arena',
            'location': 'Oakland, CA',
            'about': 'Ric Flair returned as President of WCW.'
        }, [
            {'wrestlers': ['Ric Flair', 'Hollywood Hulk Hogan'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'Flair confronted Hogan over control of WCW.'},
            {'wrestlers': ['Goldberg', 'Bam Bam Bigelow'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg continued his path back to the title.'},
        ])

        # David Arquette Wins Title
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Thunder',
            'date': date(2000, 4, 26),
            'venue': 'Unnamed Arena',
            'location': 'Unknown',
            'about': 'Actor David Arquette won the WCW World Heavyweight Championship.'
        }, [
            {'wrestlers': ['David Arquette', 'Diamond Dallas Page', 'Jeff Jarrett'], 'winner': 'David Arquette',
             'match_type': 'Tag Team', 'title': 'WCW World Heavyweight Championship', 'title_changed': True,
             'about': 'In a moment that symbolized WCW\'s struggles, actor David Arquette won the World Title.'},
        ])

    def seed_nitro_2000(self, wcw):
        """Seed key Nitro episodes from 2000."""
        self.stdout.write('\n--- 2000: Vince Russo Era ---\n')

        # Vince Russo Arrives
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(2000, 4, 10),
            'venue': 'Kemper Arena',
            'location': 'Kansas City, MO',
            'about': 'Vince Russo and Eric Bischoff returned to reboot WCW.'
        }, [
            {'wrestlers': ['Various'], 'winner': 'Various',
             'match_type': 'Reboot', 'about': 'WCW was rebooted with new storylines and pushed younger talent.'},
            {'wrestlers': ['Booker T', 'Jeff Jarrett'], 'winner': 'Booker T',
             'match_type': 'Singles', 'about': 'Booker T\'s push to the main event began.'},
        ])

        # Booker T Wins World Title
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(2000, 7, 31),
            'venue': 'America West Arena',
            'location': 'Phoenix, AZ',
            'about': 'Booker T won the WCW World Heavyweight Championship.'
        }, [
            {'wrestlers': ['Booker T', 'Jeff Jarrett'], 'winner': 'Booker T',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship', 'title_changed': True,
             'about': 'Booker T became a 5-time WCW World Heavyweight Champion.'},
            {'wrestlers': ['Goldberg', 'Scott Steiner'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg battled Big Poppa Pump.'},
        ])

        # Scott Steiner Push
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(2000, 11, 13),
            'venue': 'Target Center',
            'location': 'Minneapolis, MN',
            'about': 'Scott Steiner emerged as WCW\'s top heel.'
        }, [
            {'wrestlers': ['Scott Steiner', 'Booker T'], 'winner': 'Scott Steiner',
             'match_type': 'Singles', 'about': 'Big Poppa Pump dominated.'},
            {'wrestlers': ['Goldberg', 'Lex Luger'], 'winner': 'Goldberg',
             'match_type': 'Singles', 'about': 'Goldberg in action.'},
        ])

    def seed_nitro_2001(self, wcw):
        """Seed the final Nitro episodes from 2001."""
        self.stdout.write('\n--- 2001: The End ---\n')

        # Final Nitro Ever - March 26, 2001
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(2001, 3, 26),
            'venue': 'Panama City Beach',
            'location': 'Panama City Beach, FL',
            'about': 'The final episode of WCW Monday Nitro. The end of an era. Vince McMahon appeared on both Raw and Nitro as he purchased WCW.'
        }, [
            {'wrestlers': ['Sting', 'Ric Flair'], 'winner': 'Sting',
             'match_type': 'Singles', 'about': 'The final match in WCW history. Two icons closed out the company.'},
            {'wrestlers': ['Booker T', 'Scott Steiner'], 'winner': 'Booker T',
             'match_type': 'Singles', 'title': 'WCW World Heavyweight Championship',
             'about': 'WCW World Heavyweight Championship match on the final night.'},
            {'wrestlers': ['Vince McMahon', 'Ted Turner'], 'winner': 'Vince McMahon',
             'match_type': 'Segment', 'about': 'Vince McMahon announced he had purchased WCW, ending the Monday Night Wars.'},
        ])

        # Second to Last Nitro
        self.create_episode_with_matches(wcw, {
            'name': 'WCW Monday Nitro',
            'date': date(2001, 3, 19),
            'venue': 'Jacksonville Coliseum',
            'location': 'Jacksonville, FL',
            'about': 'The penultimate Nitro as rumors of WCW\'s sale intensified.'
        }, [
            {'wrestlers': ['Scott Steiner', 'Diamond Dallas Page'], 'winner': 'Scott Steiner',
             'match_type': 'Singles', 'about': 'WCW continued despite uncertain future.'},
            {'wrestlers': ['Ric Flair', 'Dusty Rhodes'], 'winner': 'Ric Flair',
             'match_type': 'Singles', 'about': 'Old rivals battled as WCW neared the end.'},
        ])
