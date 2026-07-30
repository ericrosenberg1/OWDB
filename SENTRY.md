# Sentry — OWDB (Open Wrestling Database)

Project: `rosenberg-digital/owdb` · platform `python-django`

Initialised at the end of `owdb_django/settings.py` so Django config is
loaded first. The Django integration captures unhandled exceptions in views and
celery task failures (if `sentry-sdk[django]` exposes the Celery integration
when celery is also installed).

## Which environments report

`resolve_sentry_dsn()` in `owdb_django/settings.py` decides this:

| `APP_ENV`    | `SENTRY_DSN` env var | Reports?                      |
| ------------ | -------------------- | ----------------------------- |
| `production` | unset                | yes — built-in production DSN |
| anything     | set to a DSN         | yes — that DSN                |
| anything     | set but empty        | no (kill switch)              |
| not `production` | unset            | **no**                        |

The built-in DSN used to be the fallback for *every* environment, so any
checkout — a laptop, a bare `docker compose up`, a CI runner — reported into
the production project tagged `environment=development`. That produced three
digest alerts nobody could attribute to a host (ROS-1204, ROS-1206, ROS-1212).
Non-production runtimes now have to opt in explicitly.

If you *want* a dev box reporting, set `SENTRY_DSN` yourself — ideally to a
separate Sentry project, so dev noise never lands in the production alert feed.

Covered by `owdb_django/owdbapp/tests/test_sentry_dsn.py`.

`pip install -r requirements.txt` will pull in `sentry-sdk[django]>=2.18`.
