# Sentry — OWDB (Open Wrestling Database)

Project: `rosenberg-digital/owdb` · platform `python-django`

Initialised at the end of `owdb_django/settings.py` so Django config is
loaded first. DSN is hardcoded but can be overridden by `SENTRY_DSN` env
var. The Django integration captures unhandled exceptions in views and
celery task failures (if `sentry-sdk[django]` exposes the Celery integration
when celery is also installed).

`pip install -r requirements.txt` will pull in `sentry-sdk[django]>=2.18`.

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
