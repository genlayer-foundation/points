from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from validators.models import ValidatorWallet, ValidatorWalletStatusSnapshot


class Command(BaseCommand):
    help = 'Backfill ValidatorWalletStatusSnapshot records using current wallet status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to backfill (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the backfill without making changes'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        today = timezone.now().date()

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        self.stdout.write(self.style.WARNING(
            'NOTE: This command uses each wallet\'s CURRENT status for all historical days. '
            'If a wallet\'s status changed over time, backfilled data will not reflect the '
            'actual historical status. Intended for initial bootstrap only.'
        ))

        wallets = ValidatorWallet.objects.all()
        total_created = 0

        self.stdout.write(f'Backfilling {days} days of snapshots for {wallets.count()} wallets...')

        for wallet in wallets:
            for day_offset in range(days):
                date = today - timedelta(days=day_offset)
                if not dry_run:
                    _, created = ValidatorWalletStatusSnapshot.objects.get_or_create(
                        wallet=wallet,
                        date=date,
                        defaults={'status': wallet.status}
                    )
                    if created:
                        total_created += 1
                else:
                    exists = ValidatorWalletStatusSnapshot.objects.filter(
                        wallet=wallet, date=date
                    ).exists()
                    if not exists:
                        total_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Backfill complete! Created {total_created} snapshot records.'
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
