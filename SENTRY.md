# Sentry — OWDB (Open Wrestling Database)

Project: `rosenberg-digital/owdb` · platform `python-django`

Initialised at the end of `owdb_django/settings.py` so Django config is
loaded first. DSN is hardcoded but can be overridden by `SENTRY_DSN` env
var. The Django integration captures unhandled exceptions in views and
celery task failures (if `sentry-sdk[django]` exposes the Celery integration
when celery is also installed).

`pip install -r requirements.txt` will pull in `sentry-sdk[django]>=2.18`.
