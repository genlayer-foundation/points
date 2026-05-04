from django_filters.rest_framework import DjangoFilterBackend
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

    def get_serializer_class(self):
        if self.action == 'list':
            return LightStreamSerializer
        return StreamSerializer
