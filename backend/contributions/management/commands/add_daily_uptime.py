from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from contributions.models import Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier, update_all_ranks, update_user_leaderboard_entries, update_referrer_points
from django.db.models import Q
from datetime import datetime, timedelta
import pytz
import decimal

MAX_DATE_RANGE_DAYS = 366

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
        parser.add_argument(
            '--date',
            type=str,
            help='Process a specific date (YYYY-MM-DD) instead of today'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date for range processing (YYYY-MM-DD, inclusive)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for range processing (YYYY-MM-DD, inclusive)'
        )

    def _parse_date(self, date_str):
        """Parse a YYYY-MM-DD string into a date object."""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            raise ValueError(f'Invalid date format: {date_str}. Use YYYY-MM-DD.')

    def _get_dates_to_process(self, options):
        """Determine which dates to process based on command options."""
        single_date = options.get('date')
        start_date = options.get('start_date')
        end_date = options.get('end_date')

        if single_date:
            if start_date or end_date:
                raise ValueError('Cannot use --date with --start-date or --end-date')
            return [self._parse_date(single_date)]

        if start_date and end_date:
            start = self._parse_date(start_date)
            end = self._parse_date(end_date)
            if start > end:
                raise ValueError(f'Start date {start} is after end date {end}')
            if (end - start).days > MAX_DATE_RANGE_DAYS:
                raise ValueError(
                    f'Date range exceeds {MAX_DATE_RANGE_DAYS} days. '
                    f'Process in smaller batches to avoid memory issues.'
                )
            dates = []
            current = start
            while current <= end:
                dates.append(current)
                current += timedelta(days=1)
            return dates

        if start_date or end_date:
            raise ValueError('Both --start-date and --end-date are required for range processing')

        # Default: today
        return [timezone.now().date()]

    def _check_active_in_window(self, network_wallets, target_date, lookback_days, ValidatorWalletStatusSnapshot):
        """
        Check if any wallet was active in the lookback window.
        Falls back to current wallet status if no snapshots exist for the target date,
        but only for recent dates (today or yesterday) to avoid granting incorrect
        historical points when current status differs from past status.
        Returns (is_active, used_fallback).
        """
        lookback_start = target_date - timedelta(days=lookback_days)

        # Check snapshots in the lookback window
        has_active_in_window = ValidatorWalletStatusSnapshot.objects.filter(
            wallet__in=network_wallets,
            date__gte=lookback_start,
            date__lte=target_date,
            status='active'
        ).exists()

        if has_active_in_window:
            return True, False

        # Fallback: only for recent dates (today/yesterday) where sync may have been down.
        # For historical backfills, current wallet status may not reflect past status.
        today = timezone.now().date()
        is_recent = (today - target_date).days <= 1

        if is_recent:
            has_any_snapshot = ValidatorWalletStatusSnapshot.objects.filter(
                wallet__in=network_wallets,
                date=target_date
            ).exists()

            if not has_any_snapshot:
                has_active_wallet = network_wallets.filter(status='active').exists()
                if has_active_wallet:
                    return True, True  # Active via fallback

        return False, False

    def _check_existing_contribution(self, user, uptime_type, target_date, network):
        """Check if an uptime contribution already exists for this user/date/network."""
        date_contributions = Contribution.objects.filter(
            user=user,
            contribution_type=uptime_type,
            contribution_date__date=target_date,
        )
        if network == 'asimov':
            # Match (asimov) or legacy contributions without any network marker
            return date_contributions.filter(
                Q(notes__contains='(asimov)') |
                (~Q(notes__contains='(asimov)') & ~Q(notes__contains='(bradbury)'))
            ).exists()
        else:
            return date_contributions.filter(
                notes__contains=f'({network})'
            ).exists()

    def _get_multiplier(self, uptime_type, target_date, force):
        """
        Get the multiplier value for the given date.
        Returns (multiplier_value, error_message).
        """
        contribution_datetime = datetime.combine(
            target_date,
            datetime.min.time(),
            tzinfo=pytz.UTC
        )
        try:
            _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                uptime_type,
                at_date=contribution_datetime
            )
            return multiplier_value, None
        except GlobalLeaderboardMultiplier.DoesNotExist:
            if force:
                return decimal.Decimal('1.0'), 'fallback'
            return None, 'missing'

    def process_date(self, target_date, uptime_type, validators, networks_to_process,
                     lookback_days, points, force, dry_run, verbose,
                     ValidatorWallet, ValidatorWalletStatusSnapshot):
        """
        Process a single date: create uptime contributions for eligible validators.
        Returns (contributions_to_create, users_affected, network_stats, multiplier_errors).
        """
        contributions_to_create = []
        users_affected = set()
        network_stats = {n: 0 for n in networks_to_process}
        multiplier_errors = 0

        # Cache multiplier per date (same for all users on same date)
        multiplier_value, mult_error = self._get_multiplier(uptime_type, target_date, force)

        if mult_error == 'missing':
            self.stdout.write(
                self.style.ERROR(
                    f'  {target_date}: No multiplier found for "Uptime". Use --force to override.'
                )
            )
            return contributions_to_create, users_affected, network_stats, 1

        if mult_error == 'fallback':
            self.stdout.write(
                self.style.WARNING(
                    f'  {target_date}: No multiplier found, using default of 1.0 (--force enabled)'
                )
            )

        frozen_global_points = round(points * float(multiplier_value))
        contribution_datetime = datetime.combine(
            target_date,
            datetime.min.time(),
            tzinfo=pytz.UTC
        )

        for validator in validators:
            user = validator.user

            for network in networks_to_process:
                network_wallets = ValidatorWallet.objects.filter(
                    operator=validator,
                    network=network
                )

                if not network_wallets.exists():
                    if verbose:
                        self.stdout.write(f'  {user}: No wallets on {network}, skipping')
                    continue

                # Check activity in lookback window
                is_active, used_fallback = self._check_active_in_window(
                    network_wallets, target_date, lookback_days, ValidatorWalletStatusSnapshot
                )

                if not is_active:
                    if verbose:
                        self.stdout.write(f'  {user}: No active wallets on {network} in lookback window, skipping')
                    continue

                if used_fallback:
                    self.stdout.write(
                        self.style.WARNING(
                            f'  {user}: Using current wallet status as fallback for {network} on {target_date} (no snapshots found)'
                        )
                    )

                # Check for existing contribution
                if self._check_existing_contribution(user, uptime_type, target_date, network):
                    if verbose:
                        self.stdout.write(f'  {user}: Uptime for {network} on {target_date} already exists, skipping')
                    continue

                if verbose:
                    self.stdout.write(
                        f'  {user}: Adding uptime for {network} on {target_date} '
                        f'({points} points x {multiplier_value} = {frozen_global_points} global points)'
                    )

                contributions_to_create.append(Contribution(
                    user=user,
                    contribution_type=uptime_type,
                    points=points,
                    contribution_date=contribution_datetime,
                    multiplier_at_creation=multiplier_value,
                    frozen_global_points=frozen_global_points,
                    notes=f'Auto-generated daily uptime for {target_date} ({network})'
                ))
                users_affected.add(user)
                network_stats[network] += 1

        return contributions_to_create, users_affected, network_stats, multiplier_errors

    def handle(self, *args, **options):
        from validators.models import ValidatorWallet, Validator, ValidatorWalletStatusSnapshot

        dry_run = options['dry_run']
        verbose = options['verbose']
        points = options['points']
        force = options['force']
        network_filter = options.get('network')

        # Parse dates
        try:
            dates_to_process = self._get_dates_to_process(options)
        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))

        self.stdout.write(self.style.SUCCESS('Starting daily uptime generation...'))

        # Get the uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name='Uptime')
            self.stdout.write(f'Found uptime contribution type: {uptime_type.name} (ID: {uptime_type.id})')
        except ContributionType.DoesNotExist:
            raise CommandError('Uptime contribution type not found')

        # Determine which networks to process
        from django.conf import settings as django_settings
        networks_to_process = [network_filter] if network_filter else list(django_settings.TESTNET_NETWORKS.keys())
        lookback_days = django_settings.UPTIME_LOOKBACK_DAYS

        self.stdout.write(f'Networks to process: {networks_to_process}')
        self.stdout.write(f'Lookback window: {lookback_days} days')
        self.stdout.write(f'Dates to process: {dates_to_process[0]} to {dates_to_process[-1]} ({len(dates_to_process)} days)')

        # Get all validators with linked wallets
        validators = list(Validator.objects.filter(
            validator_wallets__isnull=False
        ).distinct().select_related('user'))
        total_users = len(validators)

        self.stdout.write(f'Found {total_users} validators with linked wallets')

        # Track global stats
        total_new_contributions = 0
        total_multiplier_errors = 0
        all_users_affected = set()
        all_contributions_to_create = []
        total_network_stats = {n: 0 for n in networks_to_process}

        for target_date in dates_to_process:
            contributions, users, network_stats, mult_errors = self.process_date(
                target_date=target_date,
                uptime_type=uptime_type,
                validators=validators,
                networks_to_process=networks_to_process,
                lookback_days=lookback_days,
                points=points,
                force=force,
                dry_run=dry_run,
                verbose=verbose,
                ValidatorWallet=ValidatorWallet,
                ValidatorWalletStatusSnapshot=ValidatorWalletStatusSnapshot,
            )
            all_contributions_to_create.extend(contributions)
            all_users_affected.update(users)
            total_multiplier_errors += mult_errors
            for n in networks_to_process:
                total_network_stats[n] += network_stats.get(n, 0)

        total_new_contributions = len(all_contributions_to_create)

        # Bulk create contributions (skips save()/clean() and signals for performance)
        # Wrapped in a transaction so partial failures don't leave stale leaderboard state
        if all_contributions_to_create and not dry_run:
            with transaction.atomic():
                self.stdout.write(f'Creating {total_new_contributions} contributions...')
                Contribution.objects.bulk_create(all_contributions_to_create, batch_size=500)

                # Update leaderboard for all affected users
                self.stdout.write(f'Updating leaderboard for {len(all_users_affected)} users...')
                for user in all_users_affected:
                    update_user_leaderboard_entries(user)

                # Update referral points (bulk_create skips post_save signal)
                referrers_updated = set()
                for contribution in all_contributions_to_create:
                    if hasattr(contribution.user, 'referred_by') and contribution.user.referred_by:
                        if contribution.user.referred_by_id not in referrers_updated:
                            update_referrer_points(contribution)
                            referrers_updated.add(contribution.user.referred_by_id)

                self.stdout.write('Updating all leaderboard ranks...')
                update_all_ranks()

        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'Daily uptime generation completed!\n'
            f'- Validators with wallets: {total_users}\n'
            f'- New uptime contributions added: {total_new_contributions}\n'
            f'- Per-network breakdown: {total_network_stats}\n'
            f'- Dates skipped due to missing multipliers: {total_multiplier_errors}'
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))

        # Raise error if all dates failed due to missing multipliers (surfaces to HTTP endpoint)
        if total_multiplier_errors > 0 and total_new_contributions == 0 and not dry_run:
            raise CommandError(
                f'No contributions created — all {total_multiplier_errors} date(s) '
                f'skipped due to missing multipliers. Use --force to override.'
            )
