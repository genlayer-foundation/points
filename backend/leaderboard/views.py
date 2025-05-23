from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from .models import GlobalLeaderboardMultiplier, LeaderboardEntry, update_all_ranks
from .serializers import GlobalLeaderboardMultiplierSerializer, LeaderboardEntrySerializer


class GlobalLeaderboardMultiplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows global leaderboard multipliers to be viewed.
    """
    queryset = GlobalLeaderboardMultiplier.objects.all()
    serializer_class = GlobalLeaderboardMultiplierSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['contribution_type']
    search_fields = ['contribution_type__name', 'notes', 'description']
    ordering_fields = ['created_at', 'valid_from', 'multiplier_value']
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get all currently active multipliers.
        """
        now = timezone.now()
        # Get the most recent multiplier for each contribution type
        contribution_types = {}
        for multiplier in GlobalLeaderboardMultiplier.objects.filter(valid_from__lte=now).order_by('contribution_type', '-valid_from'):
            if multiplier.contribution_type_id not in contribution_types:
                contribution_types[multiplier.contribution_type_id] = multiplier
        
        active_multipliers = list(contribution_types.values())
        serializer = self.get_serializer(active_multipliers, many=True)
        return Response(serializer.data)


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows viewing the leaderboard.
    Read-only because entries are automatically created and updated.
    """
    queryset = LeaderboardEntry.objects.all()
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [permissions.AllowAny]  # Allow access without authentication
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__email', 'user__name']
    ordering_fields = ['rank', 'total_points', 'updated_at']
    ordering = ['rank']
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def recalculate(self, request):
        """
        Force a recalculation of all leaderboard ranks.
        Admin only.
        """
        update_all_ranks()
        return Response({"message": "Leaderboard ranks recalculated successfully."}, 
                        status=status.HTTP_200_OK)
                        
    @action(detail=False, methods=['get'])
    def top(self, request):
        """
        Get the top 10 users on the leaderboard.
        """
        top_entries = LeaderboardEntry.objects.all().order_by('rank')[:10]
        serializer = self.get_serializer(top_entries, many=True)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get statistics for the dashboard.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        from users.models import User
        
        # Get total participants
        participant_count = User.objects.filter(
            contributions__isnull=False
        ).distinct().count()
        
        # Get total contributions
        contribution_count = Contribution.objects.count()
        
        # Get total points
        total_points = Contribution.objects.aggregate(
            total=Sum('frozen_global_points')
        )['total'] or 0
        
        return Response({
            'participant_count': participant_count,
            'contribution_count': contribution_count,
            'total_points': total_points,
        })
        
    def _get_user_stats(self, user):
        """
        Helper method to get statistics for a user.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        
        # Get user's contributions
        contributions = Contribution.objects.filter(user=user)
        
        # Get user's total points
        total_points = contributions.aggregate(
            total=Sum('frozen_global_points')
        )['total'] or 0
        
        # Get user's contribution count
        contribution_count = contributions.count()
        
        # Get average points per contribution
        avg_points = total_points / contribution_count if contribution_count > 0 else 0
        
        # Get contribution breakdown by type
        contribution_types = []
        types_data = contributions.values(
            'contribution_type__name', 
            'contribution_type__id'
        ).annotate(
            count=Count('id'),
            total_points=Sum('frozen_global_points')
        ).order_by('-total_points')
        
        for type_data in types_data:
            percentage = (type_data['total_points'] / total_points * 100) if total_points > 0 else 0
            contribution_types.append({
                'id': type_data['contribution_type__id'],
                'name': type_data['contribution_type__name'],
                'count': type_data['count'],
                'total_points': type_data['total_points'],
                'percentage': percentage,
            })
        
        return {
            'totalContributions': contribution_count,
            'totalPoints': total_points,
            'averagePoints': avg_points,
            'contributionTypes': contribution_types,
        }
        
    @action(detail=False, methods=['get'], url_path='user/(?P<user_id>[^/.]+)')
    def user_stats(self, request, user_id=None):
        """
        Get statistics for a specific user by ID.
        """
        from users.models import User
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
            
        stats = self._get_user_stats(user)
        return Response(stats)
            
    @action(detail=False, methods=['get'], url_path='user_stats/by-address/(?P<address>[^/.]+)')
    def user_stats_by_address(self, request, address=None):
        """
        Get statistics for a specific user by wallet address.
        """
        from users.models import User
        
        try:
            user = User.objects.get(address=address)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
            
        stats = self._get_user_stats(user)
        return Response(stats)
