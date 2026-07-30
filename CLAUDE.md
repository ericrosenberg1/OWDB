# OWDB — Claude Code Instructions

## Tech stack
- Django 5.2 (`requirements.txt` pins `>=5.2,<5.3`) with Celery for background tasks
- SQLite in production (`/app/data/db.sqlite3` on the NUC) and in dev; PostgreSQL only in CI
- Sentry error monitoring via sentry-sdk[django]

## Auto-fix guidelines
- **Test command:** `python manage.py test owdb_django.owdbapp.tests --verbosity=0`
  The app is installed as `owdb_django.owdbapp`, so a bare `owdbapp.tests` label
  fails with `ModuleNotFoundError: No module named 'owdbapp'` instead of running
  anything. CI (`.github/workflows/ci.yml`) runs the whole suite via
  `python manage.py test`.
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
- `owdb_django/wrestlebot/` — AI enrichment logic (a sibling app, NOT under `owdbapp/`;
  the legacy in-app `owdbapp.wrestlebot` module was removed)
- `owdb_django/settings.py` — Django settings (never hardcode secrets)
- `owdb_django/owdbapp/tests/` — test suite
