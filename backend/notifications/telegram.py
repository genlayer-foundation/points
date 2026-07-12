"""Telegram delivery channel for portal notifications.

Enqueue helpers are called from services.notify()/broadcast() and
campaigns.send_campaign() when the event or campaign includes the
'telegram' channel. They write pending rows into the TelegramMessage
outbox; deliver_pending() drains it, triggered by the cron-protected
/api/v1/notifications/telegram/deliver/ endpoint (or the
deliver_telegram_messages management command).

Enqueueing is best-effort and idempotent: failures are logged and swallowed
so Telegram can never break portal notification creation, and the partial
unique constraint on (notification, connection) makes repeated enqueues
(re-broadcasts, campaign resends) no-ops.
"""
import logging
import re
import time
from datetime import timedelta

from django.conf import settings
from django.db import connection as db_connection
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from social_connections.models import TelegramConnection, TelegramMessage
from social_connections.telegram import TELEGRAM_MAX_LEN, escape, send_telegram_message

logger = logging.getLogger(__name__)

# Telegram's global budget is ~30 messages/second; one 25-row batch per second
# keeps a safety margin. ponytail: fixed pacing, adaptive throttling only if
# broadcasts ever grow past a few thousand linked users.
CLAIM_BATCH_SIZE = 25
DEFAULT_RUN_LIMIT = 400
MAX_ATTEMPTS = 3
STALE_SENDING_MINUTES = 10


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

# Per-event accents; the category map is the fallback for future events.
EVENT_EMOJI = {
    'submission.accepted': '✅',
    'submission.rejected': '❌',
    'submission.more_info_needed': '📝',
    'submission.proposal_questioned': '❓',
    'submission.appealed': '⚖️',
    'submission.more_info_resubmitted': '📨',
    'contribution.highlighted': '🌟',
    'validator.graduated': '🎓',
    'mission.published': '🎯',
    'node_version.published': '🚀',
    'alert.published': '🚨',
    'custom.announcement': '📣',
}
CATEGORY_EMOJI = {
    'submission': '📄',
    'contribution': '🏆',
    'community': '👥',
    'content': '📰',
    'validator': '🖥️',
    'system': '⚙️',
    'announcement': '📣',
}
# Long bodies collapse behind Telegram's expandable quote so the card stays
# compact in the chat list.
EXPANDABLE_BODY_THRESHOLD = 400


def _emoji_for(notification):
    return (
        EVENT_EMOJI.get(notification.event_type)
        or CATEGORY_EMOJI.get(notification.category)
        or '🔔'
    )


def _absolute_link_url(notification):
    url = (notification.link_url or '').strip()
    if not url:
        return ''
    if url.startswith('#/'):
        url = url[1:]
    if not url.startswith(('http://', 'https://')):
        url = f"{settings.FRONTEND_URL}{url}"
    return url


def notification_link_button(notification):
    """Inline-keyboard reply_markup for the notification's link, or None.

    The link travels as a button (not an <a> in the text): that is what makes
    the message read as a card in Telegram.
    """
    url = _absolute_link_url(notification)
    if not url:
        return None
    label = notification.link_label or 'Open in portal'
    return {'inline_keyboard': [[{'text': label[:64], 'url': url}]]}


def render_notification_text(notification):
    """Render a Notification row as a Telegram HTML "card":

        {emoji} <b>{title}</b>
        <i>{category} · GenLayer Portal</i>

        <blockquote>{body}</blockquote>

    The blockquote draws Telegram's accent bar next to the body; the link is
    delivered separately as an inline button (notification_link_button).
    """
    category_label = notification.get_category_display() if notification.category else ''
    byline_parts = [part for part in (category_label, 'GenLayer Portal') if part]
    header = (
        f"{_emoji_for(notification)} <b>{escape(notification.title)}</b>\n"
        f"<i>{escape(' · '.join(byline_parts))}</i>"
    )

    body = (notification.body or '').strip()
    if not body:
        return header

    # Escape FIRST, then budget on the escaped length: escaping expands
    # & < > up to 5x, so budgeting raw text would overshoot the limit and
    # force send-time truncation straight through the HTML tags.
    escaped_body = escape(body)
    budget = TELEGRAM_MAX_LEN - len(header) - len('\n\n<blockquote expandable></blockquote>')
    if budget <= 20:
        return header
    if len(escaped_body) > budget:
        cut = escaped_body[: budget - 1]
        # Never end inside an entity (&amp; / &lt; / &gt;).
        cut = re.sub(r'&[a-zA-Z]{0,4}$', '', cut)
        escaped_body = cut + '…'
    open_tag = (
        '<blockquote expandable>'
        if len(escaped_body) > EXPANDABLE_BODY_THRESHOLD
        else '<blockquote>'
    )
    return f"{header}\n\n{open_tag}{escaped_body}</blockquote>"


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------

def eligible_connections(users):
    return TelegramConnection.objects.filter(
        user__in=users,
        notifications_enabled=True,
        blocked_at__isnull=True,
    )


