"""
Seed historic WWE Raw episodes with matches and significant moments.

Usage:
    python manage.py seed_raw_episodes
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue
)


class Command(BaseCommand):
    help = 'Seed historic WWE Raw episodes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding WWE Raw Episodes ===\n'))

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        if not wwe:
            wwe = Promotion.objects.filter(abbreviation='WWF').first()

        self.seed_raw_1993(wwe)
        self.seed_raw_1997(wwe)
        self.seed_raw_1998(wwe)
        self.seed_raw_1999(wwe)
        self.seed_raw_2000s(wwe)
        self.seed_raw_2010s(wwe)
        self.seed_raw_2020s(wwe)

        self.stdout.write(self.style.SUCCESS('\n=== Raw Seeding Complete ==='))
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
            event_type='TV',
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

    def seed_raw_1993(self, wwe):
        """Seed the first Raw episodes from 1993."""
        self.stdout.write('\n--- 1993: The Beginning ---\n')

        # First Raw Ever - January 11, 1993
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1993, 1, 11),
            'venue': 'Manhattan Center',
            'location': 'New York City, NY',
            'about': 'The very first episode of Monday Night Raw. A historic night that changed wrestling television forever.'
        }, [
            {'wrestlers': ['Koko B. Ware', 'Yokozuna'], 'winner': 'Yokozuna',
             'match_type': 'Singles', 'about': 'First match in Raw history. Yokozuna squashed Koko B. Ware.'},
            {'wrestlers': ['The Steiner Brothers', 'The Executioners'], 'winner': 'The Steiner Brothers',
             'match_type': 'Tag Team', 'about': 'Rick and Scott Steiner dominated in their Raw debut.'},
            {'wrestlers': ['Max Moon', 'Shawn Michaels'], 'winner': 'Shawn Michaels',
             'match_type': 'Singles', 'about': 'The Heartbreak Kid picked up a victory.'},
            {'wrestlers': ['The Undertaker', 'Damien Demento'], 'winner': 'The Undertaker',
             'match_type': 'Singles', 'about': 'Main event of the first Raw. Undertaker dominated.'},
        ])

        # Raw January 18, 1993
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1993, 1, 18),
            'venue': 'Manhattan Center',
            'location': 'New York City, NY',
            'about': 'Second episode of Raw featuring Mr. Perfect vs Ric Flair.'
        }, [
            {'wrestlers': ['Mr. Perfect', 'Ric Flair'], 'winner': 'Mr. Perfect',
             'match_type': 'Loser Leaves WWF', 'about': 'Classic match. Ric Flair lost and left WWF.'},
            {'wrestlers': ['Marty Jannetty', 'Glen Ruth'], 'winner': 'Marty Jannetty',
             'match_type': 'Singles', 'about': 'Jannetty in singles action.'},
        ])

        # Raw January 25, 1993
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1993, 1, 25),
            'venue': 'Manhattan Center',
            'location': 'New York City, NY',
            'about': 'Royal Rumble fallout episode.'
        }, [
            {'wrestlers': ['Bret Hart', 'Razor Ramon'], 'winner': 'Bret Hart',
             'match_type': 'Singles', 'about': 'WWF Champion Bret Hart defeated Razor Ramon.'},
            {'wrestlers': ['Tatanka', 'Damien Demento'], 'winner': 'Tatanka',
             'match_type': 'Singles', 'about': 'Tatanka continued his undefeated streak.'},
        ])

    def seed_raw_1997(self, wwe):
        """Seed key Raw episodes from 1997 - Start of Attitude Era."""
        self.stdout.write('\n--- 1997: Attitude Era Begins ---\n')

        # Austin 3:16 Aftermath - Post King of the Ring
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1997, 3, 17),
            'venue': 'Manhattan Center',
            'location': 'New York City, NY',
            'about': 'Building to WrestleMania 13 with Austin vs Bret Hart.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Savio Vega'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'Austin dominated heading into WrestleMania.'},
            {'wrestlers': ['The Undertaker', 'Mankind'], 'winner': 'The Undertaker',
             'match_type': 'Singles', 'about': 'Continuation of their legendary rivalry.'},
        ])

        # Montreal Screwjob Aftermath - Raw after Survivor Series
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1997, 11, 10),
            'venue': 'Municipal Auditorium',
            'location': 'Springfield, MO',
            'about': 'The Raw after the Montreal Screwjob. Vince McMahon appeared with a black eye from Bret Hart.'
        }, [
            {'wrestlers': ['Shawn Michaels', 'Mankind'], 'winner': 'Shawn Michaels',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'First title defense after Montreal.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'Rocky Maivia'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'Austin faced the future Rock.'},
        ])

        # DX Formation
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1997, 12, 15),
            'venue': 'Richmond Coliseum',
            'location': 'Richmond, VA',
            'about': 'D-Generation X continued to shock the wrestling world with their antics.'
        }, [
            {'wrestlers': ['Shawn Michaels', 'Undertaker'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'DX interference led to chaos.'},
            {'wrestlers': ['Triple H', 'Owen Hart'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'Triple H picking up momentum.'},
        ])

    def seed_raw_1998(self, wwe):
        """Seed key Raw episodes from 1998 - Peak Attitude Era."""
        self.stdout.write('\n--- 1998: Peak Attitude Era ---\n')

        # Raw after WrestleMania 14
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1998, 3, 30),
            'venue': 'Albany Civic Center',
            'location': 'Albany, NY',
            'about': 'The Raw after WrestleMania 14. The Austin Era begins in full force.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'The Rock'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'New WWF Champion Austin faced The Rock.'},
            {'wrestlers': ['Triple H', 'Owen Hart'], 'winner': 'Triple H',
             'match_type': 'Singles', 'title': 'WWF European Championship',
             'about': 'European Championship match.'},
        ])

        # Mike Tyson Involvement
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1998, 1, 19),
            'venue': 'Fresno Convention Center',
            'location': 'Fresno, CA',
            'about': 'Mike Tyson made his first WWF appearance, leading to his WrestleMania involvement.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Shawn Michaels'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'Austin and Michaels brawled with Tyson involvement.'},
            {'wrestlers': ['The Rock', 'Chainz'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'The Rock continued his rise.'},
        ])

        # Austin Stuns McMahon
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1998, 4, 13),
            'venue': 'Norfolk Scope',
            'location': 'Norfolk, VA',
            'about': 'Stone Cold Steve Austin stunned Vince McMahon in an iconic moment.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Dude Love'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'title': 'WWF Championship',
             'about': 'Austin defended against his friend Mick Foley.'},
            {'wrestlers': ['Triple H', 'X-Pac'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'DX internal strife.'},
        ])

        # The Rock joins The Corporation
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1998, 11, 16),
            'venue': 'St. Louis Arena',
            'location': 'St. Louis, MO',
            'about': 'The Rock revealed as the Corporate Champion after the Deadly Game tournament.'
        }, [
            {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Corporate Rock vs Mankind.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'The Big Boss Man'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'Austin battled The Corporation.'},
        ])

        # Christmas Raw 1998
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1998, 12, 28),
            'venue': 'Reunion Arena',
            'location': 'Dallas, TX',
            'about': 'Mankind won the WWF Championship in a historic moment.'
        }, [
            {'wrestlers': ['Mankind', 'The Rock'], 'winner': 'Mankind',
             'match_type': 'Singles', 'title': 'WWF Championship', 'title_changed': True,
             'about': 'MANKIND WON THE TITLE! That\'ll put butts in seats! Historic moment with Tony Schiavone spoiling it on Nitro.'},
            {'wrestlers': ['D-Lo Brown', 'Mark Henry'], 'winner': 'D-Lo Brown',
             'match_type': 'Singles', 'about': 'D-Lo Brown in action.'},
        ])

    def seed_raw_1999(self, wwe):
        """Seed key Raw episodes from 1999."""
        self.stdout.write('\n--- 1999: Monday Night Wars Peak ---\n')

        # Raw after Royal Rumble
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1999, 1, 25),
            'venue': 'America West Arena',
            'location': 'Phoenix, AZ',
            'about': 'Post-Royal Rumble fallout with WrestleMania season beginning.'
        }, [
            {'wrestlers': ['The Rock', 'Mankind'], 'winner': 'The Rock',
             'match_type': 'I Quit', 'title': 'WWF Championship', 'title_changed': True,
             'about': 'Brutal I Quit match with controversial ending using recording.'},
            {'wrestlers': ['Triple H', 'X-Pac'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'DX tensions continued.'},
        ])

        # Higher Power Revealed
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1999, 6, 7),
            'venue': 'Moline Arena',
            'location': 'Moline, IL',
            'about': 'The Corporate Ministry\'s Higher Power was revealed to be Vince McMahon. IT WAS ME AUSTIN!'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'The Undertaker'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'Higher Power revelation interrupted the match.'},
            {'wrestlers': ['The Rock', 'Triple H'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Two future icons collided.'},
        ])

        # Raw Is War 1000th Episode Celebration
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(1999, 8, 23),
            'venue': 'Kemper Arena',
            'location': 'Kansas City, MO',
            'about': 'Jesse Ventura made a surprise return as guest referee.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'Triple H', 'Mankind'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Triple Threat', 'title': 'WWF Championship',
             'about': 'Triple threat for the title with Jesse Ventura as referee.'},
            {'wrestlers': ['The Rock', 'Big Show'], 'winner': 'The Rock',
             'match_type': 'Singles', 'about': 'Rock continued his dominance.'},
        ])

    def seed_raw_2000s(self, wwe):
        """Seed key Raw episodes from 2000-2009."""
        self.stdout.write('\n--- 2000s: Brand Split Era ---\n')

        # Raw after WrestleMania 17
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2001, 4, 2),
            'venue': 'Compaq Center',
            'location': 'Houston, TX',
            'about': 'Fallout from the greatest WrestleMania ever. Austin aligned with McMahon.'
        }, [
            {'wrestlers': ['Stone Cold Steve Austin', 'The Rock'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Singles', 'about': 'Continuation of their legendary rivalry.'},
            {'wrestlers': ['Triple H', 'Chris Jericho'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'Two of the best in the ring.'},
        ])

        # Brand Split Begins
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2002, 3, 25),
            'venue': 'Pepsi Arena',
            'location': 'Albany, NY',
            'about': 'The Brand Extension began as WWE split into Raw and SmackDown.'
        }, [
            {'wrestlers': ['Triple H', 'Booker T'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'First match of the brand split era.'},
            {'wrestlers': ['Rob Van Dam', 'Raven'], 'winner': 'Rob Van Dam',
             'match_type': 'Singles', 'title': 'Hardcore Championship',
             'about': 'RVD in hardcore action.'},
        ])

        # Evolution Debuts
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2003, 1, 20),
            'venue': 'Fleet Center',
            'location': 'Boston, MA',
            'about': 'Evolution made their presence known.'
        }, [
            {'wrestlers': ['Triple H', 'Scott Steiner'], 'winner': 'Triple H',
             'match_type': 'Singles', 'title': 'World Heavyweight Championship',
             'about': 'Triple H retained the World Heavyweight Championship.'},
            {'wrestlers': ['Batista', 'Tommy Dreamer'], 'winner': 'Batista',
             'match_type': 'Singles', 'about': 'Batista dominated.'},
            {'wrestlers': ['Randy Orton', 'Maven'], 'winner': 'Randy Orton',
             'match_type': 'Singles', 'about': 'The Legend Killer in action.'},
        ])

        # Batista Turns on Triple H
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2005, 2, 21),
            'venue': 'Wachovia Center',
            'location': 'Philadelphia, PA',
            'about': 'Batista gave Triple H the thumbs down, turning on Evolution.'
        }, [
            {'wrestlers': ['Triple H', 'Chris Benoit'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'Batista\'s shocking turn overshadowed the match.'},
            {'wrestlers': ['Randy Orton', 'Chris Jericho'], 'winner': 'Randy Orton',
             'match_type': 'Singles', 'about': 'Orton continued his rise.'},
        ])

        # John Cena Drafted to Raw
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2005, 6, 6),
            'venue': 'Staples Center',
            'location': 'Los Angeles, CA',
            'about': 'John Cena was drafted to Raw, bringing the WWE Championship.'
        }, [
            {'wrestlers': ['John Cena', 'Christian'], 'winner': 'John Cena',
             'match_type': 'Singles', 'about': 'Cena\'s first Raw match as champion.'},
            {'wrestlers': ['Edge', 'Kane'], 'winner': 'Edge',
             'match_type': 'Singles', 'about': 'Edge continued his rise as a main eventer.'},
        ])

        # Edge Cashes In MITB
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2006, 1, 9),
            'venue': 'Pepsi Arena',
            'location': 'Albany, NY',
            'about': 'Edge cashed in Money in the Bank on John Cena after an Elimination Chamber match.'
        }, [
            {'wrestlers': ['Edge', 'John Cena'], 'winner': 'Edge',
             'match_type': 'Singles', 'title': 'WWE Championship', 'title_changed': True,
             'about': 'First ever Money in the Bank cash-in on television. Edge won the WWE Championship.'},
            {'wrestlers': ['Shawn Michaels', 'Triple H'], 'winner': 'Shawn Michaels',
             'match_type': 'Singles', 'about': 'DX members collided.'},
        ])

        # Chris Jericho Returns
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2007, 11, 19),
            'venue': 'Scottrade Center',
            'location': 'St. Louis, MO',
            'about': 'Y2J returned to WWE with cryptic video codes.'
        }, [
            {'wrestlers': ['Randy Orton', 'Shawn Michaels'], 'winner': 'Randy Orton',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'Orton retained before Jericho\'s return.'},
            {'wrestlers': ['Triple H', 'Umaga'], 'winner': 'Triple H',
             'match_type': 'Singles', 'about': 'The Game in action.'},
        ])

    def seed_raw_2010s(self, wwe):
        """Seed key Raw episodes from 2010-2019."""
        self.stdout.write('\n--- 2010s: PG Era to Reality Era ---\n')

        # Nexus Debuts
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2010, 6, 7),
            'venue': 'American Airlines Arena',
            'location': 'Miami, FL',
            'about': 'The Nexus debuted by destroying everything in their path.'
        }, [
            {'wrestlers': ['John Cena', 'CM Punk'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'Match interrupted by Nexus invasion.'},
            {'wrestlers': ['Wade Barrett', 'Various'], 'winner': 'Wade Barrett',
             'match_type': 'Destruction', 'about': 'Nexus laid waste to the ring, commentary, and everyone.'},
        ])

        # CM Punk Pipe Bomb
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2011, 6, 27),
            'venue': 'Thomas & Mack Center',
            'location': 'Las Vegas, NV',
            'about': 'CM Punk delivered the legendary Pipe Bomb promo, changing wrestling.'
        }, [
            {'wrestlers': ['John Cena', 'R-Truth'], 'winner': 'John Cena',
             'match_type': 'Singles', 'about': 'Cena defended before Punk\'s historic promo.'},
            {'wrestlers': ['Rey Mysterio', 'Jack Swagger'], 'winner': 'Rey Mysterio',
             'match_type': 'Singles', 'about': 'Mysterio picked up a victory.'},
        ])

        # Raw 1000
        self.create_episode_with_matches(wwe, {
            'name': 'Raw 1000',
            'date': date(2012, 7, 23),
            'venue': 'Scottrade Center',
            'location': 'St. Louis, MO',
            'about': 'The 1000th episode of Raw with returns, title changes, and historic moments.'
        }, [
            {'wrestlers': ['CM Punk', 'John Cena'], 'winner': 'CM Punk',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'CM Punk turned heel by attacking The Rock. Big Show cost Cena.'},
            {'wrestlers': ['The Rock', 'Various'], 'winner': 'The Rock',
             'match_type': 'Segment', 'about': 'The Rock returned to celebrate Raw 1000.'},
            {'wrestlers': ['DX', 'Various'], 'winner': 'DX',
             'match_type': 'Reunion', 'about': 'D-Generation X reunited.'},
        ])

        # The Shield Debuts
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2012, 11, 18),
            'venue': 'Bankers Life Fieldhouse',
            'location': 'Indianapolis, IN',
            'about': 'The Shield debuted at Survivor Series and continued their attack.'
        }, [
            {'wrestlers': ['CM Punk', 'John Cena'], 'winner': 'CM Punk',
             'match_type': 'Singles', 'about': 'The Shield interfered on behalf of Punk.'},
            {'wrestlers': ['Dean Ambrose', 'Seth Rollins', 'Roman Reigns'], 'winner': 'The Shield',
             'match_type': 'Segment', 'about': 'The Shield made their presence known.'},
        ])

        # Daniel Bryan Yes Movement - Raw After WM30
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2014, 4, 7),
            'venue': 'Smoothie King Center',
            'location': 'New Orleans, LA',
            'about': 'The Raw after Daniel Bryan\'s WrestleMania moment. Yes! chants echoed.'
        }, [
            {'wrestlers': ['Daniel Bryan', 'Triple H'], 'winner': 'Daniel Bryan',
             'match_type': 'Segment', 'about': 'Bryan celebrated his WWE World Heavyweight Championship win.'},
            {'wrestlers': ['The Shield', 'Evolution'], 'winner': 'No Contest',
             'match_type': 'Brawl', 'about': 'The Shield and Evolution brawled.'},
        ])

        # Seth Rollins Cashes In at WrestleMania
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2015, 3, 30),
            'venue': 'SAP Center',
            'location': 'San Jose, CA',
            'about': 'Raw after WrestleMania 31 where Seth Rollins became champion.'
        }, [
            {'wrestlers': ['Seth Rollins', 'Randy Orton'], 'winner': 'Seth Rollins',
             'match_type': 'Singles', 'about': 'New champion Rollins faced a vengeful Orton.'},
            {'wrestlers': ['John Cena', 'Rusev'], 'winner': 'John Cena',
             'match_type': 'Singles', 'about': 'Cena continued his US title open challenge.'},
        ])

        # Women's Revolution
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2015, 7, 13),
            'venue': 'Mohegan Sun Arena',
            'location': 'Wilkes-Barre, PA',
            'about': 'Stephanie McMahon introduced Charlotte, Becky Lynch, and Sasha Banks, sparking the Women\'s Revolution.'
        }, [
            {'wrestlers': ['Charlotte', 'Brie Bella'], 'winner': 'Charlotte',
             'match_type': 'Singles', 'about': 'Charlotte made her main roster debut.'},
            {'wrestlers': ['Sasha Banks', 'Becky Lynch'], 'winner': 'Sasha Banks',
             'match_type': 'Singles', 'about': 'The Boss and The Lass Kicker arrived.'},
        ])

        # Kevin Owens Debut
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2015, 5, 18),
            'venue': 'Richmond Coliseum',
            'location': 'Richmond, VA',
            'about': 'Kevin Owens made his Raw debut by attacking John Cena.'
        }, [
            {'wrestlers': ['John Cena', 'Neville'], 'winner': 'John Cena',
             'match_type': 'Singles', 'title': 'WWE United States Championship',
             'about': 'Cena\'s open challenge answered by Neville.'},
            {'wrestlers': ['Kevin Owens', 'John Cena'], 'winner': 'Kevin Owens',
             'match_type': 'Attack', 'about': 'Owens laid out Cena after the match.'},
        ])

    def seed_raw_2020s(self, wwe):
        """Seed key Raw episodes from 2020-present."""
        self.stdout.write('\n--- 2020s: ThunderDome to Present ---\n')

        # Raw Goes ThunderDome
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2020, 8, 24),
            'venue': 'Amway Center',
            'location': 'Orlando, FL',
            'about': 'First Raw from the ThunderDome with virtual fans during pandemic.'
        }, [
            {'wrestlers': ['Drew McIntyre', 'Randy Orton'], 'winner': 'Drew McIntyre',
             'match_type': 'Singles', 'title': 'WWE Championship',
             'about': 'McIntyre defended the title in the ThunderDome era.'},
            {'wrestlers': ['Asuka', 'Sasha Banks'], 'winner': 'Asuka',
             'match_type': 'Singles', 'about': 'Two of the best women\'s wrestlers collided.'},
        ])

        # Edge Returns from Injury
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2020, 1, 27),
            'venue': 'Toyota Center',
            'location': 'Houston, TX',
            'about': 'Edge returned at Royal Rumble and appeared on Raw.'
        }, [
            {'wrestlers': ['Edge', 'Randy Orton'], 'winner': 'No Contest',
             'match_type': 'Confrontation', 'about': 'Edge and Orton faced off before their WrestleMania feud.'},
            {'wrestlers': ['Brock Lesnar', 'Ricochet'], 'winner': 'Brock Lesnar',
             'match_type': 'Singles', 'about': 'Lesnar dominated Ricochet.'},
        ])

        # Cody Rhodes Returns
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2022, 4, 4),
            'venue': 'American Airlines Center',
            'location': 'Dallas, TX',
            'about': 'The Raw after WrestleMania 38. Cody Rhodes returned to WWE.'
        }, [
            {'wrestlers': ['Cody Rhodes', 'The Miz'], 'winner': 'Cody Rhodes',
             'match_type': 'Singles', 'about': 'Cody\'s triumphant WWE return after WrestleMania debut.'},
            {'wrestlers': ['Seth Rollins', 'Kevin Owens'], 'winner': 'Seth Rollins',
             'match_type': 'Singles', 'about': 'Rollins dealt with his WrestleMania loss to Cody.'},
        ])

        # Raw 30th Anniversary
        self.create_episode_with_matches(wwe, {
            'name': 'Raw 30th Anniversary',
            'date': date(2023, 1, 23),
            'venue': 'Wells Fargo Center',
            'location': 'Philadelphia, PA',
            'about': 'Celebrating 30 years of Monday Night Raw with legends and surprises.'
        }, [
            {'wrestlers': ['The Rock', 'Various'], 'winner': 'The Rock',
             'match_type': 'Segment', 'about': 'The Rock returned for the 30th anniversary celebration.'},
            {'wrestlers': ['Hulk Hogan', 'Various'], 'winner': 'Hulk Hogan',
             'match_type': 'Segment', 'about': 'Hulk Hogan made an appearance.'},
            {'wrestlers': ['Stone Cold Steve Austin', 'Various'], 'winner': 'Stone Cold Steve Austin',
             'match_type': 'Segment', 'about': 'Austin stunned people in celebration.'},
        ])

        # WWE Netflix Era Begins
        self.create_episode_with_matches(wwe, {
            'name': 'Monday Night Raw',
            'date': date(2025, 1, 6),
            'venue': 'Intuit Dome',
            'location': 'Inglewood, CA',
            'about': 'Historic first Raw episode on Netflix. Beginning of a new era.'
        }, [
            {'wrestlers': ['Roman Reigns', 'Solo Sikoa'], 'winner': 'Roman Reigns',
             'match_type': 'Singles', 'about': 'Bloodline civil war continues in the Netflix era.'},
            {'wrestlers': ['CM Punk', 'Seth Rollins'], 'winner': 'No Contest',
             'match_type': 'Singles', 'about': 'Their rivalry exploded in the new era.'},
        ])
