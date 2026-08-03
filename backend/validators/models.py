import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist
from django.db import IntegrityError, models, transaction
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

    GRAFANA_STATUS_CHOICES = [
        ('on', 'On'),
        ('shame', 'Shame'),
        ('unknown', 'Unknown'),
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

    # Overview showcase: hand-pick which validators appear on the public overview
    # and set their assets under management (USD). Edited in admin; not touched by
    # the on-chain sync, so the curated values survive every sync run.
    show_in_overview = models.BooleanField(default=False, db_index=True)
    overview_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first in the overview validators panel.",
    )
    assets_under_management_usd = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True,
        help_text="Assets under management in USD, shown on the overview (e.g. 42600000 → $42.6M).",
    )

    # Grafana observability status (Wall of Shame). Synced by a 5-min cron that
    # mirrors the GenLayer Foundation Grafana dashboard: 'on' if the node
    # reported in the last 5 min, 'shame' if it didn't, 'unknown' before the
    # first sync or when Grafana itself is unreachable.
    metrics_status = models.CharField(
        max_length=10, choices=GRAFANA_STATUS_CHOICES, default='unknown', db_index=True
    )
    logs_status = models.CharField(
        max_length=10, choices=GRAFANA_STATUS_CHOICES, default='unknown', db_index=True
    )
    last_grafana_check_at = models.DateTimeField(null=True, blank=True)
    metrics_shame_started_at = models.DateTimeField(null=True, blank=True)
    logs_shame_started_at = models.DateTimeField(null=True, blank=True)
    version_shame_started_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['address', 'network'], name='unique_wallet_per_network')
        ]

    def __str__(self):
        return f"ValidatorWallet {self.address[:10]}... ({self.network}/{self.status})"


class ValidatorOperatorWallet(BaseModel):
    """
    Operator wallet claimed by a validator profile.

    ValidatorWallet.operator_address comes from chain state. This table stores
    the portal-side first-come-first-served attribution for that operator wallet.
    """
    validator = models.ForeignKey(
        'Validator',
        on_delete=models.CASCADE,
        related_name='operator_wallets',
    )
    address = models.CharField(max_length=42, unique=True, db_index=True)

    class Meta:
        ordering = ['address']

    def save(self, *args, **kwargs):
        if self.address:
            self.address = self.address.lower()
        super().save(*args, **kwargs)

    def matching_wallet_count(self):
        if not self.address:
            return 0
        return ValidatorWallet.objects.filter(operator_address=self.address.lower()).count()

    def __str__(self):
        return f"{self.address} -> {self.validator_id}"


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
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first on the Ecosystem page. Ties fall back to newest-first.",
    )

    def __str__(self):
        asimov = self.node_version_asimov or 'Not set'
        bradbury = self.node_version_bradbury or 'Not set'
        return f"{self.user.email} - Asimov: {asimov}, Bradbury: {bradbury}"


def get_validator_profile(user, *, trust_cached_missing=False):
    """Return a user's Validator profile, falling back to the database.

    Reverse OneToOne lookups can be stale on long-lived User instances after an
    admin action creates the Validator row. Querying by id keeps graduation
    checks authoritative even when the relation cache says "missing".
    """
    user_id = getattr(user, 'id', None)
    if not user_id:
        return None

    try:
        validator_relation = user._meta.get_field('validator')
    except (AttributeError, FieldDoesNotExist):
        validator_relation = None

    if validator_relation is not None and validator_relation.is_cached(user):
        validator = validator_relation.get_cached_value(user)
        if validator is not None or trust_cached_missing:
            return validator

    return Validator.objects.filter(user_id=user_id).first()


def user_has_validator_profile(user):
    return get_validator_profile(user) is not None


def ensure_validator_profile(user):
    user_id = getattr(user, 'id', None)
    if not user_id:
        return None

    try:
        with transaction.atomic():
            validator, _ = Validator.objects.get_or_create(user_id=user_id)
    except IntegrityError:
        validator = Validator.objects.get(user_id=user_id)

    try:
        user._meta.get_field('validator').set_cached_value(user, validator)
    except (AttributeError, FieldDoesNotExist):
        pass

    return validator


