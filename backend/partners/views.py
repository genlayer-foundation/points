from rest_framework import filters, permissions, viewsets

from .models import Partner
from .serializers import LightPartnerSerializer, PartnerSerializer


class PartnerViewSet(viewsets.ReadOnlyModelViewSet):
    """Public read-only API for ecosystem partners."""

    queryset = Partner.objects.filter(is_active=True)
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['display_order', 'name', 'created_at']
    lookup_field = 'slug'

    def get_serializer_class(self):
        if self.action == 'list':
            return LightPartnerSerializer
        return PartnerSerializer
