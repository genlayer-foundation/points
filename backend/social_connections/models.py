"""
Abstract base model for social connections.
"""
from django.db import models
from django.conf import settings
from utils.models import BaseModel


class SocialConnection(BaseModel):
    """
    Abstract base model for social connections.

    Provides common fields for storing OAuth connection data across
    different social platforms (GitHub, Twitter, Discord, etc.).
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)s'
    )
    username = models.CharField(
        max_length=100,
        blank=True,
        help_text="Platform username"
    )
    platform_user_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Platform user ID for unique identification"
    )
    access_token = models.TextField(
        blank=True,
        help_text="Encrypted access token"
    )
    refresh_token = models.TextField(
        blank=True,
        help_text="Encrypted refresh token (if applicable)"
    )
    linked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the account was linked"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__}: {self.username or self.platform_user_id}"
