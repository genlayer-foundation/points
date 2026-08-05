"""Single source of truth for every notification event the portal can emit.

Adding a new notification over time:
1. Register an EventType here (category, priority, default audience, channels).
2. Emit it from the producing code:
   - personal events call services.notify(...)
   - announcements call services.broadcast(...), usually via an admin that
     uses notifications.admin_mixins.BroadcastNotificationAdminMixin.

`channels` is the foundation for future delivery channels (email, Telegram).
The portal channel is the notification row itself; when an external channel
ships, a delivery outbox + per-user preferences will key off this field.
"""
from dataclasses import dataclass

from .models import Notification


@dataclass(frozen=True)
class EventType:
    slug: str
    category: str
    priority: int = Notification.PRIORITY_NORMAL
    audience: str = Notification.AUDIENCE_ALL  # default audience when broadcast
    channels: tuple = ('portal',)              # future: 'email', 'telegram'


_EVENT_TYPES = [
    # --- Personal, automatic ---
    # High-signal events also push to linked Telegram accounts; content-noise
    # events stay portal-only. Flipping one is a one-line channels change.
    EventType('submission.accepted', category='submission',
              channels=('portal', 'telegram')),
    EventType('submission.rejected', category='submission', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('submission.more_info_needed', category='submission', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('submission.proposal_questioned', category='submission', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('submission.appealed', category='submission', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('submission.more_info_resubmitted', category='submission', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('contribution.highlighted', category='contribution',
              channels=('portal', 'telegram')),
    EventType('referral.joined', category='community'),
    EventType('validator.graduated', category='validator', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),
    EventType('email.verify_reminder', category='system', priority=Notification.PRIORITY_HIGH),

    # --- Broadcast, admin-explicit ---
    EventType('featured.published', category='content'),
    EventType('partner.published', category='content'),
    EventType('contribution_type.published', category='content'),
    EventType('mission.published', category='content',
              channels=('portal', 'telegram')),
    EventType('stream.published', category='content'),
    EventType('poap.published', category='content'),
    # Audience resolved per task category (builders/validators/community)
    # by services.broadcast_social_task.
    EventType('social_task.published', category='content'),
    EventType(
        'node_version.published',
        category='validator',
        priority=Notification.PRIORITY_HIGH,
        audience=Notification.AUDIENCE_VALIDATORS,
        channels=('portal', 'telegram'),
    ),
    EventType('alert.published', category='system', priority=Notification.PRIORITY_HIGH,
              channels=('portal', 'telegram')),

    # --- Campaigns (admin-composed, fan-out via notifications.campaigns) ---
    # Campaign Telegram delivery gates on campaign.channels, not this entry;
    # listed here so the registry stays the single source of truth.
    EventType('custom.announcement', category='announcement',
              channels=('portal', 'telegram')),
]

EVENT_TYPES = {}
for _event in _EVENT_TYPES:
    if _event.slug in EVENT_TYPES:
        raise RuntimeError(f"Duplicate notification event slug: {_event.slug}")
    EVENT_TYPES[_event.slug] = _event


def get_event_type(slug):
    try:
        return EVENT_TYPES[slug]
    except KeyError:
        raise KeyError(
            f"Unknown notification event type '{slug}'. "
            "Register it in notifications/registry.py."
        ) from None
