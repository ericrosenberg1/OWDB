from django.apps import AppConfig


class OwdbappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "owdb_django.owdbapp"

    def ready(self):
        # Registers the deploy-time system checks: SQLite directory writable
        # (ROS-1204), production SECRET_KEY set, and search_fields resolvable
        # (ROS-3608).
        from . import checks  # noqa: F401
