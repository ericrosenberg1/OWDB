"""
WrestleBot 2.0 Data Quality Module

Provides comprehensive data quality checks, validation, and cleanup functionality
to ensure database entries are accurate and properly formatted.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from django.db.models import Q, Count
from django.utils.text import slugify

logger = logging.getLogger(__name__)


@dataclass
class QualityIssue:
    """Represents a data quality issue found in an entity."""
    entity_type: str
    entity_id: int
    entity_name: str
    issue_type: str  # 'error', 'warning', 'suggestion'
    issue_code: str  # machine-readable code
    description: str
    field: Optional[str] = None
    current_value: Any = None
    suggested_value: Any = None
    auto_fixable: bool = False


@dataclass
class QualityReport:
    """Summary report of data quality check results."""
    total_checked: int = 0
    entities_with_issues: int = 0
    issues: List[QualityIssue] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0
    suggestions: int = 0
    auto_fixable: int = 0

    def add_issue(self, issue: QualityIssue):
        """Add an issue to the report."""
        self.issues.append(issue)
        if issue.issue_type == 'error':
            self.errors += 1
        elif issue.issue_type == 'warning':
            self.warnings += 1
        else:
            self.suggestions += 1
        if issue.auto_fixable:
            self.auto_fixable += 1


class DataQualityChecker:
    """
    Checks data quality across all entity types.

    Issue codes:
    - INVALID_*: Data format/value errors
    - MISSING_*: Required or important data missing
    - SUSPICIOUS_*: Data that looks wrong
    - DUPLICATE_*: Potential duplicate entries
    - ORPHAN_*: Entries with broken relationships
    """

    # Patterns for detecting suspicious data
    SUSPICIOUS_NAME_PATTERNS = [
        r'^[a-z]',  # Name starting with lowercase
        r'\d{4,}',  # Contains 4+ consecutive digits
        r'[<>{}|\[\]]',  # HTML/code characters
        r'^\s|\s$',  # Leading/trailing whitespace
        r'\s{2,}',  # Multiple consecutive spaces
        r'^(test|unknown|tbd|n/a|none)$',  # Placeholder names
        r'vs\.?\s',  # Contains "vs" suggesting match text, not a name
        r',\s*\w+\s+\w+',  # Contains comma followed by another name
    ]

    # Known invalid wrestler names (common scraping artifacts)
    INVALID_WRESTLER_NAMES = {
        'unknown', 'tbd', 'vacant', 'n/a', 'none', 'test',
        'wrestler', 'champion', 'title', 'match', 'winner',
        'vs', 'defeated', 'def', 'and', 'the', 'with',
    }

    # Patterns that indicate a wrestler entry is actually a stable/faction
    STABLE_INDICATORS = [
        r'\(professional wrestling\)$',  # Wikipedia disambiguation
        r'\(wrestling\)$',
        r'\(faction\)$',
        r'\(stable\)$',
        r'\(tag team\)$',
        r'\(group\)$',
    ]

    # Known stables/factions that might be misclassified as wrestlers
    KNOWN_STABLES = {
        'retribution', 'the shield', 'd-generation x', 'dx', 'nwo', 'n.w.o.',
        'evolution', 'the nexus', 'legacy', 'the wyatt family', 'the bloodline',
        'judgment day', 'imperium', 'damage ctrl', 'the hurt business',
        'the new day', 'the usos', 'authors of pain', 'undisputed era',
        'the club', 'bullet club', 'los ingobernables', 'chaos',
        'suzuki-gun', 'united empire', 'house of black', 'the elite',
    }

    # Known tag teams that should be two wrestlers, not one entry
    # Format: 'tag team name': ['member1', 'member2']
    KNOWN_TAG_TEAMS = {
        'ftr': ['Dax Harwood', 'Cash Wheeler'],
        'the young bucks': ['Matt Jackson', 'Nick Jackson'],
        'young bucks': ['Matt Jackson', 'Nick Jackson'],
        'the usos': ['Jey Uso', 'Jimmy Uso'],
        'usos': ['Jey Uso', 'Jimmy Uso'],
        'the new day': ['Kofi Kingston', 'Xavier Woods', 'Big E'],
        'new day': ['Kofi Kingston', 'Xavier Woods', 'Big E'],
        'diy': ['Johnny Gargano', 'Tommaso Ciampa'],
        'motor city machine guns': ['Alex Shelley', 'Chris Sabin'],
        'mcmg': ['Alex Shelley', 'Chris Sabin'],
        'the hardys': ['Matt Hardy', 'Jeff Hardy'],
        'hardys': ['Matt Hardy', 'Jeff Hardy'],
        'hardy boyz': ['Matt Hardy', 'Jeff Hardy'],
        'the dudley boyz': ['Bubba Ray Dudley', 'D-Von Dudley'],
        'dudley boyz': ['Bubba Ray Dudley', 'D-Von Dudley'],
        'edge and christian': ['Edge', 'Christian'],
        'rated rko': ['Edge', 'Randy Orton'],
        'legacy': ['Cody Rhodes', 'Ted DiBiase Jr.'],
        'authors of pain': ['Akam', 'Rezar'],
        'aop': ['Akam', 'Rezar'],
        'american alpha': ['Jason Jordan', 'Chad Gable'],
        'lucha bros': ['Pentagon Jr.', 'Rey Fenix'],
        'lucha brothers': ['Pentagon Jr.', 'Rey Fenix'],
        'proud n powerful': ['Santana', 'Ortiz'],
        'santana and ortiz': ['Santana', 'Ortiz'],
        'private party': ['Marq Quen', 'Isiah Kassidy'],
        'the acclaimed': ['Max Caster', 'Anthony Bowens'],
        'acclaimed': ['Max Caster', 'Anthony Bowens'],
        'swerve in our glory': ['Swerve Strickland', 'Keith Lee'],
    }

    # Minimum/maximum reasonable values
    MIN_YEAR = 1900
    MAX_YEAR_OFFSET = 2  # Allow up to 2 years in the future

    def __init__(self):
        self._current_year = datetime.now().year

    def check_wrestler(self, wrestler) -> List[QualityIssue]:
        """Check a single wrestler for quality issues."""
        issues = []

        # Check if this is actually a stable/faction misclassified as a wrestler
        stable_issue = self._check_if_stable(wrestler)
        if stable_issue:
            issues.append(stable_issue)

        # Check name quality
        name_issues = self._check_name_quality(
            wrestler.name, 'wrestler', wrestler.id, wrestler.name
        )
        issues.extend(name_issues)

        # Check for comma-separated names (common parsing error)
        if ',' in wrestler.name and len(wrestler.name.split(',')) > 1:
            parts = [p.strip() for p in wrestler.name.split(',')]
            if all(len(p.split()) >= 2 or p[0].isupper() for p in parts if p):
                issues.append(QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=wrestler.name,
                    issue_type='error',
                    issue_code='INVALID_MULTI_NAME',
                    description=f'Name appears to contain multiple wrestlers: {wrestler.name}',
                    field='name',
                    current_value=wrestler.name,
                    auto_fixable=False,
                ))

        # Check year fields
        if wrestler.debut_year:
            if not self._is_valid_year(wrestler.debut_year):
                issues.append(QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=wrestler.name,
                    issue_type='error',
                    issue_code='INVALID_DEBUT_YEAR',
                    description=f'Invalid debut year: {wrestler.debut_year}',
                    field='debut_year',
                    current_value=wrestler.debut_year,
                    auto_fixable=False,
                ))

        if wrestler.retirement_year:
            if not self._is_valid_year(wrestler.retirement_year):
                issues.append(QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=wrestler.name,
                    issue_type='error',
                    issue_code='INVALID_RETIREMENT_YEAR',
                    description=f'Invalid retirement year: {wrestler.retirement_year}',
                    field='retirement_year',
                    current_value=wrestler.retirement_year,
                    auto_fixable=False,
                ))

            # Check retirement before debut
            if wrestler.debut_year and wrestler.retirement_year < wrestler.debut_year:
                issues.append(QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=wrestler.name,
                    issue_type='error',
                    issue_code='INVALID_YEAR_SEQUENCE',
                    description=f'Retirement year ({wrestler.retirement_year}) before debut ({wrestler.debut_year})',
                    field='retirement_year',
                    current_value=wrestler.retirement_year,
                    auto_fixable=False,
                ))

        # Check for very short about text (likely incomplete)
        if wrestler.about and 0 < len(wrestler.about) < 20:
            issues.append(QualityIssue(
                entity_type='wrestler',
                entity_id=wrestler.id,
                entity_name=wrestler.name,
                issue_type='warning',
                issue_code='INCOMPLETE_ABOUT',
                description=f'About text is very short ({len(wrestler.about)} chars)',
                field='about',
                current_value=wrestler.about[:50],
                auto_fixable=False,
            ))

        # Check for orphan wrestlers (no matches, no promotions)
        if hasattr(wrestler, 'matches'):
            match_count = wrestler.matches.count()
            if match_count == 0:
                issues.append(QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=wrestler.name,
                    issue_type='warning',
                    issue_code='ORPHAN_NO_MATCHES',
                    description='Wrestler has no associated matches',
                    auto_fixable=False,
                ))

        return issues

    def check_event(self, event) -> List[QualityIssue]:
        """Check a single event for quality issues."""
        issues = []

        # Check name quality
        name_issues = self._check_name_quality(
            event.name, 'event', event.id, event.name
        )
        issues.extend(name_issues)

        # Check date
        if event.date:
            if event.date.year < self.MIN_YEAR or event.date.year > self._current_year + self.MAX_YEAR_OFFSET:
                issues.append(QualityIssue(
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    issue_type='error',
                    issue_code='INVALID_DATE',
                    description=f'Event date year {event.date.year} is outside valid range',
                    field='date',
                    current_value=str(event.date),
                    auto_fixable=False,
                ))

        # Check for missing promotion
        if not event.promotion:
            issues.append(QualityIssue(
                entity_type='event',
                entity_id=event.id,
                entity_name=event.name,
                issue_type='warning',
                issue_code='MISSING_PROMOTION',
                description='Event has no associated promotion',
                auto_fixable=False,
            ))

        # Check for orphan events (no matches)
        if hasattr(event, 'matches'):
            match_count = event.matches.count()
            if match_count == 0:
                issues.append(QualityIssue(
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    issue_type='warning',
                    issue_code='ORPHAN_NO_MATCHES',
                    description='Event has no associated matches',
                    auto_fixable=False,
                ))

        # Check for unreasonable attendance
        if event.attendance:
            if event.attendance < 0:
                issues.append(QualityIssue(
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    issue_type='error',
                    issue_code='INVALID_ATTENDANCE',
                    description=f'Negative attendance: {event.attendance}',
                    field='attendance',
                    current_value=event.attendance,
                    suggested_value=None,
                    auto_fixable=True,
                ))
            elif event.attendance > 200000:  # Largest wrestling events rarely exceed 100k
                issues.append(QualityIssue(
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    issue_type='warning',
                    issue_code='SUSPICIOUS_ATTENDANCE',
                    description=f'Unusually high attendance: {event.attendance}',
                    field='attendance',
                    current_value=event.attendance,
                    auto_fixable=False,
                ))

        return issues

    def check_promotion(self, promotion) -> List[QualityIssue]:
        """Check a single promotion for quality issues."""
        issues = []

        # Check name quality
        name_issues = self._check_name_quality(
            promotion.name, 'promotion', promotion.id, promotion.name
        )
        issues.extend(name_issues)

        # Check year fields
        if promotion.founded_year:
            if not self._is_valid_year(promotion.founded_year):
                issues.append(QualityIssue(
                    entity_type='promotion',
                    entity_id=promotion.id,
                    entity_name=promotion.name,
                    issue_type='error',
                    issue_code='INVALID_FOUNDED_YEAR',
                    description=f'Invalid founded year: {promotion.founded_year}',
                    field='founded_year',
                    current_value=promotion.founded_year,
                    auto_fixable=False,
                ))

        if promotion.closed_year:
            if not self._is_valid_year(promotion.closed_year):
                issues.append(QualityIssue(
                    entity_type='promotion',
                    entity_id=promotion.id,
                    entity_name=promotion.name,
                    issue_type='error',
                    issue_code='INVALID_CLOSED_YEAR',
                    description=f'Invalid closed year: {promotion.closed_year}',
                    field='closed_year',
                    current_value=promotion.closed_year,
                    auto_fixable=False,
                ))

            # Check closed before founded
            if promotion.founded_year and promotion.closed_year < promotion.founded_year:
                issues.append(QualityIssue(
                    entity_type='promotion',
                    entity_id=promotion.id,
                    entity_name=promotion.name,
                    issue_type='error',
                    issue_code='INVALID_YEAR_SEQUENCE',
                    description=f'Closed year ({promotion.closed_year}) before founded ({promotion.founded_year})',
                    field='closed_year',
                    current_value=promotion.closed_year,
                    auto_fixable=False,
                ))

        # Check website URL format
        if promotion.website:
            if not promotion.website.startswith(('http://', 'https://')):
                issues.append(QualityIssue(
                    entity_type='promotion',
                    entity_id=promotion.id,
                    entity_name=promotion.name,
                    issue_type='warning',
                    issue_code='INVALID_URL_FORMAT',
                    description='Website URL missing protocol',
                    field='website',
                    current_value=promotion.website,
                    suggested_value=f'https://{promotion.website}',
                    auto_fixable=True,
                ))

        return issues

    def check_venue(self, venue) -> List[QualityIssue]:
        """Check a single venue for quality issues."""
        issues = []

        # Check name quality
        name_issues = self._check_name_quality(
            venue.name, 'venue', venue.id, venue.name
        )
        issues.extend(name_issues)

        # Check capacity
        if venue.capacity:
            if venue.capacity < 0:
                issues.append(QualityIssue(
                    entity_type='venue',
                    entity_id=venue.id,
                    entity_name=venue.name,
                    issue_type='error',
                    issue_code='INVALID_CAPACITY',
                    description=f'Negative capacity: {venue.capacity}',
                    field='capacity',
                    current_value=venue.capacity,
                    suggested_value=None,
                    auto_fixable=True,
                ))
            elif venue.capacity > 500000:  # No venue exceeds this
                issues.append(QualityIssue(
                    entity_type='venue',
                    entity_id=venue.id,
                    entity_name=venue.name,
                    issue_type='warning',
                    issue_code='SUSPICIOUS_CAPACITY',
                    description=f'Unusually high capacity: {venue.capacity}',
                    field='capacity',
                    current_value=venue.capacity,
                    auto_fixable=False,
                ))

        # Check for orphan venues (no events)
        if hasattr(venue, 'events'):
            event_count = venue.events.count()
            if event_count == 0:
                issues.append(QualityIssue(
                    entity_type='venue',
                    entity_id=venue.id,
                    entity_name=venue.name,
                    issue_type='warning',
                    issue_code='ORPHAN_NO_EVENTS',
                    description='Venue has no associated events',
                    auto_fixable=False,
                ))

        return issues

    def check_title(self, title) -> List[QualityIssue]:
        """Check a single title for quality issues."""
        issues = []

        # Check name quality
        name_issues = self._check_name_quality(
            title.name, 'title', title.id, title.name
        )
        issues.extend(name_issues)

        # Check for missing promotion
        if not title.promotion:
            issues.append(QualityIssue(
                entity_type='title',
                entity_id=title.id,
                entity_name=title.name,
                issue_type='error',
                issue_code='MISSING_PROMOTION',
                description='Title has no associated promotion',
                auto_fixable=False,
            ))

        # Check year fields
        if title.debut_year:
            if not self._is_valid_year(title.debut_year):
                issues.append(QualityIssue(
                    entity_type='title',
                    entity_id=title.id,
                    entity_name=title.name,
                    issue_type='error',
                    issue_code='INVALID_DEBUT_YEAR',
                    description=f'Invalid debut year: {title.debut_year}',
                    field='debut_year',
                    current_value=title.debut_year,
                    auto_fixable=False,
                ))

        return issues

    def check_match(self, match) -> List[QualityIssue]:
        """
        Check a single match for quality issues.

        Issue codes:
        - DECEASED_IN_MATCH: Deceased wrestler appears after death date
        - ERA_MISMATCH: Wrestlers from incompatible time periods
        - UNLINKED_WRESTLERS: Match has text but no wrestler links
        """
        issues = []

        # Get event date for temporal checks
        event_date = match.event.date if match.event else None

        # Check for unlinked wrestlers (match_text exists but no M2M links)
        if match.match_text and hasattr(match, 'wrestlers'):
            if match.wrestlers.count() == 0:
                issues.append(QualityIssue(
                    entity_type='match',
                    entity_id=match.id,
                    entity_name=match.match_text[:50] + '...' if len(match.match_text) > 50 else match.match_text,
                    issue_type='warning',
                    issue_code='UNLINKED_WRESTLERS',
                    description='Match has text but no linked wrestler objects',
                    field='wrestlers',
                    current_value=match.match_text[:100],
                    auto_fixable=False,
                ))

        # Check wrestlers in the match
        wrestlers = list(match.wrestlers.all()) if hasattr(match, 'wrestlers') else []

        if event_date and wrestlers:
            # Check for deceased wrestlers in matches after their death
            issues.extend(self._check_deceased_in_match(match, wrestlers, event_date))

            # Check for retired wrestlers in matches after retirement
            issues.extend(self._check_retired_in_match(match, wrestlers, event_date))

            # Check for era mismatches (e.g., 1960s wrestler vs 2020s wrestler)
            issues.extend(self._check_era_consistency(match, wrestlers, event_date))

        # Check for tag teams stored as single wrestlers
        issues.extend(self._check_tag_team_as_wrestler(match, wrestlers))

        return issues

    def _check_deceased_in_match(
        self,
        match,
        wrestlers: List,
        event_date: date
    ) -> List[QualityIssue]:
        """Check if any deceased wrestlers appear in matches after their death."""
        issues = []

        for wrestler in wrestlers:
            if wrestler.death_date and event_date > wrestler.death_date:
                issues.append(QualityIssue(
                    entity_type='match',
                    entity_id=match.id,
                    entity_name=match.match_text[:50] if match.match_text else f'Match #{match.id}',
                    issue_type='error',
                    issue_code='DECEASED_IN_MATCH',
                    description=f'{wrestler.name} died on {wrestler.death_date} but appears in match on {event_date}',
                    field='wrestlers',
                    current_value=wrestler.name,
                    auto_fixable=True,  # Can auto-delete the match
                ))

        return issues

    def _check_retired_in_match(
        self,
        match,
        wrestlers: List,
        event_date: date
    ) -> List[QualityIssue]:
        """Check if any retired wrestlers appear in matches after retirement."""
        issues = []

        for wrestler in wrestlers:
            # Check retirement year - if event year > retirement year, flag it
            # (allowing same year for data imprecision, e.g., retired mid-year)
            if wrestler.retirement_year and event_date.year > wrestler.retirement_year:
                issues.append(QualityIssue(
                    entity_type='match',
                    entity_id=match.id,
                    entity_name=match.match_text[:50] if match.match_text else f'Match #{match.id}',
                    issue_type='error',
                    issue_code='RETIRED_IN_MATCH',
                    description=f'{wrestler.name} retired in {wrestler.retirement_year} but appears in match on {event_date}',
                    field='wrestlers',
                    current_value=wrestler.name,
                    auto_fixable=True,  # Can auto-delete the match
                ))

        return issues

    def _check_tag_team_as_wrestler(
        self,
        match,
        wrestlers: List
    ) -> List[QualityIssue]:
        """Check if any wrestlers are actually tag teams stored incorrectly."""
        issues = []

        for wrestler in wrestlers:
            name_lower = wrestler.name.lower().strip()
            if name_lower in self.KNOWN_TAG_TEAMS:
                members = self.KNOWN_TAG_TEAMS[name_lower]
                issues.append(QualityIssue(
                    entity_type='match',
                    entity_id=match.id,
                    entity_name=match.match_text[:50] if match.match_text else f'Match #{match.id}',
                    issue_type='error',
                    issue_code='TAG_TEAM_AS_WRESTLER',
                    description=f'"{wrestler.name}" is a tag team, should be individual wrestlers: {", ".join(members)}',
                    field='wrestlers',
                    current_value=wrestler.name,
                    suggested_value=members,
                    auto_fixable=True,  # Can auto-fix by replacing with individual wrestlers
                ))

        return issues

    def _check_era_consistency(
        self,
        match,
        wrestlers: List,
        event_date: date
    ) -> List[QualityIssue]:
        """Check for wrestlers from incompatible eras in the same match."""
        issues = []

        # Get debut and retirement years for all wrestlers
        debut_years = [w.debut_year for w in wrestlers if w.debut_year]
        retirement_years = [w.retirement_year for w in wrestlers if w.retirement_year]

        if len(debut_years) >= 2:
            # Check for large gap between earliest and latest debut (>25 years is suspicious)
            min_debut = min(debut_years)
            max_debut = max(debut_years)

            if max_debut - min_debut > 25:
                issues.append(QualityIssue(
                    entity_type='match',
                    entity_id=match.id,
                    entity_name=match.match_text[:50] if match.match_text else f'Match #{match.id}',
                    issue_type='warning',
                    issue_code='ERA_MISMATCH',
                    description=f'Large era gap: debut years range from {min_debut} to {max_debut} ({max_debut - min_debut} years)',
                    field='wrestlers',
                    auto_fixable=False,
                ))

        # Check if a wrestler retired before another debuted (impossible to have faced)
        for i, w1 in enumerate(wrestlers):
            if not w1.retirement_year:
                continue
            for w2 in wrestlers[i + 1:]:
                if not w2.debut_year:
                    continue
                # If w1 retired before w2 debuted, they couldn't have wrestled
                if w1.retirement_year < w2.debut_year - 1:  # Allow 1 year overlap for data imprecision
                    issues.append(QualityIssue(
                        entity_type='match',
                        entity_id=match.id,
                        entity_name=match.match_text[:50] if match.match_text else f'Match #{match.id}',
                        issue_type='error',
                        issue_code='ERA_MISMATCH',
                        description=f'{w1.name} retired in {w1.retirement_year} but {w2.name} debuted in {w2.debut_year}',
                        field='wrestlers',
                        auto_fixable=False,
                    ))

        return issues

    def check_event_synthetic(self, event) -> List[QualityIssue]:
        """
        Check if an event appears to be synthetic/AI-generated.

        This is separate from check_event() because it requires checking
        match data and deceased wrestlers.

        Issue codes:
        - SYNTHETIC_EVENT: Event appears fabricated (deceased wrestlers in future)
        - FUTURE_EVENT: Event date is unreasonably far in the future
        - IMPOSSIBLE_CARD: Card contains impossible wrestler combinations
        """
        issues = []

        if not event.date:
            return issues

        today = date.today()
        event_date = event.date

        # Check for events more than 30 days in the future
        if event_date > today + timedelta(days=30):
            issues.append(QualityIssue(
                entity_type='event',
                entity_id=event.id,
                entity_name=event.name,
                issue_type='warning',
                issue_code='FUTURE_EVENT',
                description=f'Event date {event_date} is more than 30 days in the future',
                field='date',
                current_value=str(event_date),
                auto_fixable=False,
            ))

        # Check matches for deceased wrestlers and era issues
        matches = list(event.matches.all()) if hasattr(event, 'matches') else []
        deceased_violations = []
        era_violations = []

        for match in matches:
            match_issues = self.check_match(match)
            for issue in match_issues:
                if issue.issue_code == 'DECEASED_IN_MATCH':
                    deceased_violations.append(issue.description)
                elif issue.issue_code == 'ERA_MISMATCH' and issue.issue_type == 'error':
                    era_violations.append(issue.description)

        # If we have deceased wrestlers in a future event, it's synthetic
        if event_date > today and deceased_violations:
            issues.append(QualityIssue(
                entity_type='event',
                entity_id=event.id,
                entity_name=event.name,
                issue_type='error',
                issue_code='SYNTHETIC_EVENT',
                description=f'Future event contains deceased wrestlers: {"; ".join(deceased_violations[:3])}',
                field='matches',
                auto_fixable=False,
            ))

        # If we have impossible era combinations, flag it
        if era_violations:
            issues.append(QualityIssue(
                entity_type='event',
                entity_id=event.id,
                entity_name=event.name,
                issue_type='error',
                issue_code='IMPOSSIBLE_CARD',
                description=f'Event has impossible wrestler combinations: {"; ".join(era_violations[:3])}',
                field='matches',
                auto_fixable=False,
            ))

        return issues

    def find_synthetic_events(self, limit: int = 1000) -> List[QualityIssue]:
        """
        Scan events to find synthetic/impossible data.

        Returns list of events that appear to be synthetic/fabricated.
        """
        from ..models import Event

        issues = []
        today = date.today()

        # Focus on future events and recent events (where synthetic data is most likely)
        events = Event.objects.filter(
            date__gt=today - timedelta(days=30)
        ).prefetch_related('matches', 'matches__wrestlers')[:limit]

        for event in events:
            event_issues = self.check_event_synthetic(event)
            synthetic_issues = [i for i in event_issues if i.issue_code in ('SYNTHETIC_EVENT', 'IMPOSSIBLE_CARD')]
            issues.extend(synthetic_issues)

        return issues

    def _check_name_quality(
        self,
        name: str,
        entity_type: str,
        entity_id: int,
        entity_name: str
    ) -> List[QualityIssue]:
        """Check name field for quality issues."""
        issues = []

        if not name:
            issues.append(QualityIssue(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name or f'#{entity_id}',
                issue_type='error',
                issue_code='MISSING_NAME',
                description='Name is empty or missing',
                field='name',
                auto_fixable=False,
            ))
            return issues

        # Check for suspicious patterns
        for pattern in self.SUSPICIOUS_NAME_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                # Determine if it's the comma pattern (multiple names)
                if pattern == r',\s*\w+\s+\w+':
                    issues.append(QualityIssue(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        issue_type='error',
                        issue_code='SUSPICIOUS_NAME_MULTI',
                        description=f'Name appears to contain multiple entries: {name}',
                        field='name',
                        current_value=name,
                        auto_fixable=False,
                    ))
                elif pattern == r'vs\.?\s':
                    issues.append(QualityIssue(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        issue_type='error',
                        issue_code='SUSPICIOUS_NAME_VS',
                        description=f'Name contains "vs" suggesting match text: {name}',
                        field='name',
                        current_value=name,
                        auto_fixable=False,
                    ))
                else:
                    issues.append(QualityIssue(
                        entity_type=entity_type,
                        entity_id=entity_id,
                        entity_name=entity_name,
                        issue_type='warning',
                        issue_code='SUSPICIOUS_NAME_FORMAT',
                        description=f'Name has suspicious format: {name}',
                        field='name',
                        current_value=name,
                        auto_fixable=False,
                    ))
                break

        # Check for invalid wrestler names
        if entity_type == 'wrestler':
            name_lower = name.lower().strip()
            if name_lower in self.INVALID_WRESTLER_NAMES:
                issues.append(QualityIssue(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    entity_name=entity_name,
                    issue_type='error',
                    issue_code='INVALID_PLACEHOLDER_NAME',
                    description=f'Name is a placeholder or invalid: {name}',
                    field='name',
                    current_value=name,
                    auto_fixable=False,
                ))

        # Check for leading/trailing whitespace (auto-fixable)
        if name != name.strip():
            issues.append(QualityIssue(
                entity_type=entity_type,
                entity_id=entity_id,
                entity_name=entity_name,
                issue_type='warning',
                issue_code='NAME_WHITESPACE',
                description='Name has leading/trailing whitespace',
                field='name',
                current_value=name,
                suggested_value=name.strip(),
                auto_fixable=True,
            ))

        return issues

    def _is_valid_year(self, year: int) -> bool:
        """Check if a year is within valid range."""
        return self.MIN_YEAR <= year <= self._current_year + self.MAX_YEAR_OFFSET

    def _check_if_stable(self, wrestler) -> Optional[QualityIssue]:
        """Check if a wrestler entry is actually a stable/faction."""
        name = wrestler.name
        name_lower = name.lower().strip()

        # Check for Wikipedia disambiguation patterns
        for pattern in self.STABLE_INDICATORS:
            if re.search(pattern, name, re.IGNORECASE):
                return QualityIssue(
                    entity_type='wrestler',
                    entity_id=wrestler.id,
                    entity_name=name,
                    issue_type='error',
                    issue_code='MISCLASSIFIED_STABLE',
                    description=f'Entry appears to be a stable/faction, not a wrestler: {name}',
                    field='name',
                    current_value=name,
                    auto_fixable=False,
                )

        # Check against known stables list
        # Remove common prefixes/suffixes for matching
        normalized = re.sub(r'\s*\([^)]*\)\s*$', '', name_lower).strip()
        if normalized in self.KNOWN_STABLES:
            return QualityIssue(
                entity_type='wrestler',
                entity_id=wrestler.id,
                entity_name=name,
                issue_type='error',
                issue_code='MISCLASSIFIED_STABLE',
                description=f'Entry is a known stable/faction, not a wrestler: {name}',
                field='name',
                current_value=name,
                auto_fixable=False,
            )

        return None

    def run_quality_check(
        self,
        entity_types: List[str] = None,
        limit: int = 1000
    ) -> QualityReport:
        """
        Run quality checks across specified entity types.

        Args:
            entity_types: List of types to check (default: all)
            limit: Maximum entities to check per type

        Returns:
            QualityReport with all found issues
        """
        from ..models import Wrestler, Event, Promotion, Venue, Title

        if entity_types is None:
            entity_types = ['wrestler', 'event', 'promotion', 'venue', 'title']

        report = QualityReport()
        checked_entities: Set[Tuple[str, int]] = set()

        model_map = {
            'wrestler': (Wrestler, self.check_wrestler),
            'event': (Event, self.check_event),
            'promotion': (Promotion, self.check_promotion),
            'venue': (Venue, self.check_venue),
            'title': (Title, self.check_title),
        }

        for entity_type in entity_types:
            if entity_type not in model_map:
                continue

            model_class, check_func = model_map[entity_type]

            try:
                entities = model_class.objects.all()[:limit]

                for entity in entities:
                    report.total_checked += 1
                    entity_key = (entity_type, entity.id)

                    if entity_key in checked_entities:
                        continue
                    checked_entities.add(entity_key)

                    try:
                        issues = check_func(entity)
                        if issues:
                            report.entities_with_issues += 1
                            for issue in issues:
                                report.add_issue(issue)
                    except Exception as e:
                        logger.error(f"Error checking {entity_type} {entity.id}: {e}")

            except Exception as e:
                logger.error(f"Error running quality check for {entity_type}: {e}")

        logger.info(
            f"Quality check complete: {report.total_checked} checked, "
            f"{report.entities_with_issues} with issues, "
            f"{report.errors} errors, {report.warnings} warnings"
        )

        return report


class DataCleaner:
    """
    Cleans and fixes data quality issues.

    Can automatically fix some issues and flag others for manual review.
    """

    def __init__(self):
        self.checker = DataQualityChecker()

    def fix_auto_fixable_issues(
        self,
        issues: List[QualityIssue],
        dry_run: bool = True
    ) -> Dict[str, int]:
        """
        Fix issues that can be automatically corrected.

        Args:
            issues: List of QualityIssue objects
            dry_run: If True, don't actually make changes

        Returns:
            Dict with counts of fixed issues by type
        """
        from ..models import Wrestler, Event, Promotion, Venue, Title
        from owdb_django.wrestlebot.models import WrestleBotActivity

        model_map = {
            'wrestler': Wrestler,
            'event': Event,
            'promotion': Promotion,
            'venue': Venue,
            'title': Title,
        }

        fixed_counts = {}

        for issue in issues:
            if not issue.auto_fixable:
                continue

            model_class = model_map.get(issue.entity_type)
            if not model_class:
                continue

            try:
                entity = model_class.objects.get(id=issue.entity_id)
                fixed = False

                if issue.issue_code == 'NAME_WHITESPACE' and issue.suggested_value:
                    if not dry_run:
                        entity.name = issue.suggested_value
                        entity.save(update_fields=['name', 'updated_at'])
                    fixed = True

                elif issue.issue_code == 'INVALID_ATTENDANCE':
                    if not dry_run:
                        entity.attendance = None
                        entity.save(update_fields=['attendance', 'updated_at'])
                    fixed = True

                elif issue.issue_code == 'INVALID_CAPACITY':
                    if not dry_run:
                        entity.capacity = None
                        entity.save(update_fields=['capacity', 'updated_at'])
                    fixed = True

                elif issue.issue_code == 'INVALID_URL_FORMAT' and issue.suggested_value:
                    if not dry_run:
                        entity.website = issue.suggested_value
                        entity.save(update_fields=['website', 'updated_at'])
                    fixed = True

                if fixed:
                    fixed_counts[issue.issue_code] = fixed_counts.get(issue.issue_code, 0) + 1

                    if not dry_run:
                        WrestleBotActivity.log_activity(
                            action_type='verify',
                            entity_type=issue.entity_type,
                            entity_id=issue.entity_id,
                            entity_name=issue.entity_name,
                            source='quality_cleanup',
                            details={
                                'issue_code': issue.issue_code,
                                'field': issue.field,
                                'old_value': str(issue.current_value),
                                'new_value': str(issue.suggested_value),
                            },
                        )

            except Exception as e:
                logger.error(f"Error fixing {issue.entity_type} {issue.entity_id}: {e}")

        return fixed_counts

    def find_and_flag_duplicates(
        self,
        entity_type: str,
        limit: int = 100
    ) -> List[Tuple[Any, Any, float]]:
        """
        Find potential duplicate entries.

        Returns list of (entity1, entity2, similarity_score) tuples.
        """
        from ..models import Wrestler, Promotion
        from ..scrapers.coordinator import DataValidator

        duplicates = []

        if entity_type == 'wrestler':
            wrestlers = list(Wrestler.objects.all()[:limit])

            for i, w1 in enumerate(wrestlers):
                for w2 in wrestlers[i + 1:]:
                    similarity = DataValidator.similarity(w1.name, w2.name)
                    if similarity >= 0.85:
                        duplicates.append((w1, w2, similarity))

                    # Also check aliases
                    if w1.aliases:
                        for alias in w1.get_aliases_list():
                            alias_sim = DataValidator.similarity(alias, w2.name)
                            if alias_sim >= 0.90:
                                duplicates.append((w1, w2, alias_sim))
                                break

        elif entity_type == 'promotion':
            promotions = list(Promotion.objects.all()[:limit])

            for i, p1 in enumerate(promotions):
                for p2 in promotions[i + 1:]:
                    similarity = DataValidator.similarity(p1.name, p2.name)
                    if similarity >= 0.85:
                        duplicates.append((p1, p2, similarity))

        return duplicates

    def remove_invalid_entries(
        self,
        entity_type: str,
        dry_run: bool = True
    ) -> int:
        """
        Remove entries that are clearly invalid (placeholder names, etc.).

        Only removes entries with no relationships to preserve data integrity.

        Args:
            entity_type: Type of entity to clean
            dry_run: If True, don't actually delete

        Returns:
            Count of removed entries
        """
        from ..models import Wrestler, Event, Promotion, Venue
        from owdb_django.wrestlebot.models import WrestleBotActivity

        removed_count = 0

        if entity_type == 'wrestler':
            # Find wrestlers with invalid names and no matches
            invalid_names = list(DataQualityChecker.INVALID_WRESTLER_NAMES)
            wrestlers = Wrestler.objects.annotate(
                match_count=Count('matches')
            ).filter(
                Q(name__in=invalid_names) | Q(name__iregex=r'^(test|unknown|tbd)\d*$'),
                match_count=0
            )

            for wrestler in wrestlers:
                logger.info(f"{'Would remove' if dry_run else 'Removing'} invalid wrestler: {wrestler.name}")
                if not dry_run:
                    WrestleBotActivity.log_activity(
                        action_type='verify',
                        entity_type='wrestler',
                        entity_id=wrestler.id,
                        entity_name=wrestler.name,
                        source='quality_cleanup',
                        details={'action': 'removed', 'reason': 'invalid_name'},
                    )
                    wrestler.delete()
                removed_count += 1

        elif entity_type == 'event':
            # Find orphan events with suspicious names
            events = Event.objects.annotate(
                match_count=Count('matches')
            ).filter(
                Q(name__iregex=r'^(test|unknown|tbd)\d*$'),
                match_count=0
            )

            for event in events:
                logger.info(f"{'Would remove' if dry_run else 'Removing'} invalid event: {event.name}")
                if not dry_run:
                    WrestleBotActivity.log_activity(
                        action_type='verify',
                        entity_type='event',
                        entity_id=event.id,
                        entity_name=event.name,
                        source='quality_cleanup',
                        details={'action': 'removed', 'reason': 'invalid_name'},
                    )
                    event.delete()
                removed_count += 1

        return removed_count

    def split_multi_name_entries(
        self,
        entity_type: str,
        dry_run: bool = True
    ) -> int:
        """
        Split entries that contain multiple names (e.g., "Triple H, Ultimate Warrior").

        Args:
            entity_type: Type of entity to process
            dry_run: If True, don't actually make changes

        Returns:
            Count of entries processed
        """
        from ..models import Wrestler
        from owdb_django.wrestlebot.models import WrestleBotActivity

        processed_count = 0

        if entity_type == 'wrestler':
            # Find wrestlers with comma-separated names
            wrestlers = Wrestler.objects.filter(name__contains=',')

            for wrestler in wrestlers:
                parts = [p.strip() for p in wrestler.name.split(',')]
                # Check if parts look like separate names
                valid_parts = [p for p in parts if len(p) >= 3 and p[0].isupper()]

                if len(valid_parts) >= 2:
                    logger.info(f"{'Would split' if dry_run else 'Splitting'}: {wrestler.name} -> {valid_parts}")

                    if not dry_run:
                        # Update first entry with first name
                        old_name = wrestler.name
                        wrestler.name = valid_parts[0]
                        wrestler.save()

                        WrestleBotActivity.log_activity(
                            action_type='verify',
                            entity_type='wrestler',
                            entity_id=wrestler.id,
                            entity_name=wrestler.name,
                            source='quality_cleanup',
                            details={
                                'action': 'split',
                                'original_name': old_name,
                                'kept_name': valid_parts[0],
                            },
                        )

                        # Note: We don't auto-create the other wrestlers
                        # They should be discovered properly through normal discovery
                        # Just log what was removed
                        for removed_name in valid_parts[1:]:
                            WrestleBotActivity.log_activity(
                                action_type='verify',
                                entity_type='wrestler',
                                entity_id=0,  # No entity ID
                                entity_name=removed_name,
                                source='quality_cleanup',
                                details={
                                    'action': 'split_removed',
                                    'original_name': old_name,
                                    'note': 'Name was part of multi-name entry, should be discovered separately',
                                },
                            )

                    processed_count += 1

        return processed_count

    def fix_misclassified_stables(
        self,
        dry_run: bool = True
    ) -> int:
        """
        Find and fix wrestlers that are actually stables/factions.

        Either migrates them to the Stable model or deletes them if a stable
        with that name already exists.

        Args:
            dry_run: If True, don't actually make changes

        Returns:
            Count of entries fixed
        """
        from ..models import Wrestler, Stable
        from owdb_django.wrestlebot.models import WrestleBotActivity

        fixed_count = 0

        # Check all wrestlers for stable patterns
        for wrestler in Wrestler.objects.all():
            issue = self.checker._check_if_stable(wrestler)
            if not issue:
                continue

            # Clean the name (remove Wikipedia disambiguation)
            clean_name = re.sub(r'\s*\([^)]*\)\s*$', '', wrestler.name).strip()

            logger.info(f"{'Would fix' if dry_run else 'Fixing'} misclassified stable: {wrestler.name}")

            if not dry_run:
                # Check if stable already exists
                existing_stable = Stable.objects.filter(name__iexact=clean_name).first()

                if existing_stable:
                    # Stable exists, just delete the wrestler entry
                    WrestleBotActivity.log_activity(
                        action_type='verify',
                        entity_type='wrestler',
                        entity_id=wrestler.id,
                        entity_name=wrestler.name,
                        source='quality_cleanup',
                        details={
                            'action': 'deleted_duplicate_stable',
                            'existing_stable_id': existing_stable.id,
                            'reason': 'misclassified_stable',
                        },
                    )
                    wrestler.delete()
                else:
                    # Create new stable from wrestler data
                    stable = Stable.objects.create(
                        name=clean_name,
                        about=wrestler.about or '',
                        image=wrestler.image if hasattr(wrestler, 'image') else None,
                    )

                    WrestleBotActivity.log_activity(
                        action_type='verify',
                        entity_type='wrestler',
                        entity_id=wrestler.id,
                        entity_name=wrestler.name,
                        source='quality_cleanup',
                        details={
                            'action': 'migrated_to_stable',
                            'new_stable_id': stable.id,
                            'reason': 'misclassified_stable',
                        },
                    )

                    # Delete the wrestler entry
                    wrestler.delete()

            fixed_count += 1

        return fixed_count

    def run_cleanup_cycle(
        self,
        entity_types: List[str] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Run a full cleanup cycle.

        Args:
            entity_types: Types to clean (default: all)
            dry_run: If True, don't make changes

        Returns:
            Summary of cleanup actions
        """
        if entity_types is None:
            entity_types = ['wrestler', 'event', 'promotion', 'venue']

        results = {
            'dry_run': dry_run,
            'quality_issues': 0,
            'auto_fixed': 0,
            'invalid_removed': 0,
            'multi_name_split': 0,
            'stables_fixed': 0,
            'duplicates_found': 0,
        }

        # Run quality check
        report = self.checker.run_quality_check(entity_types=entity_types)
        results['quality_issues'] = len(report.issues)

        # Fix auto-fixable issues
        if report.auto_fixable > 0:
            auto_fixable = [i for i in report.issues if i.auto_fixable]
            fixed = self.fix_auto_fixable_issues(auto_fixable, dry_run=dry_run)
            results['auto_fixed'] = sum(fixed.values())
            results['auto_fixed_by_type'] = fixed

        # Remove invalid entries
        for entity_type in entity_types:
            removed = self.remove_invalid_entries(entity_type, dry_run=dry_run)
            results['invalid_removed'] += removed

        # Split multi-name entries (wrestlers only)
        if 'wrestler' in entity_types:
            split = self.split_multi_name_entries('wrestler', dry_run=dry_run)
            results['multi_name_split'] = split

        # Fix misclassified stables (wrestlers that are actually factions)
        if 'wrestler' in entity_types:
            stables_fixed = self.fix_misclassified_stables(dry_run=dry_run)
            results['stables_fixed'] = stables_fixed

        # Find duplicates (don't auto-fix, just report)
        for entity_type in ['wrestler', 'promotion']:
            if entity_type in entity_types:
                duplicates = self.find_and_flag_duplicates(entity_type)
                results['duplicates_found'] += len(duplicates)
                if duplicates:
                    results[f'{entity_type}_duplicates'] = [
                        {
                            'id1': d[0].id,
                            'name1': d[0].name,
                            'id2': d[1].id,
                            'name2': d[1].name,
                            'similarity': round(d[2], 3),
                        }
                        for d in duplicates[:10]  # Limit to top 10
                    ]

        logger.info(f"Cleanup cycle complete: {results}")
        return results

    def find_and_delete_synthetic_events(
        self,
        dry_run: bool = True,
        include_future_only: bool = False
    ) -> Dict[str, Any]:
        """
        Find and delete synthetic/impossible events.

        This method identifies events that are clearly fabricated:
        - Events with deceased wrestlers appearing after their death date
        - Events with impossible era combinations (wrestler retired before another debuted)

        Args:
            dry_run: If True, don't actually delete
            include_future_only: If True, only check future events (safer). Default False to catch all.

        Returns:
            Summary of deleted events
        """
        from ..models import Event, Match, Wrestler
        from owdb_django.wrestlebot.models import WrestleBotActivity

        results = {
            'dry_run': dry_run,
            'events_checked': 0,
            'synthetic_found': 0,
            'events_deleted': 0,
            'matches_deleted': 0,
            'deleted_events': [],
        }

        today = date.today()

        # Find events that have matches with deceased wrestlers
        # This is more efficient than checking all events
        deceased_wrestler_ids = list(
            Wrestler.objects.filter(death_date__isnull=False).values_list('id', flat=True)
        )

        if not deceased_wrestler_ids:
            logger.info("No deceased wrestlers in database, skipping synthetic check")
            return results

        # Find events where:
        # 1. Event has matches with wrestlers who are deceased
        # 2. Event date is after the wrestler's death date
        # We do this by checking events with any deceased wrestler, then filtering
        from django.db.models import F, Q

        # Get events that have matches with deceased wrestlers
        events_with_deceased = Event.objects.filter(
            matches__wrestlers__id__in=deceased_wrestler_ids
        ).distinct().prefetch_related('matches', 'matches__wrestlers')

        for event in events_with_deceased:
            results['events_checked'] += 1

            if not event.date:
                continue

            # Check each match for deceased wrestlers appearing after their death
            has_deceased_violation = False
            violations = []

            for match in event.matches.all():
                for wrestler in match.wrestlers.all():
                    if wrestler.death_date and event.date > wrestler.death_date:
                        has_deceased_violation = True
                        violations.append(
                            f'{wrestler.name} died {wrestler.death_date} but appears in {event.date} event'
                        )

            if not has_deceased_violation:
                continue

            # This event has a deceased wrestler appearing after their death
            synthetic_issues = [
                QualityIssue(
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    issue_type='error',
                    issue_code='SYNTHETIC_EVENT',
                    description=f'Deceased wrestler in match: {violations[0]}',
                    auto_fixable=False,
                )
            ]

            if not synthetic_issues:
                continue

            results['synthetic_found'] += 1

            event_info = {
                'id': event.id,
                'name': event.name,
                'date': str(event.date),
                'issues': [i.description for i in synthetic_issues],
                'match_count': event.matches.count(),
            }
            results['deleted_events'].append(event_info)

            if dry_run:
                logger.info(f"Would delete synthetic event: {event.name} ({event.date})")
            else:
                # Log the activity before deletion
                WrestleBotActivity.log_activity(
                    action_type='verify',
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    source='synthetic_cleanup',
                    details={
                        'action': 'deleted',
                        'reason': 'synthetic_event',
                        'issues': [i.description for i in synthetic_issues],
                        'date': str(event.date),
                        'match_count': event.matches.count(),
                    },
                )

                # Delete matches first (they have FK to event)
                match_count = event.matches.count()
                event.matches.all().delete()
                results['matches_deleted'] += match_count

                # Delete the event
                event.delete()
                results['events_deleted'] += 1

                logger.info(f"Deleted synthetic event: {event.name} ({event.date}) with {match_count} matches")

        logger.info(
            f"Synthetic event cleanup: checked {results['events_checked']}, "
            f"found {results['synthetic_found']}, deleted {results['events_deleted']}"
        )

        return results

    def detect_synthetic_by_name_pattern(
        self,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Find and delete events with suspicious name patterns in future dates.

        Patterns detected:
        - Generic TV episode names (WWE Raw #NNNN) in far future
        - Events with placeholder-like names in future

        Args:
            dry_run: If True, don't actually delete

        Returns:
            Summary of deleted events
        """
        from ..models import Event
        from owdb_django.wrestlebot.models import WrestleBotActivity
        import re

        results = {
            'dry_run': dry_run,
            'events_checked': 0,
            'suspicious_found': 0,
            'events_deleted': 0,
            'matches_deleted': 0,
            'deleted_events': [],
        }

        today = date.today()

        # Patterns for generic/suspicious event names
        suspicious_patterns = [
            r'^WWE Raw #\d{4,}$',  # WWE Raw #NNNN
            r'^AEW Dynamite #\d{3,}$',  # AEW Dynamite #NNN
            r'^WWE SmackDown #\d{4,}$',  # SmackDown #NNNN
            r'^NXT #\d{3,}$',  # NXT #NNN
            r'^Episode\s+\d+$',  # Episode N
            r'^Show\s+\d+$',  # Show N
        ]

        # Focus on events far in the future (more than 60 days)
        future_events = Event.objects.filter(
            date__gt=today + timedelta(days=60)
        ).prefetch_related('matches')

        for event in future_events:
            results['events_checked'] += 1

            # Check if name matches suspicious pattern
            is_suspicious = False
            for pattern in suspicious_patterns:
                if re.match(pattern, event.name, re.IGNORECASE):
                    is_suspicious = True
                    break

            if not is_suspicious:
                continue

            results['suspicious_found'] += 1

            event_info = {
                'id': event.id,
                'name': event.name,
                'date': str(event.date),
                'reason': 'suspicious_name_pattern_in_future',
                'match_count': event.matches.count(),
            }
            results['deleted_events'].append(event_info)

            if dry_run:
                logger.info(f"Would delete suspicious future event: {event.name} ({event.date})")
            else:
                WrestleBotActivity.log_activity(
                    action_type='verify',
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    source='synthetic_cleanup',
                    details={
                        'action': 'deleted',
                        'reason': 'suspicious_name_pattern',
                        'date': str(event.date),
                        'match_count': event.matches.count(),
                    },
                )

                match_count = event.matches.count()
                event.matches.all().delete()
                results['matches_deleted'] += match_count

                event.delete()
                results['events_deleted'] += 1

                logger.info(f"Deleted suspicious event: {event.name} ({event.date})")

        return results

    def find_and_fix_match_issues(
        self,
        dry_run: bool = True,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Find and fix match data quality issues.

        Handles:
        - DECEASED_IN_MATCH: Deletes matches with deceased wrestlers after death
        - RETIRED_IN_MATCH: Deletes matches with retired wrestlers after retirement
        - TAG_TEAM_AS_WRESTLER: Replaces tag team entry with individual wrestlers
        - ERA_MISMATCH: Deletes matches with impossible era combinations

        Args:
            dry_run: If True, don't actually make changes
            limit: Maximum matches to check

        Returns:
            Summary of fixes applied
        """
        from ..models import Match, Wrestler, Event
        from owdb_django.wrestlebot.models import WrestleBotActivity

        results = {
            'dry_run': dry_run,
            'matches_checked': 0,
            'deceased_deleted': 0,
            'retired_deleted': 0,
            'era_mismatch_deleted': 0,
            'tag_teams_fixed': 0,
            'events_cleaned': set(),  # Events that had matches deleted
        }

        today = date.today()

        # Focus on recent and future events (where synthetic data is likely)
        matches = Match.objects.filter(
            event__date__gte=today - timedelta(days=365)
        ).select_related('event').prefetch_related('wrestlers')[:limit]

        for match in matches:
            results['matches_checked'] += 1

            if not match.event or not match.event.date:
                continue

            issues = self.checker.check_match(match)
            if not issues:
                continue

            # Handle each issue type
            for issue in issues:
                if issue.issue_code == 'DECEASED_IN_MATCH':
                    if not dry_run:
                        self._delete_match_with_log(match, issue, 'deceased_wrestler')
                        results['events_cleaned'].add(match.event.id)
                    results['deceased_deleted'] += 1
                    break  # Match deleted, no more processing needed

                elif issue.issue_code == 'RETIRED_IN_MATCH':
                    if not dry_run:
                        self._delete_match_with_log(match, issue, 'retired_wrestler')
                        results['events_cleaned'].add(match.event.id)
                    results['retired_deleted'] += 1
                    break

                elif issue.issue_code == 'ERA_MISMATCH' and issue.issue_type == 'error':
                    if not dry_run:
                        self._delete_match_with_log(match, issue, 'era_mismatch')
                        results['events_cleaned'].add(match.event.id)
                    results['era_mismatch_deleted'] += 1
                    break

                elif issue.issue_code == 'TAG_TEAM_AS_WRESTLER':
                    if not dry_run:
                        self._fix_tag_team_in_match(match, issue)
                    results['tag_teams_fixed'] += 1
                    # Don't break - might have other fixable issues

        # Clean up empty events (events with all matches deleted)
        if not dry_run:
            empty_events = Event.objects.filter(
                id__in=results['events_cleaned']
            ).annotate(match_count=Count('matches')).filter(match_count=0)

            for event in empty_events:
                WrestleBotActivity.log_activity(
                    action_type='verify',
                    entity_type='event',
                    entity_id=event.id,
                    entity_name=event.name,
                    source='match_cleanup',
                    details={'action': 'deleted', 'reason': 'all_matches_invalid'},
                )
                event.delete()

        results['events_cleaned'] = len(results['events_cleaned'])

        logger.info(
            f"Match cleanup: checked {results['matches_checked']}, "
            f"deleted {results['deceased_deleted']} deceased, "
            f"deleted {results['retired_deleted']} retired, "
            f"deleted {results['era_mismatch_deleted']} era mismatch, "
            f"fixed {results['tag_teams_fixed']} tag teams"
        )

        return results

    def _delete_match_with_log(self, match, issue: QualityIssue, reason: str):
        """Delete a match and log the activity."""
        from owdb_django.wrestlebot.models import WrestleBotActivity

        WrestleBotActivity.log_activity(
            action_type='verify',
            entity_type='match',
            entity_id=match.id,
            entity_name=match.match_text[:100] if match.match_text else f'Match #{match.id}',
            source='match_cleanup',
            details={
                'action': 'deleted',
                'reason': reason,
                'issue': issue.description,
                'event_id': match.event.id if match.event else None,
                'event_name': match.event.name if match.event else None,
            },
        )
        match.delete()

    def _fix_tag_team_in_match(self, match, issue: QualityIssue):
        """Replace tag team entry with individual wrestlers."""
        from ..models import Wrestler
        from owdb_django.wrestlebot.models import WrestleBotActivity

        if not issue.suggested_value:
            return

        member_names = issue.suggested_value  # List of individual wrestler names

        # Find the tag team wrestler to remove
        tag_team_wrestler = match.wrestlers.filter(
            name__iexact=issue.current_value
        ).first()

        if not tag_team_wrestler:
            return

        # Remove the tag team entry
        match.wrestlers.remove(tag_team_wrestler)

        # Add individual wrestlers
        for member_name in member_names:
            # Find or create the individual wrestler
            wrestler = Wrestler.objects.filter(name__iexact=member_name).first()
            if not wrestler:
                # Try to find by partial match
                wrestler = Wrestler.objects.filter(name__icontains=member_name).first()

            if wrestler:
                match.wrestlers.add(wrestler)
            else:
                # Create the wrestler if not found
                wrestler = Wrestler.objects.create(name=member_name)
                match.wrestlers.add(wrestler)
                logger.info(f"Created wrestler: {member_name}")

        WrestleBotActivity.log_activity(
            action_type='verify',
            entity_type='match',
            entity_id=match.id,
            entity_name=match.match_text[:100] if match.match_text else f'Match #{match.id}',
            source='match_cleanup',
            details={
                'action': 'fixed_tag_team',
                'removed': issue.current_value,
                'added': member_names,
            },
        )
