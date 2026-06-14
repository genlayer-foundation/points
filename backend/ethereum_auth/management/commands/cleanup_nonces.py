from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from ethereum_auth.models import Nonce


class Command(BaseCommand):
    help = 'Remove used or expired SIWE nonces after a configurable grace period.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=float,
            default=1,
            help='Keep stale nonces for this many hours after their expiry time (default: 1).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many nonces would be deleted without removing them.',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        if hours < 0:
            raise CommandError('--hours must be greater than or equal to 0')

        cutoff = timezone.now() - timedelta(hours=hours)
        stale_nonces = Nonce.objects.filter(
            Q(used=True) | Q(expires_at__lte=timezone.now()),
            expires_at__lte=cutoff,
        )
        count = stale_nonces.count()

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING(
                    f'Dry run: {count} stale nonce(s) would be deleted.'
                )
            )
            return

        deleted_count, _ = stale_nonces.delete()
        self.stdout.write(
            self.style.SUCCESS(f'Deleted {deleted_count} stale nonce(s).')
        )
