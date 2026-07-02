"""
Rebuild the observability columns of ValidatorWalletStatusSnapshot from the raw
ValidatorWalletObservation log (worst-of-day latch + sample counters + latest
node version). Useful after a code change to the rollup logic or to repair a gap.

The on-chain `status` column is preserved on existing rows (only set on insert from
the latest observation's on-chain status), so this never disturbs the on-chain sync.
"""
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from validators.grafana_service import (
    _METRICS_SEVERITY,
    _latch,
    _latch_version,
)
from validators.models import ValidatorWalletObservation, ValidatorWalletStatusSnapshot


class Command(BaseCommand):
    help = 'Rebuild daily validator status rollups from the raw observation log'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=None,
            help='Only rebuild the last N days of rollups (default: all observations)'
        )

    def handle(self, *args, **options):
        days = options.get('days')
        observations = ValidatorWalletObservation.objects.all()
        if days is not None:
            # Snap the cutoff to a local-day boundary: a mid-day cutoff would rebuild
            # the oldest day in range from only part of its observations and overwrite
            # that day's correctly-latched rollup with wrong values.
            cutoff_date = timezone.localdate() - timedelta(days=days)
            cutoff = timezone.make_aware(
                datetime.combine(cutoff_date, time.min),
                timezone.get_current_timezone(),
            )
            observations = observations.filter(observed_at__gte=cutoff)
        observations = observations.order_by('wallet_id', 'observed_at')

        acc = {}
        obs_count = 0
        for obs in observations.iterator():
            obs_count += 1
            key = (obs.wallet_id, timezone.localdate(obs.observed_at))
            agg = acc.get(key)
            if agg is None:
                agg = {
                    'metrics_status': 'unknown',
                    'logs_status': 'unknown',
                    'version_status': 'unknown',
                    'metrics_samples': 0,
                    'logs_samples': 0,
                    'node_version': '',
                    'status': obs.onchain_status,
                }
                acc[key] = agg
            agg['metrics_status'] = _latch(agg['metrics_status'], obs.metrics_status, _METRICS_SEVERITY)
            agg['logs_status'] = _latch(agg['logs_status'], obs.logs_status, _METRICS_SEVERITY)
            agg['version_status'] = _latch_version(agg['version_status'], obs.version_status)
            if obs.metrics_status == 'on':
                agg['metrics_samples'] += 1
            if obs.logs_status == 'on':
                agg['logs_samples'] += 1
            if obs.node_version:
                agg['node_version'] = obs.node_version  # ascending order → latest wins
            agg['status'] = obs.onchain_status

        rollups = [
            ValidatorWalletStatusSnapshot(
                wallet_id=wallet_id,
                date=date,
                status=agg['status'],
                metrics_status=agg['metrics_status'],
                logs_status=agg['logs_status'],
                version_status=agg['version_status'],
                node_version=agg['node_version'],
                metrics_samples=agg['metrics_samples'],
                logs_samples=agg['logs_samples'],
            )
            for (wallet_id, date), agg in acc.items()
        ]

        if rollups:
            ValidatorWalletStatusSnapshot.objects.bulk_create(
                rollups,
                update_conflicts=True,
                unique_fields=['wallet', 'date'],
                update_fields=[
                    'metrics_status', 'logs_status', 'version_status',
                    'node_version', 'metrics_samples', 'logs_samples',
                ],
            )

        self.stdout.write(self.style.SUCCESS(
            f'Rebuilt {len(rollups)} daily rollup(s) from {obs_count} observation(s).'
        ))
