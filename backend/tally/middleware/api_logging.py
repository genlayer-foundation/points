"""
API Layer Logging Middleware.

Logs HTTP requests/responses for the [API] layer with smart trace breakdown.
- DEBUG=true: Logs all requests; shows breakdown for slow requests (>100ms)
- DEBUG=false: Logs only 5xx errors with breakdown
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
from .tracing import (
    init_tracing,
    clear_tracing,
    get_segments,
    format_breakdown,
    should_expand_trace,
    get_external_segments,
)


logger = get_api_logger()


class APILoggingMiddleware:
    """
    Middleware to log HTTP requests and responses with trace breakdown.

    Logging behavior:
    - DEBUG=true: All requests logged; breakdown shown for requests > 100ms
    - DEBUG=false: Only 5xx errors logged (always with breakdown)
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

        # Initialize request tracking
        correlation_id = generate_correlation_id()
        set_correlation_id(correlation_id)
        init_tracing()

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

        # Get trace segments
        segments = get_segments()
        external_segments = get_external_segments(segments)

        # Determine logging behavior
        is_server_error = response.status_code >= 500
        is_slow = should_expand_trace(duration_ms)
        has_external = len(external_segments) > 0

        # Show breakdown for slow requests or errors (only if there's something interesting)
        show_breakdown = is_server_error or (settings.DEBUG and is_slow and (has_external or db_query_count > 0))

        # Build timing info string - use full breakdown for slow/error requests
        if show_breakdown:
            breakdown = format_breakdown(duration_ms, db_time_ms, db_query_count, segments)
            timing_info = f"{duration_ms:.0f}ms ({breakdown})"
        else:
            timing_info = self._build_timing_info(duration_ms, db_time_ms, db_query_count)

        # Build log message
        log_message = (
            f"{request.method} {request.path} "
            f"{response.status_code} "
            f"{timing_info} "
            f"{format_bytes(response_size)}"
        )

        if is_server_error:
            logger.error(log_message)
        elif settings.DEBUG:
            logger.debug(log_message)

        # Clear request tracking
        clear_correlation_id()
        clear_tracing()

        return response

    def _build_timing_info(self, duration_ms: float, db_time_ms: float, db_query_count: int) -> str:
        """Build the timing info string for the log message."""
        if db_query_count > 0:
            return f"{duration_ms:.0f}ms (db: {db_time_ms:.0f}ms/{db_query_count}q)"
        return f"{duration_ms:.0f}ms"
