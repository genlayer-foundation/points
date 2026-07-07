"""Telegram bot: account linking, webhook, and command handling.

Linking uses a deep-link start payload instead of OAuth (Telegram has none):
the portal issues a one-time token, the user opens
https://t.me/<bot>?start=<token>, and the webhook binds the sender's
permanent numeric Telegram id to the portal account that requested the token.

The webhook is stateless by design: every command is a one-shot
request/response, so no conversation state machine exists. All state lives in
TelegramConnection and the TelegramMessage log.
"""
import hmac
import json
import logging
import secrets

from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import PendingOAuthState, TelegramConnection, TelegramMessage
from .telegram import escape, send_telegram_message

logger = logging.getLogger(__name__)

LINK_TOKEN_MAX_AGE_MINUTES = 15

HELP_TEXT = (
    "🤖 <b>GenLayer Portal bot</b>\n\n"
    "/rank – your leaderboard positions\n"
    "/points – your points totals\n"
    "/missions – active missions\n"
    "/mute – pause portal notifications\n"
    "/unmute – resume portal notifications\n"
    "/unlink – disconnect this Telegram account\n"
    "/help – this message"
)


# ---------------------------------------------------------------------------
# Portal-facing endpoints (session-authenticated)
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def telegram_link_token(request):
    """Issue a one-time deep-link token binding this session's user."""
    if not settings.TELEGRAM_BOT_USERNAME or not settings.TELEGRAM_BOT_TOKEN:
        return Response(
            {'error': 'telegram_not_configured'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    PendingOAuthState.cleanup_old(minutes=LINK_TOKEN_MAX_AGE_MINUTES)
    token = secrets.token_urlsafe(32)  # 43 chars of [A-Za-z0-9_-]: valid start payload
    PendingOAuthState.objects.create(
        state_id=token,
        platform='telegram',
        user=request.user,
    )
    return Response({
        'deep_link': f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}",
        'expires_in_minutes': LINK_TOKEN_MAX_AGE_MINUTES,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def telegram_disconnect(request):
    """Unlink the current user's Telegram account. Idempotent."""
    _delete_connection(TelegramConnection.objects.filter(user=request.user).first())
    return Response({'disconnected': True})


def _delete_connection(connection):
    if connection is None:
        return
    TelegramMessage.objects.filter(
        connection=connection,
        status__in=[TelegramMessage.STATUS_PENDING, TelegramMessage.STATUS_SENDING],
    ).delete()
    connection.delete()


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------

@csrf_exempt
def telegram_webhook(request):
    """Receive Telegram updates.

    Auth: Telegram echoes TELEGRAM_WEBHOOK_SECRET in a header on every call
    (set via setWebhook). An unset secret rejects everything.

    Always returns 200 after auth, even on handler errors: Telegram retries
    non-200 responses, and a poison update must not loop forever. Replays are
    harmless because every command is idempotent (token consume is atomic;
    mute/unlink are idempotent; the rest are read-only).
    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    provided = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    if not settings.TELEGRAM_WEBHOOK_SECRET or not hmac.compare_digest(
        provided, settings.TELEGRAM_WEBHOOK_SECRET
    ):
        return HttpResponseForbidden('invalid webhook secret')

    try:
        update = json.loads(request.body)
        handle_update(update)
    except Exception:
        logger.exception("Telegram webhook update handling failed")
    return JsonResponse({'ok': True})


def handle_update(update):
    """Process one Telegram update. Shared by the webhook and dev polling."""
    message = update.get('message') or {}
    chat = message.get('chat') or {}
    sender = message.get('from') or {}
    text = message.get('text')
    if chat.get('type') != 'private' or not text or sender.get('id') is None:
        return

    chat_id = str(chat['id'])
    connection = (
        TelegramConnection.objects
        .filter(platform_user_id=str(sender['id']))
        .select_related('user')
        .first()
    )
    # Permanent inbound log: conversation memory for a future per-user agent.
    TelegramMessage.objects.create(
        direction=TelegramMessage.DIRECTION_IN,
        connection=connection,
        chat_id=chat_id,
        text=text,
    )

    parts = text.strip().split()
    command = parts[0].lower().split('@')[0] if parts else ''

    if command == '/start':
        _handle_start(chat_id, sender, parts[1] if len(parts) > 1 else '', connection)
        return

    if connection is None:
        _reply(
            chat_id, None,
            "This Telegram account isn't linked to a portal account yet.\n"
            f"Open your profile at {settings.FRONTEND_URL} and press \"Link Telegram\".",
        )
        return

    handler = {
        '/help': _handle_help,
        '/rank': _handle_rank,
        '/points': _handle_points,
        '/missions': _handle_missions,
        '/mute': _handle_mute,
        '/unmute': _handle_unmute,
        '/unlink': _handle_unlink,
    }.get(command, _handle_help)
    handler(chat_id, connection)


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

def _reply(chat_id, connection, text):
    ok, _, description = send_telegram_message(chat_id, text, connection=connection)
    TelegramMessage.objects.create(
        direction=TelegramMessage.DIRECTION_OUT,
        connection=connection if connection and connection.pk else None,
        chat_id=chat_id,
        text=text,
        status=TelegramMessage.STATUS_SENT if ok else TelegramMessage.STATUS_FAILED,
        error='' if ok else description,
        attempts=1,
        sent_at=timezone.now() if ok else None,
    )


def _handle_start(chat_id, sender, token, connection):
    if not token:
        _reply(
            chat_id, connection,
            "Welcome! To link this Telegram account, open your portal profile at "
            f"{settings.FRONTEND_URL} and press \"Link Telegram\".",
        )
        return

    pending = PendingOAuthState.consume_deep_link(
        token, 'telegram', max_age_minutes=LINK_TOKEN_MAX_AGE_MINUTES
    )
    if pending is None:
        _reply(
            chat_id, connection,
            "This link expired or was already used. "
            "Get a fresh one from your portal profile.",
        )
        return

    telegram_id = str(sender['id'])
    already_linked_reply = (
        "This Telegram account is already linked to a different portal account. "
        "Unlink it there first (/unlink) if you want to move it."
    )
    if (
        TelegramConnection.objects
        .exclude(user=pending.user)
        .filter(platform_user_id=telegram_id)
        .exists()
    ):
        _reply(chat_id, connection, already_linked_reply)
        return

    try:
        connection, _ = TelegramConnection.objects.update_or_create(
            user=pending.user,
            defaults={
                'platform_user_id': telegram_id,
                'platform_username': sender.get('username') or '',
                'linked_at': timezone.now(),
                'notifications_enabled': True,
                'blocked_at': None,
            },
        )
    except IntegrityError:
        # Lost the race with a concurrent /start for the same Telegram id;
        # the unique constraint on platform_user_id is the real guard.
        _reply(chat_id, connection, already_linked_reply)
        return
    display_name = pending.user.name or pending.user.email
    _reply(
        chat_id, connection,
        f"✅ Linked to <b>{escape(display_name)}</b>. "
        "You'll now receive portal notifications here.\n\n" + HELP_TEXT,
    )


def _handle_help(chat_id, connection):
    _reply(chat_id, connection, HELP_TEXT)


def _leaderboard_lines(user):
    from leaderboard.models import LeaderboardEntry

    lines = []
    for entry in LeaderboardEntry.objects.filter(user=user).order_by('type'):
        rank = f"#{entry.rank}" if entry.rank else "unranked"
        lines.append(
            f"{escape(entry.get_type_display())}: rank {rank}, "
            f"{entry.total_points:,} points"
        )
    return lines


def _handle_rank(chat_id, connection):
    lines = _leaderboard_lines(connection.user)
    if not lines:
        _reply(
            chat_id, connection,
            "No leaderboard entries yet. Submit your first contribution at "
            f"{settings.FRONTEND_URL}/submit-contribution",
        )
        return
    _reply(chat_id, connection, "🏆 <b>Your leaderboard positions</b>\n" + "\n".join(lines))


def _handle_points(chat_id, connection):
    lines = _leaderboard_lines(connection.user)
    if not lines:
        _reply(
            chat_id, connection,
            "No points yet. Submit your first contribution at "
            f"{settings.FRONTEND_URL}/submit-contribution",
        )
        return
    _reply(chat_id, connection, "💎 <b>Your points</b>\n" + "\n".join(lines))


def _handle_missions(chat_id, connection):
    from contributions.models import Mission

    now = timezone.now()
    missions = list(
        Mission.objects
        .filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now),
            Q(end_date__isnull=True) | Q(end_date__gte=now),
        )
        .select_related('contribution_type')
        .order_by('-created_at')[:10]
    )
    if not missions:
        _reply(chat_id, connection, "No active missions right now. Check back soon!")
        return

    lines = []
    for mission in missions:
        url = f"{settings.FRONTEND_URL}/contribution-type/{mission.contribution_type_id}"
        line = f"• <a href=\"{url}\">{escape(mission.name)}</a>"
        remaining = mission.submissions_remaining()
        if mission.is_full():
            line += " (full)"
        elif remaining is not None:
            line += f" ({remaining} submissions left)"
        if mission.end_date:
            line += f" – ends {mission.end_date.strftime('%b %d')}"
        lines.append(line)
    _reply(chat_id, connection, "🎯 <b>Active missions</b>\n" + "\n".join(lines))


def _handle_mute(chat_id, connection):
    connection.notifications_enabled = False
    connection.save(update_fields=['notifications_enabled', 'updated_at'])
    _reply(chat_id, connection, "Notifications muted. Send /unmute to resume.")


def _handle_unmute(chat_id, connection):
    connection.notifications_enabled = True
    connection.save(update_fields=['notifications_enabled', 'updated_at'])
    _reply(chat_id, connection, "Notifications resumed.")


def _handle_unlink(chat_id, connection):
    _delete_connection(connection)
    _reply(
        chat_id, None,
        "Telegram account unlinked. You can re-link anytime from your portal profile.",
    )
