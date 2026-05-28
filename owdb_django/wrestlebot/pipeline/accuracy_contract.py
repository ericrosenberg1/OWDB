"""
Accuracy contract — executable rules per entity type.

The contract is the structural backbone that makes "100% accuracy" enforceable
rather than aspirational. Every persist path (canonical or bulk) MUST pass
its entity through `enforce()` before marking it `verification_state="verified"`.

Contract per entity type specifies:

  required_fields  — fields that MUST have a FieldProvenance row before
                     verification is allowed. Missing any of these → state
                     drops to "provisional" (or "candidate" if even more
                     fields are missing).
  recommended_fields — fields that SHOULD have provenance; missing them
                       lowers confidence but doesn't block verification.
  forbidden_states  — guarded transitions (e.g., verified entity with
                      zero participants — that's not a match, it's a stub).

Vocabulary:
  candidate    — entity exists because we saw a reference, but we have
                 not verified its identity (e.g., PWI orphan names,
                 unmatched match participants).
  provisional  — entity has structural data from a bulk-import source
                 but lacks per-field provenance for one or more
                 required fields. Visible on the site with a "provisional"
                 badge. Safe to display but Earl flags for upgrade.
  verified     — entity has FieldProvenance for every required field AND
                 passes all forbidden_state checks.
  rejected     — Earl or a human determined this entity is incorrect /
                 a duplicate / a junk row. Hidden from canonical views.

This module is read-by AND writes-through-by:
  - persist.py / persist_event.py / persist_media.py / persist_show.py /
    persist_title.py  — canonical extract+persist paths
  - pipeline/event_lists.py / match_extract.py / pwi.py  — bulk paths
  - bots/earl.py via consistency.check_provenance_coverage()
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Verification-state vocabulary
# ---------------------------------------------------------------------------


CANDIDATE = "candidate"
PROVISIONAL = "provisional"
VERIFIED = "verified"
REJECTED = "rejected"

VALID_STATES = (CANDIDATE, PROVISIONAL, VERIFIED, REJECTED)


# ---------------------------------------------------------------------------
# Contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Contract:
    """An accuracy contract for one entity type."""

    entity_type: str
    required_fields: tuple[str, ...]
    recommended_fields: tuple[str, ...]
    forbidden_state_checks: tuple[str, ...]  # names of check_* methods in this module

    def is_satisfied(self, entity_id: int) -> tuple[bool, list[str]]:
        """
        Returns (passed, missing_required_fields).
        If passed=True, entity is eligible for verified state.
        """
        from ..models import FieldProvenance

        covered = set(
            FieldProvenance.objects.filter(
                entity_type=self.entity_type,
                entity_id=entity_id,
                field_name__in=self.required_fields,
            )
            .values_list("field_name", flat=True)
            .distinct()
        )
        missing = [f for f in self.required_fields if f not in covered]
        return (len(missing) == 0, missing)


CONTRACTS: dict[str, Contract] = {
    # Wrestler — name is structurally required; the rest are useful but
    # not always available (some wrestlers genuinely lack a known birth date).
    "wrestler": Contract(
        entity_type="wrestler",
        required_fields=("name",),
        recommended_fields=("birth_date", "debut_year", "nationality", "hometown"),
        forbidden_state_checks=(),
    ),
    # Event — name + date are non-negotiable; venue strongly recommended.
    "event": Contract(
        entity_type="event",
        required_fields=("name", "date"),
        recommended_fields=("venue", "promotion", "attendance"),
        forbidden_state_checks=("event_must_have_promotion",),
    ),
    # Venue — name only; everything else varies.
    "venue": Contract(
        entity_type="venue",
        required_fields=("name",),
        recommended_fields=("city", "location"),
        forbidden_state_checks=("venue_name_not_a_city",),
    ),
    # Match — match_text proves we observed it; outcome is recommended.
    "match": Contract(
        entity_type="match",
        required_fields=("match_text",),
        recommended_fields=("outcome_type", "winner", "match_type", "duration_seconds"),
        forbidden_state_checks=("match_must_have_participants",),
    ),
    # Promotion — name + a year (founded or first-seen).
    "promotion": Contract(
        entity_type="promotion",
        required_fields=("name",),
        recommended_fields=("founded_year", "headquarters"),
        forbidden_state_checks=(),
    ),
    # Title — name + promotion are both required (a title without a
    # promotion is meaningless).
    "title": Contract(
        entity_type="title",
        required_fields=("name", "promotion"),
        recommended_fields=("debut_year", "title_type"),
        forbidden_state_checks=(),
    ),
    # TV show — name + promotion.
    "tv_show": Contract(
        entity_type="tv_show",
        required_fields=("name",),
        recommended_fields=("network", "premiere_year"),
        forbidden_state_checks=(),
    ),
    # Stable — name only; promotion + members highly recommended.
    "stable": Contract(
        entity_type="stable",
        required_fields=("name",),
        recommended_fields=("promotion", "formed_year"),
        forbidden_state_checks=(),
    ),
    # Book — title is the identity field. Without provenance for it,
    # the row is just a fabricated string. Author / year are recommended
    # but real books occasionally lack one or the other (out-of-print,
    # samizdat).
    "book": Contract(
        entity_type="book",
        required_fields=("title",),
        recommended_fields=("author", "publication_year", "publisher", "isbn"),
        forbidden_state_checks=(),
    ),
    # VideoGame — name is the identity field. Round-2 codex review caught
    # that the previous schema let games be created with no name-provenance
    # row, which let any fetched Wikipedia article become a VideoGame even
    # if the article was actually a person / TV show / hub list.
    "video_game": Contract(
        entity_type="video_game",
        required_fields=("name",),
        recommended_fields=("release_year", "developer", "publisher", "systems"),
        forbidden_state_checks=(),
    ),
    # Podcast — name only; hosts + launch year are recommended.
    "podcast": Contract(
        entity_type="podcast",
        required_fields=("name",),
        recommended_fields=("hosts", "launch_year"),
        forbidden_state_checks=(),
    ),
    # Special — title is the identity field for documentaries / films.
    "special": Contract(
        entity_type="special",
        required_fields=("title",),
        recommended_fields=("release_year", "kind"),
        forbidden_state_checks=(),
    ),
    # ActionFigure — name only; year + manufacturer recommended.
    "action_figure": Contract(
        entity_type="action_figure",
        required_fields=("name",),
        recommended_fields=("release_year", "manufacturer", "line"),
        forbidden_state_checks=(),
    ),
    # ThemeSong — title only; artist + year recommended.
    "theme_song": Contract(
        entity_type="theme_song",
        required_fields=("title",),
        recommended_fields=("artist", "release_year"),
        forbidden_state_checks=(),
    ),
}


# ---------------------------------------------------------------------------
# Forbidden-state checks (return list of violation messages; empty = OK)
# ---------------------------------------------------------------------------


def event_must_have_promotion(event) -> list[str]:
    if not getattr(event, "promotion_id", None):
        return ["Event has no promotion FK — meaningless without it"]
    return []


def venue_name_not_a_city(venue) -> list[str]:
    """
    Catch the multi-venue table-row bug: a venue named 'Rosemont, Illinois'
    is actually a location cell, not a venue.
    """
    import re

    name = (venue.name or "").strip()
    if not name:
        return ["Venue has empty name"]
    # Has a comma AND the second half looks like a US state / country?
    if "," in name and len(name) < 80:
        after = name.split(",")[-1].strip()
        if re.match(r"^[A-Z][A-Za-z\.\s]{1,30}$", after) and len(after) <= 30:
            return [f"Venue name {name!r} looks like a location string, not a venue"]
    return []


def match_must_have_participants(match) -> list[str]:
    if match.wrestlers.count() == 0 and match.participant_links.count() == 0:
        return ["Match has no participants — neither wrestlers M2M nor MatchParticipant rows"]
    return []


# Registry the contract layer uses to dispatch checks by name.
_FORBIDDEN_CHECK_FUNCS = {
    "event_must_have_promotion": event_must_have_promotion,
    "venue_name_not_a_city": venue_name_not_a_city,
    "match_must_have_participants": match_must_have_participants,
}


# ---------------------------------------------------------------------------
# Main entry point — call this from every persist path before marking
# an entity verified.
# ---------------------------------------------------------------------------


def enforce(entity_type: str, entity) -> tuple[str, list[str]]:
    """
    Resolve an entity's correct verification_state per its contract.

    Returns (state, reasons) where state ∈ {candidate, provisional, verified}
    and `reasons` is a list of human-readable explanations for the chosen
    state (always non-empty for provisional/candidate so Earl can quote
    them in observations).
    """
    contract = CONTRACTS.get(entity_type)
    if contract is None:
        # Unknown entity type — refuse to assert verified.
        return PROVISIONAL, [f"no accuracy contract for {entity_type!r}"]

    reasons: list[str] = []

    # Provenance coverage.
    passed, missing = contract.is_satisfied(entity.id)
    if not passed:
        reasons.append(f"Missing FieldProvenance for required fields: {', '.join(missing)}")

    # Forbidden-state checks — these are HARD blockers regardless of
    # provenance coverage.
    hard_block = False
    for check_name in contract.forbidden_state_checks:
        fn = _FORBIDDEN_CHECK_FUNCS.get(check_name)
        if fn is None:
            continue
        violations = fn(entity)
        if violations:
            reasons.extend(violations)
            hard_block = True

    if hard_block:
        # Structural violation — cannot be verified or provisional. It's
        # a candidate at best until the violation is resolved.
        return CANDIDATE, reasons

    if not passed:
        # Provenance gaps but no structural problems — provisional.
        return PROVISIONAL, reasons

    # All required provenance + all checks pass.
    return VERIFIED, []


def audit_persistence(entity_type: str, entity, *, source_fetch=None) -> dict:
    """
    One-stop check for a persist path: enforce contract + return diagnostic.

    Suggested usage at the bottom of every persist_* function:

        from .accuracy_contract import audit_persistence
        result = audit_persistence("event", event, source_fetch=fetch)
        entity.verification_state = result["state"]
        entity.save(update_fields=["verification_state"])
        return entity
    """
    state, reasons = enforce(entity_type, entity)
    return {
        "state": state,
        "reasons": reasons,
        "source_fetch_id": getattr(source_fetch, "id", None),
        "verified_eligible": state == VERIFIED,
    }
