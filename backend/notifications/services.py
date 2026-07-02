"""Notification creation and feed services.

Core entry points:
- notify(event_slug, recipient=..., ...)   -> one personal notification row
- broadcast(event_slug, ...)               -> ONE row visible to a whole audience

A user's feed merges personal rows with broadcast rows targeted at an
audience they belong to and created after they joined. Broadcast read state
is stored lazily in NotificationReceipt rows, so a broadcast is a single
insert regardless of user count.
"""
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .models import Notification, NotificationReceipt, WhatsNewAnnouncement, WhatsNewAnnouncementSeen
from .registry import get_event_type


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def internal_route(path):
    """Normalize an internal SPA path to a clean route for the frontend router.

    The frontend uses history-based routing, so new links are stored as plain
    paths (e.g. ``/missions``). Legacy ``#/`` routes and absolute URLs are
    passed through unchanged; the frontend still resolves legacy ``#/`` links.
    """
    if not path:
        return ''
    if path.startswith(('#/', 'http://', 'https://')):
        return path
    if not path.startswith('/'):
        path = f'/{path}'
    return path


def _source_for(obj):
    if obj is None:
        return {}
    meta = obj._meta
    return {
        'source_app': meta.app_label,
        'source_model': meta.model_name,
        'source_object_id': str(obj.pk),
    }


def _apply_values(notification, values):
    for field, value in values.items():
        setattr(notification, field, value)
    notification.save(update_fields=[*values.keys(), 'updated_at'])


def broadcast_dedupe_key(event_slug, source):
    """Stable key for the one broadcast row attached to a source object."""
    event = get_event_type(event_slug)
    return f"{event.slug}:{source._meta.label_lower}:{source.pk}"


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def notify(
    event_slug,
    *,
    recipient,
    title,
    body='',
    link_url='',
    link_label='',
    payload=None,
    actor=None,
    source=None,
    dedupe_key=None,
    priority=None,
):
    """Create (or dedupe-refresh) a personal notification."""
    event = get_event_type(event_slug)
    values = {
        'actor': actor,
        'event_type': event.slug,
        'category': event.category,
        'priority': priority or event.priority,
        'title': title,
        'body': body,
        'link_url': link_url,
        'link_label': link_label,
        'payload': payload or {},
        **_source_for(source),
    }

    if dedupe_key:
        # The recipient is part of the lookup, so a dedupe key shared across
        # users can never reassign another user's notification.
        notification, created = Notification.objects.get_or_create(
            recipient=recipient,
            dedupe_key=dedupe_key,
            defaults=values,
        )
        if not created:
            # Same event delivered twice: refresh the copy, keep read state.
            _apply_values(notification, values)
        return notification

    return Notification.objects.create(recipient=recipient, **values)


def broadcast(
    event_slug,
    *,
    title,
    body='',
    link_url='',
    link_label='',
    payload=None,
    actor=None,
    source=None,
    audience=None,
):
    """Create a single broadcast notification row for an audience.

    Re-broadcasting the same source object refreshes the existing row,
    bumps it to the top of every feed, and clears read receipts so it
    surfaces as unread again. It never duplicates.
    """
    event = get_event_type(event_slug)
    values = {
        'audience': audience or event.audience,
        'actor': actor,
        'event_type': event.slug,
        'category': event.category,
        'priority': event.priority,
        'title': title,
        'body': body,
        'link_url': link_url,
        'link_label': link_label,
        'payload': payload or {},
        **_source_for(source),
    }

    dedupe_key = None
    if source is not None:
        dedupe_key = broadcast_dedupe_key(event.slug, source)

    if dedupe_key:
        notification, created = Notification.objects.get_or_create(
            recipient=None,
            dedupe_key=dedupe_key,
            defaults=values,
        )
        if not created:
            # Deliberate re-broadcast: resurface as new and unread for everyone.
            with transaction.atomic():
                _apply_values(notification, values)
                Notification.objects.filter(pk=notification.pk).update(created_at=timezone.now())
                notification.receipts.all().delete()
            notification.refresh_from_db(fields=['created_at'])
        return notification

    return Notification.objects.create(recipient=None, **values)