class TelegramGroupBindCode(BaseModel):
    """One-time code that binds a Telegram group to a validator via the Deckard bot.

    A validator issues a code from the portal, pastes it in their Telegram
    group, and the Deckard support bot redeems it server-to-server (service
    account scope `telegram_bind:redeem`). One code binds exactly one group;
    a validator may hold multiple active codes (and therefore bind multiple
    groups). DM bindings are refused bot-side.

    The plaintext code is shown exactly once at issuance. Only its SHA-256
    digest is stored, mirroring service_accounts.ServiceAccountToken: lookup is
    by the non-secret `identifier` embedded in the code, then the presented
    digest is compared in constant time.
    """

    CODE_PREFIX = 'tgb_'
    DEFAULT_TTL_HOURS = 48

    STATUS_ISSUED = 'issued'
    STATUS_REDEEMED = 'redeemed'
    STATUS_EXPIRED = 'expired'
    STATUS_REVOKED = 'revoked'
    STATUS_CHOICES = [
        (STATUS_ISSUED, 'Issued'),
        (STATUS_REDEEMED, 'Redeemed'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_REVOKED, 'Revoked'),
    ]

    validator = models.ForeignKey(
        'Validator',
        on_delete=models.CASCADE,
        related_name='telegram_bind_codes',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='telegram_bind_codes',
    )
    identifier = models.CharField(
        max_length=16, unique=True,
        help_text="Non-secret lookup id embedded in the code",
    )
    digest = models.CharField(
        max_length=64, unique=True,
        help_text="SHA-256 digest of the plaintext code (plaintext is never stored)",
    )
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default=STATUS_ISSUED, db_index=True,
    )
    expires_at = models.DateTimeField()
    redeemed_at = models.DateTimeField(null=True, blank=True)
    redeemed_group_chat_id = models.CharField(
        max_length=32, blank=True,
        help_text="Telegram chat id of the bound group (set on redemption)",
    )
    redeemed_by_telegram_uid = models.CharField(
        max_length=32, blank=True,
        help_text="Numeric Telegram user id that redeemed the code (set on redemption)",
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"TelegramGroupBindCode {self.identifier} ({self.status})"

    @staticmethod
    def hash_code(plaintext):
        # Plain SHA-256 (not salted_hmac): the code secret has enough entropy
        # for its 48h single-use lifetime, and this survives SECRET_KEY rotation.
        return hashlib.sha256(plaintext.encode('utf-8')).hexdigest()

    @classmethod
    def identifier_from_plaintext(cls, plaintext):
        """Extract the non-secret lookup identifier from `tgb_<id>_<secret>`."""
        if not plaintext or not plaintext.startswith(cls.CODE_PREFIX):
            return None
        remainder = plaintext[len(cls.CODE_PREFIX):]
        identifier, separator, secret = remainder.partition('_')
        if not separator or not identifier or not secret:
            return None
        return identifier

    @classmethod
    def issue(cls, validator, created_by, ttl_hours=DEFAULT_TTL_HOURS):
        """Create a bind code and return (instance, plaintext)."""
        identifier = secrets.token_hex(6)
        plaintext = f'{cls.CODE_PREFIX}{identifier}_{secrets.token_urlsafe(12)}'
        bind_code = cls.objects.create(
            validator=validator,
            created_by=created_by,
            identifier=identifier,
            digest=cls.hash_code(plaintext),
            expires_at=timezone.now() + timedelta(hours=ttl_hours),
        )
        return bind_code, plaintext

    @property
    def effective_status(self):
        """`status` with lazy expiry: an issued code past expires_at reads expired."""
        if self.status == self.STATUS_ISSUED and self.expires_at <= timezone.now():
            return self.STATUS_EXPIRED
        return self.status

    def is_redeemable(self, now=None):
        now = now or timezone.now()
        return self.status == self.STATUS_ISSUED and self.expires_at > now


class ValidatorWalletStatusSnapshot(BaseModel):
    """
    Daily snapshot of a validator wallet's status.
    Used for uptime lookback logic to determine if a wallet was active
    within a rolling window of days.

    The observability columns (metrics/logs/version status + sample counters +
    node_version) are a per-day rollup of ValidatorWalletObservation rows, latched
    worst-of-day: a dimension is 'shame' if it was shame at ANY observation that day.
    The on-chain `status` column is owned by the on-chain sync; the Grafana sync only
    writes the observability columns (so the two syncs never clobber each other).
    """
    VERSION_STATUS_CHOICES = [
        ('on', 'On'),
        ('warning', 'Warning'),
        ('shame', 'Shame'),
        ('unknown', 'Unknown'),
    ]

    wallet = models.ForeignKey(
        ValidatorWallet,
        on_delete=models.CASCADE,
        related_name='status_snapshots'
    )
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=ValidatorWallet.STATUS_CHOICES)

    # Latched worst-of-day observability verdict (from ValidatorWalletObservation).
    metrics_status = models.CharField(
        max_length=10, choices=ValidatorWallet.GRAFANA_STATUS_CHOICES, default='unknown',
        help_text="Worst-of-day metrics verdict: shame at any observation shames the day"
    )
    logs_status = models.CharField(
        max_length=10, choices=ValidatorWallet.GRAFANA_STATUS_CHOICES, default='unknown',
        help_text="Worst-of-day logs verdict: shame at any observation shames the day"
    )
    version_status = models.CharField(
        max_length=10, choices=VERSION_STATUS_CHOICES, default='unknown',
        help_text="Best-of-day version verdict vs the active target (an upgrade clears the day)"
    )
    node_version = models.CharField(
        max_length=50, blank=True,
        help_text="Last node version observed by the Grafana sync that day"
    )
    metrics_samples = models.PositiveIntegerField(
        default=0,
        help_text="Observations that day where the node was reporting metrics"
    )
    logs_samples = models.PositiveIntegerField(
        default=0,
        help_text="Observations that day where the node was reporting logs"
    )

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(fields=['wallet', 'date'], name='unique_snapshot_per_wallet_date')
        ]

    def __str__(self):
        return f"{self.wallet.address[:10]}... {self.date} ({self.status})"


