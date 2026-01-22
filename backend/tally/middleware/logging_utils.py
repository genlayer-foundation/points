"""
Logging utilities for the Tally application.

Provides layer-specific loggers ([API], [DB], [APP]) and correlation ID tracking.
"""
import json
import logging
import threading
import uuid
from datetime import datetime
from typing import Optional


# Thread-local storage for correlation ID
_correlation_data = threading.local()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current request."""
    _correlation_data.correlation_id = correlation_id


def get_correlation_id() -> Optional[str]:
    """Get the correlation ID for the current request."""
    return getattr(_correlation_data, 'correlation_id', None)


def generate_correlation_id() -> str:
    """Generate a new short correlation ID."""
    return uuid.uuid4().hex[:6]


def clear_correlation_id() -> None:
    """Clear the correlation ID after request completes."""
    _correlation_data.correlation_id = None


def format_bytes(size_bytes: int) -> str:
    """Format bytes into human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}MB"


class LayeredFormatter(logging.Formatter):
    """
    Formatter that adds layer prefix to log messages.

    Output format: [LAYER] LEVEL: message (cid: xxx)
    """

    LAYER_MAP = {
        'tally.api': 'API',
        'tally.db': 'DB',
        'tally.app': 'APP',
        'tally.trace': 'TRACE',
    }

    def format(self, record: logging.LogRecord) -> str:
        # Determine layer from logger name
        layer = 'APP'  # default
        for logger_name, layer_name in self.LAYER_MAP.items():
            if record.name.startswith(logger_name):
                layer = layer_name
                break

        # Get correlation ID if available
        cid = get_correlation_id()
        cid_suffix = f" (cid: {cid})" if cid else ""

        # Format the message
        message = record.getMessage()
        level = record.levelname

        return f"[{layer}] {level}: {message}{cid_suffix}"


class LayeredJSONFormatter(logging.Formatter):
    """
    JSON formatter for production logging with layer identification.
    """

    LAYER_MAP = {
        'tally.api': 'API',
        'tally.db': 'DB',
        'tally.app': 'APP',
        'tally.trace': 'TRACE',
    }

    def format(self, record: logging.LogRecord) -> str:
        # Determine layer
        layer = 'APP'
        for logger_name, layer_name in self.LAYER_MAP.items():
            if record.name.startswith(logger_name):
                layer = layer_name
                break

        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'layer': layer,
            'level': record.levelname,
            'message': record.getMessage(),
        }

        # Add correlation ID if available
        cid = get_correlation_id()
        if cid:
            log_data['correlation_id'] = cid

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data, default=str)


def get_api_logger() -> logging.Logger:
    """Get the [API] layer logger."""
    return logging.getLogger('tally.api')


def get_db_logger() -> logging.Logger:
    """Get the [DB] layer logger."""
    return logging.getLogger('tally.db')


def get_app_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get the [APP] layer logger.

    Args:
        name: Optional sub-logger name (e.g., 'auth', 'users')
    """
    if name:
        return logging.getLogger(f'tally.app.{name}')
    return logging.getLogger('tally.app')