def recall_broadcast(event_slug, source):
    """Delete a source object's broadcast notification, if one exists."""
    if source is None or not source.pk:
        return 0

    event = get_event_type(event_slug)
    queryset = Notification.objects.filter(
        recipient__isnull=True,
        event_type=event.slug,
        dedupe_key=broadcast_dedupe_key(event.slug, source),
    )
    count = queryset.count()
    queryset.delete()
    return count


def estimate_broadcast_reach(audience):
    """Approximate audience size, used for admin feedback messages."""
    User = get_user_model()
    if audience == Notification.AUDIENCE_VALIDATORS:
        from validators.models import Validator
        return Validator.objects.filter(user__is_active=True).count()
    if audience == Notification.AUDIENCE_STEWARDS:
        from stewards.models import Steward
        return Steward.objects.filter(user__is_active=True).count()
    if audience == Notification.AUDIENCE_BUILDERS:
        from builders.models import Builder
        return Builder.objects.filter(user__is_active=True).count()
    if audience == Notification.AUDIENCE_COMMUNITY:
        from creators.models import Creator
        return Creator.objects.filter(user__is_active=True).count()
    return User.objects.filter(is_active=True).count()


# ---------------------------------------------------------------------------
# What's New announcements
# ---------------------------------------------------------------------------

def active_whats_new_for(user):
    """Published What's New announcements matching the user's current audience."""
    now = timezone.now()
    return WhatsNewAnnouncement.objects.filter(
        status=WhatsNewAnnouncement.STATUS_PUBLISHED,
        audience__in=audiences_for(user),
        published_at__isnull=False,
        published_at__lte=now,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    )


def annotate_whats_new_seen_state(queryset, user):
    return queryset.annotate(
        seen_current_version=Exists(
            WhatsNewAnnouncementSeen.objects.filter(
                announcement=OuterRef('pk'),
                user=user,
                version=OuterRef('version'),
            )
        )
    )


def unseen_whats_new_for(user):
    """Unseen current-version announcements for the What's New dialog."""
    return (
        annotate_whats_new_seen_state(active_whats_new_for(user), user)
        .filter(seen_current_version=False)
        .order_by('display_order', '-published_at', '-id')
    )


def seen_whats_new_for(user):
    """Recent published announcements whose current version the user has seen."""
    now = timezone.now()
    return (
        annotate_whats_new_seen_state(
            WhatsNewAnnouncement.objects.filter(
                status=WhatsNewAnnouncement.STATUS_PUBLISHED,
                audience__in=audiences_for(user),
                published_at__isnull=False,
                published_at__lte=now,
            ),
            user,
        )
        .filter(seen_current_version=True)
        .order_by('-published_at', '-id')[:12]
    )


def whats_new_unseen_count(user):
    return unseen_whats_new_for(user).count()


def mark_whats_new_seen(user, ids, action=WhatsNewAnnouncementSeen.ACTION_SEEN):
    """Mark visible current-version announcements as seen for a user."""
    if not ids:
        return 0

    announcements = list(active_whats_new_for(user).filter(pk__in=ids))
    if not announcements:
        return 0

    WhatsNewAnnouncementSeen.objects.bulk_create(
        [
            WhatsNewAnnouncementSeen(
                announcement=announcement,
                user=user,
                version=announcement.version,
                action=action,
            )
            for announcement in announcements
        ],
        ignore_conflicts=True,
    )
    return len(announcements)


# ---------------------------------------------------------------------------
# Feed queries and read state
# ---------------------------------------------------------------------------

UNREAD_Q = (
    Q(recipient__isnull=False, read_at__isnull=True)
    | Q(recipient__isnull=True, receipt_read=False)
)


def audiences_for(user):
    audiences = [Notification.AUDIENCE_ALL]
    from validators.models import Validator
    if Validator.objects.filter(user=user).exists():
        audiences.append(Notification.AUDIENCE_VALIDATORS)
    from stewards.models import Steward
    if Steward.objects.filter(user=user).exists():
        audiences.append(Notification.AUDIENCE_STEWARDS)
    from builders.models import Builder
    if Builder.objects.filter(user=user).exists():
        audiences.append(Notification.AUDIENCE_BUILDERS)
    from creators.models import Creator
    if Creator.objects.filter(user=user).exists():
        audiences.append(Notification.AUDIENCE_COMMUNITY)
    return audiences


