"""
Consistency self-checks for entity data.

Pure-Python rules engine: takes an entity, returns a list of issues. No
external sources, no LLM calls — just internal-consistency validation
("does the data we have contradict itself?").

These checks complement the source-grounding work in verify.py: that one
proves a fact came from a citable source. THIS one proves the facts don't
contradict each other.

Issues are logged to WrestleBotActivity (action_type='error'). High-severity
issues also lower FieldProvenance.confidence on the offending field so the
reconcile pipeline can prefer alternate sources next round.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsistencyIssue:
    severity: str       # "warning" | "error"
    field: str          # e.g. "debut_year" or "(multi)"
    message: str        # human-readable
    rule: str           # the rule id (for tracking)


# -- pure check functions ----------------------------------------------------


def _check_dates(birth: Optional[date], death: Optional[date]) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    if birth and death:
        if death < birth:
            issues.append(ConsistencyIssue(
                severity="error",
                field="death_date",
                message=f"death_date {death} is before birth_date {birth}",
                rule="death_before_birth",
            ))
        elif (death - birth).days < 365 * 5:
            issues.append(ConsistencyIssue(
                severity="warning",
                field="death_date",
                message=f"death_date is less than 5 years after birth_date — suspicious",
                rule="death_too_soon",
            ))
    if birth and birth.year < 1850:
        issues.append(ConsistencyIssue(
            severity="error", field="birth_date",
            message=f"birth_date year {birth.year} is implausible (<1850)",
            rule="birth_year_too_old",
        ))
    if birth and birth.year > date.today().year - 5:
        issues.append(ConsistencyIssue(
            severity="warning", field="birth_date",
            message=f"birth_date year {birth.year} implies wrestler is under 5 yrs old",
            rule="birth_year_too_new",
        ))
    return issues


def _check_career_years(
    birth: Optional[date],
    debut: Optional[int],
    retirement: Optional[int],
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    if debut and retirement:
        if retirement < debut:
            issues.append(ConsistencyIssue(
                severity="error", field="retirement_year",
                message=f"retirement_year {retirement} is before debut_year {debut}",
                rule="retirement_before_debut",
            ))
        if retirement - debut > 70:
            issues.append(ConsistencyIssue(
                severity="warning", field="retirement_year",
                message=f"career length {retirement - debut} yrs > 70 — verify",
                rule="career_too_long",
            ))
    if birth and debut:
        age_at_debut = debut - birth.year
        if age_at_debut < 12:
            issues.append(ConsistencyIssue(
                severity="error", field="debut_year",
                message=f"age at debut ({age_at_debut}) is implausibly young",
                rule="debut_too_young",
            ))
        if age_at_debut > 60:
            issues.append(ConsistencyIssue(
                severity="warning", field="debut_year",
                message=f"age at debut ({age_at_debut}) is unusually old — verify",
                rule="debut_too_old",
            ))
    return issues


_NAME_BAD_CHARS = re.compile(r"[\n\r\t]|^\s*$")
_NAME_TOO_LONG = 100
_FINISHERS_TOO_LONG = 600

# Heuristic: a value that contains a verb / clause connector + a 4-digit
# year is almost certainly prose, not a name or trainer list. "Stu Hart"
# and "The Moondogs" are valid names so we deliberately allow "The".
_PROSE_GIVEAWAYS = re.compile(
    r"\b(born|wrestler|debuted|debut|retired|known as|wrestling)\b"
    r"|\b(19|20)\d{2}\b",
    re.IGNORECASE,
)

# Aliases shouldn't be a single long sentence — typical structure is
# comma-separated short phrases.
_ALIASES_AVG_SEGMENT_LEN = 60  # average comma-segment length above which we get suspicious


def _check_strings(
    real_name: Optional[str],
    finishers: Optional[str],
    aliases: Optional[str],
    trained_by: Optional[str],
) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []

    if real_name:
        if _NAME_BAD_CHARS.search(real_name):
            issues.append(ConsistencyIssue(
                severity="warning", field="real_name",
                message="real_name contains newlines or whitespace-only chars",
                rule="real_name_format",
            ))
        if len(real_name) > _NAME_TOO_LONG:
            issues.append(ConsistencyIssue(
                severity="warning", field="real_name",
                message=f"real_name length {len(real_name)} > {_NAME_TOO_LONG}; likely captured a sentence",
                rule="real_name_too_long",
            ))
        if _PROSE_GIVEAWAYS.search(real_name):
            issues.append(ConsistencyIssue(
                severity="warning", field="real_name",
                message=f"real_name {real_name!r} contains prose words/year markers — likely a fragment, not a name",
                rule="real_name_prose_fragment",
            ))
        # A proper name should have at least one space (i.e., a first+last form).
        if " " not in real_name.strip() and not real_name.strip().startswith(("Dr", "Mr")):
            issues.append(ConsistencyIssue(
                severity="warning", field="real_name",
                message=f"real_name {real_name!r} has no spaces — possibly an alias mislabelled as real name",
                rule="real_name_single_token",
            ))

    if finishers and len(finishers) > _FINISHERS_TOO_LONG:
        issues.append(ConsistencyIssue(
            severity="warning", field="finishers",
            message=f"finishers length {len(finishers)} > {_FINISHERS_TOO_LONG}; review",
            rule="finishers_too_long",
        ))

    if aliases:
        # Detect leftover artifacts: a lone " or , inside an alias entry.
        segments = [s.strip() for s in aliases.split(",") if s.strip()]
        if segments:
            stray = [s for s in segments if s in ('"', "'", "[", "]", "(", ")")]
            if stray:
                issues.append(ConsistencyIssue(
                    severity="warning", field="aliases",
                    message=f"aliases contains {len(stray)} stray punctuation token(s): {stray!r}",
                    rule="aliases_stray_punct",
                ))
            avg_len = sum(len(s) for s in segments) / len(segments)
            if avg_len > _ALIASES_AVG_SEGMENT_LEN:
                issues.append(ConsistencyIssue(
                    severity="warning", field="aliases",
                    message=f"aliases avg segment length {avg_len:.0f} > {_ALIASES_AVG_SEGMENT_LEN}; may be unparsed prose",
                    rule="aliases_too_prose",
                ))

    if trained_by:
        # Trainer field shouldn't contain dates or prose words.
        if _PROSE_GIVEAWAYS.search(trained_by):
            issues.append(ConsistencyIssue(
                severity="warning", field="trained_by",
                message=f"trained_by {trained_by!r} contains prose/year tokens — review",
                rule="trained_by_prose_fragment",
            ))
        if ",," in trained_by:
            issues.append(ConsistencyIssue(
                severity="warning", field="trained_by",
                message="trained_by contains empty list entry (',,')",
                rule="trained_by_empty_segment",
            ))

    return issues


def _check_field_presence(wrestler) -> list[ConsistencyIssue]:
    """Sanity checks on the presence/absence of related fields."""
    issues: list[ConsistencyIssue] = []
    # If we know a retirement year, we ought to also know a debut year.
    if wrestler.retirement_year and not wrestler.debut_year:
        issues.append(ConsistencyIssue(
            severity="warning", field="debut_year",
            message="retirement_year is set but debut_year is missing — review",
            rule="retirement_without_debut",
        ))
    # If we have a death_date but no birth_date, that's odd.
    if wrestler.death_date and not wrestler.birth_date:
        issues.append(ConsistencyIssue(
            severity="warning", field="birth_date",
            message="death_date is set but birth_date is missing — review",
            rule="death_without_birth",
        ))
    return issues


_HEIGHT_OK = re.compile(r"\d+(\s*ft|\s*'|\s*cm|\s*m\b)", re.IGNORECASE)
_WEIGHT_OK = re.compile(r"\d+(\s*lb|\s*kg|\s*pound)", re.IGNORECASE)


def _check_physical(height: Optional[str], weight: Optional[str]) -> list[ConsistencyIssue]:
    issues: list[ConsistencyIssue] = []
    if height and not _HEIGHT_OK.search(height):
        issues.append(ConsistencyIssue(
            severity="warning", field="height",
            message=f"height value {height!r} doesn't match expected unit pattern",
            rule="height_format",
        ))
    if weight and not _WEIGHT_OK.search(weight):
        issues.append(ConsistencyIssue(
            severity="warning", field="weight",
            message=f"weight value {weight!r} doesn't match expected unit pattern",
            rule="weight_format",
        ))
    return issues


# -- public API --------------------------------------------------------------


def check_match(match) -> list[ConsistencyIssue]:
    """
    Match-level consistency checks. Codex P1-11 — match data had zero
    audit coverage before this.

    Rules:
      match_no_participants    Match exists with neither wrestlers M2M nor
                               MatchParticipant rows — impossible IRL.
      match_duration_implausible  Bell-to-bell over 4 hours is almost
                               certainly a parser error (one Iron Man match
                               held the record at 60 min).
      match_title_change_without_title  title_changed=True but no Title
                               FK — flag for cleanup.
      match_unresolved_participants  match.about contains an "Unresolved
                               participants:" note, meaning some names
                               couldn't be linked. Calls for Al.
      match_verified_without_winner  outcome_type != draw/no_contest and
                               we have a winning_side but no winner FK —
                               head-to-head will silently mis-attribute.
    """
    issues: list[ConsistencyIssue] = []

    n_participants = match.wrestlers.count()
    n_links = match.participant_links.count()
    if n_participants == 0 and n_links == 0:
        issues.append(ConsistencyIssue(
            severity="error", field="wrestlers",
            message="Match has zero participants",
            rule="match_no_participants",
        ))

    if match.duration_seconds is not None and match.duration_seconds > 4 * 3600:
        issues.append(ConsistencyIssue(
            severity="error", field="duration_seconds",
            message=f"Match duration {match.duration_seconds}s exceeds 4 hours — likely parse error",
            rule="match_duration_implausible",
        ))

    if match.title_changed and not match.title_id:
        issues.append(ConsistencyIssue(
            severity="warning", field="title_changed",
            message="title_changed=True but no Title FK",
            rule="match_title_change_without_title",
        ))

    if "Unresolved participants:" in (match.about or ""):
        issues.append(ConsistencyIssue(
            severity="warning", field="wrestlers",
            message="Match has unresolved participant names — needs Al to backfill",
            rule="match_unresolved_participants",
        ))

    if (match.winning_side is not None
            and match.outcome_type not in ("draw", "no_contest")
            and not match.winner_id):
        issues.append(ConsistencyIssue(
            severity="warning", field="winner",
            message="Decisive match has a winning_side but no winner FK; head-to-head will under-credit",
            rule="match_winner_without_fk",
        ))

    return issues


def check_image_legal_use(entity_type: str, entity) -> list[ConsistencyIssue]:
    """
    Image legal-compliance rules — every entity with image_url MUST also
    have a license + credit + source URL. Catches direct writes that
    bypass the assign_image_to_entity() gate.

    Rules:
      image_without_license       Entity has image_url but image_license=''
      image_credit_missing        License requires attribution and image_credit is empty
      image_license_not_allowed   image_license outside our whitelist
      image_no_source_url         image_url set but image_source_url empty (can't audit)
    """
    issues: list[ConsistencyIssue] = []
    if not hasattr(entity, "image_url"):
        return issues
    img = getattr(entity, "image_url", None) or ""
    if not img:
        return issues  # no image, no problem

    from ..sources.commons import ALLOWED_LICENSES

    license_code = (getattr(entity, "image_license", None) or "").strip()
    credit = (getattr(entity, "image_credit", None) or "").strip()
    source_url = (getattr(entity, "image_source_url", None) or "").strip()

    if not license_code:
        issues.append(ConsistencyIssue(
            severity="error", field="image_license",
            message=f"Entity has image_url but no image_license — legal-use unknown",
            rule="image_without_license",
        ))

    allowed_codes = set(ALLOWED_LICENSES.values())
    if license_code and license_code not in allowed_codes:
        issues.append(ConsistencyIssue(
            severity="error", field="image_license",
            message=(
                f"image_license={license_code!r} is not in OWDB allow-list "
                f"({sorted(allowed_codes)}). May be NC/ND/non-free."
            ),
            rule="image_license_not_allowed",
        ))

    # CC-BY and CC-BY-SA REQUIRE attribution. PD/CC0 don't.
    if license_code in ("cc-by", "cc-by-sa") and not credit:
        issues.append(ConsistencyIssue(
            severity="error", field="image_credit",
            message=(
                f"image_license={license_code} requires attribution but "
                f"image_credit is empty — legal-compliance violation"
            ),
            rule="image_credit_missing",
        ))

    if not source_url:
        issues.append(ConsistencyIssue(
            severity="warning", field="image_source_url",
            message="image_url set but image_source_url empty — provenance unauditable",
            rule="image_no_source_url",
        ))

    return issues


def check_provenance_coverage(entity_type: str, entity) -> list[ConsistencyIssue]:
    """
    Cross-cutting rule: any entity with verified=True OR
    verification_state="verified" MUST have FieldProvenance for its
    contract-required fields. Catches Codex P1 #1 / #4 / #7 regressions.
    """
    issues: list[ConsistencyIssue] = []
    try:
        from .accuracy_contract import CONTRACTS
    except ImportError:
        return issues
    contract = CONTRACTS.get(entity_type)
    if contract is None:
        return issues

    state = getattr(entity, "verification_state", None)
    legacy_verified = getattr(entity, "verified", False)
    # If the entity claims to be verified, the contract must hold.
    if state == "verified" or legacy_verified:
        passed, missing = contract.is_satisfied(entity.id)
        if not passed:
            issues.append(ConsistencyIssue(
                severity="error", field="verification_state",
                message=(
                    f"{entity_type} #{entity.id} claims verified state but "
                    f"FieldProvenance missing for: {', '.join(missing)}"
                ),
                rule="verified_without_provenance",
            ))
    return issues


def check_event(event) -> list[ConsistencyIssue]:
    """Sanity checks on Event fields. Run from wb_audit and post-persist."""
    issues: list[ConsistencyIssue] = []
    if event.attendance is not None:
        if event.attendance < 100:
            issues.append(ConsistencyIssue(
                severity="warning", field="attendance",
                message=f"attendance {event.attendance} is implausibly low",
                rule="attendance_too_low",
            ))
        if event.attendance > 200_000:
            issues.append(ConsistencyIssue(
                severity="error", field="attendance",
                message=f"attendance {event.attendance:,} exceeds any plausible wrestling event — likely parser artifact",
                rule="attendance_too_high",
            ))
    if event.date is not None:
        from datetime import date as _date
        if event.date.year < 1900 or event.date.year > _date.today().year + 2:
            issues.append(ConsistencyIssue(
                severity="warning", field="date",
                message=f"event date {event.date} year is implausible",
                rule="event_date_year",
            ))
    return issues


def check_venue(venue) -> list[ConsistencyIssue]:
    """Sanity checks on Venue fields."""
    issues: list[ConsistencyIssue] = []
    if venue.capacity is not None:
        if venue.capacity < 50:
            issues.append(ConsistencyIssue(
                severity="warning", field="capacity",
                message=f"capacity {venue.capacity} is implausibly low for a wrestling venue",
                rule="capacity_too_low",
            ))
        if venue.capacity > 300_000:
            issues.append(ConsistencyIssue(
                severity="error", field="capacity",
                message=f"capacity {venue.capacity:,} exceeds plausible venue — likely parser artifact",
                rule="capacity_too_high",
            ))
    if venue.opened_year is not None:
        from datetime import date as _date
        if venue.opened_year < 1800 or venue.opened_year > _date.today().year + 5:
            issues.append(ConsistencyIssue(
                severity="warning", field="opened_year",
                message=f"opened_year {venue.opened_year} is implausible",
                rule="opened_year_implausible",
            ))
    return issues


def check_wrestler(wrestler) -> list[ConsistencyIssue]:
    """Run all consistency rules over a Wrestler. Returns a list of issues."""
    issues: list[ConsistencyIssue] = []
    issues.extend(_check_dates(wrestler.birth_date, wrestler.death_date))
    issues.extend(_check_career_years(
        wrestler.birth_date, wrestler.debut_year, wrestler.retirement_year,
    ))
    issues.extend(_check_strings(
        wrestler.real_name, wrestler.finishers, wrestler.aliases, wrestler.trained_by,
    ))
    issues.extend(_check_physical(wrestler.height, wrestler.weight))
    issues.extend(_check_field_presence(wrestler))
    return issues


def log_issues(entity_type: str, entity_id: int, entity_name: str,
               issues: list[ConsistencyIssue]) -> int:
    """
    Log each issue to WrestleBotActivity. Returns the count logged.
    Caller decides whether to lower FieldProvenance.confidence based on issues.
    """
    if not issues:
        return 0

    from ..models import WrestleBotActivity
    count = 0
    for issue in issues:
        WrestleBotActivity.objects.create(
            action_type="error" if issue.severity == "error" else "verify",
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            source="consistency_check",
            details={
                "rule": issue.rule,
                "field": issue.field,
                "severity": issue.severity,
                "message": issue.message,
            },
            ai_assisted=False,
            success=False,
            error_message=issue.message,
        )
        count += 1
    logger.info(
        "Logged %d consistency issue(s) for %s#%d (%s)",
        count, entity_type, entity_id, entity_name,
    )
    return count


def lower_confidence_for_issues(
    entity_type: str, entity_id: int, issues: list[ConsistencyIssue],
) -> int:
    """
    Reduce FieldProvenance.confidence for fields flagged by error-severity
    issues. Pipeline can later prefer alternate sources for low-confidence
    fields during reconcile.
    """
    from ..models import FieldProvenance
    affected = 0
    for issue in issues:
        if issue.severity != "error" or issue.field == "(multi)":
            continue
        provs = FieldProvenance.objects.filter(
            entity_type=entity_type, entity_id=entity_id, field_name=issue.field,
        )
        for p in provs:
            new_conf = max(0, p.confidence - 50)
            if new_conf != p.confidence:
                p.confidence = new_conf
                p.save(update_fields=["confidence"])
                affected += 1
    return affected
