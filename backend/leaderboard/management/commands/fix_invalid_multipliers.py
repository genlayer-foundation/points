from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fixes invalid multiplier_at_creation values in the database'

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
        
        self.stdout.write(self.style.SUCCESS('Starting multiplier fix process...'))
        
        with connection.cursor() as cursor:
            # Simple approach: reset all contributions to use 1.0 multiplier
            if not dry_run:
                cursor.execute("""
                    UPDATE contributions_contribution
                    SET multiplier_at_creation = 1.0,
                        frozen_global_points = points
                """)
                
                self.stdout.write(self.style.SUCCESS(f'Reset all contributions to use 1.0 multiplier'))
            
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN - No changes were made'))
        
        self.stdout.write(self.style.SUCCESS('Multiplier fix completed'))