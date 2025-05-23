import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from leaderboard.models import GlobalLeaderboardMultiplier, LeaderboardEntry, update_all_ranks
from contributions.models import Contribution, ContributionType

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Update the leaderboard by recalculating all contribution multipliers and points'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting leaderboard update...'))
        
        try:
            with transaction.atomic():
                # Get all contributions
                contributions = Contribution.objects.all()
                self.stdout.write(f'Processing {contributions.count()} contributions')
                
                # Update each contribution with correct multiplier and points
                for contribution in contributions:
                    self._update_contribution(contribution)
                
                # Recalculate all leaderboard entries
                self._recreate_leaderboard()
                
                # Update ranks
                update_all_ranks()
                
            self.stdout.write(self.style.SUCCESS('Leaderboard update completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error updating leaderboard: {e}'))
            logger.exception('Error in update_leaderboard command')
            raise
    
    def _update_contribution(self, contribution):
        """Update a single contribution with the correct multiplier and points"""
        try:
            # Get the appropriate multiplier for this contribution at its creation date
            multiplier_obj, multiplier_value = GlobalLeaderboardMultiplier.get_active_for_type(
                contribution.contribution_type,
                at_date=contribution.contribution_date
            )
            
            # Update the multiplier and recalculate frozen points
            contribution.multiplier_at_creation = multiplier_value
            contribution.frozen_global_points = round(contribution.points * float(multiplier_value))
            
            # Save without triggering signals to avoid multiple leaderboard updates
            Contribution.objects.filter(pk=contribution.pk).update(
                multiplier_at_creation=contribution.multiplier_at_creation,
                frozen_global_points=contribution.frozen_global_points
            )
            
            self.stdout.write(
                f'Updated contribution #{contribution.pk}: {contribution.points} points × '
                f'{multiplier_value} = {contribution.frozen_global_points} global points'
            )
            
        except GlobalLeaderboardMultiplier.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    f'No active multiplier for contribution #{contribution.pk} '
                    f'({contribution.contribution_type}) on {contribution.contribution_date}'
                )
            )
    
    def _recreate_leaderboard(self):
        """Recreate the entire leaderboard from scratch based on updated contributions"""
        # Clear existing entries - optional, but ensures clean state
        LeaderboardEntry.objects.all().delete()
        
        # Get all users with contributions
        user_ids = Contribution.objects.values_list('user', flat=True).distinct()
        
        # For each user, create a new leaderboard entry
        for user_id in user_ids:
            total_points = Contribution.objects.filter(user_id=user_id).values_list(
                'frozen_global_points', flat=True
            )
            total_points = sum(total_points)
            
            LeaderboardEntry.objects.create(
                user_id=user_id,
                total_points=total_points
            )
            
            self.stdout.write(f'Created leaderboard entry for user #{user_id}: {total_points} points')