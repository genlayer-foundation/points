import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db import models
from django.utils import timezone

from utils.models import BaseModel

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
    current_roles = models.ManyToManyField(
        'DiscordRole',
        blank=True,
        related_name='discord_connections',
        help_text="Current roles for this user in the configured Discord guild",
    )
    roles_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When Discord roles were last synced",
    )
    roles_sync_error = models.TextField(
        blank=True,
        help_text="Most recent Discord role sync error, if any",
    )
    roles_manual_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this user last manually refreshed Discord roles",
    )
    guild_joined_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the user joined the configured Discord guild",
    )
    guild_nick = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nickname in the configured Discord guild",
    )

    @property
    def avatar_url(self):
        if not self.avatar_hash or not self.platform_user_id:
            return None
        return f"https://cdn.discordapp.com/avatars/{self.platform_user_id}/{self.avatar_hash}.png"

    class Meta:
        db_table = 'social_connections_discord'
        verbose_name = 'Discord Connection'
        verbose_name_plural = 'Discord Connections'


class TelegramConnection(SocialConnection):
    """Verified Telegram account link, created via the bot's /start deep link.

    Owner-only data: never exposed through public serializers. For private
    chats Telegram's chat id equals the user id, so `platform_user_id` doubles
    as the chat id for outbound sends. Telegram bots receive no user tokens,
    so the inherited access/refresh token fields stay blank.
    """

    notifications_enabled = models.BooleanField(
        default=True,
        help_text="Whether portal notifications are pushed to this Telegram account (/mute toggles this)",
    )
    blocked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set when Telegram reports the user blocked the bot; cleared on a successful re-link",
    )

    class Meta:
        db_table = 'social_connections_telegram'
        verbose_name = 'Telegram Connection'
        verbose_name_plural = 'Telegram Connections'
        constraints = [
            # Inbound commands route portal accounts by Telegram id, so one
            # Telegram account can only ever be linked to one portal user.
            # The /start handler's friendly pre-check is racy on its own;
            # this makes the invariant DB-enforced.
            models.UniqueConstraint(
                fields=['platform_user_id'],
                name='uniq_telegram_platform_user_id',
            ),
        ]


class TelegramMessage(BaseModel):
    """Telegram message log and delivery outbox in one table.

    Inbound rows (direction='in') are a permanent conversation log. Outbound
    rows are either interactive replies recorded after the fact, or
    notification deliveries enqueued as status='pending' and drained by the
    cron-triggered delivery endpoint.
    """

    DIRECTION_IN = 'in'
    DIRECTION_OUT = 'out'
    DIRECTION_CHOICES = [
        (DIRECTION_IN, 'Inbound'),
        (DIRECTION_OUT, 'Outbound'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_SENDING = 'sending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENDING, 'Sending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
    ]

    direction = models.CharField(max_length=3, choices=DIRECTION_CHOICES)
    connection = models.ForeignKey(
        TelegramConnection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='messages',
    )
    chat_id = models.CharField(
        max_length=64,
        help_text="Telegram chat id at the time of the message (historical record; "
                  "the drain sends to the connection's live platform_user_id)",
    )
    text = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        blank=True,
        default='',
        help_text="Delivery status for outbound rows; blank for inbound rows",
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    notification = models.ForeignKey(
        'notifications.Notification',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='telegram_messages',
    )
    error = models.CharField(max_length=200, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'social_connections_telegram_message'
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['direction', '-created_at']),
        ]
        constraints = [
            # One delivery per (notification, connection): makes every enqueue
            # idempotent, so re-broadcasts and campaign resends never double-send.
            models.UniqueConstraint(
                fields=['notification', 'connection'],
                condition=models.Q(
                    direction='out',
                    notification__isnull=False,
                    connection__isnull=False,
                ),
                name='uniq_telegram_out_per_notification',
            ),
        ]

    def __str__(self):
        return f"TelegramMessage({self.direction}, chat={self.chat_id}, status={self.status or 'n/a'})"


