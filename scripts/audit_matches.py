#!/usr/bin/env python
"""Audit match data for accuracy issues."""
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Event, Title, Wrestler
from django.db.models import Count

print('=== MATCH DATA AUDIT ===')
print()

# 1. Check for gender mismatches in women's title wins
print('1. MEN WINNING WOMENS TITLES (CLEAR ERRORS):')
womens_titles = Title.objects.filter(name__icontains='women')
male_wrestlers = ['MJF', 'Jon Moxley', 'Roman Reigns', 'Seth Rollins', 'Batista',
                  'Mark Henry', 'Matt Hardy', 'Andrade', 'Triple H', 'Randy Savage',
                  'Bret Hart', 'Cesaro', 'Keith Lee', 'Jungle Boy', 'AJ Styles',
                  'Sheamus', 'Brock Lesnar', 'Jeff Hardy', 'CM Punk', 'Bryan Danielson',
                  'Samoa Joe', 'Dean Ambrose', 'Daniel Bryan', 'John Cena', 'Drew McIntyre',
                  'Bobby Lashley', 'The Undertaker', 'Rey Mysterio', 'Dustin Rhodes',
                  'Austin Aries', 'Mr. Anderson', 'Wardlow', 'Matt Morgan', 'Alex Shelley']

errors = []
for t in womens_titles:
    bad_wins = Match.objects.filter(title=t).exclude(winner__isnull=True).filter(winner__name__in=male_wrestlers)
    for m in bad_wins:
        errors.append((t.name, m.winner.name, m.event.name if m.event else 'Unknown'))

print(f'Found {len(errors)} gender mismatch errors')
for err in errors[:20]:
    print(f'  {err[0]}: {err[1]} at {err[2]}')

# 2. Check for women winning men's titles
print()
print('2. WOMEN WINNING MENS-ONLY TITLES (POTENTIAL ERRORS):')
female_wrestlers = ['Charlotte Flair', 'Becky Lynch', 'Sasha Banks', 'Bayley',
                    'Asuka', 'Alexa Bliss', 'Rhea Ripley', 'Bianca Belair',
                    'Trish Stratus', 'Lita', 'Chyna', 'Beth Phoenix', 'Natalya',
                    'Naomi', 'Carmella', 'Nikki Bella', 'Brie Bella', 'Paige',
                    'Ronda Rousey', 'Shayna Baszler', 'Britt Baker', 'Thunder Rosa',
                    'Jade Cargill', 'Toni Storm', 'Saraya', 'Hikaru Shida']

mens_titles = Title.objects.filter(
    name__icontains='championship'
).exclude(
    name__icontains='women'
).exclude(
    name__icontains='knockouts'
).exclude(
    name__icontains='diva'
)

errors2 = []
for t in mens_titles:
    bad_wins = Match.objects.filter(title=t).exclude(winner__isnull=True).filter(winner__name__in=female_wrestlers)
    for m in bad_wins:
        # Skip intergender titles
        if 'mixed' in t.name.lower() or 'intergender' in t.name.lower():
            continue
        errors2.append((t.name, m.winner.name, m.event.name if m.event else 'Unknown'))

print(f'Found {len(errors2)} potential errors')
for err in errors2[:20]:
    print(f'  {err[0]}: {err[1]} at {err[2]}')

# 3. Check total match data
print()
print('3. MATCH DATA SUMMARY:')
total_matches = Match.objects.count()
matches_with_title = Match.objects.exclude(title__isnull=True).count()
matches_with_winner = Match.objects.exclude(winner__isnull=True).count()
matches_with_event = Match.objects.exclude(event__isnull=True).count()

print(f'  Total matches: {total_matches}')
print(f'  Matches with title: {matches_with_title}')
print(f'  Matches with winner: {matches_with_winner}')
print(f'  Matches with event: {matches_with_event}')

# 4. Check for duplicate/malformed entries
print()
print('4. EVENTS WITH SUSPICIOUS TITLE MATCH COUNTS:')
from django.db.models import Count
event_title_counts = Event.objects.annotate(
    title_match_count=Count('match', filter=Match.objects.filter(title__isnull=False).query.where)
).order_by('-title_match_count')[:10]

# Alternative approach
print('Events with most matches:')
for e in Event.objects.annotate(match_count=Count('match')).order_by('-match_count')[:10]:
    print(f'  {e.name}: {e.match_count} matches')

print()
print('=== AUDIT COMPLETE ===')
