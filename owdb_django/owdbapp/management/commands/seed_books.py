"""
Comprehensive Wrestling Books Seeder.

Adds wrestling books including autobiographies, biographies, and WWE publications.
Links authors and subjects to wrestlers.

Usage:
    python manage.py seed_books
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdb_django.owdbapp.models import Book, Wrestler


class Command(BaseCommand):
    help = 'Seed comprehensive wrestling book database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING BOOKS ===\n'))

        total_created = 0
        total_linked = 0

        # Autobiographies
        created, linked = self.seed_autobiographies()
        total_created += created
        total_linked += linked

        # Biographies
        created, linked = self.seed_biographies()
        total_created += created
        total_linked += linked

        # WWE Publications
        created, linked = self.seed_wwe_books()
        total_created += created
        total_linked += linked

        # History/Reference Books
        created, linked = self.seed_history_books()
        total_created += created
        total_linked += linked

        self.stdout.write(self.style.SUCCESS(f'\n=== COMPLETE ==='))
        self.stdout.write(f'Books created: {total_created}')
        self.stdout.write(f'Wrestler links: {total_linked}')
        self.stdout.write(f'Total books in DB: {Book.objects.count()}')

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

    def create_book(self, title, author, year, publisher, wrestler_names, about=None):
        """Create a book with wrestler links."""
        slug = slugify(f"{title}-{year}" if year else title)

        book, created = Book.objects.get_or_create(
            slug=slug,
            defaults={
                'title': title,
                'author': author,
                'publication_year': year,
                'publisher': publisher,
                'about': about or f"{title} by {author}"
            }
        )

        linked = 0
        if wrestler_names:
            for wrestler_name in wrestler_names:
                wrestler = self.get_or_create_wrestler(wrestler_name)
                if wrestler and wrestler not in book.related_wrestlers.all():
                    book.related_wrestlers.add(wrestler)
                    linked += 1

        return created, linked

    def seed_autobiographies(self):
        """Seed wrestler autobiographies."""
        self.stdout.write('--- Seeding Autobiographies ---')
        created_count = 0
        linked_count = 0

        autobiographies = [
            # Mick Foley
            ('Have a Nice Day: A Tale of Blood and Sweatsocks', 'Mick Foley', 1999, 'ReganBooks',
             ['Mick Foley', 'Undertaker', 'Terry Funk', 'Cactus Jack'],
             'Mick Foley\'s first autobiography covering his hardcore wrestling career'),
            ('Foley is Good: And the Real World is Faker Than Wrestling', 'Mick Foley', 2001, 'ReganBooks',
             ['Mick Foley', 'The Rock', 'Triple H', 'Vince McMahon'],
             'Mick Foley\'s second autobiography'),
            ('The Hardcore Diaries', 'Mick Foley', 2007, 'Pocket Books',
             ['Mick Foley', 'Edge', 'Terry Funk'],
             'Behind the scenes of Mick Foley\'s 2006 WWE return'),
            ('Countdown to Lockdown', 'Mick Foley', 2010, 'Grand Central Publishing',
             ['Mick Foley', 'Sting', 'Kurt Angle'],
             'Mick Foley\'s TNA experiences'),

            # The Rock
            ('The Rock Says...', 'The Rock with Joe Layden', 2000, 'ReganBooks',
             ['The Rock', 'Stone Cold Steve Austin', 'Mankind', 'Triple H'],
             'The Rock\'s autobiography covering his rise to fame'),

            # Stone Cold Steve Austin
            ('The Stone Cold Truth', 'Steve Austin with Dennis Brent', 2003, 'Pocket Books',
             ['Stone Cold Steve Austin', 'The Rock', 'Vince McMahon', 'Triple H'],
             'Stone Cold Steve Austin\'s autobiography'),

            # Bret Hart
            ('Hitman: My Real Life in the Cartoon World of Wrestling', 'Bret Hart', 2007, 'Grand Central Publishing',
             ['Bret Hart', 'Shawn Michaels', 'Vince McMahon', 'Owen Hart', 'Ric Flair'],
             'Bret Hart\'s critically acclaimed autobiography'),

            # Ric Flair
            ('To Be the Man', 'Ric Flair with Keith Elliot Greenberg', 2004, 'Pocket Books',
             ['Ric Flair', 'Dusty Rhodes', 'Ricky Steamboat', 'Arn Anderson', 'Harley Race'],
             'Ric Flair\'s autobiography'),
            ('Second Nature: The Legacy of Ric Flair and the Rise of Charlotte', 'Ric Flair and Charlotte Flair', 2017, 'St. Martin\'s Press',
             ['Ric Flair', 'Charlotte Flair', 'Sasha Banks', 'Becky Lynch'],
             'Dual autobiography of Ric and Charlotte Flair'),

            # Hulk Hogan
            ('Hollywood Hulk Hogan', 'Hulk Hogan with Michael Jan Friedman', 2002, 'Pocket Books',
             ['Hulk Hogan', 'Randy Savage', 'Ultimate Warrior', 'Vince McMahon'],
             'Hulk Hogan\'s autobiography'),
            ('My Life Outside the Ring', 'Hulk Hogan', 2009, 'St. Martin\'s Press',
             ['Hulk Hogan'],
             'Hulk Hogan\'s personal life story'),

            # Chris Jericho
            ('A Lion\'s Tale: Around the World in Spandex', 'Chris Jericho', 2007, 'Grand Central Publishing',
             ['Chris Jericho', 'Eddie Guerrero', 'Dean Malenko', 'Chris Benoit'],
             'Chris Jericho\'s early career'),
            ('Undisputed: How to Become World Champion in 1,372 Easy Steps', 'Chris Jericho', 2011, 'Grand Central Publishing',
             ['Chris Jericho', 'Shawn Michaels', 'The Rock', 'Triple H'],
             'Chris Jericho\'s WWE career'),
            ('The Best in the World: At What I Have No Idea', 'Chris Jericho', 2014, 'Gotham Books',
             ['Chris Jericho', 'CM Punk', 'Dolph Ziggler'],
             'Chris Jericho\'s third autobiography'),
            ('No Is a Four-Letter Word', 'Chris Jericho', 2017, 'Hachette Books',
             ['Chris Jericho'],
             'Chris Jericho on success in business and life'),

            # Shawn Michaels
            ('Heartbreak & Triumph: The Shawn Michaels Story', 'Shawn Michaels with Aaron Feigenbaum', 2005, 'World Wrestling Entertainment',
             ['Shawn Michaels', 'Triple H', 'Bret Hart', 'Undertaker'],
             'Shawn Michaels\' autobiography'),
            ('Wrestling for My Life', 'Shawn Michaels', 2015, 'Zondervan',
             ['Shawn Michaels'],
             'Shawn Michaels on faith and wrestling'),

            # Kurt Angle
            ('It\'s True! It\'s True!', 'Kurt Angle with John Harper', 2001, 'ReganBooks',
             ['Kurt Angle', 'The Rock', 'Triple H', 'Stone Cold Steve Austin'],
             'Kurt Angle\'s story from Olympic gold to WWE'),

            # Edge
            ('Adam Copeland on Edge', 'Adam Copeland', 2004, 'Pocket Books',
             ['Edge', 'Christian', 'Hardy Boyz', 'Dudley Boyz'],
             'Edge\'s autobiography'),

            # Daniel Bryan
            ('Yes! My Improbable Journey to the Main Event of WrestleMania', 'Daniel Bryan with Craig Tello', 2015, 'St. Martin\'s Press',
             ['Daniel Bryan', 'Shawn Michaels', 'Triple H', 'John Cena'],
             'Daniel Bryan\'s journey to WrestleMania 30'),

            # Rey Mysterio
            ('Rey Mysterio: Behind the Mask', 'Rey Mysterio', 2009, 'Pocket Books',
             ['Rey Mysterio', 'Eddie Guerrero', 'Juventud Guerrera'],
             'Rey Mysterio\'s autobiography'),

            # William Regal
            ('Walking a Golden Mile', 'William Regal', 2005, 'World Wrestling Entertainment',
             ['William Regal', 'Fit Finlay'],
             'William Regal\'s journey from England to WWE'),

            # Roddy Piper
            ('In the Pit with Piper', 'Roddy Piper with Robert Picarello', 2002, 'Berkley Books',
             ['Roddy Piper', 'Hulk Hogan', 'Ric Flair'],
             'Roddy Piper\'s autobiography'),

            # Bobby Heenan
            ('Bobby the Brain: Wrestling\'s Bad Boy Tells All', 'Bobby Heenan with Steve Anderson', 2002, 'Triumph Books',
             ['Bobby Heenan', 'Andre the Giant', 'Hulk Hogan', 'Gorilla Monsoon'],
             'Bobby Heenan\'s autobiography'),

            # Jim Ross
            ('Slobberknocker: My Life in Wrestling', 'Jim Ross with Paul O\'Brien', 2017, 'Sports Publishing',
             ['Jim Ross', 'Stone Cold Steve Austin', 'The Rock', 'Vince McMahon'],
             'Jim Ross\'s autobiography'),
            ('Under the Black Hat', 'Jim Ross', 2020, 'Tiller Press',
             ['Jim Ross', 'Tony Schiavone', 'Kenny Omega'],
             'Jim Ross\'s experiences in AEW and beyond'),

            # Brock Lesnar
            ('Death Clutch: My Story of Determination, Domination, and Survival', 'Brock Lesnar with Paul Heyman', 2011, 'William Morrow',
             ['Brock Lesnar', 'Kurt Angle', 'Undertaker'],
             'Brock Lesnar\'s autobiography'),

            # Eric Bischoff
            ('Controversy Creates Cash', 'Eric Bischoff with Jeremy Roberts', 2006, 'Pocket Books',
             ['Eric Bischoff', 'Hulk Hogan', 'Kevin Nash', 'Scott Hall', 'Sting'],
             'Eric Bischoff\'s story of running WCW'),

            # Paul Heyman
            ('The Heyman Hustle', 'Paul Heyman', 2024, 'Gallery Books',
             ['Paul Heyman', 'Brock Lesnar', 'Roman Reigns', 'CM Punk'],
             'Paul Heyman\'s autobiography'),

            # Terry Funk
            ('Terry Funk: More Than Just Hardcore', 'Terry Funk with Scott E. Williams', 2005, 'Sports Publishing',
             ['Terry Funk', 'Mick Foley', 'Dusty Rhodes', 'Ric Flair'],
             'Terry Funk\'s autobiography'),

            # Jake Roberts
            ('The Snake Pit', 'Jake Roberts', 2023, 'Post Hill Press',
             ['Jake Roberts', 'Randy Savage', 'Ultimate Warrior'],
             'Jake Roberts\' autobiography'),

            # Lita
            ('Lita: A Less Traveled R.O.A.D.', 'Amy Dumas', 2003, 'ReganBooks',
             ['Lita', 'Hardy Boyz', 'Trish Stratus'],
             'Lita\'s autobiography'),

            # Chyna
            ('If They Only Knew', 'Chyna with Michael Angeli', 2001, 'ReganBooks',
             ['Chyna', 'Triple H', 'D-Generation X'],
             'Chyna\'s autobiography'),

            # Batista
            ('Batista Unleashed', 'Dave Batista with Jeremy Roberts', 2007, 'Pocket Books',
             ['Batista', 'Triple H', 'Ric Flair', 'Randy Orton'],
             'Batista\'s autobiography'),

            # Mark Henry
            ('What It Takes', 'Mark Henry', 2022, 'Gallery Books',
             ['Mark Henry'],
             'Mark Henry\'s autobiography'),

            # Mick Foley
            ('Saint Mick: My Journey From Hardcore Legend to Santa\'s Jolly Elf', 'Mick Foley', 2019, 'Mango',
             ['Mick Foley'],
             'Mick Foley\'s holiday-themed memoir'),

            # Jon Moxley
            ('Mox', 'Jon Moxley', 2024, 'Gallery Books',
             ['Jon Moxley', 'Roman Reigns', 'Seth Rollins', 'Dean Ambrose'],
             'Jon Moxley\'s autobiography'),

            # AJ Lee
            ('Crazy Is My Superpower', 'AJ Mendez', 2017, 'Crown Archetype',
             ['AJ Lee', 'CM Punk', 'Dolph Ziggler'],
             'AJ Lee\'s autobiography'),
        ]

        for book_data in autobiographies:
            c, l = self.create_book(*book_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} autobiographies, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_biographies(self):
        """Seed wrestler biographies."""
        self.stdout.write('--- Seeding Biographies ---')
        created_count = 0
        linked_count = 0

        biographies = [
            ('Andre the Giant: A Legendary Life', 'Michael Krugman', 2009, 'Pocket Books',
             ['Andre the Giant', 'Hulk Hogan'],
             'Biography of Andre the Giant'),
            ('Owen Hart: King of Pranks', 'Martha Hart', 2020, 'ECW Press',
             ['Owen Hart', 'Bret Hart'],
             'Memorial biography by Owen Hart\'s wife'),
            ('Pain and Passion: The History of Stampede Wrestling', 'Heath McCoy', 2005, 'CanWest Books',
             ['Bret Hart', 'Owen Hart', 'Stu Hart'],
             'History of the Hart family\'s Stampede Wrestling'),
            ('Sex, Lies, and Headlocks: The Real Story of Vince McMahon and World Wrestling Entertainment', 'Shaun Assael and Mike Mooneyham', 2002, 'Crown Publishers',
             ['Vince McMahon', 'Hulk Hogan', 'Stone Cold Steve Austin'],
             'History of WWE and Vince McMahon'),
            ('The Death of WCW', 'Bryan Alvarez and R.D. Reynolds', 2004, 'ECW Press',
             ['Eric Bischoff', 'Hulk Hogan', 'Goldberg', 'Sting'],
             'Chronicle of WCW\'s downfall'),
            ('Ring of Hell: The Story of Chris Benoit', 'Matthew Randazzo V', 2008, 'Phoenix Books',
             ['Chris Benoit', 'Eddie Guerrero', 'Dean Malenko'],
             'Biography examining Chris Benoit\'s life'),
            ('Crazy Like a Fox: The Definitive Chronicle of Brian Pillman', 'Liam O\'Rinn', 2022, 'ECW Press',
             ['Brian Pillman', 'Stone Cold Steve Austin', 'Ric Flair'],
             'Biography of Brian Pillman'),
            ('Chris & Nancy: The True Story of the Benoit Murder-Suicide', 'Irvin Muchnick', 2009, 'ECW Press',
             ['Chris Benoit'],
             'Investigative book on the Benoit tragedy'),
            ('Titan: The Story of Vince McMahon', 'Greg Oliver and Steve Johnson', 2023, 'ECW Press',
             ['Vince McMahon', 'Triple H', 'Stephanie McMahon'],
             'Biography of Vince McMahon'),
        ]

        for book_data in biographies:
            c, l = self.create_book(*book_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} biographies, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_wwe_books(self):
        """Seed WWE official publications."""
        self.stdout.write('--- Seeding WWE Publications ---')
        created_count = 0
        linked_count = 0

        wwe_books = [
            ('WWE Encyclopedia of Sports Entertainment', 'WWE', 2012, 'DK Publishing',
             ['Hulk Hogan', 'Stone Cold Steve Austin', 'The Rock', 'John Cena'],
             'Comprehensive WWE encyclopedia'),
            ('WWE Encyclopedia: The Definitive Guide to WWE', 'WWE', 2020, 'DK Publishing',
             ['Roman Reigns', 'John Cena', 'The Rock', 'Stone Cold Steve Austin'],
             'Updated WWE encyclopedia'),
            ('WWE 50', 'Kevin Sullivan', 2013, 'DK Publishing',
             ['Hulk Hogan', 'The Rock', 'Stone Cold Steve Austin', 'John Cena'],
             'Celebrating 50 years of WWE'),
            ('WWE Greatest Rivalries', 'Jake Black', 2014, 'DK Publishing',
             ['Stone Cold Steve Austin', 'The Rock', 'Shawn Michaels', 'Bret Hart'],
             'History of WWE\'s greatest feuds'),
            ('WWE Championship: A Look Back at 50 Years of WWE Championship History', 'Kevin Sullivan', 2011, 'Gallery Books',
             ['Bruno Sammartino', 'Hulk Hogan', 'Stone Cold Steve Austin', 'John Cena'],
             'History of the WWE Championship'),
            ('NXT: The Future Is Now', 'Jon Robinson', 2017, 'ECW Press',
             ['Finn Balor', 'Sami Zayn', 'Kevin Owens', 'Bayley', 'Sasha Banks'],
             'History of NXT'),
            ('Yes! Yes! Yes!: The Unauthorized History of WWE\'s Yes Movement', 'Jon Robinson', 2014, 'ECW Press',
             ['Daniel Bryan', 'CM Punk', 'Triple H'],
             'History of the Yes Movement'),
            ('The Monday Night War', 'Eric Bischoff', 2015, 'Pocket Books',
             ['Eric Bischoff', 'Vince McMahon', 'Hulk Hogan', 'Stone Cold Steve Austin'],
             'History of the Monday Night Wars'),
            ('The Attitude Era', 'Jon Robinson', 2015, 'DK Publishing',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Mick Foley'],
             'History of WWE\'s Attitude Era'),
            ('WWE Legends', 'Brian Shields', 2006, 'World Wrestling Entertainment',
             ['Hulk Hogan', 'Andre the Giant', 'Macho Man Randy Savage', 'Ultimate Warrior'],
             'Profiles of WWE Legends'),
            ('The WWE Book of Top 10s', 'Dean Miller', 2017, 'DK Publishing',
             ['John Cena', 'The Rock', 'Undertaker', 'Shawn Michaels'],
             'WWE rankings and lists'),
            ('WrestleMania: The Official Insider\'s Story', 'Brian Shields', 2009, 'DK Publishing',
             ['Hulk Hogan', 'Andre the Giant', 'Stone Cold Steve Austin', 'The Rock'],
             'History of WrestleMania'),
        ]

        for book_data in wwe_books:
            c, l = self.create_book(*book_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} WWE publications, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_history_books(self):
        """Seed wrestling history and reference books."""
        self.stdout.write('--- Seeding History/Reference Books ---')
        created_count = 0
        linked_count = 0

        history_books = [
            ('Squared Circle: Life, Death, and Professional Wrestling', 'David Shoemaker', 2013, 'Gotham Books',
             ['Eddie Guerrero', 'Chris Benoit', 'Owen Hart'],
             'Essays on wrestling history and mortality'),
            ('The Squared Circle: An Absolute Roundup of Wrestling Facts', 'David Shoemaker', 2023, 'Abrams Image',
             ['Roman Reigns', 'CM Punk', 'AEW Roster'],
             'Wrestling facts and history'),
            ('We Promised You a Great Main Event', 'Bill Hanstock', 2020, 'Harper',
             ['Vince McMahon', 'Stone Cold Steve Austin', 'John Cena'],
             'History of WWE'),
            ('Crazy Is My Superpower', 'AJ Mendez', 2017, 'Crown Archetype',
             ['AJ Lee'],
             'AJ Lee\'s story of overcoming mental health challenges'),
            ('National Wrestling Alliance: The Untold Story of the Monopoly That Strangled Pro Wrestling', 'Tim Hornbaker', 2007, 'ECW Press',
             ['Harley Race', 'Ric Flair', 'Dusty Rhodes'],
             'History of the NWA'),
            ('Capitol Revolution: The Rise of the McMahon Wrestling Empire', 'Tim Hornbaker', 2015, 'ECW Press',
             ['Vince McMahon', 'Vince McMahon Sr.', 'Bruno Sammartino'],
             'History of the McMahon family'),
            ('Young Bucks: Killing the Business from Backyards to the Big Leagues', 'Matt Jackson and Nick Jackson', 2020, 'Dey Street Books',
             ['Young Bucks', 'Kenny Omega', 'Cody Rhodes'],
             'The Young Bucks\' story'),
            ('The Pro Wrestling Hall of Fame: The Tag Teams', 'Greg Oliver and Steven Johnson', 2005, 'ECW Press',
             ['Road Warriors', 'Dudley Boyz', 'Hardy Boyz'],
             'History of wrestling tag teams'),
            ('The Pro Wrestling Hall of Fame: The Heels', 'Greg Oliver and Steven Johnson', 2007, 'ECW Press',
             ['Ric Flair', 'Ted DiBiase', 'Bobby Heenan'],
             'History of wrestling villains'),
            ('The Pro Wrestling Hall of Fame: Heroes & Icons', 'Greg Oliver and Steven Johnson', 2012, 'ECW Press',
             ['Hulk Hogan', 'Bruno Sammartino', 'Dusty Rhodes'],
             'History of wrestling heroes'),
            ('Sisterhood of the Squared Circle', 'Pat Laprade and Dan Murphy', 2017, 'ECW Press',
             ['Trish Stratus', 'Lita', 'Fabulous Moolah', 'Mae Young'],
             'History of women\'s wrestling'),
            ('Apter Inside WWE: The Incredible Stories Behind the Legends', 'Bill Apter', 2017, 'ECW Press',
             ['Hulk Hogan', 'Ric Flair', 'Ultimate Warrior'],
             'Bill Apter\'s wrestling photography stories'),
        ]

        for book_data in history_books:
            c, l = self.create_book(*book_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} history books, {linked_count} wrestler links')
        return created_count, linked_count
