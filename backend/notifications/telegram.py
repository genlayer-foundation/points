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

def render_notification_text(notification):
    """Render a Notification row as a Telegram HTML message."""
    header = f"<b>{escape(notification.title)}</b>"

    link_html = ''
    url = notification.link_url or ''
    if url:
        if url.startswith('#/'):
            url = url[1:]
        if not url.startswith(('http://', 'https://')):
            url = f"{settings.FRONTEND_URL}{url}"
        label = escape(notification.link_label or 'Open portal')
        link_html = f'\n\n<a href="{escape(url)}">{label}</a>'

    body = (notification.body or '').strip()
    # Truncate the raw body so title and link always survive. Escaping can
    # still overshoot the limit in pathological cases; send_telegram_message's
    # final truncate + plain-text parse fallback covers those.
    budget = TELEGRAM_MAX_LEN - len(header) - len(link_html) - 2
    if body and budget > 20:
        if len(body) > budget:
            body = body[: budget - 1] + '…'
        return f"{header}\n\n{escape(body)}{link_html}"
    return f"{header}{link_html}"


# ---------------------------------------------------------------------------
# Enqueue
# ---------------------------------------------------------------------------

def eligible_connections(users):
    return TelegramConnection.objects.filter(
        user__in=users,
        notifications_enabled=True,
        blocked_at__isnull=True,
    )


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
        TelegramMessage.objects.get_or_create(
            notification=notification,
            connection=conn,
            direction=TelegramMessage.DIRECTION_OUT,
            defaults={
                'chat_id': conn.platform_user_id,
                'text': render_notification_text(notification),
                'status': TelegramMessage.STATUS_PENDING,
            },
        )
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
        batch = []
        for notification in notifications.iterator(chunk_size=500):
            conn = connections[notification.recipient_id]
            batch.append(TelegramMessage(
                direction=TelegramMessage.DIRECTION_OUT,
                connection=conn,
                chat_id=conn.platform_user_id,
                text=render_notification_text(notification),
                status=TelegramMessage.STATUS_PENDING,
                notification=notification,
            ))
            if len(batch) >= 500:
                TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
        if batch:
            TelegramMessage.objects.bulk_create(batch, ignore_conflicts=True)
    except Exception:
        logger.exception("Telegram enqueue_campaign failed (campaign %s)", campaign.pk)


def cancel_pending_for_campaign(campaign):
    """Delete not-yet-sent outbox rows on campaign recall. Sent messages
    cannot be recalled from Telegram."""
    from .models import Notification

    return TelegramMessage.objects.filter(
        notification__in=Notification.objects.filter(dedupe_key=campaign.dedupe_key),
        status__in=[TelegramMessage.STATUS_PENDING, TelegramMessage.STATUS_SENDING],
    ).delete()[0]


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
        .select_related('connection')
        .order_by('created_at')
    )


def _finish(message, status, error=''):
    message.status = status
    message.error = error[:200]
    message.sent_at = timezone.now() if status == TelegramMessage.STATUS_SENT else message.sent_at
    message.save(update_fields=['status', 'error', 'sent_at', 'updated_at'])


def deliver_pending(limit=DEFAULT_RUN_LIMIT):
    """Send queued messages, pacing to Telegram's rate budget.

    Returns {'sent': n, 'failed': n, 'remaining': n}. On a 429 the whole
    run stops and unclaimed rows return to pending; the next cron tick
    resumes. Delivery is at-least-once, bounded by MAX_ATTEMPTS.
    """
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
            conn = message.connection
            if conn is None or not conn.notifications_enabled or conn.blocked_at:
                _finish(message, TelegramMessage.STATUS_FAILED, 'connection_gone')
                failed += 1
                continue

            # Send to the connection's LIVE chat id: if the user re-linked a
            # different Telegram account, message.chat_id is a stale record.
            ok, retry_after, description = send_telegram_message(
                conn.platform_user_id, message.text, connection=conn
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
