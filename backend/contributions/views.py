from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import ContributionType, Contribution
from .serializers import ContributionTypeSerializer, ContributionSerializer
from leaderboard.models import ContributionTypeMultiplier


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
        ContributionTypeMultiplier.objects.create(
            contribution_type=contribution_type,
            multiplier=1.0,
            is_active=True,
            notes="Initial multiplier"
        )


class ContributionViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows contributions to be viewed or edited.
    """
    queryset = Contribution.objects.all()
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'contribution_type']
    search_fields = ['notes', 'user__email', 'user__name', 'contribution_type__name']
    ordering_fields = ['created_at', 'points', 'frozen_global_points']
    
    def get_queryset(self):
        # If user is staff, show all contributions. Otherwise, show only their own.
        if self.request.user.is_staff:
            return Contribution.objects.all()
        return Contribution.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Check if a multiplier exists for this contribution type
        contribution_type = serializer.validated_data['contribution_type']
        
        try:
            multiplier = ContributionTypeMultiplier.objects.filter(
                contribution_type=contribution_type,
                is_active=True
            ).latest('created_at')
        except ContributionTypeMultiplier.DoesNotExist:
            # Create a default multiplier if none exists
            multiplier = ContributionTypeMultiplier.objects.create(
                contribution_type=contribution_type,
                multiplier=1.0,
                is_active=True,
                notes="Auto-created default multiplier"
            )
        
        # Let the signal handle the rest
        serializer.save()
