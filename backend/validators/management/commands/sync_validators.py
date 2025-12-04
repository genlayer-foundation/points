"""
Management command to sync validator wallets from GenLayer blockchain.
Should be run via cron every 5 minutes:
    */5 * * * * python manage.py sync_validators
"""
from django.core.management.base import BaseCommand
from validators.genlayer_validators_service import GenLayerValidatorsService


class Command(BaseCommand):
    help = 'Sync validator wallets from GenLayer blockchain to database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes to the database',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting validator wallet sync...'))

        dry_run = options.get('dry_run', False)
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN: No changes will be made'))

        try:
            service = GenLayerValidatorsService()

            if dry_run:
                # Just fetch and display counts
                active = service.fetch_active_validators()
                banned = service.fetch_banned_validators()

                self.stdout.write(f'Active validators: {len(active)}')
                self.stdout.write(f'Banned validators: {len(banned)}')
                self.stdout.write(self.style.SUCCESS('Dry run completed'))
                return

            # Perform actual sync
            stats = service.sync_all_validators()

            self.stdout.write(
                self.style.SUCCESS(
                    f'Sync completed: '
                    f'{stats["created"]} created, '
                    f'{stats["updated"]} updated, '
                    f'{stats["errors"]} errors'
                )
            )

            if stats['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Warning: {stats["errors"]} errors occurred during sync'
                    )
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Sync failed: {str(e)}')
            )
            raise
