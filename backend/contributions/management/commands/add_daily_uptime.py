from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction, models
from django.contrib.auth import get_user_model
from contributions.models import Contribution, ContributionType, Category
from leaderboard.models import GlobalLeaderboardMultiplier, update_all_ranks, LeaderboardEntry
from datetime import datetime, timedelta
import pytz
import decimal

User = get_user_model()

class Command(BaseCommand):
    help = 'Adds daily uptime contributions for all users from their first uptime to today'

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

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        points = options['points']
        force = options['force']
        
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
        
        # Track stats
        total_users = 0
        users_with_uptime = 0
        total_new_contributions = 0
        multiplier_errors = 0
        users_to_update_leaderboard = []  # Track users who got new contributions

        # Current date (end date for all ranges)
        today = timezone.now().date()

        # OPTIMIZATION 1: Get all validators with their creation dates
        from validators.models import Validator

        all_validators = Validator.objects.all()
        validator_created_dates = {v.user_id: v.created_at.date() for v in all_validators}

        if not validator_created_dates:
            self.stdout.write(self.style.WARNING('No validators found'))
            return

        # OPTIMIZATION 2: Get the LAST (most recent) uptime date per validator
        # We only need the max date, not all dates, since we'll start from day after last uptime
        last_uptimes = {}
        for contrib in Contribution.objects.filter(
            contribution_type=uptime_type,
            user_id__in=validator_created_dates.keys()
        ).values('user_id').annotate(
            last_date=models.Max('contribution_date')
        ):
            last_uptimes[contrib['user_id']] = contrib['last_date'].date()

        # Determine start date for each validator
        # Key insight: We start from day AFTER last uptime (or from creation date if no uptime)
        # This means we never create duplicates - no need to check existing dates!
        validator_start_dates = {}
        for user_id, created_date in validator_created_dates.items():
            if user_id in last_uptimes:
                # Has uptime → start from day AFTER last recorded uptime
                validator_start_dates[user_id] = last_uptimes[user_id] + timedelta(days=1)
            else:
                # No uptime yet → start from validator creation date
                validator_start_dates[user_id] = created_date

        users_with_uptime = len(validator_start_dates)

        # Get all validator users
        users = User.objects.filter(id__in=validator_start_dates.keys())
        total_users = users.count()

        if verbose:
            self.stdout.write(f'Processing {total_users} validators')

        # Process each validator
        for user in users:
            # Get the start date from our pre-fetched data
            # This is either the last uptime date (for existing validators) or validator creation date (for new validators)
            start_date = validator_start_dates[user.id]

            if verbose:
                self.stdout.write(
                    f'Processing user {user} - starting from {start_date}, '
                    f'generating daily contributions until {today}'
                )

            # Generate a contribution for each day from start_date to today
            # No need to check for existing dates since we start from day after last uptime
            new_contributions = []
            current_date = start_date

            while current_date <= today:
                # Create a new contribution for this date
                contribution_date = datetime.combine(
                    current_date, 
                    datetime.min.time(), 
                    tzinfo=pytz.UTC
                )
                
                # Get the active multiplier for this date
                try:
                    _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                        uptime_type, 
                        at_date=contribution_date
                    )
                except GlobalLeaderboardMultiplier.DoesNotExist:
                    if force:
                        multiplier_value = decimal.Decimal('1.0')
                    else:
                        multiplier_errors += 1
                        if verbose:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'  - {current_date}: No multiplier found for contribution type "Uptime". '
                                    f'Skipping this date. Use --force to override.'
                                )
                            )
                        current_date += timedelta(days=1)
                        continue
                
                # Calculate the global points
                frozen_global_points = round(points * float(multiplier_value))
                
                if verbose:
                    self.stdout.write(
                        f'  - {current_date}: Adding new uptime contribution '
                        f'({points} points × {multiplier_value} = {frozen_global_points} global points)'
                    )
                
                if not dry_run:
                    # Create a new contribution
                    new_contribution = Contribution(
                        user=user,
                        contribution_type=uptime_type,
                        points=points,
                        contribution_date=contribution_date,
                        multiplier_at_creation=multiplier_value,
                        frozen_global_points=frozen_global_points,
                        notes=f'Auto-generated daily uptime for {current_date}'
                    )
                    new_contributions.append(new_contribution)
                
                total_new_contributions += 1
                current_date += timedelta(days=1)
            
            # Save all new contributions in bulk
            if new_contributions and not dry_run:
                try:
                    with transaction.atomic():
                        # Save contributions directly with all fields pre-populated
                        Contribution.objects.bulk_create(new_contributions)
                        
                        # Track this user for leaderboard update
                        users_to_update_leaderboard.append(user)
                        
                        if verbose:
                            self.stdout.write(f'Added {len(new_contributions)} new contributions for {user}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error saving contributions for {user}: {str(e)}')
                    )
        
        # Update leaderboard entries for all affected users
        if users_to_update_leaderboard and not dry_run:
            self.stdout.write('Updating leaderboard entries...')

            # OPTIMIZATION 3: Simplified leaderboard updates
            # bulk_create doesn't trigger post_save signals, so we need to manually update leaderboards.
            # However, we can optimize by calling update_user_leaderboard_entries which handles
            # all leaderboard types for a user efficiently.
            from leaderboard.models import update_user_leaderboard_entries

            for user in users_to_update_leaderboard:
                # This single call updates all leaderboard types the user qualifies for
                # and recalculates ranks for all affected leaderboards
                update_user_leaderboard_entries(user)

                if verbose:
                    self.stdout.write(f'Updated leaderboard entries for {user}')
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'Daily uptime generation completed!\n'
            f'- Total users: {total_users}\n'
            f'- Users with uptime: {users_with_uptime}\n'
            f'- New uptime contributions added: {total_new_contributions}\n'
            f'- Dates skipped due to missing multipliers: {multiplier_errors}'
        ))
        
        if multiplier_errors > 0:
            self.stdout.write(
                self.style.WARNING(
                    f'Some contributions were skipped due to missing multipliers. '
                    f'Use --force to use a default multiplier of 1.0 for these dates.'
                )
            )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))