import logging
import os

from celery import Celery
from celery.signals import beat_init

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'owdb_django.settings')

app = Celery('owdb_django')

# Load config from Django settings, using the CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all registered Django apps
app.autodiscover_tasks()

logger = logging.getLogger(__name__)


@beat_init.connect
def sync_beat_schedule(**kwargs):
    """Sync CELERY_BEAT_SCHEDULE into the DB when using DatabaseScheduler."""
    if os.getenv("SYNC_CELERY_SCHEDULE", "true").lower() != "true":
        return

    try:
        from django.core.management import call_command
        call_command("setup_celery_schedule", verbosity=0)
    except Exception as exc:
        logger.warning("Celery schedule sync failed: %s", exc)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
