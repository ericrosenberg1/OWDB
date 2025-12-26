#!/usr/bin/env python
"""Fast cleanup of incorrect title assignments using bulk operations."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title, Wrestler
from django.db.models import Q

print('=== FAST TITLE CLEANUP ===')
print()

# Get wrestler IDs by gender
MALE_NAMES = [
    'MJF', 'Jon Moxley', 'Roman Reigns', 'Seth Rollins', 'Randy Savage', 'Batista',
    'Mark Henry', 'Matt Hardy', 'Jeff Hardy', 'Andrade', 'Triple H', 'The Rock',
    'Bret Hart', 'Cesaro', 'Keith Lee', 'Jungle Boy', 'AJ Styles', 'Sheamus',
    'Brock Lesnar', 'CM Punk', 'Bryan Danielson', 'Samoa Joe', 'Dean Ambrose',
    'Daniel Bryan', 'John Cena', 'Drew McIntyre', 'Bobby Lashley', 'The Undertaker',
    'Rey Mysterio', 'Dustin Rhodes', 'Austin Aries', 'Mr. Anderson', 'Wardlow',
    'Matt Morgan', 'Alex Shelley', 'Sting', 'Kenny Omega', 'Cody Rhodes', 'Adam Cole',
    'Hangman Adam Page', 'Orange Cassidy', 'Pac', 'Miro', 'Darby Allin', 'Ricky Starks',
    'Swerve Strickland', 'Will Ospreay', 'Hook', 'Eddie Kingston', 'Luchasaurus',
    'Lance Archer', 'Mick Foley', 'Edge', 'Kevin Owens', 'Dolph Ziggler', 'Goldberg',
    'Kane', 'Big Show', 'Kofi Kingston', 'Shawn Michaels', 'Stone Cold Steve Austin',
    'Hulk Hogan', 'Randy Orton', 'Booker T', 'Kurt Angle', 'Rob Van Dam', 'Ric Flair',
    'Chris Jericho', 'Eddie Guerrero', 'Rey Fenix', 'Penta El Zero Miedo', 'Ortiz',
    'Santana', 'Powerhouse Hobbs', 'Rhino', 'Abyss', 'Bobby Roode', 'Magnus',
    'Christopher Daniels', 'Frankie Kazarian', 'Bully Ray', 'Eric Young', 'James Storm',
    'Jeff Jarrett', 'Taz', 'The Sandman', 'Rhyno', 'Lance Storm', 'Steve Corino',
    'Sami Zayn', 'Big E', 'Rick Steiner', 'Scott Steiner'
]

male_wrestler_ids = set(Wrestler.objects.filter(name__in=MALE_NAMES).values_list('id', flat=True))
print(f'Found {len(male_wrestler_ids)} male wrestlers')

# Get women's title IDs
womens_title_ids = list(Title.objects.filter(
    Q(name__icontains='women') | Q(name__icontains='knockouts') | Q(name__icontains='diva')
).values_list('id', flat=True))
print(f'Found {len(womens_title_ids)} womens titles')

# Clear title from matches where:
# 1. It's a women's title
# 2. The winner is a male wrestler
print()
print('Clearing titles from women title matches with male winners...')

updated = Match.objects.filter(
    title_id__in=womens_title_ids,
    winner_id__in=male_wrestler_ids
).update(title=None)

print(f'Cleared title from {updated} matches')

# Check remaining issues
print()
print('Verifying...')
remaining = Match.objects.filter(
    title_id__in=womens_title_ids,
    winner_id__in=male_wrestler_ids
).count()
print(f'Remaining gender mismatches: {remaining}')

# Final stats
print()
print('Final stats:')
total_title_matches = Match.objects.exclude(title__isnull=True).count()
print(f'Total title matches: {total_title_matches}')
