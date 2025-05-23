from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from contributions.models import Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier, update_all_ranks
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
        
        # Get all users
        users = User.objects.all()
        total_users = users.count()
        
        # Current date (end date for all ranges)
        today = timezone.now().date()
        
        # Process each user
        for user in users:
            # Find the first uptime contribution for this user
            first_uptime = Contribution.objects.filter(
                user=user,
                contribution_type=uptime_type
            ).order_by('contribution_date').first()
            
            if not first_uptime:
                if verbose:
                    self.stdout.write(f'User {user} has no uptime contributions, skipping')
                continue
            
            users_with_uptime += 1
            
            # Get the start date from the first contribution
            start_date = first_uptime.contribution_date.date()
            
            if verbose:
                self.stdout.write(
                    f'Processing user {user} - first uptime on {start_date}, '
                    f'generating daily contributions until {today}'
                )
            
            # Get all existing uptime dates for this user to avoid duplicates
            existing_dates = set(
                Contribution.objects.filter(
                    user=user,
                    contribution_type=uptime_type
                ).values_list('contribution_date__date', flat=True)
            )
            
            # Generate a contribution for each day from start_date to today
            # if there isn't already one for that date
            new_contributions = []
            current_date = start_date
            
            while current_date <= today:
                # Skip if there's already a contribution for this date
                if current_date in existing_dates:
                    if verbose:
                        self.stdout.write(f'  - {current_date}: Uptime already exists, skipping')
                    current_date += timedelta(days=1)
                    continue
                
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
                        self.stdout.write(
                            self.style.WARNING(
                                f'  - {current_date}: No multiplier found, using default of 1.0 (--force enabled)'
                            )
                        )
                    else:
                        multiplier_errors += 1
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
                        
                        if verbose:
                            self.stdout.write(f'Added {len(new_contributions)} new contributions for {user}')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error saving contributions for {user}: {str(e)}')
                    )
        
        # Update leaderboard ranks if we made changes
        if total_new_contributions > 0 and not dry_run:
            self.stdout.write('Updating leaderboard ranks...')
            update_all_ranks()
        
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