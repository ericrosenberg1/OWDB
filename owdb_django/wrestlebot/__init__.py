"""
WrestleBot 2.0 - Autonomous Data Enhancement Service

A lightweight, autonomous service that continuously improves the wrestling database by:
1. Discovery - Adding new entries (wrestlers, events, promotions, etc.)
2. Enrichment - Adding more details to incomplete entries
3. Quality - Improving accuracy through cross-source verification

This is a Django app that provides:
- Models for activity tracking and configuration
- Admin interface for monitoring bot activity
- Celery tasks for scheduled operations
- Quality checking and data cleanup utilities
"""

default_app_config = 'owdb_django.wrestlebot.apps.WrestlebotConfig'
