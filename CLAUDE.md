# OWDB — Claude Code Instructions

## Tech stack
- Django 6.0 on Python 3.14 (`requirements.txt` pins `>=6.0.7,<6.1`, capped by
  django-celery-beat 2.9.0) with Celery for background tasks. 6.0 is not an LTS, the next
  LTS is 6.2.
- SQLite in production and in dev, PostgreSQL only in CI
- Deploy and host details live in private ops docs. If a `CLAUDE.local.md`
  exists next to this file, read it for machine-specific notes.
- Sentry error monitoring via sentry-sdk[django]. Since 2026-10-08 `sentry_sdk.init` uses
  `LoggedHttpTransport` (`owdb_django/sentry_transport.py`, ported from FreelancerDashboard).
  It logs the exception or HTTP status behind every lost envelope to the console as a
  `Sentry ...` warning and retries a dropped connection once. The SDK files every loss as
  `network_error` with no cause otherwise. It overrides private SDK methods, so
  `test_sentry_transport.py` fails if an SDK upgrade renames them.

## Auto-fix guidelines
- **Test command:** `python manage.py test owdb_django.owdbapp.tests --verbosity=0`
  The app is installed as `owdb_django.owdbapp`, so a bare `owdbapp.tests` label
  fails with `ModuleNotFoundError: No module named 'owdbapp'` instead of running
  anything.
- **Gates run locally, not in GitHub Actions** (retired 2026-09-03). `.githooks/pre-push`
  runs `scripts/ci-gates.sh`: `ruff check`, `ruff format --check`, then the full suite.
  Run `ruff format .` before pushing. `.githooks/pre-commit` runs infra-leak-guard,
  which blocks host names, paths and other private infra details from this public repo.
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

## Conventions and known behavior
- **Review gate.** Public pages read through `.public()`, which hides only `rejected`
  rows (`candidate` stays visible). `MatchQuerySet.public()` also drops matches whose
  event is rejected. When a filter joins through events or matches, use
  `__in=<public subquery>`, not a negated multi-valued `Q`, which Django turns into
  "has no rejected row anywhere". Left unfiltered on purpose: `wrestlebot_health`
  lifetime totals, `tasks.py` counts, admin's `TVShow.episode_count`, all wrestlebot code.
- `accuracy_contract.enforce()` keeps a `rejected` status unchanged, so a re-extraction
  never lifts a human or Earl rejection.
- Rating and detail-URL maps (`UserRating.ENTITY_TYPE_CHOICES` and both view maps) must
  list the same entity types. A test pins them together. The wrestlebot writes
  `"tv_show"`, not `"tvshow"`.
- **TV episodes.** `ingest_episode_list()` tries Wikipedia's numbered episode list, then
  falls back to the specials list (WWE Raw and SmackDown have no numbered list). The
  ingester upserts on `(promotion, name, date)`, so any change to generated episode names
  needs a data migration in the same release or every episode duplicates.
- Leave these alone: the third SmackDown table shape (a colspan Taping and Airing pair
  with identical headers, so nothing says which date aired), and the TMDB route, which
  stays dormant until a `TMDB_API_KEY` and `TVShow.tmdb_id` exist.
- No sitemap exists in this project.
- The legacy `owdbapp` scrapers and Commons image fetch are off the beat schedule
  (decided 2026-09-10, `docs/autonomy-schedule-consolidation.md`). The task functions
  remain. WrestleBot is the one ingestion path.
