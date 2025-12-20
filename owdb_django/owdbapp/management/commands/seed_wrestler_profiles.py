"""
Seed wrestler profiles with comprehensive bios, birth info, and career details.

Usage:
    python manage.py seed_wrestler_profiles
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import Wrestler


class Command(BaseCommand):
    help = 'Seed wrestler profiles with comprehensive bios'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== Seeding Wrestler Profiles ===\n'))

        updated = 0
        created = 0

        wrestlers_data = [
            # Legends
            {
                'name': 'Hulk Hogan',
                'real_name': 'Terry Gene Bollea',
                'birth_date': date(1953, 8, 11),
                'hometown': 'Augusta, Georgia, USA',
                'height': "6'7\"",
                'weight': '302 lbs',
                'debut_year': 1977,
                'about': 'Hulk Hogan is arguably the most iconic professional wrestler of all time. He defined the golden era of professional wrestling in the 1980s with his charismatic persona, trademark catchphrases like "Whatcha gonna do, brother?" and his signature leg drop finisher. Hogan main-evented multiple WrestleManias and was the face of the WWF during its national expansion. In 1996, he shocked the wrestling world by turning heel and forming the New World Order (nWo) in WCW, proving his versatility and reinventing himself as Hollywood Hogan. A 12-time world champion across WWF, WCW, and TNA, Hogan\'s impact on wrestling culture extends far beyond the ring into mainstream pop culture.'
            },
            {
                'name': 'Ric Flair',
                'real_name': 'Richard Morgan Fliehr',
                'birth_date': date(1949, 2, 25),
                'hometown': 'Memphis, Tennessee, USA',
                'height': "6'1\"",
                'weight': '243 lbs',
                'debut_year': 1972,
                'about': 'Ric Flair, "The Nature Boy," is widely considered the greatest professional wrestler of all time. Known for his flamboyant personality, signature "WOOO!" catchphrase, and the Figure Four Leglock submission, Flair was a 16-time world champion across NWA, WCW, and WWE. He was the cornerstone of the legendary Four Horsemen stable and main-evented countless events over five decades. His influence on in-ring psychology, promos, and character work has shaped generations of wrestlers. Flair\'s career spanned from the territorial era through the Monday Night Wars and into the modern era, cementing his legacy as one of wrestling\'s all-time greats.'
            },
            {
                'name': 'The Undertaker',
                'real_name': 'Mark William Calaway',
                'birth_date': date(1965, 3, 24),
                'hometown': 'Houston, Texas, USA',
                'height': "6'10\"",
                'weight': '309 lbs',
                'debut_year': 1984,
                'about': 'The Undertaker is one of the most iconic and respected figures in professional wrestling history. Debuting at Survivor Series 1990, he portrayed a supernatural mortician character that evolved over 30 years while remaining consistently compelling. His WrestleMania streak of 21 consecutive victories became legendary, and matches at "The Showcase of the Immortals" were considered must-see events. Known for his dedication to character and in-ring storytelling, The Undertaker main-evented WrestleMania multiple times and held world championships seven times. His Phenom persona, entrance, and matches like the Hell in a Cell with Mankind define pro wrestling\'s theatrical potential.'
            },
            {
                'name': 'Stone Cold Steve Austin',
                'real_name': 'Steven James Anderson',
                'birth_date': date(1964, 12, 18),
                'hometown': 'Austin, Texas, USA',
                'height': "6'2\"",
                'weight': '252 lbs',
                'debut_year': 1989,
                'about': 'Stone Cold Steve Austin is credited as the driving force behind WWE winning the Monday Night Wars. His anti-authority character and feud with Vince McMahon captivated audiences and defined the Attitude Era. The "Austin 3:16" promo after winning King of the Ring 1996 changed wrestling forever. Known for his Stone Cold Stunner, beer-drinking celebrations, and middle finger salutes, Austin was a cultural phenomenon. A six-time WWF/WWE Champion, he main-evented three consecutive WrestleManias and his merchandise sales remain legendary. His 2022 return at WrestleMania 38 for a No Holds Barred match with Kevin Owens proved his enduring popularity.'
            },
            {
                'name': 'The Rock',
                'real_name': 'Dwayne Douglas Johnson',
                'birth_date': date(1972, 5, 2),
                'hometown': 'Hayward, California, USA',
                'height': "6'5\"",
                'weight': '260 lbs',
                'debut_year': 1996,
                'about': 'The Rock, born into wrestling royalty as the son of Rocky Johnson and grandson of Peter Maivia, became one of the biggest crossover stars in entertainment history. Starting as Rocky Maivia, he evolved into "The Great One" with unparalleled charisma, catchphrases like "If you smell what The Rock is cooking!" and electrifying promos. An 8-time WWE Champion, he main-evented multiple WrestleManias against Steve Austin, Hulk Hogan, John Cena, and Roman Reigns. His Hollywood career made him one of the highest-paid actors in the world, yet he continues to return to WWE for special appearances, including his 2024 heel turn as the "Final Boss."'
            },
            {
                'name': 'John Cena',
                'real_name': 'John Felix Anthony Cena Jr.',
                'birth_date': date(1977, 4, 23),
                'hometown': 'West Newbury, Massachusetts, USA',
                'height': "6'1\"",
                'weight': '251 lbs',
                'debut_year': 2000,
                'about': 'John Cena is the defining WWE Superstar of the 2000s and 2010s. With his "Never Give Up" motto and five moves of doom, Cena polarized fans with his superhero booking while consistently delivering in big matches. A record-tying 16-time world champion, he has granted over 650 Make-A-Wish requests, more than any other celebrity. His feuds with Edge, CM Punk, and The Rock created memorable moments. Like The Rock before him, Cena transitioned to Hollywood stardom while maintaining his WWE connection. His 2025 retirement tour marks the end of an era for a man who was the face of WWE for over a decade.'
            },
            {
                'name': 'Shawn Michaels',
                'real_name': 'Michael Shawn Hickenbottom',
                'birth_date': date(1965, 7, 22),
                'hometown': 'Chandler, Arizona, USA',
                'height': "6'1\"",
                'weight': '225 lbs',
                'debut_year': 1984,
                'about': 'Shawn Michaels, "The Heartbreak Kid" and "Mr. WrestleMania," is considered by many to be the greatest in-ring performer in wrestling history. From his Rockers tag team days to his iconic singles career, HBK consistently delivered show-stealing matches. His 1997 feud with Bret Hart culminated in the controversial Montreal Screwjob. After retiring due to back injuries in 1998, he made a miraculous comeback in 2002 and continued performing at an elite level until 2010. His matches against The Undertaker at WrestleManias 25 and 26 are considered among the greatest of all time. He currently works as a trainer and producer for WWE NXT.'
            },
            {
                'name': 'Triple H',
                'real_name': 'Paul Michael Levesque',
                'birth_date': date(1969, 7, 27),
                'hometown': 'Nashua, New Hampshire, USA',
                'height': "6'4\"",
                'weight': '255 lbs',
                'debut_year': 1992,
                'about': 'Triple H rose from blue-blood gimmick beginnings to become one of WWE\'s most successful performers and eventually its creative leader. As a member of D-Generation X and leader of Evolution, he defined multiple eras. A 14-time world champion, "The Game" was known for intelligent heel work and main event matches against Steve Austin, The Rock, Shawn Michaels, and many others. His marriage to Stephanie McMahon positioned him within the McMahon family, and he founded NXT, reshaping WWE\'s developmental system. Since 2022, he has served as WWE\'s Chief Content Officer, overseeing all creative and talent development.'
            },
            {
                'name': 'Bret Hart',
                'real_name': 'Bret Sergeant Hart',
                'birth_date': date(1957, 7, 2),
                'hometown': 'Calgary, Alberta, Canada',
                'height': "6'0\"",
                'weight': '234 lbs',
                'debut_year': 1976,
                'about': 'Bret "The Hitman" Hart is widely regarded as one of the most technically proficient wrestlers in history. From Calgary\'s Hart family wrestling dynasty, he trained in the legendary Hart Dungeon before becoming a WWF superstar. As part of The Hart Foundation tag team and later as a singles competitor, he won 5 WWF Championships. His feud with Shawn Michaels remains one of wrestling\'s most compelling rivalries, culminating in the infamous Montreal Screwjob at Survivor Series 1997. Known for his Sharpshooter submission, pink and black attire, and "excellence of execution" moniker, Bret\'s influence on technical wrestling is immeasurable.'
            },
            {
                'name': 'Randy Savage',
                'real_name': 'Randall Mario Poffo',
                'birth_date': date(1952, 11, 15),
                'hometown': 'Columbus, Ohio, USA',
                'height': "6'2\"",
                'weight': '237 lbs',
                'debut_year': 1973,
                'about': 'Randy "Macho Man" Savage was one of professional wrestling\'s most colorful and talented performers. Known for his distinctive gravelly voice, flamboyant outfits, and "Ooooh yeah!" catchphrase, Savage combined athletic ability with showmanship. His matches with Ricky Steamboat at WrestleMania III are considered among the greatest of all time. As part of the Mega Powers with Hulk Hogan and later as a top heel, he captivated audiences. His relationship with Miss Elizabeth added romantic drama to wrestling storytelling. Savage held multiple world championships in WWF and WCW before his passing in 2011.'
            },
            {
                'name': 'Andre the Giant',
                'real_name': 'André René Roussimoff',
                'birth_date': date(1946, 5, 19),
                'hometown': 'Coulommiers, France',
                'height': "7'4\"",
                'weight': '520 lbs',
                'debut_year': 1964,
                'about': 'Andre the Giant was professional wrestling\'s first true global attraction and pop culture icon. Billed as "The Eighth Wonder of the World," his immense size due to gigantism made him a legitimate spectacle. For 15 years, he was undefeated in professional wrestling, drawing crowds worldwide. His body slam by Hulk Hogan at WrestleMania III in front of 93,173 fans remains one of wrestling\'s most iconic moments. Beyond wrestling, he appeared in films like The Princess Bride. Andre passed away in 1993, but his legacy endures through the Andre the Giant Memorial Battle Royal at WrestleMania.'
            },
            {
                'name': 'Mick Foley',
                'real_name': 'Michael Francis Foley',
                'birth_date': date(1965, 6, 7),
                'hometown': 'Bloomington, Indiana, USA',
                'height': "6'2\"",
                'weight': '287 lbs',
                'debut_year': 1986,
                'about': 'Mick Foley is professional wrestling\'s most celebrated hardcore legend. Wrestling under multiple personas—Cactus Jack, Mankind, and Dude Love—he sacrificed his body in legendary matches. His Hell in a Cell match with The Undertaker at King of the Ring 1998, where he was thrown off and through the cell, is the most replayed match in wrestling history. A three-time WWE Champion and best-selling author, Foley brought legitimacy to hardcore wrestling while displaying surprising depth in character work. His "Have a Nice Day!" catchphrase and sock puppet Mr. Socko made him unexpectedly beloved despite his violent matches.'
            },
            # Modern Stars
            {
                'name': 'Roman Reigns',
                'real_name': 'Leati Joseph Anoa\'i',
                'birth_date': date(1985, 5, 25),
                'hometown': 'Pensacola, Florida, USA',
                'height': "6'3\"",
                'weight': '265 lbs',
                'debut_year': 2010,
                'about': 'Roman Reigns is the current face of WWE and one of professional wrestling\'s biggest stars. A member of the legendary Anoa\'i wrestling family, he played football at Georgia Tech before transitioning to wrestling. As part of The Shield with Seth Rollins and Dean Ambrose, he became a main eventer. His 2020 heel turn as "The Tribal Chief" leading The Bloodline transformed him into wrestling\'s most compelling character. His 1,316-day reign as Universal/Undisputed WWE Universal Champion is among the longest in modern history. His feuds with Cody Rhodes, Brock Lesnar, and The Rock have headlined multiple WrestleManias.'
            },
            {
                'name': 'Seth Rollins',
                'real_name': 'Colby Daniel Lopez',
                'birth_date': date(1986, 5, 28),
                'hometown': 'Buffalo, Iowa, USA',
                'height': "6'1\"",
                'weight': '217 lbs',
                'debut_year': 2005,
                'about': 'Seth Rollins is one of the most athletically gifted performers in WWE history. The inaugural NXT Champion and "Architect" of The Shield, he became one of WWE\'s top stars. His Money in the Bank cash-in at WrestleMania 31 to steal the title from Brock Lesnar and Roman Reigns is unforgettable. A multi-time world champion, Rollins is known for his Curb Stomp, Phoenix Splash, and ability to deliver in big matches. His character work has evolved from corporate champion to The Messiah to the "Visionary." Married to fellow wrestler Becky Lynch, he continues to be a centerpiece of WWE programming.'
            },
            {
                'name': 'Becky Lynch',
                'real_name': 'Rebecca Quin',
                'birth_date': date(1987, 1, 30),
                'hometown': 'Limerick, Ireland',
                'height': "5'6\"",
                'weight': '135 lbs',
                'debut_year': 2002,
                'about': 'Becky Lynch revolutionized women\'s wrestling as "The Man." After years as a reliable performer, her organic rise to the top in 2018-2019 made her WWE\'s most popular star regardless of gender. Her bloody face after being legitimately punched by Nia Jax became an iconic image. She main-evented WrestleMania 35 in the first-ever women\'s main event, winning both the Raw and SmackDown Women\'s Championships. A groundbreaking star who proved women could headline and draw, Lynch combines Irish wit, tough persona, and excellent in-ring work. Married to Seth Rollins, she is a multiple-time women\'s champion.'
            },
            {
                'name': 'Charlotte Flair',
                'real_name': 'Ashley Elizabeth Fliehr',
                'birth_date': date(1986, 4, 5),
                'hometown': 'Charlotte, North Carolina, USA',
                'height': "5'10\"",
                'weight': '145 lbs',
                'debut_year': 2012,
                'about': 'Charlotte Flair, daughter of Ric Flair, has established herself as one of the greatest female wrestlers ever. With 14 world championship reigns, she is approaching her father\'s record. As part of the Four Horsewomen with Becky Lynch, Sasha Banks, and Bayley, she helped elevate women\'s wrestling in WWE. Her athleticism, Figure Eight submission (evolution of her father\'s Figure Four), and big-match performances have headlined multiple pay-per-views. Charlotte\'s matches against Sasha Banks, Becky Lynch, and Rhea Ripley are modern classics. She brings a regal presence and legitimate athletic ability that make her a generational talent.'
            },
            {
                'name': 'Kenny Omega',
                'real_name': 'Tyson Smith',
                'birth_date': date(1983, 10, 16),
                'hometown': 'Winnipeg, Manitoba, Canada',
                'height': "6'0\"",
                'weight': '228 lbs',
                'debut_year': 2000,
                'about': 'Kenny Omega is considered one of the greatest wrestlers of his generation. His matches in New Japan Pro-Wrestling, particularly against Kazuchika Okada, redefined what was possible in professional wrestling and earned unprecedented ratings from wrestling journalists. As leader of The Elite with The Young Bucks, he was instrumental in founding AEW. The first AEW Triple Crown Champion (World, Tag Team, Trios), his "Best Bout Machine" nickname is well-earned. Known for the One Winged Angel, V-Trigger, and his video game-inspired personality, Omega bridges Japanese and North American wrestling styles brilliantly.'
            },
            {
                'name': 'Jon Moxley',
                'real_name': 'Jonathan David Good',
                'birth_date': date(1985, 12, 7),
                'hometown': 'Cincinnati, Ohio, USA',
                'height': "6'4\"",
                'weight': '234 lbs',
                'debut_year': 2004,
                'about': 'Jon Moxley reinvented himself after leaving WWE as Dean Ambrose. In AEW and NJPW, he embraced a violent, unhinged style that showcased his full potential. The second AEW World Champion, he led the company through the pandemic with multiple title reigns. His promos are intense and personal, his matches brutal and compelling. In NJPW, he won the IWGP US Championship and impressed Japanese audiences. A member of The Blackpool Combat Club with Bryan Danielson, Moxley represents wrestling\'s hardcore spirit. His book "MOX" revealed a fascinating journey through wrestling\'s independent scene to main event stardom.'
            },
            {
                'name': 'Bryan Danielson',
                'real_name': 'Bryan Lloyd Danielson',
                'birth_date': date(1981, 5, 22),
                'hometown': 'Aberdeen, Washington, USA',
                'height': "5'10\"",
                'weight': '210 lbs',
                'debut_year': 1999,
                'about': 'Bryan Danielson is one of professional wrestling\'s most universally respected performers. In Ring of Honor, he was the longest-reigning ROH World Champion and established himself as a technical master. In WWE as Daniel Bryan, the "YES! Movement" at WrestleMania XXX created one of wrestling\'s most organic fan-driven stories. After retirement due to concussions, he returned in 2018 and later joined AEW, where he formed The Blackpool Combat Club. Known for his kicks, submissions, and incredible work rate, Danielson proves smaller wrestlers can be top-tier attractions. His AEW run has featured classic matches with Kenny Omega, MJF, and Kazuchika Okada.'
            },
            {
                'name': 'CM Punk',
                'real_name': 'Phillip Jack Brooks',
                'birth_date': date(1978, 10, 26),
                'hometown': 'Chicago, Illinois, USA',
                'height': "6'2\"",
                'weight': '218 lbs',
                'debut_year': 1999,
                'about': 'CM Punk is one of the most polarizing and compelling figures in modern wrestling. His "Pipe Bomb" promo in 2011 changed wrestling, leading to his historic 434-day WWE Championship reign. Known for his straight edge lifestyle, articulate promos, and workrate, Punk resonated with fans who felt WWE underutilized him. He left wrestling in 2014 due to burnout and injuries, tried MMA in UFC, then returned to wrestling in 2021 at AEW. After a controversial AEW departure following backstage altercations, he returned to WWE in 2023 at Survivor Series. His feuds with John Cena, Chris Jericho, and Brock Lesnar are modern classics.'
            },
            {
                'name': 'AJ Styles',
                'real_name': 'Allen Neal Jones',
                'birth_date': date(1977, 6, 2),
                'hometown': 'Jacksonville, North Carolina, USA',
                'height': "5'11\"",
                'weight': '218 lbs',
                'debut_year': 1998,
                'about': 'AJ Styles is a true journeyman who became a WWE Champion. Rising through TNA where he won every major title, and NJPW where he led Bullet Club and held the IWGP Heavyweight Championship, Styles finally debuted in WWE at the 2016 Royal Rumble. His phenomenal ability immediately made him a top star, winning the WWE Championship multiple times. Known for the Phenomenal Forearm, Styles Clash, and Calf Crusher, his ring work remains elite into his mid-40s. Often called "Mr. TNA" for building that promotion, his WWE run proved he belonged among wrestling\'s all-time greats.'
            },
            {
                'name': 'Cody Rhodes',
                'real_name': 'Cody Garrett Runnels',
                'birth_date': date(1985, 6, 30),
                'hometown': 'Charlotte, North Carolina, USA',
                'height': "6'1\"",
                'weight': '220 lbs',
                'debut_year': 2006,
                'about': 'Cody Rhodes\' wrestling journey is one of modern wrestling\'s great stories. The son of "The American Dream" Dusty Rhodes, he left WWE in 2016 to reinvent himself on the independent scene. He was instrumental in founding AEW, serving as an EVP while becoming one of its top stars. After surprisingly leaving AEW in 2022, he returned to WWE at WrestleMania 38. His quest to win the championship his father never held captivated fans, and at WrestleMania XL in 2024, he defeated Roman Reigns to finally "finish the story." Cody\'s blend of old-school presentation and modern wrestling sensibility makes him unique.'
            },
            {
                'name': 'Kazuchika Okada',
                'real_name': 'Kazuchika Okada',
                'birth_date': date(1987, 11, 8),
                'hometown': 'Anjō, Aichi, Japan',
                'height': "6'3\"",
                'weight': '242 lbs',
                'debut_year': 2004,
                'about': 'Kazuchika Okada is the ace of New Japan Pro-Wrestling and one of the greatest wrestlers in history. After a learning excursion to TNA, he returned to NJPW in 2012 and immediately defeated Hiroshi Tanahashi for the IWGP Heavyweight Championship, beginning his era. His matches against Tanahashi, Kenny Omega, and other top stars regularly receive maximum ratings from wrestling journalists. Known for the Rainmaker clothesline, elegant ring work, and big-match aura, Okada held the IWGP Heavyweight Championship for a record 720 consecutive days. In 2024, he debuted in AEW, bringing his "Rain Maker" persona to American audiences.'
            },
            {
                'name': 'Brock Lesnar',
                'real_name': 'Brock Edward Lesnar',
                'birth_date': date(1977, 7, 12),
                'hometown': 'Webster, South Dakota, USA',
                'height': "6'3\"",
                'weight': '286 lbs',
                'debut_year': 2000,
                'about': 'Brock Lesnar is professional wrestling\'s most legitimate athlete. An NCAA Division I National Champion wrestler at the University of Minnesota, he combined freakish athleticism with wrestling ability to become WWE\'s youngest champion at 25. After leaving WWE, he played in the NFL preseason and became UFC Heavyweight Champion, legitimizing his "Beast Incarnate" persona. His return to WWE in 2012 led to dominant runs, including ending The Undertaker\'s WrestleMania streak at WrestleMania XXX. Known for his devastating suplexes and F-5, Lesnar is booked as wrestling\'s ultimate final boss, making every appearance feel special.'
            },
            {
                'name': 'MJF',
                'real_name': 'Maxwell Jacob Friedman',
                'birth_date': date(1996, 3, 15),
                'hometown': 'Plainview, New York, USA',
                'height': "5'11\"",
                'weight': '220 lbs',
                'debut_year': 2015,
                'about': 'MJF is the best young heel in professional wrestling. Known for his articulate, cutting promos and willingness to embrace true villain heat, he has drawn comparisons to a young Ric Flair. After standout work in MLW and on the independent scene, he became one of AEW\'s most featured performers from the company\'s launch. His feuds with Cody Rhodes, Jon Moxley, and CM Punk showcased his talent for long-term storytelling. As AEW World Champion for 287 days, he proved he could carry a company. His character—an arrogant, entitled heel who backs up his talk—resonates because he commits fully to it.'
            },
            {
                'name': 'Rhea Ripley',
                'real_name': 'Demi Bennett',
                'birth_date': date(1996, 10, 11),
                'hometown': 'Adelaide, South Australia, Australia',
                'height': "5'8\"",
                'weight': '137 lbs',
                'debut_year': 2013,
                'about': 'Rhea Ripley has emerged as WWE\'s most dominant female star. The first NXT UK Women\'s Champion, she transitioned to NXT proper where she became the first Australian woman to hold a WWE Championship. After a slow main roster start, she reinvented herself as part of Judgment Day, embracing a heavy metal, gothic aesthetic that fit her naturally. Her WrestleMania 39 victory over Charlotte Flair launched her into the main event. Known as "Mami" and "The Eradicator," her combination of power, athleticism, and charisma make her a legitimate crossover star. Her relationship with Dominik Mysterio adds compelling soap opera elements.'
            },
            {
                'name': 'Bianca Belair',
                'real_name': 'Bianca Nicole Crawford',
                'birth_date': date(1989, 4, 9),
                'hometown': 'Knoxville, Tennessee, USA',
                'height': "5'7\"",
                'weight': '160 lbs',
                'debut_year': 2016,
                'about': 'Bianca Belair is one of the most athletic performers in WWE history. A former collegiate track and field athlete, she brings legitimate athleticism to professional wrestling. Her trademark hair braid serves as both a unique visual and sometimes a weapon. After rising through NXT, she won the Royal Rumble in 2021 and main-evented WrestleMania 37, defeating Sasha Banks in a historic match between two Black women. Known as "The EST of WWE" (Strongest, Fastest, Baddest, etc.), Belair has held the Raw Women\'s Championship multiple times and consistently delivers in big matches with her power moves and personality.'
            },
            {
                'name': 'Hiroshi Tanahashi',
                'real_name': 'Hiroshi Tanahashi',
                'birth_date': date(1976, 11, 13),
                'hometown': 'Ogaki, Gifu, Japan',
                'height': "6'0\"",
                'weight': '229 lbs',
                'debut_year': 1999,
                'about': 'Hiroshi Tanahashi is credited with saving New Japan Pro-Wrestling during its darkest period. Known as "The Ace" and "Once in a Century Talent," he rebuilt NJPW\'s popularity through compelling matches and a charismatic babyface persona. An 8-time IWGP Heavyweight Champion, his feuds with Kazuchika Okada defined modern NJPW. His High Fly Flow and dramatic selling style influenced a generation. Even as he aged, Tanahashi remained a main event presence, embodying fighting spirit. He also crossed over into acting and music in Japan. His legacy as NJPW\'s savior and one of the greatest Japanese wrestlers ever is secure.'
            },
            {
                'name': 'Sami Zayn',
                'real_name': 'Rami Sebei',
                'birth_date': date(1984, 7, 12),
                'hometown': 'Laval, Quebec, Canada',
                'height': "6'1\"",
                'weight': '212 lbs',
                'debut_year': 2002,
                'about': 'Sami Zayn\'s journey from El Generico on the independent scene to main event WWE star is remarkable. In ROH and PWG as the masked El Generico, he had classic matches against Kevin Steen (Owens), Bryan Danielson, and many others. In NXT, his feud with Kevin Owens produced emotional storytelling. On the main roster, he bounced between undercard and featured roles until 2022, when his "Honorary Uce" storyline with The Bloodline became wrestling\'s most compelling narrative. His WrestleMania 40 match against Roman Reigns capped an incredible career arc. The Syrian-Canadian represents wrestling\'s international appeal.'
            },
            {
                'name': 'Kevin Owens',
                'real_name': 'Kevin Yanick Steen',
                'birth_date': date(1984, 5, 7),
                'hometown': 'Marieville, Quebec, Canada',
                'height': "6'0\"",
                'weight': '266 lbs',
                'debut_year': 2000,
                'about': 'Kevin Owens combines brash personality with legitimate in-ring ability. As Kevin Steen in Ring of Honor, he was a top heel and world champion. His NXT debut attacking Sami Zayn after their emotional handshake established him immediately. Owens has held multiple championships in WWE including the Universal and Intercontinental titles. Known for his Pop-up Powerbomb, Stunner, and willingness to take big bumps, he\'s also one of wrestling\'s best talkers. His WrestleMania 38 match against Stone Cold Steve Austin brought Austin out of 19-year retirement, cementing Owens\' place in history. A consummate professional who delivers consistently.'
            },
        ]

        for data in wrestlers_data:
            name = data.pop('name')
            slug = slugify(name)
            # Check by name or slug to avoid duplicates
            wrestler = Wrestler.objects.filter(name__iexact=name).first()
            if not wrestler:
                wrestler = Wrestler.objects.filter(slug=slug).first()

            if wrestler:
                # Update existing wrestler
                for key, value in data.items():
                    if hasattr(wrestler, key) and (getattr(wrestler, key) is None or getattr(wrestler, key) == ''):
                        setattr(wrestler, key, value)
                wrestler.save()
                updated += 1
                self.stdout.write(f'  Updated: {name}')
            else:
                # Create new wrestler
                wrestler = Wrestler.objects.create(name=name, **data)
                created += 1
                self.stdout.write(f'  + Created: {name}')

        self.stdout.write(self.style.SUCCESS(f'\n=== Complete: {created} created, {updated} updated ==='))
