from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from contributions.models import Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier, update_user_leaderboard_entries
from django.db.models import Q
from datetime import datetime, timedelta
import pytz
import decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Adds daily uptime contributions for validators with active wallets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without making changes'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Increase output verbosity'
        )
        parser.add_argument(
            '--points',
            type=int,
            default=1,
            help='Points to assign for each daily uptime contribution (default: 1)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if no multipliers exist (will use 1.0 as multiplier)'
        )
        parser.add_argument(
            '--network',
            type=str,
            choices=['asimov', 'bradbury'],
            help='Only process a specific network (default: all networks)'
        )

    def handle(self, *args, **options):
        from validators.models import ValidatorWallet, Validator, ValidatorWalletStatusSnapshot

        dry_run = options['dry_run']
        verbose = options['verbose']
        points = options['points']
        force = options['force']
        network_filter = options.get('network')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        self.stdout.write(self.style.SUCCESS('Starting daily uptime generation...'))

        # Get the uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name='Uptime')
            self.stdout.write(f'Found uptime contribution type: {uptime_type.name} (ID: {uptime_type.id})')
        except ContributionType.DoesNotExist:
            self.stdout.write(self.style.ERROR('Error: Uptime contribution type not found'))
            return

        # Determine which networks to process
        from django.conf import settings as django_settings
        networks_to_process = [network_filter] if network_filter else list(django_settings.TESTNET_NETWORKS.keys())
        lookback_days = django_settings.UPTIME_LOOKBACK_DAYS

        self.stdout.write(f'Networks to process: {networks_to_process}')
        self.stdout.write(f'Lookback window: {lookback_days} days')

        # Track stats
        total_users = 0
        total_new_contributions = 0
        multiplier_errors = 0
        users_to_update_leaderboard = []
        network_stats = {n: 0 for n in networks_to_process}

        # Current date
        today = timezone.now().date()
        lookback_start = today - timedelta(days=lookback_days)

        # Get all validators with linked wallets
        validators = Validator.objects.filter(
            validator_wallets__isnull=False
        ).distinct().select_related('user')
        total_users = validators.count()

        self.stdout.write(f'Found {total_users} validators with linked wallets')

        for validator in validators:
            user = validator.user

            for network in networks_to_process:
                # Check if user has wallets on this network
                network_wallets = ValidatorWallet.objects.filter(
                    operator=validator,
                    network=network
                )

                if not network_wallets.exists():
                    if verbose:
                        self.stdout.write(f'  {user}: No wallets on {network}, skipping')
                    continue

                # Check if ANY wallet was active in the lookback window
                has_active_in_window = ValidatorWalletStatusSnapshot.objects.filter(
                    wallet__in=network_wallets,
                    date__gte=lookback_start,
                    date__lte=today,
                    status='active'
                ).exists()

                if not has_active_in_window:
                    if verbose:
                        self.stdout.write(f'  {user}: No active wallets on {network} in lookback window, skipping')
                    continue

                # Check for existing uptime contribution for this user/date/network
                # For asimov, also match legacy contributions without any network marker
                # (old format: "Auto-generated daily uptime for 2025-12-01")
                today_contributions = Contribution.objects.filter(
                    user=user,
                    contribution_type=uptime_type,
                    contribution_date__date=today,
                )
                if network == 'asimov':
                    existing = today_contributions.filter(
                        Q(notes__contains='(asimov)') |
                        (~Q(notes__contains='(asimov)') & ~Q(notes__contains='(bradbury)'))
                    ).exists()
                else:
                    existing = today_contributions.filter(
                        notes__contains=f'({network})'
                    ).exists()

                if existing:
                    if verbose:
                        self.stdout.write(f'  {user}: Uptime for {network} on {today} already exists, skipping')
                    continue

                # Get the active multiplier for today
                contribution_date = datetime.combine(
                    today,
                    datetime.min.time(),
                    tzinfo=pytz.UTC
                )

                used_force_multiplier = False
                try:
                    _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                        uptime_type,
                        at_date=contribution_date
                    )
                except GlobalLeaderboardMultiplier.DoesNotExist:
                    if force:
                        used_force_multiplier = True
                        multiplier_value = decimal.Decimal('1.0')
                        self.stdout.write(
                            self.style.WARNING(
                                f'  {today}: No multiplier found, using default of 1.0 (--force enabled)'
                            )
                        )
                    else:
                        multiplier_errors += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'  {today}: No multiplier found for "Uptime". Use --force to override.'
                            )
                        )
                        continue

                frozen_global_points = round(points * float(multiplier_value))

                if verbose:
                    self.stdout.write(
                        f'  {user}: Adding uptime for {network} on {today} '
                        f'({points} points x {multiplier_value} = {frozen_global_points} global points)'
                    )

                if not dry_run:
                    contribution = Contribution(
                        user=user,
                        contribution_type=uptime_type,
                        points=points,
                        contribution_date=contribution_date,
                        multiplier_at_creation=multiplier_value,
                        frozen_global_points=frozen_global_points,
                        notes=f'Auto-generated daily uptime for {today} ({network})'
                    )
                    if used_force_multiplier:
                        # Keep Contribution.save() and post_save side effects while honoring --force.
                        contribution._allow_missing_multiplier = True
                    contribution.save()

                    if user not in users_to_update_leaderboard:
                        users_to_update_leaderboard.append(user)

                total_new_contributions += 1
                network_stats[network] += 1

        # Update leaderboard entries for all affected users
        if users_to_update_leaderboard and not dry_run:
            self.stdout.write('Updating leaderboard entries...')

            for user in users_to_update_leaderboard:
                update_user_leaderboard_entries(user)
                if verbose:
                    self.stdout.write(f'Updated leaderboard entries for {user}')

        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'Daily uptime generation completed!\n'
            f'- Validators with wallets: {total_users}\n'
            f'- New uptime contributions added: {total_new_contributions}\n'
            f'- Per-network breakdown: {network_stats}\n'
            f'- Dates skipped due to missing multipliers: {multiplier_errors}'
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
