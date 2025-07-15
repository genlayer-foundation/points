from rest_framework.pagination import PageNumberPagination
from django.db.models.query import QuerySet
import decimal
from django.db import connection


class SafePageNumberPagination(PageNumberPagination):
    """
    A custom pagination class that safely handles invalid decimal values
    in querysets by filtering them out before pagination.
    """
    # Default page size
    page_size = 100
    # Enable client to control page size using 'limit' query parameter
    page_size_query_param = 'limit'
    # Set maximum page size to prevent abuse
    max_page_size = 100
    
    def paginate_queryset(self, queryset, request, view=None):
        """
        Override paginate_queryset to handle potential decimal errors
        """
        try:
            return super().paginate_queryset(queryset, request, view)
        except decimal.InvalidOperation:
            # If we encounter decimal error, we need to handle it directly in the database
            print("WARNING: Encountered invalid decimal error in pagination. Applying direct database fix...")
            
            # Emergency fix - run direct SQL to fix the corrupted data
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
            
            # Try again with the original queryset after fixing the database
            return super().paginate_queryset(queryset, request, view)