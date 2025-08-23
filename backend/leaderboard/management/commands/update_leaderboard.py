import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from leaderboard.models import GlobalLeaderboardMultiplier, recalculate_all_leaderboards
from contributions.models import Contribution

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
                updated_count = 0
                for contribution in contributions:
                    if self._update_contribution(contribution):
                        updated_count += 1
                
                self.stdout.write(f'Updated {updated_count} contributions with correct multipliers')
                
                # Recalculate all leaderboards using the new function
                self.stdout.write('Recalculating all leaderboard entries...')
                result = recalculate_all_leaderboards()
                self.stdout.write(self.style.SUCCESS(result))
                
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
            
            # Check if update is needed
            old_multiplier = contribution.multiplier_at_creation
            old_points = contribution.frozen_global_points
            
            # Update the multiplier and recalculate frozen points
            contribution.multiplier_at_creation = multiplier_value
            contribution.frozen_global_points = round(contribution.points * float(multiplier_value))
            
            # Only update if values changed
            if old_multiplier != contribution.multiplier_at_creation or old_points != contribution.frozen_global_points:
                # Save without triggering signals to avoid multiple leaderboard updates
                Contribution.objects.filter(pk=contribution.pk).update(
                    multiplier_at_creation=contribution.multiplier_at_creation,
                    frozen_global_points=contribution.frozen_global_points
                )
                
                self.stdout.write(
                    f'Updated contribution #{contribution.pk}: {contribution.points} points × '
                    f'{multiplier_value} = {contribution.frozen_global_points} global points '
                    f'(was {old_points})'
                )
                return True
            
            return False
            
        except GlobalLeaderboardMultiplier.DoesNotExist:
            # No multiplier exists, use default of 1.0
            if contribution.multiplier_at_creation != 1.0:
                contribution.multiplier_at_creation = 1.0
                contribution.frozen_global_points = contribution.points
                
                Contribution.objects.filter(pk=contribution.pk).update(
                    multiplier_at_creation=contribution.multiplier_at_creation,
                    frozen_global_points=contribution.frozen_global_points
                )
                
                self.stdout.write(
                    self.style.WARNING(
                        f'No active multiplier for contribution #{contribution.pk} '
                        f'({contribution.contribution_type}) on {contribution.contribution_date}. '
                        f'Using default multiplier of 1.0'
                    )
                )
                return True
            
            return False