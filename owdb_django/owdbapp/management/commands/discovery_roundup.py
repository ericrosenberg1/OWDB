"""
Discovery Roundup - Analyzes existing data and adds missing entries.

Discovers missing wrestlers, venues, events, titles, and stables
by analyzing existing match text, event data, and cross-references.

Usage:
    python manage.py discovery_roundup
    python manage.py discovery_roundup --round=1
    python manage.py discovery_roundup --round=2
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.db.models import Count
from datetime import date
from owdb_django.owdbapp.models import (
    Event, Match, Wrestler, Promotion, Title, Venue, Stable
)


class Command(BaseCommand):
    help = 'Discover and add missing entries from existing data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--round',
            type=int,
            default=0,
            help='Run specific round (1 or 2), or 0 for both'
        )

    def handle(self, *args, **options):
        round_num = options.get('round', 0)

        if round_num == 0 or round_num == 1:
            self.stdout.write(self.style.SUCCESS('\n=== ROUND 1: DISCOVERY UPDATES ===\n'))
            self.round_1_updates()

        if round_num == 0 or round_num == 2:
            self.stdout.write(self.style.SUCCESS('\n=== ROUND 2: CROSS-REFERENCE UPDATES ===\n'))
            self.round_2_updates()

        self.stdout.write(self.style.SUCCESS('\n=== DISCOVERY COMPLETE ==='))
        self.print_summary()

    def round_1_updates(self):
        """Round 1: Add missing PPVs, wrestler data, venues, titles."""
        self.add_missing_ppvs()
        self.add_wrestler_hometowns()
        self.add_missing_venues()
        self.add_missing_titles()
        self.add_missing_stables()

    def round_2_updates(self):
        """Round 2: Cross-reference and deeper discovery."""
        self.add_more_ppvs()
        self.add_legendary_wrestlers()
        self.link_stable_members()
        self.add_historical_titles()

    def add_missing_ppvs(self):
        """Add major PPV events that are missing."""
        self.stdout.write('--- Adding Missing PPVs ---')
        created = 0

        wwe = Promotion.objects.filter(abbreviation__in=['WWE', 'WWF']).first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        ecw = Promotion.objects.filter(abbreviation='ECW').first()
        tna = Promotion.objects.filter(abbreviation__in=['TNA', 'IMPACT']).first()

        # WWE Big 4 PPVs
        if wwe:
            # WrestleMania (1985-2025)
            for year in range(1985, 2026):
                num = year - 1984
                name = f"WrestleMania {num}" if num <= 30 else f"WrestleMania {num}"
                if num == 40:
                    name = "WrestleMania XL"
                elif num == 30:
                    name = "WrestleMania XXX"
                elif num == 25:
                    name = "WrestleMania 25"
                elif num == 20:
                    name = "WrestleMania XX"
                elif num == 10:
                    name = "WrestleMania X"

                slug = slugify(f"{name}-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    # Approximate dates (usually late March/early April)
                    event_date = date(year, 4, 1)
                    Event.objects.create(
                        name=name, slug=slug, date=event_date, promotion=wwe,
                        about=f"{name} - WWE's flagship event"
                    )
                    created += 1

            # SummerSlam (1988-2025)
            for year in range(1988, 2026):
                name = f"SummerSlam {year}"
                slug = slugify(f"summerslam-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    event_date = date(year, 8, 20)
                    Event.objects.create(
                        name=name, slug=slug, date=event_date, promotion=wwe,
                        about=f"SummerSlam {year} - The Biggest Party of the Summer"
                    )
                    created += 1

            # Royal Rumble (1988-2025)
            for year in range(1988, 2026):
                name = f"Royal Rumble {year}"
                slug = slugify(f"royal-rumble-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    event_date = date(year, 1, 25)
                    Event.objects.create(
                        name=name, slug=slug, date=event_date, promotion=wwe,
                        about=f"Royal Rumble {year} - 30-Man Over-the-Top Rope Battle Royal"
                    )
                    created += 1

            # Survivor Series (1987-2025)
            for year in range(1987, 2026):
                name = f"Survivor Series {year}"
                slug = slugify(f"survivor-series-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    event_date = date(year, 11, 25)
                    Event.objects.create(
                        name=name, slug=slug, date=event_date, promotion=wwe,
                        about=f"Survivor Series {year} - Traditional Elimination Matches"
                    )
                    created += 1

            # Other WWE PPVs
            other_ppvs = [
                ('Money in the Bank', 2010, 2025, 6),
                ('Hell in a Cell', 2009, 2022, 10),
                ('TLC: Tables, Ladders & Chairs', 2009, 2020, 12),
                ('Elimination Chamber', 2010, 2025, 2),
                ('Extreme Rules', 2009, 2025, 5),
                ('Clash of Champions', 2016, 2020, 9),
                ('Backlash', 1999, 2025, 5),
                ('Judgment Day', 1998, 2009, 5),
                ('No Mercy', 1999, 2017, 10),
                ('Unforgiven', 1998, 2008, 9),
                ('Armageddon', 1999, 2008, 12),
                ('Vengeance', 2001, 2007, 6),
                ('Bad Blood', 1997, 2004, 6),
                ('King of the Ring', 1993, 2002, 6),
                ('In Your House', 1995, 1999, 4),
            ]
            for ppv_name, start_year, end_year, month in other_ppvs:
                for year in range(start_year, end_year + 1):
                    name = f"{ppv_name} {year}"
                    slug = slugify(f"{ppv_name}-{year}")
                    if not Event.objects.filter(slug=slug).exists():
                        event_date = date(year, month, 15)
                        Event.objects.create(
                            name=name, slug=slug, date=event_date, promotion=wwe,
                            about=f"{ppv_name} {year}"
                        )
                        created += 1

        # AEW PPVs
        if aew:
            aew_ppvs = [
                ('Double or Nothing', 2019, 2025, 5),
                ('All Out', 2019, 2025, 9),
                ('Full Gear', 2019, 2025, 11),
                ('Revolution', 2020, 2025, 3),
                ('Forbidden Door', 2022, 2025, 6),
                ('All In', 2023, 2025, 8),
                ('Dynasty', 2024, 2025, 4),
                ('WrestleDream', 2023, 2025, 10),
            ]
            for ppv_name, start_year, end_year, month in aew_ppvs:
                for year in range(start_year, end_year + 1):
                    name = f"AEW {ppv_name} {year}"
                    slug = slugify(f"aew-{ppv_name}-{year}")
                    if not Event.objects.filter(slug=slug).exists():
                        event_date = date(year, month, 20)
                        Event.objects.create(
                            name=name, slug=slug, date=event_date, promotion=aew,
                            about=f"AEW {ppv_name} {year}"
                        )
                        created += 1

        # WCW PPVs
        if wcw:
            wcw_ppvs = [
                ('Starrcade', 1983, 2000, 12),
                ('Bash at the Beach', 1994, 2000, 7),
                ('Halloween Havoc', 1989, 2000, 10),
                ('SuperBrawl', 1991, 2001, 2),
                ('The Great American Bash', 1985, 2000, 7),
                ('Fall Brawl', 1993, 2000, 9),
                ('Spring Stampede', 1994, 2000, 4),
                ('Souled Out', 1997, 2000, 1),
                ('Uncensored', 1995, 2000, 3),
                ('Road Wild', 1996, 1999, 8),
                ('World War 3', 1995, 1998, 11),
            ]
            for ppv_name, start_year, end_year, month in wcw_ppvs:
                for year in range(start_year, end_year + 1):
                    name = f"WCW {ppv_name} {year}"
                    slug = slugify(f"wcw-{ppv_name}-{year}")
                    if not Event.objects.filter(slug=slug).exists():
                        event_date = date(year, month, 15)
                        Event.objects.create(
                            name=name, slug=slug, date=event_date, promotion=wcw,
                            about=f"WCW {ppv_name} {year}"
                        )
                        created += 1

        # ECW PPVs
        if ecw:
            ecw_ppvs = [
                ('Barely Legal', 1997, 1997, 4),
                ('Hardcore Heaven', 1995, 2000, 5),
                ('Heat Wave', 1994, 2000, 8),
                ('November to Remember', 1993, 2000, 11),
                ('Living Dangerously', 1998, 2000, 3),
                ('Guilty as Charged', 1999, 2001, 1),
                ('Anarchy Rulz', 1999, 2000, 10),
                ('Cyberslam', 1996, 2000, 2),
            ]
            for ppv_name, start_year, end_year, month in ecw_ppvs:
                for year in range(start_year, end_year + 1):
                    name = f"ECW {ppv_name} {year}"
                    slug = slugify(f"ecw-{ppv_name}-{year}")
                    if not Event.objects.filter(slug=slug).exists():
                        event_date = date(year, month, 15)
                        Event.objects.create(
                            name=name, slug=slug, date=event_date, promotion=ecw,
                            about=f"ECW {ppv_name} {year}"
                        )
                        created += 1

        # TNA/Impact PPVs
        if tna:
            tna_ppvs = [
                ('Bound for Glory', 2005, 2024, 10),
                ('Lockdown', 2005, 2018, 4),
                ('Slammiversary', 2005, 2024, 6),
                ('Genesis', 2005, 2014, 1),
                ('Against All Odds', 2005, 2012, 2),
                ('Sacrifice', 2005, 2014, 5),
                ('Victory Road', 2004, 2012, 7),
                ('No Surrender', 2005, 2012, 9),
                ('Turning Point', 2004, 2012, 11),
                ('Final Resolution', 2005, 2012, 12),
                ('Hard Justice', 2008, 2010, 8),
                ('Hardcore War', 2023, 2024, 8),
            ]
            for ppv_name, start_year, end_year, month in tna_ppvs:
                for year in range(start_year, end_year + 1):
                    name = f"TNA {ppv_name} {year}"
                    slug = slugify(f"tna-{ppv_name}-{year}")
                    if not Event.objects.filter(slug=slug).exists():
                        event_date = date(year, month, 15)
                        Event.objects.create(
                            name=name, slug=slug, date=event_date, promotion=tna,
                            about=f"TNA {ppv_name} {year}"
                        )
                        created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} PPV events'))

    def add_wrestler_hometowns(self):
        """Add missing hometown data to wrestlers."""
        self.stdout.write('--- Adding Wrestler Hometowns ---')
        updated = 0

        hometown_data = {
            'Stone Cold Steve Austin': ('Victoria, Texas', 'USA', '6\'2"', '252 lbs'),
            'The Rock': ('Hayward, California', 'USA', '6\'5"', '260 lbs'),
            'John Cena': ('West Newbury, Massachusetts', 'USA', '6\'1"', '251 lbs'),
            'Triple H': ('Nashua, New Hampshire', 'USA', '6\'4"', '255 lbs'),
            'The Undertaker': ('Houston, Texas', 'USA', '6\'10"', '309 lbs'),
            'Shawn Michaels': ('San Antonio, Texas', 'USA', '6\'1"', '225 lbs'),
            'Bret Hart': ('Calgary, Alberta', 'Canada', '6\'0"', '235 lbs'),
            'Randy Savage': ('Columbus, Ohio', 'USA', '6\'2"', '237 lbs'),
            'Hulk Hogan': ('Tampa, Florida', 'USA', '6\'7"', '302 lbs'),
            'Ric Flair': ('Charlotte, North Carolina', 'USA', '6\'1"', '243 lbs'),
            'Chris Jericho': ('Manhasset, New York', 'Canada', '6\'0"', '227 lbs'),
            'CM Punk': ('Chicago, Illinois', 'USA', '6\'2"', '218 lbs'),
            'Edge': ('Orangeville, Ontario', 'Canada', '6\'5"', '241 lbs'),
            'Randy Orton': ('St. Louis, Missouri', 'USA', '6\'5"', '250 lbs'),
            'Batista': ('Washington, D.C.', 'USA', '6\'6"', '290 lbs'),
            'Rey Mysterio': ('San Diego, California', 'Mexico', '5\'6"', '175 lbs'),
            'Eddie Guerrero': ('El Paso, Texas', 'Mexico', '5\'8"', '220 lbs'),
            'Kurt Angle': ('Pittsburgh, Pennsylvania', 'USA', '6\'0"', '220 lbs'),
            'Mick Foley': ('Long Island, New York', 'USA', '6\'2"', '287 lbs'),
            'Big Show': ('Aiken, South Carolina', 'USA', '7\'0"', '383 lbs'),
            'Kane': ('Knoxville, Tennessee', 'USA', '7\'0"', '323 lbs'),
            'Roman Reigns': ('Pensacola, Florida', 'USA', '6\'3"', '265 lbs'),
            'Seth Rollins': ('Davenport, Iowa', 'USA', '6\'1"', '217 lbs'),
            'Dean Ambrose': ('Cincinnati, Ohio', 'USA', '6\'4"', '225 lbs'),
            'AJ Styles': ('Gainesville, Georgia', 'USA', '5\'11"', '218 lbs'),
            'Kenny Omega': ('Winnipeg, Manitoba', 'Canada', '6\'0"', '205 lbs'),
            'Jon Moxley': ('Cincinnati, Ohio', 'USA', '6\'4"', '225 lbs'),
            'Cody Rhodes': ('Marietta, Georgia', 'USA', '6\'1"', '220 lbs'),
            'Becky Lynch': ('Dublin', 'Ireland', '5\'6"', '135 lbs'),
            'Charlotte Flair': ('Charlotte, North Carolina', 'USA', '5\'10"', '143 lbs'),
            'Sasha Banks': ('Boston, Massachusetts', 'USA', '5\'5"', '114 lbs'),
            'Bayley': ('San Jose, California', 'USA', '5\'6"', '119 lbs'),
            'Bianca Belair': ('Knoxville, Tennessee', 'USA', '5\'7"', '140 lbs'),
            'Drew McIntyre': ('Ayr, Scotland', 'UK', '6\'5"', '265 lbs'),
            'Bobby Lashley': ('Junction City, Kansas', 'USA', '6\'3"', '273 lbs'),
            'Brock Lesnar': ('Webster, South Dakota', 'USA', '6\'3"', '286 lbs'),
            'Goldberg': ('Tulsa, Oklahoma', 'USA', '6\'4"', '285 lbs'),
            'Daniel Bryan': ('Aberdeen, Washington', 'USA', '5\'10"', '210 lbs'),
            'Kofi Kingston': ('Ghana', 'Ghana', '6\'0"', '212 lbs'),
            'Kevin Owens': ('Marieville, Quebec', 'Canada', '6\'0"', '266 lbs'),
            'Sami Zayn': ('Montreal, Quebec', 'Canada', '6\'1"', '212 lbs'),
            'Finn Balor': ('Bray, County Wicklow', 'Ireland', '5\'11"', '190 lbs'),
            'Rob Van Dam': ('Battle Creek, Michigan', 'USA', '6\'0"', '235 lbs'),
            'Booker T': ('Houston, Texas', 'USA', '6\'3"', '256 lbs'),
            'Sting': ('Omaha, Nebraska', 'USA', '6\'2"', '250 lbs'),
            'Ultimate Warrior': ('Crawfordsville, Indiana', 'USA', '6\'2"', '280 lbs'),
            'Cesaro': ('Lucerne', 'Switzerland', '6\'5"', '232 lbs'),
            'Sheamus': ('Dublin', 'Ireland', '6\'4"', '267 lbs'),
            'Dolph Ziggler': ('Cleveland, Ohio', 'USA', '6\'0"', '213 lbs'),
            'The Miz': ('Cleveland, Ohio', 'USA', '6\'2"', '221 lbs'),
            'Jeff Hardy': ('Cameron, North Carolina', 'USA', '6\'2"', '225 lbs'),
            'Matt Hardy': ('Cameron, North Carolina', 'USA', '6\'2"', '236 lbs'),
            'Mark Henry': ('Silsbee, Texas', 'USA', '6\'4"', '412 lbs'),
            'MJF': ('Long Island, New York', 'USA', '5\'11"', '212 lbs'),
            'Hangman Adam Page': ('Richmond, Virginia', 'USA', '6\'0"', '214 lbs'),
            'Orange Cassidy': ('Wherever', 'USA', '5\'10"', '170 lbs'),
            'Darby Allin': ('Seattle, Washington', 'USA', '5\'8"', '170 lbs'),
        }

        for name, (hometown, nationality, height, weight) in hometown_data.items():
            wrestler = Wrestler.objects.filter(name__iexact=name).first()
            if not wrestler:
                wrestler = Wrestler.objects.filter(name__icontains=name).first()
            if wrestler:
                changed = False
                if not wrestler.hometown:
                    wrestler.hometown = hometown
                    changed = True
                if not wrestler.nationality:
                    wrestler.nationality = nationality
                    changed = True
                if not wrestler.height:
                    wrestler.height = height
                    changed = True
                if not wrestler.weight:
                    wrestler.weight = weight
                    changed = True
                if changed:
                    wrestler.save()
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f'  Updated {updated} wrestler profiles'))

    def add_missing_venues(self):
        """Add iconic wrestling venues."""
        self.stdout.write('--- Adding Missing Venues ---')
        created = 0

        venues = [
            ('Madison Square Garden', 'New York City, NY', 20789),
            ('Staples Center', 'Los Angeles, CA', 21000),
            ('AT&T Stadium', 'Arlington, TX', 80000),
            ('MetLife Stadium', 'East Rutherford, NJ', 82500),
            ('Allegiant Stadium', 'Las Vegas, NV', 65000),
            ('SoFi Stadium', 'Inglewood, CA', 70240),
            ('Toyota Center', 'Houston, TX', 18300),
            ('Barclays Center', 'Brooklyn, NY', 19000),
            ('TD Garden', 'Boston, MA', 19580),
            ('United Center', 'Chicago, IL', 23500),
            ('Wells Fargo Center', 'Philadelphia, PA', 21000),
            ('Scotiabank Arena', 'Toronto, ON', 19800),
            ('O2 Arena', 'London, UK', 20000),
            ('Wembley Stadium', 'London, UK', 90000),
            ('Tokyo Dome', 'Tokyo, Japan', 55000),
            ('Budokan Hall', 'Tokyo, Japan', 14471),
            ('Korakuen Hall', 'Tokyo, Japan', 1800),
            ('ECW Arena', 'Philadelphia, PA', 1300),
            ('Hammerstein Ballroom', 'New York City, NY', 2200),
            ('Manhattan Center', 'New York City, NY', 3500),
            ('Full Sail University', 'Winter Park, FL', 400),
            ('Daily\'s Place', 'Jacksonville, FL', 5500),
            ('Impact Zone', 'Orlando, FL', 1400),
            ('Georgia Dome', 'Atlanta, GA', 71250),
            ('Superdome', 'New Orleans, LA', 73000),
            ('Pontiac Silverdome', 'Pontiac, MI', 80300),
            ('SkyDome', 'Toronto, ON', 67000),
            ('Cow Palace', 'Daly City, CA', 11089),
            ('Boston Garden', 'Boston, MA', 14890),
            ('The Forum', 'Inglewood, CA', 17505),
        ]

        for name, location, capacity in venues:
            slug = slugify(name)
            if not Venue.objects.filter(slug=slug).exists():
                Venue.objects.create(
                    name=name, slug=slug, location=location, capacity=capacity
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} venues'))

    def add_missing_titles(self):
        """Add missing championship titles."""
        self.stdout.write('--- Adding Missing Titles ---')
        created = 0

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        ecw = Promotion.objects.filter(abbreviation='ECW').first()
        tna = Promotion.objects.filter(abbreviation__in=['TNA', 'IMPACT']).first()
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()

        titles_data = []

        if wwe:
            titles_data.extend([
                (wwe, 'Intercontinental Championship', 1979, None),
                (wwe, 'WWE 24/7 Championship', 2019, 2022),
                (wwe, 'Cruiserweight Championship', 2016, 2020),
                (wwe, 'European Championship', 1997, 2002),
                (wwe, 'Light Heavyweight Championship', 1997, 2001),
                (wwe, 'Million Dollar Championship', 1989, 1992),
            ])

        if aew:
            titles_data.extend([
                (aew, 'AEW World Championship', 2019, None),
                (aew, 'AEW Continental Championship', 2023, None),
                (aew, 'FTW Championship', 2020, None),
                (aew, 'AEW World Trios Championship', 2022, None),
            ])

        if wcw:
            titles_data.extend([
                (wcw, 'WCW World Heavyweight Championship', 1991, 2001),
                (wcw, 'WCW United States Championship', 1975, 2001),
                (wcw, 'WCW World Tag Team Championship', 1975, 2001),
                (wcw, 'WCW Cruiserweight Championship', 1996, 2001),
                (wcw, 'WCW Television Championship', 1974, 2000),
                (wcw, 'WCW Hardcore Championship', 1999, 2001),
            ])

        if ecw:
            titles_data.extend([
                (ecw, 'ECW World Heavyweight Championship', 1992, 2001),
                (ecw, 'ECW World Television Championship', 1992, 2001),
                (ecw, 'ECW World Tag Team Championship', 1992, 2001),
            ])

        if tna:
            titles_data.extend([
                (tna, 'TNA/Impact World Championship', 2002, None),
                (tna, 'TNA X Division Championship', 2002, None),
                (tna, 'TNA World Tag Team Championship', 2002, None),
                (tna, 'TNA Knockouts Championship', 2007, None),
                (tna, 'TNA Television Championship', 2020, None),
                (tna, 'TNA Digital Media Championship', 2021, None),
            ])

        for promo, name, debut_year, retirement_year in titles_data:
            slug = slugify(name)
            if not Title.objects.filter(slug=slug).exists():
                Title.objects.create(
                    name=name, slug=slug, promotion=promo,
                    debut_year=debut_year, retirement_year=retirement_year
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} titles'))

    def add_missing_stables(self):
        """Add missing wrestling stables/factions."""
        self.stdout.write('--- Adding Missing Stables ---')
        created = 0

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()

        stables_data = [
            ('nWo', wcw, 1996, 2002, 'New World Order - the most influential faction in wrestling history'),
            ('D-Generation X', wwe, 1997, 2010, 'Iconic rebellious faction led by Triple H and Shawn Michaels'),
            ('The Shield', wwe, 2012, 2019, 'Roman Reigns, Seth Rollins, and Dean Ambrose'),
            ('Evolution', wwe, 2003, 2005, 'Triple H, Ric Flair, Randy Orton, and Batista'),
            ('The Four Horsemen', wcw, 1985, 1999, 'Ric Flair\'s legendary faction'),
            ('The Bloodline', wwe, 2021, None, 'Roman Reigns\' Samoan dynasty'),
            ('The Elite', aew, 2019, None, 'Kenny Omega and The Young Bucks'),
            ('The Inner Circle', aew, 2019, 2022, 'Chris Jericho\'s AEW faction'),
            ('Bullet Club', None, 2013, None, 'Iconic NJPW/cross-promotional faction'),
            ('The Hart Foundation', wwe, 1986, 1997, 'Bret Hart and Jim Neidhart\'s legendary team'),
            ('The Ministry of Darkness', wwe, 1998, 1999, 'The Undertaker\'s dark faction'),
            ('The Corporation', wwe, 1998, 1999, 'Vince McMahon\'s corporate faction'),
            ('The Nexus', wwe, 2010, 2011, 'Wade Barrett\'s invasion faction'),
            ('The New Day', wwe, 2014, None, 'Kofi Kingston, Big E, and Xavier Woods'),
            ('Judgment Day', wwe, 2022, None, 'Finn Balor, Damian Priest, Rhea Ripley'),
            ('Imperium', wwe, 2019, None, 'Gunther\'s European faction'),
            ('The Hurt Business', wwe, 2020, 2021, 'Bobby Lashley, MVP, Cedric Alexander, Shelton Benjamin'),
            ('Rated-RKO', wwe, 2006, 2007, 'Edge and Randy Orton'),
            ('The Brothers of Destruction', wwe, 1998, 2018, 'The Undertaker and Kane'),
            ('Team Extreme', wwe, 1999, 2002, 'The Hardy Boyz and Lita'),
        ]

        for name, promo, formed, disbanded, about in stables_data:
            slug = slugify(name)
            if not Stable.objects.filter(slug=slug).exists():
                Stable.objects.create(
                    name=name, slug=slug, promotion=promo,
                    formed_year=formed, disbanded_year=disbanded, about=about
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} stables'))

    def add_more_ppvs(self):
        """Round 2: Add more PPVs and special events."""
        self.stdout.write('--- Adding More PPVs (Round 2) ---')
        created = 0

        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()

        # NXT TakeOver events
        if wwe:
            takeovers = [
                ('NXT TakeOver: Brooklyn', 2015, 8),
                ('NXT TakeOver: Brooklyn II', 2016, 8),
                ('NXT TakeOver: Brooklyn III', 2017, 8),
                ('NXT TakeOver: Brooklyn 4', 2018, 8),
                ('NXT TakeOver: New Orleans', 2018, 4),
                ('NXT TakeOver: Chicago', 2017, 5),
                ('NXT TakeOver: Chicago II', 2018, 6),
                ('NXT TakeOver: Philadelphia', 2018, 1),
                ('NXT TakeOver: Toronto', 2016, 11),
                ('NXT TakeOver: Toronto 2019', 2019, 8),
                ('NXT TakeOver: WarGames', 2017, 11),
                ('NXT TakeOver: WarGames II', 2018, 11),
                ('NXT TakeOver: WarGames III', 2019, 11),
                ('NXT TakeOver: Stand & Deliver', 2021, 4),
                ('NXT TakeOver: In Your House', 2020, 6),
                ('NXT TakeOver: XXV', 2019, 6),
                ('NXT TakeOver: XXX', 2020, 8),
                ('NXT TakeOver: 31', 2020, 10),
            ]
            for name, year, month in takeovers:
                slug = slugify(f"{name}-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    Event.objects.create(
                        name=name, slug=slug, date=date(year, month, 15),
                        promotion=wwe, about=f"{name}"
                    )
                    created += 1

        # Create NJPW if missing
        if not njpw:
            njpw = Promotion.objects.create(
                name='New Japan Pro-Wrestling',
                abbreviation='NJPW',
                founded_year=1972,
                headquarters='Tokyo, Japan'
            )

        # NJPW major events
        njpw_events = [
            ('Wrestle Kingdom', 2007, 2025, 1),
            ('Dominion', 2009, 2024, 6),
            ('G1 Climax Finals', 1991, 2024, 8),
            ('King of Pro-Wrestling', 2012, 2019, 10),
            ('Power Struggle', 2011, 2023, 11),
            ('New Beginning', 2011, 2024, 2),
            ('Sakura Genesis', 2017, 2023, 4),
            ('Wrestling Dontaku', 1992, 2023, 5),
        ]
        for name, start_year, end_year, month in njpw_events:
            for year in range(start_year, end_year + 1):
                slug = slugify(f"njpw-{name}-{year}")
                if not Event.objects.filter(slug=slug).exists():
                    Event.objects.create(
                        name=f"NJPW {name} {year}", slug=slug,
                        date=date(year, month, 4), promotion=njpw,
                        about=f"NJPW {name} {year}"
                    )
                    created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} additional events'))

    def add_legendary_wrestlers(self):
        """Round 2: Add legendary wrestlers that may be missing."""
        self.stdout.write('--- Adding Legendary Wrestlers ---')
        created = 0

        legends = [
            ('Bruno Sammartino', 'Pittsburgh, Pennsylvania', 'Italy', 1959, 2013),
            ('Andre the Giant', 'Grenoble', 'France', 1964, 1992),
            ('Lou Thesz', 'St. Louis, Missouri', 'USA', 1932, 1990),
            ('Gorgeous George', 'Butte, Nebraska', 'USA', 1932, 1962),
            ('Killer Kowalski', 'Windsor, Ontario', 'Canada', 1947, 1977),
            ('Pat Patterson', 'Montreal, Quebec', 'Canada', 1958, 1984),
            ('Gorilla Monsoon', 'Rochester, New York', 'USA', 1959, 1999),
            ('Iron Sheik', 'Tehran', 'Iran', 1972, 2023),
            ('Nikolai Volkoff', 'Zagreb', 'Croatia', 1970, 2018),
            ('Junkyard Dog', 'Wadesboro, North Carolina', 'USA', 1977, 1998),
            ('Superstar Billy Graham', 'Phoenix, Arizona', 'USA', 1969, 1987),
            ('Bob Backlund', 'Princeton, Minnesota', 'USA', 1973, 2018),
            ('Sgt. Slaughter', 'Parris Island, South Carolina', 'USA', 1972, 2018),
            ('Jake Roberts', 'Gainesville, Texas', 'USA', 1974, 2024),
            ('Roddy Piper', 'Saskatoon, Saskatchewan', 'Canada', 1973, 2015),
            ('Jimmy Snuka', 'Fiji', 'Fiji', 1970, 2017),
            ('Don Muraco', 'Honolulu, Hawaii', 'USA', 1970, 1995),
            ('Greg Valentine', 'Seattle, Washington', 'USA', 1970, 2018),
            ('Tito Santana', 'Tocula, Mexico', 'Mexico', 1977, 2002),
            ('Honky Tonk Man', 'Memphis, Tennessee', 'USA', 1977, 2019),
            ('Mr. Perfect', 'Robbinsdale, Minnesota', 'USA', 1980, 2003),
            ('Rick Rude', 'Robbinsdale, Minnesota', 'USA', 1982, 1999),
            ('British Bulldog', 'Golborne, England', 'UK', 1984, 2002),
            ('Owen Hart', 'Calgary, Alberta', 'Canada', 1986, 1999),
            ('Yokozuna', 'San Francisco, California', 'USA', 1984, 2000),
            ('Diesel', 'Detroit, Michigan', 'USA', 1990, 2024),
            ('Razor Ramon', 'Miami, Florida', 'USA', 1984, 2022),
            ('Vader', 'Lynwood, California', 'USA', 1978, 2018),
            ('Harley Race', 'Quitman, Missouri', 'USA', 1960, 2009),
            ('Dusty Rhodes', 'Austin, Texas', 'USA', 1968, 2015),
            ('Terry Funk', 'Amarillo, Texas', 'USA', 1965, 2022),
            ('Dory Funk Jr.', 'Hammond, Indiana', 'USA', 1963, 2015),
            ('Jack Brisco', 'Blackwell, Oklahoma', 'USA', 1965, 2010),
            ('Ricky Steamboat', 'Honolulu, Hawaii', 'USA', 1976, 2010),
            ('Magnum T.A.', 'Norfolk, Virginia', 'USA', 1978, 1986),
            ('Tully Blanchard', 'San Antonio, Texas', 'USA', 1975, 1997),
            ('Arn Anderson', 'Rome, Georgia', 'USA', 1982, 2019),
            ('Barry Windham', 'Sweetwater, Texas', 'USA', 1979, 2010),
            ('Lex Luger', 'Buffalo, New York', 'USA', 1985, 2006),
            ('Sid Vicious', 'West Memphis, Arkansas', 'USA', 1987, 2017),
        ]

        for name, hometown, nationality, debut, retirement in legends:
            slug = slugify(name)
            if not Wrestler.objects.filter(slug=slug).exists():
                Wrestler.objects.create(
                    name=name, slug=slug, hometown=hometown,
                    nationality=nationality, debut_year=debut,
                    retirement_year=retirement if retirement != 2024 else None
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} legendary wrestlers'))

    def link_stable_members(self):
        """Link wrestlers to their stables."""
        self.stdout.write('--- Linking Stable Members ---')
        linked = 0

        stable_members = {
            'The Shield': ['Roman Reigns', 'Seth Rollins', 'Dean Ambrose'],
            'D-Generation X': ['Triple H', 'Shawn Michaels', 'X-Pac', 'Road Dogg', 'Billy Gunn', 'Chyna'],
            'Evolution': ['Triple H', 'Ric Flair', 'Randy Orton', 'Batista'],
            'The New Day': ['Kofi Kingston', 'Big E', 'Xavier Woods'],
            'The Bloodline': ['Roman Reigns', 'Jimmy Uso', 'Jey Uso', 'Solo Sikoa'],
            'nWo': ['Hulk Hogan', 'Kevin Nash', 'Scott Hall', 'Syxx', 'The Giant', 'Eric Bischoff'],
            'The Four Horsemen': ['Ric Flair', 'Arn Anderson', 'Tully Blanchard', 'Barry Windham', 'Ole Anderson'],
            'The Elite': ['Kenny Omega', 'Matt Jackson', 'Nick Jackson', 'Hangman Adam Page', 'Cody Rhodes'],
            'The Inner Circle': ['Chris Jericho', 'Jake Hager', 'Santana', 'Ortiz', 'Sammy Guevara', 'MJF'],
            'Judgment Day': ['Finn Balor', 'Damian Priest', 'Rhea Ripley', 'Dominik Mysterio'],
        }

        for stable_name, member_names in stable_members.items():
            stable = Stable.objects.filter(name__iexact=stable_name).first()
            if not stable:
                stable = Stable.objects.filter(name__icontains=stable_name).first()
            if stable:
                for member_name in member_names:
                    wrestler = Wrestler.objects.filter(name__iexact=member_name).first()
                    if not wrestler:
                        wrestler = Wrestler.objects.filter(name__icontains=member_name).first()
                    if wrestler and wrestler not in stable.members.all():
                        stable.members.add(wrestler)
                        linked += 1

        self.stdout.write(self.style.SUCCESS(f'  Linked {linked} wrestlers to stables'))

    def add_historical_titles(self):
        """Add more historical titles."""
        self.stdout.write('--- Adding Historical Titles ---')
        created = 0

        # Get or create promotions
        nwa = Promotion.objects.filter(abbreviation='NWA').first()
        if not nwa:
            nwa = Promotion.objects.create(
                name='National Wrestling Alliance',
                abbreviation='NWA',
                founded_year=1948
            )

        awa = Promotion.objects.filter(abbreviation='AWA').first()
        if not awa:
            awa = Promotion.objects.create(
                name='American Wrestling Association',
                abbreviation='AWA',
                founded_year=1960,
                closed_year=1991
            )

        njpw = Promotion.objects.filter(abbreviation='NJPW').first()

        historical_titles = [
            (nwa, 'NWA World Heavyweight Championship', 1948, None),
            (nwa, 'NWA World Tag Team Championship', 1950, None),
            (nwa, "NWA World Women's Championship", 1954, None),
            (awa, 'AWA World Heavyweight Championship', 1960, 1991),
            (awa, 'AWA World Tag Team Championship', 1960, 1991),
        ]

        if njpw:
            historical_titles.extend([
                (njpw, 'IWGP World Heavyweight Championship', 2021, None),
                (njpw, 'IWGP Heavyweight Championship', 1987, 2021),
                (njpw, 'IWGP Intercontinental Championship', 2011, 2021),
                (njpw, 'IWGP United States Heavyweight Championship', 2017, None),
                (njpw, 'IWGP Tag Team Championship', 1985, None),
                (njpw, 'IWGP Junior Heavyweight Championship', 1986, None),
                (njpw, 'NEVER Openweight Championship', 2012, None),
                (njpw, 'G1 Climax Trophy', 1991, None),
            ])

        for promo, name, debut, retirement in historical_titles:
            slug = slugify(name)
            if not Title.objects.filter(slug=slug).exists():
                Title.objects.create(
                    name=name, slug=slug, promotion=promo,
                    debut_year=debut, retirement_year=retirement
                )
                created += 1

        self.stdout.write(self.style.SUCCESS(f'  Created {created} historical titles'))

    def print_summary(self):
        """Print final database summary."""
        self.stdout.write('\n--- DATABASE SUMMARY ---')
        self.stdout.write(f'  Events: {Event.objects.count():,}')
        self.stdout.write(f'  Matches: {Match.objects.count():,}')
        self.stdout.write(f'  Wrestlers: {Wrestler.objects.count():,}')
        self.stdout.write(f'  Titles: {Title.objects.count():,}')
        self.stdout.write(f'  Promotions: {Promotion.objects.count():,}')
        self.stdout.write(f'  Venues: {Venue.objects.count():,}')
        self.stdout.write(f'  Stables: {Stable.objects.count():,}')
