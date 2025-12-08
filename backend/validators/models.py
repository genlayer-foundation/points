from django.db import models
from django.conf import settings
from django.utils import timezone
from utils.models import BaseModel
from .node_version import NodeVersionMixin


class ValidatorWallet(BaseModel):
    """
    Represents a validator wallet contract from GenLayer.
    An operator (Validator model) can have multiple validator wallets.
    Data is synced from GenLayer via cron job every 5 minutes.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('quarantined', 'Quarantined'),  # Temporarily banned
        ('banned', 'Banned'),            # Permanently banned
        ('inactive', 'Inactive'),        # Not in any list, no longer active
    ]

    address = models.CharField(max_length=42, unique=True, db_index=True)
    operator = models.ForeignKey(
        'Validator',
        on_delete=models.CASCADE,
        related_name='validator_wallets',
        null=True,
        blank=True
    )
    operator_address = models.CharField(max_length=42, db_index=True, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Metadata from getIdentity() - stored but not displayed yet
    moniker = models.CharField(max_length=255, blank=True)
    logo_uri = models.URLField(blank=True, max_length=500)
    website = models.URLField(blank=True, max_length=500)
    description = models.TextField(blank=True)

    # Stake info from validatorView()
    v_stake = models.CharField(max_length=78, blank=True)  # Self stake
    d_stake = models.CharField(max_length=78, blank=True)  # Delegated stake

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"ValidatorWallet {self.address[:10]}... ({self.status})"


class Validator(NodeVersionMixin, BaseModel):
    """
    Represents a validator with their node version information.
    One-to-one relationship with User.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='validator'
    )
    # node_version field is inherited from NodeVersionMixin
    
    def __str__(self):
        return f"{self.user.email} - Node: {self.node_version or 'Not set'}"
    
    # Methods clean_version, version_matches_or_higher, and save are inherited from NodeVersionMixin