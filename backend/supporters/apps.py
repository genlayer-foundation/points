from django.apps import AppConfig


class SupportersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'supporters'  # Module path (must match folder name)
    label = 'creators'   # App label for migrations and database (keeps compatibility)
