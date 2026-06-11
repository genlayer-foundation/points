from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from utils.models import BaseModel


class SocialTask(BaseModel):
    """A repeatable social action that awards points (separate from Contributions).

    Three layers, one row:
    - Category (FK) — drives UI surface label and which leaderboard the points feed.
    - Verification logic (`verification_type`) — slug of a registered Verifier.
    - Specifics — typed target_* fields. Each verifier declares which it needs.

    Admins create tasks via Django admin. Completion is recorded by
    `SocialTaskCompletion`, which `leaderboard.models.calculate_category_points`
    sums alongside contributions.
    """

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    category = models.ForeignKey(
        'contributions.Category',
        on_delete=models.PROTECT,
        related_name='social_tasks',
    )
    points = models.PositiveIntegerField(
        default=10,
        help_text='Points awarded on completion. Frozen as points_awarded on each completion row.',
    )

    # Verification logic: matches a registered Verifier in social_tasks.verifiers.
    # Choices come from the registry at admin-render time (no static choices=).
    verification_type = models.CharField(max_length=32)

    # Typed "specifics" — each verifier reads what it needs.
    # Add more fields here as new verifiers land (e.g. target_repo when
    # github_star is implemented).
    target_handle = models.CharField(
        max_length=64,
        blank=True,
        help_text='X / Twitter handle without @. Used by: twitter_follow.',
    )
    target_guild_id = models.CharField(
        max_length=64,
        blank=True,
        help_text=(
            'Discord server (guild) id. Used by: discord_guild_join. '
            'Falls back to settings.DISCORD_GUILD_ID when blank.'
        ),
    )
    target_repo = models.CharField(
        max_length=140,
        blank=True,
        help_text='GitHub repository as owner/repo (e.g. genlayer-foundation/points). Used by: github_star.',
    )

    action_url = models.URLField(help_text='External URL the user is sent to on click.')
    cta_text = models.CharField(max_length=50, default='Complete')

    # Derived from the verifier in save(); not admin-editable.
    platform = models.CharField(max_length=20, default='generic', editable=False)

    is_active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name

    def is_currently_active(self, now=None):
        now = now or timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True

    def clean(self):
        super().clean()
        # Lazy import — verifiers depend on Django being set up.
        from .verifiers import get_verifier

        verifier = get_verifier(self.verification_type)
        if verifier is None:
            raise ValidationError({
                'verification_type': f'Unknown verification type: {self.verification_type!r}'
            })

        errors = {}
        for field_name in verifier.required_fields:
            if not getattr(self, field_name, '').strip():
                errors[field_name] = (
                    f'Required for verification type {verifier.verification_type!r}.'
                )
        if not errors:
            errors = verifier.clean_task(self)
        if errors:
            raise ValidationError(errors)

        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({
                'ends_at': 'Must be after starts_at — an inverted window is never active.'
            })

    def save(self, *args, **kwargs):
        from .verifiers import platform_for

        self.platform = platform_for(self.verification_type)
        super().save(*args, **kwargs)


class SocialTaskCompletion(BaseModel):
    """A single user's completion of a SocialTask. One row per (user, task)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='social_task_completions',
    )
    task = models.ForeignKey(
        SocialTask,
        on_delete=models.PROTECT,
        related_name='completions',
    )

    points_awarded = models.PositiveIntegerField(
        help_text='Snapshot of task.points at completion time. Frozen.',
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    # Snapshot of task.verification_type at completion time so the audit row
    # stays meaningful even if the task is later reconfigured.
    verification_type = models.CharField(max_length=32)
    verification_data = models.JSONField(default=dict, blank=True)

    class Meta:
        # unique_together already creates a (user, task) index; no extra
        # index needed for that pair.
        unique_together = ('user', 'task')
        indexes = [
            models.Index(fields=['task', 'completed_at']),
        ]

    def __str__(self):
        return f'{self.user} -> {self.task} ({self.points_awarded} pts)'
