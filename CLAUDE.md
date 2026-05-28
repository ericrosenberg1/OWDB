# OWDB — Claude Code Instructions

## Tech stack
- Django 4.x with Celery for background tasks
- PostgreSQL (production) / SQLite (dev)
- Sentry error monitoring via sentry-sdk[django]

## Auto-fix guidelines
- **Test command:** `python manage.py test owdbapp.tests --verbosity=0`
- Only modify files directly named in the stack trace
- Do not create or modify Django migrations — post a comment on the issue instead
- Do not modify `models.py` without a migration — post a comment
- Error handling: Django's `Http404`, `PermissionDenied`, or raise with context
- Follow isort import ordering already in each file

## File map
- `owdb_django/owdbapp/views.py` — HTTP request handlers
- `owdb_django/owdbapp/models.py` — ORM models (requires migration for schema changes)
- `owdb_django/owdbapp/scrapers/` — Cagematch, TMDB, Wikipedia, etc.
- `owdb_django/owdbapp/tasks.py` — Celery background tasks
- `owdb_django/owdbapp/wrestlebot/` — AI enrichment logic
- `owdb_django/settings.py` — Django settings (never hardcode secrets)
- `owdb_django/owdbapp/tests/` — test suite
