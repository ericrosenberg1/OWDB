# Sentry — OWDB (Open Wrestling Database)

Project: `rosenberg-digital/owdb` · platform `python-django`

Initialised at the end of `owdb_django/settings.py` so Django config is
loaded first. DSN is read from the `SENTRY_DSN` env var only, no hardcoded
fallback, so environments without it set (local dev, CI) run with Sentry
disabled instead of silently reporting into the production project. The
Django integration captures unhandled exceptions in views and celery task
failures (if `sentry-sdk[django]` exposes the Celery integration when
celery is also installed).

`pip install -r requirements.txt` pulls in `sentry-sdk[django]>=2.66.1`.

## What does not report

`manage.py shell`, `manage.py dbshell`, `manage.py test` and `python -c` do not
initialise Sentry — `settings.SENTRY_ENABLED` is `False` for them. An operator
mistyping an import at a REPL used to open a production issue; four of the six
"new issues" in the Jul 25–Aug 1 weekly digest were that, not real faults
(ROS-1409, ROS-1411).

The list in `settings.NON_REPORTING_COMMANDS` is a **denylist**. Adding to it
silences things, so add sparingly: gunicorn, celery and the boot-time `migrate`
/ `collectstatic` steps all report, and anything unrecognised reports by
default. Quietly losing a real production error is the worse failure.

## Why an envelope was lost

The SDK counts a failed send as a lost event (client-report reason `network_error`)
and only logs the cause with `debug=True`. OWDB lost 1,106 error envelopes in
September 2026 that way, each matching a lost transaction from the same hour, with
nothing in the container log. `owdb_django/sentry_transport.py` (`LoggedHttpTransport`,
passed as `transport=` to `sentry_sdk.init`) now logs a `Sentry send raised ...`,
`Sentry envelope lost after retry ...` or `Sentry rejected envelope: HTTP ...` warning
with the cause and item types, and retries a dropped connection once before counting
the envelope as lost. Its logger is excluded from Sentry so a failing Sentry can't
feed itself. Grep the web container log for `Sentry ` to see the causes.
