from django.apps import AppConfig


class CommunityXpConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'community_xp'
    verbose_name = 'Community XP'

    def ready(self):
        from . import signals  # noqa: F401
