from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Max, F
from django.db.models.functions import Coalesce
from .models import ContributionType, Contribution, Evidence
from .serializers import ContributionTypeSerializer, ContributionSerializer, EvidenceSerializer
from leaderboard.models import GlobalLeaderboardMultiplier
from rest_framework.parsers import MultiPartParser, FormParser


class ContributionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contribution types to be viewed.
    """
    queryset = ContributionType.objects.all()
    serializer_class = ContributionTypeSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
        
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def statistics(self, request):
        """
        Get aggregated statistics for each contribution type.
        Returns:
            - count of each contribution type
            - current points multiplier
            - number of participants with each type
            - last date someone earned each type
        """
        types_with_stats = ContributionType.objects.annotate(
            count=Count('contributions'),
            participants_count=Count('contributions__user', distinct=True),
            last_earned=Coalesce(Max('contributions__contribution_date'), timezone.now())
        ).values('id', 'name', 'description', 'min_points', 'max_points', 'count', 'participants_count', 'last_earned')
        
        # Add current multiplier for each type
        result = []
        for type_data in types_with_stats:
            try:
                contribution_type = ContributionType.objects.get(id=type_data['id'])
                multiplier_value = GlobalLeaderboardMultiplier.get_current_multiplier_value(contribution_type)
                type_data['current_multiplier'] = multiplier_value
            except Exception:
                type_data['current_multiplier'] = 1.0
            
            result.append(type_data)
            
        return Response(result)


class ContributionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contributions to be viewed.
    """
    queryset = Contribution.objects.all().order_by('-contribution_date')
    serializer_class = ContributionSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'contribution_type']
    search_fields = ['notes', 'user__email', 'user__name', 'contribution_type__name']
    ordering_fields = ['contribution_date', 'created_at', 'points', 'frozen_global_points']
    ordering = ['-contribution_date']
    
    def get_queryset(self):
        queryset = Contribution.objects.all().order_by('-contribution_date')
        
        # Filter by user address if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(user__address=user_address)
            
        return queryset


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows evidence to be viewed.
    """
    queryset = Evidence.objects.all().order_by('-created_at')
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['contribution', 'contribution__user']
    search_fields = ['description', 'url']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]
