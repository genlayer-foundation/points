"""Local development loop: feed bot updates without a public webhook URL.

    python manage.py run_telegram_polling

Deletes any registered webhook first (Telegram forbids getUpdates while a
webhook is set). Dev only; production uses the webhook.
"""
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from social_connections.telegram import redact_token, telegram_api_url
from social_connections.telegram_bot import handle_update

RETRY_BACKOFF_SECONDS = 5


class Command(BaseCommand):
    help = "Long-poll Telegram getUpdates and handle updates (local dev only)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete-webhook',
            action='store_true',
            help='Delete a registered webhook before polling. Required when one '
                 'is set: without this guard, running the command with a '
                 'production token would silently disable production intake.',
        )

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN is not configured')

        # Telegram forbids getUpdates while a webhook is registered, and a
        # registered webhook almost certainly means this token belongs to a
        # deployed environment. Refuse to hijack it by accident.
        try:
            info = requests.get(telegram_api_url('getWebhookInfo'), timeout=10).json()
            webhook_url = (info.get('result') or {}).get('url', '')
            if webhook_url:
                if not options['delete_webhook']:
                    raise CommandError(
                        f'A webhook is registered ({webhook_url}): this token looks '
                        'like a deployed environment. Re-run with --delete-webhook '
                        'if you really want to take over its updates.'
                    )
                requests.post(telegram_api_url('deleteWebhook'), timeout=10)
                self.stdout.write(f'Deleted webhook {webhook_url}')
        except requests.RequestException as exc:
            # Transport errors embed the request URL, which contains the token.
            raise CommandError(f'Telegram API unreachable: {redact_token(exc)}')
        self.stdout.write('Polling Telegram for updates (Ctrl+C to stop)...')

        offset = None
        while True:
            try:
                response = requests.get(
                    telegram_api_url('getUpdates'),
                    params={
                        'timeout': 30,
                        'offset': offset,
                        'allowed_updates': '["message"]',
                    },
                    timeout=40,
                )
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self.stderr.write(f"getUpdates error: {redact_token(exc)}")
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue

            # An invalid/revoked token answers instantly with a 4xx; without
            # this check the loop would hammer Telegram at full speed forever.
            if response.status_code in (401, 403, 404):
                raise CommandError(
                    f'getUpdates rejected ({response.status_code}): '
                    'is TELEGRAM_BOT_TOKEN valid?'
                )

            try:
                payload = response.json()
            except ValueError:
                payload = {}
            if not response.ok or not payload.get('ok', False):
                self.stderr.write(
                    f"getUpdates failed ({response.status_code}): "
                    f"{redact_token(payload.get('description', response.text))[:200]}"
                )
                time.sleep(RETRY_BACKOFF_SECONDS)
                continue
            updates = payload.get('result', [])

            for update in updates:
                offset = update['update_id'] + 1
                try:
                    handle_update(update)
                except Exception as exc:
                    self.stderr.write(
                        f"update {update.get('update_id')} failed: {redact_token(exc)}"
                    )
