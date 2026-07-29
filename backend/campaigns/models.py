"""Marketing campaign vanity links and durable acquisition attribution.

Marketing creates campaigns and role links in Django admin; the public URL is
always {FRONTEND_URL}/join/<role-segment>/<alias>, reverse-proxied by Amplify
to the resolver in views.py. Creating a campaign is data only: no route,
Amplify, or DNS change is ever needed per campaign.
"""
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from utils.models import BaseModel

ROLE_BUILDER = 'builder'
ROLE_VALIDATOR = 'validator'
ROLE_COMMUNITY = 'community'
ROLE_CHOICES = [
    (ROLE_BUILDER, 'Builder'),
    (ROLE_VALIDATOR, 'Validator'),
    (ROLE_COMMUNITY, 'Community'),
]

# Public URL segment <-> canonical role (Category slug) mapping.
ROLE_SEGMENT_TO_ROLE = {
    'builders': ROLE_BUILDER,
    'validators': ROLE_VALIDATOR,
    'community': ROLE_COMMUNITY,
}
ROLE_TO_SEGMENT = {role: segment for segment, role in ROLE_SEGMENT_TO_ROLE.items()}

# Ad click IDs forwarded from the vanity request onto the redirect target so
# auto-tagged paid traffic keeps its ad-platform join in GA. Keep in sync with
# ATTRIBUTION_PARAMS in frontend/src/lib/analytics.js.
CLICK_ID_FORWARD_PARAMS = ('gclid', 'gbraid', 'wbraid', 'fbclid', 'twclid', 'msclkid', 'ttclid')

MAX_DESTINATION_LENGTH = 200

# Destinations must sit under one of these portal prefixes (exact match or
# prefix + '/'). Extend when marketing needs a new landing surface.
ALLOWED_DESTINATION_PREFIXES = (
    '/',
    '/builders',
    '/validators',
    '/community',
    '/how-it-works',
    '/referral-program',
    '/hackathon',
    '/gen-tv',
    '/gen-news',
    '/ecosystem-partners',
)
RESERVED_DESTINATION_PREFIXES = (
    '/admin',
    '/api',
    '/oauth',
    '/static',
    '/media',
    '/join',
    '/swagger',
    '/campaigns',
)


def generate_tracking_id():
    """Opaque, non-sensitive link ID published as utm_id."""
    return 'cl-' + secrets.token_hex(6)


def _matches_prefix(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip('/') + '/')


def validate_destination_path(path):
    """Validate a campaign destination as a safe relative portal path.

    Runs on write (model clean) AND again in the resolver before every
    redirect, so corrupt stored data fails closed instead of redirecting.
    """
    if not isinstance(path, str) or not path:
        raise ValidationError('Destination is required.')
    if len(path) > MAX_DESTINATION_LENGTH:
        raise ValidationError('Destination is too long.')
    if not path.startswith('/') or path.startswith('//'):
        raise ValidationError('Destination must be a relative portal path starting with "/".')
    if any(ch in path for ch in ('#', '?', '@', '\\', ' ')) or '..' in path or ':' in path:
        raise ValidationError('Destination must not include a scheme, host, query, fragment, or traversal.')
    if any(_matches_prefix(path, prefix) for prefix in RESERVED_DESTINATION_PREFIXES):
        raise ValidationError('Destination points at a reserved path.')
    # '/' allows only the portal root, never every path.
    allowed = path == '/' or any(
        _matches_prefix(path, prefix) for prefix in ALLOWED_DESTINATION_PREFIXES if prefix != '/'
    )
    if not allowed:
        raise ValidationError('Destination is not an allowed portal path.')


class MarketingCampaign(BaseModel):
    name = models.CharField(max_length=200)
    tracking_key = models.CharField(
        max_length=64,
        unique=True,
        validators=[RegexValidator(r'^[a-z0-9_]+$', 'Use only lowercase letters, digits, and underscores.')],
        help_text=(
            'Published as utm_campaign, e.g. ethcc_role_recruitment. Immutable once '
            'links are live; clone the campaign instead of changing its meaning.'
        ),
    )
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, help_text='Prefer deactivating over deleting.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def clean(self):
        if self.tracking_key:
            self.tracking_key = self.tracking_key.strip().lower()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'End must be after start.'})

    def is_expired_at(self, dt):
        return bool(self.ends_at and dt >= self.ends_at)

    def is_live_at(self, dt):
        if not self.is_active or self.is_expired_at(dt):
            return False
        return not (self.starts_at and dt < self.starts_at)


