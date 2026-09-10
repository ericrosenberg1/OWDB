"""
Rename generated TV episode events from an em-dash separator to a hyphen.

The bulk episode ingester names numbered episodes after the show and the
air date. It used an em-dash to join them, which put an em-dash on every
episode row on the public site, against the house style for this site's
copy.

The rename has to happen in the same release as the code change. The
ingester upserts on `(promotion, name, date)`, so a code-only change would
have matched nothing on the next run and created a second copy of all 358
episodes instead of updating them.

Only the exact generated shape is touched: an em-dash surrounded by single
spaces, on a `tv_episode` row whose trailing segment is an ISO date. An
event that legitimately carries an em-dash in its own title is left alone.
Slugs are untouched, `slugify` drops the separator either way.
"""

from __future__ import annotations

import re

from django.db import migrations

_GENERATED_NAME = re.compile(r"^(?P<show>.+?) (?P<sep>[—-]) (?P<date>\d{4}-\d{2}-\d{2})$")


def _reseparate(apps, schema_editor, *, old: str, new: str) -> None:
    Event = apps.get_model("owdbapp", "Event")
    updates = []
    for event in Event.objects.filter(event_type="tv_episode", name__contains=f" {old} "):
        match = _GENERATED_NAME.match(event.name)
        if not match or match.group("sep") != old:
            continue
        event.name = f"{match.group('show')} {new} {match.group('date')}"
        updates.append(event)
    if updates:
        Event.objects.bulk_update(updates, ["name"], batch_size=500)


def forwards(apps, schema_editor):
    _reseparate(apps, schema_editor, old="—", new="-")


def backwards(apps, schema_editor):
    _reseparate(apps, schema_editor, old="-", new="—")


class Migration(migrations.Migration):
    dependencies = [
        ("owdbapp", "0031_userrating_venue_choice"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
