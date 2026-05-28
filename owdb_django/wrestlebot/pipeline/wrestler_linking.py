"""
Wrestler interlinking — promotion-history coverage + rotating review.

Two jobs:

  1. Promotion linking — scan a wrestler's stored Wikipedia source content
     for promotion mentions, create WrestlerPromotionHistory rows when we
     can confirm the wrestler actually worked there.

  2. Rotating review queue — surface the N wrestlers whose data hasn't
     been refreshed in M days. Powers Al's "living database" sweep.

Accuracy contract:
  - We only create a promotion link if the wrestler's stored Wikipedia
    content contains either a clear promotion-mention link AND a year
    range, OR the promotion's name appears in a contextual position
    (infobox 'Promotions worked' / 'Billed from' / etc.). We DO NOT
    create links from prose-only mentions because Wikipedia commonly
    mentions opponents and other wrestlers' promotions in passing.
  - WWE/WWF and similar predecessor relationships are honored: linking
    a wrestler to "World Wrestling Federation" also surfaces the
    "WWE" connection on the UI, but we don't silently duplicate rows.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)


# Promotions that share an identity / lineage. Linking a wrestler to one
# means the UI should surface the other as a known-equivalent.
#
# Key: canonical promotion-name (the current name).
# Value: tuple of names that should be merged-or-aliased under the key.
PROMOTION_EQUIVALENCE_GROUPS: dict[str, tuple[str, ...]] = {
    "WWE": ("World Wrestling Federation", "World Wide Wrestling Federation",
            "WWWF", "WWF", "WWE"),
    "Total Nonstop Action Wrestling": (
        "Total Nonstop Action Wrestling", "TNA Wrestling", "TNA",
        "Impact Wrestling", "Impact!",
    ),
    "World Championship Wrestling": (
        "World Championship Wrestling", "Jim Crockett Promotions",
        "Mid-Atlantic Championship Wrestling",
    ),
}


def _build_promotion_aliases() -> dict[str, "Promotion"]:
    """
    Map every promotion alias (lowercase) → its Promotion row.
    Uses both Promotion.name + Promotion.abbreviation + equivalence groups.
    """
    from owdb_django.owdbapp.models import Promotion
    out: dict[str, "Promotion"] = {}
    # Exclude rows that have been rejected by Earl / a human (e.g.
    # "Royal Rumble match" was wrongly classified as a promotion).
    # Also exclude obviously-not-a-promotion names (anything ending
    # 'match', 'tournament', etc.).
    bad_tokens = (" match", " tournament", " championship", " title")
    qs = Promotion.objects.only("id", "name", "abbreviation", "nicknames",
                                 "verification_state")
    for p in qs:
        if getattr(p, "verification_state", None) == "rejected":
            continue
        low = p.name.lower()
        if any(low.endswith(tok) for tok in bad_tokens):
            continue
        out[p.name.strip().lower()] = p
        if getattr(p, "abbreviation", None):
            out[p.abbreviation.strip().lower()] = p
        for a in (getattr(p, "nicknames", "") or "").split(","):
            a = a.strip().lower()
            if a:
                out.setdefault(a, p)
    # Equivalence groups: if any alias resolves to a known Promotion row,
    # also map every other alias in that group to the same row.
    for canonical, aliases in PROMOTION_EQUIVALENCE_GROUPS.items():
        target = out.get(canonical.lower())
        if not target:
            # Fall back to ANY alias in this group that resolved.
            for alt in aliases:
                target = out.get(alt.lower())
                if target:
                    break
        if not target:
            continue
        for alt in aliases:
            out.setdefault(alt.lower(), target)
    return out


# ----------------------------------------------------------------- linking


@dataclass
class WrestlerLinkingReport:
    """Summary of one wrestler's promotion-linking pass."""
    wrestler_id: int
    wrestler_name: str
    existing_promotion_count: int = 0
    new_promotion_links: list[str] = field(default_factory=list)
    mention_hits: dict[str, int] = field(default_factory=dict)
    skipped_low_confidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "wrestler_id": self.wrestler_id,
            "wrestler_name": self.wrestler_name,
            "existing_promotion_count": self.existing_promotion_count,
            "new_promotion_links": self.new_promotion_links,
            "mention_hits_top_5": dict(
                sorted(self.mention_hits.items(), key=lambda kv: -kv[1])[:5]
            ),
            "skipped_low_confidence": self.skipped_low_confidence[:10],
        }


def _count_promotion_mentions(html: str, promotion_lookup: dict) -> Counter:
    """
    For an HTML page, count how many times each promotion alias appears
    in `<a href="/wiki/X">` link targets. We restrict to LINKS specifically
    because prose mentions are noisy (every "vs. wrestler-X" article on
    a wrestler's page mentions opponents' promotions in passing).
    """
    hits: Counter = Counter()
    if not html:
        return hits
    # Build a regex of alias→promotion for fast scanning over hrefs.
    for href_match in re.finditer(r'href="/wiki/([^"#?]+)"', html):
        target = href_match.group(1).replace("_", " ").strip()
        target_lc = target.lower()
        if target_lc in promotion_lookup:
            hits[target_lc] += 1
    return hits


