from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Directly fixes corrupt decimal values in the database'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting direct database fix...'))
        
        with connection.cursor() as cursor:
            # Fix multiplier_at_creation in contributions table - direct SQL approach
            cursor.execute("""
                UPDATE contributions_contribution
                SET multiplier_at_creation = '1.0'
                WHERE multiplier_at_creation IS NOT NULL
            """)
            
            cursor.execute("""
                UPDATE contributions_contribution
                SET frozen_global_points = points
            """)
            
            # Get count of updated rows
            cursor.execute("SELECT COUNT(*) FROM contributions_contribution")
            count = cursor.fetchone()[0]
            
            self.stdout.write(self.style.SUCCESS(f'Fixed {count} rows in contributions_contribution table'))
        
        self.stdout.write(self.style.SUCCESS('Database fix completed successfully'))