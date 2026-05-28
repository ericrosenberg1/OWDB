"""
Tests for the rotating-review surfacing in
`owdb_django.wrestlebot.pipeline.wrestler_linking`.

Coverage:
    - Regression: the early-exit in `wrestlers_due_for_review` previously
      triggered when the COMBINED total of incomplete + complete reached
      2*limit. If many complete wrestlers came first in the queryset, the
      loop could fill up `complete` without ever discovering any
      `incomplete` entries — Al would never see the wrestlers that
      actually needed work.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from owdb_django.owdbapp.models import (
    Promotion,
    Wrestler,
    WrestlerPromotionHistory,
)
from owdb_django.wrestlebot.pipeline.wrestler_linking import (
    wrestlers_due_for_review,
)


class WrestlersDueForReviewTests(TestCase):
    def _set_updated_at(self, wrestler, when):
        # Wrestler.updated_at is auto_now=True, so a plain .save() would
        # overwrite it. Bypass via .update() which skips auto_now.
        Wrestler.objects.filter(pk=wrestler.pk).update(updated_at=when)

    def _make_complete(self, name, when):
        w = Wrestler.objects.create(
            name=name,
            about=f"Bio for {name}",
            image_url=f"https://example.com/{name}.jpg",
        )
        promo = Promotion.objects.create(name=f"Promo for {name}")
        WrestlerPromotionHistory.objects.create(
            wrestler=w,
            promotion=promo,
            start_year=2020,
        )
        self._set_updated_at(w, when)
        return w

    def _make_incomplete(self, name, when):
        # No bio, no image, no promotion history — fails all three checks.
        w = Wrestler.objects.create(name=name)
        self._set_updated_at(w, when)
        return w

    def test_incomplete_surfaced_alongside_complete_rotation(self):
        """
        With 30 complete (older) + 5 incomplete (newer but still overdue),
        the function should return all 5 incomplete plus 20 complete for
        the rotation slot. The old break condition (`>= limit * 2`) could
        starve the incomplete list when complete wrestlers dominated the
        early queryset; the new condition keeps iterating until BOTH lists
        are at their cap (or the queryset is exhausted).
        """
        cutoff = timezone.now() - timedelta(days=60)

        complete_ids = []
        for i in range(30):
            # Older updated_at => they come first in qs (ordered ASC).
            w = self._make_complete(
                f"Complete {i:02d}",
                cutoff + timedelta(minutes=i),
            )
            complete_ids.append(w.id)

        incomplete_ids = []
        for i in range(5):
            # Newer updated_at than the 30 complete, but still > 14 days
            # old so they're surfaced by the `updated_at__lt=cutoff` filter.
            w = self._make_incomplete(
                f"Incomplete {i}",
                timezone.now() - timedelta(days=20, minutes=-i),
            )
            incomplete_ids.append(w.id)

        result = wrestlers_due_for_review(days_since_review=14, limit=20)
        result_ids = [w.id for w in result]

        self.assertEqual(
            len(result),
            25,
            "Should return all 5 incomplete + 20 complete (up to `limit` per tier)",
        )

        for inc_id in incomplete_ids:
            self.assertIn(
                inc_id,
                result_ids,
                "Every incomplete wrestler must surface — the old break "
                "condition could hide them when complete wrestlers "
                "filled the early queryset",
            )

        result_complete = [i for i in result_ids if i in complete_ids]
        self.assertEqual(
            len(result_complete),
            20,
            "Exactly `limit` complete wrestlers should ride along for the rotation slot",
        )

        # The 20 surfaced complete should be the 20 oldest (most overdue),
        # since qs is ordered by updated_at ASC and the function slices
        # `complete[:limit]`.
        self.assertEqual(
            result_complete,
            complete_ids[:20],
            "The 20 complete should be the 20 most-overdue (oldest "
            "updated_at) — those are the ones the rotation prioritises",
        )