class DiscordRole(models.Model):
    """Cached Discord guild role metadata."""

    guild_id = models.CharField(max_length=100, db_index=True)
    role_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    color = models.PositiveIntegerField(default=0)
    position = models.IntegerField(default=0)
    hoist = models.BooleanField(default=False)
    managed = models.BooleanField(default=False)
    mentionable = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def color_hex(self):
        return f"#{self.color:06x}"

    def __str__(self):
        return f"{self.name} ({self.guild_id}/{self.role_id})"

    class Meta:
        db_table = 'social_connections_discord_role'
        unique_together = ('guild_id', 'role_id')
        ordering = ['guild_id', '-position', 'name']
        indexes = [
            models.Index(fields=['guild_id', 'deleted_at']),
            models.Index(fields=['role_id']),
        ]


class DiscordRoleSyncLock(models.Model):
    """Database-backed lock for scheduled Discord role syncs."""

    name = models.CharField(max_length=100, unique=True)
    owner_token = models.CharField(max_length=32, null=True, blank=True, db_index=True)
    acquired_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'social_connections_discord_role_sync_lock'

    def __str__(self):
        return f"DiscordRoleSyncLock({self.name}, acquired={self.acquired_at})"


class DiscordEarnedRoleAssignment(BaseModel):
    """Append-only record of an earned Discord role granted by the portal."""

    connection = models.ForeignKey(
        DiscordConnection,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='earned_role_assignments',
    )
    discord_user_id = models.CharField(max_length=100, db_index=True)
    discord_username = models.CharField(max_length=100, blank=True)
    role_id = models.CharField(max_length=100, db_index=True)
    role_name = models.CharField(max_length=100)
    total_points = models.PositiveIntegerField()
    poap_count = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'social_connections_discord_earned_role_assignment'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.discord_username or self.discord_user_id}: {self.role_name}"


class PendingOAuthState(models.Model):
    """Short-lived OAuth state data stored server-side for multi-worker safety."""

    state_id = models.CharField(max_length=64, unique=True)
    platform = models.CharField(max_length=20, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    code_verifier = models.TextField(blank=True)
    redirect_url = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'social_connections_pending_oauth_state'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['platform', 'state_id']),
            models.Index(fields=['platform', 'session_key']),
        ]

    @classmethod
    def consume(cls, state_id, platform, user_id, session_key, max_age_minutes=10):
        """Atomically consume a pending OAuth state row and return it."""
        if not session_key:
            return None
        cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
        with transaction.atomic():
            pending = (
                cls.objects
                .select_for_update()
                .filter(
                    state_id=state_id,
                    platform=platform,
                    user_id=user_id,
                    session_key=session_key,
                    consumed_at__isnull=True,
                    created_at__gte=cutoff,
                )
                .first()
            )
            if not pending:
                return None

            pending.consumed_at = timezone.now()
            pending.save(update_fields=['consumed_at'])
            return pending

    @classmethod
    def consume_deep_link(cls, state_id, platform, max_age_minutes=10):
        """Atomically consume a state row for cross-channel deep-link flows.

        Unlike consume(), there is deliberately no user or session binding:
        the Telegram /start webhook is the consumer, which runs outside any
        browser session, and the token itself identifies the issuing user.
        The unguessable one-time token is the sole credential.
        """
        cutoff = timezone.now() - timedelta(minutes=max_age_minutes)
        with transaction.atomic():
            pending = (
                cls.objects
                .select_for_update()
                .filter(
                    state_id=state_id,
                    platform=platform,
                    consumed_at__isnull=True,
                    created_at__gte=cutoff,
                )
                .first()
            )
            if not pending:
                return None

            pending.consumed_at = timezone.now()
            pending.save(update_fields=['consumed_at'])
            return pending

    @classmethod
    def cleanup_old(cls, minutes=10, platform=None):
        """Delete expired rows, scoped to one platform.

        Flows use different lifetimes (Telegram deep-link tokens live longer
        than OAuth states), so each flow must only sweep its own platform;
        an unscoped 10-minute sweep would expire Telegram tokens early.
        """
        cutoff = timezone.now() - timedelta(minutes=minutes)
        queryset = cls.objects.filter(created_at__lt=cutoff)
        if platform:
            queryset = queryset.filter(platform=platform)
        deleted, _ = queryset.delete()
        if deleted:
            logger.debug(f"Cleaned up {deleted} expired pending OAuth states")
        return deleted

    def __str__(self):
        return f"PendingOAuthState({self.platform}, user={self.user_id})"


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
