import logging

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.cache import cache
from django.db.models import Count, Q, Min
from django.utils import timezone
from datetime import timedelta
from contributions.models import Contribution, ContributionType
from users.models import User

logger = logging.getLogger(__name__)


class ActiveValidatorsView(APIView):
    """
    Get active validators based on their first uptime contribution.
    Returns data points showing validator activation over time with continuous dates.
    """
    permission_classes = [permissions.AllowAny]
    
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
    permission_classes = [permissions.AllowAny]

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
    Totals are deduplicated across cohorts so users present in multiple roles
    are only counted once in the overall participant total.

    A "builder" is counted from the date of their first accepted contribution
    in the `builder` category (excluding the welcome auto-award). The
    "validator" is counted from their validator graduation date. Both cohorts
    require `user.visible=True`, matching the Dashboard `/leaderboard/stats/`
    definitions so the time series and the live counts agree.
    """
    permission_classes = [permissions.AllowAny]

    EXCLUDED_BUILDER_SLUGS = ('builder-welcome', 'builder')

    def get(self, request):
        from django.db.models import Min
        from datetime import date, timedelta
        from collections import defaultdict
        from validators.models import Validator
        from builders.models import Builder
        from leaderboard.models import LeaderboardEntry

        # Validators are users with a visible Validator profile AND at least
        # one recorded validator graduation date. Graduation is first taken
        # from the frozen graduation leaderboard, then backfilled from the
        # validator auto-award contribution for older data.
        validators_by_date = defaultdict(set)
        validator_user_ids = set(
            Validator.objects.filter(user__visible=True).values_list('user_id', flat=True)
        )
        if validator_user_ids:
            graduation_dates = {}

            graduation_entries = (
                LeaderboardEntry.objects
                .filter(
                    type='validator-waitlist-graduation',
                    user_id__in=validator_user_ids,
                    graduation_date__isnull=False
                )
                .values('user_id', 'graduation_date')
            )
            for entry in graduation_entries:
                graduation_dates[entry['user_id']] = entry['graduation_date'].date()

            validator_graduations = (
                Contribution.objects
                .filter(user_id__in=validator_user_ids)
                .filter(contribution_type__slug='validator')
                .exclude(contribution_date__isnull=True)
                .values('user_id')
                .annotate(graduation_date=Min('contribution_date'))
            )
            for entry in validator_graduations:
                if entry['user_id'] not in graduation_dates:
                    graduation_dates[entry['user_id']] = entry['graduation_date'].date()

            for user_id, graduation_date in graduation_dates.items():
                validators_by_date[graduation_date].add(user_id)

        # Use first waitlist contribution per user so repeat submissions do not inflate counts.
        waitlist_by_date = defaultdict(set)
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
            waitlist_entries = (
                Contribution.objects
                .filter(contribution_type=waitlist_type)
                .values('user_id')
                .annotate(first_contribution=Min('contribution_date'))
                .order_by('first_contribution')
            )

            for entry in waitlist_entries:
                waitlist_by_date[entry['first_contribution'].date()].add(entry['user_id'])
        except ContributionType.DoesNotExist:
            pass

        # Builders are users with a visible Builder profile AND at least one
        # accepted contribution in the `builder` category (excluding the
        # welcome/auto-award). Mirrors the Dashboard `?type=builder` rule so
        # this time series matches the live builder count.
        builders_by_date = defaultdict(set)
        builder_user_ids = set(
            Builder.objects.filter(user__visible=True).values_list('user_id', flat=True)
        )
        if builder_user_ids:
            qualifying_contributions = (
                Contribution.objects
                .filter(user_id__in=builder_user_ids)
                .filter(contribution_type__category__slug='builder')
                .exclude(contribution_type__slug__in=self.EXCLUDED_BUILDER_SLUGS)
                .values('user_id')
                .annotate(first_contribution=Min('contribution_date'))
            )
            for entry in qualifying_contributions:
                builders_by_date[entry['first_contribution'].date()].add(entry['user_id'])

        # Find date range across all sources
        all_dates = set(validators_by_date.keys()) | set(waitlist_by_date.keys()) | set(builders_by_date.keys())

        if not all_dates:
            return Response({'data': []})

        start_date = min(all_dates)
        end_date = max(max(all_dates), date.today())

        # Build cumulative time series
        data = []
        current_validators = set()
        current_waitlist = set()
        current_builders = set()

        current_date = start_date
        while current_date <= end_date:
            current_validators.update(validators_by_date.get(current_date, set()))
            current_waitlist.update(waitlist_by_date.get(current_date, set()))
            current_builders.update(builders_by_date.get(current_date, set()))

            unique_participants = current_validators | current_waitlist | current_builders
            cohort_total = (
                len(current_validators) +
                len(current_waitlist) +
                len(current_builders)
            )

            data.append({
                'date': current_date.isoformat(),
                'validators': len(current_validators),
                'waitlist': len(current_waitlist),
                'builders': len(current_builders),
                'total': len(unique_participants),
                'cohort_total': cohort_total,
                'overlap_count': cohort_total - len(unique_participants)
            })

            current_date += timedelta(days=1)

        return Response({'data': data})


class TestnetMetricsView(APIView):
    """
    Server-side proxy for the public testnet explorer API.

    Each testnet exposes a Nuxt-fronted explorer that proxies GenScan's
    /api/v1/* endpoints. Browsers can't fetch those directly because the
    explorer hosts don't serve CORS headers, so we proxy from Django and
    cache the aggregate KPIs for a short window.
    """
    permission_classes = [permissions.AllowAny]

    EXPLORER_BASE_URLS = {
        'asimov': 'https://explorer-asimov.genlayer.com',
        'bradbury': 'https://explorer-bradbury.genlayer.com',
    }
    GEN_DECIMALS = 18
    CACHE_TTL_SECONDS = 60
    HTTP_TIMEOUT_SECONDS = 10

    def get(self, request):
        network = request.query_params.get('network', '').lower()
        base_url = self.EXPLORER_BASE_URLS.get(network)
        if not base_url:
            return Response(
                {'error': f"Unknown network '{network}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = f'testnet_metrics:{network}'
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached)

        now = int(timezone.now().timestamp())
        seven_days_ago = now - 7 * 86400
        one_day_ago = now - 86400

        try:
            general = requests.get(
                f'{base_url}/api/v1/analytics/general-kpis',
                timeout=self.HTTP_TIMEOUT_SECONDS,
            )
            history = requests.get(
                f'{base_url}/api/v1/analytics/kpi-histories',
                params={
                    'metric': 'total_finalized_transactions',
                    'interval': 'D1',
                    'from_timestamp': seven_days_ago,
                    'to_timestamp': now,
                },
                timeout=self.HTTP_TIMEOUT_SECONDS,
            )
            tps = requests.get(
                f'{base_url}/api/v1/analytics/relative-kpis',
                params={'from_timestamp': one_day_ago, 'to_timestamp': now},
                timeout=self.HTTP_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            logger.warning('Testnet metrics fetch failed for %s: %s', network, exc)
            return Response(
                {'error': f'Upstream request failed: {exc}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        for label, response in (('general-kpis', general), ('kpi-histories', history), ('relative-kpis', tps)):
            if not response.ok:
                logger.warning('Testnet %s upstream %s returned %s', network, label, response.status_code)
                return Response(
                    {'error': f'Upstream {label} returned {response.status_code}'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        general_data = general.json() or {}
        history_data = history.json()
        tps_data = tps.json() or {}

        if isinstance(history_data, list):
            buckets = history_data
        elif isinstance(history_data, dict):
            buckets = history_data.get('histories') or history_data.get('data') or history_data.get('buckets') or []
        else:
            buckets = []

        decisions_7d = 0
        for point in buckets:
            if not isinstance(point, dict):
                continue
            raw_value = point.get('value') if point.get('value') is not None else point.get('count', 0)
            try:
                decisions_7d += int(float(raw_value or 0))
            except (TypeError, ValueError):
                continue

        try:
            staked_raw = int(general_data.get('total_gen_staked') or 0)
        except (TypeError, ValueError):
            staked_raw = 0
        gen_staked = staked_raw // (10 ** self.GEN_DECIMALS) if staked_raw else 0

        result = {
            'decisions7d': decisions_7d,
            'decisionsAllTime': int(general_data.get('total_finalized_transactions') or 0),
            'chainTxAllTime': int(general_data.get('total_rollup_transactions') or 0),
            'contractsAllTime': int(general_data.get('total_contracts') or 0),
            'validators': int(general_data.get('total_validators') or 0),
            'genStaked': gen_staked,
            'avgTps': float(tps_data.get('avg_tps') or 0),
        }

        cache.set(cache_key, result, self.CACHE_TTL_SECONDS)
        return Response(result)