class CampaignLink(BaseModel):
    campaign = models.ForeignKey(MarketingCampaign, on_delete=models.CASCADE, related_name='links')
    tracking_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        default=generate_tracking_id,
        help_text='Server-generated opaque ID published as utm_id. Immutable.',
    )
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    alias = models.CharField(
        max_length=64,
        validators=[RegexValidator(r'^[a-z0-9-]+$', 'Use only lowercase letters, digits, and hyphens.')],
        help_text='URL segment after the role, e.g. "ethcc" for /join/builders/ethcc.',
    )
    destination_path = models.CharField(
        max_length=MAX_DESTINATION_LENGTH,
        help_text='Relative portal path the link redirects to, e.g. /builders.',
    )
    utm_source = models.CharField(max_length=64, help_text='e.g. x, discord, newsletter, ethcc')
    utm_medium = models.CharField(max_length=64, help_text='e.g. organic_social, paid_social, email, event')
    utm_content = models.CharField(max_length=64, blank=True, help_text='Optional creative ID, e.g. launch_post_01')
    utm_term = models.CharField(max_length=64, blank=True)
    is_active = models.BooleanField(default=True, help_text='Prefer pausing over deleting.')
    starts_at = models.DateTimeField(null=True, blank=True, help_text='Optional override of the campaign window.')
    ends_at = models.DateTimeField(null=True, blank=True, help_text='Optional override of the campaign window.')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['role', 'alias'], name='unique_campaign_link_role_alias'),
        ]

    def __str__(self):
        return f'/join/{ROLE_TO_SEGMENT.get(self.role, self.role)}/{self.alias}'

    def clean(self):
        for field in ('alias', 'utm_source', 'utm_medium', 'utm_content', 'utm_term'):
            value = getattr(self, field)
            if value:
                setattr(self, field, value.strip().lower())
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'End must be after start.'})
        validate_destination_path(self.destination_path)

    @property
    def public_url(self):
        return f'{settings.FRONTEND_URL}/join/{ROLE_TO_SEGMENT.get(self.role, self.role)}/{self.alias}'

    @property
    def utm_query(self):
        params = {
            'utm_id': self.tracking_id,
            'utm_source': self.utm_source,
            'utm_medium': self.utm_medium,
            'utm_campaign': self.campaign.tracking_key,
        }
        if self.utm_content:
            params['utm_content'] = self.utm_content
        if self.utm_term:
            params['utm_term'] = self.utm_term
        return urlencode(params)

    @property
    def redirect_target(self):
        return f'{settings.FRONTEND_URL}{self.destination_path}?{self.utm_query}'

    def is_expired_at(self, dt):
        return bool(self.ends_at and dt >= self.ends_at) or self.campaign.is_expired_at(dt)

    def is_live_at(self, dt):
        if not self.is_active or not self.campaign.is_live_at(dt):
            return False
        if self.starts_at and dt < self.starts_at:
            return False
        return not (self.ends_at and dt >= self.ends_at)


class CampaignRedirectHit(models.Model):
    """One resolver request. These are redirect requests, not unique humans:
    link preview bots and scanners hit vanity URLs too (classified below).

    Privacy: never add raw IPs, full referrer URLs, full user agents, wallet
    addresses, or emails to this table.
    """

    DEVICE_DESKTOP = 'desktop'
    DEVICE_MOBILE = 'mobile'
    DEVICE_TABLET = 'tablet'
    DEVICE_BOT = 'bot'
    DEVICE_UNKNOWN = 'unknown'
    DEVICE_CHOICES = [
        (DEVICE_DESKTOP, 'Desktop'),
        (DEVICE_MOBILE, 'Mobile'),
        (DEVICE_TABLET, 'Tablet'),
        (DEVICE_BOT, 'Bot'),
        (DEVICE_UNKNOWN, 'Unknown'),
    ]

    campaign_link = models.ForeignKey(CampaignLink, on_delete=models.CASCADE, related_name='hits')
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    referrer_host = models.CharField(max_length=100, blank=True)
    user_agent_family = models.CharField(max_length=32, blank=True)
    device_category = models.CharField(max_length=10, choices=DEVICE_CHOICES, default=DEVICE_UNKNOWN)
    is_probable_bot = models.BooleanField(default=False)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f'{self.campaign_link_id} @ {self.occurred_at:%Y-%m-%d %H:%M}'


class UserAcquisitionAttribution(BaseModel):
    """Authoritative first-touch signup attribution, written once when the
    user is created from a pending wallet signup.

    The snapshot columns duplicate the FK on purpose: a campaign may later be
    renamed, archived, or deleted, and historical acquisition facts must not
    silently change.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='acquisition_attribution',
    )
    campaign_link = models.ForeignKey(
        CampaignLink, null=True, blank=True, on_delete=models.SET_NULL, related_name='acquisitions',
    )
    link_tracking_id = models.CharField(max_length=20)
    campaign_key = models.CharField(max_length=64)
    source = models.CharField(max_length=64, blank=True)
    medium = models.CharField(max_length=64, blank=True)
    content = models.CharField(max_length=64, blank=True)
    term = models.CharField(max_length=64, blank=True)
    link_role = models.CharField(max_length=16, blank=True)
    landing_path = models.CharField(max_length=MAX_DESTINATION_LENGTH, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    registered_at = models.DateTimeField()

    class Meta:
        ordering = ['-registered_at']

    def __str__(self):
        return f'{self.user_id} <- {self.campaign_key}'
