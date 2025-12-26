#!/usr/bin/env python
"""Analyze cleanup options for match data."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler

print('=== ANALYZING CLEANUP OPTIONS ===')
print()

# 1. Count how much data we have
print('1. DATA COUNTS:')
total_matches = Match.objects.count()
matches_with_title = Match.objects.exclude(title__isnull=True).count()
matches_with_winner = Match.objects.exclude(winner__isnull=True).count()
total_events = Event.objects.count()
total_titles = Title.objects.count()
total_wrestlers = Wrestler.objects.count()

print(f'Total matches: {total_matches:,}')
print(f'  - with title: {matches_with_title:,}')
print(f'  - with winner: {matches_with_winner:,}')
print(f'Total events: {total_events:,}')
print(f'Total titles: {total_titles}')
print(f'Total wrestlers: {total_wrestlers:,}')

# 2. Check if match_text contains real match info
print()
print('2. MATCH_TEXT QUALITY CHECK:')
matches_with_text = Match.objects.exclude(match_text__isnull=True).exclude(match_text='').count()
print(f'Matches with match_text: {matches_with_text:,}')

# Sample match_text to see if they look real
print()
print('Sample match_text values:')
for m in Match.objects.exclude(match_text__isnull=True).order_by('?')[:10]:
    print(f'  - {m.match_text[:80]}')

# 3. Check if result field has useful data
print()
print('3. RESULT FIELD QUALITY:')
matches_with_result = Match.objects.exclude(result__isnull=True).exclude(result='').count()
print(f'Matches with result: {matches_with_result:,}')

print()
print('Sample result values:')
for m in Match.objects.exclude(result__isnull=True).exclude(result='').order_by('?')[:10]:
    print(f'  - {m.result[:80] if m.result else "None"}')

# 4. Identify which data is trustworthy
print()
print('4. TRUSTWORTHY DATA ANALYSIS:')

# Check if WM40 type events have correct data
major_events = Event.objects.filter(name__icontains='WrestleMania').exclude(name__icontains='Dynamite')[:5]
correct_count = 0
total_checked = 0
for event in major_events:
    matches = Match.objects.filter(event=event).exclude(title__isnull=True).select_related('title', 'winner')
    for m in matches:
        total_checked += 1
        if m.winner and m.match_text:
            # Check if winner name appears in match_text
            if m.winner.name.lower() in m.match_text.lower():
                correct_count += 1

print(f'Major PPV title matches where winner is in match_text: {correct_count}/{total_checked}')

# 5. Estimate cleanup effort
print()
print('5. CLEANUP OPTIONS:')
print()
print('Option A: Clear ALL winner fields and re-derive from match_text')
print(f'  - Would affect {matches_with_winner:,} matches')
print()
print('Option B: Clear ALL title assignments and re-derive from match_text')
print(f'  - Would affect {matches_with_title:,} matches')
print()
print('Option C: Clear both winner and title, keep only match_text and result')
print(f'  - Would keep match_text as the source of truth')
print()
print('Option D: Clear only obviously wrong data (gender mismatches, etc)')
print(f'  - Would require complex logic to identify wrong data')

# 6. Check if we can parse match_text to extract winner
print()
print('6. PARSING MATCH_TEXT FOR WINNERS:')
print()

# Check if match_text contains "vs" pattern
for m in Match.objects.exclude(match_text__isnull=True).order_by('?')[:20]:
    text = m.match_text
    result = m.result if m.result else ''

    # Try to extract participants from text like "Title: Wrestler1 vs. Wrestler2"
    if ' vs. ' in text or ' vs ' in text:
        parts = text.replace(' vs. ', ' vs ').split(' vs ')
        # First part might have title info
        participants = []
        for i, p in enumerate(parts):
            if i == 0 and ':' in p:
                # Remove title prefix
                p = p.split(':')[-1].strip()
            participants.append(p.strip())

        # Try to find winner in result
        winner_from_result = None
        if result:
            for p in participants:
                if p.lower() in result.lower():
                    winner_from_result = p
                    break

        print(f'Text: {text[:60]}')
        print(f'Participants: {participants}')
        print(f'Result: {result[:50] if result else "None"}')
        print(f'Winner from result: {winner_from_result}')
        print()
