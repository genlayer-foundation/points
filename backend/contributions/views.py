from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Max, F
from django.db.models.functions import Coalesce
from .models import ContributionType, Contribution
from .serializers import ContributionTypeSerializer, ContributionSerializer
from leaderboard.models import GlobalLeaderboardMultiplier


class ContributionTypeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows contribution types to be viewed or edited.
    """
    queryset = ContributionType.objects.all()
    serializer_class = ContributionTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def perform_create(self, serializer):
        contribution_type = serializer.save()
        
        # Create an initial multiplier for this contribution type
        GlobalLeaderboardMultiplier.objects.create(
            contribution_type=contribution_type,
            multiplier_value=1.0,
            valid_from=timezone.now(),
            description="Initial multiplier",
            notes="Automatically created when contribution type was added"
        )
        
    @action(detail=False, methods=['get'])
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
        ).values('id', 'name', 'description', 'count', 'participants_count', 'last_earned')
        
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


class ContributionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows contributions to be viewed or edited.
    """
    queryset = Contribution.objects.all().order_by('-contribution_date')
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'contribution_type']
    search_fields = ['notes', 'user__email', 'user__name', 'contribution_type__name']
    ordering_fields = ['contribution_date', 'created_at', 'points', 'frozen_global_points']
    ordering = ['-contribution_date']
    
    def get_queryset(self):
        # If user is staff, show all contributions. Otherwise, show only their own.
        if self.request.user.is_staff:
            return Contribution.objects.all().order_by('-contribution_date')
        return Contribution.objects.filter(user=self.request.user).order_by('-contribution_date')
    
    def perform_create(self, serializer):
        # Check if a multiplier exists for this contribution type
        contribution_type = serializer.validated_data['contribution_type']
        
        try:
            # The model validation will automatically check for a valid multiplier
            # and create frozen_global_points
            pass
        except Exception:
            # Create a default multiplier if validation fails
            now = timezone.now()
            GlobalLeaderboardMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier_value=1.0,
                valid_from=now,
                description="Default multiplier",
                notes="Auto-created default multiplier when contribution was added"
            )
        
        # Let the model's save method and signals handle the rest
        serializer.save()
