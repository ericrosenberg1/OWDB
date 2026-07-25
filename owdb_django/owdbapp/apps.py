from django.apps import AppConfig


class OwdbappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "owdb_django.owdbapp"

    def ready(self):
        # Registers the SQLite-directory-writable deploy check (ROS-1204).
        from . import checks  # noqa: F401
