#!/usr/bin/env python
"""Deep investigation of data issues."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title

print('=== DEEP DATA INVESTIGATION ===')
print()

# Look at specific bad matches
print('1. EXAMINING SPECIFIC BAD WOMEN TITLE MATCHES:')
womens_titles = Title.objects.filter(name__icontains='women')

for t in womens_titles[:3]:
    print(f'\n{t.name}:')
    bad_matches = Match.objects.filter(
        title=t,
        winner__name__in=['MJF', 'Roman Reigns', 'Seth Rollins', 'Jon Moxley', 'Randy Savage']
    ).select_related('winner', 'event')[:5]

    for m in bad_matches:
        print(f'  Event: {m.event.name if m.event else "None"}')
        print(f'  Match Text: {m.match_text}')
        print(f'  Result: {m.result}')
        print(f'  Winner: {m.winner.name if m.winner else "None"}')
        print(f'  Wrestlers: {[w.name for w in m.wrestlers.all()]}')
        print()

# Check if the match_text itself mentions the title correctly
print()
print('2. CHECKING IF TITLE MATCHES ARE REAL:')
print()

# Check if match_text mentions "women" or similar for women's titles
womens_title_matches = Match.objects.filter(title__name__icontains='women')[:20]
for m in womens_title_matches:
    title_in_text = 'women' in m.match_text.lower() if m.match_text else False
    print(f'Title: {m.title.name}')
    print(f'Match Text: {m.match_text[:70] if m.match_text else "None"}')
    print(f'Title mentioned in text: {title_in_text}')
    print()

# The issue might be that titles are randomly assigned to matches
print()
print('3. CHECKING TITLE ASSIGNMENT PATTERN:')

# How many matches have a title that is NOT in the match_text?
correct_title_in_text = 0
wrong_title_in_text = 0

for m in Match.objects.exclude(title__isnull=True).exclude(match_text__isnull=True)[:1000]:
    title_name = m.title.name.lower()
    match_text = m.match_text.lower()

    # Check if the title (or key words from it) appear in match_text
    title_keywords = [w for w in title_name.split() if len(w) > 3 and w not in ['championship', 'world', 'the']]

    found = False
    for keyword in title_keywords:
        if keyword in match_text:
            found = True
            break

    if found:
        correct_title_in_text += 1
    else:
        wrong_title_in_text += 1
        if wrong_title_in_text <= 5:
            print(f'  Title NOT in match_text:')
            print(f'    Title: {m.title.name}')
            print(f'    Text: {m.match_text[:80]}')

print()
print(f'Title in match_text: {correct_title_in_text}')
print(f'Title NOT in match_text: {wrong_title_in_text}')

# 4. Conclusion about the data
print()
print('4. DATA QUALITY CONCLUSION:')
print()

# The real issue: is the entire dataset synthetic?
# Let's check a known real event
from owdb_django.owdbapp.models import Event

wm40 = Event.objects.filter(name__icontains='WrestleMania 40').first()
if wm40:
    print(f'WrestleMania 40 ({wm40.name}):')
    for m in Match.objects.filter(event=wm40).select_related('title', 'winner'):
        wrestlers = [w.name for w in m.wrestlers.all()]
        print(f'  {m.match_text[:60]}')
        print(f'    Wrestlers: {wrestlers}')
        print(f'    Winner: {m.winner.name if m.winner else None}')
        print(f'    Title: {m.title.name if m.title else None}')
        print()
