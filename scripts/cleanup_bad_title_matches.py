#!/usr/bin/env python
"""Clean up incorrectly assigned title matches."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title, Wrestler

print('=== CLEANING UP BAD TITLE MATCHES ===')
print()

# Define gender for known wrestlers
MALE_WRESTLERS = {
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
}

FEMALE_WRESTLERS = {
    'Charlotte Flair', 'Becky Lynch', 'Sasha Banks', 'Bayley', 'Asuka', 'Alexa Bliss',
    'Rhea Ripley', 'Bianca Belair', 'Trish Stratus', 'Lita', 'Chyna', 'Beth Phoenix',
    'Natalya', 'Naomi', 'Carmella', 'Nikki Bella', 'Brie Bella', 'Paige',
    'Ronda Rousey', 'Shayna Baszler', 'Britt Baker', 'Thunder Rosa', 'Jade Cargill',
    'Toni Storm', 'Saraya', 'Hikaru Shida', 'Riho', 'Nyla Rose', 'Kris Statlander',
    'Penelope Ford', 'Anna Jay', 'Tay Conti', 'Ruby Soho', 'Jamie Hayter',
    'Willow Nightingale', 'Mercedes Mone', 'Iyo Sky', 'Dakota Kai', 'Kairi Sane',
    'Liv Morgan', 'Lacey Evans', 'Nia Jax', 'Tamina', 'Sonya Deville', 'Mandy Rose',
    'Zelina Vega', 'Mickie James', 'Gail Kim', 'Awesome Kong', 'Tara', 'Brooke Tessmacher'
}

# 1. Fix women's title matches with male winners/participants
print('1. FIXING WOMENS TITLE MATCHES:')
womens_titles = Title.objects.filter(name__icontains='women') | Title.objects.filter(name__icontains='knockouts') | Title.objects.filter(name__icontains='diva')

fixed_count = 0
for title in womens_titles:
    bad_matches = Match.objects.filter(title=title)
    for m in bad_matches:
        wrestlers = set(w.name for w in m.wrestlers.all())

        # Check if any male wrestlers are in the match
        has_male = bool(wrestlers & MALE_WRESTLERS)

        # Check if no female wrestlers in match
        has_female = bool(wrestlers & FEMALE_WRESTLERS)

        if has_male and not has_female:
            # This is a synthetic match - clear the title
            m.title = None
            m.save(update_fields=['title'])
            fixed_count += 1

print(f'  Cleared title from {fixed_count} matches with only male wrestlers')

# 2. Fix men's title matches with only female participants
print()
print('2. FIXING MENS TITLE MATCHES:')
mens_titles = Title.objects.exclude(name__icontains='women').exclude(name__icontains='knockouts').exclude(name__icontains='diva').exclude(name__icontains='mixed')

fixed_count2 = 0
for title in mens_titles:
    bad_matches = Match.objects.filter(title=title)
    for m in bad_matches:
        wrestlers = set(w.name for w in m.wrestlers.all())

        # Check if only female wrestlers
        has_male = bool(wrestlers & MALE_WRESTLERS)
        has_female = bool(wrestlers & FEMALE_WRESTLERS)

        if has_female and not has_male:
            # This is wrong - women shouldn't be in men's title matches
            m.title = None
            m.save(update_fields=['title'])
            fixed_count2 += 1

print(f'  Cleared title from {fixed_count2} matches with only female wrestlers')

# 3. Verify the fix
print()
print('3. VERIFICATION:')
remaining_issues = 0
for title in womens_titles:
    bad = Match.objects.filter(title=title).filter(winner__name__in=list(MALE_WRESTLERS)).count()
    if bad > 0:
        print(f'  {title.name}: {bad} male winners remaining')
        remaining_issues += bad

print(f'  Total remaining gender mismatches: {remaining_issues}')

# 4. Stats
print()
print('4. FINAL STATS:')
total_title_matches = Match.objects.exclude(title__isnull=True).count()
print(f'  Total title matches remaining: {total_title_matches}')
