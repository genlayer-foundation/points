from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone
from contributions.models import Contribution, ContributionType
from leaderboard.models import GlobalLeaderboardMultiplier, update_all_ranks
import decimal


class Command(BaseCommand):
    help = 'Fixes corrupted decimal values and other data issues in contributions'
    
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
            '--fix-null-multipliers',
            action='store_true',
            help='Fix NULL multiplier_at_creation values (set to 1.0)'
        )
        parser.add_argument(
            '--fix-invalid-multipliers',
            action='store_true',
            help='Fix invalid/corrupted multiplier_at_creation values'
        )
        parser.add_argument(
            '--fix-global-points',
            action='store_true',
            help='Recalculate all frozen_global_points values'
        )
        parser.add_argument(
            '--fix-all',
            action='store_true',
            help='Apply all fixes (equivalent to enabling all fix options)'
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        verbose = options['verbose']
        fix_null_multipliers = options['fix_null_multipliers'] or options['fix_all']
        fix_invalid_multipliers = options['fix_invalid_multipliers'] or options['fix_all']
        fix_global_points = options['fix_global_points'] or options['fix_all']
        
        if not any([fix_null_multipliers, fix_invalid_multipliers, fix_global_points]):
            self.stdout.write(self.style.WARNING(
                'No fixes selected. Please specify at least one fix option or use --fix-all. '
                'Run with --help for more information.'
            ))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('Starting contribution data fix...'))
        
        # Track stats
        contributions_with_null_multipliers = 0
        contributions_with_invalid_multipliers = 0
        contributions_with_wrong_points = 0
        total_contributions = Contribution.objects.count()
        
        # Direct SQL fixes for more reliable handling of corrupted data
        with connection.cursor() as cursor:
            # Step 1: Fix NULL multiplier_at_creation values
            if fix_null_multipliers:
                self.stdout.write('Fixing NULL multiplier_at_creation values...')
                
                # First count how many NULL values we have
                cursor.execute("""
                    SELECT COUNT(*) FROM contributions_contribution
                    WHERE multiplier_at_creation IS NULL
                """)
                contributions_with_null_multipliers = cursor.fetchone()[0]
                
                if verbose:
                    self.stdout.write(f'Found {contributions_with_null_multipliers} contributions with NULL multiplier_at_creation')
                
                if not dry_run and contributions_with_null_multipliers > 0:
                    # Fix NULL values by setting to 1.0
                    cursor.execute("""
                        UPDATE contributions_contribution
                        SET multiplier_at_creation = '1.0'
                        WHERE multiplier_at_creation IS NULL
                    """)
                    self.stdout.write(self.style.SUCCESS(f'Fixed {contributions_with_null_multipliers} NULL multiplier values'))
            
            # Step 2: Fix invalid multiplier_at_creation values
            if fix_invalid_multipliers:
                self.stdout.write('Fixing invalid multiplier_at_creation values...')
                
                # The database operation should set all multipliers that cause problems to 1.0
                # Since we can't easily count corrupted values, we'll update all for safety
                if not dry_run:
                    cursor.execute("""
                        UPDATE contributions_contribution
                        SET multiplier_at_creation = '1.0'
                        WHERE multiplier_at_creation != '1.0'
                        AND (
                            multiplier_at_creation = ''
                            OR multiplier_at_creation = 'None'
                            OR multiplier_at_creation = 'null'
                            OR multiplier_at_creation LIKE '%e%'
                            OR multiplier_at_creation LIKE '%E%'
                            OR multiplier_at_creation LIKE '%,%'
                            OR CAST(multiplier_at_creation AS TEXT) NOT LIKE '%.%'
                        )
                    """)
                    
                    # Get count of affected rows (SQLite doesn't support getting affected rows directly)
                    cursor.execute("""
                        SELECT COUNT(*) FROM contributions_contribution
                        WHERE multiplier_at_creation = '1.0'
                    """)
                    fixed_count = cursor.fetchone()[0]
                    contributions_with_invalid_multipliers = fixed_count
                    
                    self.stdout.write(self.style.SUCCESS(f'Fixed potentially invalid multiplier values'))
            
            # Step 3: Recalculate all frozen_global_points values based on points and multiplier
            if fix_global_points:
                self.stdout.write('Recalculating frozen_global_points values...')
                
                if not dry_run:
                    # Update frozen_global_points to match points * multiplier_at_creation
                    cursor.execute("""
                        UPDATE contributions_contribution
                        SET frozen_global_points = CAST(points * CAST(multiplier_at_creation AS REAL) AS INTEGER)
                    """)
                    
                    # Count contributions that were updated
                    cursor.execute("""
                        SELECT COUNT(*) FROM contributions_contribution
                    """)
                    contributions_with_wrong_points = cursor.fetchone()[0]
                    
                    self.stdout.write(self.style.SUCCESS(f'Recalculated global points for all contributions'))
        
        # Now use the ORM for more complex operations like updating the leaderboard
        with transaction.atomic():
            if not dry_run and fix_global_points:
                self.stdout.write('Updating leaderboard ranks...')
                update_all_ranks()
            
            if dry_run:
                # Roll back all changes in dry run mode
                transaction.set_rollback(True)
        
        # Print summary
        self.stdout.write(self.style.SUCCESS(
            f'Contribution data fix completed!\n'
            f'- Total contributions: {total_contributions}\n'
            f'- Fixed NULL multipliers: {contributions_with_null_multipliers}\n'
            f'- Fixed invalid multipliers: {contributions_with_invalid_multipliers}\n'
            f'- Recalculated global points: {contributions_with_wrong_points}'
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))