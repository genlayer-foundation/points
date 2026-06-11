"""Campaign targeting and delivery for admin-composed custom notifications.

resolve_recipients() is the channel-agnostic enumeration step: it turns a
CustomNotification's targeting into a concrete user queryset. The portal
channel fans that set out into personal Notification rows here; future email
or Telegram channels reuse the same resolution and add their own delivery.
"""
import re
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.db.models.functions import Lower
from django.utils import timezone

from .models import CustomNotification, Notification
from .registry import get_event_type
from .services import internal_route

WALLET_RE = re.compile(r'^0[xX][0-9a-fA-F]{40}$')

FANOUT_BATCH_SIZE = 500


class CampaignSendError(Exception):
    """Raised when a campaign cannot be sent (e.g. zero recipients)."""


@dataclass
class ResolvedAudience:
    users: object  # User queryset; the enumeration future channels reuse
    unmatched_wallets: list = field(default_factory=list)


@dataclass
class CampaignSendResult:
    total: int
    created: int
    refreshed: int
    unmatched_wallets: list = field(default_factory=list)


def parse_wallet_lines(raw_text):
    """Parse pasted wallet addresses.

    Splits on newlines and commas, strips whitespace, collapses duplicates
    case-insensitively. Returns ({lowercased_address: original_line}, invalid_lines).
    """
    addresses = {}
    invalid_lines = []
    for chunk in re.split(r'[\n,]+', raw_text or ''):
        line = chunk.strip()
        if not line:
            continue
        if not WALLET_RE.match(line):
            invalid_lines.append(line)
            continue
        addresses.setdefault(line.lower(), line)
    return addresses, invalid_lines


def _role_user_ids(role):
    if role == 'builders':
        from builders.models import Builder
        return Builder.objects.values('user_id')
    if role == 'validators':
        from validators.models import Validator
        return Validator.objects.values('user_id')
    if role == 'stewards':
        from stewards.models import Steward
        return Steward.objects.values('user_id')
    if role == 'creators':
        from creators.models import Creator
        return Creator.objects.values('user_id')
    raise ValueError(f"Unknown campaign target role: {role}")


def resolve_recipients(campaign):
    """Resolve a campaign's targeting to a concrete set of active users.

    Inactive users are excluded in every mode. Banned and non-visible users
    are deliberately included: those flags gate participation and public
    listings, not the user's own notification feed.
    """
    User = get_user_model()
    active_users = User.objects.filter(is_active=True)

    if campaign.target_mode == CustomNotification.TARGET_EVERYONE:
        return ResolvedAudience(users=active_users)

    if campaign.target_mode == CustomNotification.TARGET_ROLES:
        role_q = Q(pk__in=[])
        for role in campaign.target_roles:
            role_q |= Q(pk__in=_role_user_ids(role))
        return ResolvedAudience(users=active_users.filter(role_q))

    if campaign.target_mode == CustomNotification.TARGET_USERS:
        return ResolvedAudience(users=campaign.target_users.filter(is_active=True))

    if campaign.target_mode == CustomNotification.TARGET_WALLETS:
        addresses, invalid_lines = parse_wallet_lines(campaign.target_wallets)
        users = (
            active_users
            .exclude(address__isnull=True)
            .exclude(address='')
            .annotate(address_key=Lower('address'))
            .filter(address_key__in=addresses.keys())
        )
        matched_keys = {key for key in users.values_list('address_key', flat=True)}
        unmatched = invalid_lines + [
            original for key, original in addresses.items() if key not in matched_keys
        ]
        return ResolvedAudience(users=users, unmatched_wallets=unmatched)

    raise ValueError(f"Unknown campaign target mode: {campaign.target_mode}")


def send_campaign(campaign, *, actor=None):
    """Fan a campaign out as personal notification rows. Idempotent.

    A resend refreshes the copy and resurfaces the notification as unread,
    scoped to the currently resolved audience; recipients removed from the
    targeting keep their old row untouched. The status flip happens last and
    outside any transaction so a crash mid-fan-out leaves a resumable draft.
    """
    audience = resolve_recipients(campaign)
    total = audience.users.count()
    if total == 0:
        raise CampaignSendError('No recipients matched the targeting.')

    event = get_event_type('custom.announcement')
    now = timezone.now()
    values = {
        'actor': actor,
        'event_type': event.slug,
        'category': event.category,
        'priority': campaign.priority,
        'title': campaign.title,
        'body': campaign.body,
        'link_url': internal_route(campaign.link_url),
        'link_label': campaign.link_label,
        'payload': {'campaign_id': campaign.pk},
        'source_app': 'notifications',
        'source_model': 'customnotification',
        'source_object_id': str(campaign.pk),
    }

    # Resend path (no-op on first send): refresh copy and resurface as
    # unread, but only for users still in the audience. .update() bypasses
    # auto_now/auto_now_add, so both timestamps are set explicitly; the
    # created_at bump moves the row back to the top of the feed.
    existing = Notification.objects.filter(
        dedupe_key=campaign.dedupe_key,
        recipient__in=audience.users,
    )
    existing_recipient_ids = set(existing.values_list('recipient_id', flat=True))
    refreshed = existing.update(
        **values,
        read_at=None,
        created_at=now,
        updated_at=now,
    )

    missing = audience.users.exclude(pk__in=existing_recipient_ids)
    batch = []
    for user in missing.iterator(chunk_size=FANOUT_BATCH_SIZE):
        batch.append(Notification(recipient=user, dedupe_key=campaign.dedupe_key, **values))
        if len(batch) >= FANOUT_BATCH_SIZE:
            Notification.objects.bulk_create(batch, ignore_conflicts=True)
            batch = []
    if batch:
        Notification.objects.bulk_create(batch, ignore_conflicts=True)

    campaign.status = CustomNotification.STATUS_SENT
    campaign.sent_at = now
    campaign.sent_by = actor
    campaign.sent_count = total
    campaign.unmatched_wallets = audience.unmatched_wallets
    campaign.save(update_fields=[
        'status', 'sent_at', 'sent_by', 'sent_count', 'unmatched_wallets', 'updated_at',
    ])

    return CampaignSendResult(
        total=total,
        created=total - refreshed,
        refreshed=refreshed,
        unmatched_wallets=audience.unmatched_wallets,
    )
