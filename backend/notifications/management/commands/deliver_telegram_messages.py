"""Drain the Telegram delivery outbox from the CLI (dev/ops convenience;
production uses the cron-triggered /api/v1/notifications/telegram/deliver/)."""
from django.core.management.base import BaseCommand

from notifications.telegram import DEFAULT_RUN_LIMIT, deliver_pending


class Command(BaseCommand):
    help = "Send pending Telegram notification messages."

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=DEFAULT_RUN_LIMIT)

    def handle(self, *args, **options):
        stats = deliver_pending(limit=options['limit'])
        self.stdout.write(
            f"sent={stats['sent']} failed={stats['failed']} remaining={stats['remaining']}"
        )
