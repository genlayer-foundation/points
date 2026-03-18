"""
Management command to clean up expired authentication nonces.

Run manually:
    python manage.py cleanup_nonces

Schedule with cron (recommended daily):
    0 3 * * * cd /path/to/backend && python manage.py cleanup_nonces

Or use Django-celery-beat for scheduled tasks.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from ethereum_auth.models import Nonce


class Command(BaseCommand):
    help = 'Clean up expired and used nonces from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Delete nonces that expired more than this many hours ago (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        dry_run = options['dry_run']
        
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Find nonces to delete:
        # 1. Expired nonces older than cutoff
        # 2. Used nonces (regardless of age, they're no longer needed)
        expired_nonces = Nonce.objects.filter(expires_at__lt=cutoff_time)
        used_nonces = Nonce.objects.filter(used=True, created_at__lt=cutoff_time)
        
        expired_count = expired_nonces.count()
        used_count = used_nonces.count()
        
        # Get total count of nonces to delete (combine queries)
        nonces_to_delete = Nonce.objects.filter(
            models.Q(expires_at__lt=cutoff_time) |
            models.Q(used=True, created_at__lt=cutoff_time)
        )
        total_count = nonces_to_delete.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {total_count} nonces '
                    f'({expired_count} expired, {used_count} used)'
                )
            )
        else:
            deleted_count, _ = nonces_to_delete.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} nonces'
                )
            )
        
        # Report remaining nonces
        remaining = Nonce.objects.count()
        self.stdout.write(f'Remaining nonces in database: {remaining}')


# Import models for Q objects
from django.db import models
