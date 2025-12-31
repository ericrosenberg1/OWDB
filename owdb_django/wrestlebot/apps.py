from django.apps import AppConfig


class WrestlebotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'owdb_django.wrestlebot'
    verbose_name = 'WrestleBot'

    def ready(self):
        # Import signals if needed
        pass
