"""
Management command to seed the database with sample wrestling data.
Data sourced from Wikipedia for accuracy.
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from datetime import date
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Event, Match, Title, Venue,
    VideoGame, Podcast, Book, Special
)


class Command(BaseCommand):
    help = 'Seeds the database with sample wrestling data from Wikipedia'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database with wrestling data...')

        # Create Promotions
        self.stdout.write('Creating promotions...')
        promotions = self.create_promotions()

        # Create Venues
        self.stdout.write('Creating venues...')
        venues = self.create_venues()

        # Create Wrestlers
        self.stdout.write('Creating wrestlers...')
        wrestlers = self.create_wrestlers()

        # Create Titles
        self.stdout.write('Creating titles...')
        titles = self.create_titles(promotions)

        # Create Events
        self.stdout.write('Creating events...')
        events = self.create_events(promotions, venues)

        # Create Matches
        self.stdout.write('Creating matches...')
        self.create_matches(events, wrestlers, titles)

        # Create Video Games
        self.stdout.write('Creating video games...')
        self.create_video_games(promotions)

        # Create Podcasts
        self.stdout.write('Creating podcasts...')
        self.create_podcasts(wrestlers)

        # Create Books
        self.stdout.write('Creating books...')
        self.create_books(wrestlers)

        # Create Specials/Documentaries
        self.stdout.write('Creating specials...')
        self.create_specials(wrestlers)

        self.stdout.write(self.style.SUCCESS('Database seeded successfully!'))

    def create_promotions(self):
        promotions_data = [
            {
                'name': 'World Wrestling Entertainment',
                'abbreviation': 'WWE',
                'founded_year': 1952,
                'website': 'https://www.wwe.com',
                'about': 'World Wrestling Entertainment, Inc., d/b/a WWE, is an American professional wrestling promotion based in Stamford, Connecticut. WWE is the largest wrestling promotion in the world, reaching 16 million viewers in the U.S. It holds over 500 events a year and is broadcast to about 1 billion homes worldwide in 30 languages.',
                'nicknames': 'The Fed, Sports Entertainment'
            },
            {
                'name': 'All Elite Wrestling',
                'abbreviation': 'AEW',
                'founded_year': 2019,
                'website': 'https://www.allelitewrestling.com',
                'about': 'All Elite Wrestling (AEW) is an American professional wrestling promotion headquartered in Jacksonville, Florida. It was founded by Tony Khan (who also serves as its CEO and head of creative), alongside wrestling veterans Cody Rhodes, Matt Jackson, Nick Jackson, and Kenny Omega.',
                'nicknames': 'The alternative, The good guys'
            },
            {
                'name': 'New Japan Pro-Wrestling',
                'abbreviation': 'NJPW',
                'founded_year': 1972,
                'website': 'https://www.njpw1972.com',
                'about': 'New Japan Pro-Wrestling Co., Ltd. is a Japanese professional wrestling promotion based in Nakano, Tokyo. NJPW is the largest professional wrestling promotion in Japan and the second largest in the world. It is known for its strong style wrestling and has produced many legendary wrestlers.',
                'nicknames': 'Strong Style, King of Sports'
            },
            {
                'name': 'Impact Wrestling',
                'abbreviation': 'IMPACT',
                'founded_year': 2002,
                'website': 'https://impactwrestling.com',
                'about': 'Impact Wrestling, formerly known as TNA (Total Nonstop Action) Wrestling, is an American professional wrestling promotion based in Nashville, Tennessee. It was founded by Jeff and Jerry Jarrett in 2002 and has been home to many notable wrestlers throughout its history.',
                'nicknames': 'TNA, The Land of Opportunity'
            },
            {
                'name': 'Ring of Honor',
                'abbreviation': 'ROH',
                'founded_year': 2002,
                'website': 'https://www.rohwrestling.com',
                'about': 'Ring of Honor (ROH) is an American professional wrestling promotion based in Baltimore, Maryland. Known for its emphasis on in-ring competition, ROH has been credited with helping launch the careers of many top wrestlers including Bryan Danielson, CM Punk, and Samoa Joe.',
                'nicknames': 'Honor, Pure Wrestling'
            },
        ]

        promotions = {}
        for data in promotions_data:
            promo, created = Promotion.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            promotions[data['abbreviation']] = promo
            if created:
                self.stdout.write(f'  Created: {promo.name}')

        return promotions

    def create_venues(self):
        venues_data = [
            {
                'name': 'Madison Square Garden',
                'location': 'New York City, New York, USA',
                'capacity': 20789,
            },
            {
                'name': 'Allegiant Stadium',
                'location': 'Las Vegas, Nevada, USA',
                'capacity': 65000,
            },
            {
                'name': 'Tokyo Dome',
                'location': 'Tokyo, Japan',
                'capacity': 55000,
            },
            {
                'name': 'Wembley Stadium',
                'location': 'London, England, UK',
                'capacity': 90000,
            },
            {
                'name': 'AT&T Stadium',
                'location': 'Arlington, Texas, USA',
                'capacity': 80000,
            },
        ]

        venues = {}
        for data in venues_data:
            venue, created = Venue.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            venues[data['name']] = venue
            if created:
                self.stdout.write(f'  Created: {venue.name}')

        return venues

    def create_wrestlers(self):
        wrestlers_data = [
            {
                'name': 'Stone Cold Steve Austin',
                'real_name': 'Steven James Anderson',
                'debut_year': 1989,
                'retirement_year': 2003,
                'hometown': 'Victoria, Texas',
                'nationality': 'American',
                'finishers': 'Stone Cold Stunner, Lou Thesz Press',
                'aliases': 'The Texas Rattlesnake, The Bionic Redneck, Stunning Steve Austin, The Ringmaster',
                'about': 'Stone Cold Steve Austin is an American retired professional wrestler and actor, widely regarded as one of the greatest and most influential professional wrestlers of all time. He was the central figure of the Attitude Era, a boom period in business for the WWF in the late 1990s.',
            },
            {
                'name': 'The Rock',
                'real_name': 'Dwayne Douglas Johnson',
                'debut_year': 1996,
                'hometown': 'Hayward, California',
                'nationality': 'American',
                'finishers': "Rock Bottom, People's Elbow",
                'aliases': "Rocky Maivia, The People's Champion, The Great One, The Brahma Bull",
                'about': 'Dwayne "The Rock" Johnson is a professional wrestler and actor. One of the greatest professional wrestlers of all time, he wrestled for WWE for eight years prior to pursuing an acting career. He is regarded as one of the most charismatic wrestlers ever.',
            },
            {
                'name': 'John Cena',
                'real_name': 'John Felix Anthony Cena Jr.',
                'debut_year': 2000,
                'hometown': 'West Newbury, Massachusetts',
                'nationality': 'American',
                'finishers': 'Attitude Adjustment, STF',
                'aliases': 'The Champ, The Face That Runs The Place, The Cenation Leader',
                'about': 'John Cena is an American professional wrestler and actor. Widely regarded as one of the greatest professional wrestlers of all time, he is tied with Ric Flair for the most world championship reigns in WWE history with 16.',
            },
            {
                'name': 'CM Punk',
                'real_name': 'Phillip Jack Brooks',
                'debut_year': 1999,
                'hometown': 'Chicago, Illinois',
                'nationality': 'American',
                'finishers': 'Go To Sleep (GTS), Anaconda Vise',
                'aliases': 'The Best in the World, The Voice of the Voiceless, The Second City Saint',
                'about': 'CM Punk is an American professional wrestler. Known for his outspoken personality and technical wrestling ability, he is a two-time WWE Champion and delivered the famous "Pipe Bomb" promo in 2011.',
            },
            {
                'name': 'Kazuchika Okada',
                'real_name': 'Kazuchika Okada',
                'debut_year': 2004,
                'hometown': 'Anjo, Aichi, Japan',
                'nationality': 'Japanese',
                'finishers': 'Rainmaker (Short-Arm Lariat), Money Clip',
                'aliases': 'The Rainmaker',
                'about': 'Kazuchika Okada is a Japanese professional wrestler. He is a five-time IWGP Heavyweight Champion and is regarded as one of the best wrestlers in the world, known for his athleticism, charisma, and main event caliber matches.',
            },
        ]

        wrestlers = {}
        for data in wrestlers_data:
            wrestler, created = Wrestler.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            wrestlers[data['name']] = wrestler
            if created:
                self.stdout.write(f'  Created: {wrestler.name}')

        return wrestlers

    def create_titles(self, promotions):
        titles_data = [
            {
                'name': 'WWE Championship',
                'promotion': promotions['WWE'],
                'debut_year': 1963,
                'about': 'The WWE Championship is the top championship in WWE and has been held by legends like Hulk Hogan, Stone Cold Steve Austin, The Rock, John Cena, and many more.',
            },
            {
                'name': 'AEW World Championship',
                'promotion': promotions['AEW'],
                'debut_year': 2019,
                'about': 'The AEW World Championship is the top title in All Elite Wrestling. Chris Jericho was the inaugural champion.',
            },
            {
                'name': 'IWGP World Heavyweight Championship',
                'promotion': promotions['NJPW'],
                'debut_year': 2021,
                'about': 'The IWGP World Heavyweight Championship is the top title in New Japan Pro-Wrestling, unified from the IWGP Heavyweight and Intercontinental Championships.',
            },
            {
                'name': 'Impact World Championship',
                'promotion': promotions['IMPACT'],
                'debut_year': 2007,
                'about': 'The Impact World Championship (formerly the TNA World Heavyweight Championship) is the top title in Impact Wrestling.',
            },
            {
                'name': 'ROH World Championship',
                'promotion': promotions['ROH'],
                'debut_year': 2002,
                'about': 'The ROH World Championship is the top title in Ring of Honor, having been held by many wrestling legends.',
            },
        ]

        titles = {}
        for data in titles_data:
            title, created = Title.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            titles[data['name']] = title
            if created:
                self.stdout.write(f'  Created: {title.name}')

        return titles

    def create_events(self, promotions, venues):
        events_data = [
            {
                'name': 'WrestleMania 40',
                'promotion': promotions['WWE'],
                'venue': venues['Allegiant Stadium'],
                'date': date(2024, 4, 6),
                'attendance': 72000,
                'about': 'WrestleMania 40 (also known as WrestleMania XL) was the fortieth annual WrestleMania professional wrestling pay-per-view event produced by WWE.',
            },
            {
                'name': 'AEW All In',
                'promotion': promotions['AEW'],
                'venue': venues['Wembley Stadium'],
                'date': date(2023, 8, 27),
                'attendance': 81035,
                'about': 'All In was a professional wrestling pay-per-view event held by AEW at Wembley Stadium in London. It was the largest wrestling event held in the UK.',
            },
            {
                'name': 'Wrestle Kingdom 18',
                'promotion': promotions['NJPW'],
                'venue': venues['Tokyo Dome'],
                'date': date(2024, 1, 4),
                'attendance': 26000,
                'about': 'Wrestle Kingdom 18 was a professional wrestling pay-per-view event produced by NJPW at the Tokyo Dome in Tokyo, Japan.',
            },
            {
                'name': 'WrestleMania III',
                'promotion': promotions['WWE'],
                'venue': venues['AT&T Stadium'],
                'date': date(1987, 3, 29),
                'attendance': 93173,
                'about': 'WrestleMania III was the third annual WrestleMania professional wrestling pay-per-view, famous for the Hulk Hogan vs Andre the Giant match.',
            },
            {
                'name': 'Supercard of Honor',
                'promotion': promotions['ROH'],
                'venue': venues['Madison Square Garden'],
                'date': date(2023, 4, 1),
                'attendance': 5800,
                'about': 'Supercard of Honor is an annual professional wrestling event produced by Ring of Honor.',
            },
        ]

        events = {}
        for data in events_data:
            event, created = Event.objects.get_or_create(
                name=data['name'],
                date=data['date'],
                defaults=data
            )
            events[data['name']] = event
            if created:
                self.stdout.write(f'  Created: {event.name}')

        return events

    def create_matches(self, events, wrestlers, titles):
        matches_data = [
            {
                'event': events['WrestleMania 40'],
                'match_text': 'Cody Rhodes vs Roman Reigns - WWE Championship',
                'match_type': 'Singles Match',
                'result': 'Win',
                'match_order': 1,
                'about': 'Cody Rhodes finished his story by defeating Roman Reigns for the WWE Championship.',
            },
            {
                'event': events['AEW All In'],
                'match_text': 'CM Punk vs Samoa Joe - AEW World Championship',
                'match_type': 'Singles Match',
                'result': 'Win',
                'match_order': 1,
                'about': 'CM Punk faced Samoa Joe in the main event of All In at Wembley Stadium.',
            },
            {
                'event': events['Wrestle Kingdom 18'],
                'match_text': 'Kazuchika Okada vs Tetsuya Naito - IWGP World Heavyweight Championship',
                'match_type': 'Singles Match',
                'result': 'Win',
                'match_order': 1,
                'about': 'Okada defended the IWGP World Heavyweight Championship against Naito at the Tokyo Dome.',
            },
            {
                'event': events['WrestleMania III'],
                'match_text': 'Hulk Hogan vs Andre the Giant - WWF Championship',
                'match_type': 'Singles Match',
                'result': 'Win',
                'match_order': 1,
                'about': 'The legendary match where Hulk Hogan bodyslammed Andre the Giant in front of over 93,000 fans.',
            },
            {
                'event': events['Supercard of Honor'],
                'match_text': 'Claudio Castagnoli vs Eddie Kingston - ROH World Championship',
                'match_type': 'Singles Match',
                'result': 'Win',
                'match_order': 1,
                'about': 'A hard-hitting match for the ROH World Championship.',
            },
        ]

        for data in matches_data:
            match, created = Match.objects.get_or_create(
                event=data['event'],
                match_text=data['match_text'],
                defaults=data
            )
            if created:
                # Add wrestlers to the match
                if 'Stone Cold' in data['match_text'] or 'Austin' in data['match_text']:
                    if 'Stone Cold Steve Austin' in wrestlers:
                        match.wrestlers.add(wrestlers['Stone Cold Steve Austin'])
                if 'Rock' in data['match_text']:
                    if 'The Rock' in wrestlers:
                        match.wrestlers.add(wrestlers['The Rock'])
                if 'Cena' in data['match_text']:
                    if 'John Cena' in wrestlers:
                        match.wrestlers.add(wrestlers['John Cena'])
                if 'CM Punk' in data['match_text']:
                    if 'CM Punk' in wrestlers:
                        match.wrestlers.add(wrestlers['CM Punk'])
                if 'Okada' in data['match_text']:
                    if 'Kazuchika Okada' in wrestlers:
                        match.wrestlers.add(wrestlers['Kazuchika Okada'])

                self.stdout.write(f'  Created: {match.match_text}')

    def create_video_games(self, promotions):
        games_data = [
            {
                'name': 'WWE 2K24',
                'release_year': 2024,
                'systems': 'PS5, Xbox Series X/S, PS4, Xbox One, PC',
                'developer': 'Visual Concepts',
                'publisher': '2K Sports',
                'about': 'WWE 2K24 is a professional wrestling video game featuring a roster of WWE superstars past and present.',
            },
            {
                'name': 'AEW: Fight Forever',
                'release_year': 2023,
                'systems': 'PS5, Xbox Series X/S, PS4, Xbox One, PC, Switch',
                'developer': 'Yuke\'s',
                'publisher': 'THQ Nordic',
                'about': 'AEW: Fight Forever is a professional wrestling video game based on All Elite Wrestling.',
            },
            {
                'name': 'WWE 2K23',
                'release_year': 2023,
                'systems': 'PS5, Xbox Series X/S, PS4, Xbox One, PC',
                'developer': 'Visual Concepts',
                'publisher': '2K Sports',
                'about': 'WWE 2K23 features John Cena on the cover and includes the Showcase mode based on his career.',
            },
            {
                'name': 'Fire Pro Wrestling World',
                'release_year': 2017,
                'systems': 'PS4, PC',
                'developer': 'Spike Chunsoft',
                'publisher': 'Spike Chunsoft',
                'about': 'Fire Pro Wrestling World is a professional wrestling video game featuring customizable wrestlers and a deep simulation engine.',
            },
            {
                'name': 'WWF No Mercy',
                'release_year': 2000,
                'systems': 'Nintendo 64',
                'developer': 'AKI Corporation',
                'publisher': 'THQ',
                'about': 'WWF No Mercy is widely considered one of the greatest wrestling video games ever made, known for its gameplay and customization options.',
            },
        ]

        for data in games_data:
            game, created = VideoGame.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                if 'WWE' in data['name'] or 'WWF' in data['name']:
                    game.promotions.add(promotions['WWE'])
                if 'AEW' in data['name']:
                    game.promotions.add(promotions['AEW'])
                self.stdout.write(f'  Created: {game.name}')

    def create_podcasts(self, wrestlers):
        podcasts_data = [
            {
                'name': 'Something to Wrestle with Bruce Prichard',
                'hosts': 'Bruce Prichard, Conrad Thompson',
                'launch_year': 2016,
                'url': 'https://www.stwpodcast.com',
                'about': 'A weekly podcast where Bruce Prichard shares behind-the-scenes stories from his time in WWE and wrestling.',
            },
            {
                'name': 'Talk Is Jericho',
                'hosts': 'Chris Jericho',
                'launch_year': 2013,
                'url': 'https://omny.fm/shows/talk-is-jericho',
                'about': 'Chris Jericho interviews wrestlers, musicians, actors, and other entertainers.',
            },
            {
                'name': 'Grilling JR',
                'hosts': 'Jim Ross, Conrad Thompson',
                'launch_year': 2018,
                'about': 'WWE Hall of Famer Jim Ross shares stories and recaps classic WWE events.',
            },
            {
                'name': 'The New Day: Feel the Power',
                'hosts': 'Xavier Woods, Kofi Kingston, Big E',
                'launch_year': 2019,
                'about': 'The New Day members discuss wrestling, gaming, and pop culture.',
            },
            {
                'name': 'Busted Open Radio',
                'hosts': 'Dave LaGreca, Bully Ray',
                'launch_year': 2006,
                'about': 'A daily wrestling talk show covering all major promotions and wrestling news.',
            },
        ]

        for data in podcasts_data:
            podcast, created = Podcast.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created: {podcast.name}')

    def create_books(self, wrestlers):
        books_data = [
            {
                'title': 'Have A Nice Day: A Tale of Blood and Sweatsocks',
                'author': 'Mick Foley',
                'publication_year': 1999,
                'publisher': 'ReganBooks',
                'isbn': '978-0060392994',
                'about': 'Mick Foley\'s autobiography became a New York Times bestseller, detailing his journey in professional wrestling.',
            },
            {
                'title': 'The Rock Says...',
                'author': 'Dwayne Johnson',
                'publication_year': 2000,
                'publisher': 'ReganBooks',
                'isbn': '978-0060392307',
                'about': 'The Rock\'s autobiography covering his early life, football career, and rise in WWE.',
            },
            {
                'title': 'Hitman: My Real Life in the Cartoon World of Wrestling',
                'author': 'Bret Hart',
                'publication_year': 2007,
                'publisher': 'Grand Central Publishing',
                'isbn': '978-0446539388',
                'about': 'Bret "The Hitman" Hart\'s autobiography covering his legendary wrestling career and family legacy.',
            },
            {
                'title': 'Death of WCW',
                'author': 'Bryan Alvarez, R.D. Reynolds',
                'publication_year': 2004,
                'publisher': 'ECW Press',
                'isbn': '978-1550226614',
                'about': 'A detailed look at the rise and fall of World Championship Wrestling.',
            },
            {
                'title': 'Yes!: My Improbable Journey to the Main Event of WrestleMania',
                'author': 'Daniel Bryan',
                'publication_year': 2015,
                'publisher': 'St. Martin\'s Press',
                'isbn': '978-1250067920',
                'about': 'Daniel Bryan\'s autobiography about his journey from indie wrestling to WWE main eventer.',
            },
        ]

        for data in books_data:
            book, created = Book.objects.get_or_create(
                title=data['title'],
                defaults=data
            )
            if created:
                # Link related wrestlers
                if 'Rock' in data['author'] and 'The Rock' in wrestlers:
                    book.related_wrestlers.add(wrestlers['The Rock'])
                self.stdout.write(f'  Created: {book.title}')

    def create_specials(self, wrestlers):
        specials_data = [
            {
                'title': 'Andre the Giant',
                'release_year': 2018,
                'type': 'documentary',
                'about': 'HBO documentary exploring the life and legacy of Andre the Giant, directed by Jason Hehir.',
            },
            {
                'title': 'The Resurrection of Jake The Snake',
                'release_year': 2015,
                'type': 'documentary',
                'about': 'Documentary about Jake "The Snake" Roberts\' recovery from addiction with help from DDP.',
            },
            {
                'title': 'Beyond the Mat',
                'release_year': 1999,
                'type': 'documentary',
                'about': 'Barry Blaustein\'s documentary exploring the real lives of professional wrestlers.',
            },
            {
                'title': 'WWE: The Monday Night War',
                'release_year': 2014,
                'type': 'series',
                'about': 'Documentary series about the rating war between WWF Raw and WCW Nitro in the late 1990s.',
            },
            {
                'title': 'Dark Side of the Ring',
                'release_year': 2019,
                'type': 'series',
                'about': 'Documentary series exploring the controversial and tragic stories in professional wrestling history.',
            },
        ]

        for data in specials_data:
            special, created = Special.objects.get_or_create(
                title=data['title'],
                defaults=data
            )
            if created:
                self.stdout.write(f'  Created: {special.title}')
