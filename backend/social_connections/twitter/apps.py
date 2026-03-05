from django.apps import AppConfig


class TwitterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_connections.twitter'
    label = 'social_twitter'
    verbose_name = 'Twitter Connection'
