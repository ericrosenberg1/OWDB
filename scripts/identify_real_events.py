#!/usr/bin/env python
"""
Identify which events have real vs synthetic match data.
Real events typically have:
- Matches that make chronological sense (wrestlers active at that time)
- Title matches with appropriate title holders
- Proper match results
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler
from django.db.models import Count
import re

print('=== IDENTIFYING REAL VS SYNTHETIC DATA ===')
print()

# Known real major WWE PPVs with verifiable data
KNOWN_REAL_EVENTS = [
    'WrestleMania 40', 'WrestleMania 39', 'WrestleMania 38', 'WrestleMania 37',
    'WrestleMania 36', 'WrestleMania 35', 'WrestleMania 34', 'WrestleMania 33',
    'WrestleMania 32', 'WrestleMania 31', 'WrestleMania 30', 'WrestleMania 29',
    'Royal Rumble 2024', 'Royal Rumble 2023', 'Royal Rumble 2022',
    'SummerSlam 2024', 'SummerSlam 2023', 'SummerSlam 2022',
    'Survivor Series 2023', 'Survivor Series 2022',
    'AEW All Out 2024', 'AEW All Out 2023', 'AEW All In 2023',
    'AEW Revolution 2024', 'AEW Revolution 2023',
    'AEW Double or Nothing 2024', 'AEW Double or Nothing 2023',
]

# Check which events look synthetic
# Synthetic patterns:
# 1. TV shows with title matches every episode
# 2. Wrestlers from different eras in same match
# 3. Gender mismatches in title matches

print('1. ANALYZING EVENT PATTERNS:')

# Check TV shows - they shouldn't have many title matches
tv_patterns = ['Raw #', 'SmackDown #', 'Dynamite #', 'NXT #', 'Thunder #', 'Nitro #',
               'Saturday Night #', 'Superstars #', 'Rampage #', 'Collision #']

print('   TV shows with excessive title matches:')
for pattern in tv_patterns:
    events = Event.objects.filter(name__icontains=pattern)
    for e in events[:100]:  # Check first 100 of each
        title_matches = Match.objects.filter(event=e, title__isnull=False).count()
        total_matches = Match.objects.filter(event=e).count()
        if total_matches > 0 and title_matches / total_matches > 0.5:
            # More than 50% title matches is suspicious for TV
            print(f'      {e.name}: {title_matches}/{total_matches} title matches')

# 2. Check for anachronistic matches (wrestlers from different eras)
print()
print('2. CHECKING FOR ANACHRONISTIC MATCHES:')

# Wrestlers with known active periods
era_checks = [
    # (Wrestler who retired before X, Wrestler who debuted after X)
    ('Hulk Hogan', 'MJF'),  # Hogan retired ~2012, MJF debuted 2015+
    ('Randy Savage', 'Roman Reigns'),  # Savage died 2011, Roman debuted 2012
    ('Ultimate Warrior', 'Seth Rollins'),  # Warrior died 2014, minimal overlap
]

anachronistic = 0
for old_name, new_name in era_checks:
    old = Wrestler.objects.filter(name__icontains=old_name).first()
    new = Wrestler.objects.filter(name__icontains=new_name).first()
    if old and new:
        # Find matches with both
        matches = Match.objects.filter(wrestlers=old).filter(wrestlers=new)
        count = matches.count()
        if count > 0:
            anachronistic += count
            print(f'   {old.name} vs {new.name}: {count} matches (impossible)')
            for m in matches[:3]:
                print(f'      Event: {m.event.name if m.event else None}')

print(f'   Total anachronistic matches found: {anachronistic}')

# 3. Mark synthetic title matches for removal
print()
print('3. IDENTIFYING SYNTHETIC TITLE MATCHES:')

# A title match is likely synthetic if:
# - The match_text has a title prefix but participants don't match the era
# - The winner makes no sense (gender mismatch, era mismatch)

synthetic_count = 0
sample_synthetic = []

for m in Match.objects.exclude(title__isnull=True).select_related('title', 'winner', 'event').prefetch_related('wrestlers')[:5000]:
    is_synthetic = False

    # Check era mismatches
    wrestlers = list(m.wrestlers.all())
    wrestler_names = [w.name for w in wrestlers]

    # Check for impossible combinations
    has_old_era = any(n in str(wrestler_names) for n in ['Hulk Hogan', 'Randy Savage', 'Ultimate Warrior', 'Andre the Giant'])
    has_new_era = any(n in str(wrestler_names) for n in ['Roman Reigns', 'Seth Rollins', 'MJF', 'Kenny Omega', 'Jon Moxley'])

    if has_old_era and has_new_era:
        is_synthetic = True

    # Check if title matches the event era
    if m.event and m.title:
        event_name = m.event.name.lower()
        title_name = m.title.name.lower()

        # AEW titles shouldn't appear in WWE/WCW events
        if 'aew' in title_name and ('wwe' in event_name or 'wcw' in event_name or 'wwf' in event_name):
            is_synthetic = True

        # WWE titles shouldn't appear in AEW events
        if 'wwe' in title_name and 'aew' in event_name:
            is_synthetic = True

    if is_synthetic:
        synthetic_count += 1
        if len(sample_synthetic) < 10:
            sample_synthetic.append({
                'event': m.event.name if m.event else None,
                'title': m.title.name,
                'wrestlers': wrestler_names
            })

print(f'   Synthetic title matches found: {synthetic_count}')
print('   Samples:')
for s in sample_synthetic:
    print(f'      {s["event"]}: {s["title"]} - {s["wrestlers"]}')

# 4. Stats on remaining data
print()
print('=== CURRENT DATA STATUS ===')
print(f'   Total events: {Event.objects.count()}')
print(f'   Total matches: {Match.objects.count()}')
print(f'   Title matches: {Match.objects.exclude(title__isnull=True).count()}')
