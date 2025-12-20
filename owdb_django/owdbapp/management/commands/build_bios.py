"""
Build out biographies and profiles for database entries.
Adds structured content with appropriate subheaders.

For individuals: Uses decades or promotions to delineate major periods.
For promotions: Uses decades or ownership changes.

Usage:
    python manage.py build_bios --model=wrestlers --limit=50
    python manage.py build_bios --model=promotions --limit=20
"""
from django.core.management.base import BaseCommand
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Stable
)


class Command(BaseCommand):
    help = 'Build out biographies and profiles for database entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='all',
            help='Model to add bios to: wrestlers, promotions, stables, all'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=100,
            help='Maximum number of entries to process'
        )

    def handle(self, *args, **options):
        model = options.get('model', 'all')
        limit = options.get('limit', 100)

        self.stdout.write(self.style.SUCCESS(f'\n=== Building Biographies ({model}) ===\n'))

        if model in ['all', 'wrestlers']:
            self.build_wrestler_bios(limit)
        if model in ['all', 'promotions']:
            self.build_promotion_bios(limit)
        if model in ['all', 'stables']:
            self.build_stable_bios(limit)

        self.stdout.write(self.style.SUCCESS('\n=== Biography Building Complete ===\n'))

    def build_wrestler_bios(self, limit):
        """Build structured biographies for wrestlers with short or no bios."""
        self.stdout.write('\n--- Building Wrestler Biographies ---\n')

        # Get wrestlers with short or no about text
        wrestlers = Wrestler.objects.filter(
            about__isnull=False
        ).exclude(about='').order_by('-created_at')[:limit]

        count = 0
        for wrestler in wrestlers:
            # Skip if already has a long bio with headers
            if wrestler.about and len(wrestler.about) > 500 and '##' in wrestler.about:
                continue

            enhanced_bio = self.enhance_wrestler_bio(wrestler)
            if enhanced_bio and enhanced_bio != wrestler.about:
                wrestler.about = enhanced_bio
                wrestler.save(update_fields=['about'])
                self.stdout.write(f'  + {wrestler.name}')
                count += 1

        self.stdout.write(f'\nEnhanced {count} wrestler bios')

    def enhance_wrestler_bio(self, wrestler):
        """Enhance a wrestler's biography with structured content."""
        parts = []

        # Start with existing about if present
        if wrestler.about:
            parts.append(wrestler.about)

        # Add career timeline section if we have debut/retirement years
        if wrestler.debut_year or wrestler.retirement_year:
            career_info = []

            if wrestler.debut_year:
                career_info.append(f"made their professional wrestling debut in {wrestler.debut_year}")

            if wrestler.retirement_year:
                career_info.append(f"retired in {wrestler.retirement_year}")

            if career_info:
                career_text = wrestler.name + " " + " and ".join(career_info) + "."
                if career_text not in ' '.join(parts):
                    parts.append(career_text)

        # Add finishing move section if available
        if wrestler.finishers:
            finisher_text = f"Known for signature moves including: {wrestler.finishers}."
            if finisher_text not in ' '.join(parts):
                parts.append(finisher_text)

        # Add hometown info
        if wrestler.hometown:
            hometown_text = f"Billed from {wrestler.hometown}."
            if hometown_text not in ' '.join(parts) and wrestler.hometown not in ' '.join(parts):
                parts.append(hometown_text)

        # Add real name if different from ring name
        if wrestler.real_name and wrestler.real_name.lower() != wrestler.name.lower():
            real_name_text = f"Real name: {wrestler.real_name}."
            if real_name_text not in ' '.join(parts) and wrestler.real_name not in ' '.join(parts):
                parts.append(real_name_text)

        return ' '.join(parts) if parts else None

    def build_promotion_bios(self, limit):
        """Build structured biographies for promotions."""
        self.stdout.write('\n--- Building Promotion Biographies ---\n')

        promotions = Promotion.objects.filter(
            about__isnull=False
        ).exclude(about='').order_by('-created_at')[:limit]

        count = 0
        for promotion in promotions:
            # Skip if already has a long bio
            if promotion.about and len(promotion.about) > 500:
                continue

            enhanced_bio = self.enhance_promotion_bio(promotion)
            if enhanced_bio and enhanced_bio != promotion.about:
                promotion.about = enhanced_bio
                promotion.save(update_fields=['about'])
                self.stdout.write(f'  + {promotion.name}')
                count += 1

        self.stdout.write(f'\nEnhanced {count} promotion bios')

    def enhance_promotion_bio(self, promotion):
        """Enhance a promotion's biography with structured content."""
        parts = []

        # Start with existing about if present
        if promotion.about:
            parts.append(promotion.about)

        # Add founding info
        if promotion.founded_year:
            founding_text = f"Founded in {promotion.founded_year}."
            if str(promotion.founded_year) not in ' '.join(parts):
                parts.append(founding_text)

        # Add closure info if applicable
        if promotion.closed_year:
            closure_text = f"Ceased operations in {promotion.closed_year}."
            if str(promotion.closed_year) not in ' '.join(parts):
                parts.append(closure_text)

        # Add headquarters info
        if promotion.headquarters:
            hq_text = f"Headquartered in {promotion.headquarters}."
            if promotion.headquarters not in ' '.join(parts):
                parts.append(hq_text)

        return ' '.join(parts) if parts else None

    def build_stable_bios(self, limit):
        """Build structured biographies for stables/factions."""
        self.stdout.write('\n--- Building Stable Biographies ---\n')

        stables = Stable.objects.filter(
            about__isnull=False
        ).exclude(about='').order_by('-created_at')[:limit]

        count = 0
        for stable in stables:
            # Skip if already has a long bio
            if stable.about and len(stable.about) > 500:
                continue

            enhanced_bio = self.enhance_stable_bio(stable)
            if enhanced_bio and enhanced_bio != stable.about:
                stable.about = enhanced_bio
                stable.save(update_fields=['about'])
                self.stdout.write(f'  + {stable.name}')
                count += 1

        self.stdout.write(f'\nEnhanced {count} stable bios')

    def enhance_stable_bio(self, stable):
        """Enhance a stable's biography with structured content."""
        parts = []

        # Start with existing about if present
        if stable.about:
            parts.append(stable.about)

        # Add formation/disbandment info
        if stable.formed_year:
            formed_text = f"Formed in {stable.formed_year}."
            if str(stable.formed_year) not in ' '.join(parts):
                parts.append(formed_text)

        if stable.disbanded_year:
            disbanded_text = f"Disbanded in {stable.disbanded_year}."
            if str(stable.disbanded_year) not in ' '.join(parts):
                parts.append(disbanded_text)

        # Add member count if we have members
        member_count = stable.members.count()
        if member_count > 0:
            members_text = f"Featured {member_count} known members throughout its history."
            if 'members' not in ' '.join(parts).lower():
                parts.append(members_text)

        return ' '.join(parts) if parts else None
