from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from campaigns.models import CampaignRedirectHit


class Command(BaseCommand):
    help = 'Delete campaign redirect hits older than the retention window (default 90 days).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=settings.CAMPAIGN_HIT_RETENTION_DAYS,
            help='Retention window in days.',
        )
        parser.add_argument('--dry-run', action='store_true', help='Only report what would be deleted.')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(days=options['days'])
        queryset = CampaignRedirectHit.objects.filter(occurred_at__lt=cutoff)
        count = queryset.count()
        if options['dry_run']:
            self.stdout.write(f'Would delete {count} redirect hits older than {cutoff.isoformat()}.')
            return
        queryset.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} redirect hits older than {cutoff.isoformat()}.'))
