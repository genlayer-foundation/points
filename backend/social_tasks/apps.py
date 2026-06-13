from django.apps import AppConfig
from django.db.models.signals import post_save


class SocialTasksConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_tasks'
    verbose_name = 'Social Tasks'

    def ready(self):
        from leaderboard.models import update_leaderboard_on_social_task_completion
        from .models import SocialTaskCompletion

        post_save.connect(
            update_leaderboard_on_social_task_completion,
            sender=SocialTaskCompletion,
            dispatch_uid='social_tasks.update_leaderboard_on_social_task_completion',
        )
