import logging
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.core.cache import cache
from django.db.models import Min
from datetime import timedelta
from community_xp.constants import COMMUNITY_MEMBER_EXCLUDED_TYPE_SLUGS
from contributions.models import Contribution, ContributionType
from validators.permissions import IsCronToken
from .overview_metrics import (
    build_overview_payload,
    empty_network_activity_payload,
    empty_overview_payload,
    latest_network_activity,
    latest_overview_payload,
    refresh_overview_metrics,
)

logger = logging.getLogger(__name__)


class OverviewMetricsView(APIView):
    """
    Public investor overview payload.

    Served from the latest composite ``overview_payload`` MetricSnapshot that the
    cron persists. If no snapshot exists, the view performs a live overview
    rebuild with ``build_overview_payload()`` and returns the empty payload only
    if that fallback fails.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            payload = latest_overview_payload() or build_overview_payload()
        except Exception:
            logger.exception("Failed to build public overview metrics payload")
            payload = empty_overview_payload()
        return Response(payload)


class RefreshOverviewMetricsView(APIView):
    """Cron-protected snapshot refresh for the overview metrics."""
    authentication_classes = []
    permission_classes = [IsCronToken]

    def post(self, request):
        results = refresh_overview_metrics()
        # Drop the network-activity cache so the freshly-persisted snapshot is
        # served on the next request instead of stale cached data.
        cache.delete(NetworkActivityView.CACHE_KEY)
        return Response({
            'count': len(results),
            'metrics': [
                {
                    'metric_key': item.metric_key,
                    'source': item.source,
                    'status': item.status,
                    'observed_at': item.observed_at,
                }
                for item in results
            ],
        }, status=status.HTTP_202_ACCEPTED)


class NetworkActivityView(APIView):
    """
    Overview-chart payload: weekday-aligned weekly decisions across Studio +
    the two testnets, plus the latest rolling-week daily averages and TPS.

    Served from the latest ``network_activity`` MetricSnapshot that the 15-minute
    cron (``refresh_overview_metrics``) persists, so the public page reads from the
    DB instead of doing a live three-API fetch. The cron's refresh endpoint drops
    ``CACHE_KEY`` on completion, so a new snapshot is reflected at once; otherwise
    the short TTL just smooths repeated reads between cron runs.
    """
    permission_classes = [permissions.AllowAny]
    CACHE_KEY = 'overview_network_activity_weekly_v5'
    CACHE_TTL_SECONDS = 120

    def get(self, request):
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            return Response(cached)

        payload = latest_network_activity() or empty_network_activity_payload()

        cache.set(self.CACHE_KEY, payload, self.CACHE_TTL_SECONDS)
        return Response(payload)


class ParticipantsGrowthView(APIView):
    """
    Get time series data for validators, waitlist users, builders, and creators growth over time.
    Totals are deduplicated across cohorts so users present in multiple roles
    are only counted once in the overall participant total.

    A "builder" is counted from the date of their first accepted contribution
    in the `builder` category (excluding the welcome auto-award). The
    "validator" is counted from their validator graduation date. Both cohorts
    require `user.visible=True`, matching the Dashboard `/leaderboard/stats/`
    definitions so the time series and the live counts agree.
    """
    permission_classes = [permissions.AllowAny]

    EXCLUDED_BUILDER_SLUGS = ('builder-welcome', 'builder', 'project-review-reward')

    def _add_first_seen(self, first_seen_by_user, user_id, seen_at):
        if not user_id or not seen_at:
            return

        seen_date = seen_at.date() if hasattr(seen_at, 'date') else seen_at
        current_date = first_seen_by_user.get(user_id)
        if current_date is None or seen_date < current_date:
            first_seen_by_user[user_id] = seen_date

    def _community_members_by_date(self):
        from creators.models import Creator
        from community_xp.models import Mee6CurrentXP
        from community_xp.services import get_default_guild_id
        from poaps.models import PoapClaim

        first_seen_by_user = {}
        guild_id = str(get_default_guild_id())

        contribution_members = (
            Contribution.objects
            .filter(
                contribution_type__category__slug='community',
                user__visible=True,
            )
            .exclude(contribution_type__slug__in=COMMUNITY_MEMBER_EXCLUDED_TYPE_SLUGS)
            .exclude(contribution_date__isnull=True)
            .values('user_id')
            .annotate(first_contribution=Min('contribution_date'))
        )
        for entry in contribution_members:
            self._add_first_seen(first_seen_by_user, entry['user_id'], entry['first_contribution'])

        mee6_members = (
            Mee6CurrentXP.objects
            .filter(
                guild_id=guild_id,
                matched_user__visible=True,
                matched_user_id__isnull=False,
                xp__gt=0,
            )
            .values('matched_user_id')
            .annotate(
                first_matched=Min('matched_at'),
                first_synced=Min('synced_at'),
                first_created=Min('created_at'),
            )
        )
        mee6_member_user_ids = set()
        for entry in mee6_members:
            user_id = entry['matched_user_id']
            mee6_member_user_ids.add(user_id)
            self._add_first_seen(
                first_seen_by_user,
                user_id,
                entry['first_matched'] or entry['first_synced'] or entry['first_created'],
            )

        creator_members = (
            Creator.objects
            .filter(user__visible=True, user_id__in=mee6_member_user_ids)
            .values('user_id')
            .annotate(first_created=Min('created_at'))
        )
        for entry in creator_members:
            self._add_first_seen(first_seen_by_user, entry['user_id'], entry['first_created'])

        poap_members = (
            PoapClaim.objects
            .filter(user__isnull=False, user__visible=True)
            .values('user_id')
            .annotate(first_claimed=Min('claimed_at'))
        )
        for entry in poap_members:
            self._add_first_seen(first_seen_by_user, entry['user_id'], entry['first_claimed'])

        community_by_date = defaultdict(set)
        for user_id, first_seen_date in first_seen_by_user.items():
            community_by_date[first_seen_date].add(user_id)

        return community_by_date

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

        community_members_by_date = self._community_members_by_date()

        # Find date range across all sources
        all_dates = (
            set(validators_by_date.keys()) |
            set(waitlist_by_date.keys()) |
            set(builders_by_date.keys()) |
            set(community_members_by_date.keys())
        )

        if not all_dates:
            return Response({'data': []})

        start_date = min(all_dates)
        end_date = max(max(all_dates), date.today())

        # Build cumulative time series
        data = []
        current_validators = set()
        current_waitlist = set()
        current_builders = set()
        current_community_members = set()

        current_date = start_date
        while current_date <= end_date:
            current_validators.update(validators_by_date.get(current_date, set()))
            current_waitlist.update(waitlist_by_date.get(current_date, set()))
            current_builders.update(builders_by_date.get(current_date, set()))
            current_community_members.update(community_members_by_date.get(current_date, set()))

            unique_participants = (
                current_validators |
                current_waitlist |
                current_builders |
                current_community_members
            )
            unique_contributors = (
                current_validators |
                current_builders |
                current_community_members
            )
            cohort_total = (
                len(current_validators) +
                len(current_waitlist) +
                len(current_builders) +
                len(current_community_members)
            )
            contributor_cohort_total = (
                len(current_validators) +
                len(current_builders) +
                len(current_community_members)
            )

            data.append({
                'date': current_date.isoformat(),
                'validators': len(current_validators),
                'waitlist': len(current_waitlist),
                'builders': len(current_builders),
                'community_members': len(current_community_members),
                'unique_contributors': len(unique_contributors),
                'total': len(unique_participants),
                'cohort_total': cohort_total,
                'overlap_count': cohort_total - len(unique_participants),
                'contributor_cohort_total': contributor_cohort_total,
                'contributor_overlap_count': contributor_cohort_total - len(unique_contributors),
            })

            current_date += timedelta(days=1)

        return Response({'data': data})
