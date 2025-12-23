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
from owdb_django.owdbapp.models import Promotion, Title, Venue, VideoGame, Podcast, Book, Special, Stable


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
            total_updated += self.enrich_promotions_batch_2()
            total_updated += self.enrich_promotions_batch_3()
            total_updated += self.enrich_promotions_batch_4()
            total_updated += self.enrich_promotions_batch_5()
            total_updated += self.enrich_promotions_batch_6()
            total_updated += self.enrich_promotions_batch_7()
            total_updated += self.enrich_promotions_batch_8()
            total_updated += self.enrich_promotions_batch_9()
            total_updated += self.enrich_promotions_batch_10()
            total_updated += self.enrich_promotions_batch_11()
            total_updated += self.enrich_promotions_batch_12()
            total_updated += self.enrich_promotions_batch_13()
            total_updated += self.enrich_promotions_batch_14()
            total_updated += self.enrich_promotions_batch_15()
            total_updated += self.enrich_promotions_batch_16()
            total_updated += self.enrich_promotions_batch_17()
            total_updated += self.enrich_promotions_batch_18()
            total_updated += self.enrich_promotions_batch_19()
            total_updated += self.enrich_promotions_batch_20()
            total_updated += self.enrich_promotions_batch_21()
            total_updated += self.enrich_promotions_batch_22()
            total_updated += self.enrich_promotions_batch_23()
        if entity_type in ['all', 'championships']:
            total_updated += self.enrich_championships()
            total_updated += self.enrich_championships_batch_2()
            total_updated += self.enrich_championships_batch_3()
            total_updated += self.enrich_championships_batch_4()
            total_updated += self.enrich_championships_batch_5()
            total_updated += self.enrich_championships_batch_6()
            total_updated += self.enrich_championships_batch_7()
            total_updated += self.enrich_championships_batch_8()
            total_updated += self.enrich_championships_batch_9()
            total_updated += self.enrich_championships_batch_10()
            total_updated += self.enrich_championships_batch_11()
            total_updated += self.enrich_championships_batch_12()
        if entity_type in ['all', 'venues']:
            total_updated += self.enrich_venues()
        if entity_type in ['all', 'games']:
            total_updated += self.enrich_video_games()
            total_updated += self.enrich_video_games_batch_2()
            total_updated += self.enrich_video_games_batch_3()
            total_updated += self.enrich_video_games_batch_4()
        if entity_type in ['all', 'podcasts']:
            total_updated += self.enrich_podcasts()
            total_updated += self.enrich_podcasts_batch_2()
            total_updated += self.enrich_podcasts_batch_3()
            total_updated += self.enrich_podcasts_batch_4()
        if entity_type in ['all', 'books']:
            total_updated += self.enrich_books()
            total_updated += self.enrich_books_batch_2()
            total_updated += self.enrich_books_batch_3()
        if entity_type in ['all', 'documentaries']:
            total_updated += self.enrich_documentaries()
        if entity_type in ['all', 'stables']:
            total_updated += self.enrich_stables()
            total_updated += self.enrich_stables_batch_2()
            total_updated += self.enrich_stables_batch_3()

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

    def enrich_promotions_batch_2(self):
        """Enrich wrestling promotions batch 2."""
        self.stdout.write('--- Enriching Promotions Batch 2 ---')
        updated = 0
        promotions_data = [
            {'name': 'AWA', 'about': 'The American Wrestling Association was founded by Verne Gagne in 1960. Based in Minneapolis, it was one of the big three territories alongside WWF and NWA. Produced stars like Hulk Hogan, Curt Hennig, and the Road Warriors.'},
            {'name': 'Extreme Championship Wrestling', 'about': 'ECW revolutionized professional wrestling from 1992-2001. Paul Heyman created an alternative to mainstream wrestling with hardcore matches, adult content, and launching careers of Steve Austin, Mick Foley, and Rey Mysterio.'},
            {'name': 'Championship Wrestling from Florida', 'about': 'CWF was one of the most influential NWA territories, operating from 1961-1987. Promoted by Eddie Graham, it produced Dusty Rhodes, Jack Brisco, and countless legends.'},
            {'name': 'Continental Wrestling Association', 'about': 'The CWA was the Memphis territory operated by Jerry Jarrett and Jerry Lawler. Known for wild angles and some of the best promos in wrestling history.'},
            {'name': 'Big Japan Pro Wrestling', 'about': 'BJW was founded in 1995 and is known for deathmatch wrestling. Features both strong style and extreme stipulation matches. Home of the Deathmatch King title.'},
            {'name': 'Combat Zone Wrestling', 'about': 'CZW was founded in 1999 in New Jersey. Known for ultraviolent deathmatches and the annual Tournament of Death. Launched careers of many hardcore stars.'},
            {'name': 'Chikara', 'about': 'Chikara was a Philadelphia-based promotion founded in 2002. Known for comic book style wrestling and unique characters. Season-based storytelling format.'},
            {'name': 'Evolve', 'about': 'Evolve Wrestling operated from 2010-2020. Run by Gabe Sapolsky, it served as an unofficial WWE developmental territory. Produced stars like Matt Riddle.'},
            {'name': 'Florida Championship Wrestling', 'about': 'FCW was WWE\'s developmental territory from 2007-2012 before becoming NXT. Based in Tampa, it trained future stars like Roman Reigns and Seth Rollins.'},
            {'name': 'Frontier Martial-Arts Wrestling', 'about': 'FMW was founded by Atsushi Onita in 1989. Pioneered exploding barbed wire matches and extreme wrestling in Japan. Influenced ECW.'},
            {'name': 'Gaea Japan', 'about': 'Gaea Japan was a women\'s wrestling promotion founded by Chigusa Nagayo in 1995. Known for serious athletic women\'s wrestling until closing in 2005.'},
            {'name': 'Gorgeous Ladies of Wrestling', 'about': 'GLOW operated from 1986-1990. Featured women wrestlers in a syndicated TV format. Recently depicted in Netflix series. Launched careers of Madusa and others.'},
            {'name': 'Global Force Wrestling', 'about': 'GFW was founded by Jeff Jarrett in 2014. Briefly merged with Impact Wrestling before Jarrett returned to WWE as a Hall of Famer.'},
            {'name': 'House of Hardcore', 'about': 'House of Hardcore was founded by Tommy Dreamer in 2012. Celebrates the legacy of ECW with hardcore wrestling shows.'},
            {'name': 'IWA Mid-South', 'about': 'IWA Mid-South was founded in 1996 in Indiana. Known for the King of the Deathmatch tournament. Produced CM Punk and many hardcore stars.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 2')
        return updated

    def enrich_promotions_batch_3(self):
        """Enrich wrestling promotions batch 3."""
        self.stdout.write('--- Enriching Promotions Batch 3 ---')
        updated = 0
        promotions_data = [
            {'name': 'World Championship Wrestling', 'about': 'WCW operated from 1988-2001 under Ted Turner\'s ownership. Home of the nWo, Monday Nitro, and the Monday Night Wars. Purchased by WWE in 2001 for $4.2 million.'},
            {'name': 'World Wrestling Federation', 'about': 'The WWF was the dominant American promotion from 1979-2002. Created WrestleMania, the Attitude Era, and global wrestling stars. Changed name to WWE due to legal issues.'},
            {'name': 'Smoky Mountain Wrestling', 'about': 'SMW was founded by Jim Cornette in 1991. Operated in Tennessee and Kentucky with old-school NWA style. Closed in 1995 but influential in developing talent.'},
            {'name': 'Ohio Valley Wrestling', 'about': 'OVW was WWE\'s developmental territory from 2000-2008. Based in Louisville, Kentucky, it trained John Cena, Brock Lesnar, and Randy Orton.'},
            {'name': 'Deep South Wrestling', 'about': 'DSW was WWE\'s developmental territory from 2005-2007. Based in Georgia, it briefly trained WWE prospects before closing.'},
            {'name': 'Frontier Wrestling Alliance', 'about': 'FWA was a British promotion from 1993-2007. Known for developing UK talent like Jonny Storm and helped establish British wrestling scene.'},
            {'name': 'International Championship Wrestling', 'about': 'ICW was founded in Scotland in 2006. Known for aggressive, adult-oriented wrestling. Helped launch the British wrestling boom.'},
            {'name': 'What Culture Pro Wrestling', 'about': 'WCPW operated from 2016-2018. Founded by wrestling media site WhatCulture. Became Defiant Wrestling before closing.'},
            {'name': 'Lucha Underground', 'about': 'Lucha Underground operated from 2014-2018. Cinematic wrestling series on El Rey Network. Featured unique characters like Pentagon Jr. and Prince Puma.'},
            {'name': 'World of Sport Wrestling', 'about': 'World of Sport was British TV wrestling from 1965-1988. Produced Big Daddy, Giant Haystacks, and unique British style. Briefly revived in 2018.'},
            {'name': "All Japan Women's Pro-Wrestling", 'about': 'AJW operated from 1968-2005. The premier women\'s wrestling promotion, producing legends like Jaguar Yokota, Dump Matsumoto, and the Crush Gals.'},
            {'name': 'Stampede Wrestling', 'about': 'Stampede Wrestling was the Hart family promotion in Calgary from 1948-1989. Stu Hart trained legendary wrestlers including his sons Bret and Owen.'},
            {'name': 'Mid-South Wrestling', 'about': 'Mid-South Wrestling was Bill Watts\' promotion from 1979-1987. Based in Louisiana, it was known for realistic, hard-hitting wrestling.'},
            {'name': 'World Class Championship Wrestling', 'about': 'WCCW was the Von Erich family promotion in Dallas from 1966-1988. Produced legendary feuds and the tragic Von Erich story.'},
            {'name': 'Puerto Rico World Wrestling Council', 'about': 'WWC has operated in Puerto Rico since 1973. Founded by Carlos Colon, it has been home to legendary bloodfeuds and Caribbean wrestling.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 3')
        return updated

    def enrich_promotions_batch_4(self):
        """Enrich wrestling promotions batch 4 - Japanese and international."""
        self.stdout.write('--- Enriching Promotions Batch 4 ---')
        updated = 0
        promotions_data = [
            {'name': 'NJPW', 'about': 'New Japan Pro-Wrestling is Japan\'s largest promotion, founded by Antonio Inoki in 1972. Known for strong style wrestling, the G1 Climax tournament, and stars like Okada, Tanahashi, and Naito. Wrestle Kingdom is their biggest annual event.'},
            {'name': 'All Japan Pro Wrestling', 'about': 'AJPW was founded by Giant Baba in 1972. Home of the Four Pillars of Heaven (Misawa, Kawada, Kobashi, Taue) and legendary Triple Crown Championship matches.'},
            {'name': 'Pro Wrestling NOAH', 'about': 'NOAH was founded by Mitsuharu Misawa in 2000 after leaving AJPW. Known for the GHC Championship and carrying on the fighting spirit of King\'s Road style wrestling.'},
            {'name': 'Dragon Gate', 'about': 'Dragon Gate was founded in 2004, evolving from Toryumon. Known for fast-paced junior heavyweight wrestling and complex faction warfare.'},
            {'name': 'DDT Pro-Wrestling', 'about': 'DDT was founded in 1997 by Sanshiro Takagi. Known for comedy wrestling, unique stipulations, and the Ironman Heavymetalweight Championship defended anywhere.'},
            {'name': 'Stardom', 'about': 'World Wonder Ring Stardom is Japan\'s premier women\'s promotion, founded in 2010 by Rossy Ogawa. Features top joshi talent like Mayu Iwatani and Utami Hayashishita.'},
            {'name': 'Tokyo Joshi Pro Wrestling', 'about': 'TJPW is a DDT subsidiary founded in 2013. Known for mixing comedy with serious wrestling and developing talent like Miyu Yamashita and Yuka Sakazaki.'},
            {'name': 'Ice Ribbon', 'about': 'Ice Ribbon was founded in 2006 as a joshi promotion. Known for developing young female talent and unique match stipulations.'},
            {'name': 'ZERO1', 'about': 'Pro Wrestling ZERO1 was founded by Shinya Hashimoto in 2001. Known for strong style and international partnerships with NWA.'},
            {'name': 'FREEDOMS', 'about': 'Pro Wrestling FREEDOMS was founded in 2009. Known for deathmatch wrestling and hardcore stipulations in the Japanese circuit.'},
            {'name': 'Gatoh Move', 'about': 'Gatoh Move/ChocoPro is Emi Sakura\'s promotion known for apartment wrestling and unique presentation on YouTube.'},
            {'name': 'WAVE', 'about': 'Pro Wrestling WAVE was founded in 2007. A joshi promotion known for competitive women\'s wrestling matches.'},
            {'name': 'SEAdLINNNG', 'about': 'SEAdLINNNG was founded by Nanae Takahashi in 2015. A joshi promotion featuring hard-hitting women\'s wrestling.'},
            {'name': 'WRESTLE-1', 'about': 'WRESTLE-1 operated from 2013-2020. Founded by Keiji Mutoh after leaving AJPW, it featured a mix of veterans and young talent.'},
            {'name': 'Michinoku Pro Wrestling', 'about': 'Michinoku Pro was founded in 1993 by The Great Sasuke. Known for high-flying junior heavyweight action and producing Taka Michinoku.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 4')
        return updated

    def enrich_promotions_batch_5(self):
        """Enrich wrestling promotions batch 5 - Mexican and Latin American."""
        self.stdout.write('--- Enriching Promotions Batch 5 ---')
        updated = 0
        promotions_data = [
            {'name': 'CMLL', 'about': 'Consejo Mundial de Lucha Libre is the oldest wrestling promotion in the world, founded in 1933 in Mexico City. Home of Arena Mexico and traditional lucha libre.'},
            {'name': 'AAA', 'about': 'Lucha Libre AAA Worldwide was founded in 1992 by Antonio Peña. Known for TripleMania and producing international stars like Rey Mysterio, Eddie Guerrero, and Pentagon Jr.'},
            {'name': 'Lucha Underground', 'about': 'Lucha Underground was a cinematic wrestling series from 2014-2018. Featured The Temple, unique characters, and launched Pentagon Dark and Prince Puma.'},
            {'name': 'Crash Lucha Libre', 'about': 'The Crash Lucha Libre was founded in 2014 in Tijuana. Known for mixing lucha libre with American indie style wrestling.'},
            {'name': 'International Wrestling League', 'about': 'IWL (Liga Internacional de Lucha Libre) promoted lucha libre events in Mexico during the 1990s and 2000s.'},
            {'name': 'IWRG', 'about': 'International Wrestling Revolution Group was founded in 1996 in Mexico. Known for hardcore lucha libre and developing young talent.'},
            {'name': 'DTU', 'about': 'Desastre Total Ultraviolento is a Mexican promotion known for extreme matches and deathmatch wrestling.'},
            {'name': 'Promociones Mora', 'about': 'Promociones Mora promotes lucha libre events throughout Mexico, featuring traditional lucha format.'},
            {'name': 'International Wrestling Association', 'about': 'IWA in Puerto Rico has promoted wrestling since 1994. Known for hardcore wrestling and developing Caribbean talent.'},
            {'name': 'WWL', 'about': 'World Wrestling League operated in Puerto Rico as an alternative to WWC with touring stars.'},
            {'name': 'CMLL Guadalajara', 'about': 'CMLL\'s Guadalajara branch promotes lucha libre at Arena Coliseo Guadalajara.'},
            {'name': 'ELITE AAA', 'about': 'ELITE is AAA\'s secondary promotion, featuring lucha libre throughout Mexican venues.'},
            {'name': 'Full Latinoamericana', 'about': 'Full Latinoamericana promotes independent lucha libre events featuring Mexican talent.'},
            {'name': 'LLUSA', 'about': 'Lucha Libre USA was a short-lived American promotion featuring lucha libre style wrestling.'},
            {'name': 'Lucha Libre Boom', 'about': 'Lucha Libre Boom promotes independent lucha events in Mexico featuring rising talent.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 5')
        return updated

    def enrich_promotions_batch_6(self):
        """Enrich wrestling promotions batch 6 - British and European."""
        self.stdout.write('--- Enriching Promotions Batch 6 ---')
        updated = 0
        promotions_data = [
            {'name': 'PROGRESS Wrestling', 'about': 'PROGRESS was founded in 2012 in London. Known for intense storylines and launching British wrestling stars like Will Ospreay and Pete Dunne.'},
            {'name': 'Revolution Pro Wrestling', 'about': 'RevPro was founded in 2012 in the UK. Has partnerships with NJPW and features top British and international talent.'},
            {'name': 'ICW', 'about': 'Insane Championship Wrestling was founded in Scotland in 2006. Known for aggressive, adult-oriented wrestling and passionate crowds.'},
            {'name': 'wXw', 'about': 'Westside Xtreme Wrestling is Germany\'s top promotion, founded in 2000. Known for the 16 Carat Gold tournament.'},
            {'name': 'WCPW', 'about': 'What Culture Pro Wrestling operated from 2016-2018. Founded by wrestling media site WhatCulture, became Defiant Wrestling.'},
            {'name': 'Defiant Wrestling', 'about': 'Defiant Wrestling evolved from WCPW. Featured British and international talent before closing.'},
            {'name': 'Fight Club Pro', 'about': 'Fight Club Pro was a British promotion known for hosting international indie stars and wild matches.'},
            {'name': 'OTT', 'about': 'Over The Top Wrestling is Ireland\'s top promotion, founded in 2014. Features Irish and international talent.'},
            {'name': 'TNT Extreme Wrestling', 'about': 'TNT Extreme Wrestling is a British promotion known for hardcore and deathmatch wrestling.'},
            {'name': 'Attack Pro', 'about': 'Attack! Pro Wrestling promotes events in Wales featuring British indie talent and unique presentations.'},
            {'name': 'Preston City Wrestling', 'about': 'PCW is a British promotion based in Preston, known for quality indie wrestling shows.'},
            {'name': 'IPW UK', 'about': 'International Pro Wrestling UK promotes events throughout Britain featuring local and touring talent.'},
            {'name': 'World of Sport Wrestling', 'about': 'World of Sport was British TV wrestling from 1965-1988. Featured Big Daddy, Giant Haystacks, and unique British catch style.'},
            {'name': 'Catch Wrestling World', 'about': 'Catch Wrestling World promotes traditional British catch wrestling style shows.'},
            {'name': 'Triple W', 'about': 'WWW (World Wide Wrestling) is a French promotion founded in 2014. Features European indie talent.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 6')
        return updated

    def enrich_championships_batch_2(self):
        """Enrich wrestling championships batch 2."""
        self.stdout.write('--- Enriching Championships Batch 2 ---')
        updated = 0
        titles_data = [
            {'name': 'WWE Tag Team Championship', 'about': 'The WWE Tag Team Championship is one of wrestling\'s most prestigious tag titles. Lineage includes legendary teams like The Hart Foundation, Road Warriors, and New Day.'},
            {'name': 'World Tag Team Championship', 'about': 'The World Tag Team Championship was the Raw brand tag title from 2002-2010. Held by The Dudley Boyz, Edge and Christian, and other legendary teams.'},
            {'name': 'Raw Tag Team Championship', 'about': 'The Raw Tag Team Championship is the primary tag title on Raw since 2016. The New Day, Usos, and FTR have held the gold.'},
            {'name': 'SmackDown Tag Team Championship', 'about': 'The SmackDown Tag Team Championship is the SmackDown brand tag title since 2016. Features blue straps and unique design.'},
            {'name': 'NXT Tag Team Championship', 'about': 'The NXT Tag Team Championship was created in 2013. Held by The Ascension, American Alpha, and The Undisputed ERA.'},
            {'name': 'AEW World Tag Team Championship', 'about': 'The AEW World Tag Team Championship was introduced in 2019. SCU were first champions. Features teams from around the world.'},
            {'name': 'IWGP Tag Team Championship', 'about': 'The IWGP Tag Team Championship is NJPW\'s premier tag title. Held by legendary teams like Tencozy and CHAOS.'},
            {'name': 'NEVER Openweight Championship', 'about': 'The NEVER Openweight Championship is an NJPW title emphasizing fighting spirit. Tomohiro Ishii and Katsuyori Shibata have defined the title.'},
            {'name': 'IWGP Junior Heavyweight Championship', 'about': 'The IWGP Junior Heavyweight Championship is NJPW\'s top junior title. Legendary holders include Jushin Liger, Tiger Mask, and Hiromu Takahashi.'},
            {'name': 'Triple Crown Heavyweight Championship', 'about': 'The Triple Crown is AJPW\'s unified world title since 1989. Combining the PWF, United National, and International titles.'},
            {'name': 'GHC Tag Team Championship', 'about': 'The GHC Tag Team Championship is Pro Wrestling NOAH\'s tag title. Part of the Global Honored Crown title system.'},
            {'name': 'Open the Dream Gate Championship', 'about': 'The Open the Dream Gate is Dragon Gate\'s top title. Named after the company\'s philosophy of opening the gate to dreams.'},
            {'name': 'World Wonder Ring Stardom Championship', 'about': 'The World of Stardom Championship is Stardom\'s top title. Held by Mayu Iwatani and Giulia.'},
            {'name': 'TNA World Heavyweight Championship', 'about': 'The TNA World Heavyweight Championship was Impact\'s top title from 2007-2017. Held by Kurt Angle and AJ Styles.'},
            {'name': 'TNA X Division Championship', 'about': 'The X Division Championship is Impact\'s high-flying title. "It\'s not about weight limits, it\'s about no limits."'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 2')
        return updated

    def enrich_championships_batch_3(self):
        """Enrich wrestling championships batch 3."""
        self.stdout.write('--- Enriching Championships Batch 3 ---')
        updated = 0
        titles_data = [
            {'name': 'WWE 24/7 Championship', 'about': 'The WWE 24/7 Championship was introduced in 2019. Can be defended anytime, anywhere. Known for comedic title changes.'},
            {'name': 'Million Dollar Championship', 'about': 'The Million Dollar Championship was created by Ted DiBiase in 1989. A custom title that has been revived periodically.'},
            {'name': 'Hardcore Championship', 'about': 'The WWE Hardcore Championship was defended under 24/7 rules from 1998-2002. Held by Mick Foley, Crash Holly, and many others.'},
            {'name': 'European Championship', 'about': 'The WWE European Championship was active from 1997-2002. Shawn Michaels was first champion. Prestigious mid-card title.'},
            {'name': 'Light Heavyweight Championship', 'about': 'The WWE Light Heavyweight Championship was for cruiserweight stars from 1981-2001. Held by Taka Michinoku and Dean Malenko.'},
            {'name': 'Cruiserweight Championship', 'about': 'The WWE Cruiserweight Championship featured high-flyers with weight limits. Multiple versions throughout WWE history.'},
            {'name': 'AEW International Championship', 'about': 'The AEW International Championship (formerly All-Atlantic) is AEW\'s secondary title. Orange Cassidy and Will Ospreay have held it.'},
            {'name': 'AEW TBS Championship', 'about': 'The AEW TBS Championship is AEW\'s secondary women\'s title. Jade Cargill was dominant first champion.'},
            {'name': 'FTW Championship', 'about': 'The FTW Championship was created by Taz in ECW. Revived in AEW as a rogue title.'},
            {'name': 'ROH World Television Championship', 'about': 'The ROH TV Championship is Ring of Honor\'s workhorse title. Defended regularly on ROH programming.'},
            {'name': 'ROH World Tag Team Championship', 'about': 'The ROH World Tag Team Championship is Ring of Honor\'s tag title. Teams like The Briscoes have defined it.'},
            {'name': 'ECW World Heavyweight Championship', 'about': 'The ECW World Heavyweight Championship was ECW\'s top title from 1992-2001. Held by Shane Douglas, Sandman, and RVD.'},
            {'name': 'ECW Television Championship', 'about': 'The ECW TV Championship was ECW\'s workhorse title. 2 Cold Scorpio and Rob Van Dam had legendary reigns.'},
            {'name': 'ECW Tag Team Championship', 'about': 'The ECW Tag Team Championship was held by legendary teams like The Dudley Boyz, The Eliminators, and RVD/Sabu.'},
            {'name': 'WCW World Heavyweight Championship', 'about': 'The WCW World Heavyweight Championship was WCW\'s top title. Ric Flair, Goldberg, and Booker T are legendary champions.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 3')
        return updated

    def enrich_podcasts_batch_2(self):
        """Enrich wrestling podcasts batch 2."""
        self.stdout.write('--- Enriching Podcasts Batch 2 ---')
        updated = 0
        podcasts_data = [
            {'name': 'Arn', 'about': 'The Arn Show is Arn Anderson\'s podcast with Conrad Thompson. Discusses his legendary career with the Four Horsemen, WCW, and WWE.'},
            {'name': 'The Kurt Angle Show', 'about': 'The Kurt Angle Show features the Olympic gold medalist discussing his career in WWE, TNA, and amateur wrestling.'},
            {'name': 'Foley Is Pod', 'about': 'Foley Is Pod features Mick Foley discussing his hardcore legend career, writing, and life beyond wrestling.'},
            {'name': 'The Hall of Fame', 'about': 'The Hall of Fame podcast features Booker T discussing his career from Harlem Heat to WWE Champion.'},
            {'name': 'X-Pac 12360', 'about': 'X-Pac 12360 features Sean Waltman discussing D-Generation X, nWo, and his cruiserweight career.'},
            {'name': 'Insight with Chris Van Vliet', 'about': 'Insight with Chris Van Vliet features in-depth interviews with wrestling stars and celebrities.'},
            {'name': 'Wrestlenomics', 'about': 'Wrestlenomics covers the business side of wrestling with Brandon Thurston. Features ratings analysis and financial news.'},
            {'name': 'Fightful', 'about': 'Fightful podcasts feature Sean Ross Sapp with wrestling news, interviews, and analysis.'},
            {'name': 'Going Broadway', 'about': 'Going Broadway is SRS and Carmine\'s wrestling discussion show on Fightful.'},
            {'name': 'Busted Open Radio', 'about': 'Busted Open Radio on SiriusXM features Dave LaGreca, Mickie James, and guests discussing wrestling news.'},
            {'name': 'The Extreme Life of Matt Hardy', 'about': 'The Extreme Life of Matt Hardy chronicles his career from the Hardy Boyz to current day.'},
            {'name': 'The Jim Cornette Experience', 'about': 'The Jim Cornette Experience features the controversial manager\'s opinions on wrestling past and present.'},
            {'name': 'Drive Thru', 'about': 'Jim Cornette\'s Drive-Thru features listener questions and wrestling discussion.'},
            {'name': 'My World with Jeff Jarrett', 'about': 'My World features Jeff Jarrett discussing his career, founding TNA, and WWE Hall of Fame career.'},
            {'name': 'Two Man Power Trip of Wrestling', 'about': 'Two Man Power Trip features interviews with wrestling legends and current stars.'},
            {'name': 'The Sessions with Renee Paquette', 'about': 'The Sessions features Renee Paquette with candid wrestling interviews and conversations.'},
            {'name': 'Notsam Wrestling', 'about': 'NotSam Wrestling features Sam Roberts discussing WWE and wrestling topics.'},
            {'name': 'Cafe de Rene', 'about': 'Cafe de Rene with Rene Dupree discusses his career in WWE and Japan.'},
            {'name': 'The Mark Henry Show', 'about': 'The Mark Henry Show features the World\'s Strongest Man discussing his WWE career.'},
            {'name': 'The Bump', 'about': 'WWE\'s The Bump is the official WWE talk show featuring interviews with current WWE Superstars.'},
        ]
        for data in podcasts_data:
            name = data.pop('name')
            updated += self.update_podcast(name, **data)
        self.stdout.write(f'  Updated {updated} podcasts batch 2')
        return updated

    def update_stable(self, name, **kwargs):
        """Update a stable with enriched data."""
        stable = Stable.objects.filter(name__iexact=name).first()
        if not stable:
            stable = Stable.objects.filter(name__icontains=name).first()
        if stable:
            updated = False
            for field, value in kwargs.items():
                if value and hasattr(stable, field):
                    if not getattr(stable, field, None) or field == 'about':
                        setattr(stable, field, value)
                        updated = True
            if updated:
                stable.save()
                return 1
        return 0

    def enrich_stables(self):
        """Enrich wrestling stables and factions."""
        self.stdout.write('--- Enriching Stables ---')
        updated = 0
        stables_data = [
            {'name': 'nWo', 'about': 'The New World Order (nWo) was formed in 1996 when Hulk Hogan turned heel and joined Scott Hall and Kevin Nash. The nWo revolutionized wrestling and launched the Monday Night Wars. Their black and white colors and "Too Sweet" hand gesture became iconic.'},
            {'name': 'D-Generation X', 'about': 'D-Generation X (DX) was formed in 1997 by Shawn Michaels and Triple H. Known for rebellious attitude, crotch chops, and "Suck It" catchphrase. Members included Chyna, X-Pac, Road Dogg, and Billy Gunn.'},
            {'name': 'The Four Horsemen', 'about': 'The Four Horsemen were wrestling\'s most prestigious faction, formed by Ric Flair in 1985. Members included Arn Anderson, Tully Blanchard, and Ole Anderson. Known for limousines, fine suits, and being the dirtiest players in the game.'},
            {'name': 'Evolution', 'about': 'Evolution was Triple H\'s faction in WWE from 2003-2005. Featured Ric Flair, Randy Orton, and Batista. Represented past, present, and future of WWE.'},
            {'name': 'The Shield', 'about': 'The Shield debuted in 2012 with Roman Reigns, Seth Rollins, and Dean Ambrose. Their tactical gear, fist bump, and entrance through the crowd made them one of WWE\'s most dominant factions.'},
            {'name': 'Bullet Club', 'about': 'Bullet Club was formed in 2013 by Finn Balor (Prince Devitt) in NJPW. Members included AJ Styles, Kenny Omega, and The Young Bucks. Their merchandise and influence revolutionized wrestling factions.'},
            {'name': 'The Nexus', 'about': 'The Nexus was a faction of NXT Season 1 rookies who invaded Raw in 2010. Led by Wade Barrett, they terrorized WWE before being dismantled by John Cena.'},
            {'name': 'The Wyatt Family', 'about': 'The Wyatt Family was Bray Wyatt\'s cult-like faction. With Luke Harper, Erick Rowan, and later Braun Strowman, they terrorized WWE with eerie promos and swamp-themed entrance.'},
            {'name': 'The Bloodline', 'about': 'The Bloodline is Roman Reigns\' family faction. With Jimmy and Jey Uso, Solo Sikoa, and Paul Heyman, they dominated WWE for years. "Acknowledge Me" became Roman\'s signature.'},
            {'name': 'The Elite', 'about': 'The Elite is The Young Bucks, Kenny Omega, Cody Rhodes (formerly), and Hangman Adam Page. They helped found AEW and are known for Being The Elite web series.'},
            {'name': 'Undisputed Era', 'about': 'The Undisputed Era was Adam Cole, Kyle O\'Reilly, Bobby Fish, and Roderick Strong in NXT. They dominated NXT, holding all the gold simultaneously.'},
            {'name': 'The Inner Circle', 'about': 'The Inner Circle was Chris Jericho\'s AEW faction with Sammy Guevara, Santana, Ortiz, Jake Hager, and later MJF. "A Little Bit of the Bubbly" was their catchphrase.'},
            {'name': 'The Hart Foundation', 'about': 'The Hart Foundation originally was Bret Hart and Jim Neidhart. Later reformed as anti-American faction with Owen Hart, British Bulldog, and Brian Pillman.'},
            {'name': 'The Ministry of Darkness', 'about': 'The Ministry of Darkness was The Undertaker\'s cult faction in 1999. Featured the Acolytes, Mideon, and Viscera in dark, ritualistic storylines.'},
            {'name': 'The Dangerous Alliance', 'about': 'The Dangerous Alliance was Paul E. Dangerously\'s WCW faction featuring Steve Austin, Arn Anderson, Rick Rude, Larry Zbyszko, Bobby Eaton, and Madusa.'},
            {'name': 'The Dungeon of Doom', 'about': 'The Dungeon of Doom was Kevin Sullivan\'s WCW faction created to destroy Hulk Hogan. Featured The Giant, Meng, and Taskmaster Sullivan himself.'},
            {'name': 'The Corporation', 'about': 'The Corporation was Vince McMahon\'s heel faction in 1998-1999. Featured The Rock, Shane McMahon, Big Boss Man, and others opposing Stone Cold Steve Austin.'},
            {'name': 'Right to Censor', 'about': 'Right to Censor was Steven Richards\' faction parodying censorship groups. Featured Bull Buchanan, The Goodfather, Ivory, and Val Venis.'},
            {'name': 'Los Ingobernables de Japon', 'about': 'Los Ingobernables de Japon (LIJ) was formed by Tetsuya Naito in NJPW. Features EVIL, SANADA, Hiromu Takahashi, and BUSHI with tranquilo attitude.'},
            {'name': 'Chaos', 'about': 'CHAOS is NJPW\'s largest faction, formed by Shinsuke Nakamura in 2009. Later led by Kazuchika Okada. Features Hirooki Goto, Tomohiro Ishii, and others.'},
            {'name': 'Suzuki-gun', 'about': 'Suzuki-gun is Minoru Suzuki\'s heel faction in NJPW. Known for aggressive, rule-breaking style and Suzuki\'s terrifying presence.'},
            {'name': 'The Judgment Day', 'about': 'The Judgment Day was originally Edge\'s faction, but became Finn Balor, Damian Priest, Rhea Ripley, and Dominik Mysterio. Gothic-themed heel faction.'},
            {'name': 'Imperium', 'about': 'Imperium is WALTER (Gunther)\'s faction featuring European wrestling excellence. Marcel Barthel and Fabian Aichner enforce mat-based, hard-hitting style.'},
            {'name': 'The Straight Edge Society', 'about': 'The Straight Edge Society was CM Punk\'s cult faction in 2010. Members Luke Gallows, Serena, and Joey Mercury followed Punk\'s straight edge lifestyle.'},
            {'name': 'Legacy', 'about': 'Legacy was Randy Orton\'s faction with Ted DiBiase Jr. and Cody Rhodes. Second-generation superstars who targeted WWE legends.'},
        ]
        for data in stables_data:
            name = data.pop('name')
            updated += self.update_stable(name, **data)
        self.stdout.write(f'  Updated {updated} stables')
        return updated

    def enrich_promotions_batch_7(self):
        """Enrich wrestling promotions batch 7 - American Indies."""
        self.stdout.write('--- Enriching Promotions Batch 7 ---')
        updated = 0
        promotions_data = [
            {'name': 'CZW', 'about': 'Combat Zone Wrestling was founded in 1999 in New Jersey. Known for ultraviolent deathmatches and Tournament of Death. Launched careers of many hardcore stars.'},
            {'name': 'Game Changer Wrestling', 'about': 'GCW was founded in 2010. Jersey-based promotion featuring deathmatch wrestling and indie stars. The Wrld on GCW and Homecoming are signature events.'},
            {'name': 'PWG', 'about': 'Pro Wrestling Guerrilla was founded in 2003 in California. BOLA tournament and indie showcase. Super Dragon and Excalibur founded the promotion.'},
            {'name': 'SHIMMER', 'about': 'SHIMMER Women Athletes was founded in 2005. Premier American women\'s promotion. Features international joshi and American talent.'},
            {'name': 'CHIKARA', 'about': 'Chikara was a Philadelphia promotion founded in 2002. Comic book storytelling and unique characters. King of Trios tournament.'},
            {'name': 'Beyond Wrestling', 'about': 'Beyond Wrestling is a New England promotion founded in 2009. Uncharted Territory weekly show. Indie showcase.'},
            {'name': 'AIW', 'about': 'Absolute Intense Wrestling is an Ohio promotion founded in 2005. Midwest indie scene. Hell on Earth and other signature events.'},
            {'name': 'AAW', 'about': 'AAW Pro Wrestling is a Chicago promotion founded in 2004. Jim Lynam Memorial Tournament. Midwest indie showcase.'},
            {'name': 'Black Label Pro', 'about': 'Black Label Pro is an Indiana promotion founded in 2017. Slamilton and other unique events. Midwest indie wrestling.'},
            {'name': 'DEFY Wrestling', 'about': 'DEFY Wrestling is a Seattle promotion founded in 2017. Pacific Northwest indie scene. Features international talent.'},
            {'name': 'Create A Pro', 'about': 'Create A Pro Wrestling is a New York school and promotion. Pat Buck\'s wrestling academy. NXT UK and WWE alumni.'},
            {'name': 'Wrestling Revolver', 'about': 'Wrestling Revolver is an Iowa promotion founded in 2016. Sami Callihan\'s promotion. Midwest hardcore indie.'},
            {'name': 'GCW Tournament of Death', 'about': 'The Tournament of Death is GCW\'s annual deathmatch tournament. Ultraviolent wrestling showcase. Crown jewel event.'},
            {'name': 'Warrior Wrestling', 'about': 'Warrior Wrestling is a Chicago-area promotion founded in 2018. Stadium series events. Family-friendly indie wrestling.'},
            {'name': 'Glory Pro', 'about': 'Glory Pro Wrestling is a Missouri promotion. Midwest indie scene. Features rising talent.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 7')
        return updated

    def enrich_promotions_batch_8(self):
        """Enrich wrestling promotions batch 8 - Historical territories."""
        self.stdout.write('--- Enriching Promotions Batch 8 ---')
        updated = 0
        promotions_data = [
            {'name': 'Georgia Championship Wrestling', 'about': 'GCW was the premier NWA territory in the Southeast. TBS home before WWF buyout. Gordon Solie commentary. Dusty Rhodes, Tommy Rich, and more.'},
            {'name': 'Jim Crockett Promotions', 'about': 'JCP was the Mid-Atlantic NWA territory run by the Crockett family. Became WCW. Starrcade originated here. Ric Flair territory.'},
            {'name': 'Central States Wrestling', 'about': 'Central States was the Kansas City NWA territory. Operated from 1963-1989. Bob Geigel promoter. Harley Race home territory.'},
            {'name': 'Pacific Northwest Wrestling', 'about': 'Pacific Northwest Wrestling was the Oregon and Washington NWA territory. Portland base. Don Owen promoted. Regional powerhouse.'},
            {'name': 'Big Time Wrestling', 'about': 'Big Time Wrestling was the Detroit NWA territory. The Sheik dominated. Ed Farhat\'s promotion. Midwest wrestling.'},
            {'name': 'International Wrestling', 'about': 'International Wrestling was the Montreal territory. Andre the Giant started here. French-Canadian wrestling hub.'},
            {'name': 'Maple Leaf Wrestling', 'about': 'Maple Leaf Wrestling was the Toronto territory. Frank Tunney promotion. Canadian wrestling hub until WWF expansion.'},
            {'name': 'Western States Sports', 'about': 'Western States Sports was the Amarillo territory. Dory Funk Sr. promotion. Produced Dory Jr. and Terry Funk.'},
            {'name': 'San Francisco NWA', 'about': 'San Francisco was an NWA territory featuring Pat Patterson and other stars. Cow Palace venue. West Coast wrestling.'},
            {'name': 'Houston Wrestling', 'about': 'Houston Wrestling was Paul Boesch\'s Texas territory. Sam Houston Coliseum. NWA affiliate. Texas wrestling legacy.'},
            {'name': 'Central Wrestling Association', 'about': 'CWA was Jerry Lawler and Jerry Jarrett\'s Memphis territory. USWA predecessor. Best angles in wrestling.'},
            {'name': 'USWA', 'about': 'United States Wrestling Association merged Memphis and Dallas from 1989-1997. Jerry Lawler. Jeff Jarrett development.'},
            {'name': 'Southwest Championship Wrestling', 'about': 'SWCW was the San Antonio territory. Joe Blanchard promotion. Later became TWA.'},
            {'name': 'Western Championship Wrestling', 'about': 'WCW (the territory) was the Omaha NWA affiliate. Not the Turner WCW. Midwest wrestling.'},
            {'name': 'All South Wrestling', 'about': 'All South Wrestling was a Tennessee and Mississippi territory. Southern wrestling circuit.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 8')
        return updated

    def enrich_promotions_batch_9(self):
        """Enrich wrestling promotions batch 9 - Modern and misc."""
        self.stdout.write('--- Enriching Promotions Batch 9 ---')
        updated = 0
        promotions_data = [
            {'name': 'National Wrestling Alliance', 'about': 'The NWA was founded in 1948 as an alliance of territories. The World Heavyweight Championship is one of wrestling\'s oldest. Billy Corgan owns current NWA.'},
            {'name': 'TNA Wrestling', 'about': 'TNA Wrestling operated from 2002-2017. Founded by Jeff Jarrett. Six-sided ring. Became Impact Wrestling. Jeff Hardy, AJ Styles, Kurt Angle.'},
            {'name': 'NWA Powerrr', 'about': 'NWA Powerrr is the current NWA\'s studio wrestling show. Retro presentation. YouTube and Fite TV. Nick Aldis era.'},
            {'name': 'Championship Wrestling from Hollywood', 'about': 'CWFH is a Los Angeles indie promotion. NWA affiliate. United Wrestling Network. TV show format.'},
            {'name': 'NWA Hollywood', 'about': 'NWA Hollywood is the Los Angeles NWA affiliate. United Wrestling Network. West Coast wrestling.'},
            {'name': 'Reality of Wrestling', 'about': 'ROW is Booker T\'s Texas promotion and training center. Houston-based. Develops talent for WWE and AEW.'},
            {'name': 'Thunder Rosa Presenta', 'about': 'Thunder Rosa\'s Mission Pro is Texas-based women\'s wrestling. Develops Latina and women talent.'},
            {'name': 'Women of Wrestling', 'about': 'WOW is David McLane\'s women\'s promotion. GLOW successor. TV-oriented presentation.'},
            {'name': 'WrestlePro', 'about': 'WrestlePro is a New Jersey promotion. Northeast indie scene. Features touring talent.'},
            {'name': 'FEST Wrestling', 'about': 'FEST Wrestling is a Florida punk rock wrestling show. Music festival integration. Unique presentation.'},
            {'name': 'Black and Brave', 'about': 'Black and Brave is Seth Rollins and Marek Brave\'s wrestling school. Iowa training center. Tyler Black legacy.'},
            {'name': 'Freelance Wrestling', 'about': 'Freelance Wrestling is a Chicago indie promotion. Monthly shows. Midwest indie scene.'},
            {'name': 'Scenic City Invitational', 'about': 'SCI is an annual Tennessee tournament. Top indie talent showcase. NWA affiliate.'},
            {'name': 'Pro Wrestling ZERO1 USA', 'about': 'ZERO1 USA is the American branch of the Japanese promotion. Strong style wrestling.'},
            {'name': 'West Coast Pro', 'about': 'WCP is a California indie promotion. Bay Area wrestling scene. Features indie stars.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 9')
        return updated

    def enrich_championships_batch_4(self):
        """Enrich wrestling championships batch 4 - Women's titles."""
        self.stdout.write('--- Enriching Championships Batch 4 ---')
        updated = 0
        titles_data = [
            {'name': 'NXT Women\'s Championship', 'about': 'The NXT Women\'s Championship was introduced in 2013. Paige was first champion. Charlotte, Sasha, Bayley, and Asuka defined the title.'},
            {'name': 'WWE Divas Championship', 'about': 'The Divas Championship was WWE\'s women\'s title from 2008-2016. Butterfly design. Replaced by Women\'s Championship.'},
            {'name': 'Impact Knockouts Championship', 'about': 'The Knockouts Championship is Impact\'s women\'s title since 2007. Gail Kim, Awesome Kong, and Tessa Blanchard held it.'},
            {'name': 'ROH Women\'s World Championship', 'about': 'The ROH Women\'s World Championship was introduced in 2018. Features top women\'s talent.'},
            {'name': 'World of Stardom Championship', 'about': 'The World of Stardom Championship is Stardom\'s secondary singles title. Red belt design.'},
            {'name': 'Wonder of Stardom Championship', 'about': 'The Wonder of Stardom Championship is Stardom\'s white belt. High-work rate secondary title.'},
            {'name': 'IWGP Women\'s Championship', 'about': 'The IWGP Women\'s Championship was introduced in 2022. Stardom integration. KAIRI Saya was first champion.'},
            {'name': 'CMLL World Women\'s Championship', 'about': 'The CMLL World Women\'s Championship is lucha libre\'s top women\'s title. Arena Mexico defended.'},
            {'name': 'AAA Reina de Reinas Championship', 'about': 'The Reina de Reinas is AAA\'s top women\'s title. Queen of Queens. Mexican women\'s wrestling.'},
            {'name': 'WWE Women\'s Tag Team Championship', 'about': 'The WWE Women\'s Tag Team Championship was introduced in 2019. Boss \'n\' Hug Connection first champs.'},
            {'name': 'NXT UK Women\'s Championship', 'about': 'The NXT UK Women\'s Championship featured British women\'s talent. Rhea Ripley and Meiko Satomura held it.'},
            {'name': 'AEW Women\'s World Championship', 'about': 'The AEW Women\'s World Championship is AEW\'s top women\'s title. Riho first champion.'},
            {'name': 'Shimmer Championship', 'about': 'The SHIMMER Championship is SHIMMER\'s top women\'s title. American women\'s wrestling showcase.'},
            {'name': 'ChocoPro Championship', 'about': 'The ChocoPro Championship is the apartment wrestling title. Emi Sakura\'s promotion top prize.'},
            {'name': 'SEAdLINNNG Beyond the Sea Championship', 'about': 'The Beyond the Sea Championship is SEAdLINNNG\'s top women\'s title. Joshi wrestling.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 4')
        return updated

    def enrich_championships_batch_5(self):
        """Enrich wrestling championships batch 5 - Historical and misc."""
        self.stdout.write('--- Enriching Championships Batch 5 ---')
        updated = 0
        titles_data = [
            {'name': 'AWA World Heavyweight Championship', 'about': 'The AWA World Heavyweight Championship was the American Wrestling Association\'s top title. Verne Gagne, Nick Bockwinkel legends.'},
            {'name': 'AWA World Tag Team Championship', 'about': 'The AWA World Tag Team Championship was the AWA\'s tag title. Road Warriors, High Flyers held it.'},
            {'name': 'NWA Television Championship', 'about': 'The NWA TV Championship was a workhorse title. Arn Anderson and Tully Blanchard defined it.'},
            {'name': 'NWA United States Championship', 'about': 'The NWA US Championship was Mid-Atlantic\'s top title. Ric Flair, Magnum TA legends.'},
            {'name': 'WCW United States Championship', 'about': 'The WCW US Championship continued NWA lineage. Sting, DDP, Goldberg held it.'},
            {'name': 'WCW Television Championship', 'about': 'The WCW TV Championship was the workhorse title. Lord Steven Regal defined it.'},
            {'name': 'WCW Cruiserweight Championship', 'about': 'The WCW Cruiserweight Championship showcased luchadores. Rey Mysterio, Dean Malenko, Eddie Guerrero.'},
            {'name': 'WCW World Tag Team Championship', 'about': 'The WCW World Tag Team Championship was held by legendary teams. Road Warriors, Steiners, Outsiders.'},
            {'name': 'Impact World Tag Team Championship', 'about': 'The Impact World Tag Team Championship is Impact\'s tag title. The North, LAX, and others.'},
            {'name': 'GHC National Championship', 'about': 'The GHC National Championship is Pro Wrestling NOAH\'s secondary title. Junior heavyweight focused.'},
            {'name': 'Open the Brave Gate Championship', 'about': 'The Open the Brave Gate is Dragon Gate\'s secondary title. Junior heavyweight showcase.'},
            {'name': 'ROH Pure Championship', 'about': 'The ROH Pure Championship emphasizes technical wrestling. Pure wrestling rules. Jonathan Gresham defined it.'},
            {'name': 'NWA World Junior Heavyweight Championship', 'about': 'The NWA World Junior Heavyweight Championship is one of wrestling\'s oldest junior titles.'},
            {'name': 'PWG World Championship', 'about': 'The PWG World Championship is Pro Wrestling Guerrilla\'s top title. BOLA winner often challenges.'},
            {'name': 'CZW World Heavyweight Championship', 'about': 'The CZW World Heavyweight Championship is Combat Zone Wrestling\'s top title. Deathmatch company.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 5')
        return updated

    def enrich_video_games_batch_2(self):
        """Enrich wrestling video games batch 2."""
        self.stdout.write('--- Enriching Video Games Batch 2 ---')
        updated = 0
        games_data = [
            {'name': 'WWE 2K20', 'about': 'WWE 2K20 was critically panned for bugs and glitches. Led to the series taking a year off. Roman Reigns and Becky Lynch cover.'},
            {'name': 'WWE 2K15', 'about': 'WWE 2K15 was the first next-gen WWE game. John Cena cover. MyCareer mode introduced.'},
            {'name': 'WWE 2K14', 'about': 'WWE 2K14 featured The Rock on the cover. 30 Years of WrestleMania mode. Streak vs Career.'},
            {'name': 'WWE 13', 'about': 'WWE 13 featured the Attitude Era. CM Punk cover. Revolution mode for historical storylines.'},
            {'name': 'WWE 12', 'about': 'WWE 12 introduced the Predator engine. Randy Orton cover. Bigger, Badder, Better tagline.'},
            {'name': 'WWE All Stars', 'about': 'WWE All Stars featured exaggerated arcade action. Legends vs current stars. Over the top presentation.'},
            {'name': 'SmackDown vs. Raw 2011', 'about': 'SVR 2011 introduced WWE Universe mode. John Cena cover. Last THQ pre-2K era.'},
            {'name': 'SmackDown vs. Raw 2010', 'about': 'SVR 2010 featured story designer. Create your own storylines. THQ era peak.'},
            {'name': 'SmackDown vs. Raw 2009', 'about': 'SVR 2009 featured Road to WrestleMania mode. Triple H, Undertaker, Cena, Batista covers.'},
            {'name': 'SmackDown vs. Raw 2008', 'about': 'SVR 2008 introduced ECW brand. John Cena cover. Fighting style system.'},
            {'name': 'SmackDown! vs. Raw', 'about': 'The first SVR introduced superstar voices. Eddie Guerrero tribute. PS2 classic.'},
            {'name': 'SmackDown! Shut Your Mouth', 'about': 'Shut Your Mouth had massive roster. The Rock cover. Iconic PS2 era.'},
            {'name': 'SmackDown! Just Bring It', 'about': 'Just Bring It was the first PS2 SmackDown game. Fred Durst in-game. Rock cover.'},
            {'name': 'WWF SmackDown! 2', 'about': 'SmackDown 2: Know Your Role was PS1 classic. The Rock cover. Season mode.'},
            {'name': 'WWF SmackDown!', 'about': 'The original SmackDown game for PS1. Launched the THQ series. Fast paced action.'},
            {'name': 'WWF Raw', 'about': 'WWF Raw for Xbox was anchor of original Xbox. Brock Lesnar era. Unfamiliar controls.'},
            {'name': 'WWE Legends of WrestleMania', 'about': 'Legends of WrestleMania featured classic wrestlers. WrestleMania relive mode. Hulk Hogan cover.'},
            {'name': 'WWE Battlegrounds', 'about': 'WWE Battlegrounds was arcade brawler style. Cartoon graphics. Power-ups and over-top-action.'},
            {'name': 'WCW vs. nWo: World Tour', 'about': 'WCW World Tour for N64 introduced AKI engine. WCW roster. THQ era beginning.'},
            {'name': 'WCW Nitro', 'about': 'WCW Nitro was THQ\'s first WCW game. Goldberg era roster. PS1 and N64.'},
        ]
        for data in games_data:
            name = data.pop('name')
            updated += self.update_game(name, **data)
        self.stdout.write(f'  Updated {updated} video games batch 2')
        return updated

    def enrich_promotions_batch_10(self):
        """Enrich wrestling promotions batch 10."""
        self.stdout.write('--- Enriching Promotions Batch 10 ---')
        updated = 0
        promotions_data = [
            {'name': '5 Star Wrestling', 'about': '5 Star Wrestling is a video game featuring original wrestlers. UK-developed. Licensed characters.'},
            {'name': 'AAW: Professional Wrestling Redefined', 'about': 'AAW is the Chicago indie promotion founded in 2004. Midwest wrestling staple.'},
            {'name': 'Active Advance Pro Wrestling', 'about': 'ACTIVE is a Japanese women\'s promotion. Joshi wrestling development.'},
            {'name': 'All American Wrestling', 'about': 'All American Wrestling promoted events featuring American-style wrestling.'},
            {'name': 'All Pro Wrestling', 'about': 'All Pro Wrestling is a California indie promotion. Bay Area wrestling scene.'},
            {'name': 'All Star Wrestling', 'about': 'All Star Wrestling was a British promotion on ITV. Classic British catch.'},
            {'name': 'Alpha-1 Wrestling', 'about': 'Alpha-1 Wrestling is a Canadian indie promotion. Ontario wrestling scene.'},
            {'name': 'American Wrestling Federation', 'about': 'AWF was a 1990s promotion featuring former WWF stars.'},
            {'name': 'Arsion', 'about': 'Arsion was a Japanese women\'s promotion. Joshi wrestling from 1998-2002.'},
            {'name': 'Attack! Pro Wrestling', 'about': 'Attack! Pro Wrestling is a Welsh promotion. Cardiff-based indie wrestling.'},
            {'name': 'Battlarts', 'about': 'Battlarts was a Japanese shoot-style promotion. Yuki Ishikawa founded. 1996-2011.'},
            {'name': 'Bellatrix Female Warriors', 'about': 'Bellatrix was a British women\'s promotion. UK female wrestling.'},
            {'name': 'British Championship Wrestling', 'about': 'BCW promoted British wrestling events across the UK.'},
            {'name': 'Capitol Wrestling Corporation', 'about': 'Capitol Wrestling was the precursor to WWF. Vince McMahon Sr. Founded 1952.'},
            {'name': 'Catch Wrestling Association', 'about': 'CWA promoted catch wrestling events. Traditional European style.'},
            {'name': 'Chaotic Wrestling', 'about': 'Chaotic Wrestling is a New England promotion. Massachusetts indie scene.'},
            {'name': 'ChocoPro', 'about': 'ChocoPro is Emi Sakura\'s apartment wrestling promotion. YouTube streaming.'},
            {'name': 'Consejo Mundial de Lucha Libre', 'about': 'CMLL is the world\'s oldest wrestling promotion, founded 1933. Arena Mexico home. Traditional lucha libre.'},
            {'name': 'Continental Championship Wrestling', 'about': 'CCW was the Alabama NWA territory. Southeastern wrestling.'},
            {'name': 'Diamond Ring', 'about': 'Diamond Ring is a Japanese promotion founded by Kensuke Sasaki.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 10')
        return updated

    def enrich_promotions_batch_11(self):
        """Enrich wrestling promotions batch 11."""
        self.stdout.write('--- Enriching Promotions Batch 11 ---')
        updated = 0
        promotions_data = [
            {'name': 'Dragon Gate USA', 'about': 'Dragon Gate USA was the American branch of Dragon Gate. Gabe Sapolsky ran it.'},
            {'name': 'Dragongate', 'about': 'Dragongate is Japanese promotion known for fast-paced junior action. Faction warfare.'},
            {'name': 'Eastern Sports Association', 'about': 'ESA was a regional wrestling promotion in the eastern United States.'},
            {'name': 'Family Wrestling Entertainment', 'about': 'FWE was a New York indie promotion. Family-friendly wrestling.'},
            {'name': 'Femmes Fatales', 'about': 'Femmes Fatales was a Canadian women\'s wrestling promotion.'},
            {'name': 'Fighting Network Rings', 'about': 'RINGS was a Japanese shoot-style promotion. Akira Maeda founded it 1991.'},
            {'name': 'Fred Kohler Enterprises', 'about': 'Fred Kohler promoted wrestling in Chicago. Historic promoter.'},
            {'name': 'Future of Wrestling', 'about': 'FOW promotes indie wrestling showcasing future stars.'},
            {'name': 'Ganbare Pro-Wrestling', 'about': 'Ganbare Pro is a Japanese underdog-themed promotion.'},
            {'name': 'Global Wrestling Federation', 'about': 'GWF was a Texas promotion in the 1990s. TV wrestling.'},
            {'name': 'Grand Prix Wrestling', 'about': 'Grand Prix Wrestling was a Canadian Maritime promotion.'},
            {'name': 'Hart Legacy Wrestling', 'about': 'Hart Legacy was the Hart family\'s modern promotion in Calgary.'},
            {'name': 'Heartland Wrestling Association', 'about': 'HWA was an Ohio developmental promotion. Les Thatcher.'},
            {'name': 'Hustle', 'about': 'Hustle was a Japanese entertainment wrestling promotion. 2004-2009.'},
            {'name': 'Impact Pro Wrestling', 'about': 'IPW promotes wrestling events in various regions.'},
            {'name': 'Impact Wrestling', 'about': 'Impact Wrestling (formerly TNA) is a major American promotion. Founded 2002.'},
            {'name': 'Independent Wrestling Federation (Russia)', 'about': 'IWF Russia promotes professional wrestling in Russia.'},
            {'name': 'Inoki Genome Federation', 'about': 'IGF was Antonio Inoki\'s MMA-wrestling hybrid promotion.'},
            {'name': 'Insane Championship Wrestling', 'about': 'ICW is a Scottish promotion known for adult-oriented wrestling.'},
            {'name': 'International Wrestling Enterprise', 'about': 'IWE was a Japanese promotion from 1966-1981. Rival to JWA.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 11')
        return updated

    def enrich_promotions_batch_12(self):
        """Enrich wrestling promotions batch 12."""
        self.stdout.write('--- Enriching Promotions Batch 12 ---')
        updated = 0
        promotions_data = [
            {'name': 'International Wrestling Revolution Group', 'about': 'IWRG is a Mexican promotion founded 1996. Hardcore lucha libre.'},
            {'name': 'International Wrestling Syndicate', 'about': 'IWS is a Canadian promotion in Quebec. Hardcore indie.'},
            {'name': 'JDStar', 'about': 'JDStar was a Japanese women\'s promotion. Joshi wrestling.'},
            {'name': 'JWP Joshi Puroresu', 'about': 'JWP was a major Japanese women\'s promotion. Joshi wrestling.'},
            {'name': 'Japan Pro Wrestling Alliance', 'about': 'JWA was Japan\'s first major promotion. Rikidozan founded it.'},
            {'name': 'Japan Women\'s Pro-Wrestling', 'about': 'JWPW was a women\'s promotion in Japan.'},
            {'name': 'Jersey All Pro Wrestling', 'about': 'JAPW was a New Jersey indie promotion. Hardcore wrestling.'},
            {'name': 'Kingdom Pro Wrestling', 'about': 'KPW promotes indie wrestling events.'},
            {'name': 'La Liga Wrestling', 'about': 'La Liga Wrestling promotes lucha libre style events.'},
            {'name': 'LLPW-X', 'about': 'LLPW-X is Ladies Legend Pro Wrestling. Japanese women\'s promotion.'},
            {'name': 'Lucha Libre Boom', 'about': 'Lucha Libre Boom promotes independent lucha events.'},
            {'name': 'Lucha Libre Feminil', 'about': 'Lucha Libre Feminil promotes Mexican women\'s lucha.'},
            {'name': 'Lyger Dojo', 'about': 'Lyger Dojo was Jushin Liger\'s training promotion.'},
            {'name': 'Major League Wrestling', 'about': 'MLW is Court Bauer\'s promotion. Sports-based presentation.'},
            {'name': 'Masked Republic', 'about': 'Masked Republic promotes lucha libre and merchandise.'},
            {'name': 'Memphis Championship Wrestling', 'about': 'MCW was WWE\'s Memphis developmental territory.'},
            {'name': 'Mexicali Pro Wrestling', 'about': 'MPW promotes lucha libre in Mexicali region.'},
            {'name': 'New Japan Pro Wrestling', 'about': 'NJPW is Japan\'s largest promotion. Antonio Inoki founded 1972.'},
            {'name': 'Nigel McGuinness Wrestling', 'about': 'Nigel McGuinness promotions featured British wrestling.'},
            {'name': 'NWE Wrestling', 'about': 'NWE promotes indie wrestling events.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 12')
        return updated

    def enrich_promotions_batch_13(self):
        """Enrich wrestling promotions batch 13."""
        self.stdout.write('--- Enriching Promotions Batch 13 ---')
        updated = 0
        promotions_data = [
            {'name': 'Ohio Valley Wrestling', 'about': 'OVW is a developmental promotion in Louisville. WWE partner 2000-2008.'},
            {'name': 'Oriental Pro Wrestling', 'about': 'OPW promotes Japanese-style wrestling.'},
            {'name': 'Osaka Pro Wrestling', 'about': 'Osaka Pro is a Japanese comedy wrestling promotion.'},
            {'name': 'Oz Academy', 'about': 'Oz Academy is a Japanese women\'s promotion. Mayumi Ozaki founded.'},
            {'name': 'Pacific Coast Wrestling', 'about': 'PCW promoted wrestling on the US Pacific Coast.'},
            {'name': 'Pacific Northwest Wrestling', 'about': 'PNW was the Portland NWA territory. Don Owen promoted.'},
            {'name': 'Pandemonium Pro Wrestling', 'about': 'PPW promotes indie wrestling events.'},
            {'name': 'Pennsylvania Championship Wrestling', 'about': 'PCW promotes wrestling in Pennsylvania.'},
            {'name': 'Philadelphia Wrestling', 'about': 'Philadelphia wrestling scene has rich ECW history.'},
            {'name': 'Premier Wrestling Federation', 'about': 'PWF promotes indie wrestling with TV presence.'},
            {'name': 'Pro Wrestling Guerrilla', 'about': 'PWG is a California indie founded 2003. BOLA tournament.'},
            {'name': 'Pro Wrestling NOAH', 'about': 'NOAH was founded by Mitsuharu Misawa 2000. Japanese strong style.'},
            {'name': 'Pro Wrestling Wave', 'about': 'WAVE is a Japanese women\'s promotion founded 2007.'},
            {'name': 'Pro Wrestling Zero1', 'about': 'ZERO1 was founded by Shinya Hashimoto 2001.'},
            {'name': 'Pure Wrestling Association', 'about': 'PWA promotes pure wrestling style events.'},
            {'name': 'Queens of Combat', 'about': 'QOC is a women\'s wrestling promotion in the US.'},
            {'name': 'Reality of Wrestling', 'about': 'ROW is Booker T\'s Houston promotion and training center.'},
            {'name': 'Revolution Pro Wrestling', 'about': 'RevPro is a British promotion with NJPW partnership.'},
            {'name': 'Ring of Honor', 'about': 'ROH was founded 2002. Pure wrestling. Tony Khan owns since 2022.'},
            {'name': 'Rocky Mountain Pro Wrestling', 'about': 'RMPW promotes wrestling in Colorado region.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 13')
        return updated

    def enrich_promotions_batch_14(self):
        """Enrich wrestling promotions batch 14."""
        self.stdout.write('--- Enriching Promotions Batch 14 ---')
        updated = 0
        promotions_data = [
            {'name': 'Sendai Girls\' Pro Wrestling', 'about': 'Sendai Girls is a Japanese women\'s promotion. Meiko Satomura.'},
            {'name': 'Shine Wrestling', 'about': 'SHINE is an American women\'s promotion. WWN affiliated.'},
            {'name': 'Smoky Mountain Wrestling', 'about': 'SMW was Jim Cornette\'s 1990s NWA-style promotion.'},
            {'name': 'Southern Championship Wrestling', 'about': 'SCW promoted Southern wrestling style.'},
            {'name': 'Southside Wrestling Entertainment', 'about': 'SWE is a British promotion in Surrey.'},
            {'name': 'Stampede Wrestling', 'about': 'Stampede was the Hart family Calgary territory.'},
            {'name': 'Stardom', 'about': 'Stardom is Japan\'s top women\'s promotion. Rossy Ogawa founded 2010.'},
            {'name': 'Strong Style Wrestling', 'about': 'SSW promotes Japanese strong style events.'},
            {'name': 'Target Sports', 'about': 'Target Sports promoted wrestling events.'},
            {'name': 'Tennessee Championship Wrestling', 'about': 'TCW promoted wrestling in Tennessee.'},
            {'name': 'The Wrestling Channel', 'about': 'TWC was a UK wrestling TV network.'},
            {'name': 'Thunder Pro Wrestling', 'about': 'Thunder Pro promotes indie wrestling.'},
            {'name': 'Tokyo Joshi Pro Wrestling', 'about': 'TJPW is DDT\'s women\'s promotion. Yuka Sakazaki.'},
            {'name': 'Total Nonstop Action Wrestling', 'about': 'TNA operated 2002-2017. Became Impact Wrestling.'},
            {'name': 'Toryumon', 'about': 'Toryumon was the predecessor to Dragon Gate. Ultimo Dragon.'},
            {'name': 'UWA World Trios Championship', 'about': 'UWA was a Mexican promotion. Trios wrestling.'},
            {'name': 'Ultimate Pro Wrestling', 'about': 'UPW trained John Cena and other WWE stars.'},
            {'name': 'Union Pro Wrestling', 'about': 'Union Pro is a Japanese promotion.'},
            {'name': 'Universal Championship Wrestling', 'about': 'UCW promotes indie wrestling events.'},
            {'name': 'Universal Wrestling Association', 'about': 'UWA was a major Mexican promotion. Lucha libre.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 14')
        return updated

    def enrich_promotions_batch_15(self):
        """Enrich wrestling promotions batch 15."""
        self.stdout.write('--- Enriching Promotions Batch 15 ---')
        updated = 0
        promotions_data = [
            {'name': 'Universal Wrestling Federation', 'about': 'UWF was Bill Watts\' promotion. Also Japanese shoot-style.'},
            {'name': 'USA Pro Wrestling', 'about': 'USA Pro promoted American wrestling events.'},
            {'name': 'Vintage Wrestling', 'about': 'Vintage Wrestling celebrates classic wrestling history.'},
            {'name': 'W*ING', 'about': 'W*ING was a Japanese deathmatch promotion. Extreme wrestling.'},
            {'name': 'Westside Championship Wrestling', 'about': 'WCW promoted western US indie wrestling.'},
            {'name': 'Women Superstars Uncensored', 'about': 'WSU is an American women\'s indie promotion.'},
            {'name': 'Women of Wrestling', 'about': 'WOW is David McLane\'s women\'s wrestling promotion.'},
            {'name': 'World Championship Wrestling', 'about': 'WCW was Ted Turner\'s promotion 1988-2001. nWo. Nitro.'},
            {'name': 'World Class Championship Wrestling', 'about': 'WCCW was the Von Erich Dallas territory.'},
            {'name': 'World League Wrestling', 'about': 'WLW promotes wrestling in Missouri.'},
            {'name': 'World of Sport Wrestling', 'about': 'WoS was British TV wrestling. Big Daddy. Giant Haystacks.'},
            {'name': 'World Wide Wrestling Federation', 'about': 'WWWF became WWF in 1979. Bruno Sammartino era.'},
            {'name': 'World Wonder Ring Stardom', 'about': 'Stardom is top Japanese women\'s promotion.'},
            {'name': 'World Wrestling All-Stars', 'about': 'WWA was a 2000s indie featuring WCW alumni.'},
            {'name': 'World Wrestling Council', 'about': 'WWC is Puerto Rico\'s top promotion. Carlos Colon.'},
            {'name': 'World Wrestling Entertainment', 'about': 'WWE is the largest wrestling company. Founded 1952.'},
            {'name': 'World Wrestling Federation', 'about': 'WWF was WWE\'s name until 2002. Hulkamania.'},
            {'name': 'World Wrestling League', 'about': 'WWL promoted wrestling in Puerto Rico.'},
            {'name': 'Xtreme Pro Wrestling', 'about': 'XPW was a Los Angeles extreme promotion.'},
            {'name': 'Zero1 Pro-Wrestling', 'about': 'ZERO1 was founded by Shinya Hashimoto. Strong style.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 15')
        return updated

    def enrich_stables_batch_2(self):
        """Enrich wrestling stables batch 2."""
        self.stdout.write('--- Enriching Stables Batch 2 ---')
        updated = 0
        stables_data = [
            {'name': 'The Brood', 'about': 'The Brood was Edge, Christian, and Gangrel. Vampire gimmick. Blood baths.'},
            {'name': 'The Nation of Domination', 'about': 'The Nation was a militant Black stable. Faarooq led, then The Rock.'},
            {'name': 'Raven\'s Flock', 'about': 'Raven\'s Flock followed Raven in WCW. Included Kidman and Saturn.'},
            {'name': 'The Oddities', 'about': 'The Oddities were a circus-themed faction. Golga, Kurrgan, Giant Silva.'},
            {'name': 'J.O.B. Squad', 'about': 'The J.O.B. Squad was a jobber faction. Al Snow, Scorpio, Gillberg.'},
            {'name': 'The Cabinet', 'about': 'The Cabinet was JBL\'s faction. Orlando Jordan, Bashams.'},
            {'name': 'Spirit Squad', 'about': 'The Spirit Squad were male cheerleaders. Kenny, Mikey, Nicky, Johnny, Mitch.'},
        ]
        for data in stables_data:
            name = data.pop('name')
            updated += self.update_stable(name, **data)
        self.stdout.write(f'  Updated {updated} stables batch 2')
        return updated

    def enrich_video_games_batch_3(self):
        """Enrich wrestling video games batch 3."""
        self.stdout.write('--- Enriching Video Games Batch 3 ---')
        updated = 0
        games_data = [
            {'name': 'Pro Wrestling', 'about': 'Pro Wrestling for NES was an early wrestling game. Star Man. A Winner Is You.'},
            {'name': 'WWF WrestleFest', 'about': 'WWF WrestleFest was an arcade classic. Royal Rumble mode. Technos.'},
            {'name': 'WWF Royal Rumble', 'about': 'WWF Royal Rumble for SNES/Genesis featured 12-man rumbles.'},
            {'name': 'WWF Super WrestleMania', 'about': 'Super WrestleMania was 16-bit era WWF game. Hulk Hogan era.'},
            {'name': 'WWF Raw', 'about': 'WWF Raw for SNES/Genesis featured Bret Hart era roster.'},
            {'name': 'Saturday Night Slam Masters', 'about': 'Slam Masters was Capcom\'s wrestling game. Arcade fighter style.'},
            {'name': 'Fire Pro Wrestling Returns', 'about': 'Fire Pro Wrestling Returns for PS2 was critically acclaimed. 2D classic.'},
            {'name': 'Def Jam: Fight for NY', 'about': 'Def Jam FFNY was AKI engine fighting game. Hip hop stars.'},
            {'name': 'WWE Day of Reckoning', 'about': 'Day of Reckoning was GameCube exclusive. AKI-style gameplay.'},
            {'name': 'WWE Day of Reckoning 2', 'about': 'DoR 2 continued GameCube series. Triple H cover.'},
            {'name': 'TNA Impact!', 'about': 'TNA Impact! was TNA\'s video game. Midway developed.'},
            {'name': 'WCW Mayhem', 'about': 'WCW Mayhem was EA Sports\' WCW game. Late WCW era.'},
            {'name': 'ECW Hardcore Revolution', 'about': 'ECW Hardcore Revolution was Acclaim\'s ECW game. WWF Attitude engine.'},
            {'name': 'ECW Anarchy Rulz', 'about': 'ECW Anarchy Rulz was the sequel. Tommy Dreamer cover.'},
            {'name': 'WrestleMania XXI', 'about': 'WrestleMania 21 was Xbox exclusive. Career mode. THQ.'},
            {'name': 'Backyard Wrestling', 'about': 'Backyard Wrestling was an extreme wrestling game. ICP featured.'},
            {'name': 'Showdown: Legends of Wrestling', 'about': 'Showdown featured classic wrestlers. Acclaim\'s legends series.'},
            {'name': 'Ultimate Muscle', 'about': 'Ultimate Muscle was based on anime. GCN/PS2.'},
            {'name': 'Galactic Wrestling', 'about': 'Galactic Wrestling was a sci-fi wrestling game.'},
            {'name': 'Rumble Roses', 'about': 'Rumble Roses was Konami\'s women\'s wrestling game. PS2.'},
        ]
        for data in games_data:
            name = data.pop('name')
            updated += self.update_game(name, **data)
        self.stdout.write(f'  Updated {updated} video games batch 3')
        return updated

    def enrich_books_batch_2(self):
        """Enrich wrestling books batch 2."""
        self.stdout.write('--- Enriching Books Batch 2 ---')
        updated = 0
        books_data = [
            {'name': 'Sex, Lies and Headlocks', 'about': 'Sex, Lies and Headlocks chronicles the WWF/WWE corporate story.'},
            {'name': 'The Monday Night War', 'about': 'The Monday Night War book covers WWF vs WCW battle.'},
            {'name': 'Titan Sinking', 'about': 'Titan Sinking covers WWF\'s steroid scandal in early 90s.'},
            {'name': 'Titan Shattered', 'about': 'Titan Shattered continues Titan Sinking\'s story.'},
            {'name': 'Pain and Passion', 'about': 'Pain and Passion is Bret Hart\'s second book.'},
            {'name': 'Lion\'s Pride', 'about': 'Lion\'s Pride covers New Japan Pro-Wrestling history.'},
            {'name': 'Ring of Hell', 'about': 'Ring of Hell covers the Chris Benoit tragedy.'},
            {'name': 'Tributes', 'about': 'Tributes is Dave Meltzer\'s obituaries collection.'},
            {'name': 'We Promised You a Great Main Event', 'about': 'We Promised You a Great Main Event is Bill Hanstock\'s WWE history.'},
            {'name': 'Capitol Revolution', 'about': 'Capitol Revolution covers WWWF history. Tim Hornbaker.'},
            {'name': 'National Wrestling Alliance', 'about': 'NWA book chronicles the alliance history.'},
            {'name': 'Professional Wrestling', 'about': 'Professional Wrestling is an academic study of the art form.'},
            {'name': 'Young Bucks: Killing the Business', 'about': 'Killing the Business is The Young Bucks\' autobiography.'},
            {'name': 'MOX', 'about': 'MOX is Jon Moxley\'s autobiography about his career.'},
            {'name': 'No Is a Four-Letter Word', 'about': 'No Is a Four-Letter Word is Jericho\'s motivational book.'},
            {'name': 'Best in the World', 'about': 'Best in the World is Chris Jericho\'s fourth book.'},
            {'name': 'The Best There Is', 'about': 'The Best There Is is another Bret Hart biography.'},
            {'name': 'Cageside Seats', 'about': 'Cageside Seats covers wrestling journalism.'},
            {'name': 'Slobberknocker', 'about': 'Slobberknocker is Jim Ross\'s autobiography.'},
            {'name': 'Under the Black Hat', 'about': 'Under the Black Hat is Jim Ross\'s second book.'},
        ]
        for data in books_data:
            name = data.pop('name')
            updated += self.update_book(name, **data)
        self.stdout.write(f'  Updated {updated} books batch 2')
        return updated

    def enrich_podcasts_batch_3(self):
        """Enrich wrestling podcasts batch 3."""
        self.stdout.write('--- Enriching Podcasts Batch 3 ---')
        updated = 0
        podcasts_data = [
            {'name': 'Cheap Heat', 'about': 'Cheap Heat is The Ringer\'s wrestling podcast. Peter Rosenberg hosted.'},
            {'name': 'The Lapsed Fan', 'about': 'The Lapsed Fan is an in-depth wrestling history podcast.'},
            {'name': 'OSW Review', 'about': 'OSW Review is an Irish video podcast. Golden Noggers awards.'},
            {'name': 'Solomonster Sounds Off', 'about': 'Solomonster is a wrestling opinion podcast.'},
            {'name': 'The Ross Report', 'about': 'The Ross Report was Jim Ross\'s podcast before Grilling JR.'},
            {'name': 'Stone Cold Podcast', 'about': 'Stone Cold Podcast was Steve Austin\'s interview show on WWE Network.'},
            {'name': 'Table for 3', 'about': 'Table for 3 is WWE Network show with three superstars.'},
            {'name': 'After the Bell', 'about': 'After the Bell is Corey Graves\' WWE podcast.'},
            {'name': 'The Broken Skull Sessions', 'about': 'Broken Skull Sessions is Stone Cold\'s interview show.'},
            {'name': 'Straight Up Steve Austin', 'about': 'Straight Up Steve Austin was USA Network show.'},
            {'name': 'The A Show', 'about': 'The A Show covers wrestling with humor and analysis.'},
            {'name': 'Keepin\' It 100', 'about': 'Keepin\' It 100 is Konnan\'s wrestling podcast.'},
            {'name': 'Booking The Territory', 'about': 'Booking The Territory covers wrestling history.'},
            {'name': 'What Happened When?', 'about': 'WHW is Tony Schiavone\'s WCW history podcast.'},
            {'name': 'Bischoff on Wrestling', 'about': 'Bischoff on Wrestling features Eric Bischoff\'s takes.'},
            {'name': 'We Watch Wrestling', 'about': 'We Watch Wrestling is a comedy wrestling podcast.'},
            {'name': 'Getting Over', 'about': 'Getting Over covers wrestling psychology and business.'},
            {'name': 'PWTorch Livecast', 'about': 'PWTorch Livecast is Wade Keller\'s wrestling news show.'},
            {'name': 'Figure Four Daily', 'about': 'Figure Four Daily is Bryan Alvarez\'s wrestling show.'},
            {'name': 'Wrestling Observer Live', 'about': 'WOL is Bryan Alvarez\'s daily show on F4W.'},
        ]
        for data in podcasts_data:
            name = data.pop('name')
            updated += self.update_podcast(name, **data)
        self.stdout.write(f'  Updated {updated} podcasts batch 3')
        return updated

    def enrich_championships_batch_6(self):
        """Enrich wrestling championships batch 6."""
        self.stdout.write('--- Enriching Championships Batch 6 ---')
        updated = 0
        titles_data = [
            {'name': 'WWE Speed Championship', 'about': 'WWE Speed Championship is defended on X/Twitter. Quick matches.'},
            {'name': 'WWE Women\'s World Championship', 'about': 'WWE Women\'s World Championship is Raw\'s top women\'s title.'},
            {'name': 'WWE Women\'s Championship', 'about': 'WWE Women\'s Championship is SmackDown\'s top women\'s title.'},
            {'name': 'AEW Continental Championship', 'about': 'AEW Continental Championship was held by Eddie Kingston.'},
            {'name': 'AEW Trios Championship', 'about': 'AEW World Trios Championship features three-person teams.'},
            {'name': 'TNT Championship', 'about': 'TNT Championship is AEW\'s workhorse title. Cody Rhodes first.'},
            {'name': 'TBS Championship', 'about': 'TBS Championship is AEW\'s secondary women\'s title.'},
            {'name': 'FTW Championship', 'about': 'FTW Championship was created by Taz. Revived in AEW.'},
            {'name': 'NWA Worlds Heavyweight Championship', 'about': 'NWA Worlds Heavyweight Championship dates to 1948. Ten Pounds of Gold.'},
            {'name': 'IWGP Global Heavyweight Championship', 'about': 'IWGP Global Heavyweight Championship is NJPW\'s newest title.'},
            {'name': 'Strong Openweight Championship', 'about': 'NJPW Strong Openweight title for American shows.'},
            {'name': 'RevPro British Heavyweight Championship', 'about': 'RevPro British Heavyweight title is UK\'s top prize.'},
            {'name': 'Progress World Championship', 'about': 'PROGRESS World Championship is the UK promotion\'s top title.'},
            {'name': 'ICW World Heavyweight Championship', 'about': 'ICW World Heavyweight title is Scotland\'s top prize.'},
            {'name': 'GCW World Championship', 'about': 'GCW World Championship is Game Changer Wrestling\'s top title.'},
            {'name': 'DDT Universal Championship', 'about': 'DDT Universal Championship is DDT\'s top title.'},
            {'name': 'KO-D Openweight Championship', 'about': 'KO-D Openweight is DDT\'s secondary singles title.'},
            {'name': 'Ironman Heavymetalweight Championship', 'about': 'Ironman Heavymetalweight can be won anywhere, anytime.'},
            {'name': 'Goddess of Stardom Championship', 'about': 'Goddess of Stardom is Stardom\'s tag team title.'},
            {'name': 'Artist of Stardom Championship', 'about': 'Artist of Stardom is Stardom\'s trios title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 6')
        return updated

    def enrich_promotions_batch_16(self):
        """Enrich wrestling promotions batch 16."""
        self.stdout.write('--- Enriching Promotions Batch 16 ---')
        updated = 0
        promotions_data = [
            {'name': '50th State Big Time Wrestling', 'about': '50th State Big Time Wrestling was a Hawaiian promotion.'},
            {'name': 'Actwres girl\'Z', 'about': 'Actwres girl\'Z is a Japanese women\'s promotion. Joshi puroresu.'},
            {'name': 'Africa Wrestling Alliance', 'about': 'Africa Wrestling Alliance promotes wrestling in Africa.'},
            {'name': 'All Wrestling Organization', 'about': 'All Wrestling Organization was an indie promotion.'},
            {'name': 'American Wrestling Association', 'about': 'AWA was Verne Gagne\'s legendary promotion. Minneapolis-based.'},
            {'name': 'Apache Pro-Wrestling Army', 'about': 'Apache Pro-Wrestling Army is a Japanese promotion.'},
            {'name': 'Asia-Pacific Federation of Wrestling', 'about': 'Asia-Pacific Federation governed wrestling in the region.'},
            {'name': 'Assault Championship Wrestling', 'about': 'Assault Championship Wrestling was an indie promotion.'},
            {'name': 'Atlantic Athletic Commission', 'about': 'Atlantic Athletic Commission was a regional promotion.'},
            {'name': 'Australian wrestling', 'about': 'Australian wrestling has a long history dating back decades.'},
            {'name': 'BSE Pro', 'about': 'BSE Pro is an indie wrestling promotion.'},
            {'name': 'Big Time Wrestling (Boston)', 'about': 'Big Time Wrestling Boston was a New England territory.'},
            {'name': 'Big Time Wrestling (Detroit)', 'about': 'Big Time Wrestling Detroit was The Sheik\'s territory.'},
            {'name': 'Big Time Wrestling (San Francisco)', 'about': 'Big Time Wrestling SF was a West Coast territory.'},
            {'name': 'Brazilian Wrestling Federation', 'about': 'Brazilian Wrestling Federation promotes wrestling in Brazil.'},
            {'name': 'British Kingdom Pro-Wrestling', 'about': 'British Kingdom Pro-Wrestling is a UK indie promotion.'},
            {'name': 'Century Wrestling Alliance', 'about': 'Century Wrestling Alliance was an indie promotion.'},
            {'name': 'ChickFight', 'about': 'ChickFight was a women\'s wrestling tournament series.'},
            {'name': 'CyberFight', 'about': 'CyberFight is the parent company of DDT, NOAH, and TJPW.'},
            {'name': 'Diamond Ring (professional wrestling)', 'about': 'Diamond Ring was Katsuhiko Nakajima\'s promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 16')
        return updated

    def enrich_promotions_batch_17(self):
        """Enrich wrestling promotions batch 17."""
        self.stdout.write('--- Enriching Promotions Batch 17 ---')
        updated = 0
        promotions_data = [
            {'name': 'Dominion Wrestling Union', 'about': 'Dominion Wrestling Union was a Canadian promotion.'},
            {'name': 'Dradition', 'about': 'Dradition is Keiji Mutoh\'s Japanese promotion.'},
            {'name': 'Extreme Rising', 'about': 'Extreme Rising was an attempted ECW reunion promotion.'},
            {'name': 'Fighting of World Japan Pro Wrestling', 'about': 'FoW Japan was a short-lived Japanese promotion.'},
            {'name': 'Fédération Française de Catch Professionnel', 'about': 'FFCP governs professional wrestling in France.'},
            {'name': 'Global Professional Wrestling Alliance', 'about': 'GPWA was an alliance of indie promotions.'},
            {'name': 'Grand Pro Wrestling', 'about': 'Grand Pro Wrestling was a Japanese promotion.'},
            {'name': 'Great Canadian Wrestling', 'about': 'Great Canadian Wrestling was a Canadian indie promotion.'},
            {'name': 'Heart of America Sports Attractions', 'about': 'Heart of America was a Midwestern territory.'},
            {'name': 'High Impact Wrestling', 'about': 'High Impact Wrestling is a Canadian indie promotion.'},
            {'name': 'Hustle (professional wrestling)', 'about': 'Hustle was a sports entertainment promotion in Japan.'},
            {'name': 'I-Generation Superstars of Wrestling', 'about': 'I-Generation was a Florida indie promotion.'},
            {'name': 'IWF Promotions', 'about': 'IWF Promotions was an indie wrestling company.'},
            {'name': 'Incredibly Strange Wrestling', 'about': 'ISW combined wrestling with punk rock culture.'},
            {'name': 'Independent Professional Wrestling Alliance', 'about': 'IPWA was an indie wrestling alliance.'},
            {'name': 'Independent circuit', 'about': 'The indie circuit refers to non-major promotion wrestling.'},
            {'name': 'International Pro Wrestling: United Kingdom', 'about': 'IPW:UK was a British indie promotion.'},
            {'name': 'International World Class Championship Wrestling', 'about': 'IWCCW was an offshoot of WCCW.'},
            {'name': 'International Wrestling Alliance', 'about': 'IWA was an international wrestling alliance.'},
            {'name': 'International Wrestling Association of Japan', 'about': 'IWA Japan was a deathmatch promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 17')
        return updated

    def enrich_promotions_batch_18(self):
        """Enrich wrestling promotions batch 18."""
        self.stdout.write('--- Enriching Promotions Batch 18 ---')
        updated = 0
        promotions_data = [
            {'name': 'Japan Pro-Wrestling', 'about': 'Japan Pro-Wrestling was an early Japanese promotion.'},
            {'name': 'Kingdom Professional Wrestling', 'about': 'Kingdom Pro Wrestling was an indie promotion.'},
            {'name': 'Kyushu Pro-Wrestling', 'about': 'Kyushu Pro-Wrestling is based in southern Japan.'},
            {'name': 'Ladies Major League Wrestling', 'about': 'Ladies Major League was a women\'s wrestling promotion.'},
            {'name': 'Ladies Professional Wrestling Association', 'about': 'LPWA was an 80s-90s women\'s promotion.'},
            {'name': 'Lucha Britannia', 'about': 'Lucha Britannia was a UK lucha libre promotion.'},
            {'name': 'Lucha Libre AAA Worldwide', 'about': 'AAA is Mexico\'s largest lucha libre promotion.'},
            {'name': 'Lucha Libre Elite', 'about': 'Lucha Libre Elite was an AAA spinoff promotion.'},
            {'name': 'Lucha Libre Femenil', 'about': 'Lucha Libre Femenil is women\'s lucha libre wrestling.'},
            {'name': 'Lucha Libre USA', 'about': 'Lucha Libre USA was MTV\'s lucha libre show.'},
            {'name': 'Lutte Internationale', 'about': 'Lutte Internationale was a French Canadian promotion.'},
            {'name': 'Manila Wrestling Federation', 'about': 'Manila Wrestling Federation is based in the Philippines.'},
            {'name': 'Maple Leaf Pro Wrestling', 'about': 'Maple Leaf Pro Wrestling is a Canadian promotion.'},
            {'name': 'Maximum Pro Wrestling', 'about': 'Maximum Pro Wrestling was an indie promotion.'},
            {'name': 'Melbourne City Wrestling', 'about': 'Melbourne City Wrestling is an Australian promotion.'},
            {'name': 'Memphis Wrestling', 'about': 'Memphis Wrestling was the legendary Lawler territory.'},
            {'name': 'Metro Pro Wrestling', 'about': 'Metro Pro Wrestling is a Kansas City indie.'},
            {'name': 'Mid-Eastern Wrestling Federation', 'about': 'MEWF was a Mid-Atlantic indie promotion.'},
            {'name': 'NEO Japan Ladies Pro-Wrestling', 'about': 'NEO was a Japanese women\'s promotion from 2000s.'},
            {'name': 'NOVA Pro Wrestling', 'about': 'NOVA Pro Wrestling is a Virginia indie promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 18')
        return updated

    def enrich_promotions_batch_19(self):
        """Enrich wrestling promotions batch 19."""
        self.stdout.write('--- Enriching Promotions Batch 19 ---')
        updated = 0
        promotions_data = [
            {'name': 'NWA All-Star Wrestling', 'about': 'NWA All-Star was a Pacific Northwest territory.'},
            {'name': 'NWA Hollywood Wrestling', 'about': 'NWA Hollywood was a California territory.'},
            {'name': 'NWA Mid-America', 'about': 'NWA Mid-America was a Tennessee/Kentucky territory.'},
            {'name': 'NWA San Francisco', 'about': 'NWA San Francisco was a Bay Area territory.'},
            {'name': 'NWA Shockwave', 'about': 'NWA Shockwave is a modern NWA affiliate.'},
            {'name': 'NWA Wildside', 'about': 'NWA Wildside was a Georgia indie promotion.'},
            {'name': 'NXT', 'about': 'NXT is WWE\'s developmental brand. Triple H vision.'},
            {'name': 'NXT UK (WWE brand)', 'about': 'NXT UK was WWE\'s British brand until 2022.'},
            {'name': 'Nación Lucha Libre', 'about': 'Nación Lucha Libre is a Mexican promotion.'},
            {'name': 'Naked Women\'s Wrestling League', 'about': 'NWWL was an adult wrestling promotion.'},
            {'name': 'National Wrestling Association', 'about': 'NWA was the original alliance formed in 1948.'},
            {'name': 'National Wrestling Conference', 'about': 'NWC was a regional wrestling conference.'},
            {'name': 'National Wrestling Federation', 'about': 'NWF was a regional wrestling promotion.'},
            {'name': 'New Generation Wrestling', 'about': 'New Generation Wrestling was an indie promotion.'},
            {'name': 'Northern Championship Wrestling', 'about': 'Northern Championship Wrestling is a UK promotion.'},
            {'name': 'Off the Ropes', 'about': 'Off the Ropes was an indie wrestling promotion.'},
            {'name': 'On the Mat', 'about': 'On the Mat was a wrestling production.'},
            {'name': 'One Pro Wrestling', 'about': 'One Pro Wrestling was a UK indie promotion.'},
            {'name': 'Oriental Wrestling Entertainment', 'about': 'OWE is a Chinese wrestling promotion.'},
            {'name': 'Pancrase', 'about': 'Pancrase is a Japanese MMA/shoot wrestling promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 19')
        return updated

    def enrich_promotions_batch_20(self):
        """Enrich wrestling promotions batch 20."""
        self.stdout.write('--- Enriching Promotions Batch 20 ---')
        updated = 0
        promotions_data = [
            {'name': 'Perros del Mal (promotion)', 'about': 'Perros del Mal was a Mexican promotion. Hardcore style.'},
            {'name': 'Philippine Wrestling Revolution', 'about': 'PWR is the top Philippine wrestling promotion.'},
            {'name': 'Phoenix Championship Wrestling', 'about': 'Phoenix Championship Wrestling was an Arizona indie.'},
            {'name': 'Powerful Women of Wrestling', 'about': 'POWW was a women\'s wrestling promotion.'},
            {'name': 'Prairie Wrestling Alliance', 'about': 'Prairie Wrestling Alliance is a Canadian indie.'},
            {'name': 'Pro Championship Wrestling', 'about': 'Pro Championship Wrestling was an indie promotion.'},
            {'name': 'Pro Wrestling Elite', 'about': 'Pro Wrestling Elite was an indie promotion.'},
            {'name': 'Pro Wrestling Federation', 'about': 'Pro Wrestling Federation was a regional promotion.'},
            {'name': 'Pro Wrestling Freedoms', 'about': 'Pro Wrestling Freedoms is a Japanese deathmatch promotion.'},
            {'name': 'Pro Wrestling Fujiwara Gumi', 'about': 'PWFG was a shoot-style promotion. Yoshiaki Fujiwara.'},
            {'name': 'Pro Wrestling Land\'s End', 'about': 'Pro Wrestling Land\'s End was a Japanese promotion.'},
            {'name': 'Pro Wrestling Noah', 'about': 'Pro Wrestling NOAH was founded by Mitsuharu Misawa in 2000.'},
            {'name': 'Pro Wrestling Pride', 'about': 'Pro Wrestling Pride was an indie promotion.'},
            {'name': 'Pro Wrestling USA', 'about': 'Pro Wrestling USA was an 80s alliance of AWA, NWA, WCCW.'},
            {'name': 'Pro-Pain Pro Wrestling', 'about': 'Pro-Pain Pro Wrestling was a hardcore indie.'},
            {'name': 'Pro-Wrestling Basara', 'about': 'Pro-Wrestling Basara is a Japanese indie promotion.'},
            {'name': 'Pro-Wrestling Shi-En', 'about': 'Pro-Wrestling Shi-En is a Japanese promotion.'},
            {'name': 'Pro-Wrestling: EVE', 'about': 'EVE is a British women\'s wrestling promotion.'},
            {'name': 'Professional Wrestling Just Tap Out', 'about': 'JTO is a Japanese promotion founded in 2018.'},
            {'name': 'Promo Azteca', 'about': 'Promo Azteca is a Mexican lucha libre promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 20')
        return updated

    def enrich_promotions_batch_21(self):
        """Enrich wrestling promotions batch 21."""
        self.stdout.write('--- Enriching Promotions Batch 21 ---')
        updated = 0
        promotions_data = [
            {'name': 'Resistance Pro Wrestling', 'about': 'Resistance Pro was a Chicago indie promotion.'},
            {'name': 'Ring Ka King', 'about': 'Ring Ka King was TNA\'s Indian wrestling show.'},
            {'name': 'Ring Warriors', 'about': 'Ring Warriors is a Florida-based wrestling promotion.'},
            {'name': 'Ring of Honor Wrestling', 'about': 'ROH is now owned by Tony Khan and AEW.'},
            {'name': 'Riot City Wrestling', 'about': 'Riot City Wrestling is an Australian promotion.'},
            {'name': 'Shimmer Women Athletes', 'about': 'Shimmer is a women\'s wrestling promotion. Dave Prazak.'},
            {'name': 'Singapore Pro Wrestling', 'about': 'Singapore Pro Wrestling promotes in Southeast Asia.'},
            {'name': 'Smash', 'about': 'Smash was a Japanese promotion from 2010-2012.'},
            {'name': 'Soft Ground Wrestling', 'about': 'Soft Ground Wrestling was an indie promotion.'},
            {'name': 'South Atlantic Pro Wrestling', 'about': 'South Atlantic Pro Wrestling was a regional promotion.'},
            {'name': 'Southern Championship Wrestling (Georgia)', 'about': 'SCW Georgia was a Southern territory.'},
            {'name': 'St. Louis Wrestling Club', 'about': 'St. Louis Wrestling Club was Sam Muchnick\'s legendary territory.'},
            {'name': 'Strong Style Pro-Wrestling', 'about': 'Strong Style Pro-Wrestling was a Japanese promotion.'},
            {'name': 'Super World of Sports', 'about': 'SWS was a short-lived Japanese promotion in 1990s.'},
            {'name': 'Superstars of Wrestling (Canadian TV series)', 'about': 'Superstars of Wrestling was a Canadian wrestling show.'},
            {'name': 'Tenryu Project', 'about': 'Tenryu Project was Genichiro Tenryu\'s promotion.'},
            {'name': 'The Crash Lucha Libre', 'about': 'The Crash is a Tijuana-based lucha libre promotion.'},
            {'name': 'Tokyo Pro Wrestling', 'about': 'Tokyo Pro Wrestling was an early Japanese promotion.'},
            {'name': 'Toryumon (Último Dragón)', 'about': 'Toryumon was Ultimo Dragon\'s developmental system.'},
            {'name': 'Total Nonstop Action Wrestling', 'about': 'TNA Wrestling was founded in 2002. Jeff Jarrett.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 21')
        return updated

    def enrich_promotions_batch_22(self):
        """Enrich wrestling promotions batch 22."""
        self.stdout.write('--- Enriching Promotions Batch 22 ---')
        updated = 0
        promotions_data = [
            {'name': 'Turnbuckle Championship Wrestling', 'about': 'TCW was an indie wrestling promotion.'},
            {'name': 'U-Kei (martial arts)', 'about': 'U-Kei was a martial arts organization.'},
            {'name': 'UWF International', 'about': 'UWFI was a shoot-style wrestling promotion.'},
            {'name': 'United Japan Pro-Wrestling', 'about': 'United Japan Pro-Wrestling was formed in 1953.'},
            {'name': 'United States Wrestling Association', 'about': 'USWA was the Memphis/Dallas merger. Jerry Lawler.'},
            {'name': 'United Wrestling Network', 'about': 'UWN is a modern indie wrestling network.'},
            {'name': 'Universal Lucha Libre', 'about': 'Universal Lucha Libre is a Mexican promotion.'},
            {'name': 'Universal Wrestling Corporation', 'about': 'UWC was a wrestling promotion.'},
            {'name': 'Universal Wrestling Federation (Herb Abrams)', 'about': 'UWF was Herb Abrams\' ill-fated promotion.'},
            {'name': 'Universal Wrestling Federation (Japan)', 'about': 'UWF Japan was a shoot-style pioneer.'},
            {'name': 'Verband der Berufsringer', 'about': 'Verband der Berufsringer is a German wrestling association.'},
            {'name': 'WAR (wrestling promotion)', 'about': 'WAR was Tenryu\'s promotion after leaving AJPW.'},
            {'name': 'WWNLive', 'about': 'WWNLive was Gabe Sapolsky\'s streaming platform.'},
            {'name': 'World Association of Wrestling', 'about': 'WAW is a British promotion. Knight family.'},
            {'name': 'World Championship Wrestling (Australia)', 'about': 'WCW Australia was an Australian promotion.'},
            {'name': 'World Series Wrestling', 'about': 'World Series Wrestling was an Australian show.'},
            {'name': 'World Women\'s Wrestling', 'about': 'World Women\'s Wrestling was a women\'s promotion.'},
            {'name': 'World Wrestling Alliance (Massachusetts)', 'about': 'WWA Massachusetts was a New England indie.'},
            {'name': 'World Wrestling Association', 'about': 'WWA was a Midwest territory. Indianapolis.'},
            {'name': 'World Wrestling Association (Indianapolis)', 'about': 'WWA Indianapolis was Dick the Bruiser\'s territory.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 22')
        return updated

    def enrich_promotions_batch_23(self):
        """Enrich wrestling promotions batch 23."""
        self.stdout.write('--- Enriching Promotions Batch 23 ---')
        updated = 0
        promotions_data = [
            {'name': 'World Wrestling Network', 'about': 'World Wrestling Network was a wrestling organization.'},
            {'name': 'WrestleReunion', 'about': 'WrestleReunion is a wrestling fan convention.'},
            {'name': 'Wrestlicious', 'about': 'Wrestlicious was a women\'s wrestling show with comedy.'},
            {'name': 'Wrestling New Classic', 'about': 'WNC was a Japanese women\'s promotion.'},
            {'name': 'Wrestling Retribution Project', 'about': 'WRP was an indie wrestling project.'},
            {'name': 'Wrestling Superstars Live', 'about': 'WSL was a touring wrestling show.'},
            {'name': 'Wrestling of Darkness 666', 'about': 'Wrestling of Darkness 666 is a horror-themed promotion.'},
            {'name': 'XWA', 'about': 'XWA is a wrestling promotion.'},
            {'name': 'Xcitement Wrestling Federation', 'about': 'XWF was an early 2000s promotion. Jimmy Hart.'},
            {'name': 'Xtreme Latin American Wrestling', 'about': 'XLAW is a Latin American wrestling promotion.'},
        ]
        for data in promotions_data:
            name = data.pop('name')
            updated += self.update_promotion(name, **data)
        self.stdout.write(f'  Updated {updated} promotions batch 23')
        return updated

    def enrich_championships_batch_7(self):
        """Enrich wrestling championships batch 7."""
        self.stdout.write('--- Enriching Championships Batch 7 ---')
        updated = 0
        titles_data = [
            {'name': '1PW Tag Team Championship', 'about': '1PW Tag Team Championship was One Pro Wrestling\'s tag title.'},
            {'name': '1PW Women\'s World Championship', 'about': '1PW Women\'s title was One Pro Wrestling\'s women\'s title.'},
            {'name': '2AW Tag Team Championship', 'about': '2AW Tag Team Championship is a Japanese tag title.'},
            {'name': 'AAA Latin American Championship', 'about': 'AAA Latin American Championship is a regional AAA title.'},
            {'name': 'AAA Mascot Tag Team Championship', 'about': 'AAA Mascot Tag Team title for mini-estrella teams.'},
            {'name': 'AAA Mega Championship', 'about': 'AAA Mega Championship is AAA\'s top title.'},
            {'name': 'AAA Northern Tag Team Championship', 'about': 'AAA Northern Tag Team is a regional AAA tag title.'},
            {'name': 'AAA Reina de Reinas Championship', 'about': 'Reina de Reinas is AAA\'s top women\'s championship.'},
            {'name': 'AAA World Cruiserweight Championship', 'about': 'AAA World Cruiserweight is for lighter wrestlers.'},
            {'name': 'AAA World Mixed Tag Team Championship', 'about': 'AAA Mixed Tag Team is for intergender teams.'},
            {'name': 'AAA World Tag Team Championship', 'about': 'AAA World Tag Team Championship is AAA\'s top tag title.'},
            {'name': 'AAA World Trios Championship', 'about': 'AAA World Trios is for three-person teams.'},
            {'name': 'AAAW Single Championship', 'about': 'AAAW Single Championship is a Japanese women\'s title.'},
            {'name': 'AAW Tag Team Championship', 'about': 'AAW Tag Team Championship is AAW\'s tag team title.'},
            {'name': 'AAW Women\'s Championship', 'about': 'AAW Women\'s Championship is AAW\'s women\'s title.'},
            {'name': 'ACW Tag Team Championship', 'about': 'ACW Tag Team Championship is Anarchy Championship Wrestling\'s tag title.'},
            {'name': 'AEW All-Atlantic Championship', 'about': 'AEW All-Atlantic was renamed Continental Championship.'},
            {'name': 'AEW Tag Team Championship', 'about': 'AEW World Tag Team Championship is AEW\'s top tag title.'},
            {'name': 'AEW Women\'s Championship', 'about': 'AEW Women\'s World Championship is AEW\'s top women\'s title.'},
            {'name': 'AEW Women\'s World Tag Team Championship', 'about': 'AEW Women\'s Tag Team Championship is for women\'s teams.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 7')
        return updated

    def enrich_championships_batch_8(self):
        """Enrich wrestling championships batch 8."""
        self.stdout.write('--- Enriching Championships Batch 8 ---')
        updated = 0
        titles_data = [
            {'name': 'AJPW All Asia Tag Team Championship', 'about': 'AJPW All Asia Tag Team is a prestigious tag title.'},
            {'name': 'AJPW World Junior Heavyweight Championship', 'about': 'AJPW World Junior title is for lighter weight wrestlers.'},
            {'name': 'AJPW World Tag Team Championship', 'about': 'AJPW World Tag Team is All Japan\'s top tag title.'},
            {'name': 'AJW Championship', 'about': 'AJW Championship was All Japan Women\'s top title.'},
            {'name': 'AJW Junior Championship', 'about': 'AJW Junior Championship was for younger AJW wrestlers.'},
            {'name': 'APW Tag Team Championship', 'about': 'APW Tag Team Championship is APW\'s tag team title.'},
            {'name': 'AWA Southern Tag Team Championship', 'about': 'AWA Southern Tag Team was a regional AWA title.'},
            {'name': 'AWA World Women\'s Championship', 'about': 'AWA World Women\'s was the AWA\'s women\'s title.'},
            {'name': 'AWF Tag Team Championship', 'about': 'AWF Tag Team Championship is AWF\'s tag team title.'},
            {'name': 'AWG Single Championship', 'about': 'AWG Single Championship is a joshi wrestling title.'},
            {'name': 'Alberta Tag Team Championship', 'about': 'Alberta Tag Team Championship is a Canadian tag title.'},
            {'name': 'All Asia Tag Team Championship', 'about': 'All Asia Tag Team is a prestigious Japanese tag title.'},
            {'name': 'All Pacific Championship', 'about': 'All Pacific Championship is for Pacific region wrestlers.'},
            {'name': 'Asia Dream Tag Team Championship', 'about': 'Asia Dream Tag Team is a Japanese women\'s tag title.'},
            {'name': 'Asia Tag Team Championship', 'about': 'Asia Tag Team Championship is a regional Asian tag title.'},
            {'name': 'Atlantic Athletic Commission World Heavyweight Championship', 'about': 'AAC World Heavyweight was a regional heavyweight title.'},
            {'name': 'Australian Tag Team Championship', 'about': 'Australian Tag Team Championship is Australia\'s tag title.'},
            {'name': 'BJW Women\'s Championship', 'about': 'BJW Women\'s Championship is Big Japan\'s women\'s title.'},
            {'name': 'BJW World Strong Heavyweight Championship', 'about': 'BJW World Strong Heavyweight is Big Japan\'s strong style title.'},
            {'name': 'Beyond the Sea Single Championship', 'about': 'Beyond the Sea Single is a joshi wrestling title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 8')
        return updated

    def enrich_championships_batch_9(self):
        """Enrich wrestling championships batch 9."""
        self.stdout.write('--- Enriching Championships Batch 9 ---')
        updated = 0
        titles_data = [
            {'name': 'Blast Queen Championship', 'about': 'Blast Queen Championship is a Japanese women\'s title.'},
            {'name': 'CMLL World Heavyweight Championship', 'about': 'CMLL World Heavyweight is CMLL\'s top heavyweight title.'},
            {'name': 'CMLL World Light Heavyweight Championship', 'about': 'CMLL World Light Heavyweight is for lighter heavyweights.'},
            {'name': 'CMLL World Lightweight Championship', 'about': 'CMLL World Lightweight is for lightweight luchadores.'},
            {'name': 'CMLL World Middleweight Championship', 'about': 'CMLL World Middleweight is for middleweight luchadores.'},
            {'name': 'CMLL World Mini-Estrella Championship', 'about': 'CMLL Mini-Estrella is for mini wrestlers.'},
            {'name': 'CMLL World Super Lightweight Championship', 'about': 'CMLL Super Lightweight is for super lightweights.'},
            {'name': 'CMLL World Tag Team Championship', 'about': 'CMLL World Tag Team is CMLL\'s top tag title.'},
            {'name': 'CMLL World Trios Championship', 'about': 'CMLL World Trios is for three-person lucha teams.'},
            {'name': 'CMLL World Welterweight Championship', 'about': 'CMLL World Welterweight is for welterweight luchadores.'},
            {'name': 'CMLL World Womens Championship', 'about': 'CMLL World Women\'s Championship is CMLL\'s women\'s title.'},
            {'name': 'CWA World Heavyweight Championship', 'about': 'CWA World Heavyweight was Continental Wrestling\'s top title.'},
            {'name': 'CWA World Heavyweight Championship (Memphis)', 'about': 'CWA Memphis World Heavyweight was Jerry Lawler\'s title.'},
            {'name': 'Chaotic Wrestling Pan Optic Championship', 'about': 'Chaotic Wrestling Pan Optic is a New England indie title.'},
            {'name': 'DEFY World Championship', 'about': 'DEFY World Championship is Seattle\'s DEFY Wrestling title.'},
            {'name': 'FIP World Heavyweight Championship', 'about': 'FIP World Heavyweight is Full Impact Pro\'s top title.'},
            {'name': 'FMW Brass Knuckles Heavyweight Championship', 'about': 'FMW Brass Knuckles was a hardcore title.'},
            {'name': 'FMW Independent Heavyweight Championship', 'about': 'FMW Independent Heavyweight was FMW\'s secondary title.'},
            {'name': 'G1 Climax Trophy', 'about': 'G1 Climax Trophy is awarded to the G1 Climax winner.'},
            {'name': 'GHC Junior Heavyweight Championship', 'about': 'GHC Junior Heavyweight is NOAH\'s junior title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 9')
        return updated

    def enrich_championships_batch_10(self):
        """Enrich wrestling championships batch 10."""
        self.stdout.write('--- Enriching Championships Batch 10 ---')
        updated = 0
        titles_data = [
            {'name': 'GHC Junior Heavyweight Tag Team Championship', 'about': 'GHC Junior Tag Team is NOAH\'s junior tag title.'},
            {'name': 'IWGP Heavyweight Championship', 'about': 'IWGP Heavyweight was NJPW\'s top title until 2021 unification.'},
            {'name': 'IWGP Intercontinental Championship', 'about': 'IWGP Intercontinental was NJPW\'s secondary title until unification.'},
            {'name': 'IWGP Junior Heavyweight Tag Team Championship', 'about': 'IWGP Junior Tag Team is for junior heavyweight teams.'},
            {'name': 'IWGP Tag Team Championship', 'about': 'IWGP Tag Team Championship is NJPW\'s top tag title.'},
            {'name': 'IWGP United States Heavyweight Championship', 'about': 'IWGP US Heavyweight is NJPW\'s American title.'},
            {'name': 'IWGP World Heavyweight Championship', 'about': 'IWGP World Heavyweight is the unified NJPW top title.'},
            {'name': 'Impact Digital Media Championship', 'about': 'Impact Digital Media Championship is defended online.'},
            {'name': 'Impact Knockouts Championship', 'about': 'Impact Knockouts Championship is Impact\'s women\'s title.'},
            {'name': 'Impact X Division Championship', 'about': 'Impact X Division is for high-flying wrestlers.'},
            {'name': 'King of JTO Championship', 'about': 'King of JTO is Just Tap Out\'s top title.'},
            {'name': 'King of Pro-Wrestling', 'about': 'King of Pro-Wrestling is an NJPW tournament prize.'},
            {'name': 'Legend Championship', 'about': 'Legend Championship is a wrestling title.'},
            {'name': 'Mexican National Heavyweight Championship', 'about': 'Mexican National Heavyweight is Mexico\'s national title.'},
            {'name': 'Mexican National Light Heavyweight Championship', 'about': 'Mexican National Light Heavyweight is a national title.'},
            {'name': 'Mexican National Trios Championship', 'about': 'Mexican National Trios is for three-person teams.'},
            {'name': 'Mexican National Welterweight Championship', 'about': 'Mexican National Welterweight is a national title.'},
            {'name': 'NEVER Openweight 6-Man Tag Team Championship', 'about': 'NEVER 6-Man Tag Team is for six-man teams in NJPW.'},
            {'name': 'NEVER Openweight Championship', 'about': 'NEVER Openweight is NJPW\'s fighting spirit title.'},
            {'name': 'NWA United States Television Championship', 'about': 'NWA US Television is NWA\'s TV title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 10')
        return updated

    def enrich_championships_batch_11(self):
        """Enrich wrestling championships batch 11."""
        self.stdout.write('--- Enriching Championships Batch 11 ---')
        updated = 0
        titles_data = [
            {'name': 'NWA World Women\'s Championship', 'about': 'NWA World Women\'s Championship is NWA\'s women\'s title.'},
            {'name': 'NXT Cruiserweight Championship', 'about': 'NXT Cruiserweight was for lighter wrestlers in NXT.'},
            {'name': 'OVW Rush Division Championship', 'about': 'OVW Rush Division is Ohio Valley Wrestling\'s title.'},
            {'name': 'Open The Owarai Gate Championship', 'about': 'Open The Owarai Gate is Dragon Gate\'s comedy title.'},
            {'name': 'Open The Triangle Gate Championship', 'about': 'Open The Triangle Gate is Dragon Gate\'s trios title.'},
            {'name': 'Open The Twin Gate Championship', 'about': 'Open The Twin Gate is Dragon Gate\'s tag title.'},
            {'name': 'ROH Pure Championship', 'about': 'ROH Pure Championship has strict technical wrestling rules.'},
            {'name': 'ROH Womens World Championship', 'about': 'ROH Women\'s World Championship is ROH\'s women\'s title.'},
            {'name': 'ROH World Six-Man Tag Team Championship', 'about': 'ROH World Six-Man Tag is for six-man teams.'},
            {'name': 'ROH World Tag Team Championship', 'about': 'ROH World Tag Team Championship is ROH\'s tag title.'},
            {'name': 'ROH World Television Championship', 'about': 'ROH World Television Championship is ROH\'s TV title.'},
            {'name': 'TNA Digital Media Championship', 'about': 'TNA Digital Media is defended on digital platforms.'},
            {'name': 'TNA Knockouts Championship', 'about': 'TNA Knockouts Championship is TNA\'s women\'s title.'},
            {'name': 'TNA Knockouts World Championship', 'about': 'TNA Knockouts World is TNA\'s top women\'s title.'},
            {'name': 'TNA Tag Team Championship', 'about': 'TNA Tag Team Championship is TNA\'s tag title.'},
            {'name': 'TNA Television Championship', 'about': 'TNA Television Championship is TNA\'s TV title.'},
            {'name': 'TNA World Championship', 'about': 'TNA World Championship is TNA\'s top title.'},
            {'name': 'TNA World Heavyweight Championship', 'about': 'TNA World Heavyweight is TNA\'s world title.'},
            {'name': 'TNA World Tag Team Championship', 'about': 'TNA World Tag Team is TNA\'s top tag title.'},
            {'name': 'Undisputed WWE Championship', 'about': 'Undisputed WWE Championship is WWE\'s top title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 11')
        return updated

    def enrich_championships_batch_12(self):
        """Enrich wrestling championships batch 12."""
        self.stdout.write('--- Enriching Championships Batch 12 ---')
        updated = 0
        titles_data = [
            {'name': 'WCW Hardcore Championship', 'about': 'WCW Hardcore Championship was WCW\'s hardcore title.'},
            {'name': 'WWE European Championship', 'about': 'WWE European Championship was a secondary WWE title.'},
            {'name': 'WWE Evolve Championship', 'about': 'WWE Evolve Championship was from acquired EVOLVE.'},
            {'name': 'WWE Hardcore Championship', 'about': 'WWE Hardcore Championship had 24/7 rules.'},
            {'name': 'WWE ID Championship', 'about': 'WWE ID Championship is for WWE ID program.'},
            {'name': 'WWE Intercontinental Championship', 'about': 'WWE Intercontinental is WWE\'s prestigious secondary title.'},
            {'name': 'WWE Undisputed Championship', 'about': 'WWE Undisputed was the unified WWF/WCW title.'},
            {'name': 'WWE United States Championship', 'about': 'WWE United States Championship is a secondary title.'},
            {'name': 'WWE World Championship', 'about': 'WWE World Championship is WWE\'s world title.'},
            {'name': 'WWE World Heavyweight Championship', 'about': 'WWE World Heavyweight is SmackDown\'s world title.'},
            {'name': 'WWF Canadian Championship', 'about': 'WWF Canadian Championship was a regional WWF title.'},
            {'name': 'WWF Championship', 'about': 'WWF Championship was WWF\'s top title until name change.'},
            {'name': 'WWF European Championship', 'about': 'WWF European Championship was introduced in 1997.'},
            {'name': 'WWF Intercontinental Championship', 'about': 'WWF Intercontinental is WWF\'s prestigious secondary title.'},
            {'name': 'WWF International Heavyweight Championship', 'about': 'WWF International Heavyweight was a regional title.'},
            {'name': 'WWF Tag Team Championship', 'about': 'WWF Tag Team Championship was WWF\'s tag title.'},
            {'name': 'WWF Women\'s Championship', 'about': 'WWF Women\'s Championship was WWF\'s women\'s title.'},
            {'name': 'World Heavyweight Championship (WWE)', 'about': 'World Heavyweight was WWE\'s secondary world title.'},
            {'name': 'World Heavyweight Championship (WWE, 2002–2013)', 'about': 'World Heavyweight (2002-2013) was Raw\'s world title.'},
        ]
        for data in titles_data:
            name = data.pop('name')
            updated += self.update_title(name, **data)
        self.stdout.write(f'  Updated {updated} championships batch 12')
        return updated

    def enrich_video_games_batch_4(self):
        """Enrich wrestling video games batch 4."""
        self.stdout.write('--- Enriching Video Games Batch 4 ---')
        updated = 0
        games_data = [
            {'name': 'WWE SmackDown vs. Raw Online', 'about': 'WWE SmackDown vs Raw Online was a mobile wrestling game.'},
            {'name': 'WWE SuperCard', 'about': 'WWE SuperCard is a mobile card battle game. Collect superstars.'},
            {'name': 'WWE Survivor Series (video game)', 'about': 'WWE Survivor Series was an arcade wrestling game.'},
            {'name': 'WWE WrestleMania 21 (video game)', 'about': 'WrestleMania 21 was an Xbox exclusive with career mode.'},
            {'name': 'WWE WrestleMania X8 (video game)', 'about': 'WrestleMania X8 was for GameCube. THQ developed.'},
            {'name': 'WWE WrestleMania XIX (video game)', 'about': 'WrestleMania XIX was a GameCube exclusive. Revenge mode.'},
            {'name': 'WWF Betrayal', 'about': 'WWF Betrayal was a Game Boy Color beat-em-up.'},
            {'name': 'WWF European Rampage Tour', 'about': 'WWF European Rampage Tour was an Amiga/DOS game.'},
            {'name': 'WWF King of the Ring (video game)', 'about': 'WWF King of the Ring was an NES/Game Boy game.'},
            {'name': 'WWF No Mercy (video game)', 'about': 'WWF No Mercy is considered one of the best wrestling games.'},
            {'name': 'WWF Rage in the Cage', 'about': 'WWF Rage in the Cage was for Sega CD and 32X.'},
            {'name': 'WWF Raw (1994 video game)', 'about': 'WWF Raw 1994 was for SNES, Genesis, 32X, Game Boy.'},
            {'name': 'WWF Raw (2002 video game)', 'about': 'WWF Raw 2002 was an Xbox exclusive by Anchor.'},
            {'name': 'WWF Road to WrestleMania', 'about': 'WWF Road to WrestleMania was a Game Boy Advance game.'},
            {'name': 'WWF Royal Rumble (1993 video game)', 'about': 'WWF Royal Rumble 1993 was for SNES and Genesis.'},
            {'name': 'WWF Royal Rumble (2000 video game)', 'about': 'WWF Royal Rumble 2000 was for Dreamcast and arcade.'},
            {'name': 'WWF Superstars', 'about': 'WWF Superstars was an arcade game by Technos Japan.'},
            {'name': 'WWF Superstars (handheld video game)', 'about': 'WWF Superstars handheld was a Tiger Electronics game.'},
            {'name': 'WWF War Zone', 'about': 'WWF War Zone was Acclaim\'s first 3D WWF game.'},
            {'name': 'WWF WrestleMania (1991 video game)', 'about': 'WWF WrestleMania 1991 was for NES and Game Boy.'},
            {'name': 'WWF WrestleMania Challenge', 'about': 'WWF WrestleMania Challenge was an NES sequel.'},
            {'name': 'WWF WrestleMania: Steel Cage Challenge', 'about': 'Steel Cage Challenge was for NES, Master System, Game Gear.'},
            {'name': 'WWF WrestleMania: The Arcade Game', 'about': 'WrestleMania Arcade Game was an over-the-top arcade game.'},
            {'name': 'With Authority!', 'about': 'With Authority! was a wrestling game.'},
        ]
        for data in games_data:
            name = data.pop('name')
            updated += self.update_game(name, **data)
        self.stdout.write(f'  Updated {updated} video games batch 4')
        return updated

    def enrich_podcasts_batch_4(self):
        """Enrich wrestling podcasts batch 4."""
        self.stdout.write('--- Enriching Podcasts Batch 4 ---')
        updated = 0
        podcasts_data = [
            {'name': 'Beyond The Matt - WWE Podcast', 'about': 'Beyond The Matt is a WWE-focused fan podcast.'},
            {'name': 'Bushwhacked WWE Podcast', 'about': 'Bushwhacked is a WWE fan podcast.'},
            {'name': 'Dark Side of the Ring: Unheard', 'about': 'Dark Side of the Ring: Unheard is the podcast companion.'},
            {'name': 'E&C\'s Pod of Awesomeness', 'about': 'E&C\'s Pod of Awesomeness was Edge and Christian\'s podcast.'},
            {'name': 'Jim Cornette Experience', 'about': 'Jim Cornette Experience is Jim Cornette\'s main podcast.'},
            {'name': 'Jim Cornette\'s Drive-Thru', 'about': 'Jim Cornette\'s Drive-Thru is his fan Q&A podcast.'},
            {'name': 'Kliq This: The Kevin Nash Podcast', 'about': 'Kliq This is Kevin Nash\'s wrestling podcast.'},
            {'name': 'No-Contest Wrestling', 'about': 'No-Contest Wrestling is a wrestling discussion podcast.'},
            {'name': 'Raw Recap with Sam Roberts and Megan Morant', 'about': 'Raw Recap is WWE\'s official Raw recap show.'},
            {'name': 'Six Feet Under with Mark Calaway', 'about': 'Six Feet Under is The Undertaker\'s podcast.'},
            {'name': 'Six Feet Under with The Undertaker', 'about': 'Six Feet Under features Undertaker discussing his career.'},
            {'name': 'Slam Session - The 100% Unofficial WWE Podcast', 'about': 'Slam Session is an unofficial WWE podcast.'},
            {'name': 'Story Time with Dutch Mantell', 'about': 'Story Time with Dutch Mantell features wrestling stories.'},
            {'name': 'The Attitude Era Podcast', 'about': 'Attitude Era Podcast covers late 90s wrestling.'},
            {'name': 'The Jobbers WWE Podcast', 'about': 'The Jobbers is a WWE fan podcast.'},
            {'name': 'The Ringer Wrestling Show', 'about': 'Ringer Wrestling Show is The Ringer\'s wrestling coverage.'},
            {'name': 'The Steve Austin Show', 'about': 'The Steve Austin Show is Stone Cold\'s podcast.'},
            {'name': 'The Stevie Richards Show', 'about': 'The Stevie Richards Show features the ECW legend.'},
            {'name': 'The WWE Podcast', 'about': 'The WWE Podcast is a WWE-focused show.'},
            {'name': 'WWE Podcast With Aiden', 'about': 'WWE Podcast With Aiden is a fan podcast.'},
            {'name': 'Wade Keller Pro Wrestling Podcast', 'about': 'Wade Keller Pro Wrestling Podcast is from PWTorch.'},
            {'name': 'What Do You Wanna Talk About? with Cody Rhodes', 'about': 'Cody Rhodes\' podcast features wrestling discussions.'},
            {'name': 'What\'s Wrong with Wrestling? WWE Recap Show', 'about': 'What\'s Wrong with Wrestling recaps WWE shows.'},
            {'name': 'What\'s Your Story? with Steph McMahon', 'about': 'What\'s Your Story features Stephanie McMahon interviews.'},
            {'name': 'WhatCulture Wrestling', 'about': 'WhatCulture Wrestling covers wrestling news and reviews.'},
        ]
        for data in podcasts_data:
            name = data.pop('name')
            updated += self.update_podcast(name, **data)
        self.stdout.write(f'  Updated {updated} podcasts batch 4')
        return updated

    def enrich_books_batch_3(self):
        """Enrich wrestling books batch 3."""
        self.stdout.write('--- Enriching Books Batch 3 ---')
        updated = 0
        books_data = [
            {'name': 'A Goffmanian analysis of professional wrestling', 'about': 'A Goffmanian analysis examines wrestling through sociology.'},
            {'name': 'Big Apple Take Down', 'about': 'Big Apple Take Down is a wrestling fiction book.'},
            {'name': 'Hart Strings', 'about': 'Hart Strings covers the Hart wrestling family.'},
            {'name': 'Journey into Darkness: An Unauthorized History of Kane', 'about': 'Journey into Darkness is an unauthorized Kane biography.'},
            {'name': 'WWE Encyclopedia', 'about': 'WWE Encyclopedia is the official WWE reference book.'},
            {'name': 'Professional Wrestling and the Law', 'about': 'Professional Wrestling and the Law examines legal aspects.'},
            {'name': 'Official Professional Wrestling Rulebook', 'about': 'Official Rulebook covers wrestling rules and regulations.'},
            {'name': 'Professional Wrestling in Mississippi', 'about': 'Professional Wrestling in Mississippi covers regional history.'},
            {'name': 'Unscripting Professional Wrestling', 'about': 'Unscripting examines behind-the-scenes wrestling.'},
            {'name': 'WWE Book Of Rules (And How To Make Them)', 'about': 'WWE Book of Rules covers official WWE rules.'},
            {'name': 'WWE Hardcover Ruled Journal', 'about': 'WWE Hardcover Ruled Journal is official WWE merchandise.'},
            {'name': 'Performance and Professional Wrestling', 'about': 'Performance and Professional Wrestling is academic.'},
            {'name': 'WWE : the Ultimate Poster Collection', 'about': 'WWE Ultimate Poster Collection is a poster book.'},
            {'name': 'Ultimate WWE!', 'about': 'Ultimate WWE! is a WWE reference book.'},
            {'name': 'WWE 50', 'about': 'WWE 50 celebrates 50 years of WWE history.'},
            {'name': 'The Hardcore Truth: The Bob Holly Story', 'about': 'The Hardcore Truth is Bob Holly\'s autobiography.'},
            {'name': 'The Squared Circle: Life, Death, and Professional Wrestling', 'about': 'The Squared Circle by David Shoemaker examines wrestling deaths.'},
            {'name': 'Undisputed: How to Become the World Champion in 1,372 Easy Steps', 'about': 'Undisputed is Chris Jericho\'s first autobiography.'},
            {'name': 'WWE Confidential (WWE)', 'about': 'WWE Confidential was a behind-the-scenes WWE book.'},
            {'name': 'A Lion\'s Tale: Around the World in Spandex', 'about': 'A Lion\'s Tale is Chris Jericho\'s second book.'},
            {'name': 'WWE legends', 'about': 'WWE Legends covers legendary WWE superstars.'},
            {'name': 'The encyclopedia of professional wrestling', 'about': 'Encyclopedia of Professional Wrestling is a reference.'},
            {'name': 'Bobby the Brain: Wrestling\'s Bad Boy Tells All', 'about': 'Bobby the Brain is Bobby Heenan\'s autobiography.'},
            {'name': 'It\'s Good to Be the King...Sometimes', 'about': 'It\'s Good to Be the King is Jerry Lawler\'s autobiography.'},
            {'name': 'Sex, Lies, and Headlocks', 'about': 'Sex, Lies, and Headlocks chronicles WWE\'s rise.'},
            {'name': 'The buzz on professional wrestling', 'about': 'The Buzz on Professional Wrestling examines the industry.'},
            {'name': 'Professional Wrestling Collectibles', 'about': 'Professional Wrestling Collectibles covers memorabilia.'},
        ]
        for data in books_data:
            name = data.pop('name')
            updated += self.update_book(name, **data)
        self.stdout.write(f'  Updated {updated} books batch 3')
        return updated

    def enrich_stables_batch_3(self):
        """Enrich wrestling stables batch 3."""
        self.stdout.write('--- Enriching Stables Batch 3 ---')
        updated = 0
        stables_data = [
            {'name': 'House of Torture', 'about': 'House of Torture is an NJPW heel faction. EVIL leads.'},
            {'name': 'Los Hell Brothers', 'about': 'Los Hell Brothers is a lucha libre tag team/faction.'},
            {'name': 'Los Jinetes del Aire', 'about': 'Los Jinetes del Aire is a high-flying lucha faction.'},
            {'name': 'Los Mercenarios', 'about': 'Los Mercenarios is a rudo faction in Mexico.'},
            {'name': 'Los Vipers', 'about': 'Los Vipers is a Mexican wrestling faction.'},
            {'name': 'TMDK', 'about': 'TMDK is The Mighty Don\'t Kneel. Shane Haste and Mikey Nicholls.'},
            {'name': 'United Empire', 'about': 'United Empire is Will Ospreay\'s NJPW faction.'},
        ]
        for data in stables_data:
            name = data.pop('name')
            updated += self.update_stable(name, **data)
        self.stdout.write(f'  Updated {updated} stables batch 3')
        return updated
