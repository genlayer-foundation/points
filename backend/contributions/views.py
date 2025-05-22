from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
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
