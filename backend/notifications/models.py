from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from utils.models import BaseModel


class Notification(BaseModel):
    """A portal notification.

    Personal notifications have a recipient. Broadcast notifications have
    recipient=None and are visible to every user in `audience` who joined
    before the notification was created; their per-user read state lives in
    NotificationReceipt rows created lazily when a user reads them.
    """

    PRIORITY_LOW = 1
    PRIORITY_NORMAL = 2
    PRIORITY_HIGH = 3
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
    ]

    CATEGORY_CHOICES = [
        ('submission', 'Submission'),
        ('contribution', 'Contribution'),
        ('community', 'Community'),
        ('content', 'Content'),
        ('validator', 'Validator'),
        ('system', 'System'),
        ('announcement', 'Announcement'),
    ]

    AUDIENCE_ALL = 'all'
    AUDIENCE_VALIDATORS = 'validators'
    AUDIENCE_STEWARDS = 'stewards'
    AUDIENCE_BUILDERS = 'builders'
    AUDIENCE_COMMUNITY = 'community'
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, 'All users'),
        (AUDIENCE_VALIDATORS, 'Validators'),
        (AUDIENCE_STEWARDS, 'Stewards'),
        (AUDIENCE_BUILDERS, 'Builders'),
        (AUDIENCE_COMMUNITY, 'Creators'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text='Empty for broadcast notifications.',
    )
    audience = models.CharField(
        max_length=16,
        choices=AUDIENCE_CHOICES,
        default=AUDIENCE_ALL,
        db_index=True,
        help_text='Only meaningful for broadcast notifications.',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications_sent',
    )
    event_type = models.CharField(max_length=80, db_index=True)
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, db_index=True)
    priority = models.PositiveSmallIntegerField(
        choices=PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
    )
    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    link_url = models.CharField(max_length=500, blank=True)
    link_label = models.CharField(max_length=80, blank=True)
    source_app = models.CharField(max_length=80, blank=True)
    source_model = models.CharField(max_length=80, blank=True)
    source_object_id = models.CharField(max_length=120, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=255, null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True, help_text='Personal notifications only.')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'read_at']),
            models.Index(
                fields=['audience', '-created_at'],
                condition=models.Q(recipient__isnull=True),
                name='notif_broadcast_feed_idx',
            ),
        ]
        constraints = [
            # Dedupe keys are scoped per recipient (and separately for
            # broadcasts) so a key collision between producers can never
            # reassign another user's notification.
            models.UniqueConstraint(
                fields=['recipient', 'dedupe_key'],
                condition=models.Q(recipient__isnull=False, dedupe_key__isnull=False),
                name='unique_personal_dedupe_per_recipient',
            ),
            models.UniqueConstraint(
                fields=['dedupe_key'],
                condition=models.Q(recipient__isnull=True, dedupe_key__isnull=False),
                name='unique_broadcast_dedupe',
            ),
        ]

    def __str__(self):
        target = self.recipient or f'broadcast:{self.audience}'
        return f"{self.title} -> {target}"

    @property
    def is_broadcast(self):
        return self.recipient_id is None

    def mark_read(self):
        """Mark a personal notification as read. Broadcast read state uses receipts."""
        if self.recipient_id is not None and not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at', 'updated_at'])


class NotificationReceipt(BaseModel):
    """Lazy per-user read state for broadcast notifications."""

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='receipts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_receipts',
    )
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['notification', 'user'], name='unique_notification_receipt'),
        ]

    def __str__(self):
        return f"receipt {self.notification_id} -> {self.user_id}"


def default_channels():
    return ['portal']


