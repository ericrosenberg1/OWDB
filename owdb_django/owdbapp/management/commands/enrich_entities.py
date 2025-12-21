"""
Entity Enrichment Command.

Enriches promotions, championships, venues, video games, podcasts, books, and documentaries
with comprehensive descriptions and metadata.

Usage:
    python manage.py enrich_entities
    python manage.py enrich_entities --type=promotions
    python manage.py enrich_entities --type=championships
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from owdb_django.owdbapp.models import Promotion, Title, Venue, VideoGame, Podcast, Book, Special


class Command(BaseCommand):
    help = 'Enrich all entities with descriptions and metadata'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            help='Enrich specific type (promotions, championships, venues, games, podcasts, books, documentaries)',
            default='all'
        )

    def handle(self, *args, **options):
        entity_type = options.get('type', 'all')

        self.stdout.write(self.style.SUCCESS('\n=== ENTITY ENRICHMENT ===\n'))

        total_updated = 0

        if entity_type in ['all', 'promotions']:
            total_updated += self.enrich_promotions()
        if entity_type in ['all', 'championships']:
            total_updated += self.enrich_championships()
        if entity_type in ['all', 'venues']:
            total_updated += self.enrich_venues()
        if entity_type in ['all', 'games']:
            total_updated += self.enrich_video_games()
        if entity_type in ['all', 'podcasts']:
            total_updated += self.enrich_podcasts()
        if entity_type in ['all', 'books']:
            total_updated += self.enrich_books()
        if entity_type in ['all', 'documentaries']:
            total_updated += self.enrich_documentaries()

        self.stdout.write(self.style.SUCCESS(f'\n=== ENRICHMENT COMPLETE ==='))
        self.stdout.write(f'Total entities updated: {total_updated}')

    def update_promotion(self, name, **kwargs):
        """Update a promotion with enriched data."""
        promo = Promotion.objects.filter(name__iexact=name).first()
        if not promo:
            promo = Promotion.objects.filter(slug=slugify(name)).first()
        if promo:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(promo, field):
                    if not getattr(promo, field, None) or field == 'about':
                        setattr(promo, field, value)
                        updated = True
            if updated:
                promo.save()
                return 1
        return 0

    def update_title(self, name, **kwargs):
        """Update a championship with enriched data."""
        title = Title.objects.filter(name__iexact=name).first()
        if not title:
            title = Title.objects.filter(name__icontains=name).first()
        if title:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(title, field):
                    if not getattr(title, field, None) or field == 'about':
                        setattr(title, field, value)
                        updated = True
            if updated:
                title.save()
                return 1
        return 0

    def update_venue(self, name, **kwargs):
        """Update a venue with enriched data."""
        venue = Venue.objects.filter(name__iexact=name).first()
        if not venue:
            venue = Venue.objects.filter(name__icontains=name).first()
        if venue:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(venue, field):
                    if not getattr(venue, field, None) or field == 'about':
                        setattr(venue, field, value)
                        updated = True
            if updated:
                venue.save()
                return 1
        return 0

    def update_game(self, name, **kwargs):
        """Update a video game with enriched data."""
        game = VideoGame.objects.filter(name__iexact=name).first()
        if not game:
            game = VideoGame.objects.filter(name__icontains=name).first()
        if game:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(game, field):
                    if not getattr(game, field, None) or field == 'about':
                        setattr(game, field, value)
                        updated = True
            if updated:
                game.save()
                return 1
        return 0

    def update_podcast(self, name, **kwargs):
        """Update a podcast with enriched data."""
        pod = Podcast.objects.filter(name__iexact=name).first()
        if not pod:
            pod = Podcast.objects.filter(name__icontains=name).first()
        if pod:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(pod, field):
                    if not getattr(pod, field, None) or field == 'about':
                        setattr(pod, field, value)
                        updated = True
            if updated:
                pod.save()
                return 1
        return 0

    def update_book(self, name, **kwargs):
        """Update a book with enriched data."""
        book = Book.objects.filter(title__iexact=name).first()
        if not book:
            book = Book.objects.filter(title__icontains=name).first()
        if book:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(book, field):
                    if not getattr(book, field, None) or field == 'about':
                        setattr(book, field, value)
                        updated = True
            if updated:
                book.save()
                return 1
        return 0

    def update_documentary(self, title, **kwargs):
        """Update a documentary with enriched data."""
        doc = Special.objects.filter(title__iexact=title).first()
        if not doc:
            doc = Special.objects.filter(title__icontains=title).first()
        if doc:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(doc, field):
                    if not getattr(doc, field, None) or field == 'about':
                        setattr(doc, field, value)
                        updated = True
            if updated:
                doc.save()
                return 1
        return 0

    def enrich_promotions(self):
        """Enrich wrestling promotions."""
        self.stdout.write('--- Enriching Promotions ---')
        updated = 0
        promotions_data = [
            {'name': 'WWE', 'about': 'World Wrestling Entertainment (WWE) is the largest professional wrestling promotion in the world. Founded in 1952 as Capitol Wrestling Corporation, it became WWF in 1979 and WWE in 2002. WWE produces weekly shows Raw, SmackDown, and NXT, along with premium live events including WrestleMania.'},
            {'name': 'AEW', 'about': 'All Elite Wrestling (AEW) was founded in 2019 by Tony Khan and The Elite (Cody Rhodes, Kenny Omega, The Young Bucks). It offers an alternative to WWE with Dynamite, Rampage, and Collision. AEW has partnerships with NJPW and other promotions.'},
            {'name': 'NJPW', 'about': 'New Japan Pro-Wrestling is Japan\'s largest wrestling promotion, founded in 1972 by Antonio Inoki. Known for strong style wrestling and prestigious tournaments like the G1 Climax and Best of the Super Juniors.'},
            {'name': 'Impact Wrestling', 'about': 'Impact Wrestling (formerly TNA) was founded in 2002. Based in Nashville, it has produced stars like AJ Styles, Samoa Joe, and the Knockouts division. Known for the Six Sides of Steel.'},
            {'name': 'ROH', 'about': 'Ring of Honor was founded in 2002 and became known for pure wrestling. It launched careers of CM Punk, Daniel Bryan, and Seth Rollins. Purchased by Tony Khan in 2022.'},
            {'name': 'CMLL', 'about': 'Consejo Mundial de Lucha Libre is the oldest wrestling promotion in the world, founded in 1933. Based in Mexico City\'s Arena Mexico, it is the home of traditional lucha libre.'},
            {'name': 'AAA', 'about': 'Lucha Libre AAA Worldwide was founded in 1992 by Antonio Peña. Known for high-flying lucha libre and the TripleMania event. Has produced stars like Rey Mysterio and Pentagon Jr.'},
            {'name': 'NOAH', 'about': 'Pro Wrestling NOAH was founded in 2000 by Mitsuharu Misawa after leaving AJPW. Home of the GHC Championship and strong style wrestling.'},
            {'name': 'All Japan Pro Wrestling', 'about': 'AJPW was founded in 1972 by Giant Baba. Known for the Four Pillars of Heaven era and traditional strong style wrestling.'},
            {'name': 'Dragon Gate', 'about': 'Dragon Gate was founded in 2004 as a successor to Toryumon. Known for fast-paced, high-flying junior heavyweight action and faction warfare.'},
            {'name': 'DDT', 'about': 'DDT Pro-Wrestling was founded in 1997. Known for comedy wrestling and the Ironman Heavymetalweight Championship defended in unusual locations.'},
            {'name': 'Stardom', 'about': 'World Wonder Ring Stardom is Japan\'s top women\'s wrestling promotion, founded in 2010. Features top joshi talent and intense in-ring action.'},
            {'name': 'TJPW', 'about': 'Tokyo Joshi Pro Wrestling is a DDT subsidiary founded in 2013. Known for developing young female talent with a mix of comedy and serious wrestling.'},
            {'name': 'NWA', 'about': 'The National Wrestling Alliance was founded in 1948 as an alliance of regional promotions. The NWA World Heavyweight Championship is one of wrestling\'s most prestigious titles.'},
            {'name': 'ECW', 'about': 'Extreme Championship Wrestling operated from 1992-2001. Founded by Paul Heyman, it revolutionized wrestling with extreme rules and mature content. Launched careers of Steve Austin, Mick Foley, and many others.'},
            {'name': 'WCW', 'about': 'World Championship Wrestling operated from 1988-2001. Owned by Ted Turner, it featured the nWo and Monday Night Wars. WCW was purchased by WWE in 2001.'},
            {'name': 'GCW', 'about': 'Game Changer Wrestling is an independent promotion founded in 2010. Known for deathmatch wrestling and indie stars. Home of events like The Wrld on GCW.'},
            {'name': 'PWG', 'about': 'Pro Wrestling Guerrilla was founded in 2003 in California. Known for BOLA tournament and launching indie careers. Super Dragon and Excalibur founded it.'},
            {'name': 'MLW', 'about': 'Major League Wrestling was founded in 2002 by Court Bauer. Revived in 2017, it features a sports-based presentation and classic wrestling.'},
            {'name': 'PROGRESS', 'about': 'PROGRESS Wrestling was founded in 2012 in London. Known for intense storylines and launching British wrestling careers.'},
            {'name': 'wXw', 'about': 'Westside Xtreme Wrestling is Germany\'s top promotion, founded in 2000. Known for producing European talent and the 16 Carat Gold tournament.'},
            {'name': 'RevPro', 'about': 'Revolution Pro Wrestling is a British promotion founded in 2012. Has partnerships with NJPW and features top British and international talent.'},
            {'name': 'GLEAT', 'about': 'GLEAT is a Japanese promotion founded in 2020. Features a mix of wrestling styles and presents itself as a modern alternative.'},
            {'name': 'AJPW', 'about': 'All Japan Pro Wrestling was founded by Giant Baba in 1972. Home of the Triple Crown Championship and legendary matches.'},
            {'name': 'WRESTLE-1', 'about': 'WRESTLE-1 operated from 2013-2020. Founded by Keiji Mutoh, it featured a mix of Japanese and international talent.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions')
        return updated

    def enrich_championships(self):
        """Enrich wrestling championships."""
        self.stdout.write('--- Enriching Championships ---')
        updated = 0
        titles_data = [
            {'name': 'WWE Championship', 'about': 'The WWE Championship is WWE\'s most prestigious title, established in 1963 as the WWWF World Heavyweight Championship. Held by legends including Bruno Sammartino, Hulk Hogan, Stone Cold, The Rock, and John Cena.'},
            {'name': 'Universal Championship', 'about': 'The WWE Universal Championship was introduced in 2016 as the top title on Raw. Finn Balor was the first champion. Roman Reigns held it for over 1,300 days.'},
            {'name': 'World Heavyweight Championship', 'about': 'The World Heavyweight Championship has a lineage dating to the NWA and WCW. Revived in WWE in 2023, it is SmackDown\'s top prize.'},
            {'name': 'Intercontinental Championship', 'about': 'The WWE Intercontinental Championship was created in 1979. Often called the workhorse title, it has been held by Randy Savage, Bret Hart, Shawn Michaels, and many future world champions.'},
            {'name': 'United States Championship', 'about': 'The WWE United States Championship has lineage to NWA and WCW. It represents the fighting spirit of American wrestling and has been held by top stars.'},
            {'name': 'AEW World Championship', 'about': 'The AEW World Championship is All Elite Wrestling\'s top prize, introduced in 2019. Chris Jericho was the first champion. It features a unique design.'},
            {'name': 'AEW TNT Championship', 'about': 'The AEW TNT Championship was introduced in 2020 as a workhorse title. Cody Rhodes was the first champion. Features weekly open challenges.'},
            {'name': 'IWGP World Heavyweight Championship', 'about': 'The IWGP World Heavyweight Championship is New Japan\'s top prize, created in 2021 by unifying the Heavyweight and Intercontinental titles.'},
            {'name': 'IWGP Heavyweight Championship', 'about': 'The IWGP Heavyweight Championship was NJPW\'s top title from 1987-2021. Held by Antonio Inoki, Keiji Mutoh, Kazuchika Okada, and other legends.'},
            {'name': 'NWA World Heavyweight Championship', 'about': 'The NWA World Heavyweight Championship is the oldest world title in wrestling, dating to 1948. Held by Lou Thesz, Harley Race, Ric Flair, and other legends.'},
            {'name': 'CMLL World Heavyweight Championship', 'about': 'The CMLL World Heavyweight Championship is lucha libre\'s most prestigious title, established in 1991.'},
            {'name': 'AAA Mega Championship', 'about': 'The AAA Mega Championship is AAA\'s top title, established in 2007. Defended in epic TripleMania matches.'},
            {'name': 'GHC Heavyweight Championship', 'about': 'The GHC Heavyweight Championship is Pro Wrestling NOAH\'s top title, established in 2001. GHC stands for Global Honored Crown.'},
            {'name': 'ROH World Championship', 'about': 'The ROH World Championship was established in 2002. First held by Low Ki. Known for producing future WWE and AEW stars.'},
            {'name': 'Impact World Championship', 'about': 'The Impact World Championship is TNA/Impact\'s top title, established in 2002. Held by AJ Styles, Samoa Joe, and Bobby Lashley.'},
            {'name': 'NXT Championship', 'about': 'The NXT Championship was established in 2012. First held by Seth Rollins. The developmental brand\'s top prize.'},
            {'name': 'WWE Women\'s Championship', 'about': 'The WWE Women\'s Championship represents the top of women\'s wrestling. Lineage dates to 1956 with the Fabulous Moolah.'},
            {'name': 'AEW Women\'s World Championship', 'about': 'The AEW Women\'s World Championship is AEW\'s top women\'s title, introduced in 2019. Riho was the first champion.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships')
        return updated

    def enrich_venues(self):
        """Enrich wrestling venues."""
        self.stdout.write('--- Enriching Venues ---')
        updated = 0
        venues_data = [
            {'name': 'Madison Square Garden', 'about': 'Madison Square Garden in New York City is wrestling\'s most famous arena. Known as The World\'s Most Famous Arena, it has hosted countless legendary matches and events since the early 1900s.'},
            {'name': 'Tokyo Dome', 'about': 'The Tokyo Dome is NJPW\'s home for Wrestle Kingdom. Capacity of 55,000, it has hosted the biggest matches in Japanese wrestling history.'},
            {'name': 'Budokan Hall', 'about': 'Nippon Budokan in Tokyo is a sacred venue for Japanese wrestling. AJPW and NOAH have held major events here since the 1970s.'},
            {'name': 'Arena Mexico', 'about': 'Arena Mexico in Mexico City is the home of CMLL and lucha libre. The Cathedral of Lucha Libre has hosted wrestling since 1956.'},
            {'name': 'Korakuen Hall', 'about': 'Korakuen Hall in Tokyo is the spiritual home of Japanese wrestling. With 2,000 seats, it creates an intimate atmosphere for intense matches.'},
            {'name': 'ECW Arena', 'about': 'The ECW Arena (2300 Arena) in Philadelphia was home to Extreme Championship Wrestling. Fans threw chairs and created electric atmospheres.'},
            {'name': 'Hammerstein Ballroom', 'about': 'The Hammerstein Ballroom in New York City hosted classic ECW, ROH, and indie events. Known for passionate crowds.'},
            {'name': 'Ryogoku Sumo Hall', 'about': 'Ryogoku Kokugikan in Tokyo is primarily a sumo venue but hosts major wrestling events including NJPW G1 Climax finals.'},
            {'name': 'Staples Center', 'about': 'Crypto.com Arena (formerly Staples Center) in Los Angeles has hosted WrestleMania, SummerSlam, and major wrestling events.'},
            {'name': 'AT&T Stadium', 'about': 'AT&T Stadium in Arlington, Texas has hosted multiple WrestleManias with record-breaking attendance of over 100,000 fans.'},
            {'name': 'MetLife Stadium', 'about': 'MetLife Stadium in New Jersey has hosted WrestleMania 29 and 35. One of the largest NFL stadiums in America.'},
            {'name': 'Mercedes-Benz Superdome', 'about': 'The Superdome in New Orleans has hosted multiple WrestleManias. Known for incredible atmospheres.'},
            {'name': 'Wembley Stadium', 'about': 'Wembley Stadium in London hosted AEW All In 2023 and 2024 with record-breaking crowds for British wrestling.'},
            {'name': 'SoFi Stadium', 'about': 'SoFi Stadium in Los Angeles hosted WrestleMania 39 in 2023. State-of-the-art venue with Hollywood presentation.'},
            {'name': 'Osaka-jo Hall', 'about': 'Osaka Castle Hall is a major venue for Japanese wrestling, hosting NJPW, AJPW, and joshi events.'},
        ]
        for data in venues_data:
            name = data.pop('name')
            updated += self.update_venue(name, **data)
        self.stdout.write(f'  Updated {updated} venues')
        return updated

    def enrich_video_games(self):
        """Enrich wrestling video games."""
        self.stdout.write('--- Enriching Video Games ---')
        updated = 0
        games_data = [
            {'name': 'WWE 2K24', 'about': 'WWE 2K24 celebrates 40 years of WrestleMania. Features Showcase mode reliving iconic WrestleMania moments and updated roster.'},
            {'name': 'WWE 2K23', 'about': 'WWE 2K23 features John Cena on the cover and WarGames mode. Continued the revival after 2K22\'s success.'},
            {'name': 'WWE 2K22', 'about': 'WWE 2K22 marked the series return after a two-year hiatus. "It Hits Different" with redesigned gameplay and MyRise mode.'},
            {'name': 'AEW Fight Forever', 'about': 'AEW Fight Forever is AEW\'s first console game, released in 2023. Features arcade-style gameplay reminiscent of No Mercy.'},
            {'name': 'Fire Pro Wrestling World', 'about': 'Fire Pro Wrestling World is the ultimate wrestling sandbox. 2D sprite-based gameplay with incredible customization and Steam Workshop support.'},
            {'name': 'WWF No Mercy', 'about': 'WWF No Mercy for N64 (2000) is considered the greatest wrestling game ever made. AKI engine gameplay is still beloved today.'},
            {'name': 'WWF WrestleMania 2000', 'about': 'WWF WrestleMania 2000 for N64 featured the AKI engine and deep create-a-wrestler mode. A classic of the era.'},
            {'name': 'WWE SmackDown! Here Comes the Pain', 'about': 'SmackDown! Here Comes the Pain (2003) is a PS2 classic. Features Brock Lesnar on cover and incredible season mode.'},
            {'name': 'WWE SmackDown vs. Raw 2006', 'about': 'SVR 2006 introduced the General Manager mode. One of the best PS2 wrestling games with deep career options.'},
            {'name': 'WWE SmackDown vs. Raw 2007', 'about': 'SVR 2007 featured next-gen graphics on PS3 and Xbox 360. Money in the Bank ladder match mode.'},
            {'name': 'WWE All Stars', 'about': 'WWE All Stars (2011) featured exaggerated arcade action with legends vs current stars. Over-the-top moves and colorful presentation.'},
            {'name': 'Virtual Pro Wrestling 2', 'about': 'Virtual Pro Wrestling 2 for N64 (2000) is the Japanese version that inspired No Mercy. Puroresu legends and incredible gameplay.'},
            {'name': 'King of Colosseum II', 'about': 'King of Colosseum II is a Japanese wrestling game featuring NJPW and AJPW rosters. Known for realistic simulation.'},
            {'name': 'WWE 2K19', 'about': 'WWE 2K19 features AJ Styles on the cover. Towers mode and Daniel Bryan\'s 2K Showcase of his career comeback.'},
            {'name': 'WWE 2K18', 'about': 'WWE 2K18 featured Seth Rollins on the cover. Road to Glory online mode and 8-man matches.'},
            {'name': 'WWE 2K16', 'about': 'WWE 2K16 had Stone Cold Steve Austin on the cover. 2K Showcase featured his legendary career.'},
            {'name': 'WWF Attitude', 'about': 'WWF Attitude (1999) was Acclaim\'s game featuring the Attitude Era roster and create modes.'},
            {'name': 'WCW/nWo Revenge', 'about': 'WCW/nWo Revenge (1998) for N64 featured the AKI engine and WCW roster at its peak.'},
            {'name': 'Def Jam Vendetta', 'about': 'Def Jam Vendetta (2003) featured hip-hop stars in wrestling action. AKI engine gameplay with street fighting.'},
            {'name': 'Legends of Wrestling', 'about': 'Legends of Wrestling (2001) featured classic wrestlers from multiple eras in one game.'},
        ]
        for data in games_data:
            name = data.pop('name')
            updated += self.update_game(name, **data)
        self.stdout.write(f'  Updated {updated} video games')
        return updated

    def enrich_podcasts(self):
        """Enrich wrestling podcasts."""
        self.stdout.write('--- Enriching Podcasts ---')
        updated = 0
        podcasts_data = [
            {'name': 'Talk Is Jericho', 'about': 'Talk Is Jericho is hosted by Chris Jericho. Features interviews with wrestling legends, musicians, and celebrities. One of wrestling\'s most popular podcasts.'},
            {'name': 'Something to Wrestle', 'about': 'Something to Wrestle with Bruce Prichard explores WWE history from an insider perspective. Conrad Thompson hosts.'},
            {'name': 'What Happened When', 'about': 'What Happened When features Tony Schiavone discussing WCW history with Conrad Thompson.'},
            {'name': 'Grilling JR', 'about': 'Grilling JR features Jim Ross discussing his legendary career in wrestling. Conrad Thompson hosts.'},
            {'name': 'The Masked Man Show', 'about': 'The Masked Man Show from The Ringer covers weekly wrestling with David Shoemaker.'},
            {'name': 'Wrestling Observer Radio', 'about': 'Wrestling Observer Radio with Dave Meltzer is the longest-running wrestling podcast. News, reviews, and analysis.'},
            {'name': 'Post Wrestling', 'about': 'POST Wrestling with John Pollock and Wai Ting provides in-depth wrestling coverage and reviews.'},
            {'name': 'Busted Open', 'about': 'Busted Open on SiriusXM features wrestling discussion with Dave LaGreca and various hosts.'},
            {'name': 'Cultaholic', 'about': 'Cultaholic provides wrestling news, reviews, and entertainment from former WhatCulture personalities.'},
            {'name': 'Going In Raw', 'about': 'Going In Raw features Steve and Larson\'s wrestling commentary and reactions.'},
            {'name': 'E&C Pod of Awesomeness', 'about': 'E&C Pod of Awesomeness features Edge and Christian discussing wrestling with comedy and nostalgia.'},
            {'name': 'New Day: Feel the Power', 'about': 'Feel the Power is The New Day\'s podcast featuring Big E, Kofi Kingston, and Xavier Woods.'},
            {'name': 'Oral Sessions', 'about': 'Oral Sessions with Renee Paquette features candid conversations with wrestling personalities.'},
            {'name': 'AEW Unrestricted', 'about': 'AEW Unrestricted is AEW\'s official podcast featuring interviews with AEW talent and staff.'},
            {'name': '83 Weeks', 'about': '83 Weeks with Eric Bischoff explores WCW and Nitro history with Conrad Thompson.'},
        ]
        for data in podcasts_data:
            name = data.pop('name')
            updated += self.update_podcast(name, **data)
        self.stdout.write(f'  Updated {updated} podcasts')
        return updated

    def enrich_books(self):
        """Enrich wrestling books."""
        self.stdout.write('--- Enriching Books ---')
        updated = 0
        books_data = [
            {'name': 'Have a Nice Day', 'about': 'Have a Nice Day: A Tale of Blood and Sweatsocks is Mick Foley\'s autobiography. A New York Times bestseller that changed wrestling books forever.'},
            {'name': 'Hitman', 'about': 'Hitman: My Real Life in the Cartoon World of Wrestling is Bret Hart\'s autobiography. Candid look at his legendary career and personal struggles.'},
            {'name': 'The Death of WCW', 'about': 'The Death of WCW by Bryan Alvarez and RD Reynolds chronicles the fall of World Championship Wrestling. Essential wrestling history.'},
            {'name': 'Controversy Creates Cash', 'about': 'Controversy Creates Cash is Eric Bischoff\'s autobiography covering his time running WCW and the Monday Night Wars.'},
            {'name': 'Yes!', 'about': 'Yes!: My Improbable Journey to the Main Event of WrestleMania is Daniel Bryan\'s autobiography about his underdog story.'},
            {'name': 'Undisputed', 'about': 'Undisputed: How to Become the World Champion in 1,372 Easy Steps is Chris Jericho\'s autobiography.'},
            {'name': 'A Lion\'s Tale', 'about': 'A Lion\'s Tale is Chris Jericho\'s first book covering his journey from Winnipeg to WWE stardom.'},
            {'name': 'Crazy Is My Superpower', 'about': 'Crazy Is My Superpower is AJ Lee\'s autobiography about overcoming mental health struggles to become champion.'},
            {'name': 'Squared Circle', 'about': 'The Squared Circle: Life, Death, and Professional Wrestling by David Shoemaker explores wrestling\'s cultural significance.'},
            {'name': 'Foley Is Good', 'about': 'Foley Is Good: And the Real World Is Faker Than Wrestling is Mick Foley\'s second autobiography.'},
            {'name': 'Heartbreak & Triumph', 'about': 'Heartbreak & Triumph is Shawn Michaels\' autobiography covering his career, struggles, and redemption.'},
            {'name': 'Walking a Golden Mile', 'about': 'Walking a Golden Mile is William Regal\'s autobiography about British wrestling and WWE.'},
            {'name': 'Pure Dynamite', 'about': 'Pure Dynamite is the Dynamite Kid\'s controversial autobiography about his career and personal life.'},
            {'name': 'Ric Flair: To Be the Man', 'about': 'To Be the Man is Ric Flair\'s autobiography covering his legendary career and the Four Horsemen.'},
            {'name': 'Accepted', 'about': 'Accepted is Pat Patterson\'s autobiography about being openly gay in wrestling and his creative influence.'},
        ]
        for data in books_data:
            name = data.pop('name')
            updated += self.update_book(name, **data)
        self.stdout.write(f'  Updated {updated} books')
        return updated

    def enrich_documentaries(self):
        """Enrich wrestling documentaries."""
        self.stdout.write('--- Enriching Documentaries ---')
        updated = 0
        docs_data = [
            {'name': 'Beyond the Mat', 'about': 'Beyond the Mat (1999) is Barry Blaustein\'s documentary featuring Mick Foley, Jake Roberts, and Terry Funk. Revealed the real side of wrestling.'},
            {'name': 'Wrestling with Shadows', 'about': 'Wrestling with Shadows (1998) documented Bret Hart\'s final year in WWF including the Montreal Screwjob.'},
            {'name': 'The Resurrection of Jake the Snake', 'about': 'The Resurrection of Jake the Snake Roberts (2015) follows Jake Roberts\' recovery with help from DDP Yoga.'},
            {'name': 'Dark Side of the Ring', 'about': 'Dark Side of the Ring is Vice TV\'s documentary series exploring tragic stories in wrestling history.'},
            {'name': 'Andre the Giant', 'about': 'Andre the Giant (2018) is HBO\'s documentary about the legendary Eighth Wonder of the World.'},
            {'name': 'The Last Ride', 'about': 'The Last Ride (2020) is WWE Network\'s documentary series following The Undertaker\'s final years.'},
            {'name': 'Young Rock', 'about': 'Young Rock is NBC\'s biographical comedy series about Dwayne "The Rock" Johnson\'s life and wrestling family.'},
            {'name': 'Hitman Hart', 'about': 'Hitman Hart: Wrestling with Shadows chronicles Bret Hart\'s departure from WWF and the Montreal Screwjob.'},
            {'name': 'You Cannot Kill David Arquette', 'about': 'You Cannot Kill David Arquette (2020) follows the actor\'s return to wrestling to earn respect.'},
            {'name': 'Bloodsport', 'about': 'Bloodsport: ECW\'s Most Violent Matches explores Extreme Championship Wrestling\'s hardcore legacy.'},
            {'name': 'A&E Biography', 'about': 'A&E Biography: WWE Legends features documentary profiles of wrestling\'s greatest stars.'},
            {'name': 'Iron Claw', 'about': 'The Iron Claw (2023) is a dramatic film about the Von Erich wrestling family tragedy.'},
            {'name': 'Wrestlers', 'about': 'Wrestlers (2023) is Netflix\'s reality series following Ohio Valley Wrestling.'},
            {'name': '30 for 30: Nature Boy', 'about': 'Nature Boy (2017) is ESPN\'s 30 for 30 documentary about Ric Flair\'s legendary career and personal life.'},
            {'name': 'Kayfabe: A Fake Real Movie About A Fake Real Sport', 'about': 'Kayfabe explores the art of maintaining wrestling\'s illusion and its evolution.'},
        ]
        for data in docs_data:
            title = data.pop('name')
            updated += self.update_documentary(title, **data)
        self.stdout.write(f'  Updated {updated} documentaries')
        return updated
