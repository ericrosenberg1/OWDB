"""
Add CC-licensed images to database entries.
Uses Wikimedia Commons API to find images that allow commercial use.

Usage:
    python manage.py add_images --model=wrestlers --limit=50
    python manage.py add_images --model=promotions --limit=20
    python manage.py add_images --model=all
"""
import requests
import time
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Title, Venue, Stable,
    VideoGame, Podcast, Book, Special
)


class Command(BaseCommand):
    help = 'Add CC-licensed images from Wikimedia Commons to entries without images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='all',
            help='Model to add images to: wrestlers, promotions, titles, venues, stables, all'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of entries to process'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        model = options.get('model', 'all')
        limit = options.get('limit', 100)
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        self.stdout.write(self.style.SUCCESS(f'\n=== Adding CC Images ({model}) ===\n'))

        if model in ['all', 'wrestlers']:
            self.add_wrestler_images(limit, dry_run)
        if model in ['all', 'promotions']:
            self.add_promotion_images(limit, dry_run)
        if model in ['all', 'titles']:
            self.add_title_images(limit, dry_run)
        if model in ['all', 'venues']:
            self.add_venue_images(limit, dry_run)
        if model in ['all', 'stables']:
            self.add_stable_images(limit, dry_run)

        self.stdout.write(self.style.SUCCESS('\n=== Image Addition Complete ===\n'))

    def search_wikimedia_image(self, search_term, category_hint=None):
        """
        Search Wikimedia Commons for a CC-licensed image.
        Returns the image URL if found, None otherwise.
        """
        base_url = "https://commons.wikimedia.org/w/api.php"

        # Add category hint to improve search results
        if category_hint:
            search_term = f"{search_term} {category_hint}"

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": search_term,
            "gsrnamespace": 6,  # File namespace
            "gsrlimit": 5,
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 400,  # Thumbnail width
        }

        try:
            response = requests.get(base_url, params=params, timeout=10)
            data = response.json()

            if 'query' not in data or 'pages' not in data['query']:
                return None

            for page_id, page in data['query']['pages'].items():
                if 'imageinfo' not in page:
                    continue

                imageinfo = page['imageinfo'][0]
                metadata = imageinfo.get('extmetadata', {})

                # Check license - we want CC or public domain
                license_short = metadata.get('LicenseShortName', {}).get('value', '').lower()

                # Accept CC licenses, public domain, or no restrictions
                acceptable_licenses = ['cc', 'public domain', 'pd', 'cc0', 'no restrictions']
                if any(lic in license_short for lic in acceptable_licenses):
                    # Return thumbnail URL if available, otherwise main URL
                    return imageinfo.get('thumburl') or imageinfo.get('url')

            return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  Error searching for {search_term}: {e}'))
            return None

    def add_wrestler_images(self, limit, dry_run):
        """Add images to wrestlers without images."""
        self.stdout.write('\n--- Adding Wrestler Images ---\n')

        wrestlers = Wrestler.objects.filter(image_url__isnull=True)[:limit]
        count = 0

        for wrestler in wrestlers:
            # Search with "wrestler" hint to get better results
            image_url = self.search_wikimedia_image(wrestler.name, "wrestler")

            if image_url:
                if not dry_run:
                    wrestler.image_url = image_url
                    wrestler.save(update_fields=['image_url'])
                self.stdout.write(self.style.SUCCESS(f'  + {wrestler.name}'))
                count += 1
            else:
                self.stdout.write(f'  - {wrestler.name} (no image found)')

            time.sleep(0.5)  # Rate limiting

        self.stdout.write(f'\nAdded {count} wrestler images')

    def add_promotion_images(self, limit, dry_run):
        """Add images to promotions without images."""
        self.stdout.write('\n--- Adding Promotion Images ---\n')

        promotions = Promotion.objects.filter(image_url__isnull=True)[:limit]
        count = 0

        for promotion in promotions:
            # Search with "wrestling" hint
            search_term = f"{promotion.name} logo"
            image_url = self.search_wikimedia_image(search_term, "wrestling promotion")

            if image_url:
                if not dry_run:
                    promotion.image_url = image_url
                    promotion.save(update_fields=['image_url'])
                self.stdout.write(self.style.SUCCESS(f'  + {promotion.name}'))
                count += 1
            else:
                self.stdout.write(f'  - {promotion.name} (no image found)')

            time.sleep(0.5)

        self.stdout.write(f'\nAdded {count} promotion images')

    def add_title_images(self, limit, dry_run):
        """Add images to titles without images."""
        self.stdout.write('\n--- Adding Title Images ---\n')

        titles = Title.objects.filter(image_url__isnull=True)[:limit]
        count = 0

        for title in titles:
            # Search with "championship belt" hint
            image_url = self.search_wikimedia_image(title.name, "championship belt")

            if image_url:
                if not dry_run:
                    title.image_url = image_url
                    title.save(update_fields=['image_url'])
                self.stdout.write(self.style.SUCCESS(f'  + {title.name}'))
                count += 1
            else:
                self.stdout.write(f'  - {title.name} (no image found)')

            time.sleep(0.5)

        self.stdout.write(f'\nAdded {count} title images')

    def add_venue_images(self, limit, dry_run):
        """Add images to venues without images."""
        self.stdout.write('\n--- Adding Venue Images ---\n')

        venues = Venue.objects.filter(image_url__isnull=True)[:limit]
        count = 0

        for venue in venues:
            # Search with "arena" or "stadium" hint
            image_url = self.search_wikimedia_image(venue.name, "arena stadium")

            if image_url:
                if not dry_run:
                    venue.image_url = image_url
                    venue.save(update_fields=['image_url'])
                self.stdout.write(self.style.SUCCESS(f'  + {venue.name}'))
                count += 1
            else:
                self.stdout.write(f'  - {venue.name} (no image found)')

            time.sleep(0.5)

        self.stdout.write(f'\nAdded {count} venue images')

    def add_stable_images(self, limit, dry_run):
        """Add images to stables without images."""
        self.stdout.write('\n--- Adding Stable Images ---\n')

        stables = Stable.objects.filter(image_url__isnull=True)[:limit]
        count = 0

        for stable in stables:
            # Search with "wrestling" hint
            image_url = self.search_wikimedia_image(stable.name, "wrestling faction")

            if image_url:
                if not dry_run:
                    stable.image_url = image_url
                    stable.save(update_fields=['image_url'])
                self.stdout.write(self.style.SUCCESS(f'  + {stable.name}'))
                count += 1
            else:
                self.stdout.write(f'  - {stable.name} (no image found)')

            time.sleep(0.5)

        self.stdout.write(f'\nAdded {count} stable images')