class CustomNotification(BaseModel):
    """An admin-composed campaign: arbitrary copy targeted at a set of users.

    Sending fans out personal Notification rows (one per resolved recipient,
    snapshot semantics) via notifications.campaigns.send_campaign. The
    `channels` field is the foundation for future email/Telegram delivery;
    only the portal channel delivers today.
    """

    TARGET_EVERYONE = 'everyone'
    TARGET_ROLES = 'roles'
    TARGET_USERS = 'users'
    TARGET_WALLETS = 'wallets'
    TARGET_MODE_CHOICES = [
        (TARGET_EVERYONE, 'Everyone'),
        (TARGET_ROLES, 'Users with selected roles'),
        (TARGET_USERS, 'Hand-picked users'),
        (TARGET_WALLETS, 'Pasted wallet addresses'),
    ]

    ROLE_CHOICES = [
        ('builders', 'Builders'),
        ('validators', 'Validators'),
        ('stewards', 'Stewards'),
        ('creators', 'Creators'),
    ]

    STATUS_DRAFT = 'draft'
    STATUS_SENT = 'sent'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SENT, 'Sent'),
    ]

    # Message copy. Field shapes mirror Notification so the frozen copy
    # never truncates on fan-out.
    title = models.CharField(max_length=180)
    body = models.TextField(
        blank=True,
        help_text='Supports markdown on the notifications page; shown as plain text in the dropdown preview.',
    )
    link_url = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Optional. Internal portal path ('/missions') or full https:// URL. "
            'Leave empty for a pure announcement with no redirect.'
        ),
    )
    link_label = models.CharField(max_length=80, blank=True)
    priority = models.PositiveSmallIntegerField(
        choices=Notification.PRIORITY_CHOICES,
        default=Notification.PRIORITY_NORMAL,
    )

    # Targeting
    target_mode = models.CharField(max_length=16, choices=TARGET_MODE_CHOICES, default=TARGET_EVERYONE)
    target_roles = models.JSONField(default=list, blank=True)
    target_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='custom_notifications_targeted',
    )
    target_wallets = models.TextField(
        blank=True,
        help_text='One wallet address per line. Commas and extra whitespace are tolerated.',
    )

    # Delivery record
    channels = models.JSONField(default=default_channels)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_notifications_sent',
    )
    sent_count = models.PositiveIntegerField(default=0, help_text='Resolved recipients at last send.')
    unmatched_wallets = models.JSONField(
        default=list,
        blank=True,
        help_text='Wallet lines that matched no user at last send.',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'custom notification'

    def __str__(self):
        return f"{self.title} ({self.get_target_mode_display()}, {self.status})"

    @property
    def dedupe_key(self):
        return f"custom.announcement:{self.pk}"


class WhatsNewAnnouncement(BaseModel):
    """Curated product announcement shown in the What's New dialog.

    This is intentionally separate from Notification: regular feed items are
    operational/user events, while these records are authored product updates.
    """

    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    title = models.CharField(max_length=180)
    body = models.TextField(blank=True)
    eyebrow = models.CharField(max_length=80, blank=True, default="What's new")
    link_url = models.CharField(max_length=500, blank=True)
    link_label = models.CharField(max_length=80, blank=True)

    image_url = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for the dialog image.')
    image_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for the dialog image.')
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    audience = models.CharField(
        max_length=16,
        choices=Notification.AUDIENCE_CHOICES,
        default=Notification.AUDIENCE_ALL,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['display_order', '-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'audience', 'display_order']),
            models.Index(fields=['status', 'published_at']),
        ]
        verbose_name = "What's New announcement"
        verbose_name_plural = "What's New announcements"

    def __str__(self):
        return f"{self.title} v{self.version} ({self.status})"

    def clean(self):
        super().clean()
        if self.link_label and not self.link_url:
            raise ValidationError({'link_label': 'A link label needs a link URL.'})
        if self.status == self.STATUS_PUBLISHED and not self.published_at:
            raise ValidationError({'published_at': 'Published announcements need a publish time.'})
        if self.expires_at and self.published_at and self.expires_at <= self.published_at:
            raise ValidationError({'expires_at': 'Expiration must be after publish time.'})

    def publish(self):
        self.status = self.STATUS_PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()

    def archive(self):
        self.status = self.STATUS_ARCHIVED

    def bump_version(self):
        self.version += 1


class WhatsNewAnnouncementSeen(BaseModel):
    """Per-user seen state for a specific What's New announcement version."""

    ACTION_SEEN = 'seen'
    ACTION_SKIPPED = 'skipped'
    ACTION_OPENED = 'opened'
    ACTION_CHOICES = [
        (ACTION_SEEN, 'Seen'),
        (ACTION_SKIPPED, 'Skipped'),
        (ACTION_OPENED, 'Opened link'),
    ]

    announcement = models.ForeignKey(
        WhatsNewAnnouncement,
        on_delete=models.CASCADE,
        related_name='seen_records',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='whats_new_seen',
    )
    version = models.PositiveIntegerField()
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default=ACTION_SEEN)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user', 'version'],
                name='unique_whats_new_seen_version',
            ),
        ]
        indexes = [
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user_id} saw {self.announcement_id} v{self.version}"
