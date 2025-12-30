"""
Completeness Scoring System for WrestleBot 2.0

Scores entities 0-100 based on field completeness to prioritize
which entries need the most improvement.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from django.db.models import Count, Q

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of an entity's completeness score."""
    total_score: int
    max_score: int
    percentage: float
    field_scores: Dict[str, Tuple[int, int]]  # field: (earned, max)
    missing_fields: List[str]
    suggestions: List[str]


class CompletenessScorer:
    """
    Calculates completeness scores for database entities.

    Higher scores = more complete entries.
    Lower scores = entries that need enrichment.
    """

    # Scoring weights for each entity type
    WRESTLER_WEIGHTS = {
        'name': 10,           # Required - always present
        'real_name': 10,
        'hometown': 5,
        'nationality': 5,
        'debut_year': 10,
        'retirement_year': 5,  # Only for retired wrestlers
        'bio': 15,
        'image_url': 15,
        'aliases': 5,
        'finishers': 5,
        'promotions': 10,     # Has associated promotions
        'matches': 10,        # Has match history
    }

    PROMOTION_WEIGHTS = {
        'name': 10,
        'abbreviation': 10,
        'founded_year': 10,
        'closed_year': 5,     # Only for defunct promotions
        'about': 15,
        'image_url': 15,
        'website': 5,
        'headquarters': 5,
        'wrestlers': 15,      # Has associated wrestlers
        'events': 10,         # Has events
    }

    EVENT_WEIGHTS = {
        'name': 10,
        'date': 10,           # Required
        'promotion': 15,
        'venue': 10,
        'attendance': 10,
        'image_url': 10,
        'matches': 25,        # Has match data
        'tagline': 5,
        'about': 5,
    }

    TITLE_WEIGHTS = {
        'name': 15,
        'promotion': 15,
        'weight_class': 10,
        'gender': 10,
        'is_active': 5,
        'image_url': 15,
        'about': 10,
        'title_matches': 20,  # Has title match history
    }

    VENUE_WEIGHTS = {
        'name': 15,
        'location': 15,
        'capacity': 15,
        'image_url': 20,
        'events': 20,         # Has hosted events
        'about': 15,
    }

    def score_wrestler(self, wrestler) -> ScoreBreakdown:
        """Calculate completeness score for a wrestler."""
        field_scores = {}
        missing_fields = []
        suggestions = []

        weights = self.WRESTLER_WEIGHTS.copy()

        # Name - always present
        field_scores['name'] = (weights['name'], weights['name'])

        # Real name
        if wrestler.real_name:
            field_scores['real_name'] = (weights['real_name'], weights['real_name'])
        else:
            field_scores['real_name'] = (0, weights['real_name'])
            missing_fields.append('real_name')
            suggestions.append('Add real name from Wikipedia')

        # Hometown
        if wrestler.hometown:
            field_scores['hometown'] = (weights['hometown'], weights['hometown'])
        else:
            field_scores['hometown'] = (0, weights['hometown'])
            missing_fields.append('hometown')

        # Nationality
        if wrestler.nationality:
            field_scores['nationality'] = (weights['nationality'], weights['nationality'])
        else:
            field_scores['nationality'] = (0, weights['nationality'])
            missing_fields.append('nationality')

        # Debut year
        if wrestler.debut_year:
            field_scores['debut_year'] = (weights['debut_year'], weights['debut_year'])
        else:
            field_scores['debut_year'] = (0, weights['debut_year'])
            missing_fields.append('debut_year')
            suggestions.append('Add debut year from Cagematch')

        # Retirement year - only count if wrestler is retired
        if hasattr(wrestler, 'is_retired') and wrestler.is_retired:
            if wrestler.retirement_year:
                field_scores['retirement_year'] = (weights['retirement_year'], weights['retirement_year'])
            else:
                field_scores['retirement_year'] = (0, weights['retirement_year'])
                missing_fields.append('retirement_year')
        else:
            # Not retired, don't count this field
            del weights['retirement_year']

        # Bio
        if wrestler.bio and len(wrestler.bio) > 50:
            field_scores['bio'] = (weights['bio'], weights['bio'])
        elif wrestler.bio:
            # Partial credit for short bio
            field_scores['bio'] = (weights['bio'] // 2, weights['bio'])
            suggestions.append('Expand biography with more details')
        else:
            field_scores['bio'] = (0, weights['bio'])
            missing_fields.append('bio')
            suggestions.append('Generate biography from available data')

        # Image
        if wrestler.image_url:
            field_scores['image_url'] = (weights['image_url'], weights['image_url'])
        else:
            field_scores['image_url'] = (0, weights['image_url'])
            missing_fields.append('image_url')
            suggestions.append('Fetch image from Wikimedia Commons')

        # Aliases
        if wrestler.aliases:
            field_scores['aliases'] = (weights['aliases'], weights['aliases'])
        else:
            field_scores['aliases'] = (0, weights['aliases'])
            missing_fields.append('aliases')

        # Finishers
        if wrestler.finishers:
            field_scores['finishers'] = (weights['finishers'], weights['finishers'])
        else:
            field_scores['finishers'] = (0, weights['finishers'])
            missing_fields.append('finishers')
            suggestions.append('Add finishing moves from Wikipedia/Cagematch')

        # Associated promotions
        promotion_count = wrestler.promotions.count() if hasattr(wrestler, 'promotions') else 0
        if promotion_count > 0:
            field_scores['promotions'] = (weights['promotions'], weights['promotions'])
        else:
            field_scores['promotions'] = (0, weights['promotions'])
            missing_fields.append('promotions')

        # Match history
        match_count = wrestler.matches.count() if hasattr(wrestler, 'matches') else 0
        if match_count > 0:
            field_scores['matches'] = (weights['matches'], weights['matches'])
        else:
            field_scores['matches'] = (0, weights['matches'])
            missing_fields.append('matches')

        return self._calculate_breakdown(field_scores, missing_fields, suggestions)

    def score_promotion(self, promotion) -> ScoreBreakdown:
        """Calculate completeness score for a promotion."""
        field_scores = {}
        missing_fields = []
        suggestions = []

        weights = self.PROMOTION_WEIGHTS.copy()

        # Name - always present
        field_scores['name'] = (weights['name'], weights['name'])

        # Abbreviation
        if promotion.abbreviation:
            field_scores['abbreviation'] = (weights['abbreviation'], weights['abbreviation'])
        else:
            field_scores['abbreviation'] = (0, weights['abbreviation'])
            missing_fields.append('abbreviation')

        # Founded year
        if promotion.founded_year:
            field_scores['founded_year'] = (weights['founded_year'], weights['founded_year'])
        else:
            field_scores['founded_year'] = (0, weights['founded_year'])
            missing_fields.append('founded_year')
            suggestions.append('Add founding year from Wikipedia')

        # Closed year - only for defunct promotions
        if hasattr(promotion, 'is_defunct') and promotion.is_defunct:
            if promotion.closed_year:
                field_scores['closed_year'] = (weights['closed_year'], weights['closed_year'])
            else:
                field_scores['closed_year'] = (0, weights['closed_year'])
                missing_fields.append('closed_year')
        else:
            del weights['closed_year']

        # About
        if promotion.about and len(promotion.about) > 50:
            field_scores['about'] = (weights['about'], weights['about'])
        elif promotion.about:
            field_scores['about'] = (weights['about'] // 2, weights['about'])
            suggestions.append('Expand description')
        else:
            field_scores['about'] = (0, weights['about'])
            missing_fields.append('about')
            suggestions.append('Add description from Wikipedia')

        # Image
        if promotion.image_url:
            field_scores['image_url'] = (weights['image_url'], weights['image_url'])
        else:
            field_scores['image_url'] = (0, weights['image_url'])
            missing_fields.append('image_url')
            suggestions.append('Fetch logo from Wikimedia Commons')

        # Website
        if promotion.website:
            field_scores['website'] = (weights['website'], weights['website'])
        else:
            field_scores['website'] = (0, weights['website'])
            missing_fields.append('website')

        # Headquarters
        if hasattr(promotion, 'headquarters') and promotion.headquarters:
            field_scores['headquarters'] = (weights['headquarters'], weights['headquarters'])
        else:
            field_scores['headquarters'] = (0, weights['headquarters'])
            missing_fields.append('headquarters')

        # Associated wrestlers
        wrestler_count = promotion.wrestlers.count() if hasattr(promotion, 'wrestlers') else 0
        if wrestler_count > 0:
            field_scores['wrestlers'] = (weights['wrestlers'], weights['wrestlers'])
        else:
            field_scores['wrestlers'] = (0, weights['wrestlers'])
            missing_fields.append('wrestlers')

        # Events
        event_count = promotion.events.count() if hasattr(promotion, 'events') else 0
        if event_count > 0:
            field_scores['events'] = (weights['events'], weights['events'])
        else:
            field_scores['events'] = (0, weights['events'])
            missing_fields.append('events')

        return self._calculate_breakdown(field_scores, missing_fields, suggestions)

    def score_event(self, event) -> ScoreBreakdown:
        """Calculate completeness score for an event."""
        field_scores = {}
        missing_fields = []
        suggestions = []

        weights = self.EVENT_WEIGHTS.copy()

        # Name - always present
        field_scores['name'] = (weights['name'], weights['name'])

        # Date - always present
        field_scores['date'] = (weights['date'], weights['date'])

        # Promotion
        if event.promotion:
            field_scores['promotion'] = (weights['promotion'], weights['promotion'])
        else:
            field_scores['promotion'] = (0, weights['promotion'])
            missing_fields.append('promotion')
            suggestions.append('Link to promotion')

        # Venue
        if event.venue:
            field_scores['venue'] = (weights['venue'], weights['venue'])
        else:
            field_scores['venue'] = (0, weights['venue'])
            missing_fields.append('venue')
            suggestions.append('Add venue information')

        # Attendance
        if event.attendance:
            field_scores['attendance'] = (weights['attendance'], weights['attendance'])
        else:
            field_scores['attendance'] = (0, weights['attendance'])
            missing_fields.append('attendance')

        # Image
        if event.image_url:
            field_scores['image_url'] = (weights['image_url'], weights['image_url'])
        else:
            field_scores['image_url'] = (0, weights['image_url'])
            missing_fields.append('image_url')

        # Matches
        match_count = event.matches.count() if hasattr(event, 'matches') else 0
        if match_count >= 5:
            field_scores['matches'] = (weights['matches'], weights['matches'])
        elif match_count > 0:
            # Partial credit for some matches
            field_scores['matches'] = (weights['matches'] // 2, weights['matches'])
            suggestions.append('Add more match data')
        else:
            field_scores['matches'] = (0, weights['matches'])
            missing_fields.append('matches')
            suggestions.append('Add match results from Cagematch')

        # Tagline
        if hasattr(event, 'tagline') and event.tagline:
            field_scores['tagline'] = (weights['tagline'], weights['tagline'])
        else:
            field_scores['tagline'] = (0, weights['tagline'])
            missing_fields.append('tagline')

        # About
        if hasattr(event, 'about') and event.about:
            field_scores['about'] = (weights['about'], weights['about'])
        else:
            field_scores['about'] = (0, weights['about'])
            missing_fields.append('about')

        return self._calculate_breakdown(field_scores, missing_fields, suggestions)

    def score_title(self, title) -> ScoreBreakdown:
        """Calculate completeness score for a championship title."""
        field_scores = {}
        missing_fields = []
        suggestions = []

        weights = self.TITLE_WEIGHTS.copy()

        # Name - always present
        field_scores['name'] = (weights['name'], weights['name'])

        # Promotion
        if title.promotion:
            field_scores['promotion'] = (weights['promotion'], weights['promotion'])
        else:
            field_scores['promotion'] = (0, weights['promotion'])
            missing_fields.append('promotion')

        # Weight class
        if hasattr(title, 'weight_class') and title.weight_class:
            field_scores['weight_class'] = (weights['weight_class'], weights['weight_class'])
        else:
            field_scores['weight_class'] = (0, weights['weight_class'])
            missing_fields.append('weight_class')

        # Gender
        if hasattr(title, 'gender') and title.gender:
            field_scores['gender'] = (weights['gender'], weights['gender'])
        else:
            field_scores['gender'] = (0, weights['gender'])
            missing_fields.append('gender')

        # Is active
        if hasattr(title, 'is_active'):
            field_scores['is_active'] = (weights['is_active'], weights['is_active'])
        else:
            field_scores['is_active'] = (0, weights['is_active'])

        # Image
        if title.image_url:
            field_scores['image_url'] = (weights['image_url'], weights['image_url'])
        else:
            field_scores['image_url'] = (0, weights['image_url'])
            missing_fields.append('image_url')
            suggestions.append('Fetch title belt image')

        # About
        if hasattr(title, 'about') and title.about:
            field_scores['about'] = (weights['about'], weights['about'])
        else:
            field_scores['about'] = (0, weights['about'])
            missing_fields.append('about')

        # Title matches
        match_count = title.title_matches.count() if hasattr(title, 'title_matches') else 0
        if match_count > 0:
            field_scores['title_matches'] = (weights['title_matches'], weights['title_matches'])
        else:
            field_scores['title_matches'] = (0, weights['title_matches'])
            missing_fields.append('title_matches')

        return self._calculate_breakdown(field_scores, missing_fields, suggestions)

    def score_venue(self, venue) -> ScoreBreakdown:
        """Calculate completeness score for a venue."""
        field_scores = {}
        missing_fields = []
        suggestions = []

        weights = self.VENUE_WEIGHTS.copy()

        # Name - always present
        field_scores['name'] = (weights['name'], weights['name'])

        # Location
        if venue.location:
            field_scores['location'] = (weights['location'], weights['location'])
        else:
            field_scores['location'] = (0, weights['location'])
            missing_fields.append('location')
            suggestions.append('Add city/state/country')

        # Capacity
        if venue.capacity:
            field_scores['capacity'] = (weights['capacity'], weights['capacity'])
        else:
            field_scores['capacity'] = (0, weights['capacity'])
            missing_fields.append('capacity')
            suggestions.append('Add venue capacity from Wikipedia')

        # Image
        if venue.image_url:
            field_scores['image_url'] = (weights['image_url'], weights['image_url'])
        else:
            field_scores['image_url'] = (0, weights['image_url'])
            missing_fields.append('image_url')
            suggestions.append('Fetch venue image from Wikimedia Commons')

        # Events
        event_count = venue.events.count() if hasattr(venue, 'events') else 0
        if event_count > 0:
            field_scores['events'] = (weights['events'], weights['events'])
        else:
            field_scores['events'] = (0, weights['events'])
            missing_fields.append('events')

        # About
        if hasattr(venue, 'about') and venue.about:
            field_scores['about'] = (weights['about'], weights['about'])
        else:
            field_scores['about'] = (0, weights['about'])
            missing_fields.append('about')

        return self._calculate_breakdown(field_scores, missing_fields, suggestions)

    def _calculate_breakdown(
        self,
        field_scores: Dict[str, Tuple[int, int]],
        missing_fields: List[str],
        suggestions: List[str]
    ) -> ScoreBreakdown:
        """Calculate the final score breakdown."""
        total_score = sum(earned for earned, _ in field_scores.values())
        max_score = sum(max_val for _, max_val in field_scores.values())
        percentage = (total_score / max_score * 100) if max_score > 0 else 0

        return ScoreBreakdown(
            total_score=total_score,
            max_score=max_score,
            percentage=round(percentage, 1),
            field_scores=field_scores,
            missing_fields=missing_fields,
            suggestions=suggestions[:5],  # Top 5 suggestions
        )

    def score_entity(self, entity) -> ScoreBreakdown:
        """Score any entity type automatically."""
        entity_type = entity.__class__.__name__.lower()

        scorers = {
            'wrestler': self.score_wrestler,
            'promotion': self.score_promotion,
            'event': self.score_event,
            'title': self.score_title,
            'venue': self.score_venue,
        }

        scorer = scorers.get(entity_type)
        if scorer:
            return scorer(entity)

        # Default: return a basic score
        return ScoreBreakdown(
            total_score=50,
            max_score=100,
            percentage=50.0,
            field_scores={},
            missing_fields=[],
            suggestions=[],
        )

    def get_low_score_entities(
        self,
        model_class,
        max_score: float = 50.0,
        limit: int = 20
    ) -> List[Tuple[Any, ScoreBreakdown]]:
        """
        Get entities with completeness scores below threshold.

        Returns list of (entity, score_breakdown) tuples.
        """
        results = []

        # Get all entities and score them
        # For efficiency, we could add score caching later
        for entity in model_class.objects.all()[:limit * 3]:  # Get more to filter
            breakdown = self.score_entity(entity)
            if breakdown.percentage <= max_score:
                results.append((entity, breakdown))
                if len(results) >= limit:
                    break

        # Sort by score (lowest first)
        results.sort(key=lambda x: x[1].percentage)
        return results[:limit]
