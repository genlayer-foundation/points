from django.apps import AppConfig


class LeaderboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leaderboard'

    def ready(self):
        from django.db.models.signals import post_save
        from leaderboard.models import update_leaderboard_on_builder_creation

        Builder = self.apps.get_model('builders', 'Builder')
        post_save.connect(update_leaderboard_on_builder_creation, sender=Builder)
