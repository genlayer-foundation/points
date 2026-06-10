from rest_framework.pagination import PageNumberPagination
import decimal

from tally.middleware.logging_utils import get_app_logger

logger = get_app_logger('utils')


class SafePageNumberPagination(PageNumberPagination):
    """
    A custom pagination class that surfaces invalid decimal values in
    querysets instead of silently breaking pagination.
    """
    # Default page size - uses settings.REST_FRAMEWORK['PAGE_SIZE'] if not overridden
    page_size = 10
    # Enable client to control page size using 'page_size' query parameter
    page_size_query_param = 'page_size'
    # Set maximum page size to prevent abuse
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override paginate_queryset to log decimal corruption loudly.

        Corrupt decimal data must never be "fixed" automatically on a request
        path: rewriting multiplier_at_creation/frozen_global_points would
        silently destroy frozen multiplier history, which is a core system
        invariant. Operators should investigate and repair affected rows with
        the `fix_decimal_values` management command instead.
        """
        try:
            return super().paginate_queryset(queryset, request, view)
        except decimal.InvalidOperation:
            logger.error(
                "Invalid decimal value encountered while paginating %s. "
                "Run `python manage.py fix_decimal_values` after investigating "
                "the corrupt rows; refusing to auto-rewrite contribution data.",
                queryset.model.__name__ if hasattr(queryset, 'model') else type(queryset).__name__,
                exc_info=True,
            )
            raise
