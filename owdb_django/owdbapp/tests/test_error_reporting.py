"""An admin error email must never carry a connection-string password.

`LoggedAdminEmailHandler` mails a full settings dump on every 500. Django's
`SafeExceptionReporterFilter` redacts by setting *name*, so a password sitting
inside a *value* — `redis://:<password>@host`, the shape `REDIS_URL` gives
`CACHES`, `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` — goes out intact.
`CredentialSafeReporterFilter` scrubs the value as well.

These tests assert the mail that a real 500 produces, not the text of the
config. A sibling project's first attempt at this fix asserted the config, read
correct, and changed nothing for three months because no test measured the
handler or the message (ROS-3693). `test_the_stock_filter_would_have_leaked_it`
is the positive control: it fails if `FAKE_PASSWORD` ever stops being planted
somewhere the stock filter misses, which would make every other assertion here
pass for the wrong reason.
"""

import logging

from django.conf import settings as django_settings
from django.core import mail
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path
from django.views.debug import (
    SafeExceptionReporterFilter,
    get_default_exception_reporter_filter,
)

from owdb_django.admin_email_handler import LoggedAdminEmailHandler
from owdb_django.error_reporting import CredentialSafeReporterFilter

# Not a real credential. Distinctive enough that a substring check cannot
# collide with ordinary dump text.
FAKE_PASSWORD = "ros3694-not-a-real-password"
REDIS_WITH_PASSWORD = f"redis://:{FAKE_PASSWORD}@redis.example:6379/0"


def boom(request):
    raise RuntimeError("deliberate 500 for test_error_reporting")


def ok(request):
    return HttpResponse("ok")


urlpatterns = [
    path("__error_reporting_test_boom__/", boom),
    path("__error_reporting_test_ok__/", ok),
]

# What production hands the dump once REDIS_URL carries a password.
LEAKY_CONNECTION_SETTINGS = {
    "CELERY_BROKER_URL": REDIS_WITH_PASSWORD,
    "CELERY_RESULT_BACKEND": REDIS_WITH_PASSWORD,
    "CACHES": {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": REDIS_WITH_PASSWORD,
        }
    },
}


class CredentialSafeReporterFilterTest(SimpleTestCase):
    def setUp(self):
        self.filter = CredentialSafeReporterFilter()

    def test_password_in_a_bare_connection_string_is_redacted(self):
        cleansed = self.filter.cleanse_setting("CELERY_BROKER_URL", REDIS_WITH_PASSWORD)
        self.assertNotIn(FAKE_PASSWORD, cleansed)
        # Everything an on-call reader actually needs survives.
        self.assertIn("redis.example:6379/0", cleansed)

    def test_password_nested_inside_caches_is_redacted(self):
        cleansed = self.filter.cleanse_setting("CACHES", LEAKY_CONNECTION_SETTINGS["CACHES"])
        self.assertNotIn(FAKE_PASSWORD, repr(cleansed))

    @override_settings(**LEAKY_CONNECTION_SETTINGS)
    def test_password_survives_nowhere_in_the_full_settings_dump(self):
        self.assertNotIn(FAKE_PASSWORD, repr(self.filter.get_safe_settings()))

    @override_settings(**LEAKY_CONNECTION_SETTINGS)
    def test_the_stock_filter_would_have_leaked_it(self):
        """Positive control. Without this, the tests above could pass vacuously."""
        self.assertIn(FAKE_PASSWORD, repr(SafeExceptionReporterFilter().get_safe_settings()))

    def test_request_meta_is_scrubbed_too(self):
        cleansed = self.filter.get_safe_request_meta(
            type("R", (), {"META": {"SOME_UPSTREAM_URL": REDIS_WITH_PASSWORD}})()
        )
        self.assertNotIn(FAKE_PASSWORD, repr(cleansed))

    def test_credential_free_values_are_left_readable(self):
        for value in (
            "redis://localhost:6379/0",
            "https://wrestlingdb.org/events/",
            "not a url at all",
        ):
            with self.subTest(value=value):
                self.assertEqual(self.filter.cleanse_setting("SOME_SETTING", value), value)

    def test_name_based_redaction_is_still_inherited(self):
        """The value scrub is additive. It must not displace Django's name rules."""
        cleansed = self.filter.cleanse_setting("SOME_API_TOKEN", "plain-token-value")
        self.assertEqual(cleansed, self.filter.cleansed_substitute)


class WiringTest(SimpleTestCase):
    def test_the_configured_filter_is_the_credential_safe_one(self):
        self.assertIsInstance(get_default_exception_reporter_filter(), CredentialSafeReporterFilter)

    def test_the_admin_mail_handler_is_live_on_django_request(self):
        """Assert the handler object, not the LOGGING dict that describes it."""
        handlers = logging.getLogger("django.request").handlers
        self.assertTrue(
            any(isinstance(h, LoggedAdminEmailHandler) for h in handlers),
            f"no admin mail handler on django.request: {[type(h).__name__ for h in handlers]}",
        )

    def test_admins_is_configured_from_the_environment(self):
        """A dump only reaches an inbox when ADMINS is set, so pin where it comes from."""
        self.assertIsInstance(django_settings.ADMINS, list)


@override_settings(
    ROOT_URLCONF=__name__,
    DEBUG=False,
    ADMINS=[("Admin", "admin@example.com")],
    **LEAKY_CONNECTION_SETTINGS,
)
class AdminErrorEmailEndToEndTest(TestCase):
    """Drive the real request pipeline and read the message that comes out."""

    def setUp(self):
        self.client.raise_request_exception = False
        mail.outbox.clear()

    def _body(self, message):
        return message.body + "".join(a[0] for a in (message.alternatives or []))

    def test_a_500_still_mails_the_admins(self):
        response = self.client.get("/__error_reporting_test_boom__/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(mail.outbox), 1, [m.subject for m in mail.outbox])

    def test_the_mailed_body_does_not_contain_the_connection_password(self):
        response = self.client.get("/__error_reporting_test_boom__/")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(mail.outbox), 1, [m.subject for m in mail.outbox])
        body = self._body(mail.outbox[0])
        # The dump is still there; only the password is gone.
        self.assertIn("CELERY_BROKER_URL", body)
        self.assertIn("redis.example:6379", body)
        self.assertNotIn(FAKE_PASSWORD, body)

    def test_a_working_page_mails_nothing(self):
        response = self.client.get("/__error_reporting_test_ok__/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mail.outbox, [])
