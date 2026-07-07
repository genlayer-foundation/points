"""Thin Telegram Bot API client for outbound messages.

Plain requests calls, no bot framework. Shared by the interactive webhook
replies (social_connections.telegram_bot) and the notification delivery
drain (notifications.telegram).
"""
import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

TELEGRAM_MAX_LEN = 4096
REQUEST_TIMEOUT = 10


def telegram_api_url(method):
    return f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"


def escape(text):
    """Escape user-derived content for Telegram HTML parse mode."""
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def truncate(text, limit=TELEGRAM_MAX_LEN):
    """Final safety net for Telegram's 4096-char message limit.

    Callers should truncate the plain-text segments before assembling HTML;
    if this cut ever lands inside a tag, the parse-error fallback in
    send_telegram_message() still delivers the message without formatting.
    """
    if len(text) <= limit:
        return text
    return text[: limit - 1] + '…'


def _mark_blocked(connection):
    if connection is None:
        return
    connection.blocked_at = timezone.now()
    connection.notifications_enabled = False
    connection.save(update_fields=['blocked_at', 'notifications_enabled', 'updated_at'])


def send_telegram_message(
    chat_id, text, *, connection=None, disable_web_page_preview=True, reply_markup=None
):
    """Send one message. Returns (ok, retry_after_seconds_or_None, description).

    reply_markup is an optional Bot API inline keyboard dict (URL buttons).

    Never raises. On 403 (user blocked the bot / account deactivated) the
    connection is disabled so future enqueues skip it; a later successful
    /start re-link clears the flag. On a 400 the message is retried in
    degraded form (drop HTML formatting, then the buttons) so a rendering
    bug never bricks a delivery.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        return False, None, 'bot_token_not_configured'

    payload = {
        'chat_id': chat_id,
        'text': truncate(text),
        'parse_mode': 'HTML',
        'disable_web_page_preview': disable_web_page_preview,
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup

    # Original attempt + up to two degraded retries (no parse_mode, no buttons).
    for _ in range(3):
        try:
            response = requests.post(
                telegram_api_url('sendMessage'), json=payload, timeout=REQUEST_TIMEOUT
            )
        except requests.RequestException as exc:
            logger.warning(f"Telegram sendMessage transport error: {exc}")
            return False, None, f'request_error:{exc.__class__.__name__}'

        if response.status_code == 200:
            return True, None, ''

        try:
            description = str(response.json().get('description', ''))
        except ValueError:
            description = response.text or ''

        if response.status_code == 403:
            _mark_blocked(connection)
            return False, None, 'blocked'

        if response.status_code == 429:
            try:
                retry_after = int(response.json()['parameters']['retry_after'])
            except (ValueError, KeyError, TypeError):
                retry_after = 5
            return False, retry_after, 'rate_limited'

        if response.status_code == 400:
            lowered = description.lower()
            # Broken HTML assembly (bad truncation, unescaped content):
            # retry as plain text so the message still lands.
            if "can't parse entities" in lowered and payload.pop('parse_mode', None):
                continue
            # Rejected inline button (e.g. BUTTON_URL_INVALID): retry without it.
            if ('button' in lowered or 'url' in lowered) and payload.pop('reply_markup', None):
                continue

        logger.warning(
            f"Telegram sendMessage failed ({response.status_code}): {description[:200]}"
        )
        return False, None, description[:200] or f'http_{response.status_code}'

    return False, None, 'unreachable'
