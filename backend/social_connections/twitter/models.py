"""
Twitter/X OAuth connection model.
"""
from django.db import models
from social_connections.models import SocialConnection


class TwitterConnection(SocialConnection):
    """
    Twitter/X OAuth connection.

    Stores the user's Twitter account information obtained through OAuth 2.0 with PKCE.
    """
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='twitter_connection'
    )

    class Meta:
        verbose_name = 'Twitter Connection'
        verbose_name_plural = 'Twitter Connections'
