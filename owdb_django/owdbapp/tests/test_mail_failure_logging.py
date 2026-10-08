"""A failed mail send must be logged at ERROR, never swallowed.

Signup and resend-verification caught the send error and only showed the user a
message, and Django's AdminEmailHandler sends with fail_silently=True. With no
SMTP credentials in production, the site sent nothing for weeks and nothing
reported it. Each path now calls `logger.exception`, which Sentry's logging
integration files as an event, while the user-facing result stays the same.

`FailingEmailBackend` behaves like the SMTP backend against a dead server: it
raises unless the connection was opened with fail_silently=True.
"""

import logging
import smtplib
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.core.cache import cache
from django.core.mail.backends.base import BaseEmailBackend
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from owdb_django.admin_email_handler import LoggedAdminEmailHandler

from ..models import EmailVerificationToken, UserProfile
from .proxied_client import proxied_client

FAILING_BACKEND = "owdb_django.owdbapp.tests.test_mail_failure_logging.FailingEmailBackend"
VIEWS_LOGGER = "owdb_django.owdbapp.views"
HANDLER_LOGGER = "owdb_django.admin_email_handler"


class FailingEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if self.fail_silently:
            return 0
        raise smtplib.SMTPSenderRefused(530, b"Authentication required", "noreply@example.com")


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


SIGNUP_DATA = {
    "username": "mailfail",
    "email": "mailfail@example.com",
    "password1": "testpassword123",
    "password2": "testpassword123",
}


class SignupMailFailureTest(TestCase):
    def setUp(self):
        # Rate-limit counters live in the locmem cache, which outlives a test.
        cache.clear()
        self.client = proxied_client()

    @override_settings(EMAIL_BACKEND=FAILING_BACKEND)
    def test_failed_verification_mail_is_logged_and_signup_still_succeeds(self):
        with self.assertLogs(VIEWS_LOGGER, level="ERROR") as logs:
            response = self.client.post(reverse("signup"), SIGNUP_DATA)

        self.assertRedirects(response, reverse("verification_pending"))
        user = User.objects.get(username="mailfail")
        self.assertTrue(EmailVerificationToken.objects.filter(user=user).exists())
        self.assertIn(
            "Account created, but we could not send verification email. Please contact support.",
            message_texts(response),
        )

        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.levelno, logging.ERROR)
        self.assertIn("signup", record.getMessage())
        self.assertIn(f"user_id={user.pk}", record.getMessage())
        # logger.exception, not logger.error: the traceback is what Sentry groups on.
        self.assertIsNotNone(record.exc_info)
        self.assertIsInstance(record.exc_info[1], smtplib.SMTPSenderRefused)
        # No address in the log line (send_default_pii is off for Sentry).
        self.assertNotIn("mailfail@example.com", record.getMessage())

    def test_successful_verification_mail_logs_nothing(self):
        with self.assertNoLogs(VIEWS_LOGGER, level="ERROR"):
            response = self.client.post(reverse("signup"), SIGNUP_DATA)

        self.assertRedirects(response, reverse("verification_pending"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["mailfail@example.com"])


class ResendVerificationMailFailureTest(TestCase):
    def setUp(self):
        self.client = proxied_client()
        self.user = User.objects.create_user(
            username="resender", email="resender@example.com", password="testpassword123"
        )
        UserProfile.objects.create(user=self.user, email_verified=False, can_contribute=False)
        self.client.login(username="resender", password="testpassword123")

    @override_settings(EMAIL_BACKEND=FAILING_BACKEND)
    def test_failed_resend_is_logged_and_user_sees_the_error(self):
        with self.assertLogs(VIEWS_LOGGER, level="ERROR") as logs:
            response = self.client.get(reverse("resend_verification"))

        self.assertRedirects(response, reverse("verification_pending"))
        self.assertIn(
            "Failed to send verification email. Please try again later.",
            message_texts(response),
        )

        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertIn("resend", record.getMessage())
        self.assertIn(f"user_id={self.user.pk}", record.getMessage())
        self.assertIsNotNone(record.exc_info)
        self.assertIsInstance(record.exc_info[1], smtplib.SMTPSenderRefused)

    def test_successful_resend_logs_nothing(self):
        with self.assertNoLogs(VIEWS_LOGGER, level="ERROR"):
            response = self.client.get(reverse("resend_verification"))

        self.assertRedirects(response, reverse("verification_pending"))
        self.assertEqual(len(mail.outbox), 1)


def error_record():
    try:
        raise ValueError("boom")
    except ValueError:
        exc_info = sys.exc_info()
    return logging.LogRecord(
        name="django.request",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="Internal Server Error: /x/",
        args=(),
        exc_info=exc_info,
    )


@override_settings(ADMINS=["admin@example.com"])
class AdminEmailHandlerFailureTest(SimpleTestCase):
    def test_settings_use_the_logged_handler(self):
        handler = settings.LOGGING["handlers"]["mail_admins"]
        self.assertEqual(
            handler["class"], "owdb_django.admin_email_handler.LoggedAdminEmailHandler"
        )
        # The failure logger must never route back into mail_admins.
        logger_config = settings.LOGGING["loggers"][HANDLER_LOGGER]
        self.assertEqual(logger_config["handlers"], ["console"])
        self.assertFalse(logger_config["propagate"])

    @override_settings(EMAIL_BACKEND=FAILING_BACKEND)
    def test_failed_admin_mail_is_logged_not_raised(self):
        handler = LoggedAdminEmailHandler()
        with self.assertLogs(HANDLER_LOGGER, level="ERROR") as logs:
            handler.emit(error_record())  # must not raise

        self.assertEqual(len(logs.records), 1)
        record = logs.records[0]
        self.assertEqual(record.getMessage(), "Admin error email failed to send")
        self.assertIsInstance(record.exc_info[1], smtplib.SMTPSenderRefused)

    def test_successful_admin_mail_logs_nothing(self):
        handler = LoggedAdminEmailHandler()
        with self.assertNoLogs(HANDLER_LOGGER, level="ERROR"):
            handler.emit(error_record())

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["admin@example.com"])
