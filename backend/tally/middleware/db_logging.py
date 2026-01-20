"""
DB Layer Logging Middleware.

Logs database query statistics for the [DB] layer (Backend <-> Database).
"""
from django.conf import settings
from django.db import connection, reset_queries

from .logging_utils import get_db_logger


logger = get_db_logger()


class DBLoggingMiddleware:
    """
    Middleware to log database query statistics per request.

    DEBUG=true: Logs query count and total time for each request
    DEBUG=false: Only logs database errors

    Note: Query counting only works when DEBUG=True (Django limitation).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only do detailed logging in DEBUG mode (Django requirement)
        if not settings.DEBUG:
            return self.get_response(request)

        # Reset queries at start of request
        reset_queries()

        # Process request
        response = self.get_response(request)

        # Get query statistics
        queries = connection.queries
        query_count = len(queries)

        # Calculate total DB time (even if 0 queries)
        total_time_ms = sum(
            float(q.get('time', 0)) * 1000
            for q in queries
        )

        # Store stats on request for API middleware to use
        request._db_query_count = query_count
        request._db_time_ms = total_time_ms

        return response