def _refresh_pending_text(notifications, text):
    """Sync still-queued rows with refreshed notification copy.

    Dedupe-refreshes and campaign resends update the Notification rows in
    place; without this, a pre-cron edit would deliver the original text.
    Already-sent rows are history and stay untouched.
    """
    TelegramMessage.objects.filter(
        notification__in=notifications,
        direction=TelegramMessage.DIRECTION_OUT,
        status=TelegramMessage.STATUS_PENDING,
    ).exclude(text=text).update(text=text, updated_at=timezone.now())


def enqueue_personal(notification):
    """Queue a personal notification for its recipient, if linked."""
    try:
        conn = (
            TelegramConnection.objects
            .filter(
                user=notification.recipient,
                notifications_enabled=True,
                blocked_at__isnull=True,
            )
            .first()
        )
        if conn is None:
            return
        text = render_notification_text(notification)
        _, created = TelegramMessage.objects.get_or_create(
            notification=notification,
            connection=conn,
            direction=TelegramMessage.DIRECTION_OUT,
            defaults={
                'chat_id': conn.platform_user_id,
                'text': text,
                'status': TelegramMessage.STATUS_PENDING,
            },
        )
        if not created:
            _refresh_pending_text([notification.pk], text)
    except Exception:
        logger.exception("Telegram enqueue_personal failed (notification %s)", notification.pk)


def enqueue_broadcast(notification):
    """Queue a broadcast for every linked user in its audience.

    On re-broadcast the dedupe constraint skips users already queued/sent,
    so only users who linked Telegram after the original broadcast get it.
    """
    try:
        from .services import users_for_audience

        text = render_notification_text(notification)
        batch = []
        connections = eligible_connections(users_for_audience(notification.audience))
        for conn in connections.iterator(chunk_size=500):
            batch.append(TelegramMessage(
                direction=TelegramMessage.DIRECTION_OUT,
                connection=conn,
                chat_id=conn.platform_user_id,
                text=text,
                status=TelegramMessage.STATUS_PENDING,
                notification=notification,
            ))
            if len(batch) >= 500:
                TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
        if batch:
            TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
        # A re-broadcast refreshed the notification copy; sync queued rows.
        _refresh_pending_text([notification.pk], text)
    except Exception:
        logger.exception("Telegram enqueue_broadcast failed (notification %s)", notification.pk)


def enqueue_campaign(campaign, users):
    """Queue a campaign's fanned-out personal rows for linked recipients."""
    try:
        from .models import Notification

        connections = {c.user_id: c for c in eligible_connections(users)}
        if not connections:
            return
        notifications = Notification.objects.filter(
            dedupe_key=campaign.dedupe_key,
            recipient_id__in=connections.keys(),
        )
        # All fanned-out rows carry identical copy; render once.
        text = None
        batch = []
        for notification in notifications.iterator(chunk_size=500):
            if text is None:
                text = render_notification_text(notification)
            conn = connections[notification.recipient_id]
            batch.append(TelegramMessage(
                direction=TelegramMessage.DIRECTION_OUT,
                connection=conn,
                chat_id=conn.platform_user_id,
                text=text,
                status=TelegramMessage.STATUS_PENDING,
                notification=notification,
            ))
            if len(batch) >= 500:
                TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
        if batch:
            TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
        # A resend refreshed the campaign copy; sync still-queued rows.
        if text is not None:
            _refresh_pending_text(notifications, text)
    except Exception:
        logger.exception("Telegram enqueue_campaign failed (campaign %s)", campaign.pk)


def cancel_pending_for_notifications(notifications):
    """Delete not-yet-sent outbox rows for the given notifications.

    Must run BEFORE the notifications themselves are deleted: the FK is
    SET_NULL, so deleting first would orphan the pending rows and the drain
    would still send the recalled content. Sent messages cannot be recalled
    from Telegram.
    """
    return TelegramMessage.objects.filter(
        notification__in=notifications,
        status__in=[TelegramMessage.STATUS_PENDING, TelegramMessage.STATUS_SENDING],
    ).delete()[0]


def cancel_pending_for_campaign(campaign):
    from .models import Notification

    return cancel_pending_for_notifications(
        Notification.objects.filter(dedupe_key=campaign.dedupe_key)
    )


# ---------------------------------------------------------------------------
# Drain
# ---------------------------------------------------------------------------