def feed_for(user):
    """Personal notifications + broadcasts for the user's audiences."""
    return Notification.objects.filter(
        Q(recipient=user)
        | Q(
            recipient__isnull=True,
            audience__in=audiences_for(user),
            created_at__gte=user.date_joined,
        )
    )


def annotate_read_state(queryset, user):
    return queryset.annotate(
        receipt_read=Exists(
            NotificationReceipt.objects.filter(
                notification=OuterRef('pk'),
                user=user,
                read_at__isnull=False,
            )
        )
    )


def mark_notification_read(notification, user):
    if notification.recipient_id == user.pk:
        notification.mark_read()
    elif notification.is_broadcast:
        NotificationReceipt.objects.get_or_create(
            notification=notification,
            user=user,
            defaults={'read_at': timezone.now()},
        )


def mark_all_read(user):
    now = timezone.now()
    updated = Notification.objects.filter(
        recipient=user,
        read_at__isnull=True,
    ).update(read_at=now)

    unread_broadcast_ids = list(
        annotate_read_state(feed_for(user).filter(recipient__isnull=True), user)
        .filter(receipt_read=False)
        .values_list('pk', flat=True)
    )
    NotificationReceipt.objects.bulk_create(
        [
            NotificationReceipt(notification_id=pk, user=user, read_at=now)
            for pk in unread_broadcast_ids
        ],
        ignore_conflicts=True,
    )
    return updated + len(unread_broadcast_ids)


# ---------------------------------------------------------------------------
# Personal event producers
# ---------------------------------------------------------------------------

SUBMISSION_STATE_EVENTS = {
    'accepted': 'submission.accepted',
    'rejected': 'submission.rejected',
    'more_info_needed': 'submission.more_info_needed',
}


def submission_review_link(submission):
    query = urlencode({
        'state': submission.state,
        'submission': str(submission.id),
    })
    return f"/my-submissions?{query}"


def steward_submission_review_link(submission):
    query = urlencode({
        'status': 'pending',
        'q': str(submission.id),
    })
    return f"/stewards/submissions?{query}"


def _display_submission_name(submission):
    if submission.title:
        return submission.title
    if submission.contribution_type_id:
        return submission.contribution_type.name
    return 'your submission'


def notify_submission_review(submission, actor=None):
    event_slug = SUBMISSION_STATE_EVENTS.get(submission.state)
    if not event_slug or not submission.user_id:
        return None

    name = _display_submission_name(submission)
    if submission.state == 'accepted':
        title = 'Submission accepted'
        body = f"{name} was accepted."
    elif submission.state == 'rejected':
        title = 'Submission rejected'
        body = f"{name} was rejected. Review the steward feedback in My Submissions."
    else:
        title = 'More information needed'
        body = f"More information is needed for {name}."

    decision_at = submission.reviewed_at or submission.updated_at
    decision_marker = decision_at.isoformat() if decision_at else ''

    return notify(
        event_slug,
        recipient=submission.user,
        actor=actor or submission.reviewed_by,
        title=title,
        body=body,
        link_url=submission_review_link(submission),
        link_label='Open My Submissions',
        payload={
            'submission_id': str(submission.id),
            'state': submission.state,
            'contribution_type': submission.contribution_type.name if submission.contribution_type_id else '',
        },
        source=submission,
        dedupe_key=f"submission-review:{submission.id}:{submission.state}:{decision_marker}",
    )


def notify_submission_reopened_for_steward(submission, *, kind, actor=None):
    """Notify the assigned steward when a submitter returns a submission to review."""
    if not submission.assigned_to_id:
        return None

    name = _display_submission_name(submission)
    if kind == 'appeal':
        event_slug = 'submission.appealed'
        title = 'Submission appealed'
        body = f"{name} was appealed by the submitter and is ready for re-review."
        dedupe_marker = 'appeal'
    elif kind == 'more_info_resubmitted':
        event_slug = 'submission.more_info_resubmitted'
        title = 'More information resubmitted'
        body = f"{name} was updated by the submitter after your more-information request."
        edit_at = submission.last_edited_at or submission.updated_at
        dedupe_marker = edit_at.isoformat() if edit_at else ''
    else:
        raise ValueError(f"Unknown submission reopen notification kind: {kind}")

    return notify(
        event_slug,
        recipient=submission.assigned_to,
        actor=actor or submission.user,
        title=title,
        body=body,
        link_url=steward_submission_review_link(submission),
        link_label='Open submission',
        payload={
            'submission_id': str(submission.id),
            'state': submission.state,
            'kind': kind,
            'contribution_type': submission.contribution_type.name if submission.contribution_type_id else '',
        },
        source=submission,
        dedupe_key=f"submission-reopened:{submission.id}:{kind}:{dedupe_marker}",
    )


