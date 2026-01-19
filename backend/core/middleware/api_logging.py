"""
API Layer Logging Middleware.

Logs HTTP requests/responses for the [API] layer (Frontend <-> Backend).
"""
import time
from django.conf import settings

from .logging_utils import (
    get_api_logger,
    generate_correlation_id,
    set_correlation_id,
    clear_correlation_id,
    format_bytes,
)


logger = get_api_logger()


class APILoggingMiddleware:
    """
    Middleware to log HTTP requests and responses.

    DEBUG=true: Logs all requests with method, path, status, duration, size
    DEBUG=false: Logs only errors (4xx, 5xx)
    """

    # Paths to skip logging
    SKIP_PATHS = (
        '/static/',
        '/media/',
        '/health/',
        '/favicon.ico',
        '/__debug__/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip logging for certain paths
        if any(request.path.startswith(path) for path in self.SKIP_PATHS):
            return self.get_response(request)

        # Generate and set correlation ID
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)

        # Start timing
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Get response size
        response_size = len(response.content) if hasattr(response, 'content') else 0

        # Get DB stats if available (set by DBLoggingMiddleware)
        db_query_count = getattr(request, '_db_query_count', 0)
        db_time_ms = getattr(request, '_db_time_ms', 0)
        logic_time_ms = duration_ms - db_time_ms

        # Build log message with timing breakdown
        if db_query_count > 0:
            timing_info = f"{duration_ms:.0f}ms (db: {db_time_ms:.0f}ms/{db_query_count}q, logic: {logic_time_ms:.0f}ms)"
        else:
            timing_info = f"{duration_ms:.0f}ms"

        log_message = (
            f"{request.method} {request.path} "
            f"{response.status_code} "
            f"{timing_info} "
            f"{format_bytes(response_size)}"
        )

        # Log based on status code and DEBUG setting
        is_error = response.status_code >= 400

        if is_error:
            # Always log errors
            if response.status_code >= 500:
                logger.error(log_message)
            else:
                logger.warning(log_message)
        elif settings.DEBUG:
            # In debug mode, log all requests
            logger.info(log_message)

        # Clear correlation ID
        clear_correlation_id()

        return response
