"""
Management command to import podcast episodes from RSS feeds.

Usage:
    python manage.py import_podcast_rss                    # Import all podcasts with RSS feeds
    python manage.py import_podcast_rss --podcast-id=1    # Import specific podcast
    python manage.py import_podcast_rss --limit=50        # Limit episodes per podcast
    python manage.py import_podcast_rss --match-guests    # Try to match guests to wrestlers
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from owdbapp.models import Podcast, PodcastEpisode, Wrestler


class Command(BaseCommand):
    help = 'Import podcast episodes from RSS feeds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--podcast-id',
            type=int,
            help='Import only a specific podcast by ID'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of episodes to import per podcast (0 = all)'
        )
        parser.add_argument(
            '--match-guests',
            action='store_true',
            help='Try to match guest names in episode titles to wrestlers'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.match_guests = options['match_guests']
        self.limit = options['limit']

        # Get podcasts to process
        if options['podcast_id']:
            podcasts = Podcast.objects.filter(id=options['podcast_id'], rss_feed_url__isnull=False)
        else:
            podcasts = Podcast.objects.filter(rss_feed_url__isnull=False).exclude(rss_feed_url='')

        if not podcasts.exists():
            self.stdout.write(self.style.WARNING('No podcasts with RSS feeds found.'))
            return

        self.stdout.write(f'\nProcessing {podcasts.count()} podcast(s)...\n')

        total_created = 0
        total_updated = 0
        total_skipped = 0

        for podcast in podcasts:
            created, updated, skipped = self.process_podcast(podcast)
            total_created += created
            total_updated += updated
            total_skipped += skipped

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(
            f'Import complete: {total_created} created, {total_updated} updated, {total_skipped} skipped'
        ))

    def process_podcast(self, podcast):
        """Process a single podcast's RSS feed."""
        self.stdout.write(f'\n--- {podcast.name} ---')
        self.stdout.write(f'RSS: {podcast.rss_feed_url}')

        try:
            episodes = self.fetch_rss(podcast.rss_feed_url)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching RSS: {e}'))
            return 0, 0, 0

        if not episodes:
            self.stdout.write(self.style.WARNING('No episodes found in feed'))
            return 0, 0, 0

        self.stdout.write(f'Found {len(episodes)} episodes in feed')

        if self.limit:
            episodes = episodes[:self.limit]
            self.stdout.write(f'Limiting to {self.limit} episodes')

        created = 0
        updated = 0
        skipped = 0

        for ep_data in episodes:
            result = self.import_episode(podcast, ep_data)
            if result == 'created':
                created += 1
            elif result == 'updated':
                updated += 1
            else:
                skipped += 1

        # Update last fetch time
        if not self.dry_run:
            podcast.last_rss_fetch = timezone.now()
            podcast.save(update_fields=['last_rss_fetch'])

        self.stdout.write(self.style.SUCCESS(
            f'  {created} created, {updated} updated, {skipped} skipped'
        ))

        return created, updated, skipped

    def fetch_rss(self, url):
        """Fetch and parse an RSS feed."""
        headers = {
            'User-Agent': 'OWDB Podcast Importer/1.0 (wrestlingdb.org)'
        }
        request = Request(url, headers=headers)

        with urlopen(request, timeout=30) as response:
            content = response.read()

        # Parse XML
        root = ET.fromstring(content)

        # Find channel and items
        channel = root.find('channel')
        if channel is None:
            # Try Atom format
            return self.parse_atom(root)

        return self.parse_rss(channel)

    def parse_rss(self, channel):
        """Parse RSS 2.0 format."""
        episodes = []

        for item in channel.findall('item'):
            ep_data = {
                'title': self.get_text(item, 'title'),
                'description': self.get_text(item, 'description') or self.get_text(item, 'content:encoded'),
                'published': self.parse_date(self.get_text(item, 'pubDate')),
                'guid': self.get_text(item, 'guid') or self.get_text(item, 'link'),
                'episode_url': self.get_text(item, 'link'),
                'audio_url': None,
                'duration': None,
                'image_url': None,
                'episode_number': None,
                'season_number': None,
            }

            # Get enclosure (audio file)
            enclosure = item.find('enclosure')
            if enclosure is not None:
                ep_data['audio_url'] = enclosure.get('url')

            # iTunes extensions
            itunes_ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}

            duration = item.find('itunes:duration', itunes_ns)
            if duration is not None and duration.text:
                ep_data['duration'] = self.parse_duration(duration.text)

            episode_num = item.find('itunes:episode', itunes_ns)
            if episode_num is not None and episode_num.text:
                try:
                    ep_data['episode_number'] = int(episode_num.text)
                except ValueError:
                    pass

            season_num = item.find('itunes:season', itunes_ns)
            if season_num is not None and season_num.text:
                try:
                    ep_data['season_number'] = int(season_num.text)
                except ValueError:
                    pass

            image = item.find('itunes:image', itunes_ns)
            if image is not None:
                ep_data['image_url'] = image.get('href')

            if ep_data['title']:
                episodes.append(ep_data)

        return episodes

    def parse_atom(self, root):
        """Parse Atom format."""
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        episodes = []

        for entry in root.findall('atom:entry', ns):
            ep_data = {
                'title': self.get_text(entry, 'atom:title', ns),
                'description': self.get_text(entry, 'atom:summary', ns) or self.get_text(entry, 'atom:content', ns),
                'published': self.parse_date(self.get_text(entry, 'atom:published', ns)),
                'guid': self.get_text(entry, 'atom:id', ns),
                'episode_url': None,
                'audio_url': None,
                'duration': None,
                'image_url': None,
                'episode_number': None,
                'season_number': None,
            }

            # Get links
            for link in entry.findall('atom:link', ns):
                rel = link.get('rel', 'alternate')
                if rel == 'alternate':
                    ep_data['episode_url'] = link.get('href')
                elif rel == 'enclosure':
                    ep_data['audio_url'] = link.get('href')

            if ep_data['title']:
                episodes.append(ep_data)

        return episodes

    def get_text(self, element, path, ns=None):
        """Get text content from an element."""
        if ns:
            child = element.find(path, ns)
        else:
            child = element.find(path)
        return child.text.strip() if child is not None and child.text else None

    def parse_date(self, date_str):
        """Parse various date formats."""
        if not date_str:
            return None

        try:
            # RFC 2822 (common in RSS)
            return parsedate_to_datetime(date_str)
        except Exception:
            pass

        # Try ISO format
        for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.tzinfo is None:
                    dt = timezone.make_aware(dt)
                return dt
            except ValueError:
                continue

        return None

    def parse_duration(self, duration_str):
        """Parse duration string to seconds."""
        if not duration_str:
            return None

        # Already seconds
        if duration_str.isdigit():
            return int(duration_str)

        # HH:MM:SS or MM:SS format
        parts = duration_str.split(':')
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            pass

        return None

    def import_episode(self, podcast, ep_data):
        """Import a single episode."""
        if not ep_data.get('guid'):
            return 'skipped'

        # Check if already exists
        existing = PodcastEpisode.objects.filter(guid=ep_data['guid']).first()

        if existing:
            # Update if needed
            updated = False
            if ep_data.get('description') and not existing.description:
                existing.description = ep_data['description']
                updated = True
            if ep_data.get('duration') and not existing.duration_seconds:
                existing.duration_seconds = ep_data['duration']
                updated = True

            if updated and not self.dry_run:
                existing.save()
                return 'updated'
            return 'skipped'

        # Create new episode
        if self.dry_run:
            self.stdout.write(f"    Would create: {ep_data['title'][:60]}...")
            return 'created'

        episode = PodcastEpisode.objects.create(
            podcast=podcast,
            title=ep_data['title'][:500],
            published_date=ep_data.get('published'),
            description=ep_data.get('description'),
            audio_url=ep_data.get('audio_url'),
            episode_url=ep_data.get('episode_url'),
            image_url=ep_data.get('image_url'),
            duration_seconds=ep_data.get('duration'),
            episode_number=ep_data.get('episode_number'),
            season_number=ep_data.get('season_number'),
            guid=ep_data['guid'],
        )

        # Match guests if enabled
        if self.match_guests:
            guests = self.find_guest_wrestlers(ep_data['title'], ep_data.get('description', ''))
            if guests:
                episode.guests.set(guests)
                self.stdout.write(f"    Matched guests: {[w.name for w in guests]}")

        return 'created'

    def find_guest_wrestlers(self, title, description=''):
        """Try to find wrestler names in episode title/description."""
        # Get all wrestler names for matching
        wrestlers = Wrestler.objects.all().values_list('id', 'name', 'real_name', 'aliases')

        text = f"{title} {description or ''}".lower()
        matched = []

        for wrestler_id, name, real_name, aliases in wrestlers:
            # Check ring name
            if name.lower() in text:
                matched.append(wrestler_id)
                continue

            # Check real name
            if real_name and real_name.lower() in text:
                matched.append(wrestler_id)
                continue

            # Check aliases
            if aliases:
                for alias in aliases.split(','):
                    alias = alias.strip().lower()
                    if alias and len(alias) > 3 and alias in text:
                        matched.append(wrestler_id)
                        break

        return Wrestler.objects.filter(id__in=matched[:10])  # Limit to 10 guests per episode
