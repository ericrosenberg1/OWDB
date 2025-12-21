"""
Comprehensive Wrestling Documentaries and Specials Seeder.

Adds wrestling documentaries, movies, and TV specials with cast links.

Usage:
    python manage.py seed_documentaries
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdb_django.owdbapp.models import Special, Wrestler


class Command(BaseCommand):
    help = 'Seed comprehensive wrestling documentary database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING DOCUMENTARIES ===\n'))

        total_created = 0
        total_linked = 0

        # WWE Documentaries
        created, linked = self.seed_wwe_documentaries()
        total_created += created
        total_linked += linked

        # Netflix/Streaming Documentaries
        created, linked = self.seed_streaming_docs()
        total_created += created
        total_linked += linked

        # Movies
        created, linked = self.seed_wrestling_movies()
        total_created += created
        total_linked += linked

        # TV Series
        created, linked = self.seed_tv_series()
        total_created += created
        total_linked += linked

        # Other Documentaries
        created, linked = self.seed_other_docs()
        total_created += created
        total_linked += linked

        self.stdout.write(self.style.SUCCESS(f'\n=== COMPLETE ==='))
        self.stdout.write(f'Documentaries created: {total_created}')
        self.stdout.write(f'Wrestler links: {total_linked}')
        self.stdout.write(f'Total specials in DB: {Special.objects.count()}')

    def get_or_create_wrestler(self, name):
        """Get or create wrestler by name."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.filter(name__icontains=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.create(
                name=name,
                slug=slugify(name)
            )
        return wrestler

    def create_special(self, title, year, special_type, wrestler_names, about=None):
        """Create a special (documentary/movie) with wrestler links."""
        slug = slugify(f"{title}-{year}" if year else title)

        special, created = Special.objects.get_or_create(
            slug=slug,
            defaults={
                'title': title,
                'release_year': year,
                'type': special_type,
                'about': about or title
            }
        )

        linked = 0
        if wrestler_names:
            for wrestler_name in wrestler_names:
                wrestler = self.get_or_create_wrestler(wrestler_name)
                if wrestler and wrestler not in special.related_wrestlers.all():
                    special.related_wrestlers.add(wrestler)
                    linked += 1

        return created, linked

    def seed_wwe_documentaries(self):
        """Seed WWE produced documentaries."""
        self.stdout.write('--- Seeding WWE Documentaries ---')
        created_count = 0
        linked_count = 0

        wwe_docs = [
            # WWE 24 Series
            ('WWE 24: WrestleMania Silicon Valley', 2015, 'documentary',
             ['Roman Reigns', 'Brock Lesnar', 'Seth Rollins'],
             'Behind the scenes of WrestleMania 31'),
            ('WWE 24: WrestleMania Dallas', 2016, 'documentary',
             ['Roman Reigns', 'Triple H', 'Shane McMahon', 'Undertaker'],
             'Behind the scenes of WrestleMania 32'),
            ('WWE 24: Women\'s Evolution', 2016, 'documentary',
             ['Charlotte Flair', 'Becky Lynch', 'Sasha Banks', 'Bayley'],
             'The Women\'s Revolution in WWE'),
            ('WWE 24: Finn Balor', 2017, 'documentary',
             ['Finn Balor'],
             'Finn Balor\'s journey and injury recovery'),
            ('WWE 24: Kurt Angle', 2017, 'documentary',
             ['Kurt Angle'],
             'Kurt Angle\'s WWE Hall of Fame induction'),
            ('WWE 24: Shawn Michaels', 2018, 'documentary',
             ['Shawn Michaels', 'Triple H', 'Undertaker'],
             'Shawn Michaels\' career retrospective'),
            ('WWE 24: Ronda Rousey', 2019, 'documentary',
             ['Ronda Rousey'],
             'Ronda Rousey\'s first year in WWE'),
            ('WWE 24: The Miz', 2020, 'documentary',
             ['The Miz'],
             'The Miz\'s journey to WWE Champion'),
            ('WWE 24: Daniel Bryan', 2015, 'documentary',
             ['Daniel Bryan', 'Brie Bella'],
             'Daniel Bryan\'s Yes Movement and comeback'),
            ('WWE 24: Edge', 2021, 'documentary',
             ['Edge'],
             'Edge\'s return after 9-year retirement'),
            ('WWE 24: Booker T', 2021, 'documentary',
             ['Booker T'],
             'Booker T\'s legacy and Hall of Fame journey'),

            # Biography WWE Legends (A&E)
            ('Biography: WWE Legends - Stone Cold Steve Austin', 2021, 'documentary',
             ['Stone Cold Steve Austin', 'Vince McMahon', 'The Rock'],
             'A&E Biography on Stone Cold Steve Austin'),
            ('Biography: WWE Legends - Roddy Piper', 2021, 'documentary',
             ['Roddy Piper', 'Hulk Hogan'],
             'A&E Biography on Roddy Piper'),
            ('Biography: WWE Legends - Randy Savage', 2021, 'documentary',
             ['Randy Savage', 'Miss Elizabeth', 'Hulk Hogan'],
             'A&E Biography on Randy Savage'),
            ('Biography: WWE Legends - Ultimate Warrior', 2021, 'documentary',
             ['Ultimate Warrior', 'Hulk Hogan'],
             'A&E Biography on Ultimate Warrior'),
            ('Biography: WWE Legends - Booker T', 2021, 'documentary',
             ['Booker T', 'Stevie Ray'],
             'A&E Biography on Booker T'),
            ('Biography: WWE Legends - Mick Foley', 2021, 'documentary',
             ['Mick Foley', 'Terry Funk', 'Undertaker'],
             'A&E Biography on Mick Foley'),
            ('Biography: WWE Legends - Shawn Michaels', 2021, 'documentary',
             ['Shawn Michaels', 'Triple H', 'Bret Hart'],
             'A&E Biography on Shawn Michaels'),
            ('Biography: WWE Legends - Bret Hart', 2022, 'documentary',
             ['Bret Hart', 'Shawn Michaels', 'Owen Hart'],
             'A&E Biography on Bret Hart'),
            ('Biography: WWE Legends - The Undertaker', 2022, 'documentary',
             ['Undertaker', 'Shawn Michaels', 'Triple H'],
             'A&E Biography on The Undertaker'),
            ('Biography: WWE Legends - Rob Van Dam', 2023, 'documentary',
             ['Rob Van Dam', 'Sabu', 'Paul Heyman'],
             'A&E Biography on Rob Van Dam'),
            ('Biography: WWE Legends - Ric Flair', 2023, 'documentary',
             ['Ric Flair', 'Charlotte Flair', 'Arn Anderson'],
             'A&E Biography on Ric Flair'),
            ('Biography: WWE Legends - Cody Rhodes', 2024, 'documentary',
             ['Cody Rhodes', 'Dusty Rhodes', 'Roman Reigns'],
             'A&E Biography on Cody Rhodes'),

            # The Last Ride Series
            ('The Last Ride: The Undertaker', 2020, 'series',
             ['Undertaker', 'Shawn Michaels', 'Triple H', 'Roman Reigns', 'AJ Styles'],
             'Multi-episode documentary on The Undertaker\'s final years'),

            # Other WWE Documentaries
            ('The Monday Night War', 2014, 'series',
             ['Vince McMahon', 'Eric Bischoff', 'Hulk Hogan', 'Stone Cold Steve Austin'],
             'Documentary series on WWE vs WCW'),
            ('Legends of Wrestling', 2006, 'series',
             ['Hulk Hogan', 'Ric Flair', 'Dusty Rhodes'],
             'Roundtable discussions with wrestling legends'),
            ('Self Destruction of the Ultimate Warrior', 2005, 'documentary',
             ['Ultimate Warrior', 'Hulk Hogan'],
             'Controversial documentary on Ultimate Warrior'),
            ('The Rise and Fall of ECW', 2004, 'documentary',
             ['Paul Heyman', 'Tommy Dreamer', 'Sabu', 'Rob Van Dam', 'Sandman'],
             'History of Extreme Championship Wrestling'),
            ('The Rise and Fall of WCW', 2009, 'documentary',
             ['Eric Bischoff', 'Sting', 'Goldberg', 'Hulk Hogan'],
             'History of World Championship Wrestling'),
            ('Breaking the Code: Behind the Walls of Chris Jericho', 2010, 'documentary',
             ['Chris Jericho'],
             'Documentary on Chris Jericho\'s career'),
            ('Ladies and Gentlemen, My Name is Paul Heyman', 2014, 'documentary',
             ['Paul Heyman', 'Brock Lesnar', 'CM Punk'],
             'Documentary on Paul Heyman'),
            ('For All Mankind', 2019, 'documentary',
             ['Mick Foley', 'Undertaker', 'The Rock', 'Terry Funk'],
             'Celebrating Mick Foley\'s legacy'),
            ('True Giants', 2020, 'documentary',
             ['Big Show', 'Andre the Giant', 'Giant Gonzalez', 'Great Khali'],
             'WWE\'s tallest superstars'),
            ('Ruthless Aggression', 2020, 'series',
             ['John Cena', 'Brock Lesnar', 'Batista', 'Eddie Guerrero'],
             'Documentary series on WWE\'s Ruthless Aggression Era'),
            ('Bret Hart: The Dungeon Collection', 2013, 'documentary',
             ['Bret Hart', 'Owen Hart', 'Jim Neidhart', 'British Bulldog'],
             'Documentary on the Hart Family'),
            ('CM Punk: Best in the World', 2012, 'documentary',
             ['CM Punk'],
             'Documentary on CM Punk\'s career'),
            ('The Destruction of the Shield', 2018, 'documentary',
             ['Roman Reigns', 'Seth Rollins', 'Dean Ambrose'],
             'The story of The Shield'),
            ('Owen: Hart of Gold', 2015, 'documentary',
             ['Owen Hart', 'Bret Hart', 'Jim Neidhart'],
             'Documentary tribute to Owen Hart'),
            ('Warrior: The Ultimate Legend', 2014, 'documentary',
             ['Ultimate Warrior'],
             'Memorial documentary for Ultimate Warrior'),
        ]

        for doc_data in wwe_docs:
            c, l = self.create_special(*doc_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} WWE documentaries, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_streaming_docs(self):
        """Seed Netflix, Vice, and other streaming documentaries."""
        self.stdout.write('--- Seeding Streaming Documentaries ---')
        created_count = 0
        linked_count = 0

        streaming_docs = [
            # Dark Side of the Ring (Vice)
            ('Dark Side of the Ring: The Montreal Screwjob', 2019, 'documentary',
             ['Bret Hart', 'Shawn Michaels', 'Vince McMahon', 'Earl Hebner'],
             'Vice documentary on the Montreal Screwjob'),
            ('Dark Side of the Ring: Benoit', 2020, 'documentary',
             ['Chris Benoit', 'Eddie Guerrero', 'Dean Malenko'],
             'Vice two-part documentary on Chris Benoit'),
            ('Dark Side of the Ring: Owen Hart', 2020, 'documentary',
             ['Owen Hart', 'Martha Hart', 'Bret Hart'],
             'Vice documentary on Owen Hart\'s death'),
            ('Dark Side of the Ring: Road Warriors', 2020, 'documentary',
             ['Road Warriors', 'Animal', 'Hawk'],
             'Vice documentary on the Road Warriors'),
            ('Dark Side of the Ring: The Dynamite Kid', 2020, 'documentary',
             ['Dynamite Kid', 'British Bulldog'],
             'Vice documentary on the Dynamite Kid'),
            ('Dark Side of the Ring: Jimmy Snuka', 2019, 'documentary',
             ['Jimmy Snuka'],
             'Vice documentary on Jimmy Snuka'),
            ('Dark Side of the Ring: Bruiser Brody', 2019, 'documentary',
             ['Bruiser Brody'],
             'Vice documentary on Bruiser Brody\'s death'),
            ('Dark Side of the Ring: Brawl for All', 2019, 'documentary',
             ['Bart Gunn', 'Dr. Death Steve Williams', 'Jim Ross'],
             'Vice documentary on WWE\'s Brawl for All'),
            ('Dark Side of the Ring: Grizzly Smith', 2020, 'documentary',
             ['Jake Roberts', 'Sam Houston'],
             'Vice documentary on the Von Erich-style family'),
            ('Dark Side of the Ring: New Jack', 2020, 'documentary',
             ['New Jack'],
             'Vice documentary on New Jack'),
            ('Dark Side of the Ring: Brian Pillman', 2020, 'documentary',
             ['Brian Pillman', 'Stone Cold Steve Austin'],
             'Vice documentary on Brian Pillman'),
            ('Dark Side of the Ring: The Plane Ride from Hell', 2021, 'documentary',
             ['Ric Flair', 'Scott Hall', 'Brock Lesnar'],
             'Vice documentary on infamous 2002 plane ride'),
            ('Dark Side of the Ring: Nick Gage', 2021, 'documentary',
             ['Nick Gage'],
             'Vice documentary on Nick Gage'),
            ('Dark Side of the Ring: The Steroid Trials', 2021, 'documentary',
             ['Hulk Hogan', 'Vince McMahon'],
             'Vice documentary on WWE steroid scandal'),
            ('Dark Side of the Ring: Collision in Korea', 2022, 'documentary',
             ['Ric Flair', 'Antonio Inoki', 'Muhammad Ali'],
             'Vice documentary on wrestling in North Korea'),
            ('Dark Side of the Ring: The Last of the Von Erichs', 2019, 'documentary',
             ['Kerry Von Erich', 'Kevin Von Erich'],
             'Vice documentary on the Von Erich family tragedy'),
            ('Dark Side of the Ring: Ultimate Warrior', 2022, 'documentary',
             ['Ultimate Warrior'],
             'Vice documentary on Ultimate Warrior'),

            # Netflix/HBO Documentaries
            ('Andre the Giant', 2018, 'documentary',
             ['Andre the Giant', 'Hulk Hogan', 'Vince McMahon', 'Ric Flair'],
             'HBO documentary on Andre the Giant'),
            ('The Iron Claw', 2023, 'movie',
             ['Kerry Von Erich', 'Kevin Von Erich', 'Fritz Von Erich'],
             'Dramatic film about the Von Erich family'),
            ('Wrestlers', 2023, 'series',
             ['Independent Wrestlers'],
             'Netflix series on independent wrestling scene'),
            ('Heels', 2021, 'series',
             ['Stephen Amell'],
             'Starz dramatic series about wrestling'),

            # A&E Specials
            ('Most Wanted Treasures: WWE', 2021, 'series',
             ['Mick Foley', 'AJ Francis'],
             'A&E series hunting wrestling memorabilia'),
            ('Rivals: WWE', 2022, 'series',
             ['Stone Cold Steve Austin', 'The Rock', 'Bret Hart', 'Shawn Michaels'],
             'A&E series on legendary rivalries'),

            # Other Streaming
            ('350 Days', 2018, 'documentary',
             ['Bret Hart', 'Superstar Billy Graham', 'Greg Valentine'],
             'Documentary on life on the road'),
            ('Bloodsport: ECW Documentary', 2007, 'documentary',
             ['Paul Heyman', 'Tommy Dreamer', 'Sabu'],
             'Independent documentary on ECW'),
            ('Card Subject to Change', 2010, 'documentary',
             ['Independent Wrestlers'],
             'Documentary on independent wrestling'),
            ('Gaea Girls', 2000, 'documentary',
             ['Chigusa Nagayo'],
             'Documentary on Japanese women\'s wrestling'),
            ('Lipstick & Dynamite', 2004, 'documentary',
             ['Fabulous Moolah', 'Mae Young', 'Penny Banner'],
             'Documentary on women\'s wrestling pioneers'),
        ]

        for doc_data in streaming_docs:
            c, l = self.create_special(*doc_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} streaming documentaries, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_wrestling_movies(self):
        """Seed wrestling-themed movies."""
        self.stdout.write('--- Seeding Wrestling Movies ---')
        created_count = 0
        linked_count = 0

        movies = [
            ('The Wrestler', 2008, 'movie',
             [],
             'Academy Award nominated film starring Mickey Rourke'),
            ('Fighting with My Family', 2019, 'movie',
             ['Paige', 'The Rock'],
             'Film about Paige\'s journey to WWE'),
            ('The Main Event', 2020, 'movie',
             ['Kofi Kingston', 'The Miz', 'Sheamus'],
             'Netflix family film with WWE stars'),
            ('No Holds Barred', 1989, 'movie',
             ['Hulk Hogan'],
             'Action film starring Hulk Hogan'),
            ('Suburban Commando', 1991, 'movie',
             ['Hulk Hogan'],
             'Sci-fi comedy starring Hulk Hogan'),
            ('Ready to Rumble', 2000, 'movie',
             ['Diamond Dallas Page', 'Goldberg', 'Sting'],
             'Comedy film featuring WCW stars'),
            ('The Scorpion King', 2002, 'movie',
             ['The Rock'],
             'Action film starring The Rock'),
            ('Walking Tall', 2004, 'movie',
             ['The Rock'],
             'Action film starring The Rock'),
            ('The Marine', 2006, 'movie',
             ['John Cena'],
             'Action film starring John Cena'),
            ('12 Rounds', 2009, 'movie',
             ['John Cena'],
             'Action film starring John Cena'),
            ('Bumblebee', 2018, 'movie',
             ['John Cena'],
             'Transformers film starring John Cena'),
            ('F9', 2021, 'movie',
             ['John Cena'],
             'Fast & Furious film starring John Cena'),
            ('Peacemaker', 2022, 'series',
             ['John Cena'],
             'HBO Max series starring John Cena'),
            ('Guardians of the Galaxy', 2014, 'movie',
             ['Batista'],
             'Marvel film starring Batista as Drax'),
            ('Blade Runner 2049', 2017, 'movie',
             ['Batista'],
             'Sci-fi film featuring Batista'),
            ('Army of the Dead', 2021, 'movie',
             ['Batista'],
             'Netflix film starring Batista'),
            ('They Live', 1988, 'movie',
             ['Roddy Piper'],
             'Cult classic starring Roddy Piper'),
            ('Predator', 1987, 'movie',
             ['Jesse Ventura'],
             'Action film featuring Jesse Ventura'),
            ('The Running Man', 1987, 'movie',
             ['Jesse Ventura'],
             'Sci-fi film featuring Jesse Ventura'),
            ('Nacho Libre', 2006, 'movie',
             [],
             'Comedy film about Mexican wrestling'),
            ('Wrestle', 2018, 'documentary',
             [],
             'Documentary on high school wrestling in Alabama'),
            ('Beyond the Mat', 1999, 'documentary',
             ['Mick Foley', 'Terry Funk', 'Jake Roberts'],
             'Behind the scenes documentary on wrestling'),
            ('Wrestling with Shadows', 1998, 'documentary',
             ['Bret Hart', 'Shawn Michaels', 'Vince McMahon'],
             'Documentary on Bret Hart and Montreal Screwjob'),
            ('Hitman Hart: Wrestling with Shadows', 1998, 'documentary',
             ['Bret Hart', 'Owen Hart'],
             'Documentary following Bret Hart in 1997'),
            ('Bodyslam: Revenge of the Banana', 2015, 'documentary',
             ['Honky Tonk Man'],
             'Documentary on independent wrestling'),
        ]

        for movie_data in movies:
            c, l = self.create_special(*movie_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} wrestling movies, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_tv_series(self):
        """Seed wrestling-related TV series."""
        self.stdout.write('--- Seeding TV Series ---')
        created_count = 0
        linked_count = 0

        tv_series = [
            ('Total Divas', 2013, 'series',
             ['Nikki Bella', 'Brie Bella', 'Natalya', 'Eva Marie'],
             'E! reality series following WWE Divas'),
            ('Total Bellas', 2016, 'series',
             ['Nikki Bella', 'Brie Bella', 'John Cena', 'Daniel Bryan'],
             'E! reality series following the Bella Twins'),
            ('Miz & Mrs', 2018, 'series',
             ['The Miz', 'Maryse'],
             'USA Network reality series'),
            ('Rhodes to the Top', 2021, 'series',
             ['Cody Rhodes', 'Brandi Rhodes'],
             'TNT reality series following Cody and Brandi'),
            ('WWE Tough Enough', 2001, 'series',
             ['Stone Cold Steve Austin', 'Trish Stratus'],
             'WWE competition reality series'),
            ('Southpaw Regional Wrestling', 2017, 'series',
             ['John Cena', 'Rusev', 'Fandango'],
             'WWE comedy series'),
            ('WWE 365', 2017, 'series',
             ['Kevin Owens', 'Seth Rollins', 'AJ Styles'],
             'WWE Network documentary series'),
            ('WWE Chronicle', 2018, 'series',
             ['Shinsuke Nakamura', 'Becky Lynch', 'Roman Reigns'],
             'WWE Network documentary series'),
            ('Table for 3', 2015, 'series',
             ['Various WWE Legends'],
             'WWE Network talk show'),
            ('Ride Along', 2016, 'series',
             ['Various WWE Superstars'],
             'WWE Network series riding with superstars'),
            ('Straight Up Steve Austin', 2019, 'series',
             ['Stone Cold Steve Austin'],
             'USA Network talk show'),
            ('Stone Cold Takes on America', 2023, 'series',
             ['Stone Cold Steve Austin'],
             'A&E series with Stone Cold'),
            ('GLOW', 2017, 'series',
             [],
             'Netflix series based on Gorgeous Ladies of Wrestling'),
            ('Young Rock', 2021, 'series',
             ['The Rock', 'Rocky Johnson'],
             'NBC series based on The Rock\'s childhood'),
        ]

        for series_data in tv_series:
            c, l = self.create_special(*series_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} TV series, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_other_docs(self):
        """Seed other wrestling documentaries."""
        self.stdout.write('--- Seeding Other Documentaries ---')
        created_count = 0
        linked_count = 0

        other_docs = [
            ('Ric Flair: 30 for 30', 2017, 'documentary',
             ['Ric Flair', 'Charlotte Flair'],
             'ESPN 30 for 30 on Ric Flair'),
            ('Nature Boy', 2017, 'documentary',
             ['Ric Flair', 'Dusty Rhodes', 'Ricky Steamboat'],
             'ESPN documentary on Ric Flair'),
            ('The Fabulous Freebirds', 2016, 'documentary',
             ['Michael Hayes', 'Terry Gordy', 'Buddy Roberts'],
             'Documentary on the Fabulous Freebirds'),
            ('Forever Hardcore', 2005, 'documentary',
             ['Tommy Dreamer', 'Sabu', 'Rob Van Dam', 'Sandman'],
             'Documentary on ECW'),
            ('Bloodstained Memoirs', 2009, 'documentary',
             ['Abdullah the Butcher', 'Mick Foley'],
             'Documentary on hardcore wrestling'),
            ('Barbed Wire City: The Unauthorized Story of ECW', 2013, 'documentary',
             ['Paul Heyman', 'Tommy Dreamer', 'Taz'],
             'Documentary on ECW history'),
            ('Pro Wrestlers vs Zombies', 2014, 'movie',
             ['Roddy Piper', 'Hacksaw Jim Duggan', 'Matt Hardy', 'Kurt Angle'],
             'Horror comedy with wrestling stars'),
            ('Bruno Sammartino', 2019, 'documentary',
             ['Bruno Sammartino'],
             'Documentary on Bruno Sammartino'),
            ('Doink the Clown: The Whole F\'n Show', 2021, 'documentary',
             ['Doink the Clown', 'Matt Borne'],
             'Documentary on Doink the Clown'),
            ('Johnny Valiant: An Unauthorized Story', 2019, 'documentary',
             ['Johnny Valiant'],
             'Documentary on Johnny Valiant'),
            ('Vaxxed II', 2019, 'documentary',
             [],
             'Documentary featuring wrestling families'),
            ('Superstar: The Life and Times of Andy Kaufman', 1999, 'documentary',
             ['Jerry Lawler', 'Andy Kaufman'],
             'Documentary on Andy Kaufman featuring wrestling'),
            ('Man on the Moon', 1999, 'movie',
             ['Jerry Lawler'],
             'Biopic on Andy Kaufman with Jerry Lawler'),
            ('I Am Chris Farley', 2015, 'documentary',
             [],
             'Documentary featuring wrestling references'),
        ]

        for doc_data in other_docs:
            c, l = self.create_special(*doc_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} other documentaries, {linked_count} wrestler links')
        return created_count, linked_count
