from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        """Initialize DRF tracing when the app is ready."""
        from tally.middleware.drf_tracing import install_drf_tracing
        install_drf_tracing()