class ValidatorWalletObservation(BaseModel):
    """
    Append-only log of a single Grafana-sync observation for a validator wallet.

    One row is written per active wallet per Grafana sync run, capturing the
    point-in-time observability verdict plus the on-chain status and the node
    version reported to Prometheus. This is the raw source of truth from which the
    daily ValidatorWalletStatusSnapshot rollup is materialised (and rebuildable).
    """
    wallet = models.ForeignKey(
        ValidatorWallet,
        on_delete=models.CASCADE,
        related_name='observations'
    )
    observed_at = models.DateTimeField(
        db_index=True,
        help_text="When the Grafana sync recorded this observation"
    )
    onchain_status = models.CharField(
        max_length=20, choices=ValidatorWallet.STATUS_CHOICES,
        help_text="Wallet's on-chain status at observation time"
    )
    metrics_status = models.CharField(
        max_length=10, choices=ValidatorWallet.GRAFANA_STATUS_CHOICES,
        help_text="Whether the node was reporting metrics at this observation"
    )
    logs_status = models.CharField(
        max_length=10, choices=ValidatorWallet.GRAFANA_STATUS_CHOICES,
        help_text="Whether the node was reporting logs at this observation"
    )
    version_status = models.CharField(
        max_length=10, choices=ValidatorWalletStatusSnapshot.VERSION_STATUS_CHOICES, default='unknown',
        help_text="Version verdict vs the active target at this observation"
    )
    node_version = models.CharField(
        max_length=50, blank=True,
        help_text="Node version reported to Prometheus at this observation"
    )

    class Meta:
        ordering = ['-observed_at']
        indexes = [
            models.Index(fields=['wallet', 'observed_at']),
        ]

    def __str__(self):
        return f"{self.wallet.address[:10]}... @ {self.observed_at:%Y-%m-%d %H:%M} ({self.metrics_status}/{self.logs_status})"


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
