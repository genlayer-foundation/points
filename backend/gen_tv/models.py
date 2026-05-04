from django.db import models
from django.utils import timezone

from utils.models import BaseModel


class Stream(BaseModel):
    """A livestream entry shown on Gen TV (mostly X / Twitter, for now)."""

    class Category(models.TextChoices):
        INTERNAL = 'internal', 'GenLayer Team'
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
        help_text="Thumbnail / cover image URL.",
    )
    starts_at = models.DateTimeField(
        help_text="Scheduled start time (used for sorting and status).",
    )
    ends_at = models.DateTimeField(
        help_text="Scheduled end time (used to compute status and the duration badge).",
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-starts_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    @property
    def status(self):
        now = timezone.now()
        if now < self.starts_at:
            return self.UPCOMING
        if now < self.ends_at:
            return self.LIVE
        return self.PAST
