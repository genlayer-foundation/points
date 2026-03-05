"""
Discord OAuth connection model.
"""
from django.db import models
from social_connections.models import SocialConnection


class DiscordConnection(SocialConnection):
    """
    Discord OAuth connection.

    Stores the user's Discord account information obtained through OAuth 2.0.
    Includes Discord-specific fields like discriminator and avatar hash.
    """
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='discord_connection'
    )
    discriminator = models.CharField(
        max_length=10,
        blank=True,
        help_text="Discord discriminator (legacy - newer accounts may not have this)"
    )
    avatar_hash = models.CharField(
        max_length=100,
        blank=True,
        help_text="Discord avatar hash for constructing avatar URL"
    )

    class Meta:
        verbose_name = 'Discord Connection'
        verbose_name_plural = 'Discord Connections'

    @property
    def avatar_url(self):
        """Construct the Discord avatar URL from the avatar hash."""
        if not self.avatar_hash or not self.platform_user_id:
            return None
        return f"https://cdn.discordapp.com/avatars/{self.platform_user_id}/{self.avatar_hash}.png"
