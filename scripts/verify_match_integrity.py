#!/usr/bin/env python
"""Verify and fix match integrity - winner should be a participant."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title, Wrestler
from django.db.models import Q
import re

print('=== MATCH INTEGRITY VERIFICATION ===')
print()

# 1. Check if winner is in the participants
print('1. CHECKING IF WINNER IS IN MATCH PARTICIPANTS:')

mismatches = 0
fixed = 0
sample_issues = []

for m in Match.objects.exclude(winner__isnull=True).prefetch_related('wrestlers').select_related('winner')[:50000]:
    participant_ids = set(m.wrestlers.values_list('id', flat=True))
    if m.winner_id not in participant_ids:
        mismatches += 1
        if len(sample_issues) < 5:
            sample_issues.append({
                'match_text': m.match_text[:60] if m.match_text else 'None',
                'winner': m.winner.name,
                'participants': [w.name for w in m.wrestlers.all()]
            })

print(f'  Matches where winner not in participants: {mismatches} (of 50000 sampled)')

for issue in sample_issues:
    print(f'    Match: {issue["match_text"]}')
    print(f'    Winner: {issue["winner"]}')
    print(f'    Participants: {issue["participants"]}')
    print()

# 2. Try to fix by parsing result field
print()
print('2. FIXING WINNERS BASED ON RESULT FIELD:')

def extract_winner_name(result):
    if not result:
        return None
    match = re.match(r'^(.+?)\s+wins?\s+by\s+', result, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

fixed_count = 0
for m in Match.objects.exclude(winner__isnull=True).exclude(result__isnull=True).prefetch_related('wrestlers').select_related('winner')[:50000]:
    participant_ids = set(m.wrestlers.values_list('id', flat=True))
    if m.winner_id not in participant_ids:
        # Winner is wrong - try to find correct one from result
        winner_name = extract_winner_name(m.result)
        if winner_name:
            # Find matching wrestler in participants
            for w in m.wrestlers.all():
                if w.name.lower() == winner_name.lower() or winner_name.lower() in w.name.lower():
                    m.winner = w
                    m.save(update_fields=['winner'])
                    fixed_count += 1
                    break

print(f'  Fixed {fixed_count} matches')

# 3. Check title match text consistency
print()
print('3. CHECKING TITLE MATCH TEXT CONSISTENCY:')

title_mismatch = 0
for m in Match.objects.exclude(title__isnull=True).select_related('title')[:10000]:
    if m.match_text and m.title:
        # Check if title appears in match text (at beginning)
        if m.title.name.lower() not in m.match_text.lower():
            title_mismatch += 1

print(f'  Matches where title not in match_text: {title_mismatch} (of 10000 sampled)')

# 4. Clear titles from matches where title doesn't appear in match_text
print()
print('4. CLEARING MISMATCHED TITLES:')

# This is a strong indicator of synthetic data
cleared = 0
for m in Match.objects.exclude(title__isnull=True).select_related('title'):
    if m.match_text and m.title:
        title_lower = m.title.name.lower()
        text_lower = m.match_text.lower()

        # The title should appear at the beginning of match_text for legitimate title matches
        # e.g., "WWE Championship: Wrestler A vs. Wrestler B"
        if not text_lower.startswith(title_lower.split()[0]):
            # Title doesn't match - likely synthetic
            m.title = None
            m.save(update_fields=['title'])
            cleared += 1

print(f'  Cleared {cleared} mismatched title assignments')

# 5. Final stats
print()
print('5. FINAL STATISTICS:')
print(f'  Total matches: {Match.objects.count()}')
print(f'  Title matches: {Match.objects.exclude(title__isnull=True).count()}')
print(f'  Matches with winners: {Match.objects.exclude(winner__isnull=True).count()}')
