from django.apps import AppConfig


class GitHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_connections.github'
    label = 'social_github'
    verbose_name = 'GitHub Connection'
