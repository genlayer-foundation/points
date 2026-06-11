from django.conf import settings
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
    ]

    AUDIENCE_ALL = 'all'
    AUDIENCE_VALIDATORS = 'validators'
    AUDIENCE_STEWARDS = 'stewards'
    AUDIENCE_CHOICES = [
        (AUDIENCE_ALL, 'All users'),
        (AUDIENCE_VALIDATORS, 'Validators'),
        (AUDIENCE_STEWARDS, 'Stewards'),
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
