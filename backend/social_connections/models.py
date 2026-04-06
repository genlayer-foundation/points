import logging
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)


class SocialConnection(models.Model):
    """Abstract base model for social platform OAuth connections."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)s',
    )
    platform_user_id = models.CharField(max_length=100, help_text="Platform's unique user ID")
    platform_username = models.CharField(max_length=100, help_text="Username on the platform")
    access_token = models.TextField(blank=True, help_text="Encrypted OAuth access token")
    refresh_token = models.TextField(blank=True, help_text="Encrypted OAuth refresh token")
    linked_at = models.DateTimeField(help_text="When the account was linked")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.platform_username} ({self.user})"


class GitHubConnection(SocialConnection):
    class Meta:
        db_table = 'social_connections_github'
        verbose_name = 'GitHub Connection'
        verbose_name_plural = 'GitHub Connections'


class TwitterConnection(SocialConnection):
    class Meta:
        db_table = 'social_connections_twitter'
        verbose_name = 'Twitter Connection'
        verbose_name_plural = 'Twitter Connections'


class DiscordConnection(SocialConnection):
    discriminator = models.CharField(max_length=10, blank=True, help_text="Discord discriminator (legacy)")
    avatar_hash = models.CharField(max_length=100, blank=True, help_text="Discord avatar hash for CDN URL")
    guild_member = models.BooleanField(default=False, help_text="Whether user is in the configured Discord guild")
    guild_checked_at = models.DateTimeField(null=True, blank=True, help_text="When guild membership was last checked")

    @property
    def avatar_url(self):
        if not self.avatar_hash or not self.platform_user_id:
            return None
        return f"https://cdn.discordapp.com/avatars/{self.platform_user_id}/{self.avatar_hash}.png"

    class Meta:
        db_table = 'social_connections_discord'
        verbose_name = 'Discord Connection'
        verbose_name_plural = 'Discord Connections'


class UsedOAuthCode(models.Model):
    """Tracks used OAuth authorization codes to prevent replay attacks.
    DB-backed for multi-worker safety (replaces in-memory dict)."""

    code = models.CharField(max_length=512)
    platform = models.CharField(max_length=20)
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'social_connections_used_codes'
        unique_together = ('code', 'platform')
        indexes = [
            models.Index(fields=['used_at']),
        ]

    @classmethod
    def mark_used(cls, code, platform):
        """Mark an OAuth code as used. Returns True if newly marked, False if already used."""
        from django.db import IntegrityError
        try:
            _, created = cls.objects.get_or_create(
                code=code,
                platform=platform,
            )
            return created
        except IntegrityError:
            # Concurrent request already inserted this code
            return False

    @classmethod
    def cleanup_old(cls, minutes=10):
        """Delete codes older than the specified minutes."""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        deleted, _ = cls.objects.filter(used_at__lt=cutoff).delete()
        if deleted:
            logger.debug(f"Cleaned up {deleted} expired OAuth codes")
        return deleted
