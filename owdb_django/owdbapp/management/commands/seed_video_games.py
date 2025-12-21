"""
Comprehensive Wrestling Video Games Seeder.

Adds all historic wrestling video games from 1987-2025 with wrestler rosters linked.
Covers WWE, WCW, ECW, TNA, AEW, NJPW, and more across all platforms.

Usage:
    python manage.py seed_video_games
"""
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from owdb_django.owdbapp.models import VideoGame, Wrestler, Promotion


class Command(BaseCommand):
    help = 'Seed comprehensive wrestling video game database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== SEEDING VIDEO GAMES ===\n'))

        total_created = 0
        total_linked = 0

        # WWE/WWF Games
        created, linked = self.seed_wwe_games()
        total_created += created
        total_linked += linked

        # WCW Games
        created, linked = self.seed_wcw_games()
        total_created += created
        total_linked += linked

        # ECW Games
        created, linked = self.seed_ecw_games()
        total_created += created
        total_linked += linked

        # TNA Games
        created, linked = self.seed_tna_games()
        total_created += created
        total_linked += linked

        # AEW Games
        created, linked = self.seed_aew_games()
        total_created += created
        total_linked += linked

        # Other/Multi-promotion Games
        created, linked = self.seed_other_games()
        total_created += created
        total_linked += linked

        self.stdout.write(self.style.SUCCESS(f'\n=== COMPLETE ==='))
        self.stdout.write(f'Games created: {total_created}')
        self.stdout.write(f'Wrestler links: {total_linked}')
        self.stdout.write(f'Total games in DB: {VideoGame.objects.count()}')

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

    def create_game(self, name, year, systems, developer, publisher, roster_names, about=None):
        """Create a video game with roster links."""
        slug = slugify(f"{name}-{year}")

        game, created = VideoGame.objects.get_or_create(
            slug=slug,
            defaults={
                'name': name,
                'release_year': year,
                'systems': systems,
                'developer': developer,
                'publisher': publisher,
                'about': about or f"{name} ({year})"
            }
        )

        linked = 0
        if roster_names:
            for wrestler_name in roster_names:
                wrestler = self.get_or_create_wrestler(wrestler_name)
                if wrestler and wrestler not in game.wrestlers.all():
                    game.wrestlers.add(wrestler)
                    linked += 1

        return created, linked

    def seed_wwe_games(self):
        """Seed WWE/WWF video games."""
        self.stdout.write('--- Seeding WWE/WWF Games ---')
        created_count = 0
        linked_count = 0

        # WWE 2K Series (2013-2024)
        wwe_2k_rosters = {
            2024: ['Roman Reigns', 'Cody Rhodes', 'Seth Rollins', 'Rhea Ripley', 'Bianca Belair',
                   'Becky Lynch', 'Charlotte Flair', 'Randy Orton', 'John Cena', 'Drew McIntyre',
                   'CM Punk', 'The Rock', 'Stone Cold Steve Austin', 'The Undertaker', 'Brock Lesnar',
                   'Triple H', 'Shawn Michaels', 'Kevin Owens', 'Sami Zayn', 'LA Knight',
                   'Gunther', 'Damian Priest', 'Jey Uso', 'Jimmy Uso', 'Solo Sikoa'],
            2023: ['Roman Reigns', 'Cody Rhodes', 'Seth Rollins', 'Bianca Belair', 'Becky Lynch',
                   'Charlotte Flair', 'Randy Orton', 'Brock Lesnar', 'Drew McIntyre', 'Edge',
                   'Undertaker', 'Triple H', 'Shawn Michaels', 'Stone Cold Steve Austin'],
            2022: ['Roman Reigns', 'Brock Lesnar', 'Becky Lynch', 'Bianca Belair', 'Edge',
                   'Rey Mysterio', 'The Undertaker', 'Kane', 'Mankind', 'The Rock'],
            2020: ['Roman Reigns', 'Brock Lesnar', 'Becky Lynch', 'Seth Rollins', 'AJ Styles',
                   'Kofi Kingston', 'Daniel Bryan', 'Randy Orton', 'The Undertaker', 'Hulk Hogan'],
            2019: ['AJ Styles', 'Shinsuke Nakamura', 'Ronda Rousey', 'Charlotte Flair',
                   'Daniel Bryan', 'The Miz', 'Triple H', 'The Undertaker', 'Randy Orton'],
            2018: ['Seth Rollins', 'AJ Styles', 'Brock Lesnar', 'Finn Balor', 'Kevin Owens',
                   'John Cena', 'The Undertaker', 'Kurt Angle', 'Triple H', 'Goldberg'],
            2017: ['AJ Styles', 'Brock Lesnar', 'John Cena', 'Randy Orton', 'Dean Ambrose',
                   'Seth Rollins', 'Roman Reigns', 'The Undertaker', 'Goldberg', 'Shawn Michaels'],
            2016: ['Stone Cold Steve Austin', 'The Rock', 'The Undertaker', 'Shawn Michaels',
                   'John Cena', 'Brock Lesnar', 'Seth Rollins', 'Roman Reigns', 'Dean Ambrose'],
            2015: ['John Cena', 'Randy Orton', 'Roman Reigns', 'Dean Ambrose', 'Seth Rollins',
                   'Bray Wyatt', 'Undertaker', 'Triple H', 'Hulk Hogan', 'Ultimate Warrior'],
            2014: ['Daniel Bryan', 'John Cena', 'CM Punk', 'Randy Orton', 'The Rock',
                   'Brock Lesnar', 'Undertaker', 'Triple H', 'Shawn Michaels', 'Stone Cold Steve Austin'],
        }

        for year, roster in wwe_2k_rosters.items():
            c, l = self.create_game(
                f'WWE 2K{year % 100}', year,
                'PS5, Xbox Series X/S, PS4, Xbox One, PC' if year >= 2022 else 'PS4, Xbox One, PC',
                'Visual Concepts', '2K Sports', roster,
                f'WWE 2K{year % 100} - Annual WWE simulation wrestling game'
            )
            created_count += c
            linked_count += l

        # WWE SmackDown vs Raw Series (2004-2011)
        svr_rosters = {
            2011: ['John Cena', 'Randy Orton', 'Triple H', 'Undertaker', 'Rey Mysterio',
                   'Chris Jericho', 'Edge', 'Big Show', 'Kane', 'Shawn Michaels'],
            2010: ['John Cena', 'Triple H', 'Randy Orton', 'Batista', 'Undertaker',
                   'Shawn Michaels', 'Edge', 'Chris Jericho', 'Rey Mysterio', 'Jeff Hardy'],
            2009: ['Triple H', 'John Cena', 'Randy Orton', 'Batista', 'Undertaker',
                   'Shawn Michaels', 'Edge', 'Chris Jericho', 'CM Punk', 'Jeff Hardy'],
            2008: ['John Cena', 'Bobby Lashley', 'Edge', 'Batista', 'Undertaker',
                   'Shawn Michaels', 'Triple H', 'Kane', 'Rey Mysterio', 'Mr. Kennedy'],
            2007: ['John Cena', 'Triple H', 'Batista', 'Undertaker', 'Shawn Michaels',
                   'Edge', 'Kurt Angle', 'Randy Orton', 'Rey Mysterio', 'Kane'],
            2006: ['Batista', 'John Cena', 'Triple H', 'Undertaker', 'Shawn Michaels',
                   'Randy Orton', 'Eddie Guerrero', 'Rey Mysterio', 'Kurt Angle', 'JBL'],
        }

        for year, roster in svr_rosters.items():
            c, l = self.create_game(
                f'WWE SmackDown vs. Raw {year}', year - 1,
                'PS3, Xbox 360, PS2, PSP, Wii',
                'Yuke\'s', 'THQ', roster
            )
            created_count += c
            linked_count += l

        # Classic WWF/WWE Games
        classic_games = [
            ('WWF WrestleMania', 1989, 'NES', 'Rare', 'Acclaim',
             ['Hulk Hogan', 'Andre the Giant', 'Randy Savage', 'Ted DiBiase', 'Bam Bam Bigelow', 'Honky Tonk Man']),
            ('WWF WrestleMania Challenge', 1990, 'NES', 'Rare', 'LJN',
             ['Hulk Hogan', 'Ultimate Warrior', 'Andre the Giant', 'Randy Savage', 'Big Boss Man', 'Ravishing Rick Rude']),
            ('WWF Super WrestleMania', 1992, 'SNES, Genesis', 'Sculptured Software', 'LJN',
             ['Hulk Hogan', 'Ultimate Warrior', 'Randy Savage', 'Ted DiBiase', 'Earthquake', 'Legion of Doom']),
            ('WWF Royal Rumble', 1993, 'SNES, Genesis', 'Sculptured Software', 'LJN',
             ['Bret Hart', 'Randy Savage', 'Undertaker', 'Shawn Michaels', 'Ric Flair', 'Razor Ramon']),
            ('WWF Raw', 1994, 'SNES, Genesis, 32X', 'Sculptured Software', 'Acclaim',
             ['Bret Hart', 'Shawn Michaels', 'Undertaker', 'Diesel', 'Razor Ramon', 'Yokozuna', '1-2-3 Kid', 'Lex Luger']),
            ('WWF WrestleMania: The Arcade Game', 1995, 'Arcade, SNES, Genesis, PS1, Saturn',
             'Midway', 'Acclaim', ['Bret Hart', 'Shawn Michaels', 'Undertaker', 'Razor Ramon', 'Yokozuna', 'Doink the Clown', 'Lex Luger', 'Bam Bam Bigelow']),
            ('WWF In Your House', 1996, 'PS1, Saturn, PC', 'Sculptured Software', 'Acclaim',
             ['Bret Hart', 'Shawn Michaels', 'Undertaker', 'Ultimate Warrior', 'Goldust', 'Vader', 'Owen Hart', 'British Bulldog', 'Ahmed Johnson', 'Hunter Hearst Helmsley']),
            ('WWF War Zone', 1998, 'PS1, N64, PC', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Stone Cold Steve Austin', 'The Rock', 'Undertaker', 'Shawn Michaels', 'Triple H', 'Kane', 'Mankind', 'British Bulldog', 'Ken Shamrock', 'Ahmed Johnson']),
            ('WWF Attitude', 1999, 'PS1, N64, Dreamcast, Game Boy Color', 'Iguana Entertainment', 'Acclaim',
             ['Stone Cold Steve Austin', 'The Rock', 'Undertaker', 'Mankind', 'Kane', 'Triple H', 'Shawn Michaels', 'X-Pac', 'Road Dogg', 'Billy Gunn', 'Ken Shamrock', 'Big Boss Man', 'Val Venis', 'Godfather', 'Mark Henry']),
            ('WWF SmackDown!', 2000, 'PS1', 'Yuke\'s', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Mankind', 'Kane', 'Big Show', 'Chris Jericho', 'Kurt Angle', 'Edge', 'Christian', 'Hardy Boyz', 'Dudley Boyz']),
            ('WWF SmackDown! 2: Know Your Role', 2000, 'PS1', 'Yuke\'s', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Mick Foley', 'Kane', 'Chris Jericho', 'Kurt Angle', 'Rikishi', 'Edge', 'Christian']),
            ('WWF SmackDown! Just Bring It', 2001, 'PS2', 'Yuke\'s', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Kurt Angle', 'Chris Jericho', 'Kane', 'Rob Van Dam', 'Booker T', 'Diamond Dallas Page']),
            ('WWE SmackDown! Shut Your Mouth', 2002, 'PS2', 'Yuke\'s', 'THQ',
             ['The Rock', 'Stone Cold Steve Austin', 'Triple H', 'Undertaker', 'Kurt Angle', 'Hulk Hogan', 'Ric Flair', 'Brock Lesnar', 'Chris Jericho', 'Rob Van Dam']),
            ('WWE SmackDown! Here Comes the Pain', 2003, 'PS2', 'Yuke\'s', 'THQ',
             ['Brock Lesnar', 'Kurt Angle', 'Undertaker', 'Big Show', 'Chris Benoit', 'Eddie Guerrero', 'Rey Mysterio', 'John Cena', 'Goldberg', 'Hulk Hogan', 'Stone Cold Steve Austin', 'The Rock']),
            ('WWE SmackDown! vs. Raw', 2004, 'PS2, PSP', 'Yuke\'s', 'THQ',
             ['Eddie Guerrero', 'John Cena', 'JBL', 'Undertaker', 'Triple H', 'Chris Benoit', 'Randy Orton', 'Batista', 'Edge', 'Kurt Angle', 'Shawn Michaels', 'Mick Foley', 'Brock Lesnar']),
            ('WWE Day of Reckoning', 2004, 'GameCube', 'Yuke\'s', 'THQ',
             ['Triple H', 'Shawn Michaels', 'Chris Benoit', 'Randy Orton', 'Batista', 'Edge', 'Chris Jericho', 'Kane', 'Undertaker', 'Goldberg']),
            ('WWE Day of Reckoning 2', 2005, 'GameCube', 'Yuke\'s', 'THQ',
             ['Batista', 'Triple H', 'Edge', 'John Cena', 'Randy Orton', 'Undertaker', 'Shawn Michaels', 'Eddie Guerrero', 'JBL', 'Kurt Angle']),
            ('WWE All Stars', 2011, 'PS3, Xbox 360, Wii, PS2, PSP, 3DS', 'THQ San Diego', 'THQ',
             ['John Cena', 'Randy Orton', 'Rey Mysterio', 'Triple H', 'Undertaker', 'Shawn Michaels', 'Hulk Hogan', 'Ultimate Warrior', 'Macho Man Randy Savage', 'Stone Cold Steve Austin', 'The Rock', 'Bret Hart', 'Eddie Guerrero', 'Mr. Perfect', 'Ricky Steamboat']),
            ('WWE 12', 2011, 'PS3, Xbox 360, Wii', 'Yuke\'s', 'THQ',
             ['John Cena', 'Randy Orton', 'Triple H', 'Undertaker', 'CM Punk', 'Sheamus', 'Alberto Del Rio', 'Rey Mysterio', 'The Miz', 'Edge']),
            ('WWE 13', 2012, 'PS3, Xbox 360, Wii', 'Yuke\'s', 'THQ',
             ['CM Punk', 'John Cena', 'Randy Orton', 'Triple H', 'Undertaker', 'Sheamus', 'Kane', 'Daniel Bryan', 'Stone Cold Steve Austin', 'The Rock', 'Shawn Michaels', 'Bret Hart', 'Mankind']),
        ]

        for game_data in classic_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        # WWF No Mercy and AKI Games
        aki_games = [
            ('WWF WrestleMania 2000', 1999, 'N64', 'AKI Corporation', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Mankind', 'Kane', 'Big Show', 'X-Pac', 'Road Dogg', 'Billy Gunn', 'Al Snow', 'Ken Shamrock', 'Test', 'Big Boss Man']),
            ('WWF No Mercy', 2000, 'N64', 'AKI Corporation', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Mankind', 'Kane', 'Chris Jericho', 'Kurt Angle', 'Chris Benoit', 'Eddie Guerrero', 'Edge', 'Christian', 'Hardy Boyz', 'Dudley Boyz', 'Rikishi', 'Too Cool']),
        ]

        for game_data in aki_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} WWE games, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_wcw_games(self):
        """Seed WCW video games."""
        self.stdout.write('--- Seeding WCW Games ---')
        created_count = 0
        linked_count = 0

        wcw_games = [
            ('WCW SuperBrawl Wrestling', 1994, 'SNES', 'Beam Software', 'FCI',
             ['Sting', 'Ric Flair', 'Vader', 'Ricky Steamboat', 'Barry Windham', 'Dustin Rhodes', 'Rick Rude', 'Ron Simmons', 'Steve Austin', 'Brian Pillman', 'Johnny B. Badd', 'Arn Anderson']),
            ('WCW vs. the World', 1997, 'PS1', 'AKI Corporation', 'THQ',
             ['Hulk Hogan', 'Sting', 'Ric Flair', 'Lex Luger', 'Randy Savage', 'The Giant', 'Diamond Dallas Page', 'Steiner Brothers', 'Harlem Heat']),
            ('WCW/nWo World Tour', 1997, 'N64', 'AKI Corporation', 'THQ',
             ['Hulk Hogan', 'Sting', 'Ric Flair', 'Randy Savage', 'The Giant', 'Lex Luger', 'Kevin Nash', 'Scott Hall', 'Diamond Dallas Page', 'Chris Benoit', 'Eddie Guerrero', 'Rey Mysterio', 'Dean Malenko']),
            ('WCW Nitro', 1998, 'PS1, N64, PC', 'Inland Productions', 'THQ',
             ['Hulk Hogan', 'Sting', 'Goldberg', 'Kevin Nash', 'Scott Hall', 'Diamond Dallas Page', 'Lex Luger', 'Randy Savage', 'Bret Hart', 'Chris Jericho']),
            ('WCW/nWo Revenge', 1998, 'N64', 'AKI Corporation', 'THQ',
             ['Hulk Hogan', 'Sting', 'Goldberg', 'Kevin Nash', 'Scott Hall', 'Diamond Dallas Page', 'Lex Luger', 'Randy Savage', 'Bret Hart', 'Chris Jericho', 'Eddie Guerrero', 'Rey Mysterio', 'Chris Benoit', 'Dean Malenko', 'Raven', 'Booker T']),
            ('WCW Thunder', 1998, 'PS1', 'Inland Productions', 'THQ',
             ['Goldberg', 'Hulk Hogan', 'Sting', 'Kevin Nash', 'Scott Hall', 'Diamond Dallas Page', 'Bret Hart', 'Lex Luger']),
            ('WCW Mayhem', 1999, 'PS1, N64', 'Kodiak Interactive', 'EA Sports',
             ['Goldberg', 'Hulk Hogan', 'Sting', 'Ric Flair', 'Kevin Nash', 'Scott Hall', 'Diamond Dallas Page', 'Bret Hart', 'Randy Savage', 'Buff Bagwell', 'Scott Steiner', 'Booker T']),
            ('WCW Backstage Assault', 2000, 'PS1, N64', 'Kodiak Interactive', 'EA Sports',
             ['Goldberg', 'Sting', 'Hulk Hogan', 'Kevin Nash', 'Scott Steiner', 'Booker T', 'Jeff Jarrett', 'Diamond Dallas Page']),
        ]

        for game_data in wcw_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} WCW games, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_ecw_games(self):
        """Seed ECW video games."""
        self.stdout.write('--- Seeding ECW Games ---')
        created_count = 0
        linked_count = 0

        ecw_games = [
            ('ECW Hardcore Revolution', 2000, 'PS1, N64, Dreamcast', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Tommy Dreamer', 'Rob Van Dam', 'Sabu', 'Taz', 'Raven', 'Sandman', 'Shane Douglas', 'Jerry Lynn', 'Mike Awesome', 'Masato Tanaka', 'New Jack', 'Balls Mahoney', 'Axl Rotten', 'Justin Credible', 'Lance Storm', 'Rhino', 'Tajiri', 'Super Crazy', 'Spike Dudley', 'Bubba Ray Dudley', 'D-Von Dudley']),
            ('ECW Anarchy Rulz', 2000, 'PS1, Dreamcast', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Tommy Dreamer', 'Rob Van Dam', 'Sabu', 'Raven', 'Sandman', 'Rhino', 'Jerry Lynn', 'Justin Credible', 'Lance Storm', 'Tajiri', 'Super Crazy', 'Yoshihiro Tajiri', 'Steve Corino', 'CW Anderson']),
        ]

        for game_data in ecw_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} ECW games, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_tna_games(self):
        """Seed TNA/Impact video games."""
        self.stdout.write('--- Seeding TNA Games ---')
        created_count = 0
        linked_count = 0

        tna_games = [
            ('TNA Impact!', 2008, 'PS3, Xbox 360, PS2, Wii', 'Midway Studios Los Angeles', 'Midway',
             ['AJ Styles', 'Samoa Joe', 'Kurt Angle', 'Sting', 'Christian Cage', 'Booker T', 'Kevin Nash', 'Scott Steiner', 'Team 3D', 'Jay Lethal', 'Abyss', 'Rhino', 'Jeff Jarrett', 'Christopher Daniels', 'Tomko']),
            ('TNA Impact: Cross the Line', 2010, 'PSP, DS', 'Midway Studios Los Angeles', 'SouthPeak Games',
             ['AJ Styles', 'Samoa Joe', 'Kurt Angle', 'Sting', 'Jeff Hardy', 'Mr. Anderson', 'Rob Van Dam', 'Abyss', 'Desmond Wolfe']),
        ]

        for game_data in tna_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} TNA games, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_aew_games(self):
        """Seed AEW video games."""
        self.stdout.write('--- Seeding AEW Games ---')
        created_count = 0
        linked_count = 0

        aew_games = [
            ('AEW: Fight Forever', 2023, 'PS5, Xbox Series X/S, PS4, Xbox One, PC, Switch', 'Yuke\'s', 'THQ Nordic',
             ['Kenny Omega', 'Jon Moxley', 'Chris Jericho', 'Cody Rhodes', 'Hangman Adam Page', 'MJF', 'CM Punk', 'Bryan Danielson', 'Adam Cole', 'Jade Cargill', 'Britt Baker', 'Thunder Rosa', 'Orange Cassidy', 'Darby Allin', 'Sting', 'Miro', 'PAC', 'Penta El Zero M', 'Rey Fenix', 'Jungle Boy', 'Luchasaurus', 'Christian Cage', 'Matt Hardy', 'Jeff Hardy', 'Powerhouse Hobbs', 'Ricky Starks', 'Wardlow', 'Toni Storm', 'Hikaru Shida', 'Riho', 'Nyla Rose', 'Kris Statlander', 'Ruby Soho', 'Jamie Hayter', 'Paul Wight', 'Mark Henry', 'Danhausen']),
        ]

        for game_data in aew_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} AEW games, {linked_count} wrestler links')
        return created_count, linked_count

    def seed_other_games(self):
        """Seed other wrestling games (Fire Pro, NJPW, Legends, etc.)."""
        self.stdout.write('--- Seeding Other Wrestling Games ---')
        created_count = 0
        linked_count = 0

        other_games = [
            # Fire Pro Wrestling Series
            ('Fire Pro Wrestling World', 2017, 'PS4, PC', 'Spike Chunsoft', 'Spike Chunsoft',
             ['Kenny Omega', 'Kazuchika Okada', 'Hiroshi Tanahashi', 'Tetsuya Naito', 'NJPW Roster']),
            ('Fire Pro Wrestling Returns', 2005, 'PS2', 'Spike', 'Agetec',
             ['Custom Wrestlers', 'Generic Roster']),

            # NJPW Games
            ('NJPW Strong Spirits', 2022, 'Mobile', 'Bushiroad', 'Bushiroad',
             ['Kazuchika Okada', 'Hiroshi Tanahashi', 'Tetsuya Naito', 'Kenny Omega', 'Will Ospreay', 'Jay White']),

            # Legends Games
            ('Legends of Wrestling', 2002, 'PS2, Xbox, GameCube', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Hulk Hogan', 'Ultimate Warrior', 'Bret Hart', 'Rob Van Dam', 'Terry Funk', 'Jimmy Snuka', 'George Steele', 'Ricky Steamboat', 'Iron Sheik', 'Sgt. Slaughter', 'Nikolai Volkoff', 'Captain Lou Albano', 'King Kong Bundy']),
            ('Legends of Wrestling II', 2002, 'PS2, Xbox, GameCube', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Hulk Hogan', 'Andre the Giant', 'Bret Hart', 'Owen Hart', 'Ted DiBiase', 'Roddy Piper', 'Randy Savage', 'Ultimate Warrior', 'Ric Flair', 'Ricky Steamboat', 'Terry Funk', 'Dusty Rhodes']),
            ('Showdown: Legends of Wrestling', 2004, 'PS2, Xbox', 'Acclaim Studios Salt Lake City', 'Acclaim',
             ['Hulk Hogan', 'Bret Hart', 'Ultimate Warrior', 'Randy Savage', 'Ric Flair', 'British Bulldog', 'Mr. Perfect', 'Jerry Lawler']),

            # Rumble Roses
            ('Rumble Roses', 2004, 'PS2', 'Konami', 'Konami',
             ['Female Wrestling Cast']),
            ('Rumble Roses XX', 2006, 'Xbox 360', 'Konami', 'Konami',
             ['Female Wrestling Cast']),

            # Def Jam Wrestling Games
            ('Def Jam Vendetta', 2003, 'PS2, GameCube', 'AKI Corporation', 'EA Sports Big',
             ['Hip-hop Artists']),
            ('Def Jam: Fight for NY', 2004, 'PS2, Xbox, GameCube', 'AKI Corporation', 'EA Sports Big',
             ['Hip-hop Artists']),

            # Wrestling Empire
            ('Wrestling Empire', 2021, 'PC, Switch, Mobile', 'MDickie', 'MDickie',
             ['Custom Wrestlers']),

            # RetroMania Wrestling
            ('RetroMania Wrestling', 2021, 'PS4, Xbox One, Switch, PC', 'RetroSoft Studios', 'RetroSoft Studios',
             ['Tommy Dreamer', 'Colt Cabana', 'Matt Cardona', 'Nick Aldis', 'Austin Idol', 'Stevie Richards', 'Blue Meanie', 'Warhorse']),

            # Action Arcade Wrestling
            ('Action Arcade Wrestling', 2019, 'PC, PS4, Xbox One', 'VICO Game Studio', 'VICO Game Studio',
             ['Custom Wrestlers']),

            # Virtual Pro Wrestling (Japan)
            ('Virtual Pro Wrestling 2', 2000, 'N64', 'AKI Corporation', 'Asmik Ace Entertainment',
             ['NJPW Roster', 'All Japan Roster']),

            # King of Colosseum
            ('King of Colosseum II', 2004, 'PS2', 'Spike', 'Spike',
             ['NJPW Roster', 'NOAH Roster']),

            # WWE Crush Hour (vehicular combat)
            ('WWE Crush Hour', 2003, 'PS2, GameCube', 'Pacific Coast Power & Light', 'THQ',
             ['Stone Cold Steve Austin', 'The Rock', 'Triple H', 'Undertaker', 'Kurt Angle', 'Rob Van Dam']),

            # Backyard Wrestling
            ('Backyard Wrestling: Don\'t Try This at Home', 2003, 'PS2, Xbox', 'Paradox Development', 'Eidos Interactive',
             ['New Jack', 'Sabu', 'Sandman', 'Sick Nick Mondo', 'Insane Clown Posse']),
            ('Backyard Wrestling 2: There Goes the Neighborhood', 2004, 'PS2, Xbox', 'Paradox Development', 'Eidos Interactive',
             ['New Jack', 'Sabu', 'Sandman']),
        ]

        for game_data in other_games:
            c, l = self.create_game(*game_data)
            created_count += c
            linked_count += l

        self.stdout.write(f'  Created {created_count} other games, {linked_count} wrestler links')
        return created_count, linked_count
