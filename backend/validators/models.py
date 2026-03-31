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

    NETWORK_CHOICES = [
        ('asimov', 'Asimov'),
        ('bradbury', 'Bradbury'),
    ]

    address = models.CharField(max_length=42, db_index=True)
    network = models.CharField(max_length=20, choices=NETWORK_CHOICES, default='asimov', db_index=True)
    operator = models.ForeignKey(
        'Validator',
        on_delete=models.CASCADE,
        related_name='validator_wallets',
        null=True,
        blank=True
    )
    operator_address = models.CharField(max_length=42, db_index=True)
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
        constraints = [
            models.UniqueConstraint(fields=['address', 'network'], name='unique_wallet_per_network')
        ]

    def __str__(self):
        return f"ValidatorWallet {self.address[:10]}... ({self.network}/{self.status})"


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
    # node_version_asimov and node_version_bradbury fields are inherited from NodeVersionMixin

    def __str__(self):
        asimov = self.node_version_asimov or 'Not set'
        bradbury = self.node_version_bradbury or 'Not set'
        return f"{self.user.email} - Asimov: {asimov}, Bradbury: {bradbury}"


class ValidatorWalletStatusSnapshot(BaseModel):
    """
    Daily snapshot of a validator wallet's status.
    Used for uptime lookback logic to determine if a wallet was active
    within a rolling window of days.
    """
    wallet = models.ForeignKey(
        ValidatorWallet,
        on_delete=models.CASCADE,
        related_name='status_snapshots'
    )
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=ValidatorWallet.STATUS_CHOICES)

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['wallet', 'date'], name='unique_snapshot_per_wallet_date')
        ]

    def __str__(self):
        return f"{self.wallet.address[:10]}... {self.date} ({self.status})"


class SyncLock(models.Model):
    """
    Database-backed advisory lock for cross-process sync coordination.
    Stores an ownership token so only the sync that acquired the lock can
    release it, and tracks heartbeats so long-running syncs are not mistaken
    for stale work.
    """
    name = models.CharField(max_length=100, unique=True)
    owner_token = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    acquired_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'validators_sync_lock'

    def __str__(self):
        return f"SyncLock({self.name}, acquired={self.acquired_at})"
