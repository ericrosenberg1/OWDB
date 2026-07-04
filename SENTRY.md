# Sentry — OWDB (Open Wrestling Database)

Project: `rosenberg-digital/owdb` · platform `python-django`

Initialised at the end of `owdb_django/settings.py` so Django config is
loaded first. DSN is read from the `SENTRY_DSN` env var only, no hardcoded
fallback, so environments without it set (local dev, CI) run with Sentry
disabled instead of silently reporting into the production project. The
Django integration captures unhandled exceptions in views and celery task
failures (if `sentry-sdk[django]` exposes the Celery integration when
celery is also installed).

`pip install -r requirements.txt` will pull in `sentry-sdk[django]>=2.18`.
