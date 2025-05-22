from django.core.management.base import BaseCommand
from django.db import connection
from contributions.models import Contribution
from leaderboard.models import update_all_ranks


class Command(BaseCommand):
    help = 'Updates all contributions with 0 points to 1 point'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the update without making changes'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('Starting zero points update...'))
        
        # Get count of contributions with 0 points
        zero_point_count = Contribution.objects.filter(points=0).count()
        self.stdout.write(f'Found {zero_point_count} contributions with 0 points')
        
        if not dry_run:
            # Update points from 0 to 1
            updated_count = Contribution.objects.filter(points=0).update(points=1)
            self.stdout.write(self.style.SUCCESS(f'Updated {updated_count} contributions from 0 to 1 point'))
            
            # Now we need to update frozen_global_points based on the new point value
            with connection.cursor() as cursor:
                # Update frozen_global_points based on the multiplier_at_creation
                cursor.execute("""
                    UPDATE contributions_contribution
                    SET frozen_global_points = points * CAST(multiplier_at_creation AS REAL)
                    WHERE points = 1 AND frozen_global_points = 0
                """)
            
            self.stdout.write('Updated frozen_global_points for all modified contributions')
            
            # Update leaderboard
            self.stdout.write('Updating leaderboard...')
            update_all_ranks()
            
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        
        self.stdout.write(self.style.SUCCESS('Update completed successfully'))