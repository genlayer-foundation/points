"""Local development loop: feed bot updates without a public webhook URL.

    python manage.py run_telegram_polling

Deletes any registered webhook first (Telegram forbids getUpdates while a
webhook is set). Dev only; production uses the webhook.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from social_connections.telegram import telegram_api_url
from social_connections.telegram_bot import handle_update


class Command(BaseCommand):
    help = "Long-poll Telegram getUpdates and handle updates (local dev only)."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN is not configured')

        requests.post(telegram_api_url('deleteWebhook'), timeout=10)
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
                updates = response.json().get('result', [])
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                self.stderr.write(f"getUpdates error: {exc}")
                continue

            for update in updates:
                offset = update['update_id'] + 1
                try:
                    handle_update(update)
                except Exception as exc:
                    self.stderr.write(f"update {update.get('update_id')} failed: {exc}")
