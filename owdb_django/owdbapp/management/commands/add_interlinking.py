"""
Add interlinking between related database entries.
Connects wrestlers to their stables, promotions to their titles, etc.

Usage:
    python manage.py add_interlinking --type=stables
    python manage.py add_interlinking --type=all
"""
from django.core.management.base import BaseCommand
from owdb_django.owdbapp.models import (
    Wrestler, Promotion, Title, Stable
)


class Command(BaseCommand):
    help = 'Add interlinking between related database entries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            help='Type of interlinking: stables, promotions, all'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        link_type = options.get('type', 'all')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        self.stdout.write(self.style.SUCCESS(f'\n=== Adding Interlinking ({link_type}) ===\n'))

        if link_type in ['all', 'stables']:
            self.link_wrestlers_to_stables(dry_run)

        self.stdout.write(self.style.SUCCESS('\n=== Interlinking Complete ===\n'))

    def link_wrestlers_to_stables(self, dry_run):
        """Link wrestlers to their stables based on known memberships."""
        self.stdout.write('\n--- Linking Wrestlers to Stables ---\n')

        # Define stable memberships (stable_name: [wrestler_names])
        stable_members = {
            "The Four Horsemen": [
                "Ric Flair", "Arn Anderson", "Tully Blanchard", "Barry Windham",
                "Ole Anderson", "Lex Luger", "Sid Vicious", "Brian Pillman",
                "Chris Benoit", "Dean Malenko", "Steve McMichael"
            ],
            "nWo": [
                "Hollywood Hulk Hogan", "Hulk Hogan", "Kevin Nash", "Scott Hall",
                "Syxx", "X-Pac", "The Giant", "Big Show", "Randy Savage",
                "Scott Steiner", "Buff Bagwell", "Konnan", "Curt Hennig"
            ],
            "D-Generation X": [
                "Triple H", "Shawn Michaels", "Chyna", "X-Pac", "Road Dogg",
                "Billy Gunn", "Rick Rude", "Hornswoggle"
            ],
            "The Shield": [
                "Roman Reigns", "Seth Rollins", "Dean Ambrose", "Jon Moxley"
            ],
            "Evolution": [
                "Triple H", "Ric Flair", "Randy Orton", "Batista", "Dave Bautista"
            ],
            "The Nexus": [
                "Wade Barrett", "Justin Gabriel", "Heath Slater", "David Otunga",
                "Michael Tarver", "Skip Sheffield", "Ryback", "Daniel Bryan",
                "Darren Young", "Husky Harris", "Bray Wyatt"
            ],
            "The Corporation": [
                "Vince McMahon", "Shane McMahon", "The Rock", "Big Boss Man",
                "Test", "Ken Shamrock", "Sgt. Slaughter"
            ],
            "The Ministry of Darkness": [
                "The Undertaker", "Paul Bearer", "Viscera", "Mideon", "Gangrel",
                "Edge", "Christian", "Bradshaw", "Faarooq"
            ],
            "The Hart Foundation": [
                "Bret Hart", "Owen Hart", "Jim Neidhart", "British Bulldog",
                "Brian Pillman"
            ],
            "The Nation of Domination": [
                "The Rock", "Faarooq", "D'Lo Brown", "Kama Mustafa", "Godfather",
                "Mark Henry"
            ],
            "The Wyatt Family": [
                "Bray Wyatt", "Luke Harper", "Erick Rowan", "Braun Strowman"
            ],
            "The New Day": [
                "Kofi Kingston", "Big E", "Xavier Woods"
            ],
            "The Bullet Club": [
                "AJ Styles", "Kenny Omega", "The Young Bucks", "Nick Jackson",
                "Matt Jackson", "Finn Balor", "Karl Anderson", "Luke Gallows",
                "Marty Scurll", "Cody Rhodes", "Hangman Adam Page", "Adam Page",
                "Jay White", "Kenta"
            ],
            "Los Ingobernables de Japon": [
                "Tetsuya Naito", "Evil", "Sanada", "Hiromu Takahashi", "Bushi"
            ],
            "The Bloodline": [
                "Roman Reigns", "Jimmy Uso", "Jey Uso", "Solo Sikoa"
            ],
            "The Judgment Day": [
                "Rhea Ripley", "Damian Priest", "Finn Balor", "Dominik Mysterio",
                "JD McDonagh"
            ],
            "The Elite": [
                "Kenny Omega", "The Young Bucks", "Nick Jackson", "Matt Jackson",
                "Cody Rhodes", "Hangman Adam Page", "Adam Page"
            ],
            "Inner Circle": [
                "Chris Jericho", "Sammy Guevara", "Jake Hager", "Ortiz", "Santana",
                "MJF"
            ],
            "The Dark Order": [
                "Brodie Lee", "Evil Uno", "Stu Grayson", "John Silver", "Alex Reynolds",
                "Anna Jay", "Preston Vance", "Colt Cabana"
            ],
            "Team Extreme": [
                "Jeff Hardy", "Matt Hardy", "Lita"
            ],
            "Too Cool": [
                "Scotty 2 Hotty", "Grandmaster Sexay", "Rikishi"
            ],
            "The Brood": [
                "Edge", "Christian", "Gangrel"
            ],
            "The Freebirds": [
                "Michael Hayes", "Terry Gordy", "Buddy Roberts", "Jimmy Garvin"
            ],
            "The Midnight Express": [
                "Bobby Eaton", "Dennis Condrey", "Stan Lane"
            ],
            "The Road Warriors": [
                "Hawk", "Animal", "Road Warrior Hawk", "Road Warrior Animal"
            ],
            "The Dangerous Alliance": [
                "Paul Heyman", "Steve Austin", "Rick Rude", "Arn Anderson",
                "Bobby Eaton", "Larry Zbyszko", "Madusa"
            ],
            "The Horsewomen": [
                "Charlotte Flair", "Sasha Banks", "Bayley", "Becky Lynch"
            ],
            "Damage CTRL": [
                "Bayley", "Dakota Kai", "Iyo Sky"
            ],
            "Undisputed Era": [
                "Adam Cole", "Kyle O'Reilly", "Bobby Fish", "Roderick Strong"
            ],
            "The Club": [
                "AJ Styles", "Karl Anderson", "Luke Gallows"
            ],
            "The Heenan Family": [
                "Bobby Heenan", "Andre the Giant", "King Kong Bundy", "Big John Studd",
                "Paul Orndorff", "Hercules", "Rick Rude", "Haku", "The Brain Busters",
                "Arn Anderson", "Tully Blanchard", "Mr. Perfect"
            ],
            "The Dungeon of Doom": [
                "Kevin Sullivan", "The Giant", "Big Show", "Kamala", "Meng",
                "The Shark", "One Man Gang"
            ],
            "The Wolfpac": [
                "Kevin Nash", "Lex Luger", "Sting", "Randy Savage", "Konnan"
            ],
            "Latino World Order": [
                "Eddie Guerrero", "Chavo Guerrero", "Psychosis", "Juventud Guerrera"
            ],
        }

        total_links = 0

        for stable_name, member_names in stable_members.items():
            stable = Stable.objects.filter(name=stable_name).first()
            if not stable:
                self.stdout.write(f'  ! Stable not found: {stable_name}')
                continue

            links = 0
            for member_name in member_names:
                # Try exact match first
                wrestler = Wrestler.objects.filter(name=member_name).first()

                # Try case-insensitive match
                if not wrestler:
                    wrestler = Wrestler.objects.filter(name__iexact=member_name).first()

                # Try contains match
                if not wrestler:
                    wrestler = Wrestler.objects.filter(name__icontains=member_name).first()

                if wrestler:
                    # Check if already linked
                    if stable.members.filter(pk=wrestler.pk).exists():
                        continue

                    if not dry_run:
                        stable.members.add(wrestler)
                    links += 1

            if links > 0:
                self.stdout.write(f'  + {stable_name}: {links} members linked')
                total_links += links

        self.stdout.write(f'\nTotal links added: {total_links}')
