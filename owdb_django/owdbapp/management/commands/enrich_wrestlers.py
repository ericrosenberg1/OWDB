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
        if batch == 0 or batch == 11:
            total_updated += self.enrich_womens_pioneers()
        if batch == 0 or batch == 12:
            total_updated += self.enrich_tag_team_specialists()
        if batch == 0 or batch == 13:
            total_updated += self.enrich_managers_personalities()
        if batch == 0 or batch == 14:
            total_updated += self.enrich_cruiserweights()
        if batch == 0 or batch == 15:
            total_updated += self.enrich_hardcore_legends()
        if batch == 0 or batch == 16:
            total_updated += self.enrich_nxt_stars()
        if batch == 0 or batch == 17:
            total_updated += self.enrich_roh_legends()
        if batch == 0 or batch == 18:
            total_updated += self.enrich_classic_territorial()
        if batch == 0 or batch == 19:
            total_updated += self.enrich_modern_indie()
        if batch == 0 or batch == 20:
            total_updated += self.enrich_additional_wwe()
        if batch == 0 or batch == 21:
            total_updated += self.enrich_additional_aew()
        if batch == 0 or batch == 22:
            total_updated += self.enrich_additional_japan()
        if batch == 0 or batch == 23:
            total_updated += self.enrich_additional_mexico()
        if batch == 0 or batch == 24:
            total_updated += self.enrich_remaining_wrestlers()
        if batch == 0 or batch == 25:
            total_updated += self.enrich_more_legends()
        if batch == 0 or batch == 26:
            total_updated += self.enrich_more_modern()
        if batch == 0 or batch == 27:
            total_updated += self.enrich_80s_90s_stars()
        if batch == 0 or batch == 28:
            total_updated += self.enrich_modern_stars_2()
        if batch == 0 or batch == 29:
            total_updated += self.enrich_uso_bloodline()
        if batch == 0 or batch == 30:
            total_updated += self.enrich_managers_announcers()
        if batch == 0 or batch == 31:
            total_updated += self.enrich_tag_teams_factions()
        if batch == 0 or batch == 32:
            total_updated += self.enrich_more_wcw_ecw()
        if batch == 0 or batch == 33:
            total_updated += self.enrich_modern_wwe_2()
        if batch == 0 or batch == 34:
            total_updated += self.enrich_more_aew_2()
        if batch == 0 or batch == 35:
            total_updated += self.enrich_more_japan_2()
        if batch == 0 or batch == 36:
            total_updated += self.enrich_legends_2()
        if batch == 0 or batch == 37:
            total_updated += self.enrich_women_modern()

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

    def enrich_womens_pioneers(self):
        """Enrich women's wrestling pioneers."""
        self.stdout.write('--- Enriching Women\'s Pioneers ---')
        updated = 0
        wrestlers_data = [
            {'name': 'The Fabulous Moolah', 'real_name': 'Mary Lillian Ellison', 'birth_date': '1923-07-22', 'hometown': 'Columbia, South Carolina', 'nationality': 'American', 'debut_year': 1949, 'about': 'The Fabulous Moolah held the WWF Women\'s Championship for 28 years, the longest reign in wrestling history. She trained many female wrestlers and was a fixture in WWF/WWE for decades.'},
            {'name': 'Mae Young', 'real_name': 'Johnnie Mae Young', 'birth_date': '1923-03-12', 'hometown': 'Sand Springs, Oklahoma', 'nationality': 'American', 'debut_year': 1939, 'about': 'Mae Young was a pioneer who wrestled for over 70 years. Known for her toughness and humor, she remained active in WWE into her 80s.'},
            {'name': 'Wendi Richter', 'real_name': 'Wendi Richter', 'birth_date': '1961-09-06', 'hometown': 'Dallas, Texas', 'nationality': 'American', 'debut_year': 1979, 'about': 'Wendi Richter was central to the Rock \'n\' Wrestling Connection, winning the WWF Women\'s Championship with Cyndi Lauper in her corner.'},
            {'name': 'Alundra Blayze', 'real_name': 'Debra Miceli', 'birth_date': '1964-02-09', 'hometown': 'Tampa, Florida', 'nationality': 'American', 'aliases': 'Madusa', 'about': 'Alundra Blayze (Madusa) was WWF Women\'s Champion three times and brought athletic credibility to women\'s wrestling. WWE Hall of Famer.'},
            {'name': 'Jacqueline', 'real_name': 'Jacqueline Moore', 'birth_date': '1964-01-06', 'hometown': 'Dallas, Texas', 'nationality': 'American', 'about': 'Jacqueline was the first African American WWF Women\'s Champion and also held the Cruiserweight Championship.'},
            {'name': 'Ivory', 'real_name': 'Lisa Moretti', 'birth_date': '1961-11-26', 'hometown': 'Los Angeles, California', 'nationality': 'American', 'about': 'Ivory was a three-time WWF Women\'s Champion and memorable member of Right to Censor.'},
            {'name': 'Molly Holly', 'real_name': 'Nora Greenwald', 'birth_date': '1977-08-31', 'hometown': 'Forest Lake, Minnesota', 'nationality': 'American', 'finishers': 'Molly-Go-Round', 'about': 'Molly Holly was a two-time Women\'s Champion known for her exceptional technical wrestling ability.'},
            {'name': 'Jazz', 'real_name': 'Carlene Moore-Begnaud', 'birth_date': '1972-08-27', 'hometown': 'New Orleans, Louisiana', 'nationality': 'American', 'about': 'Jazz was a two-time WWE Women\'s Champion known for her aggressive, no-nonsense style.'},
            {'name': 'Victoria', 'real_name': 'Lisa Marie Varon', 'birth_date': '1971-02-10', 'hometown': 'San Bernardino, California', 'nationality': 'American', 'aliases': 'Tara', 'finishers': 'Widow\'s Peak', 'about': 'Victoria was a two-time WWE Women\'s Champion. She later had success in TNA as Tara.'},
            {'name': 'Gail Kim', 'real_name': 'Gail Kim-Irvine', 'birth_date': '1976-02-20', 'hometown': 'Toronto, Ontario', 'nationality': 'Canadian', 'finishers': 'Eat Defeat', 'about': 'Gail Kim won the WWE Women\'s Championship in her debut match and became the face of TNA\'s Knockouts Division.'},
            {'name': 'Mickie James', 'real_name': 'Mickie James-Aldis', 'birth_date': '1979-08-31', 'hometown': 'Montpelier, Virginia', 'nationality': 'American', 'finishers': 'Mick Kick', 'about': 'Mickie James is a six-time women\'s champion in WWE. Her obsessed fan storyline with Trish Stratus is legendary.'},
            {'name': 'Natalya', 'real_name': 'Natalie Neidhart-Wilson', 'birth_date': '1982-05-27', 'hometown': 'Calgary, Alberta', 'nationality': 'Canadian', 'finishers': 'Sharpshooter', 'about': 'Natalya is from the legendary Hart wrestling family, daughter of Jim Neidhart and niece of Bret Hart.'},
            {'name': 'Paige', 'real_name': 'Saraya-Jade Bevis', 'birth_date': '1992-08-17', 'hometown': 'Norwich, England', 'nationality': 'British', 'aliases': 'Saraya', 'about': 'Paige was the first NXT Women\'s Champion. Now wrestles as Saraya in AEW.'},
            {'name': 'AJ Lee', 'real_name': 'April Mendez Brooks', 'birth_date': '1987-03-19', 'hometown': 'Union City, New Jersey', 'nationality': 'American', 'finishers': 'Black Widow', 'about': 'AJ Lee was a three-time Divas Champion with the longest combined reign in history.'},
            {'name': 'Manami Toyota', 'real_name': 'Manami Toyota', 'birth_date': '1971-03-02', 'hometown': 'Matsudo, Japan', 'nationality': 'Japanese', 'about': 'Manami Toyota is widely considered the greatest female wrestler ever. Her innovative moves set the standard.'},
            {'name': 'Bull Nakano', 'real_name': 'Keiko Nakano', 'birth_date': '1968-01-08', 'hometown': 'Kawaguchi, Japan', 'nationality': 'Japanese', 'about': 'Bull Nakano was an iconic joshi wrestler who became WWF Women\'s Champion. WWE Hall of Famer.'},
            {'name': 'Akira Hokuto', 'real_name': 'Hisako Sasahara', 'birth_date': '1967-07-14', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Akira Hokuto is a joshi legend known for brutal matches and determination despite injuries.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Women\'s pioneers')
        return updated

    def enrich_tag_team_specialists(self):
        """Enrich tag team specialists."""
        self.stdout.write('--- Enriching Tag Team Specialists ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Arn Anderson', 'real_name': 'Martin Lunde', 'birth_date': '1958-09-20', 'hometown': 'Rome, Georgia', 'nationality': 'American', 'finishers': 'Spinebuster, DDT', 'about': 'Arn Anderson, The Enforcer, was one of the greatest tag wrestlers ever as part of the Four Horsemen and Brain Busters.'},
            {'name': 'Tully Blanchard', 'real_name': 'Tully Arthur Blanchard', 'birth_date': '1954-01-22', 'hometown': 'San Antonio, Texas', 'nationality': 'American', 'about': 'Tully Blanchard was a Four Horsemen member and half of the Brain Busters with Arn Anderson.'},
            {'name': 'Rick Rude', 'real_name': 'Richard Erwin Rood', 'birth_date': '1958-12-07', 'hometown': 'Robbinsdale, Minnesota', 'nationality': 'American', 'finishers': 'Rude Awakening', 'about': 'Ravishing Rick Rude was known for his physique, charisma, and in-ring ability. Intercontinental Champion and WCW US Champion.'},
            {'name': 'Hawk', 'real_name': 'Michael Hegstrand', 'birth_date': '1957-09-12', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'Hawk was half of the Legion of Doom/Road Warriors, the most dominant tag team in wrestling history.'},
            {'name': 'Animal', 'real_name': 'Joseph Laurinaitis', 'birth_date': '1960-09-12', 'hometown': 'Philadelphia, Pennsylvania', 'nationality': 'American', 'about': 'Animal was half of the Legion of Doom/Road Warriors. A power house who dominated tag team wrestling.'},
            {'name': 'Demolition Ax', 'real_name': 'Bill Eadie', 'birth_date': '1947-12-27', 'hometown': 'Brownsville, Pennsylvania', 'nationality': 'American', 'aliases': 'Ax', 'about': 'Ax was half of Demolition, three-time WWF Tag Team Champions with the longest combined reign.'},
            {'name': 'Demolition Smash', 'real_name': 'Barry Darsow', 'birth_date': '1959-10-06', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'aliases': 'Smash, Repo Man, Krusher Khruschev', 'about': 'Smash was half of Demolition and later became Repo Man. Three-time WWF Tag Team Champion.'},
            {'name': 'Jim Neidhart', 'real_name': 'James Henry Neidhart', 'birth_date': '1955-02-08', 'hometown': 'Tampa, Florida', 'nationality': 'American', 'about': 'Jim "The Anvil" Neidhart was half of the Hart Foundation with Bret Hart. Two-time WWF Tag Team Champion.'},
            {'name': 'Marty Jannetty', 'real_name': 'Marty Jannetty', 'birth_date': '1960-02-03', 'hometown': 'Columbus, Georgia', 'nationality': 'American', 'about': 'Marty Jannetty was half of the Rockers with Shawn Michaels. Their innovative high-flying style influenced tag wrestling.'},
            {'name': 'Rick Steiner', 'real_name': 'Robert Rechsteiner', 'birth_date': '1961-03-09', 'hometown': 'Bay City, Michigan', 'nationality': 'American', 'finishers': 'Steiner Bulldog', 'about': 'Rick Steiner was half of the Steiner Brothers, one of the greatest tag teams ever.'},
            {'name': 'Scott Steiner', 'real_name': 'Scott Carl Rechsteiner', 'birth_date': '1962-07-29', 'hometown': 'Bay City, Michigan', 'nationality': 'American', 'finishers': 'Frankensteiner, Steiner Recliner', 'about': 'Scott Steiner transformed from tag team star to Big Poppa Pump. WCW World Champion and legendary for his promos.'},
            {'name': 'Bully Ray', 'real_name': 'Mark LoMonaco', 'birth_date': '1971-07-14', 'hometown': 'New York City, New York', 'nationality': 'American', 'aliases': 'Bubba Ray Dudley', 'about': 'Bubba Ray Dudley was half of the Dudley Boyz, the most decorated tag team in history.'},
            {'name': 'D-Von Dudley', 'real_name': 'Devon Hughes', 'birth_date': '1972-08-01', 'hometown': 'New Rochelle, New York', 'nationality': 'American', 'about': 'D-Von Dudley was half of the Dudley Boyz. 23-time tag team champion across multiple promotions.'},
            {'name': 'Dax Harwood', 'real_name': 'Daniel Wheeler', 'birth_date': '1984-08-14', 'hometown': 'Mocksville, North Carolina', 'nationality': 'American', 'aliases': 'Dash Wilder', 'about': 'Dax Harwood is half of FTR, considered the best tag team in the world. Multiple time champions across WWE, AEW, and NJPW.'},
            {'name': 'Cash Wheeler', 'real_name': 'David Harwood', 'birth_date': '1987-06-26', 'hometown': 'Wilson, North Carolina', 'nationality': 'American', 'aliases': 'Scott Dawson', 'about': 'Cash Wheeler is half of FTR. Their old-school style has made them tag team champions worldwide.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Tag team specialists')
        return updated

    def enrich_managers_personalities(self):
        """Enrich managers and personalities."""
        self.stdout.write('--- Enriching Managers/Personalities ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Paul Bearer', 'real_name': 'William Moody', 'birth_date': '1954-04-10', 'hometown': 'Mobile, Alabama', 'nationality': 'American', 'about': 'Paul Bearer was the iconic manager of The Undertaker and Kane. His voice and urn became wrestling legends.'},
            {'name': 'Bobby Heenan', 'real_name': 'Raymond Heenan', 'birth_date': '1944-11-01', 'hometown': 'Chicago, Illinois', 'nationality': 'American', 'about': 'Bobby "The Brain" Heenan was the greatest manager and commentator in wrestling history. His wit was unmatched.'},
            {'name': 'Jimmy Hart', 'real_name': 'James Ray Hart', 'birth_date': '1944-01-01', 'hometown': 'Jackson, Mississippi', 'nationality': 'American', 'about': 'Jimmy "Mouth of the South" Hart managed over 40 wrestlers in his career. Known for his megaphone and colorful jackets.'},
            {'name': 'Mr. Fuji', 'real_name': 'Harry Fujiwara', 'birth_date': '1934-05-04', 'hometown': 'Honolulu, Hawaii', 'nationality': 'American', 'about': 'Mr. Fuji was a five-time WWF Tag Team Champion as a wrestler and later became a legendary devious manager.'},
            {'name': 'Sensational Sherri', 'real_name': 'Sherri Martel', 'birth_date': '1958-02-08', 'hometown': 'Birmingham, Alabama', 'nationality': 'American', 'about': 'Sensational Sherri was a WWF Women\'s Champion who became a legendary manager for Shawn Michaels and others.'},
            {'name': 'Miss Elizabeth', 'real_name': 'Elizabeth Hulette', 'birth_date': '1960-11-19', 'hometown': 'Frankfort, Kentucky', 'nationality': 'American', 'about': 'Miss Elizabeth was the beloved manager and wife of Randy Savage. Their love story defined 80s wrestling.'},
            {'name': 'Paul Ellering', 'real_name': 'Paul Ellering', 'birth_date': '1953-06-15', 'hometown': 'Melrose Park, Illinois', 'nationality': 'American', 'about': 'Paul Ellering managed the Road Warriors/Legion of Doom to tag team dominance across multiple promotions.'},
            {'name': 'Jim Cornette', 'real_name': 'James Mark Cornette', 'birth_date': '1961-09-17', 'hometown': 'Louisville, Kentucky', 'nationality': 'American', 'about': 'Jim Cornette managed the Midnight Express and became a legendary booker, podcaster, and wrestling historian.'},
            {'name': 'Paul Heyman', 'real_name': 'Paul Heyman', 'birth_date': '1965-09-11', 'hometown': 'Bronx, New York', 'nationality': 'American', 'about': 'Paul Heyman created ECW and became the greatest advocate in wrestling history, managing Brock Lesnar and Roman Reigns.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Managers/Personalities')
        return updated

    def enrich_cruiserweights(self):
        """Enrich cruiserweight wrestlers."""
        self.stdout.write('--- Enriching Cruiserweights ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Dean Malenko', 'real_name': 'Dean Simon', 'birth_date': '1960-08-04', 'hometown': 'Tampa, Florida', 'nationality': 'American', 'finishers': 'Texas Cloverleaf', 'about': 'Dean Malenko, the Man of 1000 Holds, was a four-time WCW Cruiserweight Champion known for his technical mastery.'},
            {'name': 'Juventud Guerrera', 'real_name': 'Juventud Guerrera', 'birth_date': '1974-10-22', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'finishers': 'Juvi Driver', 'about': 'Juventud Guerrera was a high-flying WCW Cruiserweight Champion known for incredible aerial moves.'},
            {'name': 'Psicosis', 'real_name': 'Dionicio Castellanos', 'birth_date': '1971-01-19', 'hometown': 'Tijuana, Mexico', 'nationality': 'Mexican', 'about': 'Psicosis was a masked luchador known for his high-flying style in WCW\'s cruiserweight division.'},
            {'name': 'Super Crazy', 'real_name': 'Francisco Islas Rueda', 'birth_date': '1973-07-11', 'hometown': 'Tulancingo, Mexico', 'nationality': 'Mexican', 'finishers': 'Moonsault', 'about': 'Super Crazy was an ECW and WCW star known for his insane moonsaults and fearless style.'},
            {'name': 'Tajiri', 'real_name': 'Yoshihiro Tajiri', 'birth_date': '1970-09-29', 'hometown': 'Tochigi, Japan', 'nationality': 'Japanese', 'finishers': 'Buzzsaw Kick, Tarantula', 'about': 'Tajiri brought Japanese strong style to ECW and WWE. His mist and kicks made him a fan favorite.'},
            {'name': 'Jamie Noble', 'real_name': 'James Gibson', 'birth_date': '1976-12-23', 'hometown': 'Hanover, West Virginia', 'nationality': 'American', 'about': 'Jamie Noble was a WWE Cruiserweight Champion and later a producer. Known for his trailer park character.'},
            {'name': 'Paul London', 'real_name': 'Paul London', 'birth_date': '1980-04-16', 'hometown': 'Austin, Texas', 'nationality': 'American', 'about': 'Paul London was a high-flying WWE Tag Team Champion with Brian Kendrick. Known for incredible aerial offense.'},
            {'name': 'Brian Kendrick', 'real_name': 'Brian Kendrick', 'birth_date': '1979-05-29', 'hometown': 'Fairfax, Virginia', 'nationality': 'American', 'finishers': 'Sliced Bread #2', 'about': 'Brian Kendrick was a WWE Tag Team and Cruiserweight Champion. Later became "The" Brian Kendrick.'},
            {'name': 'Ultimo Dragon', 'real_name': 'Yoshihiro Asai', 'birth_date': '1966-12-12', 'hometown': 'Aichi, Japan', 'nationality': 'Japanese', 'finishers': 'Asai Moonsault, Dragon Sleeper', 'about': 'Ultimo Dragon held 10 titles simultaneously and invented the Asai Moonsault. A true legend of cruiserweight wrestling.'},
            {'name': 'Jushin Thunder Liger', 'real_name': 'Keiichi Yamada', 'birth_date': '1964-11-30', 'hometown': 'Hiroshima, Japan', 'nationality': 'Japanese', 'finishers': 'Liger Bomb, Shooting Star Press', 'about': 'Jushin Thunder Liger is the greatest junior heavyweight ever. His 30+ year career defined the style. WWE Hall of Famer.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Cruiserweights')
        return updated

    def enrich_hardcore_legends(self):
        """Enrich hardcore legends."""
        self.stdout.write('--- Enriching Hardcore Legends ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Mick Foley', 'real_name': 'Michael Foley', 'birth_date': '1965-06-07', 'hometown': 'Long Island, New York', 'nationality': 'American', 'aliases': 'Cactus Jack, Mankind, Dude Love', 'finishers': 'Mandible Claw, Double Arm DDT', 'about': 'Mick Foley is the Hardcore Legend. As Cactus Jack, Mankind, and Dude Love, he defined extreme wrestling. His Hell in a Cell fall is iconic.'},
            {'name': 'Terry Funk', 'real_name': 'Terrence Funk', 'birth_date': '1944-06-30', 'hometown': 'Amarillo, Texas', 'nationality': 'American', 'finishers': 'Spinning Toe Hold', 'about': 'Terry Funk is a hardcore legend who wrestled across six decades. Former NWA World Champion who helped create ECW.'},
            {'name': 'Sandman', 'real_name': 'James Fullington', 'birth_date': '1963-06-16', 'hometown': 'Philadelphia, Pennsylvania', 'nationality': 'American', 'about': 'The Sandman was the beer-drinking, cane-swinging heart of ECW. His entrance through the crowd became legendary.'},
            {'name': 'New Jack', 'real_name': 'Jerome Young', 'birth_date': '1963-01-03', 'hometown': 'Greensboro, North Carolina', 'nationality': 'American', 'about': 'New Jack was the most controversial figure in ECW. His matches were violent spectacles set to "Natural Born Killaz."'},
            {'name': 'Balls Mahoney', 'real_name': 'Jonathan Rechner', 'birth_date': '1972-08-22', 'hometown': 'Nutley, New Jersey', 'nationality': 'American', 'about': 'Balls Mahoney was an ECW legend known for his chair shots and fan connection.'},
            {'name': 'Axl Rotten', 'real_name': 'Brian Knighton', 'birth_date': '1971-02-05', 'hometown': 'Baltimore, Maryland', 'nationality': 'American', 'about': 'Axl Rotten was a hardcore specialist in ECW, often teaming with Balls Mahoney.'},
            {'name': 'Tommy Dreamer', 'real_name': 'Thomas Laughlin', 'birth_date': '1971-02-14', 'hometown': 'Yonkers, New York', 'nationality': 'American', 'finishers': 'Dreamer DDT, Dreamer Driver', 'about': 'Tommy Dreamer was the heart and soul of ECW. He bled for the company and never stopped fighting.'},
            {'name': 'Raven', 'real_name': 'Scott Levy', 'birth_date': '1964-09-08', 'hometown': 'Philadelphia, Pennsylvania', 'nationality': 'American', 'finishers': 'Evenflow DDT', 'about': 'Raven was the philosophical anti-hero of ECW. His feud with Tommy Dreamer is legendary. Also successful in WCW and WWE.'},
            {'name': 'Al Snow', 'real_name': 'Allen Sarven', 'birth_date': '1963-07-18', 'hometown': 'Lima, Ohio', 'nationality': 'American', 'about': 'Al Snow found fame in ECW and WWE with his mannequin head "Head." Former Hardcore and Tag Team Champion.'},
            {'name': 'Hardcore Holly', 'real_name': 'Robert Howard', 'birth_date': '1963-01-29', 'hometown': 'Mobile, Alabama', 'nationality': 'American', 'finishers': 'Alabama Slam', 'about': 'Hardcore Holly was a tough-as-nails competitor. Six-time Hardcore Champion known for his stiff style.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Hardcore legends')
        return updated

    def enrich_nxt_stars(self):
        """Enrich NXT stars."""
        self.stdout.write('--- Enriching NXT Stars ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Adam Cole', 'real_name': 'Austin Jenkins', 'birth_date': '1989-07-05', 'hometown': 'Panama City, Florida', 'nationality': 'American', 'finishers': 'Panama Sunrise, Last Shot', 'about': 'Adam Cole was the longest-reigning NXT Champion in history. Leader of Undisputed Era before joining AEW.'},
            {'name': 'Johnny Gargano', 'real_name': 'John Gargano', 'birth_date': '1987-08-14', 'hometown': 'Cleveland, Ohio', 'nationality': 'American', 'finishers': 'One Final Beat, Gargano Escape', 'about': 'Johnny Gargano was NXT Champion and known for his epic feuds with Tommaso Ciampa. Johnny Wrestling is beloved by fans.'},
            {'name': 'Tommaso Ciampa', 'real_name': 'Tommaso Whitney', 'birth_date': '1985-05-08', 'hometown': 'Boston, Massachusetts', 'nationality': 'American', 'finishers': 'Fairy Tale Ending, Willow\'s Bell', 'about': 'Tommaso Ciampa was a two-time NXT Champion. His turn on Johnny Gargano is one of the greatest heel turns ever.'},
            {'name': 'Velveteen Dream', 'real_name': 'Patrick Clark Jr.', 'birth_date': '1995-08-28', 'hometown': 'Washington, D.C.', 'nationality': 'American', 'about': 'Velveteen Dream was an NXT North American Champion known for his flamboyant character inspired by Prince.'},
            {'name': 'Aleister Black', 'real_name': 'Tom Budgen', 'birth_date': '1985-05-19', 'hometown': 'Amsterdam, Netherlands', 'nationality': 'Dutch', 'aliases': 'Malakai Black', 'finishers': 'Black Mass', 'about': 'Aleister Black was NXT Champion with a dark mystical character. Now Malakai Black in AEW leading the House of Black.'},
            {'name': 'Ricochet', 'real_name': 'Trevor Mann', 'birth_date': '1988-10-11', 'hometown': 'Paducah, Kentucky', 'nationality': 'American', 'finishers': '630 Senton, Recoil', 'about': 'Ricochet is one of the greatest high-flyers ever. His athleticism is unmatched. NXT North American and WWE IC Champion.'},
            {'name': 'Keith Lee', 'real_name': 'Keith Lee', 'birth_date': '1984-11-08', 'hometown': 'Wichita Falls, Texas', 'nationality': 'American', 'finishers': 'Spirit Bomb, Big Bang Catastrophe', 'about': 'Keith Lee was NXT Champion and North American Champion simultaneously. His combination of size and agility is remarkable.'},
            {'name': 'Karrion Kross', 'real_name': 'Kevin Kesar', 'birth_date': '1985-07-19', 'hometown': 'New York City, New York', 'nationality': 'American', 'finishers': 'Kross Jacket', 'about': 'Karrion Kross was a two-time NXT Champion. His apocalyptic character with Scarlett was dominant.'},
            {'name': 'Io Shirai', 'real_name': 'Masami Odate', 'birth_date': '1990-05-26', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'aliases': 'Iyo Sky', 'finishers': 'Moonsault', 'about': 'Io Shirai was NXT Women\'s Champion and is considered the best female high-flyer ever. Now IYO SKY in WWE.'},
            {'name': 'Shayna Baszler', 'real_name': 'Shayna Baszler', 'birth_date': '1980-08-08', 'hometown': 'Sioux Falls, South Dakota', 'nationality': 'American', 'finishers': 'Kirifuda Clutch', 'about': 'Shayna Baszler was a two-time NXT Women\'s Champion. Former MMA fighter who dominated the division.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} NXT stars')
        return updated

    def enrich_roh_legends(self):
        """Enrich ROH legends."""
        self.stdout.write('--- Enriching ROH Legends ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Bryan Danielson', 'real_name': 'Bryan Danielson', 'birth_date': '1981-05-22', 'hometown': 'Aberdeen, Washington', 'nationality': 'American', 'aliases': 'Daniel Bryan', 'finishers': 'Cattle Mutilation, LeBell Lock, Busaiku Knee', 'about': 'Bryan Danielson is considered one of the greatest technical wrestlers ever. ROH Champion, WWE Champion, AEW Champion.'},
            {'name': 'Samoa Joe', 'real_name': 'Nuufolau Joel Seanoa', 'birth_date': '1979-03-17', 'hometown': 'Orange County, California', 'nationality': 'American', 'finishers': 'Muscle Buster, Coquina Clutch', 'about': 'Samoa Joe was ROH\'s first homegrown star. His trilogy with CM Punk is legendary. NXT, TNA, and ROH Champion.'},
            {'name': 'Austin Aries', 'real_name': 'Daniel Healy Solwold Jr.', 'birth_date': '1978-04-15', 'hometown': 'Milwaukee, Wisconsin', 'nationality': 'American', 'finishers': 'Brainbuster, Last Chancery', 'about': 'Austin Aries is a three-time ROH World Champion and TNA World Champion. The Greatest Man That Ever Lived.'},
            {'name': 'Tyler Black', 'real_name': 'Colby Lopez', 'birth_date': '1986-05-28', 'hometown': 'Davenport, Iowa', 'nationality': 'American', 'aliases': 'Seth Rollins', 'about': 'Tyler Black was ROH World Champion before becoming Seth Rollins in WWE. One of the greatest wrestlers of his generation.'},
            {'name': 'Davey Richards', 'real_name': 'Wesley Richards', 'birth_date': '1983-02-01', 'hometown': 'Othello, Washington', 'nationality': 'American', 'finishers': 'Damage Reflex, Ankle Lock', 'about': 'Davey Richards was ROH World Champion and half of the American Wolves. Known for his intense in-ring style.'},
            {'name': 'Eddie Edwards', 'real_name': 'Edward Edwards', 'birth_date': '1983-12-30', 'hometown': 'Boston, Massachusetts', 'nationality': 'American', 'finishers': 'Die Hard Driver', 'about': 'Eddie Edwards was ROH World Champion and TNA World Champion. One half of the American Wolves.'},
            {'name': 'Jay Lethal', 'real_name': 'Jamar Shipman', 'birth_date': '1985-04-29', 'hometown': 'Elizabeth, New Jersey', 'nationality': 'American', 'finishers': 'Lethal Injection, Lethal Combination', 'about': 'Jay Lethal is a two-time ROH World Champion. His Black Machismo and Ric Flair impressions made him a star.'},
            {'name': 'Low Ki', 'real_name': 'Brandon Silvestry', 'birth_date': '1979-12-21', 'hometown': 'Brooklyn, New York', 'nationality': 'American', 'finishers': 'Ki Krusher, Warrior\'s Way', 'about': 'Low Ki was the first ROH Champion. His stiff striking style and intensity set the tone for the promotion.'},
            {'name': 'Christopher Daniels', 'real_name': 'Daniel Covell', 'birth_date': '1970-03-24', 'hometown': 'Kalamazoo, Michigan', 'nationality': 'American', 'finishers': 'Angel\'s Wings, Best Moonsault Ever', 'about': 'Christopher Daniels was the first ROH Triple Crown winner. The Fallen Angel competed at the highest level for decades.'},
            {'name': 'Alex Shelley', 'real_name': 'Patrick Martin', 'birth_date': '1983-05-23', 'hometown': 'Detroit, Michigan', 'nationality': 'American', 'about': 'Alex Shelley is half of the Motor City Machine Guns. One of the most innovative wrestlers of his generation.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} ROH legends')
        return updated

    def enrich_classic_territorial(self):
        """Enrich classic territorial era wrestlers."""
        self.stdout.write('--- Enriching Classic Territorial Era ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Harley Race', 'real_name': 'Harley Leland Race', 'birth_date': '1943-04-11', 'hometown': 'Quitman, Missouri', 'nationality': 'American', 'finishers': 'Diving Headbutt', 'about': 'Harley Race was an eight-time NWA World Champion. The King of Wrestling was tough and respected worldwide.'},
            {'name': 'Jack Brisco', 'real_name': 'Jack Brisco', 'birth_date': '1941-09-21', 'hometown': 'Blackwell, Oklahoma', 'nationality': 'American', 'finishers': 'Figure Four Leglock', 'about': 'Jack Brisco was a two-time NWA World Champion and NCAA wrestling champion. One of the greatest scientific wrestlers.'},
            {'name': 'Dory Funk Jr.', 'real_name': 'Dorrance Funk Jr.', 'birth_date': '1941-02-03', 'hometown': 'Amarillo, Texas', 'nationality': 'American', 'finishers': 'Spinning Toe Hold', 'about': 'Dory Funk Jr. was NWA World Champion for over four years. His technical style influenced generations.'},
            {'name': 'Lou Thesz', 'real_name': 'Aloysius Martin Thesz', 'birth_date': '1916-04-24', 'hometown': 'Banat, Michigan', 'nationality': 'American', 'finishers': 'Thesz Press, STF', 'about': 'Lou Thesz was the greatest champion of the territorial era. His six NWA World Championships spanned decades.'},
            {'name': 'Verne Gagne', 'real_name': 'LaVerne Clarence Gagne', 'birth_date': '1926-02-26', 'hometown': 'Corcoran, Minnesota', 'nationality': 'American', 'finishers': 'Sleeper Hold', 'about': 'Verne Gagne was a 10-time AWA World Champion and built the AWA into a major territory. Olympic-caliber athlete.'},
            {'name': 'Nick Bockwinkel', 'real_name': 'Nicholas Warren Francis Bockwinkel', 'birth_date': '1934-12-06', 'hometown': 'St. Louis, Missouri', 'nationality': 'American', 'about': 'Nick Bockwinkel was a four-time AWA World Champion. His sophisticated heel character was years ahead of its time.'},
            {'name': 'Fritz Von Erich', 'real_name': 'Jack Barton Adkisson', 'birth_date': '1929-08-16', 'hometown': 'Jewett, Texas', 'nationality': 'American', 'finishers': 'Iron Claw', 'about': 'Fritz Von Erich was a legend who built WCCW. His Iron Claw was feared. Father of the Von Erich wrestling dynasty.'},
            {'name': 'Kerry Von Erich', 'real_name': 'Kerry Gene Adkisson', 'birth_date': '1960-02-03', 'hometown': 'Niagara Falls, New York', 'nationality': 'American', 'aliases': 'Texas Tornado', 'finishers': 'Iron Claw, Tornado Punch', 'about': 'Kerry Von Erich was NWA World Champion and WWF IC Champion. The Modern Day Warrior overcame tragedy to become a star.'},
            {'name': 'Kevin Von Erich', 'real_name': 'Kevin Ross Adkisson', 'birth_date': '1957-05-15', 'hometown': 'Dallas, Texas', 'nationality': 'American', 'finishers': 'Iron Claw', 'about': 'Kevin Von Erich was a WCCW legend and the only surviving Von Erich brother. WWE Hall of Famer.'},
            {'name': 'Bruiser Brody', 'real_name': 'Frank Goodish', 'birth_date': '1946-06-18', 'hometown': 'Detroit, Michigan', 'nationality': 'American', 'finishers': 'King Kong Knee Drop', 'about': 'Bruiser Brody was a wild, uncontrollable force. His brawling style influenced hardcore wrestling. A legend in Japan.'},
            {'name': 'Stan Hansen', 'real_name': 'John Stanley Hansen II', 'birth_date': '1949-08-29', 'hometown': 'Borger, Texas', 'nationality': 'American', 'finishers': 'Western Lariat', 'about': 'Stan Hansen was a legend in Japan and America. His stiff Lariat and wild style made him an icon. WWE Hall of Famer.'},
            {'name': 'Killer Kowalski', 'real_name': 'Władek Kowalski', 'birth_date': '1926-10-13', 'hometown': 'Windsor, Ontario', 'nationality': 'Canadian', 'about': 'Killer Kowalski was one of the original monster heels. Later trained Triple H and Chyna. WWE Hall of Famer.'},
            {'name': 'Bruno Sammartino', 'real_name': 'Bruno Leopoldo Francesco Sammartino', 'birth_date': '1935-10-06', 'hometown': 'Pizzoferrato, Italy', 'nationality': 'Italian-American', 'finishers': 'Bearhug', 'about': 'Bruno Sammartino held the WWWF Championship for 11 combined years. The Living Legend sold out Madison Square Garden over 180 times.'},
            {'name': 'Pedro Morales', 'real_name': 'Pedro Morales', 'birth_date': '1942-10-22', 'hometown': 'Culebra, Puerto Rico', 'nationality': 'Puerto Rican', 'about': 'Pedro Morales was WWWF Champion and the first Triple Crown winner. A hero to Latino fans.'},
            {'name': 'Bob Backlund', 'real_name': 'Robert Louis Backlund', 'birth_date': '1949-08-14', 'hometown': 'Princeton, Minnesota', 'nationality': 'American', 'finishers': 'Crossface Chickenwing', 'about': 'Bob Backlund was WWF Champion for nearly six years. His amateur background made him a technical master. Two-time champion.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Classic territorial wrestlers')
        return updated

    def enrich_modern_indie(self):
        """Enrich modern indie stars."""
        self.stdout.write('--- Enriching Modern Indie Stars ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Bandido', 'real_name': 'Carlos Romo', 'birth_date': '1994-12-16', 'hometown': 'Torreon, Mexico', 'nationality': 'Mexican', 'finishers': '21 Plex', 'about': 'Bandido is a lucha libre sensation. His incredible athleticism made him ROH World Champion and indie star.'},
            {'name': 'Jonathan Gresham', 'real_name': 'Jonathan Gresham', 'birth_date': '1988-10-28', 'hometown': 'Atlanta, Georgia', 'nationality': 'American', 'finishers': 'Octopus Hold', 'about': 'Jonathan Gresham was ROH World Champion. The Octopus is known for his technical mastery and unique style.'},
            {'name': 'Trent Seven', 'real_name': 'Benjamin Webb', 'birth_date': '1981-11-12', 'hometown': 'Wolverhampton, England', 'nationality': 'British', 'about': 'Trent Seven was NXT UK Tag Team Champion as half of Moustache Mountain. A key figure in British wrestling.'},
            {'name': 'Mark Andrews', 'real_name': 'Mark Andrews', 'birth_date': '1992-04-17', 'hometown': 'Cardiff, Wales', 'nationality': 'Welsh', 'finishers': 'Stundog Millionaire', 'about': 'Mark Andrews was NXT UK Tag Team Champion. High-flying Welsh star who competed worldwide.'},
            {'name': 'Toni Storm', 'real_name': 'Toni Rossall', 'birth_date': '1995-10-19', 'hometown': 'Gold Coast, Australia', 'nationality': 'Australian', 'finishers': 'Storm Zero', 'about': 'Toni Storm was NXT UK Women\'s Champion and AEW Women\'s Champion. One of the best female wrestlers worldwide.'},
            {'name': 'Kota Ibushi', 'real_name': 'Kota Ibushi', 'birth_date': '1982-05-21', 'hometown': 'Amagasaki, Japan', 'nationality': 'Japanese', 'finishers': 'Kamigoye, Phoenix Splash', 'about': 'Kota Ibushi is known for his breathtaking athleticism and willingness to take risks. IWGP Heavyweight Champion.'},
            {'name': 'Zack Sabre Jr.', 'real_name': 'Zack Sherwin Mayall', 'birth_date': '1987-07-24', 'hometown': 'Sheerness, England', 'nationality': 'British', 'finishers': 'Zack Driver, Various Submissions', 'about': 'Zack Sabre Jr. is the best technical wrestler of his generation. His submission game is unmatched. NJPW and IWGP Champion.'},
            {'name': 'WALTER', 'real_name': 'Walter Hahn', 'birth_date': '1987-08-10', 'hometown': 'Vienna, Austria', 'nationality': 'Austrian', 'aliases': 'Gunther', 'finishers': 'Powerbomb, Chops', 'about': 'WALTER had the longest NXT UK Championship reign at 870 days. Now Gunther in WWE with IC Championship dominance.'},
            {'name': 'Killer Kross', 'real_name': 'Kevin Kesar', 'birth_date': '1985-07-19', 'hometown': 'Las Vegas, Nevada', 'nationality': 'American', 'aliases': 'Karrion Kross', 'about': 'Killer Kross was a two-time NXT Champion. His apocalyptic persona made him a dominant champion.'},
            {'name': 'Penta El Zero M', 'real_name': 'Unknown', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'aliases': 'Pentagon Jr, Pentagon Dark', 'finishers': 'Fear Factor, Package Piledriver', 'about': 'Pentagon Jr is one of the most popular luchadors of his generation. His Cero Miedo persona made him a worldwide star.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Modern indie stars')
        return updated

    def enrich_additional_wwe(self):
        """Enrich additional WWE wrestlers."""
        self.stdout.write('--- Enriching Additional WWE ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Sheamus', 'real_name': 'Stephen Farrelly', 'birth_date': '1978-01-28', 'hometown': 'Dublin, Ireland', 'nationality': 'Irish', 'finishers': 'Brogue Kick, White Noise', 'about': 'Sheamus is a four-time WWE Champion and first Irish-born world champion. The Celtic Warrior is known for his bruising style.'},
            {'name': 'Drew McIntyre', 'real_name': 'Andrew Galloway IV', 'birth_date': '1985-06-06', 'hometown': 'Ayr, Scotland', 'nationality': 'Scottish', 'finishers': 'Claymore Kick, Future Shock DDT', 'about': 'Drew McIntyre is a two-time WWE Champion. He won the title at WrestleMania 36. The Scottish Warrior is a fighting champion.'},
            {'name': 'Kofi Kingston', 'real_name': 'Kofi Sarkodie-Mensah', 'birth_date': '1981-08-14', 'hometown': 'Ghana', 'nationality': 'Ghanaian-American', 'finishers': 'Trouble in Paradise', 'about': 'Kofi Kingston is a WWE Champion and member of The New Day. KofiMania was a legendary WrestleMania moment.'},
            {'name': 'Big E', 'real_name': 'Ettore Ewen', 'birth_date': '1986-03-01', 'hometown': 'Tampa, Florida', 'nationality': 'American', 'finishers': 'Big Ending', 'about': 'Big E is a WWE Champion and member of The New Day. His charisma and power make him a unique star.'},
            {'name': 'Xavier Woods', 'real_name': 'Austin Watson', 'birth_date': '1986-09-04', 'hometown': 'Columbus, Georgia', 'nationality': 'American', 'finishers': 'Lost in the Woods', 'about': 'Xavier Woods is the mastermind behind The New Day and King of the Ring winner. Also hosts UpUpDownDown gaming channel.'},
            {'name': 'The Miz', 'real_name': 'Michael Mizanin', 'birth_date': '1980-10-08', 'hometown': 'Cleveland, Ohio', 'nationality': 'American', 'finishers': 'Skull Crushing Finale', 'about': 'The Miz is a two-time WWE Champion and reality TV star from The Real World. His heel work is exceptional.'},
            {'name': 'Dolph Ziggler', 'real_name': 'Nicholas Nemeth', 'birth_date': '1980-07-27', 'hometown': 'Cleveland, Ohio', 'nationality': 'American', 'finishers': 'Zig Zag, Superkick', 'about': 'Dolph Ziggler is a two-time World Heavyweight Champion known for his incredible selling and bumping.'},
            {'name': 'Rusev', 'real_name': 'Miroslav Barnyashev', 'birth_date': '1985-12-25', 'hometown': 'Plovdiv, Bulgaria', 'nationality': 'Bulgarian', 'aliases': 'Miro', 'finishers': 'Accolade, Machka Kick', 'about': 'Rusev was WWE US Champion and beloved by fans for Rusev Day. Now Miro in AEW, the Redeemer.'},
            {'name': 'Cesaro', 'real_name': 'Claudio Castagnoli', 'birth_date': '1980-12-27', 'hometown': 'Lucerne, Switzerland', 'nationality': 'Swiss', 'finishers': 'Neutralizer, Giant Swing', 'about': 'Cesaro was US Champion and tag champion in WWE. His strength is legendary. Now Claudio Castagnoli in AEW.'},
            {'name': 'Alberto Del Rio', 'real_name': 'José Alberto Rodríguez', 'birth_date': '1977-05-25', 'hometown': 'San Luis Potosí, Mexico', 'nationality': 'Mexican', 'finishers': 'Cross Armbreaker', 'about': 'Alberto Del Rio is a two-time WWE Champion and Royal Rumble winner. Represented Mexican aristocracy.'},
            {'name': 'R-Truth', 'real_name': 'Ronnie Killings', 'birth_date': '1972-01-19', 'hometown': 'Charlotte, North Carolina', 'nationality': 'American', 'about': 'R-Truth is a 54-time 24/7 Champion and beloved comedy character. His in-ring ability is often underrated.'},
            {'name': 'Booker T', 'real_name': 'Robert Booker Tio Huffman', 'birth_date': '1965-03-01', 'hometown': 'Houston, Texas', 'nationality': 'American', 'finishers': 'Scissor Kick, Spinaroonie', 'about': 'Booker T is a five-time WCW Champion and WWE Hall of Famer. Can you dig it, sucka?'},
            {'name': 'Mark Henry', 'real_name': 'Mark Henry', 'birth_date': '1971-06-12', 'hometown': 'Silsbee, Texas', 'nationality': 'American', 'finishers': 'World\'s Strongest Slam', 'about': 'Mark Henry is the World\'s Strongest Man and World Heavyweight Champion. Olympic weightlifter turned wrestler.'},
            {'name': 'JBL', 'real_name': 'John Charles Layfield', 'birth_date': '1966-11-29', 'hometown': 'Sweetwater, Texas', 'nationality': 'American', 'finishers': 'Clothesline from Hell', 'about': 'JBL was a dominant WWE Champion with a 280-day reign. Former APA member and successful commentator.'},
            {'name': 'MVP', 'real_name': 'Alvin Burke Jr.', 'birth_date': '1973-10-28', 'hometown': 'Miami, Florida', 'nationality': 'American', 'finishers': 'Playmaker', 'about': 'MVP was US Champion with the longest reign ever. His unique character and ability made him a standout.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Additional WWE wrestlers')
        return updated

    def enrich_additional_aew(self):
        """Enrich additional AEW wrestlers."""
        self.stdout.write('--- Enriching Additional AEW ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Jungle Boy', 'real_name': 'Jack Perry', 'birth_date': '1997-03-15', 'hometown': 'Los Angeles, California', 'nationality': 'American', 'finishers': 'Snare Trap', 'about': 'Jungle Boy is a fan favorite and son of Luke Perry. His athleticism and heart make him a future star.'},
            {'name': 'Luchasaurus', 'real_name': 'Austin Matelson', 'birth_date': '1984-08-07', 'hometown': 'Los Angeles, California', 'nationality': 'American', 'finishers': 'Tail Whip', 'about': 'Luchasaurus is a 65 million year old dinosaur who does impressive high-flying moves despite his size.'},
            {'name': 'Dustin Rhodes', 'real_name': 'Dustin Patrick Runnels', 'birth_date': '1969-04-11', 'hometown': 'Austin, Texas', 'nationality': 'American', 'aliases': 'Goldust', 'finishers': 'Cross Rhodes', 'about': 'Dustin Rhodes is a legend who revitalized his career in AEW. His match with Cody at Double or Nothing 2019 was emotional.'},
            {'name': 'Scorpio Sky', 'real_name': 'Schuyler Andrews', 'birth_date': '1983-03-29', 'hometown': 'Inglewood, California', 'nationality': 'American', 'about': 'Scorpio Sky was an original AEW Tag Team Champion with SCU. TNT Champion and consistent performer.'},
            {'name': 'Frankie Kazarian', 'real_name': 'Frank Gerdelman', 'birth_date': '1977-11-12', 'hometown': 'Anaheim, California', 'nationality': 'American', 'finishers': 'Flux Capacitor', 'about': 'Frankie Kazarian is a veteran of TNA and AEW. Part of SCU and multiple time tag team champion.'},
            {'name': 'Shawn Spears', 'real_name': 'Ronald Spears', 'birth_date': '1981-02-15', 'hometown': 'Niagara Falls, Ontario', 'nationality': 'Canadian', 'aliases': 'Tye Dillinger', 'about': 'Shawn Spears is the Perfect 10 who reinvented himself in AEW with a darker persona.'},
            {'name': 'Wardlow', 'real_name': 'Michael Wardlow', 'birth_date': '1988-07-09', 'hometown': 'Cleveland, Ohio', 'nationality': 'American', 'finishers': 'Powerbomb Symphony', 'about': 'Wardlow is a powerhouse who broke free from MJF to become TNT Champion. His powerbombs are devastating.'},
            {'name': 'Powerhouse Hobbs', 'real_name': 'William Hobbs', 'birth_date': '1991-11-26', 'hometown': 'Modesto, California', 'nationality': 'American', 'finishers': 'Town Business', 'about': 'Powerhouse Hobbs is a rising star with incredible strength and potential.'},
            {'name': 'Ricky Starks', 'real_name': 'Ricky Starks', 'birth_date': '1990-04-05', 'hometown': 'New Orleans, Louisiana', 'nationality': 'American', 'finishers': 'Rochambeau', 'about': 'Ricky Starks is Absolute and has incredible charisma. His star is rising in AEW.'},
            {'name': 'Brian Cage', 'real_name': 'Brian Button', 'birth_date': '1984-11-04', 'hometown': 'Hacienda Heights, California', 'nationality': 'American', 'finishers': 'Drill Claw', 'about': 'Brian Cage is The Machine with an incredible physique and Lucha Underground championship pedigree.'},
            {'name': 'Lance Archer', 'real_name': 'Lance Hoyt', 'birth_date': '1977-09-12', 'hometown': 'Dallas, Texas', 'nationality': 'American', 'finishers': 'Blackout', 'about': 'Lance Archer became a star in NJPW as the Murderhawk Monster before joining AEW. Everybody dies!'},
            {'name': 'Jake Hager', 'real_name': 'Jacob Hager Jr.', 'birth_date': '1982-03-24', 'hometown': 'Perry, Oklahoma', 'nationality': 'American', 'aliases': 'Jack Swagger', 'finishers': 'Hager Bomb, Ankle Lock', 'about': 'Jake Hager is a former WWE Champion who joined AEW and Bellator MMA. Inner Circle member.'},
            {'name': 'Santana', 'real_name': 'Mike Draztik', 'birth_date': '1985-11-19', 'hometown': 'New York City, New York', 'nationality': 'American', 'about': 'Santana was half of Proud and Powerful and LAX. Inner Circle member with incredible charisma.'},
            {'name': 'Ortiz', 'real_name': 'Angel Ortiz', 'birth_date': '1984-07-04', 'hometown': 'New York City, New York', 'nationality': 'American', 'about': 'Ortiz was half of Proud and Powerful and LAX. His chemistry with Santana is undeniable.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Additional AEW wrestlers')
        return updated

    def enrich_additional_japan(self):
        """Enrich additional Japanese wrestlers."""
        self.stdout.write('--- Enriching Additional Japan ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Toru Yano', 'real_name': 'Toru Yano', 'birth_date': '1978-05-18', 'hometown': 'Arakawa, Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Toru Yano is NJPW\'s comedy genius who sells DVDs and wins with low blows. KOPW Champion.'},
            {'name': 'Hirooki Goto', 'real_name': 'Hirooki Goto', 'birth_date': '1979-06-25', 'hometown': 'Kuwana, Mie, Japan', 'nationality': 'Japanese', 'finishers': 'GTR', 'about': 'Hirooki Goto is a NEVER Openweight Champion known for his stoic warrior persona.'},
            {'name': 'Tomohiro Ishii', 'real_name': 'Tomohiro Ishii', 'birth_date': '1975-12-10', 'hometown': 'Sagamihara, Kanagawa, Japan', 'nationality': 'Japanese', 'finishers': 'Brainbuster', 'about': 'Tomohiro Ishii is the Stone Pitbull. His hard-hitting matches consistently deliver.'},
            {'name': 'SANADA', 'real_name': 'Seiya Sanada', 'birth_date': '1988-01-28', 'hometown': 'Niigata, Japan', 'nationality': 'Japanese', 'finishers': 'Skull End, Moonsault', 'about': 'SANADA is a charismatic star who became IWGP World Heavyweight Champion. Former LIJ member.'},
            {'name': 'EVIL', 'real_name': 'Takaaki Watanabe', 'birth_date': '1987-06-25', 'hometown': 'Kamakura, Kanagawa, Japan', 'nationality': 'Japanese', 'finishers': 'EVIL', 'about': 'EVIL is a former IWGP Heavyweight Champion who betrayed LIJ to join Bullet Club.'},
            {'name': 'Hiromu Takahashi', 'real_name': 'Hiromu Takahashi', 'birth_date': '1989-12-04', 'hometown': 'Hachioji, Tokyo, Japan', 'nationality': 'Japanese', 'finishers': 'Time Bomb', 'about': 'Hiromu Takahashi is a charismatic IWGP Junior Heavyweight Champion. His wild style and Daryl the cat make him beloved.'},
            {'name': 'Tetsuya Naito', 'real_name': 'Tetsuya Naito', 'birth_date': '1982-06-22', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'finishers': 'Destino', 'about': 'Tetsuya Naito is the leader of Los Ingobernables de Japon. Two-time IWGP Heavyweight and IC Champion simultaneously.'},
            {'name': 'Taichi', 'real_name': 'Taichi Ishikari', 'birth_date': '1980-03-19', 'hometown': 'Hokkaido, Japan', 'nationality': 'Japanese', 'finishers': 'Black Mephisto', 'about': 'Taichi is NJPW\'s crooning holy emperor. His entrance songs and pants-ripping are legendary.'},
            {'name': 'Jeff Cobb', 'real_name': 'Jeffrey Cobb', 'birth_date': '1982-08-12', 'hometown': 'Honolulu, Hawaii', 'nationality': 'American', 'finishers': 'Tour of the Islands', 'about': 'Jeff Cobb is an Olympic wrestler who became a powerhouse in NJPW. His suplexes are incredible.'},
            {'name': 'Great-O-Khan', 'real_name': 'Tomoyuki Oka', 'birth_date': '1991-02-04', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'finishers': 'Eliminator', 'about': 'Great-O-Khan is the Dominator of United Empire. His Mongolian-inspired character is unique.'},
            {'name': 'Shingo Takagi', 'real_name': 'Shingo Takagi', 'birth_date': '1982-11-21', 'hometown': 'Nagano, Japan', 'nationality': 'Japanese', 'finishers': 'Last of the Dragon', 'about': 'Shingo Takagi is a former IWGP World Heavyweight Champion. The Dragon from Dragon Gate proved himself at the top.'},
            {'name': 'El Desperado', 'real_name': 'Unknown', 'hometown': 'Unknown', 'nationality': 'Japanese', 'finishers': 'Pinche Loco', 'about': 'El Desperado is a NJPW Junior Heavyweight Champion. His masked lucha style makes him a standout.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Additional Japanese wrestlers')
        return updated

    def enrich_additional_mexico(self):
        """Enrich additional Mexican wrestlers."""
        self.stdout.write('--- Enriching Additional Mexico ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Rush', 'real_name': 'Alberto Escamilla', 'birth_date': '1988-06-25', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'finishers': 'Rush\'s Driver', 'about': 'Rush is a CMLL legend and ROH Champion. The bull of CMLL brings intensity to every match.'},
            {'name': 'Dragon Lee', 'real_name': 'William Lee', 'birth_date': '1995-12-28', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'finishers': 'Desnucadora', 'about': 'Dragon Lee is a CMLL World Lightweight Champion who has competed worldwide. Incredible high-flyer.'},
            {'name': 'Andrade', 'real_name': 'Manuel Oropeza', 'birth_date': '1989-11-03', 'hometown': 'Gomez Palacio, Mexico', 'nationality': 'Mexican', 'aliases': 'La Sombra, Andrade Cien Almas', 'finishers': 'Hammerlock DDT', 'about': 'Andrade is a former NXT Champion and Mexican star. His combination of power and lucha is unique.'},
            {'name': 'Caristico', 'real_name': 'Luis Urive', 'birth_date': '1982-12-22', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'aliases': 'Mistico', 'finishers': 'La Mistica', 'about': 'Caristico as Mistico was the biggest star in CMLL history. His high-flying revolutionized lucha libre.'},
            {'name': 'Volador Jr.', 'real_name': 'Ramir Alejandro', 'birth_date': '1979-03-31', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'about': 'Volador Jr. is a CMLL World Heavyweight Champion. His high-flying style honors his father\'s legacy.'},
            {'name': 'Ultimo Guerrero', 'real_name': 'Benigno Ugalde', 'birth_date': '1971-11-24', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'finishers': 'Guerrero Special', 'about': 'Ultimo Guerrero is a CMLL legend and multi-time champion. The original Los Guerreros member.'},
            {'name': 'Negro Casas', 'real_name': 'Jose Casas', 'birth_date': '1960-02-05', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'about': 'Negro Casas is a legendary technician and part of the Casas wrestling family. CMLL icon for decades.'},
            {'name': 'Atlantis', 'real_name': 'Unknown', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'about': 'Atlantis is a CMLL legend and masked icon. His mask vs mask matches are historic.'},
            {'name': 'Blue Demon Jr.', 'real_name': 'Unknown', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'about': 'Blue Demon Jr. carries his father\'s legendary mask. A CMLL and AAA star who represents lucha royalty.'},
            {'name': 'Hijo del Fantasma', 'real_name': 'Jorge Solis', 'birth_date': '1980-10-13', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'aliases': 'Santos Escobar', 'about': 'Hijo del Fantasma became Santos Escobar in WWE NXT. Two-time NXT Cruiserweight Champion.'},
            {'name': 'Mascara Dorada', 'real_name': 'Urive Mendoza', 'birth_date': '1987-04-15', 'hometown': 'Guadalajara, Mexico', 'nationality': 'Mexican', 'aliases': 'Gran Metalik', 'about': 'Mascara Dorada competed as Gran Metalik in WWE. His aerial offense is incredible.'},
            {'name': 'LA Park', 'real_name': 'Adolfo Tapia', 'birth_date': '1965-03-13', 'hometown': 'Hermosillo, Mexico', 'nationality': 'Mexican', 'aliases': 'La Parka', 'about': 'LA Park was the original La Parka in WCW. His dancing skeleton character became iconic.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Additional Mexican wrestlers')
        return updated

    def enrich_remaining_wrestlers(self):
        """Enrich remaining notable wrestlers."""
        self.stdout.write('--- Enriching Remaining Wrestlers ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Cody Rhodes', 'real_name': 'Cody Garrett Runnels', 'birth_date': '1985-06-30', 'hometown': 'Marietta, Georgia', 'nationality': 'American', 'finishers': 'Cross Rhodes, Cody Cutter', 'about': 'Cody Rhodes finished the story at WrestleMania 40, becoming WWE Undisputed Champion. Son of Dusty Rhodes.'},
            {'name': 'Roman Reigns', 'real_name': 'Leati Joseph Anoa\'i', 'birth_date': '1985-05-25', 'hometown': 'Pensacola, Florida', 'nationality': 'American', 'finishers': 'Spear, Guillotine Choke', 'about': 'Roman Reigns is the Tribal Chief with the longest world title reign in modern history. Head of the Table.'},
            {'name': 'Seth Rollins', 'real_name': 'Colby Lopez', 'birth_date': '1986-05-28', 'hometown': 'Davenport, Iowa', 'nationality': 'American', 'finishers': 'Stomp, Pedigree', 'about': 'Seth Rollins is a multi-time world champion and visionary. From Shield member to main event star.'},
            {'name': 'Becky Lynch', 'real_name': 'Rebecca Quin', 'birth_date': '1987-01-30', 'hometown': 'Limerick, Ireland', 'nationality': 'Irish', 'finishers': 'Dis-arm-her', 'about': 'Becky Lynch is The Man. Her rise to the main event at WrestleMania 35 changed women\'s wrestling.'},
            {'name': 'Charlotte Flair', 'real_name': 'Ashley Fliehr', 'birth_date': '1986-04-05', 'hometown': 'Charlotte, North Carolina', 'nationality': 'American', 'finishers': 'Figure Eight, Natural Selection', 'about': 'Charlotte Flair is a 14-time women\'s champion, matching her father Ric. The Queen of WWE.'},
            {'name': 'Sasha Banks', 'real_name': 'Mercedes Varnado', 'birth_date': '1992-01-26', 'hometown': 'Boston, Massachusetts', 'nationality': 'American', 'aliases': 'Mercedes Mone', 'finishers': 'Bank Statement', 'about': 'Sasha Banks is The Boss and one of the Four Horsewomen. Now Mercedes Mone in NJPW and AEW.'},
            {'name': 'Bayley', 'real_name': 'Pamela Rose Martinez', 'birth_date': '1989-06-15', 'hometown': 'San Jose, California', 'nationality': 'American', 'finishers': 'Rose Plant', 'about': 'Bayley is a grand slam champion and leader of Damage CTRL. From hugger to role model.'},
            {'name': 'Asuka', 'real_name': 'Kanako Urai', 'birth_date': '1981-09-26', 'hometown': 'Osaka, Japan', 'nationality': 'Japanese', 'finishers': 'Asuka Lock', 'about': 'Asuka had an undefeated streak of 914 days in NXT. The Empress of Tomorrow is always ready.'},
            {'name': 'Bianca Belair', 'real_name': 'Bianca Crawford', 'birth_date': '1989-04-09', 'hometown': 'Knoxville, Tennessee', 'nationality': 'American', 'finishers': 'KOD', 'about': 'Bianca Belair is the EST of WWE. Her WrestleMania win over Sasha Banks was historic.'},
            {'name': 'Rhea Ripley', 'real_name': 'Demi Bennett', 'birth_date': '1996-10-11', 'hometown': 'Adelaide, Australia', 'nationality': 'Australian', 'finishers': 'Riptide', 'about': 'Rhea Ripley is Mami and Women\'s World Champion. The Nightmare emerged as a dominant force.'},
            {'name': 'Kenny Omega', 'real_name': 'Tyson Smith', 'birth_date': '1983-10-16', 'hometown': 'Winnipeg, Manitoba', 'nationality': 'Canadian', 'finishers': 'One Winged Angel, V-Trigger', 'about': 'Kenny Omega is the Best Bout Machine. His matches in NJPW and AEW are consistently legendary.'},
            {'name': 'Jon Moxley', 'real_name': 'Jonathan Good', 'birth_date': '1985-12-07', 'hometown': 'Cincinnati, Ohio', 'nationality': 'American', 'aliases': 'Dean Ambrose', 'finishers': 'Paradigm Shift, Bulldog Choke', 'about': 'Jon Moxley is a three-time AEW World Champion and deathmatch legend. From Shield to AEW main eventer.'},
            {'name': 'MJF', 'real_name': 'Maxwell Jacob Friedman', 'birth_date': '1996-03-15', 'hometown': 'Long Island, New York', 'nationality': 'American', 'finishers': 'Salt of the Earth, Heat Seeker', 'about': 'MJF is a two-time AEW World Champion. The salt of the earth is better than you and you know it.'},
            {'name': 'CM Punk', 'real_name': 'Phillip Brooks', 'birth_date': '1978-10-26', 'hometown': 'Chicago, Illinois', 'nationality': 'American', 'finishers': 'GTS, Anaconda Vise', 'about': 'CM Punk is the Voice of the Voiceless. His pipe bomb changed wrestling. Two-time WWE Champion.'},
            {'name': 'AJ Styles', 'real_name': 'Allen Jones', 'birth_date': '1977-06-02', 'hometown': 'Gainesville, Georgia', 'nationality': 'American', 'finishers': 'Styles Clash, Phenomenal Forearm', 'about': 'AJ Styles is the Phenomenal One. Two-time WWE Champion and one of the greatest ever.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Remaining wrestlers')
        return updated

    def enrich_more_legends(self):
        """Enrich more legendary wrestlers."""
        self.stdout.write('--- Enriching More Legends ---')
        updated = 0
        wrestlers_data = [
            {'name': '1-2-3 Kid', 'real_name': 'Sean Waltman', 'birth_date': '1972-07-13', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'aliases': 'X-Pac, Syxx', 'finishers': 'X-Factor, Bronco Buster', 'about': '1-2-3 Kid shocked the world by pinning Razor Ramon. As X-Pac became a founding DX member.'},
            {'name': '2 Cold Scorpio', 'real_name': 'Charles Scaggs', 'birth_date': '1966-11-25', 'hometown': 'Denver, Colorado', 'nationality': 'American', 'finishers': '450 Splash', 'about': '2 Cold Scorpio was ahead of his time with high-flying moves. ECW and WCW tag team champion.'},
            {'name': 'Abyss', 'real_name': 'Christopher Parks', 'birth_date': '1973-10-04', 'hometown': 'Washington, D.C.', 'nationality': 'American', 'finishers': 'Black Hole Slam', 'about': 'Abyss was TNA\'s monster, a multi-time NWA/TNA World Champion with a hardcore style.'},
            {'name': 'Adam Bomb', 'real_name': 'Bryan Clark', 'birth_date': '1964-08-03', 'hometown': 'Harrisburg, Pennsylvania', 'nationality': 'American', 'aliases': 'Wrath', 'about': 'Adam Bomb had a nuclear gimmick in WWF. Later became Wrath in WCW with a dominant streak.'},
            {'name': 'Adam Page', 'real_name': 'Stephen Woltz', 'birth_date': '1991-07-27', 'hometown': 'Halifax, Virginia', 'nationality': 'American', 'aliases': 'Hangman Adam Page', 'finishers': 'Buckshot Lariat, Deadeye', 'about': 'Hangman Adam Page was the fourth AEW World Champion. His anxiety storyline was groundbreaking.'},
            {'name': 'Adrian Adonis', 'real_name': 'Keith Franke', 'birth_date': '1953-09-15', 'hometown': 'Buffalo, New York', 'nationality': 'American', 'about': 'Adrian Adonis was a three-time WWF Tag Champion. His Adorable Adrian character was memorable.'},
            {'name': 'Ahmed Johnson', 'real_name': 'Tony Norris', 'birth_date': '1963-03-21', 'hometown': 'Pearl River, Louisiana', 'nationality': 'American', 'finishers': 'Pearl River Plunge', 'about': 'Ahmed Johnson was the first African American Intercontinental Champion in WWE history.'},
            {'name': 'Akira Taue', 'real_name': 'Akira Taue', 'birth_date': '1961-05-08', 'hometown': 'Chichibu, Saitama, Japan', 'nationality': 'Japanese', 'finishers': 'Ore ga Taue', 'about': 'Akira Taue was one of AJPW\'s Four Pillars of Heaven. Triple Crown Champion with epic matches.'},
            {'name': 'Akira Tozawa', 'real_name': 'Akira Tozawa', 'birth_date': '1985-07-22', 'hometown': 'Kobe, Japan', 'nationality': 'Japanese', 'finishers': 'Senton Bomb', 'about': 'Akira Tozawa is a former WWE Cruiserweight Champion known for his energetic style.'},
            {'name': 'Antonio Inoki', 'real_name': 'Kanji Inoki', 'birth_date': '1943-02-20', 'hometown': 'Yokohama, Japan', 'nationality': 'Japanese', 'finishers': 'Enzuigiri', 'about': 'Antonio Inoki founded NJPW and fought Muhammad Ali. A legendary pioneer of Japanese wrestling.'},
            {'name': 'Athena', 'real_name': 'Adrienne Reese', 'birth_date': '1991-01-07', 'hometown': 'Denton, Texas', 'nationality': 'American', 'aliases': 'Ember Moon', 'finishers': 'Eclipse', 'about': 'Athena was NXT Women\'s Champion as Ember Moon. Now ROH Women\'s Champion with a dominant reign.'},
            {'name': 'Austin Theory', 'real_name': 'Austin White', 'birth_date': '1997-08-02', 'hometown': 'Atlanta, Georgia', 'nationality': 'American', 'finishers': 'A-Town Down', 'about': 'Austin Theory is a young WWE star who cashed in MITB. United States Champion multiple times.'},
            {'name': 'Bad News Barrett', 'real_name': 'Stuart Bennett', 'birth_date': '1980-08-10', 'hometown': 'Preston, England', 'nationality': 'British', 'aliases': 'Wade Barrett', 'finishers': 'Bull Hammer Elbow', 'about': 'Bad News Barrett led Nexus and won the King of the Ring. I\'m afraid I\'ve got some bad news.'},
            {'name': 'Bad News Brown', 'real_name': 'Allen Coage', 'birth_date': '1943-09-05', 'hometown': 'New York City, New York', 'nationality': 'American', 'about': 'Bad News Brown was an Olympic judo bronze medalist who became a feared WWF heel.'},
            {'name': 'Baron Corbin', 'real_name': 'Thomas Pestock', 'birth_date': '1984-09-13', 'hometown': 'Kansas City, Kansas', 'nationality': 'American', 'finishers': 'End of Days', 'about': 'Baron Corbin is a former US Champion and King of the Ring. Former NFL player turned wrestler.'},
            {'name': 'Barry Windham', 'real_name': 'Barry Clinton Windham', 'birth_date': '1960-07-04', 'hometown': 'Sweetwater, Texas', 'nationality': 'American', 'finishers': 'Superplex', 'about': 'Barry Windham was a Four Horseman and NWA World Champion. His match with Ric Flair is legendary.'},
            {'name': 'Big Boss Man', 'real_name': 'Ray Traylor', 'birth_date': '1962-05-02', 'hometown': 'Cobb County, Georgia', 'nationality': 'American', 'finishers': 'Boss Man Slam', 'about': 'Big Boss Man was a prison guard character who became a WWF Tag Champion and Hardcore Champion.'},
            {'name': 'Big John Studd', 'real_name': 'John Minton', 'birth_date': '1948-02-19', 'hometown': 'Butler, Pennsylvania', 'nationality': 'American', 'about': 'Big John Studd was a giant who won the 1989 Royal Rumble. His feud with Andre is legendary.'},
            {'name': 'Big Show', 'real_name': 'Paul Wight', 'birth_date': '1972-02-08', 'hometown': 'Aiken, South Carolina', 'nationality': 'American', 'finishers': 'Chokeslam, WMD', 'about': 'Big Show is a seven-time world champion and the largest athlete in sports entertainment history.'},
            {'name': 'Big Van Vader', 'real_name': 'Leon White', 'birth_date': '1955-05-14', 'hometown': 'Lynwood, California', 'nationality': 'American', 'finishers': 'Vader Bomb, Vader Moonsault', 'about': 'Vader was a three-time WCW World Champion and IWGP Champion. It\'s time, it\'s Vader time!'},
            {'name': 'Billy Gunn', 'real_name': 'Monty Sopp', 'birth_date': '1963-11-01', 'hometown': 'Austin, Texas', 'nationality': 'American', 'finishers': 'Famouser', 'about': 'Billy Gunn was half of the New Age Outlaws and one of the most decorated tag team wrestlers ever.'},
            {'name': 'Blackjack Mulligan', 'real_name': 'Robert Windham', 'birth_date': '1942-11-25', 'hometown': 'Sweetwater, Texas', 'nationality': 'American', 'about': 'Blackjack Mulligan was a cowboy heel legend. Father of Barry Windham and Kendall Windham.'},
            {'name': 'Brian Pillman', 'real_name': 'Brian Pillman', 'birth_date': '1962-05-22', 'hometown': 'Cincinnati, Ohio', 'nationality': 'American', 'finishers': 'Air Pillman', 'about': 'Brian Pillman was the Loose Cannon. His innovative promos broke the fourth wall. Hollywood Blonds tag champion.'},
            {'name': 'Bronson Reed', 'real_name': 'Jermaine Haley', 'birth_date': '1988-03-04', 'hometown': 'Melbourne, Australia', 'nationality': 'Australian', 'finishers': 'Tsunami', 'about': 'Bronson Reed was NXT North American Champion. His size and agility make him a unique competitor.'},
            {'name': 'Brodie Lee', 'real_name': 'Jonathan Huber', 'birth_date': '1979-12-16', 'hometown': 'Rochester, New York', 'nationality': 'American', 'aliases': 'Luke Harper', 'finishers': 'Discus Lariat', 'about': 'Brodie Lee was the leader of the Dark Order in AEW and a beloved WWE star. Gone too soon. -1 is forever.'},
            {'name': 'Buddy Matthews', 'real_name': 'Matthew Adams', 'birth_date': '1989-01-16', 'hometown': 'Melbourne, Australia', 'nationality': 'Australian', 'aliases': 'Buddy Murphy', 'finishers': 'Murphy\'s Law', 'about': 'Buddy Matthews was WWE Cruiserweight Champion. Now part of House of Black in AEW.'},
            {'name': 'Buddy Rogers', 'real_name': 'Herman Rohde Jr.', 'birth_date': '1921-02-20', 'hometown': 'Camden, New Jersey', 'nationality': 'American', 'about': 'Buddy Rogers was the first WWWF Champion and the original Nature Boy. Ric Flair\'s inspiration.'},
            {'name': 'Captain Lou Albano', 'real_name': 'Louis Albano', 'birth_date': '1933-07-29', 'hometown': 'Mount Vernon, New York', 'nationality': 'American', 'about': 'Captain Lou Albano managed 15 WWF Tag Team Champions. WWE Hall of Famer and pop culture icon.'},
            {'name': 'Carlito', 'real_name': 'Carlos Colon Jr.', 'birth_date': '1979-01-21', 'hometown': 'San Juan, Puerto Rico', 'nationality': 'Puerto Rican', 'about': 'Carlito spits in the face of people who don\'t want to be cool. Two-time IC Champion from wrestling royalty.'},
            {'name': 'Brian Christopher', 'real_name': 'Brian Lawler', 'birth_date': '1972-01-10', 'hometown': 'Memphis, Tennessee', 'nationality': 'American', 'aliases': 'Grand Master Sexay', 'about': 'Brian Christopher was Too Much and Too Cool with Scotty 2 Hotty. Son of Jerry Lawler.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More legends')
        return updated

    def enrich_more_modern(self):
        """Enrich more modern wrestlers."""
        self.stdout.write('--- Enriching More Modern ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Anna Jay', 'real_name': 'Anna Jay', 'birth_date': '1998-08-15', 'hometown': 'Brunswick, Georgia', 'nationality': 'American', 'finishers': 'Queen Slayer', 'about': 'Anna Jay is the Star of the Show. Dark Order member and rising star in AEW.'},
            {'name': 'Anthony Bowens', 'real_name': 'Anthony Baber', 'birth_date': '1990-10-01', 'hometown': 'Nutley, New Jersey', 'nationality': 'American', 'about': 'Anthony Bowens is half of the Acclaimed. Everyone loves the Acclaimed! Scissor me, Daddy Ass!'},
            {'name': 'Bad Luck Fale', 'real_name': 'Sione Finau', 'birth_date': '1981-09-12', 'hometown': 'Tonga', 'nationality': 'Tongan', 'finishers': 'Bad Luck Fall', 'about': 'Bad Luck Fale is the Underboss of Bullet Club. A massive enforcer in NJPW.'},
            {'name': 'Bobby Fish', 'real_name': 'Robert Fish', 'birth_date': '1977-03-27', 'hometown': 'Albany, New York', 'nationality': 'American', 'finishers': 'Fish Hook', 'about': 'Bobby Fish was part of Undisputed Era in NXT. A martial arts-based wrestler with technical skill.'},
            {'name': 'Brandi Rhodes', 'real_name': 'Brandi Alexis Runnels', 'birth_date': '1983-06-23', 'hometown': 'Dearborn, Michigan', 'nationality': 'American', 'about': 'Brandi Rhodes was AEW Chief Brand Officer and in-ring performer.'},
            {'name': 'Angelina Love', 'real_name': 'Lauren Williams', 'birth_date': '1981-09-13', 'hometown': 'Toronto, Ontario', 'nationality': 'Canadian', 'about': 'Angelina Love was a six-time TNA Knockouts Champion. Part of the Beautiful People.'},
            {'name': 'Awesome Kong', 'real_name': 'Kia Stevens', 'birth_date': '1977-09-04', 'hometown': 'Carson, California', 'nationality': 'American', 'aliases': 'Kharma', 'finishers': 'Implant Buster', 'about': 'Awesome Kong was a dominant Knockouts Champion. Her matches with Gail Kim were legendary.'},
            {'name': 'Angelico', 'real_name': 'Michael Paris', 'birth_date': '1987-01-17', 'hometown': 'Johannesburg, South Africa', 'nationality': 'South African', 'about': 'Angelico is known for his high-flying and creative offense. Lucha Underground star.'},
            {'name': 'Ariya Daivari', 'real_name': 'Ariya Daivari', 'birth_date': '1989-08-28', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'Ariya Daivari was a 205 Live staple. His brother Shawn was also a WWE wrestler.'},
            {'name': 'BUSHI', 'real_name': 'Unknown', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'finishers': 'MX', 'about': 'BUSHI is a junior heavyweight member of Los Ingobernables de Japon. Known for his mist attack.'},
            {'name': 'Ben-K', 'real_name': 'Kenji Matsuda', 'birth_date': '1989-10-02', 'hometown': 'Osaka, Japan', 'nationality': 'Japanese', 'about': 'Ben-K is a Dragon Gate powerhouse. Open the Dream Gate Champion with incredible strength.'},
            {'name': 'CIMA', 'real_name': 'Nobuhiko Oshima', 'birth_date': '1977-03-22', 'hometown': 'Fukuoka, Japan', 'nationality': 'Japanese', 'about': 'CIMA is the founder of Dragon Gate. A legendary high-flyer who influenced generations.'},
            {'name': 'Blake Christian', 'real_name': 'Christian Hubble', 'birth_date': '1997-04-20', 'hometown': 'St. Louis, Missouri', 'nationality': 'American', 'about': 'Blake Christian is a high-flying indie star who has competed in NJPW, GCW, and Impact.'},
            {'name': 'BxB Hulk', 'real_name': 'Tsubasa Hasegawa', 'birth_date': '1981-10-18', 'hometown': 'Kanagawa, Japan', 'nationality': 'Japanese', 'about': 'BxB Hulk is a Dragon Gate star known for his dancing and flashy style.'},
            {'name': 'Averno', 'real_name': 'Juan Jose Gonzalez', 'birth_date': '1975-01-05', 'hometown': 'Mexico City, Mexico', 'nationality': 'Mexican', 'about': 'Averno is a CMLL legend and multiple time tag team champion. A rudo with decades of experience.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More modern wrestlers')
        return updated

    def enrich_80s_90s_stars(self):
        """Enrich 80s and 90s wrestling stars."""
        self.stdout.write('--- Enriching 80s/90s Stars ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Dino Bravo', 'real_name': 'Adolfo Bresciano', 'birth_date': '1948-08-06', 'hometown': 'Montreal, Quebec', 'nationality': 'Canadian', 'about': 'Dino Bravo was Canada\'s strongest man and a WWF tag team champion. Known for his bench press.'},
            {'name': 'Disco Inferno', 'real_name': 'Glenn Gilbertti', 'birth_date': '1968-09-22', 'hometown': 'Brooklyn, New York', 'nationality': 'American', 'about': 'Disco Inferno was a disco-dancing WCW personality who won the TV and Cruiserweight titles.'},
            {'name': 'Dr. Death Steve Williams', 'real_name': 'Steve Williams', 'birth_date': '1960-05-14', 'hometown': 'Lakewood, Colorado', 'nationality': 'American', 'finishers': 'Oklahoma Stampede', 'about': 'Dr. Death was an NCAA wrestling champion who became a legend in Japan and the US.'},
            {'name': 'Dynamite Kid', 'real_name': 'Thomas Billington', 'birth_date': '1958-12-05', 'hometown': 'Golborne, England', 'nationality': 'British', 'finishers': 'Diving Headbutt', 'about': 'Dynamite Kid was half of the British Bulldogs and influenced high-flying wrestling forever.'},
            {'name': 'Earthquake', 'real_name': 'John Tenta', 'birth_date': '1963-06-22', 'hometown': 'Surrey, British Columbia', 'nationality': 'Canadian', 'finishers': 'Earthquake Splash', 'about': 'Earthquake was a devastating WWF star who feuded with Hulk Hogan. Former sumo wrestler.'},
            {'name': 'Ernie Ladd', 'real_name': 'Ernest Ladd', 'birth_date': '1938-11-28', 'hometown': 'Orange, Texas', 'nationality': 'American', 'about': 'Ernie Ladd was an NFL star who became a top wrestling heel. The Big Cat was a legend.'},
            {'name': 'George Steele', 'real_name': 'William Myers', 'birth_date': '1937-04-16', 'hometown': 'Detroit, Michigan', 'nationality': 'American', 'about': 'George "The Animal" Steele ate turnbuckles and was a teacher in real life. WWE Hall of Famer.'},
            {'name': 'Glacier', 'real_name': 'Ray Lloyd', 'birth_date': '1964-02-20', 'hometown': 'Chamblee, Georgia', 'nationality': 'American', 'about': 'Glacier was WCW\'s Sub-Zero-inspired character. His elaborate entrance was memorable.'},
            {'name': 'Goldust', 'real_name': 'Dustin Runnels', 'birth_date': '1969-04-11', 'hometown': 'Austin, Texas', 'nationality': 'American', 'finishers': 'Curtain Call', 'about': 'Goldust was a boundary-pushing character who became a multi-time tag and IC champion.'},
            {'name': 'Gorilla Monsoon', 'real_name': 'Robert Marella', 'birth_date': '1937-06-04', 'hometown': 'Rochester, New York', 'nationality': 'American', 'about': 'Gorilla Monsoon was a powerful wrestler who became WWE\'s iconic announcer and president.'},
            {'name': 'Greg Valentine', 'real_name': 'Jonathan Wisniski Jr.', 'birth_date': '1950-09-02', 'hometown': 'Seattle, Washington', 'nationality': 'American', 'finishers': 'Figure Four Leglock', 'about': 'Greg "The Hammer" Valentine was a two-time IC Champion with a devastating figure four.'},
            {'name': 'Hacksaw Jim Duggan', 'real_name': 'James Duggan', 'birth_date': '1954-01-14', 'hometown': 'Glens Falls, New York', 'nationality': 'American', 'about': 'Hacksaw Jim Duggan won the first Royal Rumble. His 2x4 and "USA!" chants were legendary.'},
            {'name': 'Hillbilly Jim', 'real_name': 'James Morris', 'birth_date': '1952-05-05', 'hometown': 'Mudlick, Kentucky', 'nationality': 'American', 'about': 'Hillbilly Jim was a beloved WWF star who was trained by Hulk Hogan in storyline.'},
            {'name': 'Ivan Koloff', 'real_name': 'Oreal Perras', 'birth_date': '1942-08-25', 'hometown': 'Montreal, Quebec', 'nationality': 'Canadian', 'about': 'Ivan Koloff ended Bruno Sammartino\'s legendary WWWF title reign. The Russian Bear was feared.'},
            {'name': 'Jerry Lynn', 'real_name': 'Jerry Sigler', 'birth_date': '1963-05-23', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'finishers': 'Cradle Piledriver', 'about': 'Jerry Lynn had legendary matches with RVD in ECW. A technical master who excelled everywhere.'},
            {'name': 'Jesse Ventura', 'real_name': 'James Janos', 'birth_date': '1951-07-15', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'Jesse "The Body" Ventura became a legendary commentator and Governor of Minnesota.'},
            {'name': 'Jimmy Snuka', 'real_name': 'James Reiher', 'birth_date': '1943-05-18', 'hometown': 'Fiji', 'nationality': 'Fijian', 'finishers': 'Superfly Splash', 'about': 'Jimmy Superfly Snuka\'s cage dive onto Don Muraco is one of wrestling\'s iconic moments.'},
            {'name': 'Jimmy Valiant', 'real_name': 'James Fanning', 'birth_date': '1942-08-05', 'hometown': 'Trenton, New Jersey', 'nationality': 'American', 'about': 'Jimmy Valiant, the Boogie Woogie Man, was a beloved babyface in the NWA territories.'},
            {'name': 'Doink the Clown', 'real_name': 'Matt Borne', 'birth_date': '1957-06-02', 'hometown': 'Portland, Oregon', 'nationality': 'American', 'about': 'Doink the Clown was a brilliant heel who became a comedy babyface. Matt Borne was a skilled worker.'},
            {'name': 'Doc Gallows', 'real_name': 'Drew Hankinson', 'birth_date': '1983-12-25', 'hometown': 'Washington, D.C.', 'nationality': 'American', 'aliases': 'Luke Gallows, Festus', 'about': 'Doc Gallows is a founding member of Bullet Club and The Club. Multiple time tag team champion.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} 80s/90s stars')
        return updated

    def enrich_modern_stars_2(self):
        """Enrich more modern wrestling stars."""
        self.stdout.write('--- Enriching Modern Stars Part 2 ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Dominik Mysterio', 'real_name': 'Dominik Gutierrez', 'birth_date': '1997-04-01', 'hometown': 'San Diego, California', 'nationality': 'American', 'about': 'Dominik Mysterio is Rey Mysterio\'s son who joined Judgment Day. Dirty Dom became a heel star.'},
            {'name': 'EC3', 'real_name': 'Michael Hutter', 'birth_date': '1983-04-05', 'hometown': 'Pittsburgh, Pennsylvania', 'nationality': 'American', 'aliases': 'Derrick Bateman', 'about': 'EC3 was a two-time TNA World Champion. He was trouble and controlled his narrative.'},
            {'name': 'Eddie Kingston', 'real_name': 'Edward Moore', 'birth_date': '1981-12-13', 'hometown': 'Yonkers, New York', 'nationality': 'American', 'finishers': 'Backfist, Burning Hammer', 'about': 'Eddie Kingston is the Mad King. His promos and intensity made him an AEW star.'},
            {'name': 'Emi Sakura', 'real_name': 'Emi Sakura', 'birth_date': '1976-03-01', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Emi Sakura trained Riho and other joshi stars. The Freddie Mercury of wrestling.'},
            {'name': 'Eric Young', 'real_name': 'Jeremy Fritz', 'birth_date': '1979-12-15', 'hometown': 'Nashville, Tennessee', 'nationality': 'Canadian', 'about': 'Eric Young was TNA World Champion and leader of Sanity. A comedic genius who can also go.'},
            {'name': 'Erick Rowan', 'real_name': 'Joseph Ruud', 'birth_date': '1981-10-28', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'Erick Rowan was part of the Wyatt Family and Bludgeon Brothers. A big man with intelligence.'},
            {'name': 'Evil Uno', 'real_name': 'Nicolas Dansereau', 'birth_date': '1983-03-27', 'hometown': 'Montreal, Quebec', 'nationality': 'Canadian', 'about': 'Evil Uno leads the Dark Order in AEW. His look and character are unique.'},
            {'name': 'Finn Balor', 'real_name': 'Fergal Devitt', 'birth_date': '1981-07-25', 'hometown': 'Bray, Ireland', 'nationality': 'Irish', 'aliases': 'Prince Devitt', 'finishers': 'Coup de Grace', 'about': 'Finn Balor was the first Universal Champion and leader of Bullet Club. The Demon is iconic.'},
            {'name': 'Fandango', 'real_name': 'Curtis Hussey', 'birth_date': '1981-10-03', 'hometown': 'San Jose, California', 'nationality': 'American', 'about': 'Fandango brought ballroom dancing to WWE and became a tag champion with Tyler Breeze.'},
            {'name': 'El Generico', 'real_name': 'Rami Sebei', 'birth_date': '1984-05-22', 'hometown': 'Tijuana, Mexico', 'nationality': 'Canadian', 'aliases': 'Sami Zayn', 'about': 'El Generico was an indie legend before becoming Sami Zayn. His matches with Kevin Steen were legendary.'},
            {'name': 'El Phantasmo', 'real_name': 'Michael Guigliano', 'birth_date': '1988-12-19', 'hometown': 'Burnaby, British Columbia', 'nationality': 'Canadian', 'finishers': 'CR2', 'about': 'El Phantasmo is Bullet Club\'s junior heavyweight ace. His cheating antics and ability are top tier.'},
            {'name': 'Dragon Kid', 'real_name': 'Shuntaro Araki', 'birth_date': '1976-07-02', 'hometown': 'Hikone, Japan', 'nationality': 'Japanese', 'about': 'Dragon Kid is a Dragon Gate legend and the heart of the promotion. His hurricanrana is beautiful.'},
            {'name': 'Desmond Wolfe', 'real_name': 'Nigel McGuinness', 'birth_date': '1976-01-09', 'hometown': 'London, England', 'nationality': 'British', 'finishers': 'Tower of London, Jawbreaker Lariat', 'about': 'Desmond Wolfe was TNA\'s British star. As Nigel McGuinness, he was ROH World Champion.'},
            {'name': 'Great Sasuke', 'real_name': 'Masanori Murakawa', 'birth_date': '1969-07-18', 'hometown': 'Morioka, Japan', 'nationality': 'Japanese', 'about': 'Great Sasuke founded Michinoku Pro and was elected to political office while wrestling.'},
            {'name': 'Hikaru Shida', 'real_name': 'Hikaru Shida', 'birth_date': '1988-06-08', 'hometown': 'Yokohama, Japan', 'nationality': 'Japanese', 'finishers': 'Katana', 'about': 'Hikaru Shida was AEW Women\'s Champion for 372 days. She combines joshi style with kendo.'},
            {'name': 'Homicide', 'real_name': 'Nelson Erazo', 'birth_date': '1977-04-20', 'hometown': 'Brooklyn, New York', 'nationality': 'American', 'finishers': 'Cop Killa, Ace Crusher', 'about': 'Homicide was ROH and TNA World Champion. The Notorious 187 brought street credibility.'},
            {'name': 'Genichiro Tenryu', 'real_name': 'Genichiro Shimada', 'birth_date': '1950-02-02', 'hometown': 'Fukui, Japan', 'nationality': 'Japanese', 'about': 'Genichiro Tenryu was a former sumo who became a wrestling legend. His feud with Jumbo Tsuruta is historic.'},
            {'name': 'Go Shiozaki', 'real_name': 'Go Shiozaki', 'birth_date': '1982-06-07', 'hometown': 'Fukuoka, Japan', 'nationality': 'Japanese', 'finishers': 'Gowan Lariat', 'about': 'Go Shiozaki is a Pro Wrestling NOAH legend and multiple time GHC Champion. His chops are brutal.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Modern stars part 2')
        return updated

    def enrich_uso_bloodline(self):
        """Enrich Uso family and Bloodline members."""
        self.stdout.write('--- Enriching Bloodline/Uso ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Jey Uso', 'real_name': 'Joshua Fatu', 'birth_date': '1985-08-22', 'hometown': 'San Francisco, California', 'nationality': 'American', 'finishers': 'Uso Splash', 'about': 'Jey Uso is part of the most decorated tag team in WWE history. YEET! Main event Uso now.'},
            {'name': 'Jimmy Uso', 'real_name': 'Jonathan Fatu', 'birth_date': '1985-08-22', 'hometown': 'San Francisco, California', 'nationality': 'American', 'finishers': 'Uso Splash', 'about': 'Jimmy Uso is part of the Usos and the Bloodline. Multiple time tag team champion.'},
            {'name': 'Afa Anoaʻi', 'real_name': 'Afa Anoaʻi', 'birth_date': '1942-11-21', 'hometown': 'Samoa', 'nationality': 'Samoan', 'about': 'Afa was half of the Wild Samoans and patriarch of the legendary Anoaʻi wrestling family.'},
            {'name': 'Haku', 'real_name': 'Tonga Fifita', 'birth_date': '1959-02-03', 'hometown': 'Tonga', 'nationality': 'Tongan', 'aliases': 'Meng, King Haku', 'about': 'Haku is legendary for being the toughest man in wrestling. King of the Ring and feared fighter.'},
            {'name': 'Jacob Fatu', 'real_name': 'Jacob Fatu', 'birth_date': '1992-08-25', 'hometown': 'San Francisco, California', 'nationality': 'American', 'finishers': 'Moonsault', 'about': 'Jacob Fatu was MLW World Champion and joined the Bloodline. His agility for his size is amazing.'},
            {'name': 'Hikuleo', 'real_name': 'Hikuleo', 'birth_date': '1991-12-23', 'hometown': 'Kissimmee, Florida', 'nationality': 'American', 'about': 'Hikuleo is a Bullet Club member in NJPW. His size and lineage make him a future star.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Bloodline/Uso members')
        return updated

    def enrich_managers_announcers(self):
        """Enrich managers and announcers."""
        self.stdout.write('--- Enriching Managers/Announcers ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Eric Bischoff', 'real_name': 'Eric Bischoff', 'birth_date': '1955-05-27', 'hometown': 'Detroit, Michigan', 'nationality': 'American', 'about': 'Eric Bischoff ran WCW and challenged Vince McMahon. Created the NWO and Monday Night Wars.'},
            {'name': 'Excalibur', 'real_name': 'Marc Letzmann', 'birth_date': '1979-04-01', 'hometown': 'Los Angeles, California', 'nationality': 'American', 'about': 'Excalibur is AEW\'s masked voice. Former PWG wrestler who became the best commentator in wrestling.'},
            {'name': 'Freddie Blassie', 'real_name': 'Fred Blassie', 'birth_date': '1918-02-08', 'hometown': 'St. Louis, Missouri', 'nationality': 'American', 'about': 'Freddie Blassie was a Hollywood Fashion Plate who managed many champions. Pencil-necked geeks!'},
            {'name': 'Gene Okerlund', 'real_name': 'Eugene Okerlund', 'birth_date': '1942-12-19', 'hometown': 'Sisseton, South Dakota', 'nationality': 'American', 'about': 'Mean Gene Okerlund was the voice of wrestling interviews for decades. WWE Hall of Famer.'},
            {'name': 'Gordon Solie', 'real_name': 'Jonard French', 'birth_date': '1929-01-26', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'Gordon Solie was the Dean of Wrestling Announcers. His sophistication elevated the sport.'},
            {'name': 'Gedo', 'real_name': 'Keiji Takayama', 'birth_date': '1969-11-28', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Gedo is the booker of NJPW and manager of Kazuchika Okada. Former IWGP Junior Tag Champion.'},
            {'name': 'Jado', 'real_name': 'Yoshihiro Takayama', 'birth_date': '1968-01-28', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Jado is Gedo\'s longtime partner and Bullet Club associate. Multiple time tag team champion.'},
            {'name': 'Jim Ross', 'real_name': 'James Ross', 'birth_date': '1952-01-03', 'hometown': 'Fort Bragg, California', 'nationality': 'American', 'about': 'Jim Ross is the greatest wrestling announcer ever. Bah Gawd! WWE and AEW Hall of Famer.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Managers/Announcers')
        return updated

    def enrich_tag_teams_factions(self):
        """Enrich tag team and faction members."""
        self.stdout.write('--- Enriching Tag Team Members ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Jay Briscoe', 'real_name': 'Jamin Pugh', 'birth_date': '1984-01-25', 'hometown': 'Sandy Fork, Delaware', 'nationality': 'American', 'finishers': 'Jay Driller', 'about': 'Jay Briscoe was half of the most decorated ROH tag team ever. Two-time ROH World Champion. RIP Dem Boys.'},
            {'name': 'Jimmy Jacobs', 'real_name': 'James Jacobs', 'birth_date': '1984-01-02', 'hometown': 'Grand Rapids, Michigan', 'nationality': 'American', 'about': 'Jimmy Jacobs was an Age of the Fall leader in ROH and WWE writer. His promos were intense.'},
            {'name': 'Jimmy Rave', 'real_name': 'James Guffey', 'birth_date': '1982-02-02', 'hometown': 'Atlanta, Georgia', 'nationality': 'American', 'about': 'Jimmy Rave was a Ring of Honor star and Embassy member. Overcame incredible adversity.'},
            {'name': 'Jimmy Havoc', 'real_name': 'James Mayell', 'birth_date': '1984-02-04', 'hometown': 'Croydon, England', 'nationality': 'British', 'about': 'Jimmy Havoc was a deathmatch legend and PROGRESS Champion. Known for extreme hardcore.'},
            {'name': 'Jack Evans', 'real_name': 'Jack Miller', 'birth_date': '1982-12-25', 'hometown': 'Parkland, Washington', 'nationality': 'American', 'about': 'Jack Evans is one of the most acrobatic wrestlers ever. AAA and Lucha Underground star.'},
            {'name': 'Isiah Kassidy', 'real_name': 'Isaiah Kasey', 'birth_date': '1997-07-29', 'hometown': 'Lexington, Kentucky', 'nationality': 'American', 'about': 'Isiah Kassidy is half of Private Party. Young star with incredible charisma.'},
            {'name': 'Joe Hendry', 'real_name': 'Joe Hendry', 'birth_date': '1988-01-21', 'hometown': 'Edinburgh, Scotland', 'nationality': 'Scottish', 'about': 'Joe Hendry is the Prestigious One. His entrance songs and viral moments made him a star.'},
            {'name': 'Jimmy Garvin', 'real_name': 'James Williams', 'birth_date': '1952-09-25', 'hometown': 'Tampa, Florida', 'nationality': 'American', 'about': 'Jimmy Garvin was a Fabulous Freebird and NWA US Champion. His feud with Michael Hayes was legendary.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Tag team members')
        return updated

    def enrich_more_wcw_ecw(self):
        """Enrich more WCW and ECW wrestlers."""
        self.stdout.write('--- Enriching More WCW/ECW ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Konnan', 'real_name': 'Charles Ashenoff', 'birth_date': '1964-01-06', 'hometown': 'Cuba', 'nationality': 'Cuban-American', 'about': 'Konnan is a legend in WCW, AAA, and TNA. Founder of LAX and nWo Latino. Influential in lucha libre.'},
            {'name': 'Lex Luger', 'real_name': 'Lawrence Pfohl', 'birth_date': '1958-06-02', 'hometown': 'Buffalo, New York', 'nationality': 'American', 'finishers': 'Torture Rack', 'about': 'Lex Luger was the Total Package. WCW World Champion and WWF main eventer. NFL player turned wrestler.'},
            {'name': 'Magnum TA', 'real_name': 'Terry Allen', 'birth_date': '1959-06-16', 'hometown': 'Chesapeake, Virginia', 'nationality': 'American', 'finishers': 'Belly to Belly Suplex', 'about': 'Magnum TA was destined for greatness before a car accident ended his career. NWA US Champion.'},
            {'name': 'Mikey Whipwreck', 'real_name': 'Michael Watson', 'birth_date': '1973-06-04', 'hometown': 'Buffalo, New York', 'nationality': 'American', 'about': 'Mikey Whipwreck was ECW\'s ultimate underdog. Three-time ECW Champion who beat Steve Austin.'},
            {'name': 'Nikita Koloff', 'real_name': 'Nelson Simpson', 'birth_date': '1959-03-09', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'finishers': 'Russian Sickle', 'about': 'Nikita Koloff was the Russian Nightmare. His turn with Dusty Rhodes was legendary. NWA World Tag Champion.'},
            {'name': 'Public Enemy', 'real_name': 'Flyboy Rocco Rock and Johnny Grunge', 'about': 'Public Enemy (Rocco Rock and Johnny Grunge) were ECW Tag Team Champions who popularized table matches.'},
            {'name': 'Sid Vicious', 'real_name': 'Sidney Eudy', 'birth_date': '1960-12-16', 'hometown': 'West Memphis, Arkansas', 'nationality': 'American', 'aliases': 'Sid Justice, Sycho Sid', 'finishers': 'Powerbomb', 'about': 'Sid was a two-time WWF and WCW World Champion. The master and ruler of the world. I have half the brain!'},
            {'name': 'Little Guido', 'real_name': 'James Maritato', 'birth_date': '1972-08-01', 'hometown': 'Brooklyn, New York', 'nationality': 'American', 'aliases': 'Nunzio', 'about': 'Little Guido was an FBI member in ECW. Later Nunzio in WWE. Cruiserweight Champion.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More WCW/ECW')
        return updated

    def enrich_modern_wwe_2(self):
        """Enrich more modern WWE wrestlers."""
        self.stdout.write('--- Enriching More Modern WWE ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Kushida', 'real_name': 'Yujiro Kushida', 'birth_date': '1983-05-12', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'finishers': 'Hoverboard Lock', 'about': 'KUSHIDA is a time-traveling wrestler and former IWGP Junior Heavyweight Champion. Back to the Future superfan.'},
            {'name': 'Liv Morgan', 'real_name': 'Gionna Daddio', 'birth_date': '1994-06-08', 'hometown': 'Elmwood Park, New Jersey', 'nationality': 'American', 'finishers': 'Oblivion', 'about': 'Liv Morgan is a SmackDown Women\'s Champion who cashed in Money in the Bank. Riott Squad member.'},
            {'name': 'Logan Paul', 'real_name': 'Logan Paul', 'birth_date': '1995-04-01', 'hometown': 'Westlake, Ohio', 'nationality': 'American', 'finishers': 'Lucky Punch', 'about': 'Logan Paul is a YouTuber turned WWE wrestler. United States Champion with impressive athletic ability.'},
            {'name': 'Maryse', 'real_name': 'Maryse Ouellet', 'birth_date': '1983-01-21', 'hometown': 'Montreal, Quebec', 'nationality': 'Canadian', 'about': 'Maryse is a two-time Divas Champion and married to The Miz. French-Canadian bombshell.'},
            {'name': 'Matt Riddle', 'real_name': 'Matthew Riddle', 'birth_date': '1985-01-14', 'hometown': 'Allentown, Pennsylvania', 'nationality': 'American', 'aliases': 'Riddle', 'finishers': 'Bro Derek', 'about': 'Riddle is a former UFC fighter and Tag Team Champion with Randy Orton as RK-Bro. Bro!'},
            {'name': 'Matt Cardona', 'real_name': 'Matthew Cardona', 'birth_date': '1985-09-14', 'hometown': 'Merrick, New York', 'nationality': 'American', 'aliases': 'Zack Ryder', 'about': 'Matt Cardona was Zack Ryder in WWE and became GCW Universal Champion. Woo Woo Woo!'},
            {'name': 'Neville', 'real_name': 'Ben Satterly', 'birth_date': '1986-08-24', 'hometown': 'Newcastle upon Tyne, England', 'nationality': 'British', 'aliases': 'PAC', 'finishers': 'Red Arrow, Black Arrow', 'about': 'Neville was Cruiserweight Champion in WWE. Now PAC in AEW. The Man Gravity Forgot.'},
            {'name': 'Nia Jax', 'real_name': 'Savelina Fanene', 'birth_date': '1984-05-29', 'hometown': 'San Diego, California', 'nationality': 'American', 'about': 'Nia Jax is a Raw Women\'s Champion. Not like most girls. Part of the Anoa\'i family.'},
            {'name': 'Nick Aldis', 'real_name': 'Nick Aldis', 'birth_date': '1986-11-04', 'hometown': 'King\'s Lynn, England', 'nationality': 'British', 'aliases': 'Magnus', 'about': 'Nick Aldis is a former NWA World Champion and SmackDown General Manager. The National Treasure.'},
            {'name': 'Omos', 'real_name': 'Tolulope Omogbehin', 'birth_date': '1994-01-15', 'hometown': 'Lagos, Nigeria', 'nationality': 'Nigerian', 'about': 'Omos is 7\'3" and was Raw Tag Team Champion with AJ Styles. The Nigerian Giant.'},
            {'name': 'Pat McAfee', 'real_name': 'Patrick McAfee', 'birth_date': '1987-05-02', 'hometown': 'Pittsburgh, Pennsylvania', 'nationality': 'American', 'about': 'Pat McAfee is a former NFL punter and WWE announcer/wrestler. His athleticism is incredible.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More modern WWE')
        return updated

    def enrich_more_aew_2(self):
        """Enrich more AEW wrestlers."""
        self.stdout.write('--- Enriching More AEW Part 2 ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Lee Moriarty', 'real_name': 'Jon Michael Moriarty', 'birth_date': '1997-02-03', 'hometown': 'Pittsburgh, Pennsylvania', 'nationality': 'American', 'about': 'Lee Moriarty is a technical prodigy in AEW. Taiga Style. Part of The Firm and Gates of Agony.'},
            {'name': 'Malakai Black', 'real_name': 'Tom Budgen', 'birth_date': '1985-05-19', 'hometown': 'Amsterdam, Netherlands', 'nationality': 'Dutch', 'finishers': 'Black Mass', 'about': 'Malakai Black leads the House of Black in AEW. Former NXT Champion with dark mystical character.'},
            {'name': 'Marq Quen', 'real_name': 'Terrell Hughes', 'birth_date': '1998-05-05', 'hometown': 'Queens, New York', 'nationality': 'American', 'about': 'Marq Quen is half of Private Party. Known for his incredible shooting star press.'},
            {'name': 'Max Caster', 'real_name': 'Maxwell Friedman', 'birth_date': '1989-06-09', 'hometown': 'Plainview, New York', 'nationality': 'American', 'about': 'Max Caster is half of the Acclaimed. His rap entrances are legendary. Everyone loves the Acclaimed!'},
            {'name': 'Miro', 'real_name': 'Miroslav Barnyashev', 'birth_date': '1985-12-25', 'hometown': 'Plovdiv, Bulgaria', 'nationality': 'Bulgarian', 'finishers': 'Game Over', 'about': 'Miro is the Redeemer in AEW. Former TNT Champion. Was Rusev in WWE.'},
            {'name': 'Nyla Rose', 'real_name': 'Nyla Rose', 'birth_date': '1982-06-12', 'hometown': 'Washington, D.C.', 'nationality': 'American', 'finishers': 'Beast Bomb', 'about': 'Nyla Rose was the second AEW Women\'s Champion. The Native Beast. First trans champion in major promotion.'},
            {'name': 'Penelope Ford', 'real_name': 'Penelope Ford', 'birth_date': '1992-03-09', 'hometown': 'Jacksonville, Florida', 'nationality': 'American', 'about': 'Penelope Ford is an acrobatic AEW wrestler and wife of Kip Sabian.'},
            {'name': 'Preston Vance', 'real_name': 'Preston Vance', 'birth_date': '1992-10-10', 'hometown': 'Orlando, Florida', 'nationality': 'American', 'aliases': '10', 'about': 'Preston Vance is 10 of the Dark Order. Former bodybuilder turned wrestler.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More AEW part 2')
        return updated

    def enrich_more_japan_2(self):
        """Enrich more Japanese wrestlers."""
        self.stdout.write('--- Enriching More Japan Part 2 ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Naomichi Marufuji', 'real_name': 'Naomichi Marufuji', 'birth_date': '1979-09-26', 'hometown': 'Saitama, Japan', 'nationality': 'Japanese', 'finishers': 'Shiranui', 'about': 'Naomichi Marufuji is a NOAH legend. Multiple time GHC Champion with incredible junior heavyweight history.'},
            {'name': 'Masato Yoshino', 'real_name': 'Masato Yoshino', 'birth_date': '1977-03-18', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Masato Yoshino is the fastest wrestler in the world. Dragon Gate legend with World-1 era dominance.'},
            {'name': 'Naruki Doi', 'real_name': 'Naruki Doi', 'birth_date': '1981-10-03', 'hometown': 'Hyogo, Japan', 'nationality': 'Japanese', 'about': 'Naruki Doi is a Dragon Gate pioneer. Multiple time Open the Dream Gate Champion.'},
            {'name': 'Masaaki Mochizuki', 'real_name': 'Masaaki Mochizuki', 'birth_date': '1969-12-03', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Masaaki Mochizuki is the King of Kicks. Dragon Gate veteran with incredible striking ability.'},
            {'name': 'Master Wato', 'real_name': 'Yoshikuni Kawabata', 'birth_date': '1991-07-20', 'hometown': 'Tokyo, Japan', 'nationality': 'Japanese', 'about': 'Master Wato is a NJPW junior heavyweight. Trained in Mexico before returning to Japan.'},
            {'name': 'Nathan Frazer', 'real_name': 'Ben Carter', 'birth_date': '1997-03-03', 'hometown': 'Nottingham, England', 'nationality': 'British', 'about': 'Nathan Frazer is an NXT star. High-flying British talent who impressed in AEW before signing with WWE.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} More Japan part 2')
        return updated

    def enrich_legends_2(self):
        """Enrich more wrestling legends."""
        self.stdout.write('--- Enriching Legends Part 2 ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Mildred Burke', 'real_name': 'Mildred Bliss', 'birth_date': '1915-08-14', 'hometown': 'Coffeyville, Kansas', 'nationality': 'American', 'about': 'Mildred Burke was the greatest female wrestler of the early era. World Women\'s Champion for nearly 20 years.'},
            {'name': 'Pat Patterson', 'real_name': 'Pierre Clemont', 'birth_date': '1941-01-19', 'hometown': 'Montreal, Quebec', 'nationality': 'Canadian', 'about': 'Pat Patterson was the first Intercontinental Champion and legendary creative mind behind the Royal Rumble.'},
            {'name': 'Paul Orndorff', 'real_name': 'Paul Orndorff', 'birth_date': '1949-10-29', 'hometown': 'Brandon, Florida', 'nationality': 'American', 'finishers': 'Piledriver', 'about': 'Mr. Wonderful Paul Orndorff main evented WrestleMania I with Hulk Hogan. NFL player turned wrestler.'},
            {'name': 'Peter Maivia', 'real_name': 'Fanene Leifi Pita Maivia', 'birth_date': '1937-04-06', 'hometown': 'Samoa', 'nationality': 'Samoan', 'about': 'High Chief Peter Maivia was The Rock\'s grandfather. WWWF star and Samoan wrestling royalty.'},
            {'name': 'Lia Maivia', 'real_name': 'Ofelia Fuataga', 'birth_date': '1939-11-04', 'hometown': 'Samoa', 'nationality': 'Samoan', 'about': 'Lia Maivia was the first female wrestling promoter. The Rock\'s grandmother. Ran All Japan Pro Wrestling.'},
            {'name': 'Penny Banner', 'real_name': 'Mary Ann Kostecki', 'birth_date': '1934-08-11', 'hometown': 'St. Louis, Missouri', 'nationality': 'American', 'about': 'Penny Banner was a multiple time Women\'s Champion in the 1950s and 60s. Pioneer of women\'s wrestling.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Legends part 2')
        return updated

    def enrich_women_modern(self):
        """Enrich modern women wrestlers."""
        self.stdout.write('--- Enriching Modern Women ---')
        updated = 0
        wrestlers_data = [
            {'name': 'Madison Rayne', 'real_name': 'Ashley Simmons', 'birth_date': '1986-01-05', 'hometown': 'Columbus, Ohio', 'nationality': 'American', 'about': 'Madison Rayne is a five-time Knockouts Champion. Part of the Beautiful People. Now an AEW coach.'},
            {'name': 'Mariah May', 'real_name': 'Mariah May', 'birth_date': '1997-06-04', 'hometown': 'Kent, England', 'nationality': 'British', 'about': 'Mariah May is an AEW rising star. Trained in Japan at Stardom. Young British talent.'},
            {'name': 'Marina Shafir', 'real_name': 'Marina Shafir', 'birth_date': '1988-03-14', 'hometown': 'Moldova', 'nationality': 'Moldovan-American', 'about': 'Marina Shafir is a former MMA fighter and member of Four Horsewomen of MMA. NXT and AEW wrestler.'},
            {'name': 'Masha Slamovich', 'real_name': 'Maria Sivakova', 'birth_date': '1995-12-15', 'hometown': 'Moscow, Russia', 'nationality': 'Russian-American', 'about': 'Masha Slamovich is a TNA Knockouts Champion. The Russian wrestler with a killer instinct.'},
            {'name': 'Mercedes Martinez', 'real_name': 'Mercedes Martinez', 'birth_date': '1980-11-28', 'hometown': 'Waterbury, Connecticut', 'nationality': 'American', 'about': 'Mercedes Martinez is a wrestling veteran who competed in NXT and ROH. Puerto Rican powerhouse.'},
            {'name': 'ODB', 'real_name': 'Jessica Kresa', 'birth_date': '1978-03-21', 'hometown': 'Minneapolis, Minnesota', 'nationality': 'American', 'about': 'ODB is a multiple time TNA Knockouts Champion. Known for her flask and unique personality.'},
        ]
        for data in wrestlers_data:
            name = data.pop('name')
            updated += self.update_wrestler(name, **data)
        self.stdout.write(f'  Updated {updated} Modern women')
        return updated
