"""
Wrestler Profile Enrichment Command.

Adds comprehensive bios, images, and metadata to all wrestler profiles.
Uses factual information from public sources.

Usage:
    python manage.py enrich_wrestlers
    python manage.py enrich_wrestlers --batch=1  # Run specific batch
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from owdb_django.owdbapp.models import Wrestler, Promotion, Stable, Title, Event, Match


class Command(BaseCommand):
    help = 'Enrich all wrestler profiles with bios, images, and metadata'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch',
            type=int,
            help='Run specific batch (1-10)',
            default=0
        )

    def handle(self, *args, **options):
        batch = options.get('batch', 0)

        self.stdout.write(self.style.SUCCESS('\n=== WRESTLER ENRICHMENT ===\n'))

        total_updated = 0

        if batch == 0 or batch == 1:
            total_updated += self.enrich_wwe_legends()
        if batch == 0 or batch == 2:
            total_updated += self.enrich_attitude_era()
        if batch == 0 or batch == 3:
            total_updated += self.enrich_ruthless_aggression()
        if batch == 0 or batch == 4:
            total_updated += self.enrich_modern_wwe()
        if batch == 0 or batch == 5:
            total_updated += self.enrich_aew_roster()
        if batch == 0 or batch == 6:
            total_updated += self.enrich_wcw_ecw()
        if batch == 0 or batch == 7:
            total_updated += self.enrich_tna_impact()
        if batch == 0 or batch == 8:
            total_updated += self.enrich_japanese_wrestlers()
        if batch == 0 or batch == 9:
            total_updated += self.enrich_mexican_wrestlers()
        if batch == 0 or batch == 10:
            total_updated += self.enrich_british_indie()

        self.stdout.write(self.style.SUCCESS(f'\n=== ENRICHMENT COMPLETE ==='))
        self.stdout.write(f'Total wrestlers updated: {total_updated}')
        self.stdout.write(f'Total wrestlers in DB: {Wrestler.objects.count()}')

    def update_wrestler(self, name, **kwargs):
        """Update a wrestler with enriched data."""
        wrestler = Wrestler.objects.filter(name__iexact=name).first()
        if not wrestler:
            wrestler = Wrestler.objects.filter(slug=slugify(name)).first()
        if not wrestler:
            # Try partial match
            wrestler = Wrestler.objects.filter(name__icontains=name.split()[0]).first()

        if wrestler:
            updated = False
            for field, value in kwargs.items():
                if value and (not getattr(wrestler, field, None) or field == 'about'):
                    setattr(wrestler, field, value)
                    updated = True

            if updated:
                wrestler.last_enriched = timezone.now()
                wrestler.save()
                return 1
        return 0

    def enrich_wwe_legends(self):
        """Enrich WWE/WWF legends and Hall of Famers."""
        self.stdout.write('--- Enriching WWE Legends ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Hulk Hogan',
                'real_name': 'Terry Gene Bollea',
                'birth_date': '1953-08-11',
                'hometown': 'Augusta, Georgia',
                'nationality': 'American',
                'height': "6'7\"",
                'weight': '302 lbs',
                'debut_year': 1977,
                'finishers': 'Atomic Leg Drop, Axe Bomber',
                'signature_moves': 'Big Boot, Hulking Up, Body Slam',
                'trained_by': 'Hiro Matsuda',
                'about': 'Hulk Hogan is one of the most recognizable professional wrestlers of all time. He was the face of the WWF during the 1980s wrestling boom, main-eventing the first nine WrestleManias. Hogan later became the leader of the nWo in WCW, revolutionizing the industry with his heel turn. A 12-time world champion, Hogan is credited with bringing professional wrestling into mainstream pop culture.',
            },
            {
                'name': 'Andre the Giant',
                'real_name': 'André René Roussimoff',
                'birth_date': '1946-05-19',
                'hometown': 'Grenoble, France',
                'nationality': 'French',
                'height': "7'4\"",
                'weight': '520 lbs',
                'debut_year': 1966,
                'retirement_year': 1992,
                'finishers': 'Double Underhook Suplex, Sit-Down Splash',
                'signature_moves': 'Big Boot, Headbutt, Bear Hug',
                'about': 'Andre the Giant was a legendary French professional wrestler and actor, known for his great size caused by gigantism. He was the first inductee into the WWF Hall of Fame in 1993. Andre was undefeated for 15 years and his match against Hulk Hogan at WrestleMania III drew 93,173 fans to the Pontiac Silverdome. He also starred in the beloved film The Princess Bride.',
            },
            {
                'name': 'Randy Savage',
                'real_name': 'Randall Mario Poffo',
                'birth_date': '1952-11-15',
                'hometown': 'Columbus, Ohio',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '237 lbs',
                'debut_year': 1973,
                'retirement_year': 2004,
                'finishers': 'Flying Elbow Drop',
                'signature_moves': 'Double Axe Handle, Running Knee Drop, Scoop Slam',
                'trained_by': 'Angelo Poffo',
                'about': 'Macho Man Randy Savage was one of professional wrestling\'s most charismatic and talented performers. Known for his distinctive raspy voice and colorful ring attire, Savage held world championships in both WWF and WCW. His rivalry with Hulk Hogan and relationship with Miss Elizabeth created some of wrestling\'s most memorable storylines. His WrestleMania III match against Ricky Steamboat is considered one of the greatest matches ever.',
            },
            {
                'name': 'Ultimate Warrior',
                'real_name': 'James Brian Hellwig',
                'birth_date': '1959-06-16',
                'hometown': 'Crawfordsville, Indiana',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '280 lbs',
                'debut_year': 1985,
                'retirement_year': 1998,
                'finishers': 'Warrior Splash, Gorilla Press Slam',
                'signature_moves': 'Running Clothesline, Shoulder Block',
                'about': 'The Ultimate Warrior was one of the most intense and colorful characters in wrestling history. Known for his face paint, arm tassels, and explosive energy, he defeated Hulk Hogan at WrestleMania VI to become WWF Champion. His high-energy entrance and matches made him a fan favorite during the late 1980s and early 1990s.',
            },
            {
                'name': 'Roddy Piper',
                'real_name': 'Roderick George Toombs',
                'birth_date': '1954-04-17',
                'hometown': 'Glasgow, Scotland',
                'nationality': 'Canadian',
                'height': "6'2\"",
                'weight': '230 lbs',
                'debut_year': 1973,
                'retirement_year': 2011,
                'finishers': 'Sleeper Hold',
                'signature_moves': 'Eye Poke, Low Blow, Piper\'s Pit Punch',
                'about': 'Rowdy Roddy Piper was one of wrestling\'s greatest talkers and most hated villains. Born in Canada but billed from Scotland, Piper\'s feud with Hulk Hogan helped launch WrestleMania. His interview segment Piper\'s Pit was groundbreaking. While never winning a WWF World Championship, Piper was one of the most over performers of his era.',
            },
            {
                'name': 'Ted DiBiase',
                'real_name': 'Theodore Marvin DiBiase Sr.',
                'birth_date': '1954-01-18',
                'hometown': 'Miami, Florida',
                'nationality': 'American',
                'height': "6'3\"",
                'weight': '260 lbs',
                'debut_year': 1975,
                'retirement_year': 1993,
                'finishers': 'Million Dollar Dream',
                'signature_moves': 'Fist Drop, Suplex, Powerslam',
                'trained_by': 'Dory Funk Jr., Terry Funk',
                'about': 'The Million Dollar Man Ted DiBiase was one of wrestling\'s greatest heels. His wealthy persona, complete with manservant Virgil and the Million Dollar Championship, made him one of the most hated men in wrestling. A second-generation wrestler and skilled technician, DiBiase could have been world champion but his character was too valuable as a villain.',
            },
            {
                'name': 'Jake Roberts',
                'real_name': 'Aurelian Smith Jr.',
                'birth_date': '1955-05-30',
                'hometown': 'Stone Mountain, Georgia',
                'nationality': 'American',
                'height': "6'6\"",
                'weight': '249 lbs',
                'debut_year': 1975,
                'finishers': 'DDT',
                'signature_moves': 'Short-Arm Clothesline, Knee Lift',
                'about': 'Jake The Snake Roberts revolutionized wrestling promos with his psychological, soft-spoken style. The inventor of the DDT, Roberts brought his python Damien to the ring and created some of wrestling\'s most intense storylines. His feuds with Randy Savage, Rick Rude, and The Undertaker are legendary. Roberts is considered one of the best talkers in wrestling history.',
            },
            {
                'name': 'Bret Hart',
                'real_name': 'Bret Sergeant Hart',
                'birth_date': '1957-07-02',
                'hometown': 'Calgary, Alberta, Canada',
                'nationality': 'Canadian',
                'height': "6'0\"",
                'weight': '234 lbs',
                'debut_year': 1976,
                'retirement_year': 2000,
                'finishers': 'Sharpshooter',
                'signature_moves': 'Russian Leg Sweep, Backbreaker, Elbow Drop from Second Rope',
                'trained_by': 'Stu Hart',
                'about': 'The Hitman Bret Hart is considered one of the greatest technical wrestlers of all time. A 5-time WWF Champion and 2-time WCW World Champion, Hart was known for his pink and black attire and excellence of execution. He came from wrestling\'s legendary Hart family and headlined multiple WrestleManias. The Montreal Screwjob in 1997 remains one of wrestling\'s most controversial moments.',
            },
            {
                'name': 'Shawn Michaels',
                'real_name': 'Michael Shawn Hickenbottom',
                'birth_date': '1965-07-22',
                'hometown': 'San Antonio, Texas',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '225 lbs',
                'debut_year': 1984,
                'retirement_year': 2010,
                'finishers': 'Sweet Chin Music, Superkick',
                'signature_moves': 'Flying Forearm, Kip-Up, Diving Elbow Drop',
                'trained_by': 'Jose Lothario',
                'about': 'The Heartbreak Kid Shawn Michaels is widely regarded as one of the greatest in-ring performers of all time. A 4-time WWF/WWE Champion, Michaels was part of The Rockers and later founded D-Generation X. His matches at WrestleMania are legendary, including bouts against The Undertaker, Bret Hart, and Razor Ramon. After retiring due to injury in 1998, he returned in 2002 for another successful 8-year run.',
            },
            {
                'name': 'The Undertaker',
                'real_name': 'Mark William Calaway',
                'birth_date': '1965-03-24',
                'hometown': 'Houston, Texas',
                'nationality': 'American',
                'height': "6'10\"",
                'weight': '309 lbs',
                'debut_year': 1984,
                'retirement_year': 2020,
                'finishers': 'Tombstone Piledriver, Hell\'s Gate, Last Ride, Chokeslam',
                'signature_moves': 'Old School, Snake Eyes, Big Boot',
                'about': 'The Undertaker is one of the most iconic characters in wrestling history. Debuting at Survivor Series 1990, The Phenom maintained his supernatural Dead Man persona for three decades. His WrestleMania streak of 21 consecutive victories became legendary. A 7-time World Champion, Undertaker is known for his Hell in a Cell and Casket matches, and his rivalry with Kane.',
            },
            {
                'name': 'Ric Flair',
                'real_name': 'Richard Morgan Fliehr',
                'birth_date': '1949-02-25',
                'hometown': 'Charlotte, North Carolina',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '243 lbs',
                'debut_year': 1972,
                'retirement_year': 2022,
                'finishers': 'Figure-Four Leglock',
                'signature_moves': 'Knife-Edge Chop, Knee Drop, Suplex',
                'trained_by': 'Verne Gagne',
                'about': 'The Nature Boy Ric Flair is a 16-time World Champion and arguably the greatest professional wrestler of all time. Known for his flamboyant style, robes, and catchphrases like Wooo! and To be the man, you gotta beat the man, Flair led the Four Horsemen and had legendary feuds with Dusty Rhodes, Ricky Steamboat, and Sting. His 60-minute Broadway matches are wrestling classics.',
            },
            {
                'name': 'Mr. Perfect',
                'real_name': 'Curtis Michael Hennig',
                'birth_date': '1958-03-28',
                'hometown': 'Robbinsdale, Minnesota',
                'nationality': 'American',
                'height': "6'3\"",
                'weight': '257 lbs',
                'debut_year': 1980,
                'retirement_year': 2002,
                'finishers': 'Perfect Plex',
                'signature_moves': 'Rolling Neck Snap, Standing Dropkick',
                'trained_by': 'Verne Gagne, Larry Hennig',
                'about': 'Mr. Perfect Curt Hennig was one of wrestling\'s most talented in-ring performers. Known for his arrogant Perfect gimmick and vignettes showing his athletic prowess, Hennig held the AWA World Championship and WWF Intercontinental Championship. A second-generation wrestler, his technical ability and selling made him a favorite of fans and fellow wrestlers alike.',
            },
            {
                'name': 'Dusty Rhodes',
                'real_name': 'Virgil Riley Runnels Jr.',
                'birth_date': '1945-10-11',
                'hometown': 'Austin, Texas',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '302 lbs',
                'debut_year': 1968,
                'retirement_year': 2007,
                'finishers': 'Bionic Elbow',
                'signature_moves': 'Flip, Flop and Fly, Bulldog',
                'about': 'The American Dream Dusty Rhodes was one of the most charismatic performers in wrestling history. A 3-time NWA World Champion, Rhodes connected with blue-collar fans through his everyman persona and legendary promos about hard times. His feuds with Ric Flair, the Four Horsemen, and various NWA villains defined 1980s wrestling. Later became a legendary booker and trainer.',
            },
            {
                'name': 'Ricky Steamboat',
                'real_name': 'Richard Henry Blood',
                'birth_date': '1953-02-28',
                'hometown': 'Honolulu, Hawaii',
                'nationality': 'American',
                'height': "5'10\"",
                'weight': '235 lbs',
                'debut_year': 1976,
                'retirement_year': 1994,
                'finishers': 'Diving Crossbody',
                'signature_moves': 'Arm Drag, Knife-Edge Chop, Suplex',
                'about': 'Ricky The Dragon Steamboat is considered one of the greatest technical wrestlers and babyfaces of all time. His match against Randy Savage at WrestleMania III is regarded as one of the best matches ever. Steamboat held the NWA World Championship and had a legendary series of matches with Ric Flair. Known for his fire-breathing entrance and martial arts-inspired style.',
            },
            {
                'name': 'Bruno Sammartino',
                'real_name': 'Bruno Leopoldo Francesco Sammartino',
                'birth_date': '1935-10-06',
                'hometown': 'Pizzoferrato, Italy',
                'nationality': 'Italian-American',
                'height': "5'10\"",
                'weight': '275 lbs',
                'debut_year': 1959,
                'retirement_year': 1987,
                'finishers': 'Bearhug',
                'signature_moves': 'Gorilla Press, Backbreaker',
                'about': 'Bruno Sammartino is one of the greatest professional wrestlers of all time. He held the WWWF Championship for nearly 8 years in his first reign and over 4 years in his second, totaling almost 12 years as champion. The Living Legend sold out Madison Square Garden over 180 times. Sammartino was finally inducted into the WWE Hall of Fame in 2013.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} WWE legends')
        return updated

    def enrich_attitude_era(self):
        """Enrich Attitude Era stars."""
        self.stdout.write('--- Enriching Attitude Era Stars ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Stone Cold Steve Austin',
                'real_name': 'Steven James Anderson',
                'birth_date': '1964-12-18',
                'hometown': 'Victoria, Texas',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '252 lbs',
                'debut_year': 1989,
                'retirement_year': 2003,
                'finishers': 'Stone Cold Stunner, Million Dollar Dream',
                'signature_moves': 'Lou Thesz Press, Mudhole Stomps, Middle Finger Salute',
                'trained_by': 'Chris Adams',
                'about': 'Stone Cold Steve Austin is the biggest star of the Attitude Era and one of wrestling\'s all-time greats. His anti-authority persona and rivalry with Vince McMahon drove WWE to victory in the Monday Night Wars. A 6-time WWF Champion, Austin\'s Austin 3:16 promo after winning King of the Ring 1996 launched his meteoric rise. His matches at WrestleMania against The Rock are iconic.',
            },
            {
                'name': 'The Rock',
                'real_name': 'Dwayne Douglas Johnson',
                'birth_date': '1972-05-02',
                'hometown': 'Hayward, California',
                'nationality': 'American',
                'height': "6'5\"",
                'weight': '260 lbs',
                'debut_year': 1996,
                'finishers': 'Rock Bottom, People\'s Elbow',
                'signature_moves': 'Spinebuster, Sharpshooter, DDT, Samoan Drop',
                'trained_by': 'Pat Patterson, Rocky Johnson',
                'about': 'The Rock is one of the most electrifying entertainers in history. A third-generation wrestler, he debuted as Rocky Maivia before finding his voice as The People\'s Champion. A 10-time World Champion, The Rock\'s promos and catchphrases defined the Attitude Era. He transitioned to become one of Hollywood\'s biggest movie stars while occasionally returning to WWE.',
            },
            {
                'name': 'Triple H',
                'real_name': 'Paul Michael Levesque',
                'birth_date': '1969-07-27',
                'hometown': 'Nashua, New Hampshire',
                'nationality': 'American',
                'height': "6'4\"",
                'weight': '255 lbs',
                'debut_year': 1992,
                'retirement_year': 2022,
                'finishers': 'Pedigree',
                'signature_moves': 'Spinebuster, Knee Facebuster, Figure-Four Leglock',
                'trained_by': 'Killer Kowalski',
                'about': 'Triple H, The Game, The Cerebral Assassin, is a 14-time World Champion and one of the most influential figures in wrestling. Co-founder of D-Generation X, he became WWE\'s top heel in the 2000s. His matches against The Rock, Stone Cold, and Mick Foley are legendary. Now serves as WWE\'s Chief Content Officer and has revolutionized NXT.',
            },
            {
                'name': 'Mankind',
                'real_name': 'Michael Francis Foley',
                'birth_date': '1965-06-07',
                'hometown': 'Long Island, New York',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '287 lbs',
                'debut_year': 1986,
                'retirement_year': 2000,
                'finishers': 'Mandible Claw, Double Arm DDT',
                'signature_moves': 'Cactus Clothesline, Elbow Drop off Apron, Tree of Woe Elbow',
                'aliases': 'Cactus Jack, Dude Love, Mrs. Foley\'s Baby Boy',
                'about': 'Mick Foley, also known as Mankind, Cactus Jack, and Dude Love, is the Hardcore Legend. His brutal Hell in a Cell match against Undertaker at King of the Ring 1998 is legendary. A 3-time WWF Champion and bestselling author, Foley sacrificed his body for the business. His I Quit match against The Rock and rivalry with Triple H are Attitude Era classics.',
            },
            {
                'name': 'Kane',
                'real_name': 'Glenn Thomas Jacobs',
                'birth_date': '1967-04-26',
                'hometown': 'Torrejón de Ardoz, Spain',
                'nationality': 'American',
                'height': "7'0\"",
                'weight': '323 lbs',
                'debut_year': 1992,
                'retirement_year': 2021,
                'finishers': 'Chokeslam, Tombstone Piledriver',
                'signature_moves': 'Big Boot, Flying Clothesline, Sidewalk Slam',
                'about': 'Kane, The Big Red Machine, debuted as The Undertaker\'s storyline brother in 1997. His supernatural persona and in-ring ability made him a cornerstone of WWE for over two decades. A multiple-time World Champion, Kane formed legendary tag teams with Undertaker (Brothers of Destruction), X-Pac, Daniel Bryan (Team Hell No), and others. Now serves as Mayor of Knox County, Tennessee.',
            },
            {
                'name': 'Chris Jericho',
                'real_name': 'Christopher Keith Irvine',
                'birth_date': '1970-11-09',
                'hometown': 'Manhasset, New York',
                'nationality': 'Canadian-American',
                'height': "6'0\"",
                'weight': '227 lbs',
                'debut_year': 1990,
                'finishers': 'Walls of Jericho, Codebreaker, Judas Effect, Liontamer',
                'signature_moves': 'Lionsault, Enzuigiri, Bulldog',
                'trained_by': 'Hart Brothers',
                'about': 'Y2J Chris Jericho is a 7-time World Champion and one of wrestling\'s most reinventive performers. After excelling in ECW, WCW, and Japan, he debuted in WWE in 1999 and became the first Undisputed Champion. Known for his promos and constant character evolution, Jericho helped launch AEW and continues to perform at the highest level. Also fronts the rock band Fozzy.',
            },
            {
                'name': 'Kurt Angle',
                'real_name': 'Kurt Steven Angle',
                'birth_date': '1968-12-09',
                'hometown': 'Pittsburgh, Pennsylvania',
                'nationality': 'American',
                'height': "6'0\"",
                'weight': '220 lbs',
                'debut_year': 1998,
                'retirement_year': 2019,
                'finishers': 'Ankle Lock, Angle Slam',
                'signature_moves': 'German Suplex, Moonsault, Belly-to-Belly Suplex',
                'about': 'Kurt Angle won an Olympic gold medal in freestyle wrestling with a broken freakin\' neck at the 1996 Olympics. Debuting in WWE in 1999, he became one of the greatest technical wrestlers ever. A 6-time World Champion, Angle\'s matches against Brock Lesnar, Chris Benoit, and Shawn Michaels are legendary. His three I\'s - Intensity, Integrity, and Intelligence - became iconic.',
            },
            {
                'name': 'Edge',
                'real_name': 'Adam Joseph Copeland',
                'birth_date': '1973-10-30',
                'hometown': 'Orangeville, Ontario, Canada',
                'nationality': 'Canadian',
                'height': "6'5\"",
                'weight': '241 lbs',
                'debut_year': 1992,
                'finishers': 'Spear, Edgecution',
                'signature_moves': 'Edge-O-Matic, Diving Crossbody, Impaler DDT',
                'about': 'The Rated-R Superstar Edge is an 11-time World Champion and WWE Hall of Famer. Debuting as part of The Brood, he became a legendary tag team wrestler with Christian before achieving singles success. His rivalries with John Cena, The Undertaker, and Matt Hardy are iconic. After retiring due to injury in 2011, Edge made a miraculous return in 2020. Now performs in AEW.',
            },
            {
                'name': 'Christian',
                'real_name': 'William Jason Reso',
                'birth_date': '1973-11-30',
                'hometown': 'Kitchener, Ontario, Canada',
                'nationality': 'Canadian',
                'height': "6'1\"",
                'weight': '212 lbs',
                'debut_year': 1995,
                'finishers': 'Killswitch, Unprettier, Spear',
                'signature_moves': 'Frog Splash, Pendulum Kick',
                'about': 'Captain Charisma Christian is a multiple-time World Champion and one of the most underrated performers of his generation. After legendary tag team success with Edge, Christian became World Champion in both TNA and WWE. His technical ability and character work made him a consistent performer for decades. Currently manages in AEW.',
            },
            {
                'name': 'Jeff Hardy',
                'real_name': 'Jeffrey Nero Hardy',
                'birth_date': '1977-08-31',
                'hometown': 'Cameron, North Carolina',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '225 lbs',
                'debut_year': 1994,
                'finishers': 'Swanton Bomb, Twist of Fate',
                'signature_moves': 'Whisper in the Wind, Poetry in Motion, Hardyac Arrest',
                'about': 'Jeff Hardy is one of wrestling\'s most daring high-flyers. As part of The Hardy Boyz with brother Matt, he revolutionized tag team wrestling with their TLC matches against Edge & Christian and the Dudley Boyz. A 3-time World Champion, Hardy\'s charisma and risk-taking made him one of the most popular wrestlers of multiple generations.',
            },
            {
                'name': 'Matt Hardy',
                'real_name': 'Matthew Moore Hardy',
                'birth_date': '1974-09-23',
                'hometown': 'Cameron, North Carolina',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '236 lbs',
                'debut_year': 1992,
                'finishers': 'Twist of Fate, Side Effect',
                'signature_moves': 'Legdrop from Second Rope, Poetry in Motion',
                'about': 'Matt Hardy is a creative genius and innovator in professional wrestling. As part of The Hardy Boyz, he helped create the TLC match. His Version 1 character and later Broken/Woken Matt Hardy gimmick showcased his creativity. Matt has won championships across WWE, TNA, and AEW, constantly reinventing himself throughout a 30+ year career.',
            },
            {
                'name': 'Lita',
                'real_name': 'Amy Christine Dumas',
                'birth_date': '1975-04-14',
                'hometown': 'Fort Lauderdale, Florida',
                'nationality': 'American',
                'height': "5'6\"",
                'weight': '135 lbs',
                'debut_year': 1999,
                'retirement_year': 2006,
                'finishers': 'Litasault, DDT',
                'signature_moves': 'Hurricanrana, Lou Thesz Press, Moonsault',
                'about': 'Lita is a 4-time Women\'s Champion and WWE Hall of Famer who revolutionized women\'s wrestling. Her high-flying, athletic style broke barriers in an era when women\'s matches were often secondary. As part of Team Xtreme with The Hardy Boyz, she became one of the most popular stars in WWE. Inducted into the Hall of Fame in 2014.',
            },
            {
                'name': 'Trish Stratus',
                'real_name': 'Patricia Anne Stratigeas',
                'birth_date': '1975-12-18',
                'hometown': 'Richmond Hill, Ontario, Canada',
                'nationality': 'Canadian',
                'height': "5'4\"",
                'weight': '125 lbs',
                'debut_year': 2000,
                'retirement_year': 2006,
                'finishers': 'Stratusfaction, Chick Kick',
                'signature_moves': 'Handstand Hurricanrana, Lou Thesz Press',
                'about': 'Trish Stratus is a 7-time Women\'s Champion and considered one of the greatest female wrestlers of all time. Debuting as a fitness model and manager, she evolved into an elite in-ring competitor. Her rivalry with Lita elevated women\'s wrestling, and her matches against Mickie James and Victoria are classics. WWE Hall of Famer inducted in 2013.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} Attitude Era stars')
        return updated

    def enrich_ruthless_aggression(self):
        """Enrich Ruthless Aggression Era stars."""
        self.stdout.write('--- Enriching Ruthless Aggression Era ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Brock Lesnar',
                'real_name': 'Brock Edward Lesnar',
                'birth_date': '1977-07-12',
                'hometown': 'Webster, South Dakota',
                'nationality': 'American',
                'height': "6'3\"",
                'weight': '286 lbs',
                'debut_year': 2000,
                'finishers': 'F-5, Kimura Lock',
                'signature_moves': 'German Suplex, Belly-to-Belly Suplex, Shoulder Thrust',
                'about': 'Brock Lesnar is one of the most dominant athletes in combat sports history. The Next Big Thing became the youngest WWE Champion at 25. After leaving for NFL and UFC (where he became Heavyweight Champion), Lesnar returned to WWE and ended The Undertaker\'s WrestleMania streak. An 8-time World Champion known for his legitimate fighting background.',
            },
            {
                'name': 'John Cena',
                'real_name': 'John Felix Anthony Cena Jr.',
                'birth_date': '1977-04-23',
                'hometown': 'West Newbury, Massachusetts',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '251 lbs',
                'debut_year': 2000,
                'finishers': 'Attitude Adjustment, STF',
                'signature_moves': 'Five Knuckle Shuffle, Shoulder Block, Spinout Powerbomb',
                'about': 'John Cena is a 16-time World Champion, tying Ric Flair\'s record. The face of WWE for over a decade, Cena\'s Never Give Up mentality and Make-A-Wish work made him a cultural icon. His feuds with Edge, Randy Orton, and CM Punk are legendary. Cena has transitioned to Hollywood stardom while remaining connected to WWE.',
            },
            {
                'name': 'Batista',
                'real_name': 'David Michael Bautista Jr.',
                'birth_date': '1969-01-18',
                'hometown': 'Washington, D.C.',
                'nationality': 'American',
                'height': "6'6\"",
                'weight': '290 lbs',
                'debut_year': 2000,
                'retirement_year': 2019,
                'finishers': 'Batista Bomb',
                'signature_moves': 'Spear, Spinebuster, Shoulders to the Corner',
                'about': 'Batista, The Animal, is a 6-time World Champion and one of the most physically impressive wrestlers of his era. As part of Evolution with Triple H, Ric Flair, and Randy Orton, he learned from the best before his face turn. His WrestleMania 21 moment thumbing down Triple H is iconic. Now a successful Hollywood actor starring in Guardians of the Galaxy.',
            },
            {
                'name': 'Randy Orton',
                'real_name': 'Randal Keith Orton',
                'birth_date': '1980-04-01',
                'hometown': 'St. Louis, Missouri',
                'nationality': 'American',
                'height': "6'5\"",
                'weight': '250 lbs',
                'debut_year': 2000,
                'finishers': 'RKO, Punt Kick',
                'signature_moves': 'Rope-Hung DDT, Powerslam, Garvin Stomp',
                'trained_by': 'Bob Orton Jr.',
                'about': 'Randy Orton, The Viper, is a 14-time World Champion and third-generation wrestler. The Legend Killer became the youngest World Champion at 24. His methodical style and devastating RKO from outta nowhere have made him one of WWE\'s most consistent main eventers for two decades. His feuds with John Cena, Triple H, and The Undertaker are legendary.',
            },
            {
                'name': 'Rey Mysterio',
                'real_name': 'Oscar Gutierrez Rubio',
                'birth_date': '1974-12-11',
                'hometown': 'San Diego, California',
                'nationality': 'American',
                'height': "5'6\"",
                'weight': '175 lbs',
                'debut_year': 1989,
                'finishers': '619, West Coast Pop, Frog Splash',
                'signature_moves': 'Hurricanrana, Springboard Crossbody, Seated Senton',
                'trained_by': 'Rey Mysterio Sr.',
                'about': 'Rey Mysterio is the greatest cruiserweight in wrestling history. The Master of the 619 revolutionized high-flying wrestling and proved size doesn\'t matter. A World Champion in WWE, WCW, and AAA, Mysterio\'s matches against Eddie Guerrero, Psicosis, and Juventud Guerrera are legendary. Still competing at the highest level alongside his son Dominik.',
            },
            {
                'name': 'Eddie Guerrero',
                'real_name': 'Eduardo Gory Guerrero Llanes',
                'birth_date': '1967-10-09',
                'hometown': 'El Paso, Texas',
                'nationality': 'American',
                'height': "5'8\"",
                'weight': '220 lbs',
                'debut_year': 1987,
                'retirement_year': 2005,
                'finishers': 'Frog Splash, Lasso from El Paso',
                'signature_moves': 'Three Amigos, Gory Special',
                'about': 'Eddie Guerrero was one of the most beloved wrestlers of all time. Latino Heat could lie, cheat, and steal his way to victory while remaining a fan favorite. A World Champion in WWE and WCW, Eddie\'s matches against Rey Mysterio and his redemption story touched millions. His passing in 2005 devastated the wrestling world. Viva La Raza!',
            },
            {
                'name': 'CM Punk',
                'real_name': 'Phillip Jack Brooks',
                'birth_date': '1978-10-26',
                'hometown': 'Chicago, Illinois',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '218 lbs',
                'debut_year': 1999,
                'finishers': 'Go To Sleep, Anaconda Vise',
                'signature_moves': 'Running Knee, Diving Elbow Drop, Roundhouse Kick',
                'about': 'CM Punk is the Voice of the Voiceless and one of wrestling\'s most controversial figures. His Pipebomb promo in 2011 changed WWE and his 434-day WWE Championship reign was historic. The straight-edge superstar\'s feuds with John Cena, Jeff Hardy, and The Rock are legendary. After leaving WWE in 2014, he joined AEW and later returned to WWE in 2023.',
            },
            {
                'name': 'Daniel Bryan',
                'real_name': 'Bryan Lloyd Danielson',
                'birth_date': '1981-05-22',
                'hometown': 'Aberdeen, Washington',
                'nationality': 'American',
                'height': "5'10\"",
                'weight': '210 lbs',
                'debut_year': 1999,
                'finishers': 'Yes! Lock, Running Knee, Cattle Mutilation',
                'signature_moves': 'Yes! Kicks, Suicide Dive, Missile Dropkick',
                'trained_by': 'Shawn Michaels, William Regal',
                'about': 'Daniel Bryan is considered one of the greatest technical wrestlers ever. The American Dragon conquered the indie scene before joining WWE. His Yes! Movement led to his WrestleMania XXX main event victory. After retiring due to concussions, he was cleared to return and continues wrestling in AEW as Bryan Danielson. A vegan and environmentalist who brings legitimacy to everything he does.',
            },
            {
                'name': 'The Miz',
                'real_name': 'Michael Gregory Mizanin',
                'birth_date': '1980-10-08',
                'hometown': 'Parma, Ohio',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '221 lbs',
                'debut_year': 2004,
                'finishers': 'Skull Crushing Finale',
                'signature_moves': 'Corner Clothesline, It Kicks, Reality Check',
                'about': 'The Miz went from MTV\'s Real World to WWE Champion, main-eventing WrestleMania 27 against John Cena. Initially dismissed due to his reality TV background, Miz worked harder than anyone to prove himself. A 2-time WWE Champion and multiple-time Intercontinental Champion, his promos are among the best in modern WWE. Married to Maryse.',
            },
            {
                'name': 'Dolph Ziggler',
                'real_name': 'Nicholas Theodore Nemeth',
                'birth_date': '1980-07-27',
                'hometown': 'Hollywood, Florida',
                'nationality': 'American',
                'height': "6'0\"",
                'weight': '213 lbs',
                'debut_year': 2004,
                'finishers': 'Zig Zag, Superkick',
                'signature_moves': 'Famouser, Dropkick, Headstand Headlock',
                'about': 'Dolph Ziggler, The Showoff, is one of wrestling\'s best sellers and most athletic performers. A 2-time World Champion, Ziggler\'s ability to make opponents look like a million bucks while putting on exciting matches made him a favorite of fellow wrestlers and fans alike. His 2014 Survivor Series performance is legendary.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} Ruthless Aggression stars')
        return updated

    def enrich_modern_wwe(self):
        """Enrich Modern Era WWE stars."""
        self.stdout.write('--- Enriching Modern WWE Stars ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Roman Reigns',
                'real_name': 'Leati Joseph Anoaʻi',
                'birth_date': '1985-05-25',
                'hometown': 'Pensacola, Florida',
                'nationality': 'American',
                'height': "6'3\"",
                'weight': '265 lbs',
                'debut_year': 2010,
                'finishers': 'Spear, Guillotine Choke',
                'signature_moves': 'Superman Punch, Drive-By, Samoan Drop',
                'about': 'Roman Reigns, The Tribal Chief, is the Head of the Table and the biggest star in modern WWE. After debuting as part of The Shield, Reigns became the face of WWE. His heel turn in 2020 and 1,316-day Universal Championship reign established him as one of the greatest champions ever. His storyline with The Bloodline has been WWE\'s most compelling narrative in years.',
            },
            {
                'name': 'Seth Rollins',
                'real_name': 'Colby Daniel Lopez',
                'birth_date': '1986-05-28',
                'hometown': 'Davenport, Iowa',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '217 lbs',
                'debut_year': 2005,
                'finishers': 'Curb Stomp, Pedigree',
                'signature_moves': 'Suicide Dive, Superplex into Falcon Arrow, Ripcord Knee',
                'trained_by': 'Danny Daniels',
                'about': 'Seth Rollins, The Visionary, is a 4-time World Champion and arguably the best all-around performer in WWE. The Architect of The Shield became WWE\'s first first triple crown and grand slam champion. His matches are consistently the best on the card, whether he\'s a heel or babyface. His Money in the Bank cash-in at WrestleMania 31 is iconic.',
            },
            {
                'name': 'Cody Rhodes',
                'real_name': 'Cody Garrett Runnels',
                'birth_date': '1985-06-30',
                'hometown': 'Marietta, Georgia',
                'nationality': 'American',
                'height': "6'1\"",
                'weight': '220 lbs',
                'debut_year': 2006,
                'finishers': 'Cross Rhodes, Figure-Four Leglock',
                'signature_moves': 'Cody Cutter, Disaster Kick, Beautiful Disaster',
                'about': 'Cody Rhodes is the son of Dusty Rhodes who stepped out of his father\'s shadow to become a star in his own right. After leaving WWE in 2016, he helped found AEW. His return to WWE in 2022 to finish the story captivated audiences. At WrestleMania 40, he defeated Roman Reigns to win the Undisputed WWE Championship, finishing his family\'s story.',
            },
            {
                'name': 'Becky Lynch',
                'real_name': 'Rebecca Quin',
                'birth_date': '1987-01-30',
                'hometown': 'Dublin, Ireland',
                'nationality': 'Irish',
                'height': "5'6\"",
                'weight': '135 lbs',
                'debut_year': 2002,
                'finishers': 'Dis-Arm-Her',
                'signature_moves': 'Bexploder, Leg Drop',
                'about': 'Becky Lynch, The Man, is the biggest female star in modern WWE. Her heel turn in 2018 and subsequent rise as an anti-hero led to main-eventing WrestleMania 35, the first women\'s main event. A multiple-time champion, Lynch\'s promos and attitude have made her one of the most popular wrestlers regardless of gender.',
            },
            {
                'name': 'Charlotte Flair',
                'real_name': 'Ashley Elizabeth Fliehr',
                'birth_date': '1986-04-05',
                'hometown': 'Charlotte, North Carolina',
                'nationality': 'American',
                'height': "5'10\"",
                'weight': '145 lbs',
                'debut_year': 2012,
                'finishers': 'Figure-Eight, Natural Selection',
                'signature_moves': 'Moonsault, Knife-Edge Chop, Spear',
                'about': 'Charlotte Flair is a 14-time Women\'s Champion and widely considered the greatest female wrestler ever. The daughter of Ric Flair, she has consistently delivered the best women\'s matches in WWE. Part of the Four Horsewomen who revolutionized women\'s wrestling, Charlotte\'s athleticism and presence make her special.',
            },
            {
                'name': 'Bianca Belair',
                'real_name': 'Bianca Nicole Crawford',
                'birth_date': '1989-04-09',
                'hometown': 'Knoxville, Tennessee',
                'nationality': 'American',
                'height': "5'7\"",
                'weight': '160 lbs',
                'debut_year': 2016,
                'finishers': 'KOD (Kiss of Death)',
                'signature_moves': 'Gorilla Press, 450 Splash, Handspring Moonsault',
                'about': 'Bianca Belair, The EST of WWE (Strongest, Fastest, Toughest, etc.), is one of the most athletic performers in wrestling history. Her main event victory over Sasha Banks at WrestleMania 37 was historic. A former track star and CrossFit competitor, Belair uses her signature braid as a weapon and has become one of WWE\'s top stars.',
            },
            {
                'name': 'AJ Styles',
                'real_name': 'Allen Neal Jones',
                'birth_date': '1977-06-02',
                'hometown': 'Gainesville, Georgia',
                'nationality': 'American',
                'height': "5'11\"",
                'weight': '218 lbs',
                'debut_year': 1998,
                'finishers': 'Styles Clash, Phenomenal Forearm, Calf Crusher',
                'signature_moves': 'Pele Kick, Ushigoroshi, Moonsault into Inverted DDT',
                'about': 'AJ Styles, The Phenomenal One, is considered one of the greatest wrestlers of his generation. After legendary runs in TNA, ROH, and NJPW, he debuted in WWE at the 2016 Royal Rumble. A 2-time WWE Champion, Styles\' matches against John Cena, Roman Reigns, and Shinsuke Nakamura are instant classics. His versatility allows him to work any style.',
            },
            {
                'name': 'Kevin Owens',
                'real_name': 'Kevin Yanick Steen',
                'birth_date': '1984-05-07',
                'hometown': 'Marieville, Quebec, Canada',
                'nationality': 'Canadian',
                'height': "6'0\"",
                'weight': '266 lbs',
                'debut_year': 2000,
                'finishers': 'Stunner, Pop-Up Powerbomb',
                'signature_moves': 'Cannonball, Superkick, Package Piledriver',
                'about': 'Kevin Owens is a prize fighter who gives everything in every match. After conquering the indie scene as Kevin Steen, he debuted in NXT by defeating John Cena clean. A former Universal Champion, Owens\' brawling style and promo ability make him a complete package. His feuds with Sami Zayn, Cody Rhodes, and Roman Reigns are highlights.',
            },
            {
                'name': 'Sami Zayn',
                'real_name': 'Rami Sebei',
                'birth_date': '1984-07-12',
                'hometown': 'Laval, Quebec, Canada',
                'nationality': 'Canadian',
                'height': "6'1\"",
                'weight': '212 lbs',
                'debut_year': 2002,
                'finishers': 'Helluva Kick, Blue Thunder Bomb',
                'signature_moves': 'Exploder Suplex, Tornado DDT, Tope con Hilo',
                'about': 'Sami Zayn, formerly El Generico, is one of the most beloved wrestlers in the industry. His NXT rivalry with Kevin Owens is legendary. Zayn\'s underdog babyface work and ability to connect with crowds is unmatched. His work with The Bloodline and ultimate triumph at WrestleMania 40 showed his range as a performer.',
            },
            {
                'name': 'Rhea Ripley',
                'real_name': 'Demi Bennett',
                'birth_date': '1996-10-11',
                'hometown': 'Adelaide, Australia',
                'nationality': 'Australian',
                'height': "5'8\"",
                'weight': '137 lbs',
                'debut_year': 2013,
                'finishers': 'Riptide',
                'signature_moves': 'Prism Trap, Northern Lights Suplex, Dropkick',
                'about': 'Rhea Ripley, Mami, is one of the most dominant forces in women\'s wrestling. The first NXT UK Women\'s Champion and NXT Women\'s Champion, she won the Women\'s Royal Rumble and became champion at WrestleMania 39. Her unique look and powerful style have made her a crossover star and leader of The Judgment Day.',
            },
            {
                'name': 'Gunther',
                'real_name': 'Walter Hahn',
                'birth_date': '1987-08-19',
                'hometown': 'Vienna, Austria',
                'nationality': 'Austrian',
                'height': "6'4\"",
                'weight': '287 lbs',
                'debut_year': 2005,
                'finishers': 'Powerbomb, Sleeper Hold',
                'signature_moves': 'Chop, Dropkick, German Suplex',
                'about': 'Gunther, The Ring General, had the longest Intercontinental Championship reign in WWE history at 666 days. Known for his brutal chops and mat-based style, Gunther ruled NXT UK as WALTER before moving to the main roster. His matches are hard-hitting clinics that harken back to a different era of wrestling.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} Modern WWE stars')
        return updated

    def enrich_aew_roster(self):
        """Enrich AEW roster members."""
        self.stdout.write('--- Enriching AEW Roster ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Kenny Omega',
                'real_name': 'Tyson Smith',
                'birth_date': '1983-10-16',
                'hometown': 'Winnipeg, Manitoba, Canada',
                'nationality': 'Canadian',
                'height': "6'0\"",
                'weight': '205 lbs',
                'debut_year': 1999,
                'finishers': 'One-Winged Angel, V-Trigger',
                'signature_moves': 'Snap Dragon Suplex, Rise of the Terminator, Kotaro Krusher',
                'about': 'Kenny Omega, The Best Bout Machine, is considered one of the greatest wrestlers of all time. His matches in NJPW against Kazuchika Okada set new standards for wrestling. An EVP and founder of AEW, Omega has been AEW World Champion and held the Impact and AAA Mega Championships simultaneously as belt collector.',
            },
            {
                'name': 'Jon Moxley',
                'real_name': 'Jonathan Good',
                'birth_date': '1985-12-07',
                'hometown': 'Cincinnati, Ohio',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '234 lbs',
                'debut_year': 2004,
                'finishers': 'Paradigm Shift, Death Rider, Bulldog Choke',
                'signature_moves': 'Suicide Dive, Cutter',
                'aliases': 'Dean Ambrose',
                'about': 'Jon Moxley is a violent, unpredictable brawler and leader of the Blackpool Combat Club. After leaving WWE as Dean Ambrose (member of The Shield), he reinvented himself in AEW. A 4-time AEW World Champion, Moxley has also held the IWGP US Championship and CZW World Championship. His hardcore style and promos are legendary.',
            },
            {
                'name': 'MJF',
                'real_name': 'Maxwell Jacob Friedman',
                'birth_date': '1996-03-15',
                'hometown': 'Plainview, New York',
                'nationality': 'American',
                'height': "5'11\"",
                'weight': '212 lbs',
                'debut_year': 2015,
                'finishers': 'Heat Seeker, Salt of the Earth',
                'signature_moves': 'Kangaroo Kick, Eye Poke',
                'about': 'MJF is professional wrestling\'s best heel and one of its greatest talkers. The self-proclaimed Salt of the Earth uses every trick in the book to win. A 2-time AEW World Champion with the third-longest reign in company history, MJF\'s promos and character work are unmatched in modern wrestling.',
            },
            {
                'name': 'Hangman Adam Page',
                'real_name': 'Stephen Blake Woltz',
                'birth_date': '1991-07-27',
                'hometown': 'Scottsburg, Virginia',
                'nationality': 'American',
                'height': "6'0\"",
                'weight': '214 lbs',
                'debut_year': 2008,
                'finishers': 'Buckshot Lariat, Deadeye',
                'signature_moves': 'Fallaway Slam, Moonsault, Lariat',
                'about': 'Hangman Adam Page\'s journey from tag team wrestler to anxious millennial cowboy to AEW World Champion is one of wrestling\'s great long-term stories. His victory over Kenny Omega at Full Gear 2021 was years in the making. Page\'s in-ring ability and emotional storytelling resonate deeply with fans.',
            },
            {
                'name': 'Darby Allin',
                'real_name': 'Samuel Ratsch',
                'birth_date': '1992-01-07',
                'hometown': 'Seattle, Washington',
                'nationality': 'American',
                'height': "5'8\"",
                'weight': '170 lbs',
                'debut_year': 2015,
                'finishers': 'Coffin Drop',
                'signature_moves': 'Stunner, Code Red, Skateboard attacks',
                'about': 'Darby Allin is a fearless, death-defying performer who treats his body like it\'s rented. An avid skateboarder, Allin\'s unique style and willingness to take insane risks have made him a fan favorite. TNT Champion and tag partner of Sting, Allin brings a punk rock edge to wrestling.',
            },
            {
                'name': 'Orange Cassidy',
                'real_name': 'James Cipperly',
                'birth_date': '1984-11-14',
                'hometown': 'Stewartsville, New Jersey',
                'nationality': 'American',
                'height': "5'11\"",
                'weight': '175 lbs',
                'debut_year': 2004,
                'finishers': 'Orange Punch, Beach Break',
                'signature_moves': 'Superman Punch, Diving DDT, Tope Suicida',
                'about': 'Orange Cassidy\'s gimmick of wrestling with his hands in his pockets has made him one of AEW\'s most popular stars. When he actually tries, Cassidy is an excellent wrestler. His feud with Chris Jericho proved he can work at the main event level. International and AEW World Trios Champion.',
            },
            {
                'name': 'Jade Cargill',
                'real_name': 'Jade Cargill',
                'birth_date': '1992-06-03',
                'hometown': 'Brandon, Florida',
                'nationality': 'American',
                'height': "5'10\"",
                'weight': '155 lbs',
                'debut_year': 2020,
                'finishers': 'Jaded',
                'signature_moves': 'Pump Kick, Fallaway Slam, Powerbomb',
                'about': 'Jade Cargill is THAT B****. The most dominant TBS Champion in AEW history went undefeated for over two years. Her look, power, and presence are unmatched. After signing with WWE in 2024, she has continued her dominance as part of their women\'s division.',
            },
            {
                'name': 'Will Ospreay',
                'real_name': 'William Peter Ospreay',
                'birth_date': '1993-05-07',
                'hometown': 'Romford, England',
                'nationality': 'British',
                'height': "5'11\"",
                'weight': '205 lbs',
                'debut_year': 2012,
                'finishers': 'Hidden Blade, Storm Breaker, Oscutter',
                'signature_moves': 'Pip Pip Cheerio, Robinson Special, Handspring Enzuigiri',
                'about': 'Will Ospreay is the Aerial Assassin and one of the best wrestlers in the world. After revolutionizing junior heavyweight wrestling in NJPW, he bulked up and became IWGP World Champion. Now in AEW, Ospreay continues to put on Match of the Year candidates regularly. His matches against Kenny Omega and Kazuchika Okada are legendary.',
            },
            {
                'name': 'Swerve Strickland',
                'real_name': 'Shane Strickland',
                'birth_date': '1990-11-27',
                'hometown': 'Tacoma, Washington',
                'nationality': 'American',
                'height': "5'9\"",
                'weight': '185 lbs',
                'debut_year': 2011,
                'finishers': 'Swerve Stomp, JML Driver',
                'signature_moves': 'House Call, Rolling Flatliner, 450 Splash',
                'about': 'Swerve Strickland is AEW World Champion and one of the most charismatic performers in wrestling. Known for his creative offense and swagger, Swerve rose through the indies, Lucha Underground, and WWE before becoming a star in AEW. His feud with Hangman Adam Page has been violent and compelling.',
            },
            {
                'name': 'Mercedes Mone',
                'real_name': 'Mercedes Justine Kaestner-Varnado',
                'birth_date': '1992-01-26',
                'hometown': 'Fairfield, California',
                'nationality': 'American',
                'height': "5'5\"",
                'weight': '114 lbs',
                'debut_year': 2010,
                'finishers': 'Statement Maker, Mone Maker',
                'signature_moves': 'Bankrupt, Double Knee Drop, Meteora',
                'aliases': 'Sasha Banks',
                'about': 'Mercedes Mone, formerly Sasha Banks, is The CEO and one of the greatest women\'s wrestlers ever. Part of WWE\'s Four Horsewomen, she main-evented WrestleMania and created instant classics with Charlotte, Bayley, and Becky. Now in AEW, she holds multiple championships and continues her legacy.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} AEW roster')
        return updated

    def enrich_wcw_ecw(self):
        """Enrich WCW and ECW stars."""
        self.stdout.write('--- Enriching WCW/ECW Stars ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Goldberg',
                'real_name': 'William Scott Goldberg',
                'birth_date': '1966-12-27',
                'hometown': 'Tulsa, Oklahoma',
                'nationality': 'American',
                'height': "6'4\"",
                'weight': '285 lbs',
                'debut_year': 1997,
                'finishers': 'Jackhammer, Spear',
                'signature_moves': 'Press Slam, Gorilla Press',
                'about': 'Goldberg\'s 173-match winning streak in WCW made him one of the most dominant forces in wrestling history. A former NFL player, Goldberg\'s intensity and devastating moveset made him an instant star. His matches against Hogan and the nWo changed wrestling. WWE Hall of Famer who returned for multiple runs.',
            },
            {
                'name': 'Sting',
                'real_name': 'Steven James Borden',
                'birth_date': '1959-03-20',
                'hometown': 'Omaha, Nebraska',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '250 lbs',
                'debut_year': 1985,
                'retirement_year': 2024,
                'finishers': 'Scorpion Deathlock, Scorpion Death Drop',
                'signature_moves': 'Stinger Splash, Diving Splash',
                'about': 'Sting, The Icon, is WCW\'s greatest homegrown star. His transformation from colorful surfer to dark, crow-inspired avenger during the nWo era is legendary. A 15-time World Champion across promotions, Sting finally joined WWE/AEW late in his career. His final match at Revolution 2024 was a fitting farewell.',
            },
            {
                'name': 'Diamond Dallas Page',
                'real_name': 'Page Joseph Falkinburg',
                'birth_date': '1956-04-05',
                'hometown': 'Point Pleasant, New Jersey',
                'nationality': 'American',
                'height': "6'5\"",
                'weight': '248 lbs',
                'debut_year': 1991,
                'finishers': 'Diamond Cutter',
                'signature_moves': 'Discus Clothesline, Pancake',
                'about': 'DDP didn\'t become a wrestler until his late 30s but became one of WCW\'s biggest stars. A 3-time WCW World Champion, his Diamond Cutter from anywhere was devastating. Post-career, DDP Yoga has helped countless wrestlers and fans recover from injuries and addiction. A true self-made success story.',
            },
            {
                'name': 'Kevin Nash',
                'real_name': 'Kevin Scott Nash',
                'birth_date': '1959-07-09',
                'hometown': 'Detroit, Michigan',
                'nationality': 'American',
                'height': "7'0\"",
                'weight': '328 lbs',
                'debut_year': 1990,
                'finishers': 'Jackknife Powerbomb',
                'signature_moves': 'Snake Eyes, Big Boot, Sidewalk Slam',
                'aliases': 'Diesel, Oz, Vinnie Vegas',
                'about': 'Kevin Nash was one half of the Outsiders and a founding member of the nWo. After a WWE Championship run as Diesel, Nash jumped to WCW and changed the industry. A 6-time World Champion, Nash\'s size and cool factor made him a star. Also known for his behind-the-scenes influence.',
            },
            {
                'name': 'Scott Hall',
                'real_name': 'Scott Oliver Hall',
                'birth_date': '1958-10-20',
                'hometown': 'St. Mary\'s County, Maryland',
                'nationality': 'American',
                'height': "6'7\"",
                'weight': '287 lbs',
                'debut_year': 1984,
                'retirement_year': 2010,
                'finishers': 'Razor\'s Edge, Outsider\'s Edge',
                'signature_moves': 'Fallaway Slam, Discus Punch',
                'aliases': 'Razor Ramon',
                'about': 'Scott Hall, as Razor Ramon, was one of the coolest characters in WWF history. His jump to WCW with Kevin Nash launched the nWo and the Monday Night Wars. A 4-time Intercontinental Champion, Hall\'s ladder matches with Shawn Michaels are legendary. His troubled personal life and redemption were documented in The Resurrection of Jake the Snake.',
            },
            {
                'name': 'Booker T',
                'real_name': 'Robert Booker Tio Huffman',
                'birth_date': '1965-03-01',
                'hometown': 'Houston, Texas',
                'nationality': 'American',
                'height': "6'3\"",
                'weight': '256 lbs',
                'debut_year': 1989,
                'finishers': 'Scissors Kick, Book End, Spinaroonie',
                'signature_moves': 'Ax Kick, Side Slam, Harlem Sidekick',
                'about': 'Booker T is a 6-time World Champion who rose from Harlem Heat tag team success to singles stardom. His 5-time WCW Champion catchphrase Can you dig it, SUCKA?! became iconic. After WCW closed, Booker had a successful WWE run including winning King of the Ring. Now a commentator and WWE Hall of Famer.',
            },
            {
                'name': 'Rob Van Dam',
                'real_name': 'Robert Alex Szatkowski',
                'birth_date': '1970-12-18',
                'hometown': 'Battle Creek, Michigan',
                'nationality': 'American',
                'height': "6'0\"",
                'weight': '235 lbs',
                'debut_year': 1990,
                'finishers': 'Five Star Frog Splash, Van Daminator',
                'signature_moves': 'Rolling Thunder, Split-Legged Moonsault, Van Terminator',
                'about': 'Rob Van Dam, The Whole F\'n Show, revolutionized wrestling with his martial arts-influenced high-flying style. ECW\'s most popular star, RVD held the TV Championship for over two years. His WWE run saw him become WWE and ECW Champion in one night. Known for his laid-back attitude and Mr. Monday Night persona.',
            },
            {
                'name': 'Sabu',
                'real_name': 'Terry Michael Brunk',
                'birth_date': '1964-12-12',
                'hometown': 'Detroit, Michigan',
                'nationality': 'American',
                'height': "5'11\"",
                'weight': '220 lbs',
                'debut_year': 1985,
                'finishers': 'Arabian Facebuster, Triple Jump Moonsault',
                'signature_moves': 'Chair Surfing, Arabian Skullcrusher, Camel Clutch',
                'about': 'Sabu is the Homicidal, Suicidal, Genocidal death-match legend who defined ECW\'s extreme style. The nephew of The Sheik, Sabu\'s willingness to destroy his body with tables, chairs, and barbed wire made him a cult hero. His tag team with Rob Van Dam was legendary.',
            },
            {
                'name': 'Tommy Dreamer',
                'real_name': 'Thomas James Laughlin',
                'birth_date': '1971-02-14',
                'hometown': 'Yonkers, New York',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '255 lbs',
                'debut_year': 1989,
                'finishers': 'Dreamer Driver, DDT',
                'signature_moves': 'Cane Shots, Piledriver, Crossbody',
                'about': 'Tommy Dreamer is the heart and soul of ECW. The Innovator of Violence endured countless beatings, including his legendary feud with Raven, before finally winning the ECW Championship on the last episode of ECW on TNN. Dreamer has kept ECW\'s legacy alive through House of Hardcore.',
            },
            {
                'name': 'Taz',
                'real_name': 'Peter Senerchia',
                'birth_date': '1967-10-11',
                'hometown': 'Brooklyn, New York',
                'nationality': 'American',
                'height': "5'9\"",
                'weight': '245 lbs',
                'debut_year': 1987,
                'retirement_year': 2002,
                'finishers': 'Tazmission, Tazplex',
                'signature_moves': 'Various Suplexes, Arm Capture Suplex',
                'about': 'Taz was the Human Suplex Machine and FTW Champion who dominated ECW. Despite his smaller stature, Taz\'s legitimate fighting background and intense persona made him a top star. After retiring due to injuries, Taz became a color commentator for WWE and AEW.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} WCW/ECW stars')
        return updated

    def enrich_tna_impact(self):
        """Enrich TNA/Impact stars."""
        self.stdout.write('--- Enriching TNA/Impact Stars ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Samoa Joe',
                'real_name': 'Nuufolau Joel Seanoa',
                'birth_date': '1979-03-17',
                'hometown': 'Orange County, California',
                'nationality': 'American',
                'height': "6'2\"",
                'weight': '282 lbs',
                'debut_year': 1999,
                'finishers': 'Coquina Clutch, Muscle Buster',
                'signature_moves': 'Suicide Dive, Senton, Ole Kick',
                'about': 'Samoa Joe is one of the most intense competitors in wrestling. His ROH World Championship reign and legendary TNA run established him as a top star. In WWE, he became NXT Champion before moving to the main roster. Known for his MMA-influenced style and devastating submissions.',
            },
            {
                'name': 'Bobby Roode',
                'real_name': 'Robert Francis Roode Jr.',
                'birth_date': '1977-05-11',
                'hometown': 'Peterborough, Ontario, Canada',
                'nationality': 'Canadian',
                'height': "6'0\"",
                'weight': '235 lbs',
                'debut_year': 1998,
                'finishers': 'Roode Bomb, Glorious DDT',
                'signature_moves': 'Blockbuster, Spinebuster',
                'about': 'Bobby Roode is a Grand Slam Champion in TNA and multiple-time champion in WWE. As part of Beer Money with James Storm, he was half of one of the greatest tag teams ever. His Glorious entrance theme became legendary. Now performs as Robert Roode in WWE.',
            },
            {
                'name': 'James Storm',
                'real_name': 'James Allen Cox',
                'birth_date': '1977-06-01',
                'hometown': 'Franklin, Tennessee',
                'nationality': 'American',
                'height': "6'0\"",
                'weight': '228 lbs',
                'debut_year': 1997,
                'finishers': 'Last Call Superkick, Eye of the Storm',
                'signature_moves': 'Backstabber, Codebreaker off ropes',
                'about': 'The Cowboy James Storm is TNA\'s longest-tenured performer. Half of America\'s Most Wanted with Chris Harris and Beer Money with Bobby Roode, Storm finally won the TNA World Championship in 2011. Sorry about your damn luck became his iconic catchphrase.',
            },
            {
                'name': 'Austin Aries',
                'real_name': 'Daniel Healy Solwold Jr.',
                'birth_date': '1978-04-15',
                'hometown': 'Milwaukee, Wisconsin',
                'nationality': 'American',
                'height': "5'9\"",
                'weight': '202 lbs',
                'debut_year': 1999,
                'finishers': 'Brainbuster, Last Chancery',
                'signature_moves': 'Corner Dropkick, Suicide Dive, Pendulum Elbow',
                'about': 'Austin Aries, The Greatest Man That Ever Lived, is a former TNA World Champion and X Division standout. His option C cash-in concept became legendary. Known for his arrogant heel persona and technical wrestling ability.',
            },
            {
                'name': 'Moose',
                'real_name': 'Quinn Ojinnaka',
                'birth_date': '1983-09-07',
                'hometown': 'Marietta, Georgia',
                'nationality': 'American',
                'height': "6'5\"",
                'weight': '285 lbs',
                'debut_year': 2012,
                'finishers': 'Spear, No Jackhammer Needed',
                'signature_moves': 'Go To Hell, Discus Clothesline, Pump Kick',
                'about': 'Moose is a former NFL offensive lineman who became Impact World Champion. His athletic ability and power make him an imposing presence. After years as a top star in Impact, Moose has become one of the company\'s franchise players.',
            },
            {
                'name': 'Josh Alexander',
                'real_name': 'Joshua Bauman',
                'birth_date': '1987-06-27',
                'hometown': 'Etobicoke, Ontario, Canada',
                'nationality': 'Canadian',
                'height': "5'10\"",
                'weight': '230 lbs',
                'debut_year': 2005,
                'finishers': 'C4 Spike, Ankle Lock',
                'signature_moves': 'Divine Intervention, Multiple Suplexes',
                'about': 'The Walking Weapon Josh Alexander is a 2-time Impact World Champion and considered the best wrestler in Impact today. His amateur wrestling background makes him a submission specialist. Alexander has had show-stealing matches against everyone put in front of him.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} TNA/Impact stars')
        return updated

    def enrich_japanese_wrestlers(self):
        """Enrich Japanese wrestling legends and current stars."""
        self.stdout.write('--- Enriching Japanese Wrestlers ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Kazuchika Okada',
                'real_name': 'Kazuchika Okada',
                'birth_date': '1987-11-08',
                'hometown': 'Anjo, Aichi, Japan',
                'nationality': 'Japanese',
                'height': "6'3\"",
                'weight': '241 lbs',
                'debut_year': 2004,
                'finishers': 'Rainmaker, Money Clip',
                'signature_moves': 'Dropkick, Tombstone Piledriver, Air Raid Crash Neckbreaker',
                'about': 'Kazuchika Okada, The Rainmaker, is widely considered the greatest wrestler of his generation. A 5-time IWGP Heavyweight Champion, his matches against Kenny Omega redefined what was possible in wrestling. Now signed to AEW, Okada continues to deliver at the highest level. His 720-day IWGP Championship reign is legendary.',
            },
            {
                'name': 'Hiroshi Tanahashi',
                'real_name': 'Hiroshi Tanahashi',
                'birth_date': '1976-11-13',
                'hometown': 'Ogaki, Gifu, Japan',
                'nationality': 'Japanese',
                'height': "6'0\"",
                'weight': '227 lbs',
                'debut_year': 1999,
                'finishers': 'High Fly Flow, Texas Cloverleaf',
                'signature_moves': 'Slingblade, Dragon Screw, Twist and Shout',
                'about': 'The Ace Hiroshi Tanahashi saved New Japan Pro Wrestling. When the company was at its lowest point, Tanahashi carried it on his back with his charisma and match quality. An 8-time IWGP Heavyweight Champion, his feuds with Okada and Nakamura defined a generation. The Once in a Century Talent.',
            },
            {
                'name': 'Tetsuya Naito',
                'real_name': 'Tetsuya Naito',
                'birth_date': '1982-06-22',
                'hometown': 'Tokyo, Japan',
                'nationality': 'Japanese',
                'height': "5'11\"",
                'weight': '220 lbs',
                'debut_year': 2006,
                'finishers': 'Destino, Stardust Press',
                'signature_moves': 'Gloria, Combinacion Cabron, Flying Forearm',
                'about': 'Tetsuya Naito leads Los Ingobernables de Japon with tranquilo coolness. After fans voted against him headlining the Tokyo Dome, Naito transformed into wrestling\'s coolest star. A 2-time IWGP World Champion who finally won both titles at WrestleKingdom 14. Known for his slow, deliberate pace and belt-dropping antics.',
            },
            {
                'name': 'Shinsuke Nakamura',
                'real_name': 'Shinsuke Nakamura',
                'birth_date': '1980-02-24',
                'hometown': 'Mineyama, Kyoto, Japan',
                'nationality': 'Japanese',
                'height': "6'2\"",
                'weight': '229 lbs',
                'debut_year': 2002,
                'finishers': 'Kinshasa',
                'signature_moves': 'Inverted Powerslam, Good Vibrations, Landslide',
                'about': 'The King of Strong Style Shinsuke Nakamura is one of wrestling\'s most unique performers. His fighting spirit and charisma made him a 3-time IWGP Heavyweight Champion. Nakamura joined WWE in 2016 and won the NXT Championship, Royal Rumble, and multiple Intercontinental Championships. His entrance is iconic.',
            },
            {
                'name': 'Minoru Suzuki',
                'real_name': 'Minoru Suzuki',
                'birth_date': '1968-06-17',
                'hometown': 'Yokohama, Japan',
                'nationality': 'Japanese',
                'height': "5'11\"",
                'weight': '218 lbs',
                'debut_year': 1988,
                'finishers': 'Gotch-Style Piledriver, Rear Naked Choke',
                'signature_moves': 'Penalty Kick, Sleeper Hold, Forearm Strikes',
                'about': 'Minoru Suzuki is the King of Pro Wrestling and leader of Suzuki-gun. A shoot-style legend and co-founder of Pancrase MMA, Suzuki brings legitimate danger to every match. Even in his 50s, he remains one of the most terrifying wrestlers alive. His entrance to Kaze Ni Nare strikes fear.',
            },
            {
                'name': 'Kenta Kobashi',
                'real_name': 'Kenta Kobashi',
                'birth_date': '1967-03-27',
                'hometown': 'Fukuchiyama, Kyoto, Japan',
                'nationality': 'Japanese',
                'height': "6'1\"",
                'weight': '248 lbs',
                'debut_year': 1988,
                'retirement_year': 2013,
                'finishers': 'Burning Hammer, Burning Lariat',
                'signature_moves': 'Half Nelson Suplex, Moonsault, Orange Crush',
                'about': 'Kenta Kobashi is a living legend of Japanese wrestling. His matches in All Japan and Pro Wrestling NOAH are some of the greatest ever. A 3-time Triple Crown Champion, Kobashi overcame cancer to continue wrestling. His 2003 GHC Heavyweight Championship reign lasted 735 days. The Burning Hammer is the most protected finisher ever.',
            },
            {
                'name': 'Mitsuharu Misawa',
                'real_name': 'Mitsuharu Misawa',
                'birth_date': '1962-06-18',
                'hometown': 'Yubari, Hokkaido, Japan',
                'nationality': 'Japanese',
                'height': "6'1\"",
                'weight': '253 lbs',
                'debut_year': 1981,
                'retirement_year': 2009,
                'finishers': 'Emerald Flowsion, Tiger Driver',
                'signature_moves': 'Elbow Strikes, Tiger Suplex, Roaring Elbow',
                'about': 'Mitsuharu Misawa was one of the greatest professional wrestlers of all time. Originally the second Tiger Mask, he became All Japan\'s ace and later founded Pro Wrestling NOAH. His matches against Kobashi, Kawada, and Taue defined the Four Pillars of Heaven era. Tragically passed away in the ring in 2009.',
            },
            {
                'name': 'Jushin Thunder Liger',
                'real_name': 'Keiichi Yamada',
                'birth_date': '1964-11-10',
                'hometown': 'Hiroshima, Japan',
                'nationality': 'Japanese',
                'height': "5'7\"",
                'weight': '205 lbs',
                'debut_year': 1984,
                'retirement_year': 2020,
                'finishers': 'Liger Bomb, Shooting Star Press',
                'signature_moves': 'Surfboard, Romero Special, Palm Strike',
                'about': 'Jushin Thunder Liger revolutionized junior heavyweight wrestling. His 30+ year career saw him become an 11-time IWGP Junior Heavyweight Champion. Liger\'s mask and gear, inspired by the anime character, became iconic. He influenced generations of wrestlers and retired at WrestleKingdom 14.',
            },
            {
                'name': 'Great Muta',
                'real_name': 'Keiji Mutoh',
                'birth_date': '1962-12-23',
                'hometown': 'Yamanashi, Japan',
                'nationality': 'Japanese',
                'height': "6'1\"",
                'weight': '231 lbs',
                'debut_year': 1984,
                'retirement_year': 2023,
                'finishers': 'Moonsault, Shining Wizard',
                'signature_moves': 'Flashing Elbow, Green Mist, Dragon Screw',
                'about': 'The Great Muta is one of wrestling\'s most innovative performers. His face-painted alter ego terrorized opponents with green mist and high-flying moves. Mutoh created the moonsault and Shining Wizard. A champion across NWA, WCW, NJPW, and NOAH, he influenced wrestling globally.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} Japanese wrestlers')
        return updated

    def enrich_mexican_wrestlers(self):
        """Enrich Mexican lucha libre stars."""
        self.stdout.write('--- Enriching Mexican Wrestlers ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'El Santo',
                'real_name': 'Rodolfo Guzmán Huerta',
                'birth_date': '1917-09-23',
                'hometown': 'Tulancingo, Hidalgo, Mexico',
                'nationality': 'Mexican',
                'height': "5'10\"",
                'weight': '209 lbs',
                'debut_year': 1934,
                'retirement_year': 1982,
                'finishers': 'Tope de Cristo, Cavernaria',
                'about': 'El Santo, the Saint, is the most famous masked wrestler of all time and a Mexican cultural icon. His silver mask became legendary, and he starred in over 50 films fighting vampires, werewolves, and other monsters. Santo never revealed his face publicly until a week before his death. He is buried wearing his mask.',
            },
            {
                'name': 'Blue Demon',
                'real_name': 'Alejandro Muñoz Moreno',
                'birth_date': '1922-04-24',
                'hometown': 'García, Nuevo León, Mexico',
                'nationality': 'Mexican',
                'height': "5'9\"",
                'weight': '220 lbs',
                'debut_year': 1948,
                'retirement_year': 1989,
                'finishers': 'Tirabuzón, La Reinera',
                'about': 'Blue Demon was El Santo\'s greatest rival and frequent tag team partner. Together they starred in numerous films fighting supernatural enemies. A 15-time National Championship holder, Blue Demon was nearly as beloved as Santo. His son Blue Demon Jr. continues the legacy.',
            },
            {
                'name': 'Mil Mascaras',
                'real_name': 'Aaron Rodríguez Arellano',
                'birth_date': '1942-07-15',
                'hometown': 'San Luis Potosí, Mexico',
                'nationality': 'Mexican',
                'height': "5'11\"",
                'weight': '232 lbs',
                'debut_year': 1965,
                'finishers': 'Flying Cross Body',
                'signature_moves': 'Plancha, Tope Suicida',
                'about': 'Mil Máscaras, the Man of 1000 Masks, brought lucha libre to the United States and Japan. The first luchador to headline Madison Square Garden, Mil Máscaras influenced generations of high-flyers. He is a WWE Hall of Famer and still makes occasional appearances in his 80s.',
            },
            {
                'name': 'Pentagon Jr',
                'real_name': 'José Solis Huerta',
                'birth_date': '1985-02-15',
                'hometown': 'Mexico City, Mexico',
                'nationality': 'Mexican',
                'height': "5'11\"",
                'weight': '190 lbs',
                'debut_year': 2007,
                'finishers': 'Fear Factor, Pentagon Driver',
                'signature_moves': 'Package Piledriver, Sling Blade, Superkick',
                'aliases': 'Penta El Zero M, Pentagon Dark',
                'about': 'Pentagon Jr\'s Cero Miedo (Zero Fear) catchphrase defined Lucha Underground. His dark character and arm-breaking signature made him a cult favorite. As part of the Lucha Brothers with Rey Fenix, he has won tag championships across AEW, AAA, and Impact. Cero Miedo!',
            },
            {
                'name': 'Rey Fenix',
                'real_name': 'Luis Ignacio Urive Alvirde',
                'birth_date': '1990-12-27',
                'hometown': 'Mexico City, Mexico',
                'nationality': 'Mexican',
                'height': "5'8\"",
                'weight': '170 lbs',
                'debut_year': 2005,
                'finishers': 'Fenix Driver, Fire Driver',
                'signature_moves': 'Springboard Spanish Fly, Rope Walk Kick',
                'about': 'Rey Fenix is one of the most spectacular high-flyers in wrestling history. His innovative offense and death-defying moves must be seen to be believed. As part of the Lucha Brothers and Death Triangle, Fenix has won championships everywhere. He is the nephew of Rey Mysterio and son of Rey Mysterio Sr.',
            },
            {
                'name': 'El Hijo del Vikingo',
                'real_name': 'Unknown',
                'birth_date': '1995-06-12',
                'hometown': 'Reynosa, Tamaulipas, Mexico',
                'nationality': 'Mexican',
                'height': "5'8\"",
                'weight': '176 lbs',
                'debut_year': 2015,
                'finishers': '630 Senton, Imploding 450 Splash',
                'signature_moves': 'Space Flying Tiger Drop, Springboard Dragonrana',
                'about': 'El Hijo del Vikingo is revolutionizing high-flying wrestling with moves that seem impossible. The AAA Mega Champion has had viral moments that have introduced millions to lucha libre. His athleticism and creativity are unmatched in modern wrestling.',
            },
            {
                'name': 'LA Park',
                'real_name': 'Adolfo Muñoz Ibarra',
                'birth_date': '1965-03-11',
                'hometown': 'Mexico City, Mexico',
                'nationality': 'Mexican',
                'height': "5'11\"",
                'weight': '231 lbs',
                'debut_year': 1987,
                'finishers': 'Martinete, La Lanza',
                'signature_moves': 'Suicide Dive, Tope',
                'aliases': 'La Parka, LA Par-K',
                'about': 'LA Park, originally La Parka in AAA and WCW, is one of lucha libre\'s most entertaining performers. His skeleton-themed gear and chair dancing made him a cult favorite. Known for his brawling style and willingness to bleed, LA Park remains popular decades into his career.',
            },
            {
                'name': 'Dr. Wagner Jr',
                'real_name': 'Juan Manuel González Barrón',
                'birth_date': '1965-09-25',
                'hometown': 'Torreón, Coahuila, Mexico',
                'nationality': 'Mexican',
                'height': "5'10\"",
                'weight': '209 lbs',
                'debut_year': 1986,
                'finishers': 'Wagner Driver',
                'signature_moves': 'Michinoku Driver, Tope Suicida',
                'about': 'Dr. Wagner Jr is lucha libre royalty and one of Mexico\'s biggest stars. He lost his mask to Psycho Clown in one of the biggest matches in AAA history. A multiple-time champion across promotions, Wagner represents the traditional values of lucha libre.',
            },
            {
                'name': 'Psycho Clown',
                'real_name': 'Brazo de Oro Jr.',
                'birth_date': '1987-09-06',
                'hometown': 'Mexico City, Mexico',
                'nationality': 'Mexican',
                'height': "5'10\"",
                'weight': '202 lbs',
                'debut_year': 2007,
                'finishers': 'Psycho Driver',
                'signature_moves': 'Canadian Destroyer, Suicide Dive',
                'about': 'Psycho Clown is AAA\'s biggest star and leader of Los Psycho Circus. The face-painted luchador has headlined numerous TripleMania events. His Apuesta matches, including unmasking Dr. Wagner Jr, are legendary. Third generation wrestler who has transcended the clown gimmick.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} Mexican wrestlers')
        return updated

    def enrich_british_indie(self):
        """Enrich British and indie wrestling stars."""
        self.stdout.write('--- Enriching British/Indie Stars ---')
        updated = 0

        wrestlers_data = [
            {
                'name': 'Pete Dunne',
                'real_name': 'Peter Thomas England',
                'birth_date': '1993-11-09',
                'hometown': 'Birmingham, England',
                'nationality': 'British',
                'height': "5'10\"",
                'weight': '205 lbs',
                'debut_year': 2007,
                'finishers': 'Bitter End, Bruiserweight Bomb',
                'signature_moves': 'Finger Manipulation, X-Plex, Enzuigiri',
                'aliases': 'Butch',
                'about': 'Pete Dunne, The Bruiserweight, held the NXT UK Championship for 685 days, the longest reign in brand history. His joint manipulation and stiff style made him a standout. Part of British Strong Style, Dunne is now known as Butch in WWE as part of The Brawling Brutes.',
            },
            {
                'name': 'Tyler Bate',
                'real_name': 'Tyler Bate',
                'birth_date': '1997-03-07',
                'hometown': 'Dudley, England',
                'nationality': 'British',
                'height': "5'8\"",
                'weight': '175 lbs',
                'debut_year': 2012,
                'finishers': 'Tyler Driver 97, Spiral Tap',
                'signature_moves': 'Airplane Spin, Exploder Suplex, Diving Elbow Drop',
                'about': 'Tyler Bate became the first WWE United Kingdom Champion at just 19 years old. The Big Strong Boi\'s combination of power and agility belie his smaller stature. His 2017 match against Pete Dunne at NXT TakeOver: Chicago is an all-time classic. NXT Champion in 2023.',
            },
            {
                'name': 'Ilja Dragunov',
                'real_name': 'Ilja Dragunov',
                'birth_date': '1993-04-07',
                'hometown': 'Moscow, Russia (billed from Hamburg, Germany)',
                'nationality': 'Russian-German',
                'height': "5'10\"",
                'weight': '198 lbs',
                'debut_year': 2010,
                'finishers': 'Torpedo Moscow, H-Bomb',
                'signature_moves': 'Constantine Special, Gotch-Style Piledriver, Senton',
                'about': 'The Czar Ilja Dragunov brings unmatched intensity to every match. His NXT UK Championship victories over WALTER are among the best matches in WWE history. Dragunov\'s all-out style and emotional wrestling connect with fans. NXT Champion who defeated Bron Breakker.',
            },
            {
                'name': 'PAC',
                'real_name': 'Benjamin Satterley',
                'birth_date': '1986-12-22',
                'hometown': 'Newcastle upon Tyne, England',
                'nationality': 'British',
                'height': "5'8\"",
                'weight': '175 lbs',
                'debut_year': 2004,
                'finishers': 'Black Arrow, Brutalizer',
                'signature_moves': '450 Splash, Shooting Star Press, Torture Rack',
                'aliases': 'Neville, Adrian Neville',
                'about': 'PAC, The Bastard, is one of wrestling\'s most impressive high-flyers. After conquering WWE as Neville, he reinvented himself in Dragon Gate and AEW. His athleticism is unmatched, and his heel work is elite. Part of Death Triangle, PAC has been AEW All-Atlantic Champion.',
            },
            {
                'name': 'Marty Scurll',
                'real_name': 'Martin Mayra',
                'birth_date': '1988-04-01',
                'hometown': 'Cambridge, England',
                'nationality': 'British',
                'height': "5'11\"",
                'weight': '178 lbs',
                'debut_year': 2004,
                'finishers': 'Crossface Chickenwing, Graduation',
                'signature_moves': 'Finger Snap, Bird of Prey',
                'about': 'The Villain Marty Scurll was one of the biggest stars of the British wrestling boom. His finger-breaking signature and plague doctor aesthetic made him memorable. ROH World Champion and member of Bullet Club, Scurll was part of wrestling\'s biggest group.',
            },
            {
                'name': 'Claudio Castagnoli',
                'real_name': 'Claudio Castagnoli',
                'birth_date': '1980-12-27',
                'hometown': 'Lucerne, Switzerland',
                'nationality': 'Swiss',
                'height': "6'5\"",
                'weight': '232 lbs',
                'debut_year': 2000,
                'finishers': 'Ricola Bomb, Neutralizer, Giant Swing',
                'signature_moves': 'Uppercut, Pop-Up Uppercut, UFO',
                'aliases': 'Cesaro, Antonio Cesaro',
                'about': 'Claudio Castagnoli is considered one of the strongest and most technically skilled wrestlers ever. His ability to swing opponents around makes crowds go wild. After years of being overlooked in WWE as Cesaro, he joined AEW and the Blackpool Combat Club, finally getting main event opportunities.',
            },
            {
                'name': 'Chris Hero',
                'real_name': 'Christopher James Spradlin',
                'birth_date': '1979-11-26',
                'hometown': 'Dayton, Ohio',
                'nationality': 'American',
                'height': "6'5\"",
                'weight': '249 lbs',
                'debut_year': 2000,
                'finishers': 'Death Blow, Rolling Elbow',
                'signature_moves': 'Cravate, Roaring Elbow',
                'aliases': 'Kassius Ohno',
                'about': 'Chris Hero, as half of the Kings of Wrestling with Claudio Castagnoli, helped define indie wrestling. His striking and technical ability made him a favorite of hardcore fans. Hero has worked for WWE (as Kassius Ohno), ROH, PWG, and numerous promotions, always delivering.',
            },
            {
                'name': 'Roderick Strong',
                'real_name': 'Christopher Lindsey',
                'birth_date': '1983-05-07',
                'hometown': 'Tampa, Florida',
                'nationality': 'American',
                'height': "5'10\"",
                'weight': '200 lbs',
                'debut_year': 2000,
                'finishers': 'End of Heartache, Stronghold',
                'signature_moves': 'Backbreaker variations, Enzuigiri, Gibson Driver',
                'about': 'Roderick Strong has the best backbreaker in wrestling. His hard-hitting style made him an ROH legend before joining WWE. Part of Undisputed Era in NXT, Strong has won numerous tag team championships. Known for his intense workout regimen and strike combinations.',
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)

        self.stdout.write(f'  Updated {updated} British/Indie stars')
        return updated
