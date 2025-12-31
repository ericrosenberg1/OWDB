"""
TV Episode scraper for wrestling shows.

Uses TMDB for episode metadata and Cagematch for match results.
Handles both historical backfill and live updates.

Usage:
    scraper = TVEpisodeScraper()

    # Poll for new episodes (quick, TMDB only)
    results = scraper.poll_for_new_episodes()

    # Backfill historical episodes for a show
    results = scraper.scrape_show_episodes(show, start_date, end_date)
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from .tmdb import TMDBClient
from .cagematch import CagematchScraper

logger = logging.getLogger(__name__)


class TVEpisodeScraper:
    """
    Coordinates episode data from multiple sources.

    Flow:
    1. Get episode list from TMDB (air dates, episode numbers)
    2. Create Event records for each episode
    3. Match enrichment handled separately via WrestleBot (due to Cagematch rate limits)
    """

    def __init__(self):
        self.tmdb = TMDBClient()
        self.cagematch = CagematchScraper()

    def scrape_show_episodes(
        self,
        show,  # TVShow model instance
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> Dict[str, int]:
        """
        Scrape episodes for a show within date range.

        Args:
            show: TVShow model instance
            start_date: Start of date range (default: show premiere)
            end_date: End of date range (default: today)
            limit: Maximum episodes to process

        Returns:
            Dict with counts: created, updated, skipped
        """
        from owdb_django.owdbapp.models import Event

        results = {'created': 0, 'updated': 0, 'skipped': 0, 'errors': 0}

        if not show.tmdb_id:
            logger.warning("Show %s has no TMDB ID", show.name)
            return results

        # Get episodes from TMDB
        tmdb_episodes = self._get_tmdb_episodes(
            show.tmdb_id, start_date, end_date, limit
        )

        logger.info(
            "Found %d episodes from TMDB for %s",
            len(tmdb_episodes), show.name
        )

        for ep_data in tmdb_episodes:
            try:
                with transaction.atomic():
                    event, created = self._create_or_update_episode(show, ep_data)

                    if event is None:
                        results['skipped'] += 1
                    elif created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1

            except Exception as e:
                logger.error(
                    "Error processing episode %s: %s",
                    ep_data.get('episode_number'), e
                )
                results['errors'] += 1

        return results

    def _get_tmdb_episodes(
        self,
        tmdb_id: int,
        start_date: Optional[date],
        end_date: Optional[date],
        limit: int,
    ) -> List[Dict]:
        """
        Fetch episodes from TMDB within date range.

        Args:
            tmdb_id: TMDB TV show ID
            start_date: Start of date range
            end_date: End of date range
            limit: Maximum episodes to return

        Returns:
            List of episode data dicts
        """
        all_episodes = []

        # Get show details to find season count
        details = self.tmdb.get_tv_details(tmdb_id)
        if not details:
            logger.warning("Could not get TMDB details for show %d", tmdb_id)
            return []

        num_seasons = details.get('number_of_seasons', 0)
        logger.info("Show has %d seasons", num_seasons)

        # Iterate through seasons (reverse order for recent first)
        for season_num in range(num_seasons, 0, -1):
            if len(all_episodes) >= limit:
                break

            season_data = self.tmdb.get_tv_season(tmdb_id, season_num)
            if not season_data or 'episodes' not in season_data:
                continue

            for ep in season_data['episodes']:
                air_date_str = ep.get('air_date')
                if not air_date_str:
                    continue

                try:
                    air_date = date.fromisoformat(air_date_str)
                except ValueError:
                    continue

                # Filter by date range
                if start_date and air_date < start_date:
                    continue
                if end_date and air_date > end_date:
                    continue

                # Add season number to episode data
                ep['season_number'] = season_num
                all_episodes.append(ep)

                if len(all_episodes) >= limit:
                    break

        # Sort by air date (oldest first for consistent ordering)
        all_episodes.sort(key=lambda x: x.get('air_date', ''))

        return all_episodes

    def _create_or_update_episode(
        self, show, ep_data: Dict
    ) -> tuple:
        """
        Create or update an Event from TMDB episode data.

        Args:
            show: TVShow model instance
            ep_data: Episode data from TMDB

        Returns:
            Tuple of (Event instance or None, was_created boolean)
        """
        from owdb_django.owdbapp.models import Event

        air_date_str = ep_data.get('air_date')
        if not air_date_str:
            return None, False

        try:
            air_date = date.fromisoformat(air_date_str)
        except ValueError:
            return None, False

        ep_num = ep_data.get('episode_number')
        season_num = ep_data.get('season_number')

        # Build episode name
        episode_title = ep_data.get('name', '')
        if ep_num:
            # Use overall episode number for shows like Raw
            # For long-running shows, calculate total episode number
            name = f"{show.name} #{ep_num}"
            if episode_title and episode_title != f"Episode {ep_num}":
                # Include title if it's meaningful
                name = f"{show.name} #{ep_num}"
        else:
            name = episode_title or f"{show.name} Episode"

        # Check if episode exists by show + episode number
        existing = Event.objects.filter(
            tv_show=show,
            episode_number=ep_num,
            season_number=season_num,
        ).first()

        # Also check by show + date (for episodes without numbers)
        if not existing and not ep_num:
            existing = Event.objects.filter(
                tv_show=show,
                date=air_date,
            ).first()

        if existing:
            # Update with TMDB data if we have new info
            updated = False
            if not existing.tmdb_episode_id and ep_data.get('id'):
                existing.tmdb_episode_id = ep_data['id']
                updated = True
            if not existing.about and ep_data.get('overview'):
                existing.about = ep_data['overview'][:500]
                updated = True
            if not existing.episode_number and ep_num:
                existing.episode_number = ep_num
                updated = True
            if not existing.season_number and season_num:
                existing.season_number = season_num
                updated = True
            if existing.event_type != 'tv_episode':
                existing.event_type = 'tv_episode'
                updated = True

            if updated:
                existing.save()
            return existing, False

        # Create new episode
        event = Event.objects.create(
            name=name,
            date=air_date,
            promotion=show.promotion,
            tv_show=show,
            episode_number=ep_num,
            season_number=season_num,
            event_type='tv_episode',
            tmdb_episode_id=ep_data.get('id'),
            about=ep_data.get('overview', '')[:500] if ep_data.get('overview') else None,
        )

        logger.debug("Created episode: %s", event.name)
        return event, True

    def poll_for_new_episodes(self) -> Dict[str, Any]:
        """
        Quick poll for newly aired episodes (15-minute task).

        Only checks TMDB, doesn't hit Cagematch.
        Creates new episode Events for recently aired shows.

        Returns:
            Dict with results summary
        """
        from owdb_django.owdbapp.models import TVShow, Event

        results = {
            'shows_checked': 0,
            'new_episodes': 0,
            'updated_episodes': 0,
            'episodes': [],
        }

        today = date.today()
        # Look back 7 days to catch any missed episodes
        lookback_date = today - timedelta(days=7)

        # Check all active shows with TMDB IDs
        active_shows = TVShow.objects.filter(
            finale_date__isnull=True,
            tmdb_id__isnull=False
        )

        for show in active_shows:
            results['shows_checked'] += 1

            try:
                # Get latest episodes from TMDB
                episodes = self.tmdb.get_latest_episodes(show.tmdb_id, limit=10)

                for ep in episodes:
                    air_date_str = ep.get('air_date')
                    if not air_date_str:
                        continue

                    try:
                        air_date = date.fromisoformat(air_date_str)
                    except ValueError:
                        continue

                    # Only process recent episodes
                    if air_date < lookback_date:
                        continue

                    # Skip future episodes more than 30 days out
                    if air_date > today + timedelta(days=30):
                        continue

                    # Check if we have this episode
                    ep_num = ep.get('episode_number')
                    season_num = ep.get('season_number')

                    exists = Event.objects.filter(
                        tv_show=show,
                        episode_number=ep_num,
                        season_number=season_num,
                    ).exists()

                    if not exists:
                        # Add season number for processing
                        ep['season_number'] = season_num
                        event, created = self._create_or_update_episode(show, ep)
                        if created:
                            results['new_episodes'] += 1
                            results['episodes'].append({
                                'show': show.name,
                                'episode': ep_num,
                                'season': season_num,
                                'date': air_date_str,
                                'name': event.name if event else '',
                            })
                        elif event:
                            results['updated_episodes'] += 1

            except Exception as e:
                logger.error("Error polling show %s: %s", show.name, e)

        logger.info(
            "TV episode poll: checked %d shows, found %d new episodes",
            results['shows_checked'], results['new_episodes']
        )

        return results

    def backfill_show_by_year(
        self,
        show,  # TVShow model instance
        year: int,
    ) -> Dict[str, int]:
        """
        Backfill all episodes for a show in a specific year.

        Args:
            show: TVShow model instance
            year: Year to backfill

        Returns:
            Dict with counts
        """
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        return self.scrape_show_episodes(
            show,
            start_date=start_date,
            end_date=end_date,
            limit=500,  # Allow more for full year
        )

    def backfill_all_episodes(
        self,
        show,  # TVShow model instance
    ) -> Dict[str, int]:
        """
        Backfill ALL episodes for a show from premiere to present.

        Warning: This can be slow for long-running shows like Raw.

        Args:
            show: TVShow model instance

        Returns:
            Dict with counts
        """
        start_date = show.premiere_date
        end_date = date.today()

        return self.scrape_show_episodes(
            show,
            start_date=start_date,
            end_date=end_date,
            limit=5000,  # High limit for full backfill
        )

    def get_missing_episodes(
        self,
        show,  # TVShow model instance
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict]:
        """
        Find episodes that exist in TMDB but not in our database.

        Args:
            show: TVShow model instance
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of missing episode data dicts
        """
        from owdb_django.owdbapp.models import Event

        if not show.tmdb_id:
            return []

        # Get all episodes from TMDB
        tmdb_episodes = self._get_tmdb_episodes(
            show.tmdb_id,
            start_date or show.premiere_date,
            end_date or date.today(),
            limit=5000
        )

        # Get existing episode numbers
        existing = set(
            Event.objects.filter(tv_show=show)
            .values_list('episode_number', 'season_number')
        )

        missing = []
        for ep in tmdb_episodes:
            ep_num = ep.get('episode_number')
            season_num = ep.get('season_number')
            if (ep_num, season_num) not in existing:
                missing.append(ep)

        return missing

    def verify_episode_count(self, show) -> Dict[str, int]:
        """
        Compare episode count between TMDB and our database.

        Args:
            show: TVShow model instance

        Returns:
            Dict with tmdb_count, db_count, and difference
        """
        from owdb_django.owdbapp.models import Event

        if not show.tmdb_id:
            return {'error': 'No TMDB ID'}

        # Get TMDB episode count
        details = self.tmdb.get_tv_details(show.tmdb_id)
        tmdb_count = details.get('number_of_episodes', 0) if details else 0

        # Get our count
        db_count = Event.objects.filter(tv_show=show).count()

        return {
            'tmdb_count': tmdb_count,
            'db_count': db_count,
            'difference': tmdb_count - db_count,
            'complete': tmdb_count == db_count,
        }
