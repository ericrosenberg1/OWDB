"""
Seed the TVShow model with all major wrestling TV shows.

This creates TVShow records for all major wrestling promotions,
enabling the TV episode tracking system to function.

Usage:
    python manage.py seed_tv_shows
    python manage.py seed_tv_shows --promotion WWE
    python manage.py seed_tv_shows --type weekly
"""
from datetime import date

from django.core.management.base import BaseCommand

from owdb_django.owdbapp.models import TVShow, Promotion


class Command(BaseCommand):
    help = 'Seed TV shows for all major wrestling promotions'

    # Comprehensive list of wrestling TV shows with TMDB IDs where available
    TV_SHOWS = [
        # =================================================================
        # WWE / WWF
        # =================================================================
        {
            'name': 'WWE Raw',
            'promotion': 'WWE',
            'show_type': 'weekly',
            'network': 'Netflix',
            'air_day': 'Monday',
            'premiere_date': date(1993, 1, 11),
            'tmdb_id': 4370,
            'about': 'The flagship show of WWE, Monday Night Raw has been on the air since 1993.',
        },
        {
            'name': 'WWE SmackDown',
            'promotion': 'WWE',
            'show_type': 'weekly',
            'network': 'USA Network',
            'air_day': 'Friday',
            'premiere_date': date(1999, 8, 26),
            'tmdb_id': 4371,
            'about': 'The blue brand of WWE, SmackDown has been a weekly staple since 1999.',
        },
        {
            'name': 'WWE NXT',
            'promotion': 'WWE',
            'show_type': 'weekly',
            'network': 'USA Network',
            'air_day': 'Tuesday',
            'premiere_date': date(2010, 2, 23),
            'tmdb_id': 35521,
            'about': 'WWE\'s developmental brand featuring rising stars and future champions.',
        },
        {
            'name': 'WWE Main Event',
            'promotion': 'WWE',
            'show_type': 'weekly',
            'network': 'Hulu',
            'air_day': 'Thursday',
            'premiere_date': date(2012, 10, 3),
            'tmdb_id': 45533,
            'about': 'Weekly WWE programming featuring mid-card matches.',
        },
        {
            'name': 'Saturday Night\'s Main Event',
            'promotion': 'WWE',
            'show_type': 'special',
            'network': 'NBC',
            'air_day': 'Saturday',
            'premiere_date': date(1985, 5, 11),
            'about': 'Classic WWE special event series that aired on NBC.',
        },
        {
            'name': 'WWE Superstars',
            'promotion': 'WWE',
            'show_type': 'weekly',
            'premiere_date': date(1984, 9, 1),
            'finale_date': date(2016, 4, 28),
            'about': 'Long-running syndicated WWE program.',
        },
        # WWE PPV Series
        {
            'name': 'WWE WrestleMania',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(1985, 3, 31),
            'about': 'The biggest event in professional wrestling, held annually since 1985.',
        },
        {
            'name': 'WWE Royal Rumble',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(1988, 1, 24),
            'about': 'Annual WWE event featuring the 30-person Royal Rumble match.',
        },
        {
            'name': 'WWE SummerSlam',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(1988, 8, 29),
            'about': 'WWE\'s biggest summer event, second only to WrestleMania.',
        },
        {
            'name': 'WWE Survivor Series',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(1987, 11, 26),
            'about': 'Annual WWE event featuring traditional elimination matches.',
        },
        {
            'name': 'WWE Money in the Bank',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(2010, 7, 18),
            'about': 'Annual WWE event featuring ladder matches for title contracts.',
        },
        {
            'name': 'WWE Hell in a Cell',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(2009, 10, 4),
            'finale_date': date(2022, 6, 5),
            'about': 'Annual WWE event featuring Hell in a Cell matches.',
        },
        {
            'name': 'WWE Elimination Chamber',
            'promotion': 'WWE',
            'show_type': 'ppv',
            'premiere_date': date(2010, 2, 21),
            'about': 'Annual WWE event featuring the Elimination Chamber match.',
        },

        # =================================================================
        # WCW (Historical)
        # =================================================================
        {
            'name': 'WCW Monday Nitro',
            'promotion': 'WCW',
            'show_type': 'weekly',
            'network': 'TNT',
            'air_day': 'Monday',
            'premiere_date': date(1995, 9, 4),
            'finale_date': date(2001, 3, 26),
            'tmdb_id': 13579,
            'about': 'WCW\'s flagship show that competed with WWE Raw during the Monday Night Wars.',
        },
        {
            'name': 'WCW Thunder',
            'promotion': 'WCW',
            'show_type': 'weekly',
            'network': 'TBS',
            'air_day': 'Thursday',
            'premiere_date': date(1998, 1, 8),
            'finale_date': date(2001, 3, 21),
            'tmdb_id': 14247,
            'about': 'WCW\'s secondary weekly show that aired on TBS.',
        },
        {
            'name': 'WCW Saturday Night',
            'promotion': 'WCW',
            'show_type': 'weekly',
            'network': 'TBS',
            'air_day': 'Saturday',
            'premiere_date': date(1991, 9, 14),
            'finale_date': date(2000, 7, 1),
            'about': 'WCW\'s long-running Saturday program.',
        },
        # WCW PPVs
        {
            'name': 'WCW Starrcade',
            'promotion': 'WCW',
            'show_type': 'ppv',
            'premiere_date': date(1983, 11, 24),
            'finale_date': date(2000, 12, 17),
            'about': 'WCW\'s premier annual event, considered their WrestleMania.',
        },
        {
            'name': 'WCW Halloween Havoc',
            'promotion': 'WCW',
            'show_type': 'ppv',
            'premiere_date': date(1989, 10, 28),
            'finale_date': date(2000, 10, 29),
            'about': 'WCW\'s annual Halloween-themed event.',
        },
        {
            'name': 'WCW Bash at the Beach',
            'promotion': 'WCW',
            'show_type': 'ppv',
            'premiere_date': date(1994, 7, 17),
            'finale_date': date(2000, 7, 9),
            'about': 'WCW\'s summer beach-themed event.',
        },

        # =================================================================
        # ECW (Historical)
        # =================================================================
        {
            'name': 'ECW Hardcore TV',
            'promotion': 'ECW',
            'show_type': 'weekly',
            'premiere_date': date(1993, 4, 6),
            'finale_date': date(2001, 1, 13),
            'tmdb_id': 16347,
            'about': 'ECW\'s weekly television program showcasing extreme wrestling.',
        },
        {
            'name': 'ECW on TNN',
            'promotion': 'ECW',
            'show_type': 'weekly',
            'network': 'TNN',
            'air_day': 'Friday',
            'premiere_date': date(1999, 8, 27),
            'finale_date': date(2000, 10, 6),
            'about': 'ECW\'s national TV show on TNN.',
        },
        # ECW PPVs
        {
            'name': 'ECW Barely Legal',
            'promotion': 'ECW',
            'show_type': 'ppv',
            'premiere_date': date(1997, 4, 13),
            'about': 'ECW\'s first pay-per-view event.',
        },
        {
            'name': 'ECW November to Remember',
            'promotion': 'ECW',
            'show_type': 'ppv',
            'premiere_date': date(1993, 11, 13),
            'finale_date': date(2000, 11, 5),
            'about': 'ECW\'s annual November event.',
        },

        # =================================================================
        # AEW
        # =================================================================
        {
            'name': 'AEW Dynamite',
            'promotion': 'AEW',
            'show_type': 'weekly',
            'network': 'TBS',
            'air_day': 'Wednesday',
            'premiere_date': date(2019, 10, 2),
            'tmdb_id': 89770,
            'about': 'AEW\'s flagship weekly show on TBS.',
        },
        {
            'name': 'AEW Rampage',
            'promotion': 'AEW',
            'show_type': 'weekly',
            'network': 'TNT',
            'air_day': 'Friday',
            'premiere_date': date(2021, 8, 13),
            'tmdb_id': 130542,
            'about': 'AEW\'s secondary weekly show on TNT.',
        },
        {
            'name': 'AEW Collision',
            'promotion': 'AEW',
            'show_type': 'weekly',
            'network': 'TNT',
            'air_day': 'Saturday',
            'premiere_date': date(2023, 6, 17),
            'tmdb_id': 227367,
            'about': 'AEW\'s Saturday night show.',
        },
        {
            'name': 'AEW Dark',
            'promotion': 'AEW',
            'show_type': 'online',
            'network': 'YouTube',
            'air_day': 'Tuesday',
            'premiere_date': date(2019, 10, 15),
            'about': 'AEW\'s free YouTube show featuring developmental talent.',
        },
        {
            'name': 'AEW Dark: Elevation',
            'promotion': 'AEW',
            'show_type': 'online',
            'network': 'YouTube',
            'air_day': 'Monday',
            'premiere_date': date(2021, 3, 15),
            'about': 'AEW\'s second YouTube program.',
        },
        # AEW PPVs
        {
            'name': 'AEW All Out',
            'promotion': 'AEW',
            'show_type': 'ppv',
            'premiere_date': date(2019, 8, 31),
            'about': 'AEW\'s annual Labor Day weekend event.',
        },
        {
            'name': 'AEW Full Gear',
            'promotion': 'AEW',
            'show_type': 'ppv',
            'premiere_date': date(2019, 11, 9),
            'about': 'AEW\'s annual fall event.',
        },
        {
            'name': 'AEW Revolution',
            'promotion': 'AEW',
            'show_type': 'ppv',
            'premiere_date': date(2020, 2, 29),
            'about': 'AEW\'s annual winter event.',
        },
        {
            'name': 'AEW Double or Nothing',
            'promotion': 'AEW',
            'show_type': 'ppv',
            'premiere_date': date(2019, 5, 25),
            'about': 'AEW\'s annual Memorial Day weekend event.',
        },
        {
            'name': 'AEW Dynasty',
            'promotion': 'AEW',
            'show_type': 'ppv',
            'premiere_date': date(2024, 4, 21),
            'about': 'AEW\'s newest annual pay-per-view event.',
        },

        # =================================================================
        # TNA / Impact Wrestling
        # =================================================================
        {
            'name': 'Impact Wrestling',
            'promotion': 'TNA',
            'show_type': 'weekly',
            'network': 'AXS TV',
            'air_day': 'Thursday',
            'premiere_date': date(2004, 6, 4),
            'tmdb_id': 4431,
            'about': 'TNA/Impact Wrestling\'s flagship weekly show.',
        },
        {
            'name': 'TNA Xplosion',
            'promotion': 'TNA',
            'show_type': 'weekly',
            'premiere_date': date(2002, 10, 26),
            'about': 'TNA\'s secondary show featuring recaps and exclusive matches.',
        },
        # TNA PPVs
        {
            'name': 'TNA Bound for Glory',
            'promotion': 'TNA',
            'show_type': 'ppv',
            'premiere_date': date(2005, 10, 23),
            'about': 'TNA\'s biggest annual event, their WrestleMania.',
        },
        {
            'name': 'TNA Slammiversary',
            'promotion': 'TNA',
            'show_type': 'ppv',
            'premiere_date': date(2005, 6, 19),
            'about': 'TNA\'s anniversary celebration event.',
        },
        {
            'name': 'TNA Lockdown',
            'promotion': 'TNA',
            'show_type': 'ppv',
            'premiere_date': date(2005, 4, 24),
            'about': 'TNA\'s annual all-cage match event.',
        },

        # =================================================================
        # ROH (Ring of Honor)
        # =================================================================
        {
            'name': 'ROH TV',
            'promotion': 'ROH',
            'show_type': 'weekly',
            'premiere_date': date(2011, 9, 24),
            'about': 'Ring of Honor\'s weekly television program.',
        },
        {
            'name': 'ROH Final Battle',
            'promotion': 'ROH',
            'show_type': 'ppv',
            'premiere_date': date(2002, 12, 28),
            'about': 'ROH\'s annual year-end event.',
        },
        {
            'name': 'ROH Supercard of Honor',
            'promotion': 'ROH',
            'show_type': 'ppv',
            'premiere_date': date(2006, 3, 31),
            'about': 'ROH\'s WrestleMania weekend event.',
        },

        # =================================================================
        # NJPW (New Japan Pro Wrestling)
        # =================================================================
        {
            'name': 'NJPW World Tag League',
            'promotion': 'NJPW',
            'show_type': 'special',
            'premiere_date': date(2012, 11, 16),
            'about': 'NJPW\'s annual tag team tournament.',
        },
        {
            'name': 'NJPW G1 Climax',
            'promotion': 'NJPW',
            'show_type': 'special',
            'premiere_date': date(1991, 8, 8),
            'about': 'NJPW\'s prestigious annual tournament.',
        },
        {
            'name': 'NJPW Wrestle Kingdom',
            'promotion': 'NJPW',
            'show_type': 'ppv',
            'premiere_date': date(2007, 1, 4),
            'about': 'NJPW\'s biggest annual event, held at the Tokyo Dome.',
        },
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--promotion',
            type=str,
            help='Only seed shows for this promotion (e.g., WWE, AEW)',
        )
        parser.add_argument(
            '--type',
            type=str,
            choices=['weekly', 'ppv', 'special', 'online'],
            help='Only seed shows of this type',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )

    def handle(self, *args, **options):
        filter_promotion = options.get('promotion')
        filter_type = options.get('type')
        dry_run = options.get('dry_run', False)

        created = 0
        updated = 0
        skipped = 0

        for show_data in self.TV_SHOWS:
            # Apply filters
            promo_abbrev = show_data.get('promotion')
            show_type = show_data.get('show_type')

            if filter_promotion and promo_abbrev != filter_promotion:
                continue
            if filter_type and show_type != filter_type:
                continue

            # Find the promotion
            promotion = Promotion.objects.filter(abbreviation=promo_abbrev).first()
            if not promotion:
                # Try by name
                promotion = Promotion.objects.filter(name__icontains=promo_abbrev).first()

            if not promotion:
                self.stdout.write(
                    self.style.WARNING(
                        f"Promotion '{promo_abbrev}' not found, skipping {show_data['name']}"
                    )
                )
                skipped += 1
                continue

            # Prepare show data for creation/update
            defaults = {
                'promotion': promotion,
                'show_type': show_data.get('show_type', 'weekly'),
                'network': show_data.get('network'),
                'air_day': show_data.get('air_day'),
                'premiere_date': show_data.get('premiere_date'),
                'finale_date': show_data.get('finale_date'),
                'tmdb_id': show_data.get('tmdb_id'),
                'about': show_data.get('about'),
            }

            if dry_run:
                existing = TVShow.objects.filter(name=show_data['name']).exists()
                action = 'UPDATE' if existing else 'CREATE'
                self.stdout.write(f"[DRY-RUN] Would {action}: {show_data['name']}")
                continue

            # Create or update the show
            show, was_created = TVShow.objects.update_or_create(
                name=show_data['name'],
                defaults=defaults,
            )

            if was_created:
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"Created: {show.name}")
                )
            else:
                updated += 1
                self.stdout.write(f"Updated: {show.name}")

        # Summary
        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes made'))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'TV Shows seeded: {created} created, {updated} updated, {skipped} skipped'
                )
            )

        # Show counts by type
        if not dry_run:
            for show_type, label in TVShow.SHOW_TYPE_CHOICES:
                count = TVShow.objects.filter(show_type=show_type).count()
                self.stdout.write(f"  {label}: {count}")
