"""
WrestleBot 2.0 - Autonomous Data Enhancement Service

A lightweight, autonomous service that continuously improves the wrestling database by:
1. Discovery - Adding new entries (wrestlers, events, promotions, etc.)
2. Enrichment - Adding more details to incomplete entries
3. Quality - Improving accuracy through cross-source verification

Components:
- bot.py: Main orchestrator
- discovery.py: Find new entities to add
- enrichment.py: Improve existing entries
- scoring.py: Completeness scoring system
- ai_enhancer.py: Optional Claude API integration
- models.py: Activity tracking
"""

from .bot import WrestleBot
from .scoring import CompletenessScorer
from .discovery import EntityDiscovery
from .enrichment import EntityEnrichment

__all__ = [
    'WrestleBot',
    'CompletenessScorer',
    'EntityDiscovery',
    'EntityEnrichment',
]
