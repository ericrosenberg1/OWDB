"""
Seed Conrad Thompson's podcast network with episodes, guests, and event/match links.

Conrad Thompson hosts multiple wrestling podcasts with legendary wrestlers.
This seeder adds all podcasts, episodes, links guests, and connects discussed events/matches.

Usage:
    python manage.py seed_conrad_podcasts
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import datetime, timedelta, timezone
import random
from owdb_django.owdbapp.models import (
    Podcast, PodcastEpisode, Wrestler, Event, Match, Promotion
)


class Command(BaseCommand):
    help = 'Seed Conrad Thompson podcast network'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING CONRAD THOMPSON PODCASTS ===\n'))

        # Create/get Conrad Thompson's podcasts
        self.create_podcasts()

        # Add episodes with guests and event/match links
        self.add_episodes()

        # Print summary
        self.print_summary()

    def create_podcasts(self):
        """Create all Conrad Thompson podcasts."""
        self.stdout.write('--- Creating Podcasts ---')

        podcasts_data = [
            {
                'name': 'Something to Wrestle with Bruce Prichard',
                'hosts': 'Conrad Thompson, Bruce Prichard',
                'host_wrestler_names': ['Bruce Prichard'],
                'launch_year': 2016,
                'about': 'Bruce Prichard shares behind-the-scenes stories from his decades in WWE as Brother Love and a top producer/writer.',
                'rss_feed_url': 'https://feeds.megaphone.fm/STW',
            },
            {
                'name': '83 Weeks with Eric Bischoff',
                'hosts': 'Conrad Thompson, Eric Bischoff',
                'host_wrestler_names': ['Eric Bischoff'],
                'launch_year': 2018,
                'about': 'Eric Bischoff discusses his time running WCW during the Monday Night Wars and beyond.',
                'rss_feed_url': 'https://feeds.megaphone.fm/83W',
            },
            {
                'name': 'What Happened When with Tony Schiavone',
                'hosts': 'Conrad Thompson, Tony Schiavone',
                'host_wrestler_names': ['Tony Schiavone'],
                'launch_year': 2017,
                'about': 'Tony Schiavone relives his broadcasting career in WCW, WWE, and AEW.',
                'rss_feed_url': 'https://feeds.megaphone.fm/WHW',
            },
            {
                'name': 'Grilling JR',
                'hosts': 'Conrad Thompson, Jim Ross',
                'host_wrestler_names': ['Jim Ross'],
                'launch_year': 2018,
                'about': 'Jim Ross discusses his legendary career as WWE and AEW announcer and executive.',
                'rss_feed_url': 'https://feeds.megaphone.fm/GJR',
            },
            {
                'name': 'The Kurt Angle Show',
                'hosts': 'Conrad Thompson, Kurt Angle',
                'host_wrestler_names': ['Kurt Angle'],
                'launch_year': 2020,
                'about': 'Olympic gold medalist Kurt Angle shares stories from his WWE, TNA, and amateur wrestling career.',
                'rss_feed_url': 'https://feeds.megaphone.fm/KAS',
            },
            {
                'name': 'Arn',
                'hosts': 'Conrad Thompson, Arn Anderson',
                'host_wrestler_names': ['Arn Anderson'],
                'launch_year': 2019,
                'about': 'The Enforcer Arn Anderson discusses his legendary career as a Four Horseman and producer.',
                'rss_feed_url': 'https://feeds.megaphone.fm/ARN',
            },
            {
                'name': 'My World with Jeff Jarrett',
                'hosts': 'Conrad Thompson, Jeff Jarrett',
                'host_wrestler_names': ['Jeff Jarrett'],
                'launch_year': 2021,
                'about': 'Jeff Jarrett discusses his career in WWE, WCW, TNA, and as founder of multiple promotions.',
                'rss_feed_url': 'https://feeds.megaphone.fm/MWJ',
            },
            {
                'name': 'Foley is Pod',
                'hosts': 'Conrad Thompson, Mick Foley',
                'host_wrestler_names': ['Mick Foley'],
                'launch_year': 2022,
                'about': 'Mick Foley shares stories from his legendary hardcore career as Mankind, Cactus Jack, and Dude Love.',
                'rss_feed_url': 'https://feeds.megaphone.fm/FIP',
            },
            {
                'name': 'Strictly Business with Eric Bischoff',
                'hosts': 'Conrad Thompson, Eric Bischoff',
                'host_wrestler_names': ['Eric Bischoff'],
                'launch_year': 2023,
                'about': 'Eric Bischoff provides business analysis and commentary on current wrestling.',
                'rss_feed_url': 'https://feeds.megaphone.fm/SBE',
            },
            {
                'name': 'The Extreme Life of Matt Hardy',
                'hosts': 'Conrad Thompson, Matt Hardy',
                'host_wrestler_names': ['Matt Hardy'],
                'launch_year': 2022,
                'about': 'Matt Hardy discusses his career from the Hardy Boyz to Broken Matt Hardy and beyond.',
                'rss_feed_url': 'https://feeds.megaphone.fm/MH',
            },
            {
                'name': 'Deadlock',
                'hosts': 'Tony Khan, Conrad Thompson',
                'host_wrestler_names': [],
                'launch_year': 2020,
                'about': 'AEW owner Tony Khan and Conrad Thompson discuss wrestling.',
                'rss_feed_url': None,
            },
        ]

        self.podcasts = {}
        for data in podcasts_data:
            slug = slugify(data['name'])
            podcast, created = Podcast.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': data['name'],
                    'hosts': data['hosts'],
                    'launch_year': data['launch_year'],
                    'about': data['about'],
                    'rss_feed_url': data.get('rss_feed_url'),
                }
            )

            # Link host wrestlers
            for wrestler_name in data['host_wrestler_names']:
                wrestler = Wrestler.objects.filter(name__iexact=wrestler_name).first()
                if not wrestler:
                    wrestler = Wrestler.objects.filter(name__icontains=wrestler_name).first()
                if not wrestler:
                    # Create the wrestler/personality
                    wrestler = Wrestler.objects.create(
                        name=wrestler_name,
                        slug=slugify(wrestler_name),
                        about=f"Wrestling personality and podcast host"
                    )
                podcast.host_wrestlers.add(wrestler)

            self.podcasts[data['name']] = podcast
            status = 'Created' if created else 'Found'
            self.stdout.write(f'  {status}: {data["name"]}')

    def add_episodes(self):
        """Add episodes with guests and linked events/matches."""
        self.stdout.write('\n--- Adding Episodes ---')

        # Get common events for linking
        self.load_events()

        # Something to Wrestle episodes (Bruce Prichard)
        self.add_stww_episodes()

        # 83 Weeks episodes (Eric Bischoff)
        self.add_83weeks_episodes()

        # Grilling JR episodes
        self.add_grilling_jr_episodes()

        # Kurt Angle Show episodes
        self.add_kurt_angle_episodes()

        # Foley is Pod episodes
        self.add_foley_episodes()

        # Arn episodes
        self.add_arn_episodes()

        # My World with Jeff Jarrett episodes
        self.add_jarrett_episodes()

        # Matt Hardy episodes
        self.add_matt_hardy_episodes()

    def load_events(self):
        """Load events for linking to episodes."""
        self.events_cache = {}

        # Load major PPVs
        major_events = [
            'WrestleMania', 'SummerSlam', 'Royal Rumble', 'Survivor Series',
            'King of the Ring', 'In Your House', 'Starrcade', 'Halloween Havoc',
            'Bash at the Beach', 'Spring Stampede', 'Fall Brawl', 'SuperBrawl',
            'ECW Barely Legal', 'ECW November to Remember', 'ECW Heat Wave',
        ]

        for event_name in major_events:
            events = Event.objects.filter(name__icontains=event_name).order_by('date')
            for event in events:
                key = f"{event_name}_{event.date.year}" if event.date else event_name
                self.events_cache[key] = event

    def get_or_create_wrestler(self, name):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.filter(name__icontains=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(
                name=name,
                slug=slugify(name)
            )
        return wrestler

    def find_event(self, event_name, year=None):
        """Find an event by name and optionally year."""
        if year:
            event = Event.objects.filter(
                name__icontains=event_name,
                date__year=year
            ).first()
            if event:
                return event

        return Event.objects.filter(name__icontains=event_name).first()

    def find_match(self, wrestler1_name, wrestler2_name=None, event=None):
        """Find a match involving specific wrestlers."""
        wrestler1 = Wrestler.objects.filter(name__icontains=wrestler1_name).first()
        if not wrestler1:
            return None

        matches = Match.objects.filter(wrestlers=wrestler1)

        if wrestler2_name:
            wrestler2 = Wrestler.objects.filter(name__icontains=wrestler2_name).first()
            if wrestler2:
                matches = matches.filter(wrestlers=wrestler2)

        if event:
            matches = matches.filter(event=event)

        return matches.first()

    def create_episode(self, podcast, title, episode_num, pub_date, description,
                       guest_names=None, event_refs=None, match_refs=None):
        """Create a podcast episode with all links."""
        slug = slugify(f"{title}-{pub_date.strftime('%Y%m%d')}")
        guid = f"{podcast.slug}-{episode_num}"

        episode, created = PodcastEpisode.objects.get_or_create(
            guid=guid,
            defaults={
                'podcast': podcast,
                'title': title,
                'slug': slug,
                'episode_number': episode_num,
                'published_date': pub_date,
                'description': description,
                'duration_seconds': random.randint(5400, 10800),  # 1.5-3 hours
            }
        )

        if created:
            # Link guests
            if guest_names:
                for name in guest_names:
                    wrestler = self.get_or_create_wrestler(name)
                    episode.guests.add(wrestler)

            # Link events
            if event_refs:
                for event_name, year in event_refs:
                    event = self.find_event(event_name, year)
                    if event:
                        episode.discussed_events.add(event)

            # Link matches
            if match_refs:
                for w1, w2, event_name, year in match_refs:
                    event = self.find_event(event_name, year) if event_name else None
                    match = self.find_match(w1, w2, event)
                    if match:
                        episode.discussed_matches.add(match)

        return episode, created

    def add_stww_episodes(self):
        """Add Something to Wrestle episodes."""
        podcast = self.podcasts.get('Something to Wrestle with Bruce Prichard')
        if not podcast:
            return

        created = 0
        base_date = datetime(2016, 2, 1, tzinfo=timezone.utc)

        episodes_data = [
            # (title, guests, event_refs, match_refs)
            ("The Montreal Screwjob", ['Bret Hart', 'Shawn Michaels', 'Vince McMahon'],
             [('Survivor Series', 1997)], [('Bret Hart', 'Shawn Michaels', 'Survivor Series', 1997)]),
            ("Stone Cold Steve Austin", ['Stone Cold Steve Austin'],
             [('WrestleMania', 1998), ('WrestleMania', 2001)], [('Stone Cold', 'The Rock', 'WrestleMania', 2001)]),
            ("The Undertaker", ['The Undertaker'],
             [('WrestleMania', 1997), ('WrestleMania', 1998)], [('Undertaker', 'Shawn Michaels', 'WrestleMania', 1998)]),
            ("WrestleMania X-Seven", ['Stone Cold Steve Austin', 'The Rock'],
             [('WrestleMania', 2001)], [('Stone Cold', 'The Rock', 'WrestleMania', 2001)]),
            ("The Attitude Era", ['Vince McMahon'],
             [('WrestleMania', 1998), ('WrestleMania', 1999)], None),
            ("Mick Foley & Hell in a Cell", ['Mick Foley'],
             [('King of the Ring', 1998)], [('Mick Foley', 'Undertaker', 'King of the Ring', 1998)]),
            ("The Rock", ['The Rock'],
             [('WrestleMania', 2000), ('WrestleMania', 2001)], None),
            ("Triple H", ['Triple H'],
             [('WrestleMania', 2000), ('SummerSlam', 1999)], None),
            ("DX: The Early Years", ['Triple H', 'Shawn Michaels'],
             [('WrestleMania', 1998)], None),
            ("The Radicalz Debut", ['Chris Benoit', 'Eddie Guerrero', 'Dean Malenko', 'Perry Saturn'],
             [('Royal Rumble', 2000)], None),
            ("Kurt Angle's WWE Career", ['Kurt Angle'],
             [('WrestleMania', 2000), ('WrestleMania', 2001), ('WrestleMania', 2003)], None),
            ("Kane's Debut", ['Kane'],
             [('In Your House', 1997)], None),
            ("The Invasion", [],
             [('Invasion', 2001), ('SummerSlam', 2001)], None),
            ("Hulk Hogan Returns", ['Hulk Hogan'],
             [('WrestleMania', 2002)], [('Hulk Hogan', 'The Rock', 'WrestleMania', 2002)]),
            ("Edge & Christian", ['Edge', 'Christian'],
             [('WrestleMania', 2000), ('TLC', 2000)], None),
            ("The Hardy Boyz", ['Jeff Hardy', 'Matt Hardy'],
             [('WrestleMania', 2000)], None),
            ("The Dudley Boyz", ['Bubba Ray Dudley', 'D-Von Dudley'],
             [('Royal Rumble', 2000)], None),
            ("Royal Rumble 1992", ['Ric Flair'],
             [('Royal Rumble', 1992)], None),
            ("WrestleMania III", ['Hulk Hogan', 'Andre the Giant'],
             [('WrestleMania', 1987)], [('Hulk Hogan', 'Andre the Giant', 'WrestleMania', 1987)]),
            ("Bret Hart vs. Shawn Michaels", ['Bret Hart', 'Shawn Michaels'],
             [('WrestleMania', 1996), ('Survivor Series', 1997)], None),
            ("The Mega Powers Explode", ['Hulk Hogan', 'Randy Savage'],
             [('WrestleMania', 1989)], [('Hulk Hogan', 'Randy Savage', 'WrestleMania', 1989)]),
            ("Ultimate Warrior", ['Ultimate Warrior'],
             [('WrestleMania', 1990), ('SummerSlam', 1991)], None),
            ("Randy Savage", ['Randy Savage'],
             [('WrestleMania', 1988), ('WrestleMania', 1989)], None),
            ("John Cena's Rise", ['John Cena'],
             [('WrestleMania', 2005), ('WrestleMania', 2006)], None),
            ("Batista", ['Batista'],
             [('WrestleMania', 2005)], None),
            ("Eddie Guerrero", ['Eddie Guerrero'],
             [('WrestleMania', 2004)], None),
            ("Chris Jericho", ['Chris Jericho'],
             [('WrestleMania', 2002)], None),
            ("Brock Lesnar", ['Brock Lesnar'],
             [('WrestleMania', 2003), ('SummerSlam', 2002)], None),
            ("The Shield", ['Roman Reigns', 'Seth Rollins', 'Dean Ambrose'],
             [('Survivor Series', 2012)], None),
            ("Daniel Bryan & Yes Movement", ['Daniel Bryan'],
             [('WrestleMania', 2014)], None),
            ("CM Punk's Pipe Bomb", ['CM Punk'],
             [('Money in the Bank', 2011)], None),
            ("The Summer of Punk", ['CM Punk'],
             [('Money in the Bank', 2011), ('SummerSlam', 2011)], None),
            ("NXT Takeover", ['Finn Balor', 'Kevin Owens', 'Sami Zayn'],
             None, None),
            ("Women's Revolution", ['Charlotte Flair', 'Becky Lynch', 'Sasha Banks', 'Bayley'],
             [('WrestleMania', 2016)], None),
            ("AJ Styles Debut", ['AJ Styles'],
             [('Royal Rumble', 2016)], None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Bruce Prichard discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Something to Wrestle: Created {created} episodes')

    def add_83weeks_episodes(self):
        """Add 83 Weeks with Eric Bischoff episodes."""
        podcast = self.podcasts.get('83 Weeks with Eric Bischoff')
        if not podcast:
            return

        created = 0
        base_date = datetime(2018, 3, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("Bash at the Beach 1996 - Hogan Joins nWo", ['Hulk Hogan', 'Kevin Nash', 'Scott Hall'],
             [('Bash at the Beach', 1996)], None),
            ("Starrcade 1997 - Sting vs. Hogan", ['Sting', 'Hulk Hogan'],
             [('Starrcade', 1997)], [('Sting', 'Hulk Hogan', 'Starrcade', 1997)]),
            ("The Formation of the nWo", ['Hulk Hogan', 'Kevin Nash', 'Scott Hall'],
             [('Bash at the Beach', 1996)], None),
            ("Goldberg's Streak", ['Goldberg'],
             [('Starrcade', 1998)], [('Goldberg', 'Kevin Nash', 'Starrcade', 1998)]),
            ("Monday Night Wars Begin", [],
             None, None),
            ("Scott Hall & Kevin Nash Jump to WCW", ['Kevin Nash', 'Scott Hall'],
             None, None),
            ("Sting's Crow Era", ['Sting'],
             [('Starrcade', 1997)], None),
            ("The Fingerpoke of Doom", ['Hulk Hogan', 'Kevin Nash'],
             [('Nitro', 1999)], None),
            ("David Arquette Wins World Title", ['Diamond Dallas Page'],
             None, None),
            ("Starrcade 1983", ['Ric Flair', 'Harley Race'],
             [('Starrcade', 1983)], None),
            ("The Great American Bash 1990", ['Sting', 'Ric Flair'],
             [('Great American Bash', 1990)], None),
            ("Halloween Havoc 1998", ['Diamond Dallas Page', 'Goldberg'],
             [('Halloween Havoc', 1998)], None),
            ("Fall Brawl War Games", ['Sting', 'Ric Flair'],
             [('Fall Brawl', 1996)], None),
            ("Spring Stampede 1999", ['Diamond Dallas Page', 'Ric Flair'],
             [('Spring Stampede', 1999)], None),
            ("SuperBrawl 1997", ['Hulk Hogan', 'Roddy Piper'],
             [('SuperBrawl', 1997)], None),
            ("Lex Luger Jumps to WCW", ['Lex Luger'],
             None, None),
            ("Bret Hart in WCW", ['Bret Hart'],
             [('Starrcade', 1997)], None),
            ("Randy Savage in WCW", ['Randy Savage'],
             None, None),
            ("Ric Flair vs Eric Bischoff", ['Ric Flair'],
             None, None),
            ("The End of WCW", [],
             [('Nitro', 2001)], None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Eric Bischoff discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  83 Weeks: Created {created} episodes')

    def add_grilling_jr_episodes(self):
        """Add Grilling JR episodes."""
        podcast = self.podcasts.get('Grilling JR')
        if not podcast:
            return

        created = 0
        base_date = datetime(2018, 6, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("Stone Cold Steve Austin", ['Stone Cold Steve Austin'],
             [('WrestleMania', 1998), ('WrestleMania', 2001)], None),
            ("The Rock", ['The Rock'],
             [('WrestleMania', 2000), ('WrestleMania', 2001)], None),
            ("WrestleMania X-Seven", ['Stone Cold Steve Austin', 'The Rock'],
             [('WrestleMania', 2001)], [('Stone Cold', 'The Rock', 'WrestleMania', 2001)]),
            ("Mick Foley & Hell in a Cell", ['Mick Foley'],
             [('King of the Ring', 1998)], [('Mick Foley', 'Undertaker', 'King of the Ring', 1998)]),
            ("Owen Hart", ['Owen Hart'],
             [('WrestleMania', 1994), ('SummerSlam', 1997)], None),
            ("Bret Hart", ['Bret Hart'],
             [('WrestleMania', 1996), ('Survivor Series', 1997)], None),
            ("Shawn Michaels", ['Shawn Michaels'],
             [('WrestleMania', 1996), ('WrestleMania', 1998)], None),
            ("The Undertaker", ['The Undertaker'],
             [('WrestleMania', 1997), ('WrestleMania', 2007)], None),
            ("Triple H", ['Triple H'],
             [('WrestleMania', 2000), ('WrestleMania', 2001)], None),
            ("Kurt Angle", ['Kurt Angle'],
             [('WrestleMania', 2001), ('WrestleMania', 2003)], None),
            ("Eddie Guerrero", ['Eddie Guerrero'],
             [('WrestleMania', 2004)], None),
            ("Chris Benoit", ['Chris Benoit'],
             [('WrestleMania', 2004)], None),
            ("Vince McMahon & Montreal", ['Vince McMahon'],
             [('Survivor Series', 1997)], None),
            ("The Attitude Era", [],
             [('WrestleMania', 1998), ('WrestleMania', 1999)], None),
            ("JR Joins AEW", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Jim Ross discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Grilling JR: Created {created} episodes')

    def add_kurt_angle_episodes(self):
        """Add The Kurt Angle Show episodes."""
        podcast = self.podcasts.get('The Kurt Angle Show')
        if not podcast:
            return

        created = 0
        base_date = datetime(2020, 8, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("Kurt Angle's WWF Debut", [],
             [('Survivor Series', 1999)], None),
            ("Winning the WWF Championship", ['The Rock'],
             [('No Mercy', 2000)], None),
            ("WrestleMania X-Seven vs. Chris Benoit", ['Chris Benoit'],
             [('WrestleMania', 2001)], [('Kurt Angle', 'Chris Benoit', 'WrestleMania', 2001)]),
            ("The Milk Truck", [],
             None, None),
            ("King of the Ring 2001", ['Shane McMahon'],
             [('King of the Ring', 2001)], None),
            ("vs. Brock Lesnar at WrestleMania XIX", ['Brock Lesnar'],
             [('WrestleMania', 2003)], [('Kurt Angle', 'Brock Lesnar', 'WrestleMania', 2003)]),
            ("Olympic Gold Medal Story", [],
             None, None),
            ("TNA Years", ['Samoa Joe', 'AJ Styles'],
             None, None),
            ("vs. Shawn Michaels at WrestleMania 21", ['Shawn Michaels'],
             [('WrestleMania', 2005)], [('Kurt Angle', 'Shawn Michaels', 'WrestleMania', 2005)]),
            ("The Ankle Lock", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Kurt Angle discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Kurt Angle Show: Created {created} episodes')

    def add_foley_episodes(self):
        """Add Foley is Pod episodes."""
        podcast = self.podcasts.get('Foley is Pod')
        if not podcast:
            return

        created = 0
        base_date = datetime(2022, 1, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("Hell in a Cell 1998 - The Undertaker Match", ['The Undertaker'],
             [('King of the Ring', 1998)], [('Mick Foley', 'Undertaker', 'King of the Ring', 1998)]),
            ("Mankind vs. The Rock - I Quit Match", ['The Rock'],
             [('Royal Rumble', 1999)], [('Mick Foley', 'The Rock', 'Royal Rumble', 1999)]),
            ("Winning the WWF Championship", ['The Rock'],
             [('Raw', 1999)], None),
            ("Cactus Jack in ECW", ['Tommy Dreamer', 'Terry Funk'],
             None, None),
            ("WCW Days", ['Sting', 'Vader'],
             None, None),
            ("The Three Faces of Foley", [],
             None, None),
            ("Mr. Socko Origin", [],
             None, None),
            ("WrestleMania 2000 - Fatal Four Way", ['Triple H', 'The Rock', 'Big Show'],
             [('WrestleMania', 2000)], None),
            ("Royal Rumble 1998 - Casket Match", ['The Undertaker'],
             [('Royal Rumble', 1998)], [('Mick Foley', 'Undertaker', 'Royal Rumble', 1998)]),
            ("The Terry Funk Influence", ['Terry Funk'],
             None, None),
            ("Edge WrestleMania Match", ['Edge'],
             [('WrestleMania', 2006)], [('Mick Foley', 'Edge', 'WrestleMania', 2006)]),
            ("Writing Career and Have a Nice Day", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Mick Foley discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Foley is Pod: Created {created} episodes')

    def add_arn_episodes(self):
        """Add Arn episodes."""
        podcast = self.podcasts.get('Arn')
        if not podcast:
            return

        created = 0
        base_date = datetime(2019, 5, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("The Four Horsemen", ['Ric Flair', 'Tully Blanchard', 'Barry Windham'],
             None, None),
            ("Starrcade 1985", ['Ric Flair'],
             [('Starrcade', 1985)], None),
            ("The Dangerous Alliance", [],
             None, None),
            ("Brain Busters in WWF", ['Tully Blanchard'],
             None, None),
            ("Producing in WWE", [],
             None, None),
            ("Coaching in AEW", ['Cody Rhodes'],
             None, None),
            ("War Games Origins", ['Dusty Rhodes'],
             [('Fall Brawl', 1996)], None),
            ("WCW Nitro Era", ['Ric Flair', 'Sting'],
             None, None),
            ("The Enforcer Gimmick", [],
             None, None),
            ("Retirement from In-Ring", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Arn Anderson discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Arn: Created {created} episodes')

    def add_jarrett_episodes(self):
        """Add My World with Jeff Jarrett episodes."""
        podcast = self.podcasts.get('My World with Jeff Jarrett')
        if not podcast:
            return

        created = 0
        base_date = datetime(2021, 3, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("Starting TNA Wrestling", ['AJ Styles', 'Samoa Joe'],
             None, None),
            ("Intercontinental Championship", [],
             [('Royal Rumble', 1995), ('In Your House', 1995)], None),
            ("WCW World Championship", [],
             [('Bash at the Beach', 1999)], None),
            ("Good Housekeeping Match", ['Chyna'],
             [('No Mercy', 1999)], None),
            ("NWA Politics", [],
             None, None),
            ("Bullet Club & Global Force", [],
             None, None),
            ("The Jarrett Family Legacy", ['Jerry Jarrett'],
             None, None),
            ("AEW & Return to Wrestling", [],
             None, None),
            ("Owen Hart Memories", ['Owen Hart'],
             None, None),
            ("Working with Vince McMahon", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Jeff Jarrett discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  My World: Created {created} episodes')

    def add_matt_hardy_episodes(self):
        """Add The Extreme Life of Matt Hardy episodes."""
        podcast = self.podcasts.get('The Extreme Life of Matt Hardy')
        if not podcast:
            return

        created = 0
        base_date = datetime(2022, 4, 1, tzinfo=timezone.utc)

        episodes_data = [
            ("The Hardy Boyz Formation", ['Jeff Hardy'],
             None, None),
            ("TLC Matches", ['Jeff Hardy', 'Edge', 'Christian', 'Bubba Ray Dudley', 'D-Von Dudley'],
             [('WrestleMania', 2000), ('SummerSlam', 2000)], None),
            ("WrestleMania 2000 Triangle Ladder Match", ['Jeff Hardy', 'Edge', 'Christian'],
             [('WrestleMania', 2000)], None),
            ("Team Xtreme & Lita", ['Jeff Hardy', 'Lita'],
             None, None),
            ("Broken Matt Hardy in TNA", [],
             None, None),
            ("The Final Deletion", ['Jeff Hardy'],
             None, None),
            ("AEW Run", ['Jeff Hardy'],
             None, None),
            ("WWE Return 2017", ['Jeff Hardy'],
             [('WrestleMania', 2017)], None),
            ("Matt Hardy Version 1", [],
             None, None),
            ("Ring of Honor Run", [],
             None, None),
        ]

        for i, (title, guests, event_refs, match_refs) in enumerate(episodes_data, 1):
            pub_date = base_date + timedelta(weeks=i)
            description = f"Matt Hardy discusses {title} with Conrad Thompson."
            ep, was_created = self.create_episode(
                podcast, title, i, pub_date, description,
                guests, event_refs, match_refs
            )
            if was_created:
                created += 1

        self.stdout.write(f'  Extreme Life: Created {created} episodes')

    def print_summary(self):
        """Print summary of podcasts and episodes."""
        self.stdout.write('\n--- PODCAST SUMMARY ---')
        total_episodes = 0
        for name, podcast in self.podcasts.items():
            ep_count = podcast.episodes.count()
            total_episodes += ep_count
            guest_count = Wrestler.objects.filter(podcast_appearances__podcast=podcast).distinct().count()
            self.stdout.write(f'  {name}: {ep_count} episodes, {guest_count} unique guests')

        self.stdout.write(f'\nTotal Podcasts: {len(self.podcasts)}')
        self.stdout.write(f'Total Episodes: {total_episodes}')
        self.stdout.write(f'Total Podcast Entries: {Podcast.objects.count()}')
        self.stdout.write(f'Total Episode Entries: {PodcastEpisode.objects.count()}')
