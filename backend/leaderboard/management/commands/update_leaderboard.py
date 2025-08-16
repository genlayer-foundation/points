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
                
                # Update ranks for global and all categories
                from contributions.models import Category
                from leaderboard.models import LeaderboardEntry
                
                # Update global ranks
                LeaderboardEntry.update_category_ranks(category=None)
                self.stdout.write('Updated global leaderboard ranks')
                
                # Update category-specific ranks
                for category in Category.objects.all():
                    LeaderboardEntry.update_category_ranks(category=category)
                    self.stdout.write(f'Updated {category.name} leaderboard ranks')
                
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
        from contributions.models import Category
        
        # Clear existing entries - optional, but ensures clean state
        LeaderboardEntry.objects.all().delete()
        
        # Get all users with contributions
        user_ids = Contribution.objects.values_list('user', flat=True).distinct()
        
        # For each user, create leaderboard entries
        for user_id in user_ids:
            # Create global leaderboard entry
            total_points = Contribution.objects.filter(user_id=user_id).values_list(
                'frozen_global_points', flat=True
            )
            total_points = sum(total_points)
            
            if total_points > 0:
                LeaderboardEntry.objects.create(
                    user_id=user_id,
                    category=None,  # Global
                    total_points=total_points
                )
                self.stdout.write(f'Created global leaderboard entry for user #{user_id}: {total_points} points')
            
            # Create category-specific leaderboard entries
            for category in Category.objects.all():
                cat_contributions = Contribution.objects.filter(
                    user_id=user_id,
                    contribution_type__category=category
                )
                cat_points = sum(c.frozen_global_points for c in cat_contributions)
                
                if cat_points > 0:
                    LeaderboardEntry.objects.create(
                        user_id=user_id,
                        category=category,
                        total_points=cat_points
                    )
                    self.stdout.write(f'Created {category.name} leaderboard entry for user #{user_id}: {cat_points} points')