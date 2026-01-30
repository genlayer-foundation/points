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
    Returns data points showing validator activation over time with continuous dates.
    """
    
    def get(self, request):
        from django.db.models.functions import TruncDate
        from datetime import date, timedelta
        
        # Get uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name__iexact='uptime')
        except ContributionType.DoesNotExist:
            return Response({
                'data': [],
                'message': 'Uptime contribution type not found'
            })
        
        # Get all users who have uptime contributions, grouped by date (not datetime)
        validators_with_uptime = (
            Contribution.objects
            .filter(contribution_type=uptime_type)
            .values('user', 'user__address')
            .annotate(
                first_contribution=Min('contribution_date'),
                first_date=TruncDate(Min('contribution_date'))
            )
            .order_by('first_contribution')
        )
        
        # Build a dictionary of validators activated per day
        validators_by_date = {}
        for validator in validators_with_uptime:
            date_key = validator['first_date']
            if date_key not in validators_by_date:
                validators_by_date[date_key] = []
            validators_by_date[date_key].append(validator['user__address'])
        
        # Create continuous time series data
        data = []
        
        if validators_by_date:
            # Get date range
            start_date = min(validators_by_date.keys())
            end_date = max(validators_by_date.keys())
            
            # If we want to extend to today
            today = date.today()
            if end_date < today:
                end_date = today
            
            # Build continuous series
            current_date = start_date
            active_count = 0
            
            while current_date <= end_date:
                # Add new validators for this date
                if current_date in validators_by_date:
                    active_count += len(validators_by_date[current_date])
                
                data.append({
                    'date': current_date.isoformat(),
                    'count': active_count,
                    'new_validators': len(validators_by_date.get(current_date, []))
                })
                
                # Move to next day
                current_date += timedelta(days=1)
        
        return Response({'data': data})


class ContributionTypesStatsView(APIView):
    """
    Get time series data showing how many contribution types have been assigned on each date.
    """

    def get(self, request):
        from django.db.models.functions import TruncDate
        from datetime import date, timedelta

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
            date_key = contrib['contribution_date'].date()
            contributions_by_date[date_key].add(contrib['contribution_type'])

        if contributions_by_date:
            # Get date range
            start_date = min(contributions_by_date.keys())
            end_date = max(contributions_by_date.keys())

            # Extend to today if needed
            today = date.today()
            if end_date < today:
                end_date = today

            # Build continuous time series with cumulative count
            current_date = start_date

            while current_date <= end_date:
                # Add new types for this date
                if current_date in contributions_by_date:
                    cumulative_types.update(contributions_by_date[current_date])

                data.append({
                    'date': current_date.isoformat(),
                    'count': len(cumulative_types),
                    'new_types': len(contributions_by_date.get(current_date, set()))
                })

                # Move to next day
                current_date += timedelta(days=1)

        return Response({'data': data})


class ParticipantsGrowthView(APIView):
    """
    Get time series data for validators, waitlist users, and builders growth over time.
    """

    def get(self, request):
        from django.db.models.functions import TruncDate
        from datetime import date, timedelta
        from collections import defaultdict
        from validators.models import Validator
        from builders.models import Builder

        # Get validators by creation date
        validators_by_date = defaultdict(int)
        for v in Validator.objects.all():
            date_key = v.created_at.date()
            validators_by_date[date_key] += 1

        # Get waitlist users by contribution date (users with validator-waitlist contribution)
        waitlist_by_date = defaultdict(int)
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
            for c in Contribution.objects.filter(contribution_type=waitlist_type):
                date_key = c.contribution_date.date()
                waitlist_by_date[date_key] += 1
        except ContributionType.DoesNotExist:
            pass

        # Get builders by creation date
        builders_by_date = defaultdict(int)
        for b in Builder.objects.all():
            date_key = b.created_at.date()
            builders_by_date[date_key] += 1

        # Find date range across all sources
        all_dates = set(validators_by_date.keys()) | set(waitlist_by_date.keys()) | set(builders_by_date.keys())

        if not all_dates:
            return Response({'data': []})

        start_date = min(all_dates)
        end_date = max(max(all_dates), date.today())

        # Build cumulative time series
        data = []
        cum_validators = 0
        cum_waitlist = 0
        cum_builders = 0

        current_date = start_date
        while current_date <= end_date:
            cum_validators += validators_by_date.get(current_date, 0)
            cum_waitlist += waitlist_by_date.get(current_date, 0)
            cum_builders += builders_by_date.get(current_date, 0)

            data.append({
                'date': current_date.isoformat(),
                'validators': cum_validators,
                'waitlist': cum_waitlist,
                'builders': cum_builders,
                'total': cum_validators + cum_waitlist + cum_builders
            })

            current_date += timedelta(days=1)

        return Response({'data': data})