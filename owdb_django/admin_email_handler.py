"""Admin error mail that reports its own failed sends.

Django's `AdminEmailHandler` sends with `fail_silently=True` on a connection that
is also `fail_silently=True`, so when SMTP is broken every 500 notice disappears
without a trace. OWDB ran for weeks with no SMTP credentials and nothing said so.

This subclass sends with `fail_silently=False` and catches the failure itself. A
failed send is logged at ERROR with the traceback, which Sentry's logging
integration turns into an event. The request that triggered the notice is never
affected, same as before.

The logger is console-only with `propagate=False` in settings.py, so it can never
route back into this handler and loop on a broken mail server.
"""

import logging

from django.core.mail import get_connection
from django.utils.log import AdminEmailHandler

logger = logging.getLogger(__name__)


class LoggedAdminEmailHandler(AdminEmailHandler):
    def connection(self):
        return get_connection(backend=self.email_backend, fail_silently=False)

    def send_mail(self, subject, message, *args, **kwargs):
        kwargs["fail_silently"] = False
        try:
            super().send_mail(subject, message, *args, **kwargs)
        except Exception:
            logger.exception("Admin error email failed to send")
