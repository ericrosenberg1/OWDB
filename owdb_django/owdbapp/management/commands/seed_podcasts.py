"""
Management command to seed popular wrestling podcasts with RSS feeds.
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdbapp.models import Podcast, Wrestler


class Command(BaseCommand):
    help = 'Seed popular wrestling podcasts with RSS feed URLs'

    def handle(self, *args, **options):
        self.stdout.write('\n=== SEEDING WRESTLING PODCASTS ===\n')

        podcasts = [
            {
                'name': 'Talk Is Jericho',
                'hosts': 'Chris Jericho',
                'launch_year': 2013,
                'url': 'https://omny.fm/shows/talk-is-jericho',
                'rss_feed_url': 'https://www.omnycontent.com/d/playlist/9b7dacdf-a925-4f95-84dc-ac46003451ff/c2dbbe98-b75f-4a98-8b3f-ac4e0039f1eb/8cd8e1a0-12a7-4d82-9557-ac4e0039f1fa/podcast.rss',
                'about': 'Talk Is Jericho is the podcast hosted by WWE Hall of Famer and AEW star Chris Jericho. The show features interviews with musicians, actors, athletes, comedians, and fellow wrestlers, with Jericho bringing his trademark wit and insight to every conversation.',
            },
            {
                'name': 'Something to Wrestle with Bruce Prichard',
                'hosts': 'Bruce Prichard, Conrad Thompson',
                'launch_year': 2016,
                'url': 'https://www.stwpodcast.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/HSW7835889191',
                'about': 'Bruce Prichard, WWE executive and former on-screen character Brother Love, shares behind-the-scenes stories from his decades in professional wrestling. Co-hosted by Conrad Thompson.',
            },
            {
                'name': '83 Weeks with Eric Bischoff',
                'hosts': 'Eric Bischoff, Conrad Thompson',
                'launch_year': 2018,
                'url': 'https://www.83weeks.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/HSW4389879243',
                'about': 'Former WCW President Eric Bischoff discusses the Monday Night Wars era, his time running WCW, and all the stories from that legendary period in wrestling history. Co-hosted by Conrad Thompson.',
            },
            {
                'name': 'Grilling JR',
                'hosts': 'Jim Ross, Conrad Thompson',
                'launch_year': 2019,
                'url': 'https://www.grillingjr.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/HSW1631532588',
                'about': 'WWE Hall of Famer and legendary commentator Jim Ross shares stories from his career, including his time in WWE, WCW, and AEW. Co-hosted by Conrad Thompson.',
            },
            {
                'name': 'The Kurt Angle Show',
                'hosts': 'Kurt Angle, Conrad Thompson',
                'launch_year': 2020,
                'url': 'https://www.thekurtangleshow.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/WWO9802685007',
                'about': 'Olympic gold medalist and WWE Hall of Famer Kurt Angle shares stories from his legendary wrestling career, including his time in WWE, TNA, and his Olympic journey.',
            },
            {
                'name': 'What Happened When with Tony Schiavone',
                'hosts': 'Tony Schiavone, Conrad Thompson',
                'launch_year': 2017,
                'url': 'https://www.whathappenedwhen.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/HSW6884270915',
                'about': 'WCW lead announcer Tony Schiavone takes a trip down memory lane to discuss classic wrestling moments, matches, and behind-the-scenes stories from his career.',
            },
            {
                'name': 'Arn',
                'hosts': 'Arn Anderson, Conrad Thompson',
                'launch_year': 2019,
                'url': 'https://www.arnpodcast.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/ARN7834190502',
                'about': 'WWE Hall of Famer and Four Horsemen legend Arn Anderson shares stories from his storied career, including his time in WCW, WWE, and as a coach/producer.',
            },
            {
                'name': 'The Stone Cold Podcast',
                'hosts': 'Steve Austin',
                'launch_year': 2013,
                'url': 'https://podcasts.apple.com/us/podcast/the-steve-austin-show/id706529864',
                'rss_feed_url': '',  # Patreon/subscription only now
                'about': 'WWE Hall of Famer Stone Cold Steve Austin hosts this podcast featuring interviews with wrestlers, celebrities, and discussions about wrestling history and current events.',
            },
            {
                'name': 'The Foley Is Pod',
                'hosts': 'Mick Foley, Conrad Thompson',
                'launch_year': 2021,
                'url': 'https://www.foleyispod.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/WWO9215107135',
                'about': 'WWE Hall of Famer Mick Foley discusses his incredible career, from Cactus Jack to Mankind to Dude Love, sharing stories from ECW, WCW, and WWE.',
            },
            {
                'name': 'Busted Open Radio',
                'hosts': 'Dave LaGreca, Bully Ray',
                'launch_year': 2012,
                'url': 'https://www.siriusxm.com/channels/busted-open',
                'rss_feed_url': 'https://feeds.megaphone.fm/busteropen',
                'about': 'The flagship wrestling talk show on SiriusXM, featuring news, interviews, and analysis of professional wrestling.',
            },
            {
                'name': 'The Masked Man Show',
                'hosts': 'David Shoemaker, Kaz Rastagar',
                'launch_year': 2015,
                'url': 'https://www.theringer.com/the-masked-man-show',
                'rss_feed_url': 'https://feeds.megaphone.fm/the-masked-man-show',
                'about': 'The Ringer\'s wrestling podcast covering WWE, AEW, and all major wrestling promotions with analysis and interviews.',
            },
            {
                'name': 'Oral Sessions with Renee Paquette',
                'hosts': 'Renee Paquette',
                'launch_year': 2020,
                'url': 'https://oralsessions.libsyn.com/',
                'rss_feed_url': 'https://oralsessions.libsyn.com/rss',
                'about': 'Former WWE broadcaster Renee Paquette hosts conversations with wrestlers, athletes, and entertainers about their lives and careers.',
            },
            {
                'name': 'The Sessions with Renee Paquette',
                'hosts': 'Renee Paquette',
                'launch_year': 2023,
                'url': 'https://podcasts.apple.com/us/podcast/the-sessions-with-renee-paquette/id1714867608',
                'rss_feed_url': '',
                'about': 'Renee Paquette\'s continued podcast featuring in-depth interviews with wrestling personalities.',
            },
            {
                'name': 'Unrestricted',
                'hosts': 'Tony Schiavone, Aubrey Edwards',
                'launch_year': 2020,
                'url': 'https://www.allelitewrestling.com/unrestricted',
                'rss_feed_url': 'https://anchor.fm/s/174be968/podcast/rss',
                'about': 'The official AEW podcast featuring interviews with AEW wrestlers and behind-the-scenes content from All Elite Wrestling.',
            },
            {
                'name': 'Strictly Business with Eric Bischoff',
                'hosts': 'Eric Bischoff',
                'launch_year': 2020,
                'url': 'https://www.adfreeshows.com/shows/strictly-business',
                'rss_feed_url': '',
                'about': 'Eric Bischoff\'s business-focused podcast discussing the wrestling industry, media, and entertainment business strategies.',
            },
            {
                'name': 'After the Bell with Corey Graves',
                'hosts': 'Corey Graves',
                'launch_year': 2019,
                'url': 'https://www.wwe.com/after-the-bell-podcast',
                'rss_feed_url': 'https://feeds.megaphone.fm/afterthebell',
                'about': 'WWE\'s official podcast hosted by SmackDown announcer Corey Graves, featuring interviews with WWE Superstars and behind-the-scenes content.',
            },
            {
                'name': 'The New Day: Feel the Power',
                'hosts': 'Big E, Kofi Kingston, Xavier Woods',
                'launch_year': 2019,
                'url': 'https://www.wwe.com/new-day-podcast',
                'rss_feed_url': 'https://feeds.megaphone.fm/newdayfeelthepower',
                'about': 'The New Day\'s official WWE podcast featuring Big E, Kofi Kingston, and Xavier Woods discussing wrestling, pop culture, and gaming.',
            },
            {
                'name': 'Insight with Chris Van Vliet',
                'hosts': 'Chris Van Vliet',
                'launch_year': 2018,
                'url': 'https://chrisvanvliet.com/',
                'rss_feed_url': 'https://feeds.megaphone.fm/chrisvanvliet',
                'about': 'In-depth interviews with wrestlers, athletes, and entertainers, known for getting exclusive and compelling stories from guests.',
            },
            {
                'name': 'Keepin It 100 with Konnan',
                'hosts': 'Konnan, Disco Inferno',
                'launch_year': 2016,
                'url': 'https://www.keepinit100podcast.com/',
                'rss_feed_url': '',
                'about': 'Wrestling legend Konnan and Disco Inferno discuss current wrestling news, share stories from their careers, and provide commentary on the industry.',
            },
            {
                'name': 'The Lapsed Fan',
                'hosts': 'Jack Encarnacao, JP Sorrentino',
                'launch_year': 2014,
                'url': 'https://www.thelapsedfan.com/',
                'rss_feed_url': 'https://thelapsedfan.libsyn.com/rss',
                'about': 'Comprehensive retrospective coverage of classic wrestling events and eras, known for extremely detailed show reviews and historical context.',
            },
        ]

        created = 0
        updated = 0

        for podcast_data in podcasts:
            slug = slugify(podcast_data['name'])
            podcast, was_created = Podcast.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': podcast_data['name'],
                    'hosts': podcast_data.get('hosts', ''),
                    'launch_year': podcast_data.get('launch_year'),
                    'url': podcast_data.get('url', ''),
                    'rss_feed_url': podcast_data.get('rss_feed_url', ''),
                    'about': podcast_data.get('about', ''),
                }
            )

            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {podcast.name}'))
            else:
                # Update RSS feed if not set
                if podcast_data.get('rss_feed_url') and not podcast.rss_feed_url:
                    podcast.rss_feed_url = podcast_data['rss_feed_url']
                    podcast.save(update_fields=['rss_feed_url'])
                    updated += 1
                    self.stdout.write(f'  Updated RSS: {podcast.name}')
                else:
                    self.stdout.write(f'  Exists: {podcast.name}')

            # Try to link host wrestlers
            if podcast_data.get('hosts'):
                self.link_host_wrestlers(podcast, podcast_data['hosts'])

        self.stdout.write('\n=== SEEDING COMPLETE ===')
        self.stdout.write(f'Created: {created}, Updated: {updated}')
        self.stdout.write(f'Total podcasts: {Podcast.objects.count()}')
        self.stdout.write(f'Podcasts with RSS feeds: {Podcast.objects.exclude(rss_feed_url="").exclude(rss_feed_url__isnull=True).count()}')

    def link_host_wrestlers(self, podcast, hosts_str):
        """Try to link host names to existing wrestlers."""
        host_names = [h.strip() for h in hosts_str.split(',')]

        for name in host_names:
            # Try to find wrestler by name or alias
            wrestler = Wrestler.objects.filter(name__iexact=name).first()
            if not wrestler:
                # Try partial match
                wrestler = Wrestler.objects.filter(name__icontains=name).first()

            if wrestler:
                podcast.host_wrestlers.add(wrestler)
                self.stdout.write(f'    Linked host: {wrestler.name}')
