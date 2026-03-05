"""
GitHub OAuth connection model.
"""
from django.db import models
from social_connections.models import SocialConnection


class GitHubConnection(SocialConnection):
    """
    GitHub OAuth connection.

    Stores the user's GitHub account information obtained through OAuth.
    """
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='github_connection'
    )

    class Meta:
        verbose_name = 'GitHub Connection'
        verbose_name_plural = 'GitHub Connections'