def notify_contribution_highlighted(highlight):
    contribution = highlight.contribution
    if not contribution or not contribution.user_id:
        return None

    return notify(
        'contribution.highlighted',
        recipient=contribution.user,
        title='Your contribution was highlighted',
        body=f'"{highlight.title}" is now featured in the portal highlights.',
        link_url=internal_route(f'/contribution/{contribution.id}'),
        link_label='View contribution',
        payload={
            'contribution_id': contribution.id,
            'highlight_id': highlight.id,
        },
        source=highlight,
        dedupe_key=f"contribution.highlighted:{highlight.pk}",
    )


def notify_referral_joined(new_user):
    referrer = new_user.referred_by
    if not referrer:
        return None

    if new_user.name:
        display = new_user.name
    elif new_user.address:
        display = f"{new_user.address[:6]}...{new_user.address[-4:]}"
    else:
        display = 'A new participant'

    return notify(
        'referral.joined',
        recipient=referrer,
        actor=new_user,
        title='Your referral joined the portal',
        body=f'{display} joined with your referral link. You earn 10% of their contribution points.',
        link_url=internal_route('/referrals'),
        link_label='View referrals',
        payload={'referred_user_id': new_user.id},
        source=new_user,
        dedupe_key=f"referral.joined:{new_user.pk}",
    )


def notify_email_verification_reminder(user):
    """Nudge a user without a verified email to verify it from the portal."""
    return notify(
        'email.verify_reminder',
        recipient=user,
        title='Verify your email',
        body=(
            'Your Portal account does not have a verified email yet. '
            'Verify it to secure your identity and stay reachable for important updates.'
        ),
        link_url=internal_route('/verify-email'),
        link_label='Verify email',
        payload={'user_id': user.id},
        source=user,
        dedupe_key=f"email.verify_reminder:{user.pk}",
    )


def clear_email_verification_reminder(user):
    """Remove the pending reminder once the user's email is verified."""
    return Notification.objects.filter(
        recipient=user,
        event_type='email.verify_reminder',
    ).delete()[0]


def notify_validator_graduated(user, actor=None):
    return notify(
        'validator.graduated',
        recipient=user,
        actor=actor,
        title='You are now a GenLayer validator',
        body='Your validator profile is active. Keep your node up to date to earn uptime points.',
        link_url=internal_route('/validators'),
        link_label='Open validator dashboard',
        payload={'user_id': user.id},
        source=user,
        dedupe_key=f"validator.graduated:{user.pk}",
    )


# ---------------------------------------------------------------------------
# Broadcast producers (admin-explicit)
# ---------------------------------------------------------------------------

def broadcast_featured_content(featured_content, actor=None, message=''):
    content_labels = {
        'hero': 'announcement',
        'build': 'featured build',
        'community': 'community feature',
        'validator_steward': 'validator/steward feature',
    }
    label = content_labels.get(featured_content.content_type, 'featured item')
    link = featured_content.get_link() or '/'

    return broadcast(
        'featured.published',
        actor=actor,
        title=f"New {label}: {featured_content.title}",
        body=message or featured_content.description,
        link_url=internal_route(link),
        link_label='Open',
        payload={
            'featured_content_id': featured_content.id,
            'content_type': featured_content.content_type,
        },
        source=featured_content,
    )


def broadcast_partner(partner, actor=None, message=''):
    return broadcast(
        'partner.published',
        actor=actor,
        title=f"New ecosystem partner: {partner.name}",
        body=message or partner.description,
        link_url=internal_route('/ecosystem-partners'),
        link_label='View ecosystem',
        payload={
            'partner_id': partner.id,
            'partner_slug': partner.slug,
        },
        source=partner,
    )


