from django.apps import AppConfig


class DiscordConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_connections.discord'
    label = 'social_discord'
    verbose_name = 'Discord Connection'
