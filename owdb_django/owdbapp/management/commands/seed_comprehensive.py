"""
Comprehensive database seeding command for OWDB.
Seeds historic wrestlers, promoters, managers, referees, journalists, trainers,
and all other wrestling-related entities.

All data is factual information from public sources.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Match, Title, Venue,
    VideoGame, Podcast, Book, Special, Stable
)


class Command(BaseCommand):
    help = 'Comprehensive database seeding with wrestling personalities and entities'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Seed specific category: wrestlers, promotions, titles, venues, stables, media, all',
            default='all'
        )

    def handle(self, *args, **options):
        category = options.get('category', 'all')

        self.stdout.write(self.style.SUCCESS(f'\n=== Comprehensive OWDB Seeding ({category}) ===\n'))

        if category in ['all', 'wrestlers']:
            self.seed_wrestlers()
        if category in ['all', 'promotions']:
            self.seed_promotions()
        if category in ['all', 'titles']:
            self.seed_titles()
        if category in ['all', 'venues']:
            self.seed_venues()
        if category in ['all', 'stables']:
            self.seed_stables()
        if category in ['all', 'media']:
            self.seed_media()

        self.stdout.write(self.style.SUCCESS('\n=== Seeding Complete ===\n'))
        self.print_stats()

    def print_stats(self):
        self.stdout.write(f'Wrestlers: {Wrestler.objects.count()}')
        self.stdout.write(f'Promotions: {Promotion.objects.count()}')
        self.stdout.write(f'Titles: {Title.objects.count()}')
        self.stdout.write(f'Venues: {Venue.objects.count()}')
        self.stdout.write(f'Stables: {Stable.objects.count()}')
        self.stdout.write(f'Video Games: {VideoGame.objects.count()}')
        self.stdout.write(f'Podcasts: {Podcast.objects.count()}')
        self.stdout.write(f'Books: {Book.objects.count()}')
        self.stdout.write(f'Specials: {Special.objects.count()}')

    def get_or_create_wrestler(self, name, **kwargs):
        """Get or create wrestler, returns (wrestler, created)."""
        wrestler, created = Wrestler.objects.get_or_create(
            name=name,
            defaults=kwargs
        )
        if created:
            self.stdout.write(f'  + {name}')
        return wrestler, created

    def seed_wrestlers(self):
        """Seed comprehensive list of wrestling personalities."""
        self.stdout.write('\n--- Seeding Wrestlers & Wrestling Personalities ---\n')

        # LEGENDARY ERA (Pre-1980s)
        self.stdout.write('  [Legendary Era - Pre-1980s]')
        legends = [
            {"name": "Lou Thesz", "real_name": "Aloysius Martin Thesz", "debut_year": 1932, "retirement_year": 1990, "hometown": "St. Louis, Missouri", "nationality": "American", "finishers": "Lou Thesz Press, STF", "about": "Six-time NWA World Heavyweight Champion, widely considered one of the greatest professional wrestlers of all time. His career spanned six decades."},
            {"name": "Gorgeous George", "real_name": "George Raymond Wagner", "debut_year": 1932, "retirement_year": 1962, "hometown": "Seward, Nebraska", "nationality": "American", "about": "Pioneer of character-based wrestling and one of the first TV wrestling stars. His flamboyant persona influenced generations of wrestlers including Muhammad Ali."},
            {"name": "Bruno Sammartino", "real_name": "Bruno Leopoldo Francesco Sammartino", "debut_year": 1959, "retirement_year": 1981, "hometown": "Pizzoferrato, Italy", "nationality": "Italian-American", "finishers": "Bearhug", "about": "The Living Legend held the WWWF Championship for over 11 years combined across two reigns, the longest in company history."},
            {"name": "Buddy Rogers", "real_name": "Herman Gustav Rohde Jr.", "debut_year": 1939, "retirement_year": 1982, "hometown": "Camden, New Jersey", "nationality": "American", "finishers": "Figure Four Leglock", "about": "The Nature Boy was the first WWWF Champion and one of the most influential heels in wrestling history. Ric Flair adopted his persona."},
            {"name": "Verne Gagne", "real_name": "LaVerne Clarence Gagne", "debut_year": 1949, "retirement_year": 1981, "hometown": "Corcoran, Minnesota", "nationality": "American", "finishers": "Sleeper Hold", "about": "Ten-time AWA World Heavyweight Champion and founder of the American Wrestling Association. Trained many future stars including Ric Flair."},
            {"name": "Pat Patterson", "real_name": "Pierre Clermont", "debut_year": 1958, "retirement_year": 1984, "hometown": "Montreal, Quebec, Canada", "nationality": "Canadian", "about": "First Intercontinental Champion and legendary WWE creative mind. Created the Royal Rumble match concept."},
            {"name": "Killer Kowalski", "real_name": "Edward Władysław Spulnik", "debut_year": 1947, "retirement_year": 1977, "hometown": "Windsor, Ontario, Canada", "nationality": "Canadian-American", "finishers": "Claw Hold", "about": "Legendary heel and trainer who operated a wrestling school that produced Triple H, Chyna, and others."},
            {"name": "Antonino Rocca", "real_name": "Antonino Biasetton", "debut_year": 1942, "retirement_year": 1975, "hometown": "Treviso, Italy", "nationality": "Italian-Argentine", "about": "High-flying pioneer who popularized acrobatic wrestling in the United States. A major draw at Madison Square Garden."},
            {"name": "Freddie Blassie", "real_name": "Frederick Kenneth Blassman", "debut_year": 1935, "retirement_year": 1974, "hometown": "St. Louis, Missouri", "nationality": "American", "aliases": "Classy Freddie Blassie", "about": "Legendary heel wrestler who later became one of wrestling's most famous managers, leading stars like Iron Sheik and Nikolai Volkoff."},
            {"name": "The Sheik", "real_name": "Edward George Farhat", "debut_year": 1949, "retirement_year": 1998, "hometown": "Lansing, Michigan", "nationality": "American", "aliases": "Original Sheik", "about": "Pioneering hardcore wrestler known for his wild, bloody matches. Uncle of Sabu and promoter of Big Time Wrestling in Detroit."},
            {"name": "Mil Máscaras", "real_name": "Aarón Rodríguez Arellano", "debut_year": 1965, "hometown": "San Luis Potosí, Mexico", "nationality": "Mexican", "finishers": "Flying Cross Body", "about": "One of the most famous luchadors in history, known for wearing different masks. First masked wrestler to appear in Madison Square Garden."},
            {"name": "El Santo", "real_name": "Rodolfo Guzmán Huerta", "debut_year": 1934, "retirement_year": 1982, "hometown": "Tulancingo, Mexico", "nationality": "Mexican", "about": "The most iconic figure in lucha libre history. A cultural icon in Mexico who starred in dozens of films and never publicly removed his mask."},
            {"name": "Blue Demon", "real_name": "Alejandro Muñoz Moreno", "debut_year": 1948, "retirement_year": 1989, "hometown": "Mexico City, Mexico", "nationality": "Mexican", "about": "Legendary luchador and rival of El Santo. One of the most popular Mexican wrestlers of all time."},
            {"name": "Giant Baba", "real_name": "Shohei Baba", "debut_year": 1960, "retirement_year": 1999, "hometown": "Niigata, Japan", "nationality": "Japanese", "finishers": "Neckbreaker Drop", "about": "Founder of All Japan Pro Wrestling and one of the most respected figures in Japanese wrestling history."},
            {"name": "Antonio Inoki", "real_name": "Kanji Inoki", "debut_year": 1960, "retirement_year": 1998, "hometown": "Yokohama, Japan", "nationality": "Japanese", "finishers": "Enzuigiri, Octopus Hold", "about": "Founder of New Japan Pro-Wrestling and one of the most important figures in puroresu. Famous for his mixed martial arts match against Muhammad Ali."},
            {"name": "Rikidozan", "real_name": "Kim Sin-rak", "debut_year": 1951, "retirement_year": 1963, "hometown": "South Hamgyong, Korea", "nationality": "Korean-Japanese", "about": "The Father of Puroresu who founded the Japan Pro Wrestling Alliance. A national hero in post-war Japan."},
            {"name": "Nick Bockwinkel", "real_name": "Nicholas Warren Bockwinkel", "debut_year": 1954, "retirement_year": 1987, "hometown": "St. Louis, Missouri", "nationality": "American", "finishers": "Piledriver", "about": "Four-time AWA World Heavyweight Champion known for his technical skill and articulate promos."},
            {"name": "Harley Race", "real_name": "Harley Leland Race", "debut_year": 1959, "retirement_year": 1991, "hometown": "Quitman, Missouri", "nationality": "American", "finishers": "Diving Headbutt, Piledriver", "about": "Eight-time NWA World Heavyweight Champion and one of the toughest men in wrestling history. Later known as King Harley Race in WWF."},
            {"name": "Dory Funk Jr.", "real_name": "Dorrance Wilhelm Funk Jr.", "debut_year": 1963, "hometown": "Hammond, Indiana", "nationality": "American", "finishers": "Spinning Toe Hold", "about": "Former NWA World Heavyweight Champion and legendary trainer. Brother of Terry Funk."},
            {"name": "Terry Funk", "real_name": "Terrence Funk", "debut_year": 1965, "retirement_year": 2017, "hometown": "Amarillo, Texas", "nationality": "American", "finishers": "Spinning Toe Hold, Moonsault", "about": "Hardcore legend and former NWA World Heavyweight Champion. Known for his extreme matches and multiple retirements."},
            {"name": "Dusty Rhodes", "real_name": "Virgil Riley Runnels Jr.", "debut_year": 1968, "retirement_year": 2007, "hometown": "Austin, Texas", "nationality": "American", "finishers": "Bionic Elbow", "aliases": "The American Dream", "about": "Three-time NWA World Heavyweight Champion and one of the greatest talkers in wrestling history. Father of Cody and Dustin Rhodes."},
            {"name": "Jack Brisco", "real_name": "Freddie Joe Brisco", "debut_year": 1965, "retirement_year": 1985, "hometown": "Blackwell, Oklahoma", "nationality": "American", "finishers": "Figure Four Leglock", "about": "Two-time NWA World Heavyweight Champion and former NCAA wrestling champion. Known for his technical excellence."},
            {"name": "Jerry Brisco", "real_name": "Floyd Gerald Brisco", "debut_year": 1969, "hometown": "Blackwell, Oklahoma", "nationality": "American", "about": "Former NWA and WWF Tag Team Champion, brother of Jack Brisco. Later became a WWE road agent and producer."},
            {"name": "Pedro Morales", "real_name": "Pedro Antonio Morales Rivera", "debut_year": 1959, "retirement_year": 1987, "hometown": "Culebra, Puerto Rico", "nationality": "Puerto Rican", "finishers": "Boston Crab", "about": "First Triple Crown Champion in WWF/WWE history, holding the WWF, Intercontinental, and Tag Team titles."},
            {"name": "Bob Backlund", "real_name": "Robert Louis Backlund", "debut_year": 1973, "hometown": "Princeton, Minnesota", "nationality": "American", "finishers": "Crossface Chickenwing", "about": "Held the WWF Championship for nearly six years in the late 1970s and early 1980s. Two-time WWF Champion."},
        ]

        for data in legends:
            self.get_or_create_wrestler(**data)

        # GOLDEN ERA (1980s)
        self.stdout.write('\n  [Golden Era - 1980s]')
        golden_era = [
            {"name": "Hulk Hogan", "real_name": "Terry Gene Bollea", "debut_year": 1977, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Leg Drop, Atomic Leg Drop", "aliases": "Hollywood Hogan, The Immortal", "about": "Six-time WWF Champion and the face of professional wrestling during the 1980s. Main evented the first nine WrestleManias."},
            {"name": "Andre the Giant", "real_name": "André René Roussimoff", "debut_year": 1966, "retirement_year": 1992, "hometown": "Coulommiers, France", "nationality": "French", "finishers": "Sitdown Splash", "aliases": "The Eighth Wonder of the World", "about": "Legendary giant who was undefeated for 15 years. His WrestleMania III match against Hulk Hogan is one of the most famous in history."},
            {"name": "Randy Savage", "real_name": "Randall Mario Poffo", "debut_year": 1973, "retirement_year": 2005, "hometown": "Columbus, Ohio", "nationality": "American", "finishers": "Flying Elbow Drop", "aliases": "Macho Man", "about": "Two-time WWF Champion known for his intensity and iconic promos. His WrestleMania III match against Ricky Steamboat is considered one of the greatest ever."},
            {"name": "Ricky Steamboat", "real_name": "Richard Henry Blood", "debut_year": 1976, "hometown": "Honolulu, Hawaii", "nationality": "American", "finishers": "Diving Crossbody", "aliases": "The Dragon", "about": "One of the greatest technical wrestlers of all time. His matches against Randy Savage and Ric Flair are legendary."},
            {"name": "Roddy Piper", "real_name": "Roderick George Toombs", "debut_year": 1969, "retirement_year": 2011, "hometown": "Glasgow, Scotland", "nationality": "Canadian", "finishers": "Sleeper Hold", "aliases": "Rowdy, Hot Rod", "about": "One of the greatest heels and talkers in wrestling history. Host of Piper's Pit and main evented the first WrestleMania."},
            {"name": "Jake Roberts", "real_name": "Aurelian Smith Jr.", "debut_year": 1975, "hometown": "Stone Mountain, Georgia", "nationality": "American", "finishers": "DDT", "aliases": "Jake The Snake", "about": "Revolutionary promo artist who invented the DDT. Known for his dark, psychological character work."},
            {"name": "Ted DiBiase", "real_name": "Theodore Marvin DiBiase Sr.", "debut_year": 1975, "hometown": "Omaha, Nebraska", "nationality": "American", "finishers": "Million Dollar Dream", "aliases": "The Million Dollar Man", "about": "One of the greatest heels in WWF history. Created the Million Dollar Championship."},
            {"name": "Junkyard Dog", "real_name": "Sylvester Ritter", "debut_year": 1977, "retirement_year": 1998, "hometown": "Charlotte, North Carolina", "nationality": "American", "about": "Popular babyface who was one of the first major African American stars in the WWF."},
            {"name": "Tito Santana", "real_name": "Merced Solis", "debut_year": 1977, "hometown": "Tocula, Mexico", "nationality": "American", "finishers": "Flying Forearm", "about": "Two-time WWF Intercontinental Champion and popular babyface of the 1980s."},
            {"name": "Greg Valentine", "real_name": "Jonathan Anthony Wisniski Jr.", "debut_year": 1970, "hometown": "Seattle, Washington", "nationality": "American", "finishers": "Figure Four Leglock", "aliases": "The Hammer", "about": "Former Intercontinental and Tag Team Champion known for his technical wrestling and hard-hitting style."},
            {"name": "Don Muraco", "real_name": "Donald Muraco", "debut_year": 1970, "hometown": "Sunset Beach, Hawaii", "nationality": "American", "finishers": "Tombstone Piledriver", "aliases": "The Magnificent", "about": "Two-time WWF Intercontinental Champion and underrated performer of the 1980s."},
            {"name": "Iron Sheik", "real_name": "Hossein Khosrow Ali Vaziri", "debut_year": 1972, "retirement_year": 1997, "hometown": "Tehran, Iran", "nationality": "Iranian-American", "finishers": "Camel Clutch", "about": "Former WWF Champion who defeated Bob Backlund. One of the most hated heels of the 1980s."},
            {"name": "Nikolai Volkoff", "real_name": "Josip Nikolai Peruzović", "debut_year": 1968, "retirement_year": 2000, "hometown": "Split, Croatia", "nationality": "Croatian-American", "about": "Tag team partner of Iron Sheik and classic foreign heel of the 1980s."},
            {"name": "Paul Orndorff", "real_name": "Paul Parlette Orndorff Jr.", "debut_year": 1976, "retirement_year": 2000, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Piledriver", "aliases": "Mr. Wonderful", "about": "Main evented the first WrestleMania alongside Roddy Piper against Hulk Hogan and Mr. T."},
            {"name": "Superstar Billy Graham", "real_name": "Eldridge Wayne Coleman", "debut_year": 1969, "retirement_year": 1987, "hometown": "Phoenix, Arizona", "nationality": "American", "finishers": "Bearhug", "about": "Former WWF Champion whose flamboyant style influenced Hulk Hogan, Jesse Ventura, and many others."},
            {"name": "Jimmy Snuka", "real_name": "James Wiley Smith", "debut_year": 1969, "retirement_year": 2010, "hometown": "Fiji", "nationality": "Fijian-American", "finishers": "Superfly Splash", "aliases": "Superfly", "about": "High-flying pioneer whose Superfly Splash from the top of the cage is one of the most iconic images in wrestling."},
            {"name": "Sgt. Slaughter", "real_name": "Robert Remus", "debut_year": 1972, "hometown": "Parris Island, South Carolina", "nationality": "American", "finishers": "Cobra Clutch", "about": "Former WWF Champion known for his military persona. Also known for his controversial Iraqi sympathizer character."},
            {"name": "Big John Studd", "real_name": "John William Minton", "debut_year": 1972, "retirement_year": 1989, "hometown": "Butler, Pennsylvania", "nationality": "American", "about": "Winner of the 1989 Royal Rumble. Part of the legendary feud with Andre the Giant."},
            {"name": "King Kong Bundy", "real_name": "Christopher Alan Pallies", "debut_year": 1981, "retirement_year": 2007, "hometown": "Atlantic City, New Jersey", "nationality": "American", "finishers": "Big Splash, Atlantic City Avalanche", "about": "Massive heel who main evented WrestleMania 2 against Hulk Hogan in a steel cage."},
            {"name": "Hercules", "real_name": "Raymond Fernandez", "debut_year": 1978, "retirement_year": 2000, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Full Nelson", "aliases": "Hercules Hernandez", "about": "Powerful heel who later became a popular babyface in WWF."},
            {"name": "Koko B. Ware", "real_name": "James Ware", "debut_year": 1978, "hometown": "Union City, Tennessee", "nationality": "American", "aliases": "The Birdman", "about": "High-flying fan favorite known for his pet macaw Frankie."},
            {"name": "Brutus Beefcake", "real_name": "Edward Harrison Leslie", "debut_year": 1977, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Sleeper Hold", "aliases": "The Barber", "about": "Popular tag team partner and friend of Hulk Hogan who became known for cutting opponents' hair."},
            {"name": "Honky Tonk Man", "real_name": "Roy Wayne Farris", "debut_year": 1977, "hometown": "Memphis, Tennessee", "nationality": "American", "finishers": "Shake, Rattle and Roll", "about": "Longest-reigning Intercontinental Champion in WWF history with a 454-day reign."},
            {"name": "Rick Rude", "real_name": "Richard Erwin Rood", "debut_year": 1982, "retirement_year": 1994, "hometown": "Robbinsdale, Minnesota", "nationality": "American", "finishers": "Rude Awakening", "aliases": "Ravishing Rick Rude", "about": "Former Intercontinental Champion known for his physique and charisma. One of the few to work for WWF and WCW simultaneously."},
            {"name": "Mr. Perfect", "real_name": "Curt Hennig", "debut_year": 1980, "retirement_year": 2002, "hometown": "Robbinsdale, Minnesota", "nationality": "American", "finishers": "Perfect-Plex", "aliases": "Curt Hennig", "about": "Two-time Intercontinental Champion known for his incredible athleticism and Perfect-Plex finisher."},
        ]

        for data in golden_era:
            self.get_or_create_wrestler(**data)

        # ATTITUDE ERA (1990s-early 2000s)
        self.stdout.write('\n  [Attitude Era - 1990s-2000s]')
        attitude_era = [
            {"name": "Bret Hart", "real_name": "Bret Sergeant Hart", "debut_year": 1978, "hometown": "Calgary, Alberta, Canada", "nationality": "Canadian", "finishers": "Sharpshooter", "aliases": "The Hitman, The Excellence of Execution", "about": "Five-time WWF Champion and leader of the Hart Foundation. Considered one of the greatest technical wrestlers ever."},
            {"name": "Owen Hart", "real_name": "Owen James Hart", "debut_year": 1986, "retirement_year": 1999, "hometown": "Calgary, Alberta, Canada", "nationality": "Canadian", "finishers": "Sharpshooter", "about": "Two-time Tag Team Champion and former Intercontinental Champion. Tragically died during a WWF event in 1999."},
            {"name": "British Bulldog", "real_name": "David Boy Smith", "debut_year": 1978, "retirement_year": 2002, "hometown": "Golborne, England", "nationality": "British", "finishers": "Running Powerslam", "aliases": "Davey Boy Smith", "about": "Former European Champion who main evented SummerSlam 1992 at Wembley Stadium against Bret Hart."},
            {"name": "Jim Neidhart", "real_name": "James Henry Neidhart", "debut_year": 1979, "retirement_year": 2007, "hometown": "Tampa, Florida", "nationality": "American", "aliases": "The Anvil", "about": "Tag team partner of Bret Hart as The Hart Foundation. Father of Natalya."},
            {"name": "Shawn Michaels", "real_name": "Michael Shawn Hickenbottom", "debut_year": 1984, "retirement_year": 2010, "hometown": "San Antonio, Texas", "nationality": "American", "finishers": "Sweet Chin Music, Superkick", "aliases": "HBK, The Heartbreak Kid, The Showstopper", "about": "Four-time WWF/WWE Champion often called the greatest in-ring performer of all time. Mr. WrestleMania."},
            {"name": "Diesel", "real_name": "Kevin Scott Nash", "debut_year": 1990, "hometown": "Detroit, Michigan", "nationality": "American", "finishers": "Jackknife Powerbomb", "aliases": "Kevin Nash, Big Daddy Cool", "about": "Former WWF Champion as Diesel, later a founding member of the nWo as Kevin Nash."},
            {"name": "Razor Ramon", "real_name": "Scott Oliver Hall", "debut_year": 1984, "retirement_year": 2010, "hometown": "St. Mary's County, Maryland", "nationality": "American", "finishers": "Razor's Edge", "aliases": "Scott Hall, The Bad Guy", "about": "Four-time Intercontinental Champion, later founding member of the nWo."},
            {"name": "Yokozuna", "real_name": "Rodney Agatupu Anoa'i", "debut_year": 1984, "retirement_year": 1998, "hometown": "San Francisco, California", "nationality": "American", "finishers": "Banzai Drop", "about": "Two-time WWF Champion and 1993 Royal Rumble winner. Part of the legendary Anoa'i family."},
            {"name": "Lex Luger", "real_name": "Lawrence Wendell Pfohl", "debut_year": 1985, "hometown": "Chicago, Illinois", "nationality": "American", "finishers": "Torture Rack, Running Forearm", "aliases": "The Total Package, Narcissist", "about": "Former WCW World Heavyweight Champion and main eventer in both WWF and WCW."},
            {"name": "Sid Vicious", "real_name": "Sidney Raymond Eudy", "debut_year": 1987, "hometown": "West Memphis, Arkansas", "nationality": "American", "finishers": "Powerbomb", "aliases": "Sid Justice, Sycho Sid", "about": "Two-time WWF Champion and two-time WCW Champion. Known for his intense persona."},
            {"name": "Vader", "real_name": "Leon Allen White", "debut_year": 1985, "retirement_year": 2017, "hometown": "Boulder, Colorado", "nationality": "American", "finishers": "Vader Bomb, Powerbomb", "aliases": "Big Van Vader", "about": "Three-time WCW World Heavyweight Champion and one of the most physically imposing wrestlers ever."},
            {"name": "Mankind", "real_name": "Michael Francis Foley", "debut_year": 1986, "hometown": "Bloomington, Indiana", "nationality": "American", "finishers": "Mandible Claw, Double Arm DDT", "aliases": "Mick Foley, Cactus Jack, Dude Love", "about": "Three-time WWF Champion known for his hardcore style. Famous for his Hell in a Cell match with Undertaker."},
            {"name": "Triple H", "real_name": "Paul Michael Levesque", "debut_year": 1992, "hometown": "Nashua, New Hampshire", "nationality": "American", "finishers": "Pedigree", "aliases": "Hunter Hearst Helmsley, The Game, The Cerebral Assassin", "about": "14-time world champion, founder of DX, and now WWE's Chief Content Officer."},
            {"name": "X-Pac", "real_name": "Sean Michael Waltman", "debut_year": 1989, "hometown": "Minneapolis, Minnesota", "nationality": "American", "finishers": "X-Factor, Bronco Buster", "aliases": "1-2-3 Kid, Syxx", "about": "Member of both DX and the nWo. Known for his high-flying style."},
            {"name": "Road Dogg", "real_name": "Brian Gerard James", "debut_year": 1994, "hometown": "Marietta, Georgia", "nationality": "American", "finishers": "Pump Handle Slam", "aliases": "Brian James, The Roadie", "about": "Former Tag Team Champion as part of D-Generation X with Billy Gunn."},
            {"name": "Billy Gunn", "real_name": "Monty Kip Sopp", "debut_year": 1989, "hometown": "Orlando, Florida", "nationality": "American", "finishers": "Famouser", "aliases": "Mr. Ass, Bad Ass", "about": "Multiple time Tag Team Champion as part of the New Age Outlaws and DX."},
            {"name": "Mark Henry", "real_name": "Mark Jerrold Henry", "debut_year": 1996, "hometown": "Silsbee, Texas", "nationality": "American", "finishers": "World's Strongest Slam", "aliases": "The World's Strongest Man, Sexual Chocolate", "about": "Former World Heavyweight Champion and ECW Champion. Olympic weightlifter turned wrestler."},
            {"name": "D-Von Dudley", "real_name": "Devon Hughes", "debut_year": 1995, "hometown": "New York City, New York", "nationality": "American", "finishers": "Saving Grace", "aliases": "D-Von, Reverend D-Von", "about": "Ten-time WWE Tag Team Champion as part of The Dudley Boyz with Bubba Ray."},
            {"name": "Bubba Ray Dudley", "real_name": "Mark LoMonaco", "debut_year": 1991, "hometown": "Queens, New York", "nationality": "American", "finishers": "Bubba Bomb, Bubba Cutter", "aliases": "Bully Ray", "about": "Ten-time WWE Tag Team Champion as part of The Dudley Boyz. Known for table spots."},
            {"name": "Jeff Hardy", "real_name": "Jeffrey Nero Hardy", "debut_year": 1994, "hometown": "Cameron, North Carolina", "nationality": "American", "finishers": "Swanton Bomb, Twist of Fate", "aliases": "The Charismatic Enigma", "about": "Two-time WWE Champion known for his high-risk maneuvers and colorful appearance."},
            {"name": "Matt Hardy", "real_name": "Matthew Moore Hardy", "debut_year": 1994, "hometown": "Cameron, North Carolina", "nationality": "American", "finishers": "Twist of Fate, Side Effect", "aliases": "Big Money Matt, Broken Matt Hardy", "about": "Multiple time tag team champion and singles competitor. Brother of Jeff Hardy."},
            {"name": "Lita", "real_name": "Amy Christine Dumas", "debut_year": 1999, "retirement_year": 2006, "hometown": "Fort Lauderdale, Florida", "nationality": "American", "finishers": "Moonsault, Twist of Fate", "about": "Four-time Women's Champion and member of Team Xtreme with the Hardy Boyz."},
            {"name": "Trish Stratus", "real_name": "Patricia Anne Stratigeas", "debut_year": 2000, "retirement_year": 2006, "hometown": "Toronto, Ontario, Canada", "nationality": "Canadian", "finishers": "Stratusfaction, Chick Kick", "about": "Seven-time Women's Champion, considered the greatest female wrestler in WWE history."},
            {"name": "Chyna", "real_name": "Joan Marie Laurer", "debut_year": 1997, "retirement_year": 2001, "hometown": "Rochester, New York", "nationality": "American", "finishers": "Pedigree, Low Blow", "aliases": "The Ninth Wonder of the World", "about": "Former Intercontinental Champion and the only female member of DX. Pioneered intergender wrestling."},
            {"name": "Kurt Angle", "real_name": "Kurt Steven Angle", "debut_year": 1998, "retirement_year": 2019, "hometown": "Pittsburgh, Pennsylvania", "nationality": "American", "finishers": "Angle Slam, Ankle Lock", "about": "Olympic gold medalist and six-time world champion. Known for his 'Three I's': Intensity, Integrity, Intelligence."},
            {"name": "Chris Benoit", "real_name": "Christopher Michael Benoit", "debut_year": 1985, "retirement_year": 2007, "hometown": "Montreal, Quebec, Canada", "nationality": "Canadian", "finishers": "Crippler Crossface, Diving Headbutt", "aliases": "The Canadian Crippler, The Rabid Wolverine", "about": "Former World Heavyweight Champion known for his technical wrestling. His career ended in tragedy in 2007."},
            {"name": "Eddie Guerrero", "real_name": "Eduardo Gory Guerrero Llanes", "debut_year": 1987, "retirement_year": 2005, "hometown": "El Paso, Texas", "nationality": "American", "finishers": "Frog Splash, Three Amigos", "aliases": "Latino Heat", "about": "Former WWE Champion known for his charisma and 'Lie, Cheat, and Steal' persona. Beloved by fans worldwide."},
            {"name": "Rey Mysterio", "real_name": "Oscar Gutiérrez Rubio", "debut_year": 1989, "hometown": "Chula Vista, California", "nationality": "American", "finishers": "619, West Coast Pop", "aliases": "Rey Mysterio Jr., The Master of the 619", "about": "Former World Heavyweight Champion and the greatest cruiserweight in wrestling history."},
            {"name": "Dean Malenko", "real_name": "Dean Simon", "debut_year": 1979, "retirement_year": 2001, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Texas Cloverleaf", "aliases": "The Man of 1,000 Holds, The Iceman", "about": "Four-time WCW Cruiserweight Champion known for his technical mastery."},
            {"name": "Perry Saturn", "real_name": "Perry Arthur Satullo", "debut_year": 1990, "retirement_year": 2004, "hometown": "Cleveland, Ohio", "nationality": "American", "finishers": "Rings of Saturn", "about": "Former Tag Team Champion in both WCW and WWF."},
        ]

        for data in attitude_era:
            self.get_or_create_wrestler(**data)

        # RUTHLESS AGGRESSION ERA (2002-2008)
        self.stdout.write('\n  [Ruthless Aggression Era - 2002-2008]')
        ruthless_era = [
            {"name": "Batista", "real_name": "David Michael Bautista Jr.", "debut_year": 2002, "retirement_year": 2019, "hometown": "Washington, D.C.", "nationality": "American", "finishers": "Batista Bomb, Spinebuster", "aliases": "The Animal, Big Dave", "about": "Six-time world champion and member of Evolution. Transitioned to a successful Hollywood career."},
            {"name": "John Cena", "real_name": "John Felix Anthony Cena Jr.", "debut_year": 2000, "hometown": "West Newbury, Massachusetts", "nationality": "American", "finishers": "Attitude Adjustment, STF", "aliases": "The Champ, The Face That Runs the Place", "about": "16-time world champion, tied for most all-time. The face of WWE for over a decade."},
            {"name": "Randy Orton", "real_name": "Randal Keith Orton", "debut_year": 2000, "hometown": "St. Louis, Missouri", "nationality": "American", "finishers": "RKO, Punt Kick", "aliases": "The Viper, The Legend Killer, The Apex Predator", "about": "14-time world champion and youngest World Heavyweight Champion in history at age 24."},
            {"name": "JBL", "real_name": "John Charles Layfield", "debut_year": 1992, "retirement_year": 2009, "hometown": "Sweetwater, Texas", "nationality": "American", "finishers": "Clothesline from Hell", "aliases": "John Bradshaw Layfield, Bradshaw", "about": "Former WWE Champion with the longest reign of the SmackDown era at 280 days."},
            {"name": "Shelton Benjamin", "real_name": "Shelton Benjamin", "debut_year": 2000, "hometown": "Orangeburg, South Carolina", "nationality": "American", "finishers": "Paydirt, T-Bone Suplex", "aliases": "The Gold Standard", "about": "Three-time Intercontinental Champion known for his incredible athleticism."},
            {"name": "Bobby Lashley", "real_name": "Franklin Roberto Lashley", "debut_year": 2004, "hometown": "Junction City, Kansas", "nationality": "American", "finishers": "Spear, Hurt Lock", "aliases": "The All Mighty", "about": "Two-time WWE Champion and former ECW Champion. Also competed in MMA."},
            {"name": "MVP", "real_name": "Alvin Antonio Burke Jr.", "debut_year": 2003, "hometown": "Miami, Florida", "nationality": "American", "finishers": "Playmaker, Drive-By Kick", "aliases": "Montel Vontavious Porter", "about": "Longest-reigning United States Champion in WWE history."},
            {"name": "Mr. Kennedy", "real_name": "Kenneth Anderson", "debut_year": 2000, "hometown": "Green Bay, Wisconsin", "nationality": "American", "finishers": "Mic Check, Green Bay Plunge", "aliases": "Ken Anderson, Mr. Anderson", "about": "United States Champion known for announcing his own name from the ring."},
            {"name": "Umaga", "real_name": "Edward Smith Fatu", "debut_year": 1995, "retirement_year": 2009, "hometown": "San Francisco, California", "nationality": "American", "finishers": "Samoan Spike", "aliases": "Jamal", "about": "Former Intercontinental Champion and member of the Anoa'i family."},
            {"name": "Carlito", "real_name": "Carlos Edwin Colón Jr.", "debut_year": 2003, "hometown": "San Juan, Puerto Rico", "nationality": "Puerto Rican", "finishers": "Backstabber", "about": "Former Intercontinental and United States Champion. Son of Carlos Colón."},
            {"name": "John Morrison", "real_name": "John Randall Hennigan", "debut_year": 2002, "hometown": "Los Angeles, California", "nationality": "American", "finishers": "Starship Pain", "aliases": "Johnny Mundo, Johnny Impact", "about": "Multiple time Intercontinental and Tag Team Champion known for parkour-style moves."},
            {"name": "The Miz", "real_name": "Michael Gregory Mizanin", "debut_year": 2006, "hometown": "Parma, Ohio", "nationality": "American", "finishers": "Skull Crushing Finale", "aliases": "The A-Lister, The It Factor", "about": "Two-time WWE Champion and Grand Slam Champion. Known for his reality TV background and promo skills."},
            {"name": "Dolph Ziggler", "real_name": "Nicholas Theodore Nemeth", "debut_year": 2005, "hometown": "Cleveland, Ohio", "nationality": "American", "finishers": "Zig Zag, Superkick", "aliases": "The Showoff", "about": "Two-time World Heavyweight Champion and three-time Intercontinental Champion."},
            {"name": "Kofi Kingston", "real_name": "Kofi Nahaje Sarkodie-Mensah", "debut_year": 2006, "hometown": "Accra, Ghana", "nationality": "Ghanaian-American", "finishers": "Trouble in Paradise", "about": "Former WWE Champion and member of The New Day. First African-born WWE Champion."},
            {"name": "CM Punk", "real_name": "Phillip Jack Brooks", "debut_year": 1999, "hometown": "Chicago, Illinois", "nationality": "American", "finishers": "Go to Sleep, Anaconda Vise", "aliases": "The Best in the World, The Straight Edge Superstar", "about": "Two-time WWE Champion known for his 'Pipe Bomb' promo and 434-day title reign."},
            {"name": "Daniel Bryan", "real_name": "Bryan Lloyd Danielson", "debut_year": 1999, "hometown": "Aberdeen, Washington", "nationality": "American", "finishers": "Yes Lock, Busaiku Knee", "aliases": "Bryan Danielson, The American Dragon", "about": "Five-time world champion who led the 'Yes Movement' to a WrestleMania 30 victory."},
            {"name": "AJ Lee", "real_name": "April Jeanette Mendez", "debut_year": 2007, "retirement_year": 2015, "hometown": "Union City, New Jersey", "nationality": "American", "finishers": "Black Widow", "about": "Three-time Divas Champion with the longest cumulative reign in history."},
            {"name": "Paige", "real_name": "Saraya-Jade Bevis", "debut_year": 2011, "retirement_year": 2018, "hometown": "Norwich, England", "nationality": "British", "finishers": "Ram-Paige, PTO", "aliases": "Saraya", "about": "Youngest Divas Champion in history. Pioneer of the women's wrestling revolution in WWE."},
        ]

        for data in ruthless_era:
            self.get_or_create_wrestler(**data)

        # MODERN ERA (2016-Present)
        self.stdout.write('\n  [Modern Era - 2016-Present]')
        modern_era = [
            {"name": "Roman Reigns", "real_name": "Leati Joseph Anoa'i", "debut_year": 2010, "hometown": "Pensacola, Florida", "nationality": "American", "finishers": "Spear, Guillotine Choke", "aliases": "The Tribal Chief, The Head of the Table", "about": "Held the Universal Championship for over 1,300 days, the longest reign in modern WWE history."},
            {"name": "Seth Rollins", "real_name": "Colby Daniel Lopez", "debut_year": 2005, "hometown": "Davenport, Iowa", "nationality": "American", "finishers": "Curb Stomp, Pedigree", "aliases": "The Architect, The Visionary", "about": "Four-time world champion and founding member of The Shield."},
            {"name": "Dean Ambrose", "real_name": "Jonathan David Good", "debut_year": 2004, "hometown": "Cincinnati, Ohio", "nationality": "American", "finishers": "Dirty Deeds, Paradigm Shift", "aliases": "Jon Moxley", "about": "Former WWE Champion and member of The Shield. Now competes as Jon Moxley."},
            {"name": "Braun Strowman", "real_name": "Adam Scherr", "debut_year": 2015, "hometown": "Sherrills Ford, North Carolina", "nationality": "American", "finishers": "Running Powerslam", "aliases": "The Monster Among Men", "about": "Former Universal Champion and one of the most physically dominant wrestlers in WWE history."},
            {"name": "Drew McIntyre", "real_name": "Andrew McLean Galloway IV", "debut_year": 2007, "hometown": "Ayr, Scotland", "nationality": "Scottish", "finishers": "Claymore Kick, Future Shock DDT", "aliases": "The Scottish Warrior", "about": "Two-time WWE Champion who main evented WrestleMania in an empty arena."},
            {"name": "Becky Lynch", "real_name": "Rebecca Quin", "debut_year": 2002, "hometown": "Limerick, Ireland", "nationality": "Irish", "finishers": "Dis-Arm-Her, Man Handle Slam", "aliases": "The Man, Big Time Becks", "about": "The first woman to main event WrestleMania and former Raw and SmackDown Women's Champion."},
            {"name": "Charlotte Flair", "real_name": "Ashley Elizabeth Fliehr", "debut_year": 2012, "hometown": "Charlotte, North Carolina", "nationality": "American", "finishers": "Figure Eight, Natural Selection", "aliases": "The Queen", "about": "14-time women's world champion and daughter of Ric Flair."},
            {"name": "Sasha Banks", "real_name": "Mercedes Justine Kaestner-Varnado", "debut_year": 2010, "hometown": "Fairfield, California", "nationality": "American", "finishers": "Bank Statement, Frog Splash", "aliases": "The Boss, Mercedes Moné", "about": "Five-time Raw Women's Champion and member of The Four Horsewomen."},
            {"name": "Bayley", "real_name": "Pamela Rose Martinez", "debut_year": 2008, "hometown": "San Jose, California", "nationality": "American", "finishers": "Rose Plant, Bayley-to-Belly", "about": "Grand Slam Champion and member of The Four Horsewomen."},
            {"name": "Asuka", "real_name": "Kanako Urai", "debut_year": 2004, "hometown": "Osaka, Japan", "nationality": "Japanese", "finishers": "Asuka Lock", "aliases": "Kana, The Empress of Tomorrow", "about": "Longest-reigning NXT Women's Champion with an undefeated streak of over 900 days."},
            {"name": "Bianca Belair", "real_name": "Bianca Nicole Crawford", "debut_year": 2016, "hometown": "Knoxville, Tennessee", "nationality": "American", "finishers": "KOD (Kiss of Death)", "aliases": "The EST of WWE", "about": "Three-time Raw Women's Champion and 2021 Royal Rumble winner."},
            {"name": "Rhea Ripley", "real_name": "Demi Bennett", "debut_year": 2013, "hometown": "Adelaide, Australia", "nationality": "Australian", "finishers": "Riptide, Prism Trap", "aliases": "Mami, The Nightmare", "about": "Former Women's World Champion and Royal Rumble winner. First Australian women's champion."},
            {"name": "Kevin Owens", "real_name": "Kevin Yanick Steen", "debut_year": 2000, "hometown": "Marieville, Quebec, Canada", "nationality": "Canadian", "finishers": "Stunner, Pop-Up Powerbomb", "aliases": "KO", "about": "Former Universal Champion known for his hard-hitting style and intensity."},
            {"name": "Sami Zayn", "real_name": "Rami Sebei", "debut_year": 2002, "hometown": "Laval, Quebec, Canada", "nationality": "Canadian", "finishers": "Helluva Kick, Blue Thunder Bomb", "aliases": "El Generico", "about": "Former Intercontinental Champion and Honorary Uce. Known for his underdog babyface character."},
            {"name": "Finn Balor", "real_name": "Fergal Devitt", "debut_year": 2000, "hometown": "Bray, County Wicklow, Ireland", "nationality": "Irish", "finishers": "Coup de Grace", "aliases": "Prince Devitt, The Demon", "about": "First Universal Champion in WWE history. Co-founder of Bullet Club."},
            {"name": "Bray Wyatt", "real_name": "Windham Lawrence Rotunda", "debut_year": 2009, "retirement_year": 2023, "hometown": "Brooksville, Florida", "nationality": "American", "finishers": "Sister Abigail, Mandible Claw", "aliases": "The Fiend, The Eater of Worlds", "about": "Two-time Universal Champion known for his horror-inspired characters."},
            {"name": "AJ Styles", "real_name": "Allen Neal Jones", "debut_year": 1998, "hometown": "Gainesville, Georgia", "nationality": "American", "finishers": "Phenomenal Forearm, Styles Clash, Calf Crusher", "aliases": "The Phenomenal One", "about": "Two-time WWE Champion and former IWGP Heavyweight Champion. Considered one of the best of his generation."},
            {"name": "Shinsuke Nakamura", "real_name": "Shinsuke Nakamura", "debut_year": 2002, "hometown": "Minato, Kyoto, Japan", "nationality": "Japanese", "finishers": "Kinshasa", "aliases": "The King of Strong Style", "about": "Former Intercontinental Champion and three-time IWGP Heavyweight Champion."},
            {"name": "Samoa Joe", "real_name": "Nuufolau Joel Seanoa", "debut_year": 1999, "hometown": "Orange County, California", "nationality": "American", "finishers": "Muscle Buster, Coquina Clutch", "aliases": "The Samoan Submission Machine", "about": "Former NXT Champion and United States Champion. Dominant force in TNA and ROH before WWE."},
            {"name": "Cody Rhodes", "real_name": "Cody Garrett Runnels", "debut_year": 2006, "hometown": "Marietta, Georgia", "nationality": "American", "finishers": "Cross Rhodes, Cody Cutter", "aliases": "The American Nightmare, Stardust", "about": "WWE Champion who 'finished his story' at WrestleMania 40. Son of Dusty Rhodes."},
            {"name": "LA Knight", "real_name": "Shaun Ricker", "debut_year": 2003, "hometown": "Shamokin, Pennsylvania", "nationality": "American", "finishers": "BFT (Blunt Force Trauma)", "aliases": "Eli Drake", "about": "Current United States Champion known for his catchphrase 'Yeah!'"},
            {"name": "Gunther", "real_name": "Walter Hahn", "debut_year": 2005, "hometown": "Vienna, Austria", "nationality": "Austrian", "finishers": "Powerbomb, Chop", "aliases": "WALTER, The Ring General", "about": "Longest-reigning Intercontinental Champion in WWE history. Known for his hard-hitting style."},
            {"name": "Solo Sikoa", "real_name": "Joseph Fatu", "debut_year": 2018, "hometown": "Pensacola, Florida", "nationality": "American", "finishers": "Samoan Spike, Spinning Solo", "aliases": "The Enforcer, The Street Champion", "about": "Member of The Bloodline and younger brother of The Usos."},
            {"name": "Jey Uso", "real_name": "Joshua Samuel Fatu", "debut_year": 2010, "hometown": "San Francisco, California", "nationality": "American", "finishers": "Uso Splash", "aliases": "Main Event Jey", "about": "Multiple time Tag Team Champion as part of The Usos with brother Jimmy."},
            {"name": "Jimmy Uso", "real_name": "Jonathan Solofa Fatu", "debut_year": 2010, "hometown": "San Francisco, California", "nationality": "American", "finishers": "Uso Splash", "about": "Multiple time Tag Team Champion as part of The Usos with brother Jey."},
        ]

        for data in modern_era:
            self.get_or_create_wrestler(**data)

        # MANAGERS, PROMOTERS, REFEREES, COMMENTATORS
        self.stdout.write('\n  [Managers, Promoters & Non-Wrestlers]')
        non_wrestlers = [
            # Managers
            {"name": "Bobby Heenan", "real_name": "Raymond Louis Heenan", "debut_year": 1965, "retirement_year": 2004, "hometown": "Chicago, Illinois", "nationality": "American", "aliases": "The Brain, The Weasel", "about": "Legendary manager and commentator. Managed Andre the Giant, Mr. Perfect, and many others."},
            {"name": "Jimmy Hart", "real_name": "James Ray Hart", "debut_year": 1972, "hometown": "Jackson, Mississippi", "nationality": "American", "aliases": "The Mouth of the South", "about": "Hall of Fame manager known for his megaphone. Managed Hulk Hogan, The Honky Tonk Man, and many others."},
            {"name": "Paul Bearer", "real_name": "William Alvin Moody", "debut_year": 1976, "retirement_year": 2013, "hometown": "Mobile, Alabama", "nationality": "American", "about": "Iconic manager of The Undertaker and Kane. Known for carrying an urn."},
            {"name": "Sensational Sherri", "real_name": "Sherri Russell", "debut_year": 1980, "retirement_year": 2006, "hometown": "New Orleans, Louisiana", "nationality": "American", "aliases": "Sherri Martel, Queen Sherri", "about": "Former WWF Women's Champion and manager of Shawn Michaels and Randy Savage."},
            {"name": "Miss Elizabeth", "real_name": "Elizabeth Ann Hulette", "debut_year": 1985, "retirement_year": 2000, "hometown": "Frankfort, Kentucky", "nationality": "American", "about": "Legendary valet and manager of Randy Savage. Their reunion at WrestleMania VII was iconic."},
            {"name": "Paul Heyman", "real_name": "Paul Eric Heyman", "debut_year": 1986, "hometown": "Scarsdale, New York", "nationality": "American", "aliases": "Paul E. Dangerously", "about": "Founder of ECW and advocate for Brock Lesnar and Roman Reigns. One of the greatest minds in wrestling."},
            {"name": "Jim Cornette", "real_name": "James Mark Cornette", "debut_year": 1982, "hometown": "Louisville, Kentucky", "nationality": "American", "about": "Manager of the Midnight Express and SMW promoter. Known for his tennis racket and outspoken opinions."},
            {"name": "Vickie Guerrero", "real_name": "Vickie Lynn Guerrero", "debut_year": 2006, "retirement_year": 2014, "hometown": "El Paso, Texas", "nationality": "American", "about": "WWE authority figure known for her 'Excuse me!' catchphrase. Widow of Eddie Guerrero."},
            {"name": "Zelina Vega", "real_name": "Thea Megan Trinidad", "debut_year": 2010, "hometown": "Queens, New York", "nationality": "American", "finishers": "Code Red", "about": "Former Queen's Crown tournament winner and manager/wrestler."},
            # Promoters/Executives
            {"name": "Vince McMahon", "real_name": "Vincent Kennedy McMahon", "debut_year": 1969, "hometown": "Greenwich, Connecticut", "nationality": "American", "aliases": "Mr. McMahon", "about": "Former Chairman of WWE who transformed the company into a global entertainment empire."},
            {"name": "Vince McMahon Sr.", "real_name": "Vincent James McMahon", "debut_year": 1953, "retirement_year": 1982, "hometown": "Harlem, New York", "nationality": "American", "about": "Founder of the WWWF and father of Vince McMahon. Built the northeastern wrestling empire."},
            {"name": "Shane McMahon", "real_name": "Shane Brandon McMahon", "debut_year": 1998, "hometown": "Greenwich, Connecticut", "nationality": "American", "finishers": "Coast to Coast", "about": "Former WWE executive and performer known for his death-defying stunts."},
            {"name": "Stephanie McMahon", "real_name": "Stephanie Marie McMahon Levesque", "debut_year": 1998, "hometown": "Greenwich, Connecticut", "nationality": "American", "about": "Former WWE Chief Brand Officer and on-screen authority figure. Daughter of Vince McMahon."},
            {"name": "Eric Bischoff", "real_name": "Eric Aaron Bischoff", "debut_year": 1991, "hometown": "Detroit, Michigan", "nationality": "American", "about": "Former WCW President who launched the Monday Night Wars with Nitro and created the nWo."},
            {"name": "Dixie Carter", "real_name": "Dixie Carter", "debut_year": 2002, "hometown": "Dallas, Texas", "nationality": "American", "about": "Former TNA/Impact Wrestling President who ran the company from 2002-2017."},
            {"name": "Tony Khan", "real_name": "Antony Rafiq Khan", "debut_year": 2019, "hometown": "Champaign, Illinois", "nationality": "American", "about": "Founder and CEO of All Elite Wrestling. Launched AEW in 2019."},
            {"name": "Jim Crockett Jr.", "real_name": "James Allen Crockett Jr.", "debut_year": 1973, "retirement_year": 1988, "hometown": "Charlotte, North Carolina", "nationality": "American", "about": "Owner of Jim Crockett Promotions/NWA which became WCW."},
            # Referees
            {"name": "Earl Hebner", "real_name": "Earl William Hebner", "debut_year": 1977, "hometown": "Richmond, Virginia", "nationality": "American", "about": "Legendary WWE referee involved in the Montreal Screwjob. Twin brother of Dave Hebner."},
            {"name": "Charles Robinson", "real_name": "Charles Robinson", "debut_year": 1994, "hometown": "Greensboro, North Carolina", "nationality": "American", "aliases": "Little Naitch", "about": "Long-time WWE referee and protege of Ric Flair."},
            {"name": "Mike Chioda", "real_name": "Michael Chioda", "debut_year": 1989, "hometown": "Willingboro, New Jersey", "nationality": "American", "about": "Longest-tenured referee in WWE history with over 30 years of service."},
            {"name": "Nick Patrick", "real_name": "Nicholas Patrick", "debut_year": 1983, "hometown": "Charlotte, North Carolina", "nationality": "American", "about": "WCW referee known for his role in the nWo storyline."},
            {"name": "Tommy Young", "real_name": "Thomas Young", "debut_year": 1966, "retirement_year": 1992, "hometown": "Charlotte, North Carolina", "nationality": "American", "about": "Hall of Fame referee considered one of the best of his era."},
            # Commentators
            {"name": "Jim Ross", "real_name": "James William Ross", "debut_year": 1974, "hometown": "Fort Bragg, California", "nationality": "American", "aliases": "JR, Good Ol' JR", "about": "The most famous play-by-play voice in wrestling history. Known for his 'Bah Gawd!' exclamations."},
            {"name": "Jerry Lawler", "real_name": "Jerry O'Neil Lawler", "debut_year": 1970, "hometown": "Memphis, Tennessee", "nationality": "American", "finishers": "Piledriver, Fist Drop", "aliases": "The King", "about": "Memphis wrestling legend and long-time WWE commentator. Had iconic matches against Andy Kaufman."},
            {"name": "Gorilla Monsoon", "real_name": "Robert James Marella", "debut_year": 1959, "retirement_year": 1988, "hometown": "Rochester, New York", "nationality": "American", "about": "Legendary commentator and former wrestler. Voice of WWF throughout the 1980s."},
            {"name": "Jesse Ventura", "real_name": "James George Janos", "debut_year": 1975, "retirement_year": 1991, "hometown": "Minneapolis, Minnesota", "nationality": "American", "aliases": "The Body", "about": "Former wrestler and commentator who became Governor of Minnesota."},
            {"name": "Michael Cole", "real_name": "Sean Michael Coulthard", "debut_year": 1997, "hometown": "Syracuse, New York", "nationality": "American", "about": "Lead WWE commentator since 1997. Voice of modern WWE programming."},
            {"name": "Corey Graves", "real_name": "Matthew Polinsky", "debut_year": 2011, "hometown": "Pittsburgh, Pennsylvania", "nationality": "American", "about": "Current WWE color commentator. Former NXT wrestler."},
            {"name": "Tony Schiavone", "real_name": "Tony Schiavone", "debut_year": 1985, "hometown": "Virginia Beach, Virginia", "nationality": "American", "about": "Voice of WCW in the 1990s and current AEW commentator."},
            # Trainers
            {"name": "Stu Hart", "real_name": "Stewart Edward Hart", "debut_year": 1946, "retirement_year": 1989, "hometown": "Saskatoon, Saskatchewan, Canada", "nationality": "Canadian", "about": "Founder of Stampede Wrestling and patriarch of the Hart wrestling family. Trained many legends."},
            {"name": "Dory Funk Sr.", "real_name": "Dorrance Funk", "debut_year": 1943, "retirement_year": 1973, "hometown": "Hammond, Indiana", "nationality": "American", "about": "Promoter of Amarillo wrestling and father of Terry and Dory Funk Jr."},
            {"name": "Eddie Sharkey", "real_name": "Edward Sharkey", "debut_year": 1972, "hometown": "Minneapolis, Minnesota", "nationality": "American", "about": "Legendary trainer who trained Brock Lesnar, Sean Waltman, and many others."},
            {"name": "Kofi Nahaje Sarkodie-Mensah", "real_name": "Kofi Kingston", "debut_year": 2006, "hometown": "Accra, Ghana", "nationality": "Ghanaian-American", "finishers": "Trouble in Paradise", "about": "Former WWE Champion and member of The New Day."},
        ]

        for data in non_wrestlers:
            self.get_or_create_wrestler(**data)

        # WCW/NWA STARS
        self.stdout.write('\n  [WCW/NWA Stars]')
        wcw_stars = [
            {"name": "Ric Flair", "real_name": "Richard Morgan Fliehr", "debut_year": 1972, "hometown": "Charlotte, North Carolina", "nationality": "American", "finishers": "Figure Four Leglock", "aliases": "The Nature Boy", "about": "16-time world champion and widely considered the greatest professional wrestler of all time."},
            {"name": "Arn Anderson", "real_name": "Martin Anthony Lunde", "debut_year": 1982, "hometown": "Rome, Georgia", "nationality": "American", "finishers": "Spinebuster, DDT", "aliases": "The Enforcer", "about": "Founding member of The Four Horsemen. Known for his spinebuster and toughness."},
            {"name": "Tully Blanchard", "real_name": "Tully Arthur Blanchard", "debut_year": 1975, "hometown": "San Antonio, Texas", "nationality": "American", "finishers": "Slingshot Suplex", "about": "Former NWA Television Champion and member of The Four Horsemen."},
            {"name": "Ole Anderson", "real_name": "Alan Robert Rogowski", "debut_year": 1967, "retirement_year": 1990, "hometown": "Minneapolis, Minnesota", "nationality": "American", "about": "Founding member of The Four Horsemen. Former NWA Tag Team Champion."},
            {"name": "Barry Windham", "real_name": "Barry Clinton Windham", "debut_year": 1979, "hometown": "Sweetwater, Texas", "nationality": "American", "finishers": "Superplex, Iron Claw", "about": "Former NWA World Heavyweight Champion and member of The Four Horsemen."},
            {"name": "Sting", "real_name": "Steven James Borden", "debut_year": 1985, "retirement_year": 2024, "hometown": "Omaha, Nebraska", "nationality": "American", "finishers": "Scorpion Deathlock, Scorpion Death Drop", "aliases": "The Icon, The Franchise", "about": "The face of WCW throughout its existence. Never worked for WWE during his active career until late in his career."},
            {"name": "Lex Luger", "real_name": "Lawrence Wendell Pfohl", "debut_year": 1985, "hometown": "Chicago, Illinois", "nationality": "American", "finishers": "Torture Rack, Running Forearm", "aliases": "The Total Package", "about": "Former WCW World Heavyweight Champion and main eventer in both WCW and WWF."},
            {"name": "Diamond Dallas Page", "real_name": "Page Joseph Falkinburg Jr.", "debut_year": 1991, "hometown": "Point Pleasant, New Jersey", "nationality": "American", "finishers": "Diamond Cutter", "aliases": "DDP", "about": "Three-time WCW World Heavyweight Champion who started wrestling in his late 30s."},
            {"name": "Goldberg", "real_name": "William Scott Goldberg", "debut_year": 1997, "hometown": "Tulsa, Oklahoma", "nationality": "American", "finishers": "Spear, Jackhammer", "about": "Undefeated for 173 matches in WCW. Former WCW and WWE World Champion."},
            {"name": "Scott Steiner", "real_name": "Scott Carl Rechsteiner", "debut_year": 1986, "hometown": "Bay City, Michigan", "nationality": "American", "finishers": "Steiner Recliner, Frankensteiner", "aliases": "Big Poppa Pump", "about": "Former WCW World Heavyweight Champion and tag team specialist with brother Rick."},
            {"name": "Rick Steiner", "real_name": "Robert Rechsteiner", "debut_year": 1983, "hometown": "Bay City, Michigan", "nationality": "American", "finishers": "Steiner Bulldog", "aliases": "The Dog-Faced Gremlin", "about": "Multiple time Tag Team Champion as part of The Steiner Brothers."},
            {"name": "Booker T", "real_name": "Robert Booker Tio Huffman", "debut_year": 1989, "hometown": "Houston, Texas", "nationality": "American", "finishers": "Scissors Kick, Book End, Spinaroonie", "aliases": "King Booker, Booker Huffman", "about": "Five-time WCW Champion and six-time WWE World Tag Team Champion."},
            {"name": "Stevie Ray", "real_name": "Lane Huffman", "debut_year": 1989, "retirement_year": 2000, "hometown": "Houston, Texas", "nationality": "American", "about": "Tag team partner of Booker T as Harlem Heat."},
            {"name": "Chris Benoit", "real_name": "Christopher Michael Benoit", "debut_year": 1985, "retirement_year": 2007, "hometown": "Montreal, Quebec, Canada", "nationality": "Canadian", "finishers": "Crippler Crossface, Diving Headbutt", "aliases": "The Canadian Crippler", "about": "Former World Heavyweight Champion known for technical prowess."},
            {"name": "Perry Saturn", "real_name": "Perry Arthur Satullo", "debut_year": 1990, "retirement_year": 2004, "hometown": "Cleveland, Ohio", "nationality": "American", "finishers": "Rings of Saturn", "about": "Member of The Flock and later the Radicalz."},
            {"name": "Raven", "real_name": "Scott Levy", "debut_year": 1988, "hometown": "Philadelphia, Pennsylvania", "nationality": "American", "finishers": "Evenflow DDT", "about": "Leader of The Flock in WCW and multiple time Hardcore Champion."},
            {"name": "Buff Bagwell", "real_name": "Marcus Alexander Bagwell", "debut_year": 1991, "hometown": "Marietta, Georgia", "nationality": "American", "finishers": "Buff Blockbuster", "aliases": "Buff", "about": "Five-time WCW Tag Team Champion and member of the nWo."},
            {"name": "La Parka", "real_name": "Adolfo Tapia Ibarra", "debut_year": 1987, "hometown": "Torreón, Mexico", "nationality": "Mexican", "about": "Iconic luchador known for his skeleton costume and chair shots."},
            {"name": "Juventud Guerrera", "real_name": "Jose Luis Juana Guerrera", "debut_year": 1992, "hometown": "Mexico City, Mexico", "nationality": "Mexican", "finishers": "Juvi Driver, 450 Splash", "about": "Former WCW Cruiserweight Champion known for high-flying moves."},
            {"name": "Psicosis", "real_name": "Dionicio Castellanos Torres", "debut_year": 1989, "hometown": "Tijuana, Mexico", "nationality": "Mexican", "finishers": "Guillotine Leg Drop", "about": "WCW Cruiserweight known for his feuds with Rey Mysterio."},
            {"name": "Ultimo Dragon", "real_name": "Yoshihiro Asai", "debut_year": 1987, "hometown": "Nagoya, Japan", "nationality": "Japanese", "finishers": "Asai Moonsault, Dragon Sleeper", "about": "Held 10 championships simultaneously at one point. Innovative high-flyer."},
        ]

        for data in wcw_stars:
            self.get_or_create_wrestler(**data)

        # ECW ORIGINALS
        self.stdout.write('\n  [ECW Originals]')
        ecw_stars = [
            {"name": "Tommy Dreamer", "real_name": "Thomas James Laughlin", "debut_year": 1989, "hometown": "Yonkers, New York", "nationality": "American", "finishers": "Dreamer DDT, Tommyhawk", "aliases": "The Innovator of Violence", "about": "The heart and soul of ECW. Never held the ECW World Championship despite being a cornerstone of the company."},
            {"name": "Sandman", "real_name": "James Fullington", "debut_year": 1989, "hometown": "Philadelphia, Pennsylvania", "nationality": "American", "finishers": "White Russian Leg Sweep", "about": "Five-time ECW Champion known for his beer-drinking entrance and Singapore cane."},
            {"name": "Sabu", "real_name": "Terry Michael Brunk", "debut_year": 1985, "hometown": "Bombay, Michigan", "nationality": "American", "finishers": "Arabian Facebuster, Triple Jump Moonsault", "aliases": "The Homicidal, Suicidal, Genocidal Sabu", "about": "Nephew of The Sheik and extreme wrestling pioneer. Known for table-based offense."},
            {"name": "Rob Van Dam", "real_name": "Robert Alexander Szatkowski", "debut_year": 1990, "hometown": "Battle Creek, Michigan", "nationality": "American", "finishers": "Five Star Frog Splash, Van Daminator", "aliases": "RVD, Mr. Monday Night, The Whole F'n Show", "about": "Former ECW, WWE, and TNA World Champion. Known for his martial arts style."},
            {"name": "Taz", "real_name": "Peter Senerchia", "debut_year": 1987, "hometown": "Brooklyn, New York", "nationality": "American", "finishers": "Tazmission", "aliases": "The Human Suplex Machine", "about": "Dominant ECW Champion known for his suplex variations."},
            {"name": "Shane Douglas", "real_name": "Troy Alan Martin", "debut_year": 1982, "hometown": "New Brighton, Pennsylvania", "nationality": "American", "finishers": "Franchiser", "aliases": "The Franchise", "about": "Four-time ECW Champion who threw down the NWA title to launch the Extreme Championship."},
            {"name": "Raven", "real_name": "Scott Levy", "debut_year": 1988, "hometown": "Philadelphia, Pennsylvania", "nationality": "American", "finishers": "Evenflow DDT", "about": "Iconic ECW Champion known for his grunge aesthetic and psychological character."},
            {"name": "The Dudley Boyz", "real_name": "Mark LoMonaco & Devon Hughes", "debut_year": 1995, "hometown": "Dudleyville", "nationality": "American", "finishers": "3D (Dudley Death Drop)", "about": "Eight-time ECW Tag Team Champions known for putting opponents through tables."},
            {"name": "New Jack", "real_name": "Jerome Young", "debut_year": 1992, "retirement_year": 2021, "hometown": "Greensboro, North Carolina", "nationality": "American", "about": "Controversial hardcore wrestler known for extreme violence and his entrance to Natural Born Killaz."},
            {"name": "Bam Bam Bigelow", "real_name": "Scott Charles Bigelow", "debut_year": 1985, "retirement_year": 2006, "hometown": "Asbury Park, New Jersey", "nationality": "American", "finishers": "Moonsault, Greetings from Asbury Park", "aliases": "The Beast from the East", "about": "Incredibly agile big man who had memorable runs in WWF and ECW."},
            {"name": "Jerry Lynn", "real_name": "Jerry Lynn", "debut_year": 1988, "hometown": "Minneapolis, Minnesota", "nationality": "American", "finishers": "Cradle Piledriver", "about": "Two-time ECW World Champion known for his matches with RVD."},
            {"name": "Super Crazy", "real_name": "Francisco Islas Rueda", "debut_year": 1993, "hometown": "Tulancingo, Mexico", "nationality": "Mexican", "finishers": "Moonsault", "about": "High-flying luchador who was part of the ECW cruiserweight division."},
            {"name": "Tajiri", "real_name": "Yoshihiro Tajiri", "debut_year": 1994, "hometown": "Tochigi, Japan", "nationality": "Japanese", "finishers": "Buzzsaw Kick, Tarantula", "aliases": "The Japanese Buzzsaw", "about": "Former ECW and WWE Cruiserweight Champion known for his stiff kicks."},
            {"name": "Steve Corino", "real_name": "Steve Corino", "debut_year": 1994, "hometown": "Winnipeg, Manitoba, Canada", "nationality": "Canadian", "finishers": "Old School Expulsion", "about": "Former ECW World Champion and current wrestling trainer/producer."},
            {"name": "Justin Credible", "real_name": "Peter Joseph Polaco", "debut_year": 1993, "hometown": "Ozone Park, New York", "nationality": "American", "finishers": "That's Incredible", "about": "Former ECW World Champion and member of The Impact Players."},
            {"name": "Lance Storm", "real_name": "Lance Evers", "debut_year": 1990, "hometown": "Calgary, Alberta, Canada", "nationality": "Canadian", "finishers": "Canadian Maple Leaf, Superkick", "aliases": "The Canadian Crippler", "about": "Technical wrestler who once held three WCW titles simultaneously."},
            {"name": "Masato Tanaka", "real_name": "Masato Tanaka", "debut_year": 1994, "hometown": "Hirosaki, Japan", "nationality": "Japanese", "finishers": "Diamond Dust, Roaring Elbow", "about": "Former ECW World Champion known for his brutal matches with Mike Awesome."},
            {"name": "Mike Awesome", "real_name": "Michael Lee Alfonso", "debut_year": 1989, "retirement_year": 2007, "hometown": "Tampa, Florida", "nationality": "American", "finishers": "Awesome Bomb", "about": "Two-time ECW World Champion known for his power moves and high-flying ability."},
        ]

        for data in ecw_stars:
            self.get_or_create_wrestler(**data)

    def seed_promotions(self):
        """Seed comprehensive list of wrestling promotions."""
        self.stdout.write('\n--- Seeding Wrestling Promotions ---\n')

        promotions_data = [
            # Major American
            {"name": "World Wrestling Entertainment", "abbreviation": "WWE", "founded_year": 1952, "headquarters": "Stamford, Connecticut", "website": "https://www.wwe.com", "about": "The largest professional wrestling company in the world, founded by Jess McMahon and Toots Mondt as the Capitol Wrestling Corporation."},
            {"name": "All Elite Wrestling", "abbreviation": "AEW", "founded_year": 2019, "headquarters": "Jacksonville, Florida", "website": "https://www.allelitewrestling.com", "about": "Major American promotion founded by Tony Khan, Cody Rhodes, Kenny Omega, and The Young Bucks."},
            {"name": "World Championship Wrestling", "abbreviation": "WCW", "founded_year": 1988, "closed_year": 2001, "headquarters": "Atlanta, Georgia", "about": "Major promotion owned by Ted Turner that competed with WWF during the Monday Night Wars."},
            {"name": "Extreme Championship Wrestling", "abbreviation": "ECW", "founded_year": 1992, "closed_year": 2001, "headquarters": "Philadelphia, Pennsylvania", "about": "Influential hardcore wrestling promotion that pioneered extreme wrestling style."},
            {"name": "Total Nonstop Action Wrestling", "abbreviation": "TNA", "founded_year": 2002, "headquarters": "Nashville, Tennessee", "about": "Promotion founded by Jeff Jarrett, later known as Impact Wrestling."},
            {"name": "Ring of Honor", "abbreviation": "ROH", "founded_year": 2002, "headquarters": "Baltimore, Maryland", "website": "https://www.rohwrestling.com", "about": "Promotion known for its emphasis on in-ring competition, now owned by AEW."},
            {"name": "National Wrestling Alliance", "abbreviation": "NWA", "founded_year": 1948, "headquarters": "Atlanta, Georgia", "website": "https://www.nwa.com", "about": "Historic wrestling alliance that once unified territories across North America."},
            {"name": "American Wrestling Association", "abbreviation": "AWA", "founded_year": 1960, "closed_year": 1991, "headquarters": "Minneapolis, Minnesota", "about": "Major territory founded by Verne Gagne that featured legendary wrestlers."},
            # Japanese
            {"name": "New Japan Pro-Wrestling", "abbreviation": "NJPW", "founded_year": 1972, "headquarters": "Tokyo, Japan", "website": "https://www.njpw1972.com", "about": "The largest professional wrestling promotion in Japan, known for strong style."},
            {"name": "All Japan Pro Wrestling", "abbreviation": "AJPW", "founded_year": 1972, "headquarters": "Tokyo, Japan", "about": "Historic Japanese promotion founded by Giant Baba."},
            {"name": "Pro Wrestling NOAH", "abbreviation": "NOAH", "founded_year": 2000, "headquarters": "Tokyo, Japan", "about": "Japanese promotion founded by Mitsuharu Misawa after leaving All Japan."},
            {"name": "Dragon Gate", "abbreviation": "DG", "founded_year": 2004, "headquarters": "Kobe, Japan", "about": "Japanese promotion known for its fast-paced, high-flying style."},
            {"name": "DDT Pro-Wrestling", "abbreviation": "DDT", "founded_year": 1997, "headquarters": "Tokyo, Japan", "about": "Japanese promotion known for its comedic wrestling style."},
            {"name": "World Wonder Ring Stardom", "abbreviation": "Stardom", "founded_year": 2010, "headquarters": "Tokyo, Japan", "about": "Premier women's wrestling promotion in Japan."},
            # Mexican
            {"name": "Consejo Mundial de Lucha Libre", "abbreviation": "CMLL", "founded_year": 1933, "headquarters": "Mexico City, Mexico", "about": "The oldest active professional wrestling promotion in the world."},
            {"name": "Lucha Libre AAA Worldwide", "abbreviation": "AAA", "founded_year": 1992, "headquarters": "Mexico City, Mexico", "about": "Major Mexican lucha libre promotion founded by Antonio Peña."},
            # British
            {"name": "World of Sport Wrestling", "abbreviation": "WOS", "founded_year": 1965, "closed_year": 1988, "headquarters": "London, England", "about": "British wrestling promotion that aired on ITV, featuring a unique technical style."},
            {"name": "Revolution Pro Wrestling", "abbreviation": "RevPro", "founded_year": 2012, "headquarters": "London, England", "about": "Leading British wrestling promotion with strong ties to NJPW."},
            {"name": "Progress Wrestling", "abbreviation": "PROGRESS", "founded_year": 2012, "headquarters": "London, England", "about": "British promotion known for storytelling and developing future stars."},
            # Independent American
            {"name": "Pro Wrestling Guerrilla", "abbreviation": "PWG", "founded_year": 2003, "headquarters": "Reseda, California", "about": "Influential Southern California independent promotion."},
            {"name": "Game Changer Wrestling", "abbreviation": "GCW", "founded_year": 2010, "headquarters": "Atlantic City, New Jersey", "about": "Hardcore-focused independent promotion."},
            {"name": "Chikara", "abbreviation": "CHIKARA", "founded_year": 2002, "closed_year": 2020, "headquarters": "Philadelphia, Pennsylvania", "about": "Unique promotion blending wrestling with comic book storytelling."},
            {"name": "Combat Zone Wrestling", "abbreviation": "CZW", "founded_year": 1999, "headquarters": "Blackwood, New Jersey", "about": "Extreme wrestling promotion that was a training ground for many stars."},
            {"name": "Evolve Wrestling", "abbreviation": "EVOLVE", "founded_year": 2010, "closed_year": 2020, "headquarters": "New York", "about": "Technical wrestling promotion that became a WWE developmental partner."},
            {"name": "Major League Wrestling", "abbreviation": "MLW", "founded_year": 2002, "headquarters": "New York", "about": "Promotion that has had multiple incarnations since 2002."},
            # Historic Territories
            {"name": "Mid-South Wrestling", "abbreviation": "MSW", "founded_year": 1979, "closed_year": 1987, "headquarters": "Shreveport, Louisiana", "about": "Legendary territory run by Bill Watts, later became UWF."},
            {"name": "Georgia Championship Wrestling", "abbreviation": "GCW", "founded_year": 1944, "closed_year": 1984, "headquarters": "Atlanta, Georgia", "about": "Historic NWA territory that introduced wrestling to TBS."},
            {"name": "Jim Crockett Promotions", "abbreviation": "JCP", "founded_year": 1931, "closed_year": 1988, "headquarters": "Charlotte, North Carolina", "about": "Major NWA territory that became WCW."},
            {"name": "Stampede Wrestling", "abbreviation": "Stampede", "founded_year": 1948, "closed_year": 1989, "headquarters": "Calgary, Alberta, Canada", "about": "Canadian promotion run by Stu Hart that trained many legendary wrestlers."},
            {"name": "World Class Championship Wrestling", "abbreviation": "WCCW", "founded_year": 1966, "closed_year": 1990, "headquarters": "Dallas, Texas", "about": "Texas territory run by the Von Erich family."},
            {"name": "Continental Wrestling Association", "abbreviation": "CWA", "founded_year": 1977, "closed_year": 1989, "headquarters": "Memphis, Tennessee", "about": "Memphis territory run by Jerry Jarrett and Jerry Lawler."},
            {"name": "Championship Wrestling from Florida", "abbreviation": "CWF", "founded_year": 1961, "closed_year": 1987, "headquarters": "Tampa, Florida", "about": "Major Florida territory that developed many future stars."},
        ]

        for data in promotions_data:
            promo, created = Promotion.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  + {promo.name}')

    def seed_titles(self):
        """Seed comprehensive list of wrestling championships."""
        self.stdout.write('\n--- Seeding Championships ---\n')

        # Get promotions
        wwe = Promotion.objects.filter(abbreviation='WWE').first()
        aew = Promotion.objects.filter(abbreviation='AEW').first()
        njpw = Promotion.objects.filter(abbreviation='NJPW').first()
        wcw = Promotion.objects.filter(abbreviation='WCW').first()
        tna = Promotion.objects.filter(abbreviation='TNA').first()
        roh = Promotion.objects.filter(abbreviation='ROH').first()
        nwa = Promotion.objects.filter(abbreviation='NWA').first()
        ecw = Promotion.objects.filter(abbreviation='ECW').first()

        titles_data = [
            # WWE
            {"name": "WWE Championship", "promotion": wwe, "debut_year": 1963, "about": "The top championship in WWE, first won by Buddy Rogers."},
            {"name": "WWE Universal Championship", "promotion": wwe, "debut_year": 2016, "about": "Top championship on Raw, first won by Finn Balor."},
            {"name": "WWE World Heavyweight Championship", "promotion": wwe, "debut_year": 2023, "about": "Revived in 2023 as a separate world title."},
            {"name": "WWE Intercontinental Championship", "promotion": wwe, "debut_year": 1979, "about": "The workhorse championship, first won by Pat Patterson."},
            {"name": "WWE United States Championship", "promotion": wwe, "debut_year": 2003, "about": "Inherited from WCW, representing the United States."},
            {"name": "WWE Raw Tag Team Championship", "promotion": wwe, "debut_year": 2002, "about": "Tag team championship for the Raw brand."},
            {"name": "WWE SmackDown Tag Team Championship", "promotion": wwe, "debut_year": 2016, "about": "Tag team championship for the SmackDown brand."},
            {"name": "WWE Raw Women's Championship", "promotion": wwe, "debut_year": 2016, "about": "Women's championship for the Raw brand."},
            {"name": "WWE SmackDown Women's Championship", "promotion": wwe, "debut_year": 2016, "about": "Women's championship for the SmackDown brand."},
            {"name": "WWE Women's World Championship", "promotion": wwe, "debut_year": 2023, "about": "Revived women's world championship."},
            {"name": "NXT Championship", "promotion": wwe, "debut_year": 2012, "about": "Top championship in WWE's NXT brand."},
            {"name": "NXT Women's Championship", "promotion": wwe, "debut_year": 2013, "about": "Women's championship in NXT."},
            # AEW
            {"name": "AEW World Championship", "promotion": aew, "debut_year": 2019, "about": "The top championship in AEW, first won by Chris Jericho."},
            {"name": "AEW International Championship", "promotion": aew, "debut_year": 2023, "about": "Formerly the All-Atlantic Championship, renamed in 2023."},
            {"name": "AEW TNT Championship", "promotion": aew, "debut_year": 2020, "about": "Secondary men's championship, first won by Cody Rhodes."},
            {"name": "AEW Women's World Championship", "promotion": aew, "debut_year": 2019, "about": "Top women's championship, first won by Riho."},
            {"name": "AEW TBS Championship", "promotion": aew, "debut_year": 2022, "about": "Secondary women's championship, first won by Jade Cargill."},
            {"name": "AEW World Tag Team Championship", "promotion": aew, "debut_year": 2020, "about": "Top tag team championship in AEW."},
            {"name": "AEW World Trios Championship", "promotion": aew, "debut_year": 2022, "about": "Championship for three-person teams."},
            # NJPW
            {"name": "IWGP World Heavyweight Championship", "promotion": njpw, "debut_year": 2021, "about": "Unified top championship in NJPW."},
            {"name": "IWGP Heavyweight Championship", "promotion": njpw, "debut_year": 1987, "about": "Historic top championship, unified in 2021."},
            {"name": "IWGP Intercontinental Championship", "promotion": njpw, "debut_year": 2011, "about": "Secondary singles championship, unified in 2021."},
            {"name": "IWGP United States Heavyweight Championship", "promotion": njpw, "debut_year": 2017, "about": "Championship representing the US expansion."},
            {"name": "IWGP Junior Heavyweight Championship", "promotion": njpw, "debut_year": 1986, "about": "Top cruiserweight championship in NJPW."},
            {"name": "IWGP Tag Team Championship", "promotion": njpw, "debut_year": 1985, "about": "Top tag team championship in NJPW."},
            # WCW
            {"name": "WCW World Heavyweight Championship", "promotion": wcw, "debut_year": 1991, "about": "Top championship in WCW until its closure."},
            {"name": "WCW United States Championship", "promotion": wcw, "debut_year": 1975, "about": "Secondary singles championship in WCW."},
            {"name": "WCW World Tag Team Championship", "promotion": wcw, "debut_year": 1975, "about": "Top tag team championship in WCW."},
            {"name": "WCW Cruiserweight Championship", "promotion": wcw, "debut_year": 1996, "about": "Championship that revolutionized cruiserweight wrestling."},
            {"name": "WCW World Television Championship", "promotion": wcw, "debut_year": 1974, "about": "Championship defended on television."},
            # ECW
            {"name": "ECW World Heavyweight Championship", "promotion": ecw, "debut_year": 1992, "about": "Top championship in ECW."},
            {"name": "ECW World Television Championship", "promotion": ecw, "debut_year": 1992, "about": "Secondary singles championship in ECW."},
            {"name": "ECW World Tag Team Championship", "promotion": ecw, "debut_year": 1992, "about": "Top tag team championship in ECW."},
            # TNA/Impact
            {"name": "TNA World Heavyweight Championship", "promotion": tna, "debut_year": 2007, "about": "Top championship in TNA/Impact."},
            {"name": "TNA X Division Championship", "promotion": tna, "debut_year": 2002, "about": "Unique championship not defined by weight limits."},
            {"name": "TNA World Tag Team Championship", "promotion": tna, "debut_year": 2007, "about": "Top tag team championship in TNA."},
            {"name": "TNA Knockouts Championship", "promotion": tna, "debut_year": 2007, "about": "Top women's championship in TNA."},
            # ROH
            {"name": "ROH World Championship", "promotion": roh, "debut_year": 2002, "about": "Top championship in Ring of Honor."},
            {"name": "ROH World Television Championship", "promotion": roh, "debut_year": 2012, "about": "Television championship in ROH."},
            {"name": "ROH World Tag Team Championship", "promotion": roh, "debut_year": 2002, "about": "Tag team championship in ROH."},
            {"name": "ROH Women's World Championship", "promotion": roh, "debut_year": 2018, "about": "Women's championship in ROH."},
            # NWA
            {"name": "NWA World Heavyweight Championship", "promotion": nwa, "debut_year": 1948, "about": "One of the most prestigious championships in wrestling history."},
            {"name": "NWA World Tag Team Championship", "promotion": nwa, "debut_year": 1950, "about": "Historic tag team championship."},
            {"name": "NWA World Television Championship", "promotion": nwa, "debut_year": 1974, "about": "Television championship in the NWA."},
            {"name": "NWA Women's World Championship", "promotion": nwa, "debut_year": 1937, "about": "Historic women's championship."},
        ]

        for data in titles_data:
            if data.get('promotion'):
                title, created = Title.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
                if created:
                    self.stdout.write(f'  + {title.name}')

    def seed_venues(self):
        """Seed comprehensive list of wrestling venues."""
        self.stdout.write('\n--- Seeding Venues ---\n')

        venues_data = [
            # Major Arenas - USA
            {"name": "Madison Square Garden", "location": "New York City, New York, USA", "capacity": 20789},
            {"name": "Staples Center", "location": "Los Angeles, California, USA", "capacity": 20000},
            {"name": "United Center", "location": "Chicago, Illinois, USA", "capacity": 23500},
            {"name": "TD Garden", "location": "Boston, Massachusetts, USA", "capacity": 19580},
            {"name": "Wells Fargo Center", "location": "Philadelphia, Pennsylvania, USA", "capacity": 21000},
            {"name": "American Airlines Center", "location": "Dallas, Texas, USA", "capacity": 21000},
            {"name": "State Farm Arena", "location": "Atlanta, Georgia, USA", "capacity": 21000},
            {"name": "Barclays Center", "location": "Brooklyn, New York, USA", "capacity": 19000},
            {"name": "Crypto.com Arena", "location": "Los Angeles, California, USA", "capacity": 20000},
            {"name": "Chase Center", "location": "San Francisco, California, USA", "capacity": 18064},
            {"name": "T-Mobile Arena", "location": "Las Vegas, Nevada, USA", "capacity": 20000},
            {"name": "Little Caesars Arena", "location": "Detroit, Michigan, USA", "capacity": 20332},
            {"name": "Capital One Arena", "location": "Washington, D.C., USA", "capacity": 20356},
            {"name": "Prudential Center", "location": "Newark, New Jersey, USA", "capacity": 18711},
            {"name": "Toyota Center", "location": "Houston, Texas, USA", "capacity": 18055},
            # Stadiums
            {"name": "AT&T Stadium", "location": "Arlington, Texas, USA", "capacity": 80000},
            {"name": "MetLife Stadium", "location": "East Rutherford, New Jersey, USA", "capacity": 82500},
            {"name": "SoFi Stadium", "location": "Inglewood, California, USA", "capacity": 70000},
            {"name": "Mercedes-Benz Stadium", "location": "Atlanta, Georgia, USA", "capacity": 75000},
            {"name": "Allegiant Stadium", "location": "Las Vegas, Nevada, USA", "capacity": 65000},
            {"name": "Lincoln Financial Field", "location": "Philadelphia, Pennsylvania, USA", "capacity": 69000},
            {"name": "Ford Field", "location": "Detroit, Michigan, USA", "capacity": 65000},
            {"name": "NRG Stadium", "location": "Houston, Texas, USA", "capacity": 72000},
            {"name": "Raymond James Stadium", "location": "Tampa, Florida, USA", "capacity": 75000},
            {"name": "U.S. Bank Stadium", "location": "Minneapolis, Minnesota, USA", "capacity": 73000},
            {"name": "Camping World Stadium", "location": "Orlando, Florida, USA", "capacity": 60000},
            {"name": "Mercedes-Benz Superdome", "location": "New Orleans, Louisiana, USA", "capacity": 76468},
            # International
            {"name": "Wembley Stadium", "location": "London, England, UK", "capacity": 90000},
            {"name": "OVO Hydro", "location": "Glasgow, Scotland, UK", "capacity": 14300},
            {"name": "O2 Arena", "location": "London, England, UK", "capacity": 20000},
            {"name": "Tokyo Dome", "location": "Tokyo, Japan", "capacity": 55000},
            {"name": "Nippon Budokan", "location": "Tokyo, Japan", "capacity": 14471},
            {"name": "Osaka-jo Hall", "location": "Osaka, Japan", "capacity": 16000},
            {"name": "Korakuen Hall", "location": "Tokyo, Japan", "capacity": 2005},
            {"name": "Ryogoku Kokugikan", "location": "Tokyo, Japan", "capacity": 11098},
            {"name": "Arena México", "location": "Mexico City, Mexico", "capacity": 16500},
            {"name": "Scotiabank Arena", "location": "Toronto, Ontario, Canada", "capacity": 19800},
            {"name": "Rogers Arena", "location": "Vancouver, British Columbia, Canada", "capacity": 19000},
            {"name": "Saddledome", "location": "Calgary, Alberta, Canada", "capacity": 19289},
            {"name": "Bell Centre", "location": "Montreal, Quebec, Canada", "capacity": 21302},
            # Historic Venues
            {"name": "Philadelphia Arena", "location": "Philadelphia, Pennsylvania, USA", "capacity": 7500},
            {"name": "The Omni", "location": "Atlanta, Georgia, USA", "capacity": 16500},
            {"name": "Cow Palace", "location": "Daly City, California, USA", "capacity": 11089},
            {"name": "ECW Arena", "location": "Philadelphia, Pennsylvania, USA", "capacity": 1300},
            {"name": "Hammerstein Ballroom", "location": "New York City, New York, USA", "capacity": 3500},
            {"name": "Mid-Hudson Civic Center", "location": "Poughkeepsie, New York, USA", "capacity": 3000},
        ]

        for data in venues_data:
            venue, created = Venue.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  + {venue.name}')

    def seed_stables(self):
        """Seed comprehensive list of wrestling stables/factions."""
        self.stdout.write('\n--- Seeding Stables & Factions ---\n')

        stables_data = [
            {"name": "The Four Horsemen", "formed_year": 1985, "disbanded_year": 1999, "about": "Legendary stable led by Ric Flair, considered the greatest faction in wrestling history."},
            {"name": "nWo", "formed_year": 1996, "disbanded_year": 2002, "about": "New World Order - faction that revolutionized wrestling during the Monday Night Wars."},
            {"name": "D-Generation X", "formed_year": 1997, "disbanded_year": 2010, "about": "Rebellious WWF faction led by Triple H and Shawn Michaels."},
            {"name": "The Shield", "formed_year": 2012, "disbanded_year": 2019, "about": "Dominant faction featuring Roman Reigns, Seth Rollins, and Dean Ambrose."},
            {"name": "Evolution", "formed_year": 2003, "disbanded_year": 2005, "about": "Faction featuring Ric Flair, Triple H, Randy Orton, and Batista."},
            {"name": "The Nexus", "formed_year": 2010, "disbanded_year": 2011, "about": "NXT rookies who invaded Raw, led by Wade Barrett."},
            {"name": "The Corporation", "formed_year": 1998, "disbanded_year": 1999, "about": "Vince McMahon's heel faction during the Attitude Era."},
            {"name": "The Ministry of Darkness", "formed_year": 1998, "disbanded_year": 1999, "about": "The Undertaker's dark faction during the Attitude Era."},
            {"name": "The Hart Foundation", "formed_year": 1987, "disbanded_year": 1997, "about": "Canadian faction led by Bret Hart."},
            {"name": "The Nation of Domination", "formed_year": 1996, "disbanded_year": 1998, "about": "Faction that featured The Rock in his early career."},
            {"name": "The Wyatt Family", "formed_year": 2013, "disbanded_year": 2017, "about": "Cult-like faction led by Bray Wyatt."},
            {"name": "The New Day", "formed_year": 2014, "about": "Longest-reigning tag team champions in WWE history."},
            {"name": "The Bullet Club", "formed_year": 2013, "about": "Influential NJPW faction that spawned multiple spin-offs."},
            {"name": "Los Ingobernables de Japon", "formed_year": 2015, "about": "Tetsuya Naito's faction in NJPW."},
            {"name": "The Bloodline", "formed_year": 2021, "about": "Roman Reigns' family faction featuring The Usos and Solo Sikoa."},
            {"name": "The Judgment Day", "formed_year": 2022, "about": "WWE faction featuring Rhea Ripley, Damian Priest, and others."},
            {"name": "The Elite", "formed_year": 2018, "about": "Faction of Kenny Omega and The Young Bucks that helped found AEW."},
            {"name": "Inner Circle", "formed_year": 2019, "disbanded_year": 2021, "about": "Chris Jericho's AEW faction."},
            {"name": "The Dark Order", "formed_year": 2019, "about": "AEW faction originally led by Brodie Lee."},
            {"name": "Team Extreme", "formed_year": 1999, "disbanded_year": 2002, "about": "The Hardy Boyz and Lita."},
            {"name": "Too Cool", "formed_year": 1999, "disbanded_year": 2001, "about": "Scotty 2 Hotty, Grandmaster Sexay, and Rikishi."},
            {"name": "The Brood", "formed_year": 1998, "disbanded_year": 1999, "about": "Vampire-themed faction featuring Edge, Christian, and Gangrel."},
            {"name": "The Freebirds", "formed_year": 1979, "disbanded_year": 1995, "about": "Legendary southern tag team/faction."},
            {"name": "The Midnight Express", "formed_year": 1980, "disbanded_year": 1992, "about": "Tag team managed by Jim Cornette."},
            {"name": "The Road Warriors", "formed_year": 1983, "disbanded_year": 2003, "about": "Legendary tag team of Hawk and Animal, also known as the Legion of Doom."},
            {"name": "The Dangerous Alliance", "formed_year": 1991, "disbanded_year": 1992, "about": "Paul Heyman's WCW faction featuring Steve Austin, Rick Rude, and others."},
            {"name": "The Horsewomen", "formed_year": 2015, "about": "Charlotte Flair, Sasha Banks, Bayley, and Becky Lynch."},
            {"name": "Damage CTRL", "formed_year": 2022, "about": "Bayley's heel faction in WWE."},
            {"name": "Undisputed Era", "formed_year": 2017, "disbanded_year": 2021, "about": "Adam Cole's dominant NXT faction."},
            {"name": "The Club", "formed_year": 2016, "disbanded_year": 2020, "about": "AJ Styles, Karl Anderson, and Luke Gallows."},
            {"name": "Retribution", "formed_year": 2020, "disbanded_year": 2021, "about": "Masked WWE faction that invaded Raw."},
            {"name": "The Heenan Family", "formed_year": 1980, "disbanded_year": 1991, "about": "Bobby Heenan's stable of wrestlers."},
            {"name": "The Dungeon of Doom", "formed_year": 1995, "disbanded_year": 1996, "about": "WCW faction feuding with Hulk Hogan."},
            {"name": "The Wolfpac", "formed_year": 1998, "disbanded_year": 1999, "about": "The red and black nWo split led by Kevin Nash."},
            {"name": "Latino World Order", "formed_year": 1998, "disbanded_year": 1998, "about": "Eddie Guerrero's WCW faction."},
        ]

        for data in stables_data:
            stable, created = Stable.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  + {stable.name}')

    def seed_media(self):
        """Seed video games, podcasts, books, and documentaries."""
        self.stdout.write('\n--- Seeding Media (Games, Podcasts, Books, Documentaries) ---\n')

        # Video Games
        games_data = [
            {"name": "WWE 2K24", "release_year": 2024, "systems": "PS5, Xbox Series X/S, PS4, Xbox One, PC", "developer": "Visual Concepts", "publisher": "2K Sports"},
            {"name": "WWE 2K23", "release_year": 2023, "systems": "PS5, Xbox Series X/S, PS4, Xbox One, PC", "developer": "Visual Concepts", "publisher": "2K Sports"},
            {"name": "WWE 2K22", "release_year": 2022, "systems": "PS5, Xbox Series X/S, PS4, Xbox One, PC", "developer": "Visual Concepts", "publisher": "2K Sports"},
            {"name": "AEW: Fight Forever", "release_year": 2023, "systems": "PS5, Xbox Series X/S, PS4, Xbox One, PC, Switch", "developer": "Yuke's", "publisher": "THQ Nordic"},
            {"name": "Fire Pro Wrestling World", "release_year": 2017, "systems": "PS4, PC", "developer": "Spike Chunsoft", "publisher": "Spike Chunsoft"},
            {"name": "WWF No Mercy", "release_year": 2000, "systems": "Nintendo 64", "developer": "AKI Corporation", "publisher": "THQ"},
            {"name": "WWF WrestleMania 2000", "release_year": 1999, "systems": "Nintendo 64", "developer": "AKI Corporation", "publisher": "THQ"},
            {"name": "WWE SmackDown! Here Comes the Pain", "release_year": 2003, "systems": "PlayStation 2", "developer": "Yuke's", "publisher": "THQ"},
            {"name": "WWE Day of Reckoning", "release_year": 2004, "systems": "GameCube", "developer": "Yuke's", "publisher": "THQ"},
            {"name": "WWE All Stars", "release_year": 2011, "systems": "PS3, Xbox 360, Wii, PS2, PSP, 3DS", "developer": "THQ San Diego", "publisher": "THQ"},
            {"name": "WCW/nWo Revenge", "release_year": 1998, "systems": "Nintendo 64", "developer": "AKI Corporation", "publisher": "THQ"},
            {"name": "Virtual Pro Wrestling 2", "release_year": 2000, "systems": "Nintendo 64", "developer": "AKI Corporation", "publisher": "Asmik Ace"},
        ]

        for data in games_data:
            game, created = VideoGame.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                self.stdout.write(f'  + Game: {game.name}')

        # Podcasts
        podcasts_data = [
            {"name": "Something to Wrestle with Bruce Prichard", "hosts": "Bruce Prichard, Conrad Thompson", "launch_year": 2016},
            {"name": "Talk Is Jericho", "hosts": "Chris Jericho", "launch_year": 2013},
            {"name": "Grilling JR", "hosts": "Jim Ross, Conrad Thompson", "launch_year": 2018},
            {"name": "83 Weeks with Eric Bischoff", "hosts": "Eric Bischoff, Conrad Thompson", "launch_year": 2018},
            {"name": "The Kurt Angle Show", "hosts": "Kurt Angle, Conrad Thompson", "launch_year": 2020},
            {"name": "What Happened When", "hosts": "Tony Schiavone, Conrad Thompson", "launch_year": 2017},
            {"name": "Busted Open Radio", "hosts": "Dave LaGreca, Bully Ray", "launch_year": 2006},
            {"name": "The New Day: Feel the Power", "hosts": "Xavier Woods, Kofi Kingston, Big E", "launch_year": 2019},
            {"name": "Wrestling Observer Radio", "hosts": "Dave Meltzer, Bryan Alvarez", "launch_year": 1983},
            {"name": "E&C's Pod of Awesomeness", "hosts": "Edge, Christian", "launch_year": 2017},
            {"name": "The Steve Austin Show", "hosts": "Steve Austin", "launch_year": 2013},
            {"name": "Foley Is Pod", "hosts": "Mick Foley", "launch_year": 2017},
            {"name": "Arn", "hosts": "Arn Anderson, Conrad Thompson", "launch_year": 2019},
            {"name": "The Sessions with Renee Paquette", "hosts": "Renee Paquette", "launch_year": 2021},
            {"name": "AEW Unrestricted", "hosts": "Tony Schiavone, Aubrey Edwards", "launch_year": 2020},
        ]

        for data in podcasts_data:
            podcast, created = Podcast.objects.get_or_create(name=data['name'], defaults=data)
            if created:
                self.stdout.write(f'  + Podcast: {podcast.name}')

        # Books
        books_data = [
            {"title": "Have A Nice Day: A Tale of Blood and Sweatsocks", "author": "Mick Foley", "publication_year": 1999, "publisher": "ReganBooks"},
            {"title": "The Rock Says...", "author": "Dwayne Johnson", "publication_year": 2000, "publisher": "ReganBooks"},
            {"title": "Hitman: My Real Life in the Cartoon World of Wrestling", "author": "Bret Hart", "publication_year": 2007, "publisher": "Grand Central Publishing"},
            {"title": "Death of WCW", "author": "Bryan Alvarez, R.D. Reynolds", "publication_year": 2004, "publisher": "ECW Press"},
            {"title": "Yes!: My Improbable Journey to the Main Event of WrestleMania", "author": "Daniel Bryan", "publication_year": 2015, "publisher": "St. Martin's Press"},
            {"title": "The Squared Circle: Life, Death, and Professional Wrestling", "author": "David Shoemaker", "publication_year": 2013, "publisher": "Gotham Books"},
            {"title": "Sex, Lies, and Headlocks", "author": "Shaun Assael, Mike Mooneyham", "publication_year": 2002, "publisher": "Crown Publishers"},
            {"title": "Controversy Creates Cash", "author": "Eric Bischoff", "publication_year": 2006, "publisher": "Pocket Books"},
            {"title": "A Lion's Tale: Around the World in Spandex", "author": "Chris Jericho", "publication_year": 2007, "publisher": "Grand Central Publishing"},
            {"title": "Undisputed: How to Become the World Champion in 1,372 Easy Steps", "author": "Chris Jericho", "publication_year": 2011, "publisher": "Grand Central Publishing"},
            {"title": "Best in the World: At What I Have No Idea", "author": "Chris Jericho", "publication_year": 2014, "publisher": "Gotham Books"},
            {"title": "The Hardcore Truth: The Bob Holly Story", "author": "Bob Holly, Ross Williams", "publication_year": 2013, "publisher": "ECW Press"},
            {"title": "Pain and Passion: The History of Stampede Wrestling", "author": "Heath McCoy", "publication_year": 2005, "publisher": "CanWest Books"},
            {"title": "Bobby the Brain: Wrestling's Bad Boy Tells All", "author": "Bobby Heenan", "publication_year": 2002, "publisher": "Triumph Books"},
            {"title": "It's Good to Be the King...Sometimes", "author": "Jerry Lawler", "publication_year": 2002, "publisher": "Pocket Books"},
            {"title": "Slobberknocker: My Life in Wrestling", "author": "Jim Ross", "publication_year": 2017, "publisher": "Sports Publishing"},
            {"title": "Accepted: How the First Gay Superstar Changed WWE", "author": "Pat Patterson", "publication_year": 2016, "publisher": "ECW Press"},
        ]

        for data in books_data:
            book, created = Book.objects.get_or_create(title=data['title'], defaults=data)
            if created:
                self.stdout.write(f'  + Book: {book.title}')

        # Documentaries/Specials
        specials_data = [
            {"title": "Andre the Giant", "release_year": 2018, "type": "documentary", "about": "HBO documentary about the life of Andre the Giant."},
            {"title": "The Resurrection of Jake The Snake", "release_year": 2015, "type": "documentary", "about": "Documentary about Jake Roberts' recovery from addiction."},
            {"title": "Beyond the Mat", "release_year": 1999, "type": "documentary", "about": "Documentary exploring the lives of professional wrestlers."},
            {"title": "WWE: The Monday Night War", "release_year": 2014, "type": "series", "about": "Documentary series about WWF vs WCW."},
            {"title": "Dark Side of the Ring", "release_year": 2019, "type": "series", "about": "Documentary series about controversial wrestling stories."},
            {"title": "Young Rock", "release_year": 2021, "type": "series", "about": "NBC series about The Rock's early life."},
            {"title": "Heels", "release_year": 2021, "type": "series", "about": "Starz drama about a small-town wrestling promotion."},
            {"title": "GLOW", "release_year": 2017, "type": "series", "about": "Netflix series about the Gorgeous Ladies of Wrestling."},
            {"title": "Wrestling with Shadows", "release_year": 1998, "type": "documentary", "about": "Documentary following Bret Hart during the Montreal Screwjob."},
            {"title": "The Triumph and Tragedy of World Class Championship Wrestling", "release_year": 2007, "type": "documentary", "about": "Documentary about the Von Erich family and WCCW."},
            {"title": "Hitman Hart: Wrestling with Shadows", "release_year": 1998, "type": "documentary", "about": "Documentary following Bret Hart during his final WWF year."},
            {"title": "Card Subject to Change", "release_year": 2010, "type": "documentary", "about": "Documentary about independent wrestling."},
            {"title": "The Rise and Fall of ECW", "release_year": 2004, "type": "documentary", "about": "WWE documentary about Extreme Championship Wrestling."},
            {"title": "The Self Destruction of the Ultimate Warrior", "release_year": 2005, "type": "documentary", "about": "WWE documentary about the Ultimate Warrior."},
            {"title": "WWE 365", "release_year": 2018, "type": "series", "about": "Documentary series following WWE Superstars."},
            {"title": "WWE Chronicle", "release_year": 2017, "type": "series", "about": "Documentary series offering intimate looks at Superstars."},
            {"title": "Legends' House", "release_year": 2014, "type": "series", "about": "Reality series featuring WWE Legends living together."},
            {"title": "Total Divas", "release_year": 2013, "type": "series", "about": "Reality series following WWE female wrestlers."},
            {"title": "Mick Foley's Greatest Hits & Misses", "release_year": 2004, "type": "documentary", "about": "Collection of Mick Foley's most memorable moments."},
            {"title": "The Spectacular Legacy of the AWA", "release_year": 2006, "type": "documentary", "about": "Documentary about the American Wrestling Association."},
        ]

        for data in specials_data:
            special, created = Special.objects.get_or_create(title=data['title'], defaults=data)
            if created:
                self.stdout.write(f'  + Special: {special.title}')
