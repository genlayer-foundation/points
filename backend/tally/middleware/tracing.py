"""
Request Tracing Module.

Provides utilities for timing code segments within a request lifecycle.
Enables identification of bottlenecks by breaking down request processing
into measurable segments (internal operations and external calls).
"""
import threading
import time
from contextlib import contextmanager

# Threshold for expanding trace breakdown in logs
EXPAND_THRESHOLD_MS = 100

# Thread-local storage for current request's trace data
_trace_data = threading.local()


def init_tracing() -> None:
    """Initialize tracing for a new request."""
    _trace_data.segments = []
    _trace_data.start_time = time.time()


def clear_tracing() -> None:
    """Clear tracing data after request completes."""
    _trace_data.segments = []
    _trace_data.start_time = None


def record_segment(name: str, duration_ms: float, is_external: bool = False) -> None:
    """
    Record a completed segment timing.

    Args:
        name: Segment identifier (e.g., 'permissions', 'serialization', 'ext:github:check_star')
        duration_ms: Duration in milliseconds
        is_external: Whether this is an external API call
    """
    segments = getattr(_trace_data, 'segments', None)
    if segments is None:
        _trace_data.segments = []
        segments = _trace_data.segments

    segments.append({
        'name': name,
        'duration_ms': duration_ms,
        'is_external': is_external,
    })


def get_segments() -> list:
    """Get all recorded segments for current request."""
    return getattr(_trace_data, 'segments', [])


@contextmanager
def trace_segment(name: str):
    """
    Context manager for timing a code segment.

    Usage:
        with trace_segment('fetch_user_data'):
            user_data = fetch_user_data()

    Args:
        name: Identifier for the segment (e.g., 'queryset', 'validation')
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        record_segment(name, duration_ms, is_external=False)


@contextmanager
def trace_external(service: str, operation: str):
    """
    Context manager for timing external API calls.

    Usage:
        with trace_external('github', 'check_star'):
            response = requests.get(github_url)

    Args:
        service: External service name (e.g., 'github', 'cloudinary', 'genlayer')
        operation: Operation being performed (e.g., 'check_star', 'upload')
    """
    segment_name = f"ext:{service}:{operation}"
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        record_segment(segment_name, duration_ms, is_external=True)


def get_external_segments(segments: list) -> list:
    """
    Get only external segments from the segment list.

    Args:
        segments: List of segment dicts from get_segments()

    Returns:
        List of external segment dicts (aggregated by name)
    """
    # Aggregate external segments with the same name
    aggregated = {}
    for segment in segments:
        if not segment.get('is_external', False):
            continue
        name = segment['name']
        if name in aggregated:
            aggregated[name]['duration_ms'] += segment['duration_ms']
            aggregated[name]['count'] += 1
        else:
            aggregated[name] = {
                'name': name,
                'duration_ms': segment['duration_ms'],
                'count': 1,
            }

    # Sort by duration descending
    return sorted(aggregated.values(), key=lambda s: s['duration_ms'], reverse=True)


def format_breakdown(
    total_ms: float,
    db_time_ms: float,
    db_query_count: int,
    segments: list,
) -> str:
    """
    Format a timing breakdown as a single-line string.

    Shows:
    - db: Database query time (with query count)
    - ext:*: External API calls (if any)
    - app: Application code time (serialization, view logic, etc.)

    Args:
        total_ms: Total request duration in milliseconds
        db_time_ms: Database query time in milliseconds
        db_query_count: Number of database queries
        segments: List of segment dicts from get_segments()

    Returns:
        Single-line string with timing breakdown, e.g.:
        "db: 317ms/45q, app: 1243ms" or
        "db: 50ms/5q, ext:github:check_star: 780ms, app: 20ms"
    """
    external_segments = get_external_segments(segments)

    # Calculate total external time
    total_external_ms = sum(s['duration_ms'] for s in external_segments)

    # Calculate app time (everything not db or external)
    app_time_ms = max(0, total_ms - db_time_ms - total_external_ms)

    # Build the breakdown parts
    parts = []

    # Add db time first
    if db_query_count > 0:
        parts.append(f"db: {db_time_ms:.0f}ms/{db_query_count}q")

    # Add external segments
    for segment in external_segments:
        name = segment['name']
        duration = segment['duration_ms']
        count = segment['count']
        count_suffix = f" x{count}" if count > 1 else ""
        parts.append(f"{name}: {duration:.0f}ms{count_suffix}")

    # Add app time
    parts.append(f"app: {app_time_ms:.0f}ms")

    return ", ".join(parts)


def should_expand_trace(duration_ms: float) -> bool:
    """
    Determine if the trace breakdown should be shown.

    Args:
        duration_ms: Total request duration in milliseconds

    Returns:
        True if breakdown should be displayed
    """
    return duration_ms >= EXPAND_THRESHOLD_MS