def link_wrestler_promotions(wrestler) -> WrestlerLinkingReport:
    """
    Examine a wrestler's stored Wikipedia source content and create
    WrestlerPromotionHistory rows for promotions that are clearly mentioned
    (linked at least twice in the article — a single passing reference
    isn't enough evidence the wrestler worked there).

    Idempotent — won't create a duplicate (wrestler, promotion) row.
    """
    from owdb_django.owdbapp.models import (
        WrestlerPromotionHistory,
    )
    from ..models import SourceFetch

    report = WrestlerLinkingReport(
        wrestler_id=wrestler.id, wrestler_name=wrestler.name,
    )
    existing_promo_ids = set(
        WrestlerPromotionHistory.objects.filter(wrestler=wrestler)
        .values_list("promotion_id", flat=True)
    )
    report.existing_promotion_count = len(existing_promo_ids)

    fetch = (SourceFetch.objects
             .filter(entity_type="wrestler", entity_id=wrestler.id,
                     source="wikipedia", http_status=200)
             .order_by("-fetched_at").first())
    if not fetch or not fetch.raw_content:
        return report

    promotion_lookup = _build_promotion_aliases()
    if not promotion_lookup:
        return report

    hits = _count_promotion_mentions(fetch.raw_content, promotion_lookup)
    report.mention_hits = dict(hits)

    # We need strong evidence the wrestler actually worked there, not just
    # that the article happens to mention the promotion in passing. Bret
    # Hart's WWE article links to AEW + ROH + TNA + NJPW + etc. — those are
    # peers and successors of wrestlers he influenced, not his own work.
    #
    # Threshold tuned from a Roman Reigns / Becky Lynch / Bret Hart sample:
    # legitimate promotions for an active wrestler land at 10-100+ hits;
    # passing references max out around 2-3.
    LINK_HIT_THRESHOLD = 5

    for alias_lc, count in hits.most_common():
        promotion = promotion_lookup.get(alias_lc)
        if promotion is None:
            continue
        if promotion.id in existing_promo_ids:
            continue
        if count < LINK_HIT_THRESHOLD:
            report.skipped_low_confidence.append(f"{alias_lc} ({count} hit)")
            continue
        try:
            WrestlerPromotionHistory.objects.create(
                wrestler=wrestler, promotion=promotion,
                notes=f"Linked from Wikipedia article (≥{count} wiki-link hits)",
            )
            existing_promo_ids.add(promotion.id)
            report.new_promotion_links.append(promotion.name)
        except Exception as e:
            logger.warning(
                "Promotion link create failed (wrestler #%d → %s): %s",
                wrestler.id, promotion.name, e,
            )
    return report


def link_all_unlinked_wrestlers(limit: int = 30) -> dict:
    """
    Process wrestlers with FEWER than 2 promotion links + a stored
    Wikipedia source fetch. Returns a summary dict.
    """
    from django.db.models import Count
    from owdb_django.owdbapp.models import Wrestler

    candidates = (Wrestler.objects
                  .annotate(n_promos=Count("promotion_history"))
                  .filter(n_promos__lt=2, wikipedia_url__isnull=False)
                  .exclude(wikipedia_url="")
                  .order_by("id")[:limit])

    stats = {"processed": 0, "links_created": 0, "wrestlers": []}
    for w in candidates:
        rep = link_wrestler_promotions(w)
        stats["processed"] += 1
        stats["links_created"] += len(rep.new_promotion_links)
        if rep.new_promotion_links:
            stats["wrestlers"].append(rep.to_dict())
    return stats


# ---------------------------------------------------------- rotating review


def wrestlers_due_for_review(days_since_review: int = 14,
                            limit: int = 20) -> list:
    """
    Return wrestlers whose `updated_at` is older than `days_since_review`,
    ordered oldest first. The "living database" sweep — Al rotates through
    the roster.

    Wrestlers without ANY image, bio, or promotion links are prioritised
    first (they're the most-incomplete entries).
    """
    from django.db.models import Count
    from owdb_django.owdbapp.models import Wrestler

    cutoff = timezone.now() - timedelta(days=days_since_review)
    qs = (Wrestler.objects
          .filter(updated_at__lt=cutoff)
          .annotate(n_promos=Count("promotion_history"))
          .order_by("updated_at"))

    # Two-tier sort: incomplete first, then oldest within each tier.
    incomplete = []
    complete = []
    for w in qs.iterator():
        is_incomplete = (
            not w.about
            or not w.image_url
            or w.n_promos == 0
        )
        if is_incomplete:
            incomplete.append(w)
        else:
            complete.append(w)
        if len(incomplete) >= limit and len(complete) >= limit:
            break

    return incomplete[:limit] + complete[:limit]
