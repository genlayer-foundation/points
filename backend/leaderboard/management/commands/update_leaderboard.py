from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model
import decimal
import traceback

from contributions.models import Contribution
from leaderboard.models import LeaderboardEntry, GlobalLeaderboardMultiplier


User = get_user_model()


class Command(BaseCommand):
    help = 'Updates all frozen_global_points and recreates the leaderboard entries'

    def add_arguments(self, parser):
        # Optional arguments
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Increase output verbosity'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without making changes'
        )

    def handle(self, *args, **options):
        verbose = options['verbose']
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('Starting leaderboard update process...'))
        
        # Track stats
        total_contributions = 0
        updated_contributions = 0
        users_updated = 0
        
        try:
            # Step 1: Update all frozen_global_points for each contribution
            with transaction.atomic():
                self.stdout.write('Recalculating frozen_global_points for all contributions...')
                
                # Get the total count of contributions without loading objects that might have corrupted data
                total_contributions = Contribution.objects.count()
                
                if verbose:
                    self.stdout.write(f'Found {total_contributions} contributions to process')
                
                # Process contributions one by one to handle potential data corruption
                for contribution_id in Contribution.objects.values_list('id', flat=True):
                    try:
                        # Get the contribution directly by ID to isolate potential data issues
                        contribution = Contribution.objects.select_related('user', 'contribution_type').get(id=contribution_id)
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'Error loading contribution ID {contribution_id}: {str(e)}')
                        )
                        continue
                        
                    # Process this contribution
                    # Get the active multiplier for this contribution's type at the contribution date
                    try:
                        _, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                            contribution.contribution_type,
                            at_date=contribution.contribution_date or contribution.created_at
                        )
                        
                        # Calculate new frozen_global_points
                        try:
                            new_frozen_points = int(contribution.points * float(multiplier_value))
                            
                            if contribution.frozen_global_points != new_frozen_points or contribution.multiplier_at_creation != multiplier_value:
                                if verbose:
                                    self.stdout.write(
                                        f'Updating contribution {contribution.id}: '
                                        f'{contribution.points} points × {multiplier_value} = {new_frozen_points} '
                                        f'(was: {contribution.frozen_global_points})'
                                    )
                                
                                if not dry_run:
                                    contribution.multiplier_at_creation = multiplier_value
                                    contribution.frozen_global_points = new_frozen_points
                                    contribution.save(update_fields=['frozen_global_points', 'multiplier_at_creation'])
                                
                                updated_contributions += 1
                                
                        except (decimal.InvalidOperation, TypeError, ValueError) as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Error calculating points for contribution {contribution.id}: '
                                    f'{contribution.points} points × {multiplier_value}. Error: {str(e)}'
                                )
                            )
                            continue
                            
                    except GlobalLeaderboardMultiplier.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'No multiplier found for contribution {contribution.id} '
                                f'({contribution.contribution_type.name}) on '
                                f'{contribution.contribution_date or contribution.created_at}'
                            )
                        )
                
                # Step 2: Recreate all leaderboard entries
                self.stdout.write('Recreating leaderboard entries...')
                
                # First, get all users with contributions
                users_with_contributions = User.objects.filter(
                    contributions__isnull=False
                ).distinct()
                
                users_updated = users_with_contributions.count()
                
                if verbose:
                    self.stdout.write(f'Found {users_updated} users with contributions')
                
                # Optionally clear all existing leaderboard entries
                if not dry_run:
                    LeaderboardEntry.objects.all().delete()
                
                # Create new leaderboard entries
                for user in users_with_contributions:
                    # Calculate total points for this user
                    user_points = Contribution.objects.filter(user=user).aggregate(
                        total=Sum('frozen_global_points')
                    )['total'] or 0
                    
                    if verbose:
                        self.stdout.write(f'User {user.id}: {user_points} total points')
                    
                    # Create or update leaderboard entry
                    if not dry_run:
                        LeaderboardEntry.objects.update_or_create(
                            user=user,
                            defaults={'total_points': user_points}
                        )
                
                # Step 3: Update all ranks
                if not dry_run:
                    self.stdout.write('Updating all ranks...')
                    self._update_all_ranks()
                
                if dry_run:
                    # Roll back the transaction for dry runs
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING('DRY RUN - All changes rolled back'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during update: {str(e)}'))
            self.stdout.write(self.style.ERROR(traceback.format_exc()))
            return
        
        # Final stats
        self.stdout.write(self.style.SUCCESS(
            f'Leaderboard update completed successfully!\n'
            f'- Total contributions processed: {total_contributions}\n'
            f'- Contributions updated: {updated_contributions}\n'
            f'- Users with leaderboard entries: {users_updated}'
        ))
    
    def _update_all_ranks(self):
        """
        Update the ranks for all leaderboard entries.
        """
        entries = LeaderboardEntry.objects.all().order_by('-total_points')
        rank = 1
        
        for i, entry in enumerate(entries):
            # If this entry has the same points as the previous one, give it the same rank
            if i > 0 and entry.total_points == entries[i-1].total_points:
                entry.rank = entries[i-1].rank
            else:
                entry.rank = rank
            
            entry.save(update_fields=['rank'])
            
            # Only increment rank if the next entry will have a different rank
            if i < len(entries) - 1 and entry.total_points != entries[i+1].total_points:
                rank += 1