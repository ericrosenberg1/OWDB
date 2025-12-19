"""
Management command to sync Celery Beat schedules from settings to database.

This ensures that scheduled tasks defined in CELERY_BEAT_SCHEDULE are
properly registered in the django_celery_beat database tables, which is
required when using DatabaseScheduler.

Usage:
    python manage.py setup_celery_schedule
"""

import json
from django.conf import settings
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, IntervalSchedule


class Command(BaseCommand):
    help = 'Sync Celery Beat schedules from settings to database'

    def handle(self, *args, **options):
        schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})

        if not schedule:
            self.stdout.write(self.style.WARNING('No CELERY_BEAT_SCHEDULE found in settings'))
            return

        self.stdout.write(f'Found {len(schedule)} scheduled tasks in settings')

        created_count = 0
        updated_count = 0

        for task_name, task_config in schedule.items():
            task_path = task_config.get('task')
            schedule_seconds = task_config.get('schedule')
            args = task_config.get('args', [])
            kwargs = task_config.get('kwargs', {})

            if not task_path or not schedule_seconds:
                self.stdout.write(self.style.WARNING(
                    f'Skipping {task_name}: missing task or schedule'
                ))
                continue

            # Convert seconds to appropriate interval
            if schedule_seconds >= 86400:
                days = int(schedule_seconds // 86400)
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=days,
                    period=IntervalSchedule.DAYS
                )
            elif schedule_seconds >= 3600:
                hours = int(schedule_seconds // 3600)
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=hours,
                    period=IntervalSchedule.HOURS
                )
            elif schedule_seconds >= 60:
                minutes = int(schedule_seconds // 60)
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=minutes,
                    period=IntervalSchedule.MINUTES
                )
            else:
                interval, _ = IntervalSchedule.objects.get_or_create(
                    every=int(schedule_seconds),
                    period=IntervalSchedule.SECONDS
                )

            # Create or update the periodic task
            periodic_task, created = PeriodicTask.objects.update_or_create(
                name=task_name,
                defaults={
                    'task': task_path,
                    'interval': interval,
                    'crontab': None,
                    'solar': None,
                    'clocked': None,
                    'one_off': False,
                    'args': json.dumps(args),
                    'kwargs': json.dumps(kwargs),
                    'enabled': True,
                }
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {task_name}'))
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {task_name}')

        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Schedule sync complete: {created_count} created, {updated_count} updated'
        ))

        # List all enabled tasks
        enabled_tasks = PeriodicTask.objects.filter(enabled=True).count()
        self.stdout.write(f'Total enabled periodic tasks: {enabled_tasks}')
