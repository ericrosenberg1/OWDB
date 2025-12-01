from celery import shared_task
from django.core.cache import cache
from django.db.models import Count

import logging

logger = logging.getLogger(__name__)


@shared_task
def reset_daily_api_limits():
    """Reset daily API request counts for all keys. Run daily via Celery Beat."""
    from .models import APIKey
    from django.utils import timezone

    today = timezone.now().date()
    updated = APIKey.objects.filter(last_reset__lt=today).update(
        requests_today=0,
        last_reset=today
    )
    logger.info(f"Reset daily limits for {updated} API keys")
    return updated


@shared_task
def warm_stats_cache():
    """Pre-compute and cache database statistics. Run hourly."""
    from .models import Wrestler, Promotion, Event, Match, Title

    stats = {
        'wrestlers': Wrestler.objects.count(),
        'promotions': Promotion.objects.count(),
        'events': Event.objects.count(),
        'matches': Match.objects.count(),
        'titles': Title.objects.count(),
    }

    cache.set('homepage_stats', stats, timeout=3600)  # 1 hour
    logger.info(f"Warmed stats cache: {stats}")
    return stats


@shared_task
def cleanup_inactive_api_keys():
    """Remove API keys that haven't been used in 90 days. Run weekly."""
    from .models import APIKey
    from django.utils import timezone
    from datetime import timedelta

    cutoff = timezone.now() - timedelta(days=90)
    deleted, _ = APIKey.objects.filter(
        last_used__lt=cutoff,
        is_paid=False
    ).delete()

    logger.info(f"Cleaned up {deleted} inactive API keys")
    return deleted
