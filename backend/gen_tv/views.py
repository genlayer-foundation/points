from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import filters, permissions, viewsets

from .models import Stream
from .serializers import LightStreamSerializer, StreamSerializer


class StreamViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only API for Gen TV streams."""

    queryset = Stream.objects.filter(is_active=True)
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['title', 'description']
    ordering_fields = ['starts_at', 'created_at']
    lookup_field = 'slug'
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status')
        now = timezone.now()

        if status_filter == Stream.UPCOMING:
            return queryset.filter(starts_at__gt=now)
        if status_filter == Stream.LIVE:
            return queryset.filter(starts_at__lte=now, ends_at__gt=now)
        if status_filter == Stream.PAST:
            return queryset.filter(ends_at__lte=now)
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return LightStreamSerializer
        return StreamSerializer
