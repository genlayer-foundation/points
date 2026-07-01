import math
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from ethereum_auth.models import Nonce


class Command(BaseCommand):
    help = 'Remove expired SIWE nonces and used SIWE nonces older than the cleanup threshold.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=float,
            default=1,
            help=(
                'Delete nonces expired more than this many hours ago and used '
                'nonces created more than this many hours ago (default: 1).'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show how many nonces would be deleted without removing them.',
        )

    def handle(self, *args, **options):
        hours = options['hours']
        if not math.isfinite(hours) or hours < 0:
            raise CommandError('--hours must be a finite number greater than or equal to 0')

        try:
            cutoff = timezone.now() - timedelta(hours=hours)
        except OverflowError as exc:
            raise CommandError('--hours is too large') from exc

        stale_nonces = Nonce.objects.filter(
            Q(expires_at__lte=cutoff) | Q(used=True, created_at__lte=cutoff)
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
