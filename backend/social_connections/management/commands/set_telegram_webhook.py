"""Register the Telegram webhook. Run once per environment (and after
changing TELEGRAM_WEBHOOK_SECRET):

    python manage.py set_telegram_webhook --url https://<api-host>/api/webhooks/telegram/
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from social_connections.telegram import redact_token, telegram_api_url


class Command(BaseCommand):
    help = "Register the Telegram bot webhook with the secret token."

    def add_arguments(self, parser):
        parser.add_argument('--url', required=True, help='Public webhook URL')

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError('TELEGRAM_BOT_TOKEN is not configured')
        if not settings.TELEGRAM_WEBHOOK_SECRET:
            raise CommandError('TELEGRAM_WEBHOOK_SECRET is not configured')

        try:
            response = requests.post(
                telegram_api_url('setWebhook'),
                json={
                    'url': options['url'],
                    'secret_token': settings.TELEGRAM_WEBHOOK_SECRET,
                    'allowed_updates': ['message'],
                },
                timeout=10,
            )
        except requests.RequestException as exc:
            # Transport errors embed the request URL, which contains the token.
            raise CommandError(f'setWebhook request failed: {redact_token(exc)}')
        self.stdout.write(f"{response.status_code}: {response.text}")
        if not response.ok:
            raise CommandError('setWebhook failed')
