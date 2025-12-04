"""
WrestleBot AI - Self-hosted AI-powered wrestling data discovery.

This module provides intelligent data discovery and enrichment using:
1. Wikipedia API for factual data extraction (respecting copyright)
2. Self-hosted AI (Ollama) for data processing and verification
3. Strong safeguards to ensure only factual, non-copyrightable data is used
"""

from .wikipedia_api import WikipediaAPIFetcher
from .ai_processor import OllamaProcessor
from .bot import WrestleBot

__all__ = ['WikipediaAPIFetcher', 'OllamaProcessor', 'WrestleBot']
