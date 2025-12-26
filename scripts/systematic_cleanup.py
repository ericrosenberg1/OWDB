#!/usr/bin/env python
"""
Systematic cleanup of the wrestling database.
Removes synthetic data and fixes accuracy issues.
"""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler, Venue
from django.db.models import Q, Count
from datetime import date

print('=== SYSTEMATIC DATABASE CLEANUP ===')
print()

# 1. Remove future dated events and their matches
print('1. REMOVING FUTURE EVENTS AND MATCHES:')
today = date.today()
future_events = Event.objects.filter(date__gt=today)
future_count = future_events.count()
future_matches = Match.objects.filter(event__date__gt=today).count()
Match.objects.filter(event__date__gt=today).delete()
future_events.delete()
print(f'   Deleted {future_count} future events and {future_matches} matches')

# 2. Clean up duplicate titles
print()
print('2. CLEANING DUPLICATE TITLES:')
# Find titles with same or similar names
title_names = {}
for t in Title.objects.all():
    base_name = t.name.lower().strip()
    if base_name not in title_names:
        title_names[base_name] = []
    title_names[base_name].append(t)

duplicates_removed = 0
for name, titles in title_names.items():
    if len(titles) > 1:
        # Keep the one with the most matches
        primary = max(titles, key=lambda t: Match.objects.filter(title=t).count())
        for t in titles:
            if t != primary:
                # Move matches to primary title
                Match.objects.filter(title=t).update(title=primary)
                t.delete()
                duplicates_removed += 1
                print(f'   Merged duplicate: {t.name}')

print(f'   Removed {duplicates_removed} duplicate titles')

# 3. Clear titles from matches that don't make sense
print()
print('3. CLEARING INVALID TITLE ASSIGNMENTS:')

# Define gender categories for wrestlers
male_names_pattern = ['MJF', 'Roman Reigns', 'Seth Rollins', 'Jon Moxley', 'Randy Savage',
    'The Rock', 'Triple H', 'John Cena', 'Brock Lesnar', 'The Undertaker',
    'Kenny Omega', 'CM Punk', 'AJ Styles', 'Edge', 'Randy Orton', 'Batista',
    'Kurt Angle', 'Shawn Michaels', 'Stone Cold', 'Sting', 'Goldberg',
    'Kane', 'Big Show', 'Mark Henry', 'Chris Jericho', 'Mick Foley']

female_names_pattern = ['Charlotte', 'Becky', 'Sasha', 'Bayley', 'Asuka', 'Rhea',
    'Bianca', 'Alexa', 'Liv', 'Trish', 'Lita', 'Britt', 'Jade', 'Thunder Rosa',
    'Toni Storm', 'Mandy', 'Sonya', 'Mickie', 'Gail Kim']

# Clear women's titles from matches with only male participants
womens_titles = Title.objects.filter(
    Q(name__icontains='women') | Q(name__icontains='knockouts') | Q(name__icontains='diva')
)

cleared = 0
for title in womens_titles:
    matches = Match.objects.filter(title=title).prefetch_related('wrestlers')
    for m in matches:
        wrestlers = [w.name for w in m.wrestlers.all()]
        has_female = any(any(f in w for f in female_names_pattern) for w in wrestlers)
        if not has_female and wrestlers:
            m.title = None
            m.save(update_fields=['title'])
            cleared += 1

print(f'   Cleared {cleared} invalid women title assignments')

# 4. Remove matches with no wrestlers
print()
print('4. REMOVING EMPTY MATCHES:')
empty_matches = Match.objects.annotate(wrestler_count=Count('wrestlers')).filter(wrestler_count=0)
empty_count = empty_matches.count()
empty_matches.delete()
print(f'   Deleted {empty_count} matches with no wrestlers')

# 5. Remove matches with no event
print()
print('5. REMOVING ORPHAN MATCHES:')
orphan_matches = Match.objects.filter(event__isnull=True)
orphan_count = orphan_matches.count()
orphan_matches.delete()
print(f'   Deleted {orphan_count} matches with no event')

# 6. Clean up malformed event names
print()
print('6. CLEANING MALFORMED EVENT NAMES:')
# Remove events with concatenated names
malformed = Event.objects.filter(
    Q(name__contains=')(') |
    Q(name__regex=r'[a-z][A-Z]') |  # camelCase indicates concatenation
    Q(name__contains='WWEIndependent')
)
malformed_count = malformed.count()
for e in malformed:
    Match.objects.filter(event=e).delete()
malformed.delete()
print(f'   Deleted {malformed_count} malformed events')

# 7. Verify event-venue connections
print()
print('7. VERIFYING EVENT-VENUE CONNECTIONS:')
events_without_venue = Event.objects.filter(venue__isnull=True).count()
events_with_venue = Event.objects.exclude(venue__isnull=True).count()
print(f'   Events with venue: {events_with_venue}')
print(f'   Events without venue: {events_without_venue}')

# 8. Final statistics
print()
print('=== FINAL STATISTICS ===')
print(f'   Total events: {Event.objects.count()}')
print(f'   Total matches: {Match.objects.count()}')
print(f'   Total title matches: {Match.objects.exclude(title__isnull=True).count()}')
print(f'   Total wrestlers: {Wrestler.objects.count()}')
print(f'   Total titles: {Title.objects.count()}')
print(f'   Total venues: {Venue.objects.count()}')

# 9. Sample verification
print()
print('=== SAMPLE VERIFICATION ===')
print('Random title matches:')
for m in Match.objects.exclude(title__isnull=True).order_by('?')[:5]:
    print(f'   {m.title.name}')
    print(f'      Event: {m.event.name if m.event else "None"}')
    print(f'      Winner: {m.winner.name if m.winner else "None"}')
    print(f'      Wrestlers: {[w.name for w in m.wrestlers.all()]}')
    print()
