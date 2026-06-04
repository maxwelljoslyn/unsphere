from django.apps import AppConfig


class AchievementsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "achievements"

    def ready(self):
        # Importing the definitions module registers every AchievementDef
        # into the global registry.
        from . import definitions  # noqa: F401
