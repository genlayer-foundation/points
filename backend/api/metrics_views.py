from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Q, Min
from django.utils import timezone
from datetime import timedelta
from contributions.models import Contribution, ContributionType
from users.models import User


class ActiveValidatorsView(APIView):
    """
    Get active validators based on their first uptime contribution.
    Returns data points showing validator activation over time.
    """
    
    def get(self, request):
        # Get uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name__iexact='uptime')
        except ContributionType.DoesNotExist:
            return Response({
                'data': [],
                'message': 'Uptime contribution type not found'
            })
        
        # Get all users who have uptime contributions
        validators_with_uptime = (
            Contribution.objects
            .filter(contribution_type=uptime_type)
            .values('user', 'user__address')
            .annotate(first_contribution=Min('contribution_date'))
            .order_by('first_contribution')
        )
        
        # Create time series data
        data = []
        active_count = 0
        
        for validator in validators_with_uptime:
            active_count += 1
            data.append({
                'date': validator['first_contribution'].isoformat(),
                'count': active_count,
                'address': validator['user__address']
            })
        
        return Response({'data': data})


class ContributionTypesStatsView(APIView):
    """
    Get time series data showing how many contribution types have been assigned on each date.
    """
    
    def get(self, request):
        from django.db.models.functions import TruncDate
        
        # Get contributions grouped by date and contribution type
        daily_contributions = (
            Contribution.objects
            .annotate(date=TruncDate('contribution_date'))
            .values('date')
            .annotate(
                unique_types=Count('contribution_type', distinct=True),
                total_contributions=Count('id')
            )
            .order_by('date')
        )
        
        # Build cumulative data
        data = []
        cumulative_types = set()
        
        # Get all contributions to track cumulative unique types
        all_contributions = (
            Contribution.objects
            .values('contribution_date', 'contribution_type')
            .order_by('contribution_date')
        )
        
        # Group by date and count cumulative types
        from collections import defaultdict
        contributions_by_date = defaultdict(set)
        
        for contrib in all_contributions:
            date = contrib['contribution_date'].date()
            contributions_by_date[date].add(contrib['contribution_type'])
        
        # Build time series with cumulative count
        for date in sorted(contributions_by_date.keys()):
            cumulative_types.update(contributions_by_date[date])
            data.append({
                'date': date.isoformat(),
                'count': len(cumulative_types),
                'new_types': len(contributions_by_date[date])
            })
        
        return Response({'data': data})