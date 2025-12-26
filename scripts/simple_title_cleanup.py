#!/usr/bin/env python
"""Simple cleanup - clear titles that don't match the match_text."""
import os
import sys
import django

sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')
django.setup()

from owdb_django.owdbapp.models import Match, Title
from django.db import connection

print('=== SIMPLE TITLE CLEANUP ===')
print()

# Get current stats
before_count = Match.objects.exclude(title__isnull=True).count()
print(f'Title matches before: {before_count}')

# Use raw SQL for speed - clear title where match_text doesn't start with title name
print()
print('Clearing titles where match_text doesnt match...')

# Get all titles
titles = Title.objects.all()
cleared_total = 0

for title in titles:
    # Find matches with this title where the title name is NOT in match_text
    title_prefix = title.name.split()[0].lower()  # First word of title

    # Clear titles from matches where text doesn't contain title name at start
    matches_to_clear = Match.objects.filter(title=title).exclude(
        match_text__icontains=title_prefix
    )
    count = matches_to_clear.count()
    if count > 0:
        matches_to_clear.update(title=None)
        cleared_total += count
        if count > 10:
            print(f'  {title.name}: cleared {count}')

print(f'Total cleared: {cleared_total}')

# Final count
after_count = Match.objects.exclude(title__isnull=True).count()
print(f'Title matches after: {after_count}')
print(f'Reduction: {before_count - after_count}')
