"""
Tests for the review-gate admin actions.

The query-level gate (VerificationQuerySet.public() in models.py) is the
"before data goes live" half of the review gate. These bulk actions are the
other half — the actual mechanism a human uses to work through the
`candidate` backlog, since nothing previously let staff change
`verification_state` at all. See VerificationActionsMixin in admin.py.

These use `proxied_client()` rather than a bare `Client()` — see
proxied_client.py (ROS-1210) for why a bare `Client()` would 301 every
request under APP_ENV=production instead of reaching the admin view.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from ..models import Promotion, Wrestler
from .proxied_client import proxied_client


class ReviewGateAdminActionsTest(TestCase):
    """Tests for VerificationActionsMixin's bulk mark_* admin actions."""

    def setUp(self):
        self.client = proxied_client()
        self.superuser = User.objects.create_superuser(
            username="reviewadmin", email="reviewadmin@example.com", password="testpass123"
        )
        self.client.login(username="reviewadmin", password="testpass123")
        self.promotion = Promotion.objects.create(
            name="Admin Action Promotion", verification_state="candidate"
        )
        self.wrestler = Wrestler.objects.create(
            name="Admin Action Wrestler", verification_state="candidate"
        )

    def test_mark_verified_action_updates_state(self):
        response = self.client.post(
            reverse("admin:owdbapp_promotion_changelist"),
            {
                "action": "mark_verified",
                "_selected_action": [str(self.promotion.pk)],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.promotion.refresh_from_db()
        self.assertEqual(self.promotion.verification_state, "verified")

    def test_mark_provisional_action_updates_state(self):
        response = self.client.post(
            reverse("admin:owdbapp_promotion_changelist"),
            {
                "action": "mark_provisional",
                "_selected_action": [str(self.promotion.pk)],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.promotion.refresh_from_db()
        self.assertEqual(self.promotion.verification_state, "provisional")

    def test_mark_rejected_action_updates_state(self):
        response = self.client.post(
            reverse("admin:owdbapp_wrestler_changelist"),
            {
                "action": "mark_rejected",
                "_selected_action": [str(self.wrestler.pk)],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.wrestler.refresh_from_db()
        self.assertEqual(self.wrestler.verification_state, "rejected")

    def test_mark_rejected_then_mark_verified_is_reversible(self):
        """A wrong rejection can be undone from the same changelist."""
        self.client.post(
            reverse("admin:owdbapp_wrestler_changelist"),
            {"action": "mark_rejected", "_selected_action": [str(self.wrestler.pk)]},
        )
        self.wrestler.refresh_from_db()
        self.assertEqual(self.wrestler.verification_state, "rejected")

        self.client.post(
            reverse("admin:owdbapp_wrestler_changelist"),
            {"action": "mark_verified", "_selected_action": [str(self.wrestler.pk)]},
        )
        self.wrestler.refresh_from_db()
        self.assertEqual(self.wrestler.verification_state, "verified")

    def test_verification_state_is_list_filterable(self):
        """`verification_state` must be usable as a changelist filter."""
        response = self.client.get(
            reverse("admin:owdbapp_promotion_changelist"), {"verification_state": "candidate"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Action Promotion")
