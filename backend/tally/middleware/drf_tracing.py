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
    - GenericAPIView.get_serializer() -> "serializer:init"
    - GenericAPIView.get_queryset() -> "queryset:{ClassName}"
    - Serializer.to_representation() -> "serializer:render"
    - Serializer.to_internal_value() -> "serializer:parse"
    """
    global _installed
    if _installed:
        return

    try:
        from rest_framework.views import APIView
        from rest_framework.generics import GenericAPIView
        from rest_framework.serializers import Serializer

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
                'serializer:init'
            )

        # Instrument Serializer methods
        if hasattr(Serializer, 'to_representation'):
            original_to_representation = Serializer.to_representation

            @functools.wraps(original_to_representation)
            def traced_to_representation(self, instance):
                # Only trace if this is the top-level serializer call
                # to avoid tracing nested serializer calls
                if not getattr(self, '_tracing_render', False):
                    self._tracing_render = True
                    try:
                        with trace_segment('serializer:render'):
                            return original_to_representation(self, instance)
                    finally:
                        self._tracing_render = False
                return original_to_representation(self, instance)

            Serializer.to_representation = traced_to_representation

        if hasattr(Serializer, 'to_internal_value'):
            original_to_internal = Serializer.to_internal_value

            @functools.wraps(original_to_internal)
            def traced_to_internal_value(self, data):
                # Only trace if this is the top-level serializer call
                if not getattr(self, '_tracing_parse', False):
                    self._tracing_parse = True
                    try:
                        with trace_segment('serializer:parse'):
                            return original_to_internal(self, data)
                    finally:
                        self._tracing_parse = False
                return original_to_internal(self, data)

            Serializer.to_internal_value = traced_to_internal_value

        _installed = True

    except ImportError:
        # DRF not installed, skip instrumentation
        pass
