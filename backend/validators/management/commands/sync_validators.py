"""
Management command to sync validator wallets from GenLayer blockchain.
Should be run via cron every 5 minutes:
    */5 * * * * python manage.py sync_validators
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from validators.genlayer_validators_service import GenLayerValidatorsService
from validators.models import ValidatorWallet


class Command(BaseCommand):
    help = 'Sync validator wallets from GenLayer blockchain to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about each validator',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting validator wallet sync...'))

        dry_run = options.get('dry_run', False)
        verbose = options.get('verbose', False)

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: No changes will be made'))

        try:
            service = GenLayerValidatorsService()

            # Fetch data from chain
            active = service.fetch_active_validators()
            banned = service.fetch_banned_validators()

            self.stdout.write(f'Chain data: {len(active)} active, {len(banned)} banned/quarantined')

            if verbose:
                self.stdout.write('\n--- Banned/Quarantined from chain ---')
                for b in banned:
                    status = 'permanently banned' if b['permanently_banned'] else 'quarantined'
                    self.stdout.write(f"  {b['address'][:10]}... - {status} (epoch: {b['until_epoch_banned']})")

            if dry_run:
                # Show current DB state
                db_stats = ValidatorWallet.objects.values('status').annotate(
                    count=Count('status')
                ).order_by('status')
                self.stdout.write('\n--- Current DB state ---')
                for stat in db_stats:
                    self.stdout.write(f"  {stat['status']}: {stat['count']}")
                self.stdout.write(self.style.SUCCESS('\nDry run completed'))
                return

            # Perform actual sync
            stats = service.sync_all_validators()

            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSync completed: '
                    f'{stats["created"]} created, '
                    f'{stats["updated"]} updated, '
                    f'{stats["errors"]} errors'
                )
            )

            # Show final DB state by status
            db_stats = ValidatorWallet.objects.values('status').annotate(
                count=Count('status')
            ).order_by('status')

            self.stdout.write('\n--- Database state after sync ---')
            for stat in db_stats:
                self.stdout.write(f"  {stat['status']}: {stat['count']}")

            if stats['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nWarning: {stats["errors"]} errors occurred during sync'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Sync failed: {str(e)}')
            )
            raise
