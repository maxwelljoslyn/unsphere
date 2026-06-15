from django.apps import AppConfig


class GemsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gems"

    def ready(self):
        # Importing the definitions module registers every GemRuleDef into the
        # global registry.
        from . import definitions  # noqa: F401
