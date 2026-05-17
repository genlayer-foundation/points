from django.apps import AppConfig


class PoapsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'poaps'

    def ready(self):
        import poaps.signals  # noqa: F401

