"""What leaves this app in an admin error email.

`LoggedAdminEmailHandler` is on `django.request` at ERROR, so every 500 mails
`ADMIN_EMAILS` a full settings dump. Django cleanses that dump with
`SafeExceptionReporterFilter`, which redacts by setting *name*
(`API|AUTH|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE`). A password embedded in
the *value* of a connection string matches none of those names and goes out in
clear text.

This app is one environment variable away from that. `REDIS_URL` feeds
`CACHES["default"]["LOCATION"]`, `CELERY_BROKER_URL` and
`CELERY_RESULT_BACKEND` (settings.py), and the moment that URL carries
`redis://:<password>@host` all three mail the password. Those are the same three
settings that leaked a live Redis password from two sibling projects, each of
which had to be fixed after the fact (ROS-3693, ROS-3694). The deployed
`REDIS_URL` has no password today, so this is a guard, not a repair.

Redacting by value covers the shape without hiding anything useful: host, port
and database number survive, which is the part worth reading during an incident.

Scope, stated honestly: this catches credentials in URL userinfo
(`scheme://user:password@host`), which is the shape every connection string in
this project uses. Django's inherited name rules still cover keys called
PASSWORD / SECRET / TOKEN and friends, including nested ones such as
`DATABASES["default"]["PASSWORD"]`. A secret held some third way — a
query-string parameter, say — is covered by neither.
"""

import re

from django.views.debug import SafeExceptionReporterFilter

# scheme://user:password@host — the password group is what gets replaced.
# Deliberately not anchored: these turn up inside longer strings (a Celery
# broker URL, a cache LOCATION, a Sentry DSN) as well as alone.
_URL_CREDENTIALS = re.compile(
    r"(?P<prefix>[a-zA-Z][a-zA-Z0-9+.\-]*://[^/\\@\s:]*:)(?P<password>[^/\\@\s]+)(?P<at>@)"
)


class CredentialSafeReporterFilter(SafeExceptionReporterFilter):
    """SafeExceptionReporterFilter that also redacts credentials inside values.

    Deliberately does NOT extend the inherited name regex with CACHES /
    CELERY_BROKER_URL / DATABASES. Blanking those by name would hide the host,
    port and database number too, and it would still fail open for the next
    connection setting to arrive under a name nobody thought to add. Scrubbing
    the password out of the value covers both.
    """

    def cleanse_setting(self, key, value):
        cleansed = super().cleanse_setting(key, value)
        if isinstance(cleansed, str) and cleansed != self.cleansed_substitute:
            cleansed = _URL_CREDENTIALS.sub(
                lambda m: m["prefix"] + self.cleansed_substitute + m["at"], cleansed
            )
        return cleansed
