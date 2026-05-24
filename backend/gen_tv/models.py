from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from utils.models import BaseModel


class StreamCategory(BaseModel):
    """Detailed category that can be assigned to Gen TV streams."""

    class Group(models.TextChoices):
        INTERNAL = 'internal', 'Internal team'
        COMMUNITY = 'community', 'Community'

    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    group = models.CharField(max_length=20, choices=Group.choices)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'stream category'
        verbose_name_plural = 'stream categories'

    def __str__(self):
        return f"{self.name} ({self.get_group_display()})"


class Stream(BaseModel):
    """A livestream entry shown on Gen TV (mostly X / Twitter, for now)."""

    class Category(models.TextChoices):
        INTERNAL = 'internal', 'Internal team'
        COMMUNITY = 'community', 'Community'

    # Status is derived, not stored — see the `status` property below.
    UPCOMING = 'upcoming'
    LIVE = 'live'
    PAST = 'past'

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    description = models.TextField(blank=True)
    url = models.URLField(
        max_length=500,
        help_text="Source URL (X / Twitter, YouTube, etc.).",
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Cloudinary URL for thumbnail / cover image.",
    )
    image_public_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Cloudinary public ID for thumbnail / cover image.",
    )
    starts_at = models.DateTimeField(
        help_text="Scheduled start time (used for sorting and status).",
    )
    ends_at = models.DateTimeField(
        help_text="Scheduled end time (used to compute status and the duration badge).",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    detailed_category = models.ForeignKey(
        StreamCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='streams',
        help_text="Optional detailed category for filtering Gen TV.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    def clean(self):
        super().clean()
        if self.detailed_category and self.detailed_category.group != self.category:
            raise ValidationError({
                'detailed_category': (
                    "Detailed category must belong to the selected broader category."
                ),
            })

    @property
    def status(self):
        now = timezone.now()
        if now < self.starts_at:
            return self.UPCOMING
        if now < self.ends_at:
            return self.LIVE
        return self.PAST
