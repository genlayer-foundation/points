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


def format_breakdown(segments: list, indent: str = "  ") -> str:
    """
    Format segments as an indented breakdown for logging.

    Args:
        segments: List of segment dicts from get_segments()
        indent: Indentation string

    Returns:
        Multi-line string with tree-formatted breakdown
    """
    if not segments:
        return ""

    lines = []
    sorted_segments = sorted(segments, key=lambda s: s['duration_ms'], reverse=True)

    for i, segment in enumerate(sorted_segments):
        is_last = i == len(sorted_segments) - 1
        prefix = "└─" if is_last else "├─"
        name = segment['name']
        duration = segment['duration_ms']

        # Mark slowest segment as bottleneck if it's significantly slower
        bottleneck_marker = ""
        if i == 0 and duration > EXPAND_THRESHOLD_MS and len(sorted_segments) > 1:
            second_slowest = sorted_segments[1]['duration_ms'] if len(sorted_segments) > 1 else 0
            if duration > second_slowest * 2:
                bottleneck_marker = "  <- bottleneck"

        lines.append(f"{indent}{prefix} {name}: {duration:.0f}ms{bottleneck_marker}")

    return "\n".join(lines)


def should_expand_trace(duration_ms: float) -> bool:
    """
    Determine if the trace breakdown should be shown.

    Args:
        duration_ms: Total request duration in milliseconds

    Returns:
        True if breakdown should be displayed
    """
    return duration_ms >= EXPAND_THRESHOLD_MS
