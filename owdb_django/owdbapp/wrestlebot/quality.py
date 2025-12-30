"""
WrestleBot 2.0 Data Quality Module

Provides comprehensive data quality checks, validation, and cleanup functionality
to ensure database entries are accurate and properly formatted.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
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

    # Minimum/maximum reasonable values
    MIN_YEAR = 1900
    MAX_YEAR_OFFSET = 2  # Allow up to 2 years in the future

    def __init__(self):
        self._current_year = datetime.now().year

    def check_wrestler(self, wrestler) -> List[QualityIssue]:
        """Check a single wrestler for quality issues."""
        issues = []

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
        from .models import WrestleBotActivity

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
        from .models import WrestleBotActivity

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
        from .models import WrestleBotActivity

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