def broadcast_alert(alert, actor=None, message=''):
    return broadcast(
        'alert.published',
        actor=actor,
        title='Portal update',
        body=message or alert.text,
        link_url=internal_route('/'),
        link_label='Open portal',
        payload={
            'alert_id': alert.id,
            'alert_type': alert.alert_type,
        },
        source=alert,
    )


def broadcast_contribution_type(contribution_type, actor=None, message=''):
    return broadcast(
        'contribution_type.published',
        actor=actor,
        title=f"New contribution type: {contribution_type.name}",
        body=message or contribution_type.description or 'A new way to earn points is available.',
        link_url=internal_route(f'/contribution-type/{contribution_type.pk}'),
        link_label='View details',
        payload={
            'contribution_type_id': contribution_type.pk,
            'contribution_type_slug': contribution_type.slug or '',
        },
        source=contribution_type,
    )


def broadcast_mission(mission, actor=None, message=''):
    return broadcast(
        'mission.published',
        actor=actor,
        title=f"New mission: {mission.name}",
        body=message or 'A new mission is open for submissions.',
        link_url=internal_route(f'/contribution-type/{mission.contribution_type_id}'),
        link_label='View mission',
        payload={
            'mission_id': mission.pk,
            'contribution_type_id': mission.contribution_type_id,
        },
        source=mission,
    )


def broadcast_stream(stream, actor=None, message=''):
    return broadcast(
        'stream.published',
        actor=actor,
        title=f"New on Gen TV: {stream.title}",
        body=message or stream.description,
        link_url=internal_route('/gen-tv'),
        link_label='Open Gen TV',
        payload={
            'stream_id': stream.pk,
            'stream_slug': stream.slug,
            'starts_at': stream.starts_at.isoformat() if stream.starts_at else '',
        },
        source=stream,
    )


def broadcast_poap(poap_drop, actor=None, message=''):
    return broadcast(
        'poap.published',
        actor=actor,
        title=f"New POAP drop: {poap_drop.title}",
        body=message or poap_drop.description,
        link_url=internal_route(f'/community/poaps/{poap_drop.slug}'),
        link_label='View POAP',
        payload={
            'poap_drop_id': poap_drop.pk,
            'poap_drop_slug': poap_drop.slug,
        },
        source=poap_drop,
    )


SOCIAL_TASK_AUDIENCES = {
    'builder': Notification.AUDIENCE_BUILDERS,
    'validator': Notification.AUDIENCE_VALIDATORS,
    'community': Notification.AUDIENCE_COMMUNITY,
}

SOCIAL_TASK_ROUTES = {
    'builder': '/builders/tasks',
    'validator': '/validators/tasks',
    'community': '/community/tasks',
}


def broadcast_social_task(task, actor=None, message=''):
    """Announce a social task to the role its category targets.

    Builder tasks go to builders, validator tasks to validators, community
    tasks to creators (Creator profiles) — never to everyone.
    """
    category_slug = task.category.slug
    audience = SOCIAL_TASK_AUDIENCES.get(category_slug)
    if audience is None:
        # SocialTask.clean() restricts categories to the mapped three; an
        # unmapped slug means a new surface shipped without a notification
        # decision. Fail loudly instead of over-notifying everyone.
        raise ValueError(f"No notification audience mapped for social task category '{category_slug}'")

    return broadcast(
        'social_task.published',
        actor=actor,
        audience=audience,
        title=f"New task: {task.name}",
        body=message or task.description or f'Complete it to earn {task.points} points.',
        link_url=internal_route(SOCIAL_TASK_ROUTES[category_slug]),
        link_label='View tasks',
        payload={
            'social_task_id': task.pk,
            'social_task_slug': task.slug,
            'category': category_slug,
            'points': task.points,
        },
        source=task,
    )


def broadcast_target_node_version(target, actor=None, message=''):
    network = target.get_network_display() if hasattr(target, 'get_network_display') else target.network
    return broadcast(
        'node_version.published',
        actor=actor,
        title=f"Node upgrade available: {target.version}",
        body=message or (
            f"Target node version for {network} is now {target.version}. "
            "Update your node and your profile to stay in sync."
        ),
        link_url=internal_route('/profile'),
        link_label='Update node version',
        payload={
            'target_id': target.pk,
            'version': target.version,
            'network': target.network,
        },
        source=target,
    )
