#!/usr/bin/env python
"""Investigate match data issues."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler

print('=== INVESTIGATING MATCH DATA ISSUES ===')
print()

# Look at a specific problematic match
print('1. EXAMINING SPECIFIC BAD MATCHES:')
bad_match = Match.objects.filter(
    title__name__icontains='women',
    winner__name='MJF'
).select_related('title', 'winner', 'event').first()

if bad_match:
    print(f'Match ID: {bad_match.id}')
    print(f'Event: {bad_match.event.name if bad_match.event else None}')
    print(f'Title: {bad_match.title.name}')
    print(f'Winner: {bad_match.winner.name}')
    print(f'Match Text: {bad_match.match_text}')
    print(f'Result: {bad_match.result}')
    print(f'Wrestlers in match: {[w.name for w in bad_match.wrestlers.all()]}')

# Check match_text to see if there is useful info
print()
print('2. SAMPLE MATCH_TEXT VALUES FOR TITLE MATCHES:')
for m in Match.objects.exclude(title__isnull=True).order_by('?')[:10]:
    print(f'  Title: {m.title.name}')
    print(f'  Winner: {m.winner.name if m.winner else None}')
    print(f'  Match Text: {m.match_text[:100] if m.match_text else None}')
    print(f'  Wrestlers: {[w.name for w in m.wrestlers.all()]}')
    print()

# Check if there's a pattern - maybe winner is being randomly assigned
print('3. CHECKING WINNER ASSIGNMENT PATTERN:')
print('Looking at matches where winner is not in the wrestlers list...')
count = 0
for m in Match.objects.exclude(winner__isnull=True).prefetch_related('wrestlers')[:1000]:
    wrestler_ids = set(m.wrestlers.values_list('id', flat=True))
    if m.winner_id and m.winner_id not in wrestler_ids:
        count += 1
        if count <= 5:
            print(f'  Match {m.id}: Winner {m.winner.name} not in wrestlers {[w.name for w in m.wrestlers.all()]}')

print(f'Total mismatched winners in first 1000: {count}')

# Check if titles are being randomly assigned
print()
print('4. CHECKING TITLE ASSIGNMENT PATTERN:')
# Look at a regular TV show
tv_event = Event.objects.filter(name__icontains='AEW Dynamite #300').first()
if tv_event:
    print(f'Event: {tv_event.name}')
    for m in Match.objects.filter(event=tv_event):
        print(f'  Match: {m.match_text[:80] if m.match_text else None}')
        print(f'    Title: {m.title.name if m.title else None}')
        print(f'    Winner: {m.winner.name if m.winner else None}')
        print()
