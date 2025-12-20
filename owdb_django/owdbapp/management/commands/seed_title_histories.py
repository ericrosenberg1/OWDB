"""
Seed title histories with championship reigns.

Usage:
    python manage.py seed_title_histories
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Title, Wrestler, Promotion, TitleReign
)


class Command(BaseCommand):
    help = 'Seed title histories with championship reigns'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Title Histories ===\n'))

        self.ensure_titles()
        self.seed_wwe_championship_history()
        self.seed_wwf_intercontinental_history()
        self.seed_wcw_world_title_history()
        self.seed_ecw_world_title_history()
        self.seed_nwa_world_title_history()
        self.seed_iwgp_heavyweight_history()
        self.seed_aew_world_title_history()
        self.seed_tna_world_title_history()

        # Print stats
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ==='))
        self.stdout.write(f'Total Titles: {Title.objects.count()}')
        self.stdout.write(f'Total Reigns: {TitleReign.objects.count()}')

    def ensure_titles(self):
        """Ensure required titles exist."""
        titles = [
            {'name': 'WWE Championship', 'abbreviation': 'WWE'},
            {'name': 'WWF Championship', 'abbreviation': 'WWF'},
            {'name': 'WWF Intercontinental Championship', 'abbreviation': 'WWF'},
            {'name': 'WCW World Heavyweight Championship', 'abbreviation': 'WCW'},
            {'name': 'ECW World Heavyweight Championship', 'abbreviation': 'ECW'},
            {'name': 'NWA World Heavyweight Championship', 'abbreviation': 'NWA'},
            {'name': 'IWGP Heavyweight Championship', 'abbreviation': 'NJPW'},
            {'name': 'AEW World Championship', 'abbreviation': 'AEW'},
            {'name': 'TNA World Heavyweight Championship', 'abbreviation': 'TNA'},
        ]
        for t in titles:
            existing = Title.objects.filter(name=t['name']).first()
            if not existing:
                promotion = Promotion.objects.filter(abbreviation=t['abbreviation']).first()
                Title.objects.create(name=t['name'], promotion=promotion)
                self.stdout.write(f'  + Created title: {t["name"]}')

    def get_or_create_wrestler(self, name, **kwargs):
        """Get or create a wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(name=name, **kwargs)
            self.stdout.write(f'  + Created wrestler: {name}')
        return wrestler

    def add_reign(self, title_name, wrestler_name, start_date, end_date=None, reign_number=None, notes=None):
        """Add a title reign."""
        title = Title.objects.filter(name__icontains=title_name).first()
        if not title:
            self.stdout.write(self.style.WARNING(f'  ! Title not found: {title_name}'))
            return None

        wrestler = self.get_or_create_wrestler(wrestler_name)

        # Check if reign already exists
        existing = TitleReign.objects.filter(
            title=title,
            wrestler=wrestler,
            start_date=start_date
        ).first()
        if existing:
            return existing

        reign = TitleReign.objects.create(
            title=title,
            wrestler=wrestler,
            start_date=start_date,
            end_date=end_date,
            reign_number=reign_number,
            notes=notes
        )
        return reign

    def seed_wwe_championship_history(self):
        """Seed WWE Championship history."""
        self.stdout.write('\n--- Seeding WWE Championship History ---\n')

        reigns = [
            # Modern era WWE Championship
            ('WWE Championship', 'John Cena', date(2005, 4, 3), date(2006, 1, 8), 1, 'Won at WrestleMania 21'),
            ('WWE Championship', 'Edge', date(2006, 1, 8), date(2006, 1, 29), 1, 'Cashed in Money in the Bank'),
            ('WWE Championship', 'John Cena', date(2006, 1, 29), date(2006, 6, 11), 2, 'Royal Rumble 2006'),
            ('WWE Championship', 'Rob Van Dam', date(2006, 6, 11), date(2006, 7, 3), 1, 'ECW One Night Stand'),
            ('WWE Championship', 'Edge', date(2006, 7, 3), date(2006, 9, 17), 2, 'Raw'),
            ('WWE Championship', 'John Cena', date(2006, 9, 17), date(2007, 10, 7), 3, 'Unforgiven 2006'),
            ('WWE Championship', 'Randy Orton', date(2007, 10, 7), date(2007, 10, 29), 1, 'No Mercy - Cena vacated due to injury'),
            ('WWE Championship', 'Triple H', date(2007, 10, 29), date(2008, 4, 27), 5, 'No Mercy rematch'),
            ('WWE Championship', 'Randy Orton', date(2008, 4, 27), date(2008, 6, 29), 2, 'Backlash 2008'),
            ('WWE Championship', 'Triple H', date(2008, 6, 29), date(2008, 11, 23), 6, 'Night of Champions 2008'),
            ('WWE Championship', 'Edge', date(2008, 11, 23), date(2009, 2, 15), 3, 'Survivor Series 2008'),
            ('WWE Championship', 'Jeff Hardy', date(2009, 2, 15), date(2009, 4, 5), 1, 'No Way Out 2009'),
            ('WWE Championship', 'Edge', date(2009, 4, 5), date(2009, 4, 26), 4, 'WrestleMania 25'),
            ('WWE Championship', 'John Cena', date(2009, 4, 26), date(2009, 6, 28), 4, 'Backlash 2009'),
            ('WWE Championship', 'Randy Orton', date(2009, 6, 28), date(2009, 10, 4), 3, 'The Bash 2009'),
            ('WWE Championship', 'John Cena', date(2009, 10, 4), date(2009, 10, 25), 5, 'Breaking Point 2009'),
            ('WWE Championship', 'Randy Orton', date(2009, 10, 25), date(2010, 1, 31), 4, 'Hell in a Cell 2009'),
            ('WWE Championship', 'Sheamus', date(2009, 12, 13), date(2010, 2, 21), 1, 'TLC 2009 - First Irish WWE Champion'),
            ('WWE Championship', 'John Cena', date(2010, 2, 21), date(2010, 5, 23), 6, 'Elimination Chamber 2010'),
            ('WWE Championship', 'Batista', date(2010, 5, 23), date(2010, 6, 20), 2, 'Over the Limit 2010'),
            ('WWE Championship', 'John Cena', date(2010, 6, 20), date(2010, 9, 19), 7, 'Fatal 4-Way 2010'),
            ('WWE Championship', 'Sheamus', date(2010, 9, 19), date(2010, 11, 22), 2, 'Night of Champions 2010'),
            ('WWE Championship', 'Randy Orton', date(2010, 11, 22), date(2010, 12, 13), 5, 'Survivor Series 2010'),
            ('WWE Championship', 'The Miz', date(2010, 11, 22), date(2011, 5, 1), 1, 'Raw - Cashed in MITB on Orton'),
            ('WWE Championship', 'John Cena', date(2011, 5, 1), date(2011, 7, 17), 8, 'Extreme Rules 2011'),
            ('WWE Championship', 'CM Punk', date(2011, 7, 17), date(2011, 7, 25), 1, 'Money in the Bank 2011 - Classic match in Chicago'),
            ('WWE Championship', 'Rey Mysterio', date(2011, 7, 25), date(2011, 7, 25), 1, 'Raw tournament'),
            ('WWE Championship', 'John Cena', date(2011, 7, 25), date(2011, 8, 14), 9, 'Beat Rey same night'),
            ('WWE Championship', 'CM Punk', date(2011, 8, 14), date(2011, 11, 20), 2, 'SummerSlam 2011 - Unification with Cena\'s title'),
            ('WWE Championship', 'Alberto Del Rio', date(2011, 8, 14), date(2011, 10, 2), 1, 'SummerSlam - Cashed in on Punk'),
            ('WWE Championship', 'John Cena', date(2011, 10, 2), date(2011, 10, 2), 10, 'Hell in a Cell 2011'),
            ('WWE Championship', 'Alberto Del Rio', date(2011, 10, 2), date(2011, 11, 20), 2, 'Hell in a Cell 2011 - Same night'),
            ('WWE Championship', 'CM Punk', date(2011, 11, 20), date(2013, 1, 27), 3, 'Survivor Series 2011 - 434 day reign'),
            ('WWE Championship', 'The Rock', date(2013, 1, 27), date(2013, 2, 17), 1, 'Royal Rumble 2013 - Once in a lifetime rematch'),
            ('WWE Championship', 'John Cena', date(2013, 4, 7), date(2013, 5, 19), 11, 'WrestleMania 29'),
            ('WWE Championship', 'Daniel Bryan', date(2013, 8, 18), date(2013, 8, 18), 1, 'SummerSlam 2013 - Lost to Orton same night'),
            ('WWE Championship', 'Randy Orton', date(2013, 8, 18), date(2014, 4, 6), 6, 'Cash in by HHH referee'),
            ('WWE Championship', 'Daniel Bryan', date(2014, 4, 6), date(2014, 6, 9), 2, 'WrestleMania XXX - YES moment'),
            ('WWE Championship', 'Brock Lesnar', date(2014, 8, 17), date(2015, 3, 29), 1, 'SummerSlam 2014'),
            ('WWE Championship', 'Seth Rollins', date(2015, 3, 29), date(2015, 11, 4), 1, 'WrestleMania 31 Heist'),
            ('WWE Championship', 'Roman Reigns', date(2015, 11, 22), date(2015, 12, 14), 1, 'Survivor Series 2015'),
            ('WWE Championship', 'Sheamus', date(2015, 11, 22), date(2015, 12, 14), 3, 'Cashed in same night'),
            ('WWE Championship', 'Roman Reigns', date(2015, 12, 14), date(2016, 1, 24), 2, 'TLC 2015'),
            ('WWE Championship', 'Triple H', date(2016, 1, 24), date(2016, 4, 3), 7, 'Royal Rumble 2016'),
            ('WWE Championship', 'Roman Reigns', date(2016, 4, 3), date(2016, 6, 19), 3, 'WrestleMania 32'),
            ('WWE Championship', 'Seth Rollins', date(2016, 6, 19), date(2016, 7, 24), 2, 'Money in the Bank 2016'),
            ('WWE Championship', 'Dean Ambrose', date(2016, 6, 19), date(2016, 7, 24), 1, 'Same night cash in on Rollins'),
            ('WWE Championship', 'AJ Styles', date(2016, 9, 11), date(2017, 2, 12), 1, 'Backlash 2016 - 140 days'),
            ('WWE Championship', 'Bray Wyatt', date(2017, 2, 12), date(2017, 4, 2), 1, 'Elimination Chamber 2017'),
            ('WWE Championship', 'Randy Orton', date(2017, 4, 2), date(2017, 6, 18), 7, 'WrestleMania 33'),
            ('WWE Championship', 'Jinder Mahal', date(2017, 5, 21), date(2017, 11, 7), 1, 'Backlash 2017'),
            ('WWE Championship', 'AJ Styles', date(2017, 11, 7), date(2018, 11, 13), 2, 'SmackDown - 371 days'),
            ('WWE Championship', 'Daniel Bryan', date(2018, 11, 13), date(2019, 1, 27), 3, 'SmackDown'),
            ('WWE Championship', 'Kofi Kingston', date(2019, 4, 7), date(2019, 10, 4), 1, 'WrestleMania 35 - First African-born champion'),
            ('WWE Championship', 'Brock Lesnar', date(2019, 10, 4), date(2020, 4, 5), 2, 'SmackDown'),
            ('WWE Championship', 'Drew McIntyre', date(2020, 4, 5), date(2020, 11, 16), 1, 'WrestleMania 36'),
            ('WWE Championship', 'Randy Orton', date(2020, 10, 25), date(2020, 11, 16), 8, 'Hell in a Cell 2020'),
            ('WWE Championship', 'Drew McIntyre', date(2020, 11, 16), date(2021, 2, 21), 2, 'Raw'),
            ('WWE Championship', 'Bobby Lashley', date(2021, 3, 1), date(2021, 10, 25), 1, 'Raw - First reign'),
            ('WWE Championship', 'Big E', date(2021, 9, 13), date(2022, 1, 1), 1, 'Raw - Cashed in MITB'),
            ('WWE Championship', 'Brock Lesnar', date(2022, 1, 1), date(2022, 1, 29), 3, 'Day 1'),
            ('WWE Championship', 'Bobby Lashley', date(2022, 1, 29), date(2022, 3, 5), 2, 'Royal Rumble 2022'),
            ('WWE Championship', 'Brock Lesnar', date(2022, 3, 5), date(2022, 4, 3), 4, 'Elimination Chamber 2022'),
            ('WWE Championship', 'Roman Reigns', date(2022, 4, 3), None, 4, 'WrestleMania 38 - Unified WWE and Universal Championships'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added WWE Championship reigns')

    def seed_wwf_intercontinental_history(self):
        """Seed WWF/WWE Intercontinental Championship history."""
        self.stdout.write('\n--- Seeding Intercontinental Championship History ---\n')

        reigns = [
            # Classic IC Champions
            ('Intercontinental', 'Pat Patterson', date(1979, 9, 1), date(1980, 4, 21), 1, 'Inaugural champion'),
            ('Intercontinental', 'Ken Patera', date(1980, 4, 21), date(1980, 8, 9), 1, None),
            ('Intercontinental', 'Pedro Morales', date(1980, 12, 8), date(1981, 6, 20), 1, None),
            ('Intercontinental', 'Don Muraco', date(1981, 6, 20), date(1981, 11, 23), 1, None),
            ('Intercontinental', 'Pedro Morales', date(1981, 11, 23), date(1983, 1, 22), 2, None),
            ('Intercontinental', 'Don Muraco', date(1983, 1, 22), date(1984, 2, 11), 2, None),
            ('Intercontinental', 'Tito Santana', date(1984, 2, 11), date(1984, 9, 24), 1, None),
            ('Intercontinental', 'Greg Valentine', date(1984, 9, 24), date(1985, 7, 6), 1, None),
            ('Intercontinental', 'Tito Santana', date(1985, 7, 6), date(1986, 2, 8), 2, None),
            ('Intercontinental', 'Randy Savage', date(1986, 2, 8), date(1988, 3, 27), 1, None),
            ('Intercontinental', 'The Honky Tonk Man', date(1987, 6, 2), date(1988, 8, 29), 1, '454 day reign - longest in history'),
            ('Intercontinental', 'Ultimate Warrior', date(1988, 8, 29), date(1989, 4, 2), 1, 'SummerSlam 1988'),
            ('Intercontinental', 'Rick Rude', date(1989, 4, 2), date(1989, 8, 28), 1, 'WrestleMania V'),
            ('Intercontinental', 'Ultimate Warrior', date(1989, 8, 28), date(1990, 4, 1), 2, 'SummerSlam 1989'),
            ('Intercontinental', 'Mr. Perfect', date(1990, 4, 23), date(1991, 8, 26), 1, None),
            ('Intercontinental', 'Bret Hart', date(1991, 8, 26), date(1992, 1, 17), 1, 'SummerSlam 1991'),
            ('Intercontinental', 'The Mountie', date(1992, 1, 17), date(1992, 1, 19), 1, 'House show'),
            ('Intercontinental', 'Roddy Piper', date(1992, 1, 19), date(1992, 4, 5), 1, 'Royal Rumble 1992'),
            ('Intercontinental', 'Bret Hart', date(1992, 4, 5), date(1992, 8, 29), 2, 'WrestleMania VIII'),
            ('Intercontinental', 'British Bulldog', date(1992, 8, 29), date(1992, 10, 27), 1, 'SummerSlam 1992 Wembley'),
            ('Intercontinental', 'Shawn Michaels', date(1992, 10, 27), date(1993, 5, 17), 1, 'Saturday Night Main Event'),
            ('Intercontinental', 'Marty Jannetty', date(1993, 5, 17), date(1993, 6, 6), 1, 'Raw'),
            ('Intercontinental', 'Shawn Michaels', date(1993, 6, 6), date(1994, 3, 20), 2, 'Stripped'),
            ('Intercontinental', 'Razor Ramon', date(1993, 9, 27), date(1994, 3, 20), 1, 'Raw'),
            ('Intercontinental', 'Diesel', date(1994, 4, 13), date(1994, 8, 29), 1, 'Superstars'),
            ('Intercontinental', 'Razor Ramon', date(1994, 8, 29), date(1995, 1, 22), 2, 'SummerSlam 1994'),
            ('Intercontinental', 'Jeff Jarrett', date(1995, 1, 22), date(1995, 5, 19), 1, 'Royal Rumble 1995'),
            ('Intercontinental', 'Razor Ramon', date(1995, 5, 19), date(1995, 5, 22), 3, 'House show'),
            ('Intercontinental', 'Jeff Jarrett', date(1995, 5, 22), date(1995, 7, 23), 2, 'In Your House'),
            ('Intercontinental', 'Shawn Michaels', date(1995, 7, 23), date(1996, 3, 31), 3, 'In Your House'),
            ('Intercontinental', 'Stone Cold Steve Austin', date(1997, 8, 3), date(1997, 11, 9), 1, 'In Your House: Summerslam'),
            ('Intercontinental', 'Owen Hart', date(1997, 11, 9), date(1998, 4, 26), 1, 'Raw'),
            ('Intercontinental', 'The Rock', date(1997, 12, 8), date(1998, 8, 30), 1, 'Raw'),
            ('Intercontinental', 'Ken Shamrock', date(1998, 10, 12), date(1999, 2, 14), 1, 'Raw'),
            ('Intercontinental', 'Val Venis', date(1999, 2, 14), date(1999, 3, 29), 1, 'St. Valentine\'s Day Massacre'),
            ('Intercontinental', 'Road Dogg', date(1999, 3, 15), date(1999, 3, 29), 1, 'Raw'),
            ('Intercontinental', 'Goldust', date(1999, 3, 29), date(1999, 5, 4), 1, 'Raw'),
            ('Intercontinental', 'The Godfather', date(1999, 4, 12), date(1999, 6, 29), 1, 'Raw'),
            ('Intercontinental', 'Jeff Jarrett', date(1999, 6, 29), date(1999, 7, 25), 3, 'Raw'),
            ('Intercontinental', 'Edge', date(1999, 7, 24), date(1999, 8, 22), 1, 'Heat'),
            ('Intercontinental', 'Jeff Jarrett', date(1999, 8, 22), date(1999, 9, 16), 4, 'SummerSlam 1999'),
            ('Intercontinental', 'Chyna', date(1999, 10, 17), date(2000, 2, 27), 1, 'Co-champion with Jericho'),
            ('Intercontinental', 'Chris Jericho', date(1999, 12, 12), date(2000, 1, 3), 1, 'Armageddon 1999'),
            ('Intercontinental', 'Chris Benoit', date(2000, 2, 27), date(2000, 4, 2), 1, 'No Way Out 2000'),
            ('Intercontinental', 'Kurt Angle', date(2000, 2, 27), date(2000, 4, 2), 1, 'No Way Out 2000 - Dual champions'),
            ('Intercontinental', 'Chris Jericho', date(2000, 4, 2), date(2000, 4, 17), 2, 'WrestleMania 2000'),
            ('Intercontinental', 'Chris Benoit', date(2000, 5, 8), date(2000, 6, 25), 2, 'Raw'),
            ('Intercontinental', 'Rikishi', date(2000, 6, 25), date(2000, 6, 26), 1, 'King of the Ring 2000'),
            ('Intercontinental', 'Val Venis', date(2000, 7, 6), date(2000, 9, 4), 2, 'Raw'),
            ('Intercontinental', 'Eddie Guerrero', date(2000, 9, 4), date(2000, 9, 24), 1, 'Raw'),
            ('Intercontinental', 'Billy Gunn', date(2000, 10, 16), date(2000, 11, 4), 1, 'Raw'),
            ('Intercontinental', 'Chris Benoit', date(2000, 12, 10), date(2001, 2, 26), 3, 'Armageddon 2000'),
            ('Intercontinental', 'Chris Jericho', date(2001, 2, 26), date(2001, 4, 1), 3, 'Raw'),
            ('Intercontinental', 'Triple H', date(2001, 4, 16), date(2001, 5, 21), 1, 'Raw'),
            ('Intercontinental', 'Jeff Hardy', date(2001, 4, 12), date(2001, 5, 21), 1, 'SmackDown'),
            ('Intercontinental', 'Kane', date(2001, 6, 25), date(2001, 8, 9), 1, 'Raw'),
            ('Intercontinental', 'Edge', date(2001, 11, 18), date(2001, 12, 9), 2, 'Survivor Series 2001'),
            ('Intercontinental', 'Rob Van Dam', date(2002, 7, 21), date(2002, 11, 25), 1, 'Vengeance 2002'),
            ('Intercontinental', 'Chris Jericho', date(2002, 10, 14), date(2002, 11, 18), 4, 'Raw'),
            ('Intercontinental', 'Kane', date(2003, 3, 18), date(2003, 6, 23), 2, 'Raw'),
            ('Intercontinental', 'Christian', date(2003, 5, 18), date(2003, 6, 23), 1, 'Bad Blood 2003'),
            ('Intercontinental', 'Booker T', date(2003, 6, 23), date(2003, 7, 27), 1, 'Raw'),
            ('Intercontinental', 'Christian', date(2003, 8, 10), date(2003, 10, 5), 2, 'SummerSlam 2003 preshow'),
            ('Intercontinental', 'Rob Van Dam', date(2003, 9, 29), date(2004, 1, 22), 2, 'Raw'),
            ('Intercontinental', 'Randy Orton', date(2003, 12, 14), date(2004, 9, 6), 1, 'Armageddon 2003 - 7 months'),
            ('Intercontinental', 'Edge', date(2004, 7, 11), date(2004, 11, 1), 3, 'Vengeance 2004'),
            ('Intercontinental', 'Shelton Benjamin', date(2004, 10, 19), date(2005, 5, 1), 1, 'Taboo Tuesday 2004'),
            ('Intercontinental', 'Carlito', date(2005, 5, 2), date(2005, 6, 20), 1, 'Raw'),
            ('Intercontinental', 'Shelton Benjamin', date(2005, 6, 20), date(2005, 8, 22), 2, 'Raw'),
            ('Intercontinental', 'Ric Flair', date(2005, 9, 19), date(2005, 11, 7), 1, 'Raw'),
            ('Intercontinental', 'Shelton Benjamin', date(2006, 2, 20), date(2006, 8, 28), 3, 'Raw'),
            ('Intercontinental', 'Jeff Hardy', date(2006, 9, 25), date(2006, 10, 2), 2, 'Raw'),
            ('Intercontinental', 'Johnny Nitro', date(2006, 10, 2), date(2006, 10, 16), 1, 'Raw'),
            ('Intercontinental', 'Jeff Hardy', date(2006, 10, 30), date(2007, 2, 19), 3, 'Raw'),
            ('Intercontinental', 'Umaga', date(2007, 2, 19), date(2007, 6, 11), 1, 'Raw'),
            ('Intercontinental', 'Santino Marella', date(2007, 4, 16), date(2007, 8, 20), 1, 'Raw debut'),
            ('Intercontinental', 'Jeff Hardy', date(2007, 9, 3), date(2007, 10, 1), 4, 'Raw'),
            ('Intercontinental', 'Chris Jericho', date(2008, 6, 29), date(2008, 9, 7), 5, 'Night of Champions 2008'),
            ('Intercontinental', 'Kofi Kingston', date(2008, 9, 26), date(2008, 11, 3), 1, 'Raw'),
            ('Intercontinental', 'Santino Marella', date(2008, 11, 3), date(2009, 2, 15), 2, 'Raw'),
            ('Intercontinental', 'Rey Mysterio', date(2009, 4, 5), date(2009, 5, 17), 1, 'WrestleMania 25'),
            ('Intercontinental', 'Chris Jericho', date(2009, 6, 7), date(2009, 9, 13), 6, 'Extreme Rules 2009'),
            ('Intercontinental', 'Rey Mysterio', date(2009, 7, 26), date(2009, 9, 13), 2, 'Night of Champions 2009'),
            ('Intercontinental', 'John Morrison', date(2009, 9, 13), date(2009, 10, 4), 1, 'Breaking Point 2009'),
            ('Intercontinental', 'Drew McIntyre', date(2009, 12, 13), date(2010, 8, 2), 1, 'TLC 2009'),
            ('Intercontinental', 'Kofi Kingston', date(2010, 8, 2), date(2010, 12, 6), 2, 'Raw'),
            ('Intercontinental', 'Dolph Ziggler', date(2010, 12, 6), date(2011, 1, 9), 1, 'Raw'),
            ('Intercontinental', 'Kofi Kingston', date(2011, 1, 9), date(2011, 4, 22), 3, 'Raw'),
            ('Intercontinental', 'Wade Barrett', date(2011, 8, 12), date(2011, 11, 25), 1, 'SmackDown'),
            ('Intercontinental', 'Cody Rhodes', date(2011, 8, 12), date(2012, 4, 1), 1, 'SmackDown'),
            ('Intercontinental', 'Big Show', date(2012, 4, 1), date(2012, 7, 15), 1, 'WrestleMania 28'),
            ('Intercontinental', 'The Miz', date(2012, 10, 28), date(2013, 3, 4), 1, 'Main Event'),
            ('Intercontinental', 'Wade Barrett', date(2013, 1, 7), date(2013, 4, 7), 2, 'Raw'),
            ('Intercontinental', 'Curtis Axel', date(2013, 6, 16), date(2013, 11, 18), 1, 'Payback 2013'),
            ('Intercontinental', 'Big E', date(2013, 11, 18), date(2014, 5, 4), 1, 'Raw'),
            ('Intercontinental', 'Bad News Barrett', date(2014, 5, 4), date(2014, 6, 30), 3, 'Extreme Rules 2014'),
            ('Intercontinental', 'Dolph Ziggler', date(2014, 8, 17), date(2014, 9, 29), 2, 'SummerSlam 2014'),
            ('Intercontinental', 'Daniel Bryan', date(2015, 4, 6), date(2015, 5, 11), 1, 'WrestleMania 31 ladder match'),
            ('Intercontinental', 'Ryback', date(2015, 5, 31), date(2015, 9, 20), 1, 'Elimination Chamber 2015'),
            ('Intercontinental', 'Kevin Owens', date(2015, 9, 20), date(2016, 4, 4), 1, 'Night of Champions 2015'),
            ('Intercontinental', 'The Miz', date(2016, 4, 4), date(2016, 6, 19), 2, 'Raw after WM'),
            ('Intercontinental', 'Zack Ryder', date(2016, 4, 3), date(2016, 4, 4), 1, 'WrestleMania 32'),
            ('Intercontinental', 'The Miz', date(2016, 9, 11), date(2016, 10, 22), 3, 'Backlash 2016'),
            ('Intercontinental', 'Dolph Ziggler', date(2016, 9, 11), date(2016, 10, 9), 3, 'Backlash 2016'),
            ('Intercontinental', 'The Miz', date(2017, 1, 22), date(2017, 4, 2), 4, 'SmackDown'),
            ('Intercontinental', 'Dean Ambrose', date(2017, 4, 2), date(2017, 6, 4), 1, 'WrestleMania 33'),
            ('Intercontinental', 'The Miz', date(2017, 6, 4), date(2017, 10, 22), 5, 'Extreme Rules 2017'),
            ('Intercontinental', 'Roman Reigns', date(2017, 11, 20), date(2018, 2, 25), 1, 'Raw'),
            ('Intercontinental', 'The Miz', date(2018, 2, 25), date(2018, 4, 8), 6, 'Elimination Chamber 2018'),
            ('Intercontinental', 'Seth Rollins', date(2018, 4, 8), date(2018, 6, 17), 1, 'WrestleMania 34'),
            ('Intercontinental', 'Dolph Ziggler', date(2018, 6, 17), date(2018, 8, 19), 4, 'Money in the Bank 2018'),
            ('Intercontinental', 'Seth Rollins', date(2018, 8, 19), date(2018, 11, 5), 2, 'SummerSlam 2018'),
            ('Intercontinental', 'Dean Ambrose', date(2018, 11, 5), date(2019, 1, 14), 2, 'Raw'),
            ('Intercontinental', 'Bobby Lashley', date(2019, 1, 14), date(2019, 2, 17), 1, 'Raw'),
            ('Intercontinental', 'Finn Balor', date(2019, 2, 17), date(2019, 4, 9), 1, 'Elimination Chamber 2019'),
            ('Intercontinental', 'Shinsuke Nakamura', date(2019, 9, 24), date(2020, 1, 31), 1, 'Clash of Champions 2019'),
            ('Intercontinental', 'Braun Strowman', date(2020, 1, 31), date(2020, 3, 8), 1, 'SmackDown'),
            ('Intercontinental', 'Sami Zayn', date(2020, 3, 8), date(2020, 5, 22), 1, 'Elimination Chamber 2020'),
            ('Intercontinental', 'AJ Styles', date(2020, 6, 14), date(2020, 12, 20), 1, 'SmackDown tournament'),
            ('Intercontinental', 'Big E', date(2020, 12, 25), date(2021, 7, 18), 2, 'SmackDown Christmas'),
            ('Intercontinental', 'Apollo Crews', date(2021, 4, 10), date(2021, 8, 21), 1, 'WrestleMania 37'),
            ('Intercontinental', 'Shinsuke Nakamura', date(2021, 8, 21), date(2022, 3, 20), 2, 'SummerSlam 2021'),
            ('Intercontinental', 'Ricochet', date(2022, 3, 5), date(2022, 4, 8), 1, 'SmackDown'),
            ('Intercontinental', 'Gunther', date(2022, 6, 10), None, 1, 'SmackDown - Historic 500+ day reign'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added Intercontinental Championship reigns')

    def seed_wcw_world_title_history(self):
        """Seed WCW World Heavyweight Championship history."""
        self.stdout.write('\n--- Seeding WCW World Title History ---\n')

        reigns = [
            ('WCW World', 'Ric Flair', date(1991, 1, 11), date(1991, 7, 14), 1, 'First WCW World Champion'),
            ('WCW World', 'Lex Luger', date(1991, 7, 14), date(1992, 2, 29), 1, 'Great American Bash 1991'),
            ('WCW World', 'Sting', date(1992, 2, 29), date(1992, 7, 12), 1, 'SuperBrawl II'),
            ('WCW World', 'Big Van Vader', date(1992, 7, 12), date(1992, 8, 2), 1, 'Beach Blast 1992'),
            ('WCW World', 'Ron Simmons', date(1992, 8, 2), date(1992, 12, 30), 1, 'First African American world champion'),
            ('WCW World', 'Big Van Vader', date(1992, 12, 30), date(1993, 3, 11), 2, 'Starrcade 1992'),
            ('WCW World', 'Sting', date(1993, 3, 11), date(1993, 12, 27), 2, 'SuperBrawl III'),
            ('WCW World', 'Ric Flair', date(1993, 12, 27), date(1994, 6, 23), 2, 'Starrcade 1993'),
            ('WCW World', 'Hulk Hogan', date(1994, 7, 17), date(1995, 10, 29), 1, 'Bash at the Beach 1994'),
            ('WCW World', 'The Giant', date(1995, 10, 29), date(1996, 1, 29), 1, 'Halloween Havoc 1995'),
            ('WCW World', 'Ric Flair', date(1996, 1, 29), date(1996, 2, 11), 3, 'Nitro'),
            ('WCW World', 'Randy Savage', date(1996, 2, 11), date(1996, 4, 22), 1, 'Nitro'),
            ('WCW World', 'Ric Flair', date(1996, 4, 22), date(1996, 6, 16), 4, 'Nitro'),
            ('WCW World', 'The Giant', date(1996, 6, 16), date(1996, 8, 10), 2, 'Great American Bash 1996'),
            ('WCW World', 'Hulk Hogan', date(1996, 8, 10), date(1997, 12, 28), 2, 'Hog Wild - nWo era begins'),
            ('WCW World', 'Sting', date(1997, 12, 28), date(1998, 2, 22), 3, 'Starrcade 1997 - Return'),
            ('WCW World', 'Hulk Hogan', date(1998, 2, 22), date(1998, 4, 19), 3, 'SuperBrawl VIII'),
            ('WCW World', 'Randy Savage', date(1998, 4, 19), date(1998, 4, 20), 2, 'Spring Stampede 1998'),
            ('WCW World', 'Hulk Hogan', date(1998, 4, 20), date(1998, 7, 6), 4, 'Nitro'),
            ('WCW World', 'Goldberg', date(1998, 7, 6), date(1998, 12, 27), 1, 'Georgia Dome - Defeated Hogan undefeated'),
            ('WCW World', 'Kevin Nash', date(1998, 12, 27), date(1999, 1, 4), 1, 'Starrcade 1998 - Fingerpoke of Doom'),
            ('WCW World', 'Hulk Hogan', date(1999, 1, 4), date(1999, 3, 14), 5, 'Fingerpoke of Doom'),
            ('WCW World', 'Ric Flair', date(1999, 3, 14), date(1999, 4, 11), 5, 'Uncensored 1999'),
            ('WCW World', 'Diamond Dallas Page', date(1999, 4, 11), date(1999, 4, 26), 1, 'Spring Stampede 1999'),
            ('WCW World', 'Sting', date(1999, 4, 26), date(1999, 5, 9), 4, 'Nitro'),
            ('WCW World', 'Diamond Dallas Page', date(1999, 5, 9), date(1999, 5, 31), 2, 'Slamboree 1999'),
            ('WCW World', 'Kevin Nash', date(1999, 5, 31), date(1999, 7, 11), 2, 'Nitro'),
            ('WCW World', 'Hulk Hogan', date(1999, 7, 11), date(1999, 8, 9), 6, 'Bash at the Beach 1999'),
            ('WCW World', 'Sting', date(1999, 9, 12), date(1999, 10, 18), 5, 'Fall Brawl 1999'),
            ('WCW World', 'Goldberg', date(1999, 12, 19), date(2000, 1, 24), 2, 'Starrcade 1999'),
            ('WCW World', 'Bret Hart', date(2000, 1, 16), date(2000, 4, 10), 1, 'Nitro - Career-ending injury'),
            ('WCW World', 'Sid Vicious', date(2000, 1, 24), date(2000, 4, 10), 1, 'Souled Out 2000'),
            ('WCW World', 'Jeff Jarrett', date(2000, 4, 10), date(2000, 4, 16), 1, 'Nitro'),
            ('WCW World', 'Diamond Dallas Page', date(2000, 4, 16), date(2000, 4, 24), 3, 'Spring Stampede 2000'),
            ('WCW World', 'Jeff Jarrett', date(2000, 4, 24), date(2000, 6, 11), 2, 'Nitro'),
            ('WCW World', 'Kevin Nash', date(2000, 6, 11), date(2000, 8, 14), 3, 'Great American Bash 2000'),
            ('WCW World', 'Booker T', date(2000, 7, 9), date(2000, 8, 13), 1, 'Bash at the Beach 2000'),
            ('WCW World', 'Kevin Nash', date(2000, 8, 14), date(2000, 8, 28), 4, 'Nitro'),
            ('WCW World', 'Booker T', date(2000, 8, 28), date(2000, 9, 17), 2, 'Nitro'),
            ('WCW World', 'Kevin Nash', date(2000, 9, 25), date(2000, 10, 29), 5, 'Nitro'),
            ('WCW World', 'Booker T', date(2000, 10, 29), date(2000, 11, 26), 3, 'Halloween Havoc 2000'),
            ('WCW World', 'Scott Steiner', date(2000, 11, 26), date(2001, 1, 14), 1, 'Mayhem 2000'),
            ('WCW World', 'Sid Vicious', date(2001, 1, 14), date(2001, 1, 18), 2, 'Sin PPV'),
            ('WCW World', 'Scott Steiner', date(2001, 1, 29), date(2001, 3, 18), 2, 'Nitro'),
            ('WCW World', 'Booker T', date(2001, 3, 18), date(2001, 3, 26), 4, 'Greed'),
            ('WCW World', 'Scott Steiner', date(2001, 3, 26), date(2001, 3, 26), 3, 'Nitro - Final WCW World Champion'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added WCW World Championship reigns')

    def seed_ecw_world_title_history(self):
        """Seed ECW World Heavyweight Championship history."""
        self.stdout.write('\n--- Seeding ECW World Title History ---\n')

        reigns = [
            ('ECW World', 'Jimmy Snuka', date(1992, 4, 25), date(1992, 6, 23), 1, 'Inaugural champion'),
            ('ECW World', 'Don Muraco', date(1992, 6, 23), date(1992, 9, 18), 1, None),
            ('ECW World', 'Jimmy Snuka', date(1992, 9, 18), date(1993, 3, 13), 2, None),
            ('ECW World', 'Sandman', date(1993, 3, 13), date(1993, 9, 18), 1, None),
            ('ECW World', 'Terry Funk', date(1993, 9, 18), date(1994, 3, 26), 1, None),
            ('ECW World', 'Shane Douglas', date(1994, 3, 26), date(1994, 8, 27), 1, 'Eastern Championship Wrestling era'),
            ('ECW World', 'Sandman', date(1994, 11, 5), date(1995, 4, 8), 2, None),
            ('ECW World', 'Shane Douglas', date(1995, 4, 8), date(1995, 12, 29), 2, None),
            ('ECW World', 'Mikey Whipwreck', date(1995, 10, 28), date(1995, 12, 9), 1, 'Unexpected champion'),
            ('ECW World', 'Sandman', date(1995, 12, 9), date(1996, 1, 27), 3, None),
            ('ECW World', 'Raven', date(1996, 1, 27), date(1997, 4, 13), 1, '421 day reign'),
            ('ECW World', 'Terry Funk', date(1997, 4, 13), date(1997, 4, 13), 2, 'Barely Legal - Same night'),
            ('ECW World', 'Shane Douglas', date(1997, 6, 6), date(1997, 8, 17), 3, None),
            ('ECW World', 'Bam Bam Bigelow', date(1997, 11, 30), date(1998, 1, 10), 1, 'November to Remember 1997'),
            ('ECW World', 'Shane Douglas', date(1998, 1, 10), date(1998, 4, 4), 4, None),
            ('ECW World', 'Taz', date(1999, 1, 10), date(1999, 4, 17), 1, 'Guilty as Charged 1999'),
            ('ECW World', 'Mike Awesome', date(1999, 9, 19), date(2000, 4, 10), 1, 'Anarchy Rulz 1999'),
            ('ECW World', 'Taz', date(2000, 4, 13), date(2000, 4, 14), 2, 'Brief reign'),
            ('ECW World', 'Tommy Dreamer', date(2000, 4, 22), date(2000, 4, 22), 1, 'CyberSlam - Same night'),
            ('ECW World', 'Justin Credible', date(2000, 4, 22), date(2000, 8, 26), 1, 'CyberSlam'),
            ('ECW World', 'Jerry Lynn', date(2000, 8, 26), date(2000, 10, 1), 1, 'Hardcore Heaven 2000'),
            ('ECW World', 'Justin Credible', date(2000, 10, 1), date(2000, 11, 5), 2, 'Anarchy Rulz 2000'),
            ('ECW World', 'The Sandman', date(2000, 11, 5), date(2000, 11, 26), 4, 'November to Remember 2000'),
            ('ECW World', 'Steve Corino', date(2000, 11, 26), date(2000, 12, 17), 1, None),
            ('ECW World', 'The Sandman', date(2000, 12, 17), date(2001, 1, 7), 5, None),
            ('ECW World', 'Rhino', date(2001, 1, 7), date(2001, 1, 13), 1, 'Guilty as Charged 2001 - Final ECW Champion'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added ECW World Championship reigns')

    def seed_nwa_world_title_history(self):
        """Seed NWA World Heavyweight Championship history - key reigns."""
        self.stdout.write('\n--- Seeding NWA World Title History ---\n')

        reigns = [
            ('NWA World', 'Lou Thesz', date(1948, 7, 20), date(1956, 3, 15), 3, 'Unified NWA title'),
            ('NWA World', 'Whipper Billy Watson', date(1956, 3, 15), date(1956, 11, 14), 1, None),
            ('NWA World', 'Lou Thesz', date(1956, 11, 14), date(1957, 11, 9), 4, None),
            ('NWA World', 'Dick Hutton', date(1957, 11, 14), date(1959, 1, 9), 1, None),
            ('NWA World', 'Pat OConnor', date(1959, 1, 9), date(1961, 6, 30), 1, None),
            ('NWA World', 'Buddy Rogers', date(1961, 6, 30), date(1963, 1, 24), 1, 'Lost to Thesz'),
            ('NWA World', 'Lou Thesz', date(1963, 1, 24), date(1966, 1, 7), 5, None),
            ('NWA World', 'Gene Kiniski', date(1966, 1, 7), date(1969, 2, 11), 1, None),
            ('NWA World', 'Dory Funk Jr.', date(1969, 2, 11), date(1973, 5, 24), 1, '4+ year reign'),
            ('NWA World', 'Harley Race', date(1973, 5, 24), date(1973, 12, 2), 1, None),
            ('NWA World', 'Jack Brisco', date(1973, 7, 20), date(1974, 12, 10), 1, None),
            ('NWA World', 'Giant Baba', date(1974, 12, 2), date(1974, 12, 9), 1, 'First Japanese champion'),
            ('NWA World', 'Jack Brisco', date(1974, 12, 10), date(1975, 12, 10), 2, None),
            ('NWA World', 'Terry Funk', date(1975, 12, 10), date(1977, 2, 6), 1, None),
            ('NWA World', 'Harley Race', date(1977, 2, 6), date(1979, 8, 21), 2, None),
            ('NWA World', 'Dusty Rhodes', date(1979, 8, 21), date(1979, 10, 26), 1, None),
            ('NWA World', 'Harley Race', date(1979, 10, 26), date(1980, 6, 21), 3, None),
            ('NWA World', 'Giant Baba', date(1980, 3, 31), date(1980, 4, 1), 2, None),
            ('NWA World', 'Harley Race', date(1980, 6, 21), date(1981, 4, 27), 4, None),
            ('NWA World', 'Dusty Rhodes', date(1981, 6, 21), date(1981, 9, 17), 2, None),
            ('NWA World', 'Ric Flair', date(1981, 9, 17), date(1983, 6, 10), 1, 'First reign'),
            ('NWA World', 'Harley Race', date(1983, 6, 10), date(1983, 11, 24), 5, None),
            ('NWA World', 'Ric Flair', date(1983, 11, 24), date(1984, 3, 23), 2, 'Starrcade 1983'),
            ('NWA World', 'Harley Race', date(1984, 3, 23), date(1984, 5, 6), 6, None),
            ('NWA World', 'Kerry Von Erich', date(1984, 5, 6), date(1984, 5, 24), 1, 'David Von Erich Memorial'),
            ('NWA World', 'Ric Flair', date(1984, 5, 24), date(1986, 7, 26), 3, None),
            ('NWA World', 'Dusty Rhodes', date(1986, 7, 26), date(1986, 8, 9), 3, 'Great American Bash 1986'),
            ('NWA World', 'Ric Flair', date(1986, 8, 9), date(1987, 3, 26), 4, None),
            ('NWA World', 'Ronnie Garvin', date(1987, 9, 25), date(1987, 11, 26), 1, None),
            ('NWA World', 'Ric Flair', date(1987, 11, 26), date(1988, 3, 27), 5, 'Starrcade 1987'),
            ('NWA World', 'Ricky Steamboat', date(1989, 2, 20), date(1989, 5, 7), 1, 'Chi-Town Rumble'),
            ('NWA World', 'Ric Flair', date(1989, 5, 7), date(1990, 7, 7), 6, 'WrestleWar 1989'),
            ('NWA World', 'Sting', date(1990, 7, 7), date(1991, 1, 11), 1, 'Great American Bash 1990'),
            ('NWA World', 'Ric Flair', date(1991, 1, 11), date(1991, 7, 1), 7, 'Vacant/returned'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added NWA World Championship reigns')

    def seed_iwgp_heavyweight_history(self):
        """Seed IWGP Heavyweight Championship history."""
        self.stdout.write('\n--- Seeding IWGP Heavyweight Title History ---\n')

        reigns = [
            ('IWGP Heavyweight', 'Antonio Inoki', date(1987, 6, 12), date(1988, 5, 8), 1, 'Inaugural champion'),
            ('IWGP Heavyweight', 'Tatsumi Fujinami', date(1988, 5, 8), date(1988, 8, 8), 1, None),
            ('IWGP Heavyweight', 'Big Van Vader', date(1988, 8, 8), date(1989, 8, 10), 1, None),
            ('IWGP Heavyweight', 'Salman Hashimikov', date(1989, 11, 2), date(1989, 12, 31), 1, None),
            ('IWGP Heavyweight', 'Big Van Vader', date(1989, 12, 31), date(1990, 2, 10), 2, None),
            ('IWGP Heavyweight', 'Riki Choshu', date(1990, 2, 10), date(1991, 3, 21), 1, None),
            ('IWGP Heavyweight', 'Tatsumi Fujinami', date(1991, 3, 21), date(1992, 8, 16), 2, None),
            ('IWGP Heavyweight', 'Masahiro Chono', date(1992, 8, 12), date(1993, 5, 3), 1, None),
            ('IWGP Heavyweight', 'The Great Muta', date(1993, 5, 3), date(1993, 9, 23), 1, None),
            ('IWGP Heavyweight', 'Tatsumi Fujinami', date(1993, 9, 23), date(1994, 5, 1), 3, None),
            ('IWGP Heavyweight', 'Shinya Hashimoto', date(1994, 5, 1), date(1994, 6, 17), 1, None),
            ('IWGP Heavyweight', 'Masahiro Chono', date(1994, 6, 17), date(1994, 6, 17), 2, None),
            ('IWGP Heavyweight', 'Kensuke Sasaki', date(1997, 8, 10), date(1997, 11, 3), 1, None),
            ('IWGP Heavyweight', 'Tatsumi Fujinami', date(1998, 4, 4), date(1998, 8, 8), 4, None),
            ('IWGP Heavyweight', 'Shinya Hashimoto', date(1998, 8, 8), date(1999, 1, 4), 2, None),
            ('IWGP Heavyweight', 'Keiji Mutoh', date(1999, 1, 4), date(1999, 5, 3), 2, None),
            ('IWGP Heavyweight', 'Kensuke Sasaki', date(2000, 4, 7), date(2001, 1, 4), 2, None),
            ('IWGP Heavyweight', 'Kazuyuki Fujita', date(2001, 1, 4), date(2001, 5, 5), 1, None),
            ('IWGP Heavyweight', 'Scott Norton', date(2001, 9, 14), date(2001, 10, 8), 1, None),
            ('IWGP Heavyweight', 'Yuji Nagata', date(2001, 11, 12), date(2002, 6, 5), 1, None),
            ('IWGP Heavyweight', 'Hiroyoshi Tenzan', date(2003, 2, 16), date(2003, 10, 13), 1, None),
            ('IWGP Heavyweight', 'Kazuyuki Fujita', date(2004, 2, 15), date(2004, 5, 3), 2, None),
            ('IWGP Heavyweight', 'Bob Sapp', date(2004, 5, 3), date(2004, 6, 5), 1, None),
            ('IWGP Heavyweight', 'Hiroyoshi Tenzan', date(2004, 6, 5), date(2004, 8, 15), 2, None),
            ('IWGP Heavyweight', 'Kensuke Sasaki', date(2004, 8, 15), date(2005, 2, 20), 3, None),
            ('IWGP Heavyweight', 'Kazuyuki Fujita', date(2005, 2, 20), date(2005, 4, 24), 3, None),
            ('IWGP Heavyweight', 'Brock Lesnar', date(2005, 10, 8), date(2006, 1, 4), 1, 'First American champion'),
            ('IWGP Heavyweight', 'Hiroyoshi Tenzan', date(2006, 1, 4), date(2006, 2, 19), 3, None),
            ('IWGP Heavyweight', 'Brock Lesnar', date(2006, 7, 17), date(2007, 6, 29), 2, None),
            ('IWGP Heavyweight', 'Kurt Angle', date(2007, 6, 29), date(2008, 1, 4), 1, None),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2008, 1, 4), date(2008, 4, 27), 1, 'First of many reigns'),
            ('IWGP Heavyweight', 'Shinsuke Nakamura', date(2008, 4, 27), date(2009, 1, 4), 1, None),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2009, 1, 4), date(2009, 4, 5), 2, 'Wrestle Kingdom 3'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2011, 1, 4), date(2011, 10, 10), 3, 'Wrestle Kingdom 5'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2012, 2, 12), date(2012, 6, 16), 4, None),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2012, 6, 16), date(2012, 10, 8), 1, 'Dominion 6.16'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2012, 10, 8), date(2013, 4, 7), 5, None),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2013, 4, 7), date(2013, 10, 14), 2, 'Invasion Attack'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2013, 10, 14), date(2014, 4, 6), 6, 'King of Pro-Wrestling'),
            ('IWGP Heavyweight', 'AJ Styles', date(2014, 5, 3), date(2014, 10, 13), 1, 'Wrestling Dontaku'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2014, 10, 13), date(2015, 1, 4), 7, 'King of Pro-Wrestling'),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2015, 1, 4), date(2015, 7, 5), 3, 'Wrestle Kingdom 9'),
            ('IWGP Heavyweight', 'AJ Styles', date(2015, 7, 5), date(2015, 10, 12), 2, 'Dominion'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2015, 10, 12), date(2016, 1, 4), 8, 'King of Pro-Wrestling'),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2016, 1, 4), date(2016, 6, 19), 4, 'Wrestle Kingdom 10'),
            ('IWGP Heavyweight', 'Tetsuya Naito', date(2016, 6, 19), date(2016, 8, 14), 1, 'Dominion 6.19'),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2016, 8, 14), date(2018, 6, 9), 5, 'G1 Climax 26 - 720 day reign'),
            ('IWGP Heavyweight', 'Kenny Omega', date(2018, 6, 9), date(2019, 1, 4), 1, 'Dominion 6.9'),
            ('IWGP Heavyweight', 'Hiroshi Tanahashi', date(2019, 1, 4), date(2019, 4, 6), 9, 'Wrestle Kingdom 13'),
            ('IWGP Heavyweight', 'Jay White', date(2019, 4, 6), date(2019, 5, 4), 1, 'G1 Supercard'),
            ('IWGP Heavyweight', 'Kazuchika Okada', date(2019, 5, 4), date(2020, 1, 5), 6, 'Wrestling Dontaku'),
            ('IWGP Heavyweight', 'Tetsuya Naito', date(2020, 1, 5), date(2020, 2, 1), 2, 'Wrestle Kingdom 14 Night 2 - Unified titles'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added IWGP Heavyweight Championship reigns')

    def seed_aew_world_title_history(self):
        """Seed AEW World Championship history."""
        self.stdout.write('\n--- Seeding AEW World Title History ---\n')

        reigns = [
            ('AEW World', 'Chris Jericho', date(2019, 8, 31), date(2020, 2, 29), 1, 'Inaugural champion at All Out 2019'),
            ('AEW World', 'Jon Moxley', date(2020, 2, 29), date(2020, 12, 2), 1, 'Revolution 2020 - 277 days'),
            ('AEW World', 'Kenny Omega', date(2020, 12, 2), date(2021, 11, 13), 1, 'Winter Is Coming - Belt Collector'),
            ('AEW World', 'Hangman Adam Page', date(2021, 11, 13), date(2022, 5, 29), 1, 'Full Gear 2021 - Cowboy era'),
            ('AEW World', 'CM Punk', date(2022, 5, 29), date(2022, 8, 24), 1, 'Double or Nothing 2022'),
            ('AEW World', 'Jon Moxley', date(2022, 8, 24), date(2022, 9, 4), 2, 'Interim champion'),
            ('AEW World', 'CM Punk', date(2022, 9, 4), date(2022, 9, 7), 2, 'All Out 2022 - Vacated'),
            ('AEW World', 'Jon Moxley', date(2022, 9, 7), date(2022, 9, 21), 3, 'Restored as champion'),
            ('AEW World', 'MJF', date(2022, 11, 19), date(2023, 9, 2), 1, 'Full Gear 2022 - 287 days'),
            ('AEW World', 'Samoa Joe', date(2023, 12, 30), date(2024, 4, 21), 1, 'Worlds End 2023'),
            ('AEW World', 'Swerve Strickland', date(2024, 4, 21), None, 1, 'Dynasty 2024'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added AEW World Championship reigns')

    def seed_tna_world_title_history(self):
        """Seed TNA World Heavyweight Championship history."""
        self.stdout.write('\n--- Seeding TNA World Title History ---\n')

        reigns = [
            ('TNA World', 'Kurt Angle', date(2007, 10, 14), date(2008, 4, 13), 1, 'Bound for Glory III'),
            ('TNA World', 'Samoa Joe', date(2008, 4, 13), date(2008, 10, 12), 1, 'Lockdown 2008'),
            ('TNA World', 'Sting', date(2008, 10, 12), date(2009, 4, 19), 1, 'Bound for Glory IV'),
            ('TNA World', 'Mick Foley', date(2009, 4, 19), date(2009, 6, 21), 1, 'Lockdown 2009'),
            ('TNA World', 'Kurt Angle', date(2009, 6, 21), date(2009, 9, 20), 2, 'Slammiversary 2009'),
            ('TNA World', 'AJ Styles', date(2009, 9, 20), date(2010, 3, 8), 1, 'No Surrender 2009'),
            ('TNA World', 'Rob Van Dam', date(2010, 4, 19), date(2010, 6, 13), 1, 'Impact debut'),
            ('TNA World', 'Jeff Hardy', date(2010, 10, 10), date(2011, 3, 13), 1, 'Bound for Glory VI - Heel turn'),
            ('TNA World', 'Sting', date(2011, 3, 13), date(2011, 5, 15), 2, 'Victory Road 2011'),
            ('TNA World', 'Mr. Anderson', date(2011, 5, 15), date(2011, 7, 10), 1, 'Sacrifice 2011'),
            ('TNA World', 'Sting', date(2011, 7, 10), date(2011, 10, 16), 3, 'Destination X 2011'),
            ('TNA World', 'Kurt Angle', date(2011, 10, 16), date(2012, 3, 8), 3, 'Bound for Glory VII'),
            ('TNA World', 'Bobby Roode', date(2011, 11, 3), date(2012, 6, 10), 1, 'Impact - 256 day reign'),
            ('TNA World', 'Austin Aries', date(2012, 7, 8), date(2012, 10, 14), 1, 'Destination X 2012'),
            ('TNA World', 'Jeff Hardy', date(2012, 10, 14), date(2013, 3, 10), 2, 'Bound for Glory VIII'),
            ('TNA World', 'Bully Ray', date(2013, 3, 10), date(2013, 6, 2), 1, 'Lockdown 2013'),
            ('TNA World', 'Chris Sabin', date(2013, 7, 18), date(2013, 8, 1), 1, 'Destination X 2013'),
            ('TNA World', 'Bully Ray', date(2013, 8, 1), date(2013, 10, 20), 2, 'Impact'),
            ('TNA World', 'AJ Styles', date(2013, 10, 20), date(2013, 12, 19), 2, 'Bound for Glory IX'),
            ('TNA World', 'Magnus', date(2013, 12, 19), date(2014, 3, 16), 1, 'Impact'),
            ('TNA World', 'Eric Young', date(2014, 4, 10), date(2014, 6, 15), 1, 'Impact'),
            ('TNA World', 'Bobby Lashley', date(2014, 6, 15), date(2014, 10, 12), 1, 'Slammiversary 2014'),
            ('TNA World', 'Bobby Roode', date(2014, 10, 12), date(2015, 1, 7), 2, 'Bound for Glory X'),
            ('TNA World', 'Bobby Lashley', date(2015, 1, 7), date(2016, 3, 15), 2, 'Impact - 433 day reign'),
            ('TNA World', 'Drew Galloway', date(2016, 3, 15), date(2016, 5, 3), 1, 'Impact'),
            ('TNA World', 'Lashley', date(2016, 6, 12), date(2016, 10, 2), 3, 'Slammiversary 2016'),
            ('TNA World', 'Eddie Edwards', date(2016, 10, 2), date(2017, 2, 5), 1, 'Bound for Glory 2016'),
            ('TNA World', 'Bobby Lashley', date(2017, 2, 5), date(2017, 4, 20), 4, 'Impact'),
            ('TNA World', 'Alberto El Patron', date(2017, 4, 20), date(2017, 6, 4), 1, 'Redemption'),
        ]

        for title, wrestler, start, end, reign_num, notes in reigns:
            self.add_reign(title, wrestler, start, end, reign_num, notes)

        self.stdout.write(f'  Added TNA World Championship reigns')
