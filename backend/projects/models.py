from django.conf import settings
from django.db import models
from django.utils.text import slugify

from utils.models import BaseModel


class Project(BaseModel):
    """A project profile managed independently from portal content."""

    STATUS_ACTIVE = 'active'
    STATUS_IDLE = 'idle'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_IDLE, 'Idle'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='owned_projects',
        null=True,
        blank=True,
    )
    hero_image_url = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for hero image')
    hero_image_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for hero image')
    hero_image_url_tablet = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for tablet hero image (768-1023px). Falls back to hero_image_url if empty.')
    hero_image_tablet_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for tablet hero image')
    hero_image_url_mobile = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for mobile hero image (<768px). Falls back to hero_image_url if empty.')
    hero_image_mobile_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for mobile hero image')
    user_profile_image_url = models.URLField(max_length=500, blank=True, help_text='Cloudinary URL for project author image')
    user_profile_image_public_id = models.CharField(max_length=255, blank=True, help_text='Cloudinary public ID for project author image')
    view_url = models.CharField(max_length=500, blank=True, help_text='Optional dedicated Portal view URL for selected projects')
    url = models.URLField(max_length=500, blank=True, help_text='Project website or demo URL')
    github_url = models.URLField(max_length=500, blank=True)
    x_url = models.URLField(max_length=500, blank=True)
    telegram_url = models.URLField(max_length=500, blank=True)
    discord_url = models.URLField(max_length=500, blank=True)
    demo_url = models.URLField(max_length=500, blank=True)
    details = models.TextField(blank=True)
    related_contributions = models.ManyToManyField(
        'contributions.Contribution',
        blank=True,
        related_name='related_projects',
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='participating_projects',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    show_in_overview = models.BooleanField(
        default=False,
        help_text='Show this project in the portal overview featured projects section.',
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:200] or 'project'
            slug = base_slug
            suffix = 2
            queryset = type(self).objects.filter(slug=slug)
            if self.pk:
                queryset = queryset.exclude(pk=self.pk)
            while queryset.exists():
                suffix_text = f"-{suffix}"
                slug = f"{base_slug[:220 - len(suffix_text)]}{suffix_text}"
                queryset = type(self).objects.filter(slug=slug)
                if self.pk:
                    queryset = queryset.exclude(pk=self.pk)
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_link(self):
        view_url = (self.view_url or '').strip()
        if view_url:
            return view_url
        if self.url:
            return self.url
        if self.slug:
            return f"/builders/projects/{self.slug}"
        return None

    def can_be_edited_by(self, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if self.user_id == user.id:
            return True
        prefetched = getattr(self, '_prefetched_objects_cache', {})
        if 'participants' in prefetched:
            return any(participant.id == user.id for participant in prefetched['participants'])
        return self.participants.filter(id=user.id).exists()
