from django.db import models

from utils.models import BaseModel


class Partner(BaseModel):
    """An ecosystem partner organization featured in the public partners directory."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(max_length=500, blank=True, help_text="Cloudinary URL for partner logo.")
    logo_public_id = models.CharField(max_length=255, blank=True, help_text="Cloudinary public ID for partner logo.")
    website_url = models.URLField(
        max_length=500,
        help_text="Official website (primary redirect target).",
    )
    url = models.URLField(
        max_length=500,
        blank=True,
        help_text="Optional secondary URL (e.g. integration / deep link).",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first within their group.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name
