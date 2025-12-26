#!/usr/bin/env python
"""Comprehensive cleanup of match data issues."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title, Wrestler, Event
from django.db.models import Q

print('=== COMPREHENSIVE DATA CLEANUP ===')
print()

# 1. Clear women's titles from matches with all-male participants
print('1. CLEARING WOMEN TITLES FROM MALE-ONLY MATCHES:')

# Get all women's titles
womens_titles = Title.objects.filter(
    Q(name__icontains='women') | Q(name__icontains='knockouts') | Q(name__icontains='diva')
)

cleared_count = 0
for title in womens_titles:
    matches_with_title = Match.objects.filter(title=title).prefetch_related('wrestlers')

    for m in matches_with_title:
        wrestlers = list(m.wrestlers.all())
        wrestler_names = [w.name.lower() for w in wrestlers]

        # Known female name indicators
        female_indicators = ['charlotte', 'becky', 'sasha', 'bayley', 'asuka', 'alexa', 'rhea',
                             'bianca', 'trish', 'lita', 'chyna', 'mickie', 'melina', 'beth',
                             'natalya', 'paige', 'naomi', 'carmella', 'nikki', 'brie', 'ronda',
                             'shayna', 'jade', 'britt', 'thunder rosa', 'toni', 'hikaru', 'riho',
                             'nyla', 'kris', 'anna jay', 'ruby', 'jamie', 'willow', 'mercedes',
                             'iyo', 'dakota', 'kairi', 'liv', 'lacey', 'nia', 'tamina', 'sonya',
                             'mandy', 'zelina', 'gail', 'awesome kong', 'tara', 'brooke',
                             'penelope', 'tay', 'saraya']

        # Check if any wrestler has a female name
        has_female = False
        for name in wrestler_names:
            if any(ind in name for ind in female_indicators):
                has_female = True
                break

        if not has_female and wrestlers:
            m.title = None
            m.save(update_fields=['title'])
            cleared_count += 1

print(f'  Cleared {cleared_count} matches')

# 2. Check remaining title match integrity
print()
print('2. CHECKING REMAINING TITLE MATCH INTEGRITY:')
total_title = Match.objects.exclude(title__isnull=True).count()
print(f'  Total title matches: {total_title}')

# Sample some to verify quality
print()
print('3. SAMPLE VERIFICATION OF REMAINING TITLE MATCHES:')
for m in Match.objects.exclude(title__isnull=True).select_related('title', 'winner', 'event').order_by('?')[:10]:
    print(f'  {m.title.name}')
    print(f'    Event: {m.event.name if m.event else "None"}')
    print(f'    Match: {m.match_text[:50] if m.match_text else "None"}')
    print(f'    Winner: {m.winner.name if m.winner else "None"}')
    print()

# 4. Check for future events with matches (shouldn't exist)
print('4. CHECKING FOR FUTURE EVENT DATA:')
from datetime import date
future_events = Event.objects.filter(date__gt=date.today())
print(f'  Events with future dates: {future_events.count()}')

future_with_matches = 0
for e in future_events[:5]:
    match_count = Match.objects.filter(event=e).count()
    if match_count > 0:
        future_with_matches += 1
        print(f'    {e.name} ({e.date}): {match_count} matches')

# 5. Clear matches from future events (synthetic data)
print()
print('5. CLEARING MATCHES FROM FUTURE EVENTS:')
future_match_count = Match.objects.filter(event__date__gt=date.today()).count()
print(f'  Matches in future events: {future_match_count}')

if future_match_count > 0:
    Match.objects.filter(event__date__gt=date.today()).delete()
    print(f'  Deleted {future_match_count} future matches')

# 6. Final verification
print()
print('6. FINAL STATISTICS:')
print(f'  Total matches: {Match.objects.count()}')
print(f'  Total title matches: {Match.objects.exclude(title__isnull=True).count()}')
print(f'  Matches with winners: {Match.objects.exclude(winner__isnull=True).count()}')
print(f'  Total events: {Event.objects.count()}')
