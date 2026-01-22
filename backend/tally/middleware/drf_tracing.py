"""
DRF Automatic Instrumentation.

Monkey-patches Django REST Framework to automatically trace key lifecycle methods.
This enables bottleneck identification without modifying existing view code.
"""
import functools
from typing import Callable, Any

from .tracing import trace_segment

# Flag to ensure we only install once
_installed = False


def _wrap_method(original_method: Callable, segment_name: str) -> Callable:
    """
    Wrap a method to trace its execution time.

    Args:
        original_method: The original method to wrap
        segment_name: Name for the trace segment

    Returns:
        Wrapped method that traces execution time
    """
    @functools.wraps(original_method)
    def wrapper(*args, **kwargs) -> Any:
        with trace_segment(segment_name):
            return original_method(*args, **kwargs)
    return wrapper


def _wrap_method_with_dynamic_name(original_method: Callable, name_prefix: str) -> Callable:
    """
    Wrap a method with a dynamic segment name based on the class.

    Args:
        original_method: The original method to wrap
        name_prefix: Prefix for the segment name (class name will be appended)

    Returns:
        Wrapped method that traces execution time
    """
    @functools.wraps(original_method)
    def wrapper(self, *args, **kwargs) -> Any:
        class_name = self.__class__.__name__
        segment_name = f"{name_prefix}:{class_name}"
        with trace_segment(segment_name):
            return original_method(self, *args, **kwargs)
    return wrapper


def install_drf_tracing() -> None:
    """
    Install automatic tracing on DRF classes.

    Should be called once at application startup (e.g., in AppConfig.ready()).
    Instruments the following DRF methods:
    - APIView.check_permissions() -> "permissions"
    - APIView.check_throttles() -> "throttles"
    - GenericAPIView.get_serializer() -> "serializer"
    - GenericAPIView.get_queryset() -> "queryset:{ClassName}"
    """
    global _installed
    if _installed:
        return

    try:
        from rest_framework.views import APIView
        from rest_framework.generics import GenericAPIView

        # Instrument APIView methods
        if hasattr(APIView, 'check_permissions'):
            APIView.check_permissions = _wrap_method(
                APIView.check_permissions,
                'permissions'
            )

        if hasattr(APIView, 'check_throttles'):
            APIView.check_throttles = _wrap_method(
                APIView.check_throttles,
                'throttles'
            )

        # Instrument GenericAPIView methods
        if hasattr(GenericAPIView, 'get_queryset'):
            GenericAPIView.get_queryset = _wrap_method_with_dynamic_name(
                GenericAPIView.get_queryset,
                'queryset'
            )

        if hasattr(GenericAPIView, 'get_serializer'):
            GenericAPIView.get_serializer = _wrap_method(
                GenericAPIView.get_serializer,
                'serializer'
            )

        _installed = True

    except ImportError:
        # DRF not installed, skip instrumentation
        pass
