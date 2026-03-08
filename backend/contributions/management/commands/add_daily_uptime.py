from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import GlobalLeaderboardMultiplier, update_all_ranks, LeaderboardEntry
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
                network_note_marker = f'({network})'
                existing = Contribution.objects.filter(
                    user=user,
                    contribution_type=uptime_type,
                    contribution_date__date=today,
                    notes__contains=network_note_marker
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

                try:
                    _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                        uptime_type,
                        at_date=contribution_date
                    )
                except GlobalLeaderboardMultiplier.DoesNotExist:
                    if force:
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
                    Contribution.objects.create(
                        user=user,
                        contribution_type=uptime_type,
                        points=points,
                        contribution_date=contribution_date,
                        multiplier_at_creation=multiplier_value,
                        frozen_global_points=frozen_global_points,
                        notes=f'Auto-generated daily uptime for {today} ({network})'
                    )

                    if user not in users_to_update_leaderboard:
                        users_to_update_leaderboard.append(user)

                total_new_contributions += 1
                network_stats[network] += 1

        # Update leaderboard entries for all affected users
        if users_to_update_leaderboard and not dry_run:
            self.stdout.write('Updating leaderboard entries...')

            uptime_category = uptime_type.category if uptime_type.category else None

            for user in users_to_update_leaderboard:
                # Update GLOBAL leaderboard entry
                global_entry, created = LeaderboardEntry.objects.get_or_create(
                    user=user,
                    category=None
                )
                global_points = global_entry.update_points_without_ranking()

                if verbose:
                    action = 'Created' if created else 'Updated'
                    self.stdout.write(f'{action} GLOBAL leaderboard for {user}: {global_points} total points')

                # Update CATEGORY-SPECIFIC leaderboard entry
                if uptime_category:
                    category_entry, cat_created = LeaderboardEntry.objects.get_or_create(
                        user=user,
                        category=uptime_category
                    )
                    category_points = category_entry.update_points_without_ranking()

                    if verbose:
                        action = 'Created' if cat_created else 'Updated'
                        self.stdout.write(f'{action} {uptime_category.name} category leaderboard for {user}: {category_points} points')

                # Update entries for ALL categories this user has contributions in
                user_categories = Category.objects.filter(
                    contribution_types__contributions__user=user
                ).distinct()

                for category in user_categories:
                    if category != uptime_category:
                        cat_entry, cat_created = LeaderboardEntry.objects.get_or_create(
                            user=user,
                            category=category
                        )
                        cat_points = cat_entry.update_points_without_ranking()

                        if verbose and cat_created:
                            self.stdout.write(f'Created {category.name} category leaderboard for {user}: {cat_points} points')

            self.stdout.write('Updating all leaderboard ranks...')
            update_all_ranks()

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
