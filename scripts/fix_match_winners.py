#!/usr/bin/env python
"""Fix match winner assignments by parsing the result field."""
import os
import sys
import django
import re

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Wrestler

print('=== FIXING MATCH WINNERS ===')
print()

def extract_winner_from_result(result):
    """Extract winner name from result text like 'Cody Rhodes wins by pinfall'"""
    if not result:
        return None

    # Pattern: "Name wins by ..." or "Name win by ..."
    match = re.match(r'^(.+?)\s+wins?\s+by\s+', result, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None

# First, let's test the extraction
print('1. TESTING WINNER EXTRACTION:')
test_results = [
    'Cody Rhodes wins by pinfall',
    'The Undertaker wins by submission',
    'MJF wins by count-out',
    'Bret Hart wins by disqualification',
    'FTR wins by putting opponent through a table',
    'Edge wins by pinfall',
]

for r in test_results:
    winner = extract_winner_from_result(r)
    print(f'  "{r}" -> "{winner}"')

# Now process actual matches
print()
print('2. PROCESSING MATCHES:')

fixed_count = 0
already_correct = 0
could_not_fix = 0
no_result = 0

# Process in batches
batch_size = 5000
total_matches = Match.objects.exclude(result__isnull=True).exclude(result='').count()
print(f'Total matches to process: {total_matches}')

processed = 0
for match in Match.objects.exclude(result__isnull=True).exclude(result='').select_related('winner').prefetch_related('wrestlers').iterator(chunk_size=batch_size):
    processed += 1
    if processed % 10000 == 0:
        print(f'  Processed {processed}/{total_matches}...')

    winner_name = extract_winner_from_result(match.result)
    if not winner_name:
        no_result += 1
        continue

    # Get wrestlers in the match
    match_wrestlers = list(match.wrestlers.all())

    # Check if current winner is correct
    if match.winner and match.winner.name.lower() == winner_name.lower():
        already_correct += 1
        continue

    # Find the correct winner among match wrestlers
    correct_winner = None

    # Try exact match first
    for w in match_wrestlers:
        if w.name.lower() == winner_name.lower():
            correct_winner = w
            break

    # Try partial match (winner name contains wrestler name or vice versa)
    if not correct_winner:
        for w in match_wrestlers:
            if w.name.lower() in winner_name.lower() or winner_name.lower() in w.name.lower():
                correct_winner = w
                break

    # Try matching first name or last name
    if not correct_winner and ' ' in winner_name:
        winner_parts = winner_name.lower().split()
        for w in match_wrestlers:
            wrestler_parts = w.name.lower().split()
            if any(wp in winner_parts for wp in wrestler_parts):
                correct_winner = w
                break

    if correct_winner:
        if match.winner != correct_winner:
            match.winner = correct_winner
            match.save(update_fields=['winner'])
            fixed_count += 1
        else:
            already_correct += 1
    else:
        could_not_fix += 1

print()
print('3. RESULTS:')
print(f'  Fixed: {fixed_count}')
print(f'  Already correct: {already_correct}')
print(f'  Could not determine winner: {could_not_fix}')
print(f'  No result field: {no_result}')

# 4. Verify the fix
print()
print('4. VERIFICATION - Checking women title matches:')
from owdb_django.owdbapp.models import Title

womens_titles = Title.objects.filter(name__icontains='women')
male_winners = ['MJF', 'Roman Reigns', 'Seth Rollins', 'Jon Moxley', 'Randy Savage', 'Batista']

bad_count = 0
for t in womens_titles[:5]:
    bad = Match.objects.filter(title=t, winner__name__in=male_winners).count()
    bad_count += bad
    if bad > 0:
        print(f'  {t.name}: {bad} male winners still present')

print(f'  Total gender mismatches in sample: {bad_count}')