def _claim_batch(size, exclude_pks):
    """Atomically claim up to `size` deliverable rows (multi-worker safe).

    exclude_pks keeps rows that already failed retryably in THIS run from
    being re-claimed immediately; they retry on the next cron tick instead of
    burning all their attempts against the same transient failure.
    """
    now = timezone.now()
    stale_cutoff = now - timedelta(minutes=STALE_SENDING_MINUTES)
    with transaction.atomic():
        queryset = (
            TelegramMessage.objects
            .filter(direction=TelegramMessage.DIRECTION_OUT, attempts__lt=MAX_ATTEMPTS)
            .filter(
                Q(status=TelegramMessage.STATUS_PENDING)
                | Q(status=TelegramMessage.STATUS_SENDING, updated_at__lt=stale_cutoff)
            )
            .exclude(pk__in=exclude_pks)
            .order_by('created_at')
        )
        if db_connection.features.has_select_for_update_skip_locked:
            queryset = queryset.select_for_update(skip_locked=True)
        elif db_connection.features.has_select_for_update:
            queryset = queryset.select_for_update()
        pks = list(queryset.values_list('pk', flat=True)[:size])
        if pks:
            TelegramMessage.objects.filter(pk__in=pks).update(
                status=TelegramMessage.STATUS_SENDING,
                attempts=F('attempts') + 1,
                updated_at=now,
            )
    if not pks:
        return []
    return list(
        TelegramMessage.objects
        .filter(pk__in=pks)
        .select_related('connection', 'notification')
        .order_by('created_at')
    )


def _finish(message, status, error=''):
    # Queryset update, not instance save: a recall can delete the row while
    # its send is in flight, and saving a deleted instance would raise and
    # abort the rest of the run. An update on a deleted row is a no-op.
    updates = {'status': status, 'error': error[:200], 'updated_at': timezone.now()}
    if status == TelegramMessage.STATUS_SENT:
        updates['sent_at'] = timezone.now()
    TelegramMessage.objects.filter(pk=message.pk).update(**updates)


def deliver_pending(limit=DEFAULT_RUN_LIMIT):
    """Send queued messages, pacing to Telegram's rate budget.

    Returns {'sent': n, 'failed': n, 'remaining': n}. On a 429 the whole
    run stops and unclaimed rows return to pending; the next cron tick
    resumes. Delivery is at-least-once, bounded by MAX_ATTEMPTS.
    """
    # A worker that crashed mid-send on a row's FINAL attempt leaves it
    # 'sending' with attempts == MAX_ATTEMPTS; claims require attempts < MAX,
    # so without this sweep the row would be stranded forever.
    stale_cutoff = timezone.now() - timedelta(minutes=STALE_SENDING_MINUTES)
    TelegramMessage.objects.filter(
        direction=TelegramMessage.DIRECTION_OUT,
        status=TelegramMessage.STATUS_SENDING,
        attempts__gte=MAX_ATTEMPTS,
        updated_at__lt=stale_cutoff,
    ).update(
        status=TelegramMessage.STATUS_FAILED,
        error='max_attempts_exceeded',
        updated_at=timezone.now(),
    )

    sent = failed = processed = 0
    rate_limited = False
    seen_pks = set()

    while processed < limit and not rate_limited:
        batch = _claim_batch(min(CLAIM_BATCH_SIZE, limit - processed), seen_pks)
        if not batch:
            break
        processed += len(batch)
        seen_pks.update(message.pk for message in batch)
        batch_started = time.monotonic()

        for index, message in enumerate(batch):
            # Enqueued rows always carry a notification; a null FK means the
            # notification was deleted (recalled) after enqueue, so the
            # content must not be sent.
            if message.notification_id is None:
                _finish(message, TelegramMessage.STATUS_FAILED, 'notification_recalled')
                failed += 1
                continue

            conn = message.connection
            if conn is None or not conn.notifications_enabled or conn.blocked_at:
                _finish(message, TelegramMessage.STATUS_FAILED, 'connection_gone')
                failed += 1
                continue

            # Send to the connection's LIVE chat id: if the user re-linked a
            # different Telegram account, message.chat_id is a stale record.
            # The link button is built from the notification at send time, so
            # the outbox stores only the rendered text.
            ok, retry_after, description = send_telegram_message(
                conn.platform_user_id,
                message.text,
                connection=conn,
                reply_markup=notification_link_button(message.notification),
            )
            if ok:
                _finish(message, TelegramMessage.STATUS_SENT)
                sent += 1
            elif retry_after is not None:
                # Rate limited: unclaim this row and the rest of the batch,
                # stop the run. The next cron tick resumes.
                remaining_pks = [m.pk for m in batch[index:]]
                TelegramMessage.objects.filter(pk__in=remaining_pks).update(
                    status=TelegramMessage.STATUS_PENDING,
                    attempts=F('attempts') - 1,
                )
                rate_limited = True
                logger.warning("Telegram rate limited (retry_after=%s); run stopped", retry_after)
                break
            else:
                if message.attempts >= MAX_ATTEMPTS:
                    _finish(message, TelegramMessage.STATUS_FAILED, description)
                    failed += 1
                else:
                    _finish(message, TelegramMessage.STATUS_PENDING, description)

        elapsed = time.monotonic() - batch_started
        if elapsed < 1 and processed < limit and not rate_limited:
            time.sleep(1 - elapsed)

    remaining = TelegramMessage.objects.filter(
        direction=TelegramMessage.DIRECTION_OUT,
        status=TelegramMessage.STATUS_PENDING,
    ).count()
    return {'sent': sent, 'failed': failed, 'remaining': remaining}
