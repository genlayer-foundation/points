import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from utils.models import BaseModel


class PoapDrop(BaseModel):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    description = models.TextField(blank=True)
    artwork_url = models.URLField(max_length=500, blank=True)
    artwork_public_id = models.CharField(max_length=255, blank=True)
    event_start_at = models.DateTimeField()
    event_end_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    max_claims = models.PositiveIntegerField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_poap_drops',
    )
    legacy_poap_id = models.CharField(max_length=100, blank=True, db_index=True)
    discord_role_id = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-event_start_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'event_start_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['legacy_poap_id'],
                condition=~Q(legacy_poap_id=''),
                name='unique_poap_drop_legacy_poap_id',
            ),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._generate_unique_slug()
        super().save(*args, **kwargs)

    def _generate_unique_slug(self):
        base = slugify(self.title)[:170] or 'poap'
        candidate = base
        suffix = 2
        while PoapDrop.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
            candidate = f'{base}-{suffix}'
            suffix += 1
        return candidate


class PoapDistribution(BaseModel):
    METHOD_SECRET = 'secret'
    METHOD_MINT_LINK = 'mint_link'
    METHOD_DISCORD_VOICE = 'discord_voice'
    METHOD_CHOICES = [
        (METHOD_SECRET, 'Secret phrase'),
        (METHOD_MINT_LINK, 'Mint link'),
        (METHOD_DISCORD_VOICE, 'Discord voice'),
    ]

    drop = models.ForeignKey(PoapDrop, on_delete=models.CASCADE, related_name='distributions')
    method = models.CharField(max_length=30, choices=METHOD_CHOICES)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    max_claims = models.PositiveIntegerField(null=True, blank=True)
    claimed_count = models.PositiveIntegerField(default=0)
    secret_hash = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['method', 'active', 'starts_at', 'ends_at']),
        ]

    def __str__(self):
        return f'{self.drop} - {self.get_method_display()}'

    def is_open(self, at_time=None):
        at_time = at_time or timezone.now()
        if not self.active:
            return False
        if self.starts_at and at_time < self.starts_at:
            return False
        if self.ends_at and at_time > self.ends_at:
            return False
        if self.max_claims is not None and self.claimed_count >= self.max_claims:
            return False
        return True


class PoapMintLink(BaseModel):
    distribution = models.ForeignKey(
        PoapDistribution,
        on_delete=models.CASCADE,
        related_name='mint_links',
        limit_choices_to={'method': PoapDistribution.METHOD_MINT_LINK},
    )
    token_hash = models.CharField(max_length=128, unique=True)
    token_ciphertext = models.TextField(blank=True)
    max_uses = models.PositiveIntegerField(default=1)
    used_count = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.distribution.drop} link {self.pk}'

    def is_open(self, at_time=None):
        at_time = at_time or timezone.now()
        if self.expires_at and at_time > self.expires_at:
            return False
        return self.used_count < self.max_uses

    @staticmethod
    def generate_token():
        return secrets.token_urlsafe(32)


class PoapImportBatch(BaseModel):
    source_name = models.CharField(max_length=100)
    file_name = models.CharField(max_length=255, blank=True)
    total_rows = models.PositiveIntegerField(default=0)
    imported_count = models.PositiveIntegerField(default=0)
    matched_count = models.PositiveIntegerField(default=0)
    unmatched_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='poap_import_batches',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.source_name} import {self.pk}'


class PoapClaim(BaseModel):
    CLAIM_SECRET = 'secret'
    CLAIM_MINT_LINK = 'mint_link'
    CLAIM_DISCORD_VOICE = 'discord_voice'
    CLAIM_ADMIN = 'admin'
    CLAIM_LEGACY = 'legacy'
    CLAIM_METHOD_CHOICES = [
        (CLAIM_SECRET, 'Secret phrase'),
        (CLAIM_MINT_LINK, 'Mint link'),
        (CLAIM_DISCORD_VOICE, 'Discord voice'),
        (CLAIM_ADMIN, 'Admin'),
        (CLAIM_LEGACY, 'Legacy import'),
    ]

    SOURCE_PORTAL = 'portal'
    SOURCE_LEGACY_IMPORT = 'legacy_import'
    SOURCE_CHOICES = [
        (SOURCE_PORTAL, 'Portal'),
        (SOURCE_LEGACY_IMPORT, 'Legacy import'),
    ]

    drop = models.ForeignKey(PoapDrop, on_delete=models.CASCADE, related_name='claims')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='poap_claims',
        null=True,
        blank=True,
    )
    distribution = models.ForeignKey(
        PoapDistribution,
        on_delete=models.SET_NULL,
        related_name='claims',
        null=True,
        blank=True,
    )
    mint_link = models.ForeignKey(
        PoapMintLink,
        on_delete=models.SET_NULL,
        related_name='claims',
        null=True,
        blank=True,
    )
    import_batch = models.ForeignKey(
        PoapImportBatch,
        on_delete=models.SET_NULL,
        related_name='claims',
        null=True,
        blank=True,
    )
    claim_method = models.CharField(max_length=30, choices=CLAIM_METHOD_CHOICES)
    claimed_at = models.DateTimeField(default=timezone.now)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_PORTAL)
    legacy_wallet_address = models.CharField(max_length=100, blank=True, db_index=True)
    legacy_email = models.EmailField(blank=True, db_index=True)
    legacy_external_id = models.CharField(max_length=120, blank=True, db_index=True)
    legacy_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-claimed_at', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['drop', 'user'],
                condition=Q(user__isnull=False),
                name='unique_poap_claim_per_user_drop',
            ),
        ]
        indexes = [
            models.Index(fields=['drop', 'claimed_at']),
            models.Index(fields=['user', 'claimed_at']),
        ]

    def __str__(self):
        user_label = self.user_id or self.legacy_wallet_address or self.legacy_email or 'unmatched'
        return f'{self.drop} claimed by {user_label}'
