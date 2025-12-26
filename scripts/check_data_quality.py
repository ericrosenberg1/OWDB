#!/usr/bin/env python
"""Check the overall data quality and identify patterns."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler

print('=== DATA QUALITY ANALYSIS ===')
print()

# 1. Check if ANY matches look real
print('1. LOOKING FOR LEGITIMATE MATCHES:')
print()

# Check WrestleMania 40 matches
wm40 = Event.objects.filter(name__icontains='WrestleMania 40').first()
if wm40:
    print(f'Event: {wm40.name}')
    print(f'Date: {wm40.date}')
    for m in Match.objects.filter(event=wm40)[:10]:
        print(f'  - {m.match_text[:80] if m.match_text else "No text"}')
        print(f'    Winner: {m.winner.name if m.winner else None}')
        print(f'    Title: {m.title.name if m.title else None}')
else:
    print('WrestleMania 40 not found')

# Check a specific real match we know happened
print()
print('2. SEARCHING FOR KNOWN REAL MATCHES:')

# Cody Rhodes winning at WM40
cody = Wrestler.objects.filter(name='Cody Rhodes').first()
if cody:
    cody_wwe_title_wins = Match.objects.filter(
        winner=cody,
        title__name__icontains='WWE Championship'
    ).select_related('event', 'title')
    print(f'Cody Rhodes WWE Championship wins: {cody_wwe_title_wins.count()}')
    for m in cody_wwe_title_wins[:5]:
        print(f'  - {m.event.name if m.event else "No event"}: {m.title.name}')

# Roman Reigns title defenses
print()
roman = Wrestler.objects.filter(name='Roman Reigns').first()
if roman:
    roman_title_matches = Match.objects.filter(
        winner=roman,
        title__isnull=False
    ).select_related('event', 'title')
    print(f'Roman Reigns title wins: {roman_title_matches.count()}')
    for m in roman_title_matches[:5]:
        print(f'  - {m.event.name if m.event else "No event"}: {m.title.name}')

# 3. Check event date ranges
print()
print('3. EVENT DATE RANGES:')
from django.db.models import Min, Max
date_range = Event.objects.aggregate(min_date=Min('date'), max_date=Max('date'))
print(f'Earliest event: {date_range["min_date"]}')
print(f'Latest event: {date_range["max_date"]}')

# Count events by year
from django.db.models.functions import ExtractYear
from django.db.models import Count
events_by_year = Event.objects.filter(date__isnull=False).annotate(
    year=ExtractYear('date')
).values('year').annotate(count=Count('id')).order_by('year')
print('Events by year:')
for e in events_by_year:
    print(f'  {e["year"]}: {e["count"]}')

# 4. Check for patterns in bad data
print()
print('4. ANALYZING BAD DATA PATTERNS:')

# Check if the title-winner mismatches follow a pattern
mismatches = 0
correct = 0
sample_bad = []

for m in Match.objects.exclude(title__isnull=True).exclude(winner__isnull=True).select_related('title', 'winner')[:5000]:
    title_name = m.title.name.lower()
    winner_name = m.winner.name.lower()

    # Check gender mismatch
    is_womens_title = 'women' in title_name or 'knockouts' in title_name or 'diva' in title_name
    is_female_winner = any(name in winner_name for name in ['charlotte', 'becky', 'sasha', 'bayley', 'asuka', 'alexa', 'rhea', 'bianca', 'trish', 'lita', 'mickie', 'melina', 'beth', 'natalya', 'paige', 'naomi', 'carmella', 'nikki', 'brie', 'ronda', 'shayna', 'jade', 'britt', 'thunder rosa', 'toni storm', 'hikaru', 'riho', 'nyla'])

    is_male_winner = any(name in winner_name for name in ['roman', 'seth', 'dean', 'john cena', 'brock', 'undertaker', 'triple h', 'randy', 'batista', 'edge', 'cm punk', 'daniel bryan', 'aj styles', 'mox', 'jericho', 'mjf', 'kenny', 'hangman', 'samoa joe', 'keith lee'])

    if is_womens_title and is_male_winner:
        mismatches += 1
        if len(sample_bad) < 5:
            sample_bad.append((m.title.name, m.winner.name, m.match_text[:50] if m.match_text else ''))
    elif is_womens_title and is_female_winner:
        correct += 1

print(f'In sample of 5000 title matches:')
print(f'  Gender mismatches: {mismatches}')
print(f'  Correct matches: {correct}')
print(f'  Ratio: {mismatches / max(1, mismatches + correct) * 100:.1f}% mismatched')

print()
print('Sample bad matches:')
for t, w, mt in sample_bad:
    print(f'  {t}: {w} - "{mt}"')

# 5. Check if match_text matches the title
print()
print('5. CHECKING IF MATCH_TEXT MENTIONS THE TITLE:')
matches_correct = 0
title_text_mismatch = 0
for m in Match.objects.exclude(title__isnull=True)[:1000]:
    if m.match_text and m.title:
        # Check if the title name appears in match_text
        title_words = m.title.name.lower().replace('championship', '').strip().split()
        match_text_lower = m.match_text.lower()
        if any(word in match_text_lower for word in title_words if len(word) > 3):
            matches_correct += 1
        else:
            title_text_mismatch += 1
            if title_text_mismatch <= 3:
                print(f'  Mismatch: Title={m.title.name}, Text={m.match_text[:60]}')

print(f'Title in match_text: {matches_correct}')
print(f'Title NOT in match_text: {title_text_mismatch}')
