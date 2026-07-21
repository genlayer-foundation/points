from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    GlobalLeaderboardMultiplier,
    LEADERBOARD_CONFIG,
    LeaderboardEntry,
    recalculate_all_leaderboards,
)
from .serializers import GlobalLeaderboardMultiplierSerializer, LeaderboardEntrySerializer
from contributions.models import Contribution, SubmittedContribution
from users.utils import is_full_address, truncate_address, user_lookup_kwargs

ONBOARDING_CONTRIBUTION_TYPE_SLUGS = [
    'builder-welcome',
    'builder',
    'validator-waitlist',
    'validator',
    'community-link-x',
    'community-link-discord',
    'project-review-reward',
]
COMMUNITY_RANKING_MIN_POINTS = 2500


class GlobalLeaderboardMultiplierViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows global leaderboard multipliers to be viewed.
    """
    queryset = GlobalLeaderboardMultiplier.objects.all()
    serializer_class = GlobalLeaderboardMultiplierSerializer
    permission_classes = [permissions.IsAuthenticated]
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
    Filter by type to get specific leaderboards:
    - ?type=validator - Active validators
    - ?type=builder - Builders
    - ?type=steward - Stewards
    - ?type=validator-waitlist - Waitlisted users (not yet validators)
    """
    queryset = LeaderboardEntry.objects.filter(user__visible=True)
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    # Address search is handled by the exact-match ?user_address= filter only.
    # No substring matching on addresses: responses carry truncated addresses,
    # so icontains would be an oracle to reconstruct them char by char.
    search_fields = ['user__name']
    ordering_fields = ['rank', 'total_points', 'updated_at']
    ordering = ['rank']
    pagination_class = None  # Disable pagination to return all entries

    def get_throttles(self):
        # Bound anonymous scraping; authenticated browsing is unaffected.
        request = getattr(self, 'request', None)
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated:
            self.throttle_scope = None
        else:
            self.throttle_scope = 'public_leaderboard'
        return super().get_throttles()

    def _can_view_user_stats(self, user):
        request_user = self.request.user
        return bool(
            user.visible
            or (
                request_user.is_authenticated
                and (request_user.id == user.id or request_user.is_staff)
            )
        )

    def get_queryset(self):
        """
        Filter leaderboard by type, user address, and handle ordering.
        Optimized with select_related to avoid N+1 queries.
        """
        queryset = super().get_queryset()

        # Optimize queries: select related user and their profiles
        queryset = queryset.select_related(
            'user',
            'user__validator',
            'user__builder',
            'user__steward',
            'user__creator',
            'user__referral_points'
        )

        # Annotate with validator wallet counts to avoid N+1 queries
        queryset = queryset.annotate(
            _active_validators_count=Count(
                'user__validator__validator_wallets',
                filter=Q(user__validator__validator_wallets__status='active')
            ),
            _total_validators_count=Count(
                'user__validator__validator_wallets'
            )
        )

        # Filter by user address (or user id) if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(**user_lookup_kwargs(user_address, user_field='user'))
            # When filtering by user, don't apply type filter unless explicitly provided
            leaderboard_type = self.request.query_params.get('type')
            if leaderboard_type:
                queryset = queryset.filter(type=leaderboard_type)
        else:
            # Get type from query params
            leaderboard_type = self.request.query_params.get('type')

            if leaderboard_type:
                queryset = queryset.filter(type=leaderboard_type)
            else:
                # Default to validator leaderboard only when not filtering by user
                queryset = queryset.filter(type='validator')

            # Handle network filtering for validators
            # Only include validators with active wallets on the specified network.
            network = self.request.query_params.get('network')
            if network and leaderboard_type == 'validator':
                network_q = Q(
                    user__validator__validator_wallets__network=network,
                    user__validator__validator_wallets__status='active'
                )
                queryset = queryset.filter(network_q).distinct()

        # Handle rank ordering
        order = self.request.query_params.get('order', 'asc')
        if order == 'desc':
            queryset = queryset.order_by('-rank')
        else:
            queryset = queryset.order_by('rank')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Override to apply offset and limit after filtering/ordering.
        """
        if request.query_params.get('type') == 'community':
            return self.community(request)

        queryset = self.filter_queryset(self.get_queryset())
        include_count = request.query_params.get('include_count') in ('1', 'true', 'True', 'yes')
        total_count = queryset.count() if include_count else None

        # Parse offset and limit
        offset = 0
        limit = None
        try:
            offset = int(self.request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0

        limit_param = self.request.query_params.get('limit')
        if limit_param:
            try:
                limit = int(limit_param)
            except (ValueError, TypeError):
                limit = None

        # Apply offset and limit as a single slice to avoid Django slice-of-slice issues
        if limit is not None:
            queryset = queryset[offset:offset + limit]
        elif offset > 0:
            queryset = list(queryset[offset:])

        serializer = self.get_serializer(queryset, many=True)
        if include_count:
            return Response({
                'count': total_count,
                'results': serializer.data,
            })
        return Response(serializer.data)

    def get_serializer_context(self):
        """
        Add context flags to control serializer behavior.
        Use lightweight serializers for leaderboard to avoid expensive nested queries.
        """
        context = super().get_serializer_context()
        # Always use light serializers for leaderboard list view
        # User details in leaderboard don't need full validator/builder stats
        context['use_light_serializers'] = True
        # Never include expensive referral_details in leaderboard
        context['include_referral_details'] = False
        return context
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def recalculate(self, request):
        """
        Admin action to recalculate all leaderboards from scratch.
        """
        result = recalculate_all_leaderboards()
        return Response({
            'message': result,
            'status': 'success'
        }, status=status.HTTP_200_OK)
                        
    @action(detail=False, methods=['get'])
    def top(self, request):
        """
        Get the top 10 users on the validator leaderboard (default).
        """
        top_entries = LeaderboardEntry.objects.filter(user__visible=True, type='validator').order_by('rank')[:10]
        serializer = self.get_serializer(top_entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def monthly(self, request):
        """
        Get top portal point earners for the current month, or an explicit date
        range. Includes every contribution award and social-task completion in
        the category. Discord chat XP is cumulative and has no earning-event
        timestamp, so it cannot be attributed to a monthly window here.
        """
        from users.models import User
        from users.serializers import LightUserSerializer
        from social_tasks.models import SocialTaskCompletion

        leaderboard_type = request.query_params.get('type', 'validator')
        monthly_types = set(LEADERBOARD_CONFIG.keys()) | {'community'}
        if leaderboard_type not in monthly_types:
            return Response(
                {'detail': f'Unknown leaderboard type: {leaderboard_type}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            limit = int(request.query_params.get('limit', 10))
        except (TypeError, ValueError):
            limit = 10
        limit = min(max(limit, 1), 100)

        start_date_param = request.query_params.get('start_date')
        end_date_param = request.query_params.get('end_date')
        start_date = parse_date(start_date_param) if start_date_param else None
        end_date = parse_date(end_date_param) if end_date_param else None

        if start_date_param and not start_date:
            return Response(
                {'detail': 'Invalid start_date. Expected YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if end_date_param and not end_date:
            return Response(
                {'detail': 'Invalid end_date. Expected YYYY-MM-DD.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start_date and end_date and start_date > end_date:
            return Response(
                {'detail': 'start_date must be before or equal to end_date.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start_date:
            range_start = start_date
        else:
            now = timezone.localtime(timezone.now())
            range_start = now.replace(day=1).date()

        contribution_date_filters = {
            'contribution_date__date__gte': range_start,
        }
        social_task_date_filters = {
            'completed_at__date__gte': range_start,
        }
        if end_date:
            contribution_date_filters['contribution_date__date__lte'] = end_date
            social_task_date_filters['completed_at__date__lte'] = end_date

        monthly_query = Contribution.objects.filter(
            user__visible=True,
            contribution_type__category__slug=leaderboard_type,
            **contribution_date_filters,
        )
        monthly_social_tasks = SocialTaskCompletion.objects.filter(
            user__visible=True,
            task__category__slug=leaderboard_type,
            **social_task_date_filters,
        )
        if leaderboard_type != 'community':
            monthly_query = monthly_query.filter(user__leaderboard_entries__type=leaderboard_type)
            monthly_social_tasks = monthly_social_tasks.filter(
                user__leaderboard_entries__type=leaderboard_type,
            )

        contribution_totals = (
            monthly_query
            .values('user_id')
            .annotate(total_points=Sum('frozen_global_points'))
        )
        social_task_totals = (
            monthly_social_tasks
            .values('user_id')
            .annotate(total_points=Sum('points_awarded'))
        )

        totals_by_user = {}
        for entry in contribution_totals:
            totals_by_user[entry['user_id']] = {
                'contribution_points': entry['total_points'] or 0,
                'social_task_points': 0,
            }
        for entry in social_task_totals:
            totals = totals_by_user.setdefault(entry['user_id'], {
                'contribution_points': 0,
                'social_task_points': 0,
            })
            totals['social_task_points'] = entry['total_points'] or 0

        users_by_id = {
            user.id: user
            for user in User.objects.filter(id__in=totals_by_user)
        }
        monthly_totals = sorted(
            (
                {
                    'user_id': user_id,
                    **totals,
                    'total_points': (
                        totals['contribution_points'] + totals['social_task_points']
                    ),
                }
                for user_id, totals in totals_by_user.items()
                if user_id in users_by_id
                and totals['contribution_points'] + totals['social_task_points'] > 0
            ),
            key=lambda entry: (
                -entry['total_points'],
                (users_by_id[entry['user_id']].name or '').lower(),
                entry['user_id'],
            ),
        )[:limit]

        result = []
        for rank, entry in enumerate(monthly_totals, 1):
            user = users_by_id.get(entry['user_id'])
            if not user:
                continue
            result.append({
                'id': f'monthly-{leaderboard_type}-{user.id}',
                'user': user.id,
                'user_details': LightUserSerializer(user).data,
                'type': leaderboard_type,
                'total_points': entry['total_points'],
                'contribution_points': entry['contribution_points'],
                'social_task_points': entry['social_task_points'],
                'rank': rank,
            })

        return Response(result)
        
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get statistics for the dashboard.
        Supports optional 'type' parameter for category-specific stats.
        """
        from django.db.models import Sum
        from contributions.models import Contribution
        from social_tasks.models import SocialTaskCompletion
        from validators.models import Validator

        leaderboard_type = request.query_params.get('type')

        now = timezone.now()
        last_month = now - timezone.timedelta(days=30)
        effective_community_summary = None

        def get_validators():
            return Validator.objects.filter(user__visible=True)

        def get_effective_community_summary():
            nonlocal effective_community_summary
            if effective_community_summary is None:
                from community_xp.utils import (
                    effective_community_ranking_queryset,
                    get_community_member_user_ids,
                )

                score_queryset = effective_community_ranking_queryset(visible_only=True)
                effective_community_summary = {
                    'member_user_ids': get_community_member_user_ids(visible_only=True),
                    'total_points': score_queryset.aggregate(
                        total=Sum('total_points')
                    )['total'] or 0,
                    'user_ids': set(score_queryset.values_list('id', flat=True)),
                }
                effective_community_summary['member_count'] = len(
                    effective_community_summary['member_user_ids']
                )
            return effective_community_summary

        if leaderboard_type:
            # Category-specific stats
            leaderboard_entries = LeaderboardEntry.objects.filter(
                type=leaderboard_type,
                user__visible=True
            )

            # Get contribution count for this category
            category_map = {
                'validator': 'validator',
                'builder': 'builder',
                'steward': 'steward',
                'community': 'community'
            }
            category = category_map.get(leaderboard_type)

            if category:
                category_contributions = Contribution.objects.filter(
                    user__visible=True,
                    contribution_type__category__slug=category
                ).exclude(
                    contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS
                )
                contribution_count = category_contributions.count()
                new_contributions_count = category_contributions.filter(
                    created_at__gte=last_month
                ).count()
                category_social_tasks = SocialTaskCompletion.objects.filter(
                    user__visible=True,
                    task__category__slug=category,
                )
                # Raw contribution counts stay audit/activity metrics. Community
                # displayed score is MEE6 baseline + pending portal XP state.
                if leaderboard_type == 'community':
                    community_summary = get_effective_community_summary()
                    total_points = community_summary['total_points']
                    participant_count = community_summary['member_count']
                else:
                    total_points = category_contributions.aggregate(
                        total=Sum('frozen_global_points')
                    )['total'] or 0
                    total_points += category_social_tasks.aggregate(
                        total=Sum('points_awarded')
                    )['total'] or 0
                    if leaderboard_type == 'validator':
                        participant_count = get_validators().count()
                    else:
                        participant_count = category_contributions.values('user_id').distinct().count()

                new_points_count = category_contributions.filter(
                    created_at__gte=last_month
                ).aggregate(total=Sum('frozen_global_points'))['total'] or 0
                new_points_count += category_social_tasks.filter(
                    completed_at__gte=last_month,
                ).aggregate(total=Sum('points_awarded'))['total'] or 0
            else:
                contribution_count = 0
                new_contributions_count = 0
                new_points_count = 0
                total_points = leaderboard_entries.aggregate(
                    total=Sum('total_points')
                )['total'] or 0
                participant_count = leaderboard_entries.count()

        else:
            # Global stats
            all_contributions = Contribution.objects.filter(
                user__visible=True
            ).exclude(
                contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS
            )
            non_community_contributions = all_contributions.exclude(
                contribution_type__category__slug='community'
            )
            non_community_social_tasks = SocialTaskCompletion.objects.filter(
                user__visible=True,
            ).exclude(task__category__slug='community')
            community_summary = get_effective_community_summary()
            participant_user_ids = set(
                non_community_contributions
                .values_list('user_id', flat=True)
                .distinct()
            )
            participant_user_ids.update(community_summary['member_user_ids'])
            participant_count = len(participant_user_ids)
            contribution_count = all_contributions.count()
            new_contributions_count = all_contributions.filter(
                created_at__gte=last_month
            ).count()

            # Global displayed score uses raw non-community points plus the
            # effective community score, so raw community rows are not counted
            # again after they have been passed to Discord XP.
            total_points = (
                non_community_contributions.aggregate(
                    total=Sum('frozen_global_points')
                )['total'] or 0
            ) + (
                non_community_social_tasks.aggregate(
                    total=Sum('points_awarded')
                )['total'] or 0
            ) + community_summary['total_points']

            new_points_count = all_contributions.filter(
                created_at__gte=last_month
            ).aggregate(total=Sum('frozen_global_points'))['total'] or 0
            new_points_count += SocialTaskCompletion.objects.filter(
                user__visible=True,
                completed_at__gte=last_month,
            ).aggregate(total=Sum('points_awarded'))['total'] or 0

        builder_contribs = Contribution.objects.filter(
            user__visible=True,
            contribution_type__category__slug='builder',
        ).exclude(
            contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS
        )
        builder_count = builder_contribs.values('user_id').distinct().count()
        new_builders_count = builder_contribs.filter(
            created_at__gte=last_month
        ).values('user_id').distinct().count()

        validators = get_validators()
        validator_count = validators.count()
        new_validators_count = validators.filter(
            created_at__gte=last_month
        ).count()

        community_contribs = Contribution.objects.filter(
            user__visible=True,
            contribution_type__category__slug='community',
        ).exclude(
            contribution_type__slug__in=ONBOARDING_CONTRIBUTION_TYPE_SLUGS
        )
        community_summary = get_effective_community_summary()
        community_member_count = community_summary['member_count']
        from community_xp.utils import get_community_member_user_ids
        new_community_members_count = len(
            get_community_member_user_ids(visible_only=True, since=last_month)
        )

        return Response({
            'participant_count': participant_count,
            'contribution_count': contribution_count,
            'total_points': total_points,
            'builder_count': builder_count,
            'validator_count': validator_count,
            'community_member_count': community_member_count,
            # Backward-compatible alias for older clients.
            'creator_count': community_member_count,
            'new_community_members_count': new_community_members_count,
            'new_builders_count': new_builders_count,
            'new_validators_count': new_validators_count,
            'new_contributions_count': new_contributions_count,
            'new_points_count': new_points_count,
        })
        
    def _get_user_stats(self, user, category=None):
        """
        Helper method to get statistics for a user.

        Sums both `Contribution.frozen_global_points` and
        `SocialTaskCompletion.points_awarded` so the profile totals stay
        consistent with the builder/validator leaderboard ranks (which also
        include social-task points via
        `leaderboard.models.calculate_category_points`).

        Community social-task points are part of the shared effective community
        score. They remain separately reported as `socialTaskTotal` for the
        profile breakdown, but must not be added to that score a second time.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        from social_tasks.models import SocialTaskCompletion

        # Get user's contributions
        contributions = Contribution.objects.filter(user=user)

        # Get user's social-task completions (each is one "earning event")
        social_completions = SocialTaskCompletion.objects.filter(user=user)

        # Filter by category if provided
        if category:
            contributions = contributions.filter(contribution_type__category__slug=category)
            social_completions = social_completions.filter(task__category__slug=category)

        # Raw portal contribution points (audit trail). For community, displayed
        # points come from MEE6 via get_effective_community_points; for every
        # other category they are the headline number.
        raw_total_points = contributions.aggregate(
            total=Sum('frozen_global_points')
        )['total'] or 0
        social_points = social_completions.aggregate(
            total=Sum('points_awarded')
        )['total'] or 0

        community_xp_breakdown = None
        if category == 'community':
            from community_xp.utils import get_effective_community_points
            community_xp_breakdown = get_effective_community_points(user)
            base_points = community_xp_breakdown['total_points']
        else:
            base_points = raw_total_points

        # The effective community base already includes social-task points that
        # are not covered by the applied MEE6 snapshot. Other categories still
        # add their social-task stream directly.
        total_points = base_points if category == 'community' else base_points + social_points

        contribution_count = contributions.count()
        social_count = social_completions.count()
        total_count = contribution_count + social_count
        submittable_contribution_count = contributions.filter(
            contribution_type__is_submittable=True,
        ).count()

        avg_points = total_points / total_count if total_count > 0 else 0

        contribution_types = []
        types_data = contributions.values(
            'contribution_type__name',
            'contribution_type__id',
            'contribution_type__category__slug',
            'contribution_type__category__name'
        ).annotate(
            count=Count('id'),
            total_points=Sum('frozen_global_points')
        ).order_by('-total_points')

        for type_data in types_data:
            # Percentages are relative to contribution points only so the type
            # breakdown always sums to 100% — social-task points are reported
            # separately via socialTaskTotal, and community headline points are
            # MEE6-based.
            percentage = (type_data['total_points'] / raw_total_points * 100) if raw_total_points > 0 else 0
            contribution_types.append({
                'id': type_data['contribution_type__id'],
                'name': type_data['contribution_type__name'],
                'category_slug': type_data['contribution_type__category__slug'],
                'category_name': type_data['contribution_type__category__name'],
                'count': type_data['count'],
                'total_points': type_data['total_points'],
                'percentage': percentage,
            })

        result = {
            'totalContributions': total_count,
            'totalPoints': total_points,
            'averagePoints': avg_points,
            'contributionTypes': contribution_types,
            'submittableContributionCount': submittable_contribution_count,
            # Separate bucket so the frontend can render social-task earnings
            # next to the contribution breakdown without breaking the existing
            # ContributionBreakdown component (which expects entries to be real
            # ContributionType rows it can drill into).
            'socialTaskTotal': social_points,
            'socialTaskCount': social_count,
        }

        if community_xp_breakdown:
            result.update({
                'discord_xp': community_xp_breakdown['discord_xp'],
                'discord_xp_synced_at': community_xp_breakdown['discord_xp_synced_at'],
                'pending_portal_points': community_xp_breakdown['pending_portal_points'],
                'pending_social_task_points': community_xp_breakdown['pending_social_task_points'],
                'tracked_portal_points_all_time': community_xp_breakdown['tracked_portal_points_all_time'],
                'tracked_social_task_points_all_time': community_xp_breakdown['tracked_social_task_points_all_time'],
                'has_discord_xp_snapshot': community_xp_breakdown['has_discord_xp_snapshot'],
                'latest_applied_sync_completed_at': community_xp_breakdown['latest_applied_sync_completed_at'],
                'latest_applied_at': community_xp_breakdown['latest_applied_at'],
            })

        return result
        
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
        if not self._can_view_user_stats(user):
            return Response({'error': 'User not found'}, status=404)
        
        # Get category filter from query params
        category = request.query_params.get('category')
        stats = self._get_user_stats(user, category=category)
        return Response(stats)
            
    @action(detail=False, methods=['get'], url_path='user_stats/by-address/(?P<address>[^/.]+)')
    def user_stats_by_address(self, request, address=None):
        """
        Get statistics for a specific user by wallet address.
        """
        from users.models import User

        try:
            user = User.objects.get(**user_lookup_kwargs(address))
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        if not self._can_view_user_stats(user):
            return Response({'error': 'User not found'}, status=404)
        
        # Get category filter from query params
        category = request.query_params.get('category')
        stats = self._get_user_stats(user, category=category)
        return Response(stats)
    
    @action(detail=False, methods=['get'], url_path='validator-waitlist/top')
    def validator_waitlist_top(self, request):
        """
        Get top N waitlist users for the Race to Testnet Asimov leaderboard.
        Optimized endpoint that returns only what's needed for the top section.
        """
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        limit = min(max(limit, 1), 100)  # Between 1 and 100

        top_entries = LeaderboardEntry.objects.filter(
            user__visible=True,
            type='validator-waitlist'
        ).select_related(
            'user',
            'user__validator'
        ).order_by('rank')[:limit]

        serializer = self.get_serializer(top_entries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='validator-waitlist-stats')
    def validator_waitlist_stats(self, request):
        """
        Get comprehensive statistics for the waitlist dashboard.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        
        # Waitlist statistics
        waitlist_entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist',
            user__visible=True
        )
        
        # Graduation statistics
        graduation_entries = LeaderboardEntry.objects.filter(
            type='validator-waitlist-graduation',
            user__visible=True
        )
        
        # Calculate statistics
        waitlist_stats = waitlist_entries.aggregate(
            total_participants=Count('id'),
            total_points=Sum('total_points')
        )
        
        graduation_stats = graduation_entries.aggregate(
            total_graduated=Count('id'),
            total_graduated_points=Sum('total_points')
        )
        
        # Get contribution counts
        waitlist_user_ids = waitlist_entries.values_list('user_id', flat=True)
        graduated_user_ids = graduation_entries.values_list('user_id', flat=True)
        
        waitlist_contributions = Contribution.objects.filter(
            user_id__in=waitlist_user_ids
        ).count()
        
        graduated_contributions = Contribution.objects.filter(
            user_id__in=graduated_user_ids
        ).count()
        
        return Response({
            'total_participants': waitlist_stats['total_participants'] or 0,
            'total_contributions': waitlist_contributions,
            'total_graduated_contributions': graduated_contributions,
            'total_points': waitlist_stats['total_points'] or 0,
            'total_graduated_points': graduation_stats['total_graduated_points'] or 0,
            'total_graduated': graduation_stats['total_graduated'] or 0
        })
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get all available leaderboard types and their configuration.
        """
        types_info = []
        for key, config in LEADERBOARD_CONFIG.items():
            types_info.append({
                'key': key,
                'name': config['name'],
                'ranking_order': config['ranking_order']
            })

        return Response(types_info)

    @action(detail=False, methods=['get'])
    def community(self, request):
        """
        Get community statistics and paginated creators.
        Returns users sorted by effective community points.
        Supports limit/offset pagination and user_address lookup.
        """
        from users.models import User
        from users.serializers import LightUserSerializer
        from community_xp.utils import (
            build_effective_community_ranking_queryset,
            build_effective_community_scores_queryset,
            get_community_member_user_ids,
        )

        try:
            limit = int(request.query_params.get('limit', 20))
        except (ValueError, TypeError):
            limit = 20
        limit = min(max(limit, 1), 100)

        try:
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0
        offset = max(offset, 0)

        member_user_ids = get_community_member_user_ids(visible_only=True)
        ranking_snapshot = list(
            build_effective_community_ranking_queryset(
                user_ids=member_user_ids,
                visible_only=True,
            )
            .filter(total_points__gte=COMMUNITY_RANKING_MIN_POINTS)
            .order_by('-total_points', 'community_sort_name', 'id')
            .values_list('id', 'total_points')
        )
        ranked_user_ids = [user_id for user_id, _ in ranking_snapshot]
        rank_by_user_id = {
            user_id: rank
            for rank, (user_id, _) in enumerate(ranking_snapshot, start=1)
        }
        position_by_user_id = {
            user_id: position
            for position, user_id in enumerate(ranked_user_ids)
        }
        total_points_by_user_id = dict(ranking_snapshot)

        search = request.query_params.get('search', '').strip().lower()
        filtered_user_ids = ranked_user_ids
        if search:
            address_q = (
                Q(address__iexact=search) if is_full_address(search) else Q()
            )
            search_user_ids = set(
                User.objects
                .filter(id__in=ranked_user_ids, visible=True)
                .filter(Q(name__icontains=search) | address_q)
                .values_list('id', flat=True)
            )
            filtered_user_ids = [
                user_id for user_id in ranked_user_ids
                if user_id in search_user_ids
            ]

        count = len(filtered_user_ids)
        user_address = request.query_params.get('user_address')
        user_id = None
        user_rank = None
        user_total_points = None

        def serialize_community_user(user):
            user_data = LightUserSerializer(user).data
            total_points = total_points_by_user_id[user.id]
            return {
                **user_data,
                'user_details': user_data,
                'user_address': truncate_address(user.address),
                'user_name': user.name,
                'community_points': total_points,
                'total_points': total_points,
                'contribution_count': user.community_contribution_count or 0,
                'discord_xp': user.discord_xp,
                'discord_xp_synced_at': user.discord_xp_synced_at,
                'pending_portal_points': user.pending_portal_points,
                'pending_social_task_points': user.pending_social_task_points,
                'tracked_portal_points_all_time': user.tracked_portal_points_all_time,
                'tracked_social_task_points_all_time': user.tracked_social_task_points_all_time,
                'has_discord_xp_snapshot': user.has_discord_xp_snapshot,
                'latest_applied_sync_completed_at': user.latest_applied_sync_completed_at,
                'latest_applied_at': user.latest_applied_at,
                'rank': rank_by_user_id[user.id],
            }

        def get_full_details(user_ids):
            if not user_ids:
                return {}
            return {
                user.id: user
                for user in build_effective_community_scores_queryset(
                    user_ids=user_ids,
                    visible_only=True,
                )
            }

        if user_address:
            user_id = (
                User.objects
                .filter(visible=True, **user_lookup_kwargs(user_address))
                .values_list('id', flat=True)
                .first()
            )
            if user_id in rank_by_user_id:
                user_total_points = total_points_by_user_id[user_id]
                user_rank = rank_by_user_id[user_id]

        if request.query_params.get('profile_context') in ('1', 'true', 'True', 'yes'):
            top_user_id = ranked_user_ids[0] if ranked_user_ids else None
            context_user_ids = []

            if user_rank:
                user_position = position_by_user_id[user_id]
                context_offset = max(user_position - 1, 0)
                context_user_ids = ranked_user_ids[context_offset:context_offset + 3]

            detail_user_ids = list(dict.fromkeys(
                ([top_user_id] if top_user_id is not None else []) + context_user_ids
            ))
            details_by_user_id = get_full_details(detail_user_ids)
            top_user = details_by_user_id.get(top_user_id)
            top_entry = (
                serialize_community_user(top_user)
                if top_user is not None else None
            )
            context_results = [
                serialize_community_user(details_by_user_id[context_user_id])
                for context_user_id in context_user_ids
                if context_user_id in details_by_user_id
            ]

            return Response({
                'total_community': count,
                'count': count,
                'top_entry': top_entry,
                'context_results': context_results,
                'user_rank': user_rank,
                'user_total_points': user_total_points,
            })

        page_user_ids = filtered_user_ids[offset:offset + limit]
        details_by_user_id = get_full_details(page_user_ids)
        results = [
            serialize_community_user(details_by_user_id[page_user_id])
            for page_user_id in page_user_ids
            if page_user_id in details_by_user_id
        ]

        response_data = {
            'total_community': count,
            'count': count,
            'results': results,
        }

        if user_address:
            response_data['user_rank'] = user_rank
            response_data['user_total_points'] = user_total_points

        return Response(response_data)

    @action(detail=False, methods=['get'], url_path='community-podium')
    def community_podium(self, request):
        """Top three Community users by points from accepted submissions only."""
        from users.models import User
        from users.serializers import LightUserSerializer

        accepted_submission = SubmittedContribution.objects.filter(
            state='accepted',
            converted_contribution_id=OuterRef('pk'),
        )
        podium_rows = list(
            Contribution.objects
            .filter(
                user__visible=True,
                contribution_type__category__slug='community',
            )
            .annotate(has_accepted_submission=Exists(accepted_submission))
            .filter(has_accepted_submission=True)
            .values('user_id')
            .annotate(total_points=Sum('frozen_global_points'))
            .filter(total_points__gt=0)
            .order_by('-total_points', 'user__name', 'user_id')[:3]
        )

        users_by_id = {
            user.id: user
            for user in User.objects.filter(
                id__in=[row['user_id'] for row in podium_rows],
            )
        }
        return Response([
            {
                'id': f'community-podium-{row["user_id"]}',
                'user': row['user_id'],
                'user_details': LightUserSerializer(users_by_id[row['user_id']]).data,
                'type': 'community',
                'total_points': row['total_points'],
                'rank': rank,
            }
            for rank, row in enumerate(podium_rows, start=1)
            if row['user_id'] in users_by_id
        ])

    @action(detail=False, methods=['get'])
    def referrals(self, request):
        """
        Get referral leaderboard entries sorted by total referral points.
        """
        from .models import ReferralPoints
        from users.serializers import LightUserSerializer
        from django.db.models import F

        try:
            limit = int(request.query_params.get('limit', 20))
        except (ValueError, TypeError):
            limit = 20
        limit = min(max(limit, 1), 100)

        try:
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0

        referral_qs = ReferralPoints.objects.select_related('user').annotate(
            total_points=F('builder_points') + F('validator_points')
        ).filter(user__visible=True, total_points__gt=0).order_by('-total_points')

        search = request.query_params.get('search', '').strip()
        if search:
            address_q = (
                Q(user__address__iexact=search) if is_full_address(search) else Q()
            )
            referral_qs = referral_qs.filter(
                Q(user__name__icontains=search) | address_q
            )

        totals = referral_qs.aggregate(
            total_referrers=Count('id'),
            total_builder=Sum('builder_points'),
            total_validator=Sum('validator_points')
        )

        user_address = request.query_params.get('user_address')
        user_rank = None
        user_total_points = None
        if user_address:
            try:
                user_rp = referral_qs.get(**user_lookup_kwargs(user_address, user_field='user'))
                user_total_points = user_rp.builder_points + user_rp.validator_points
                user_rank = referral_qs.filter(total_points__gt=user_total_points).count() + 1
            except ReferralPoints.DoesNotExist:
                pass

        page = referral_qs[offset:offset + limit]
        results = []
        for rank, rp in enumerate(page, start=offset + 1):
            user_data = LightUserSerializer(rp.user).data
            results.append({
                **user_data,
                'referral_builder_points': rp.builder_points,
                'referral_validator_points': rp.validator_points,
                'total_referral_points': rp.builder_points + rp.validator_points,
                'total_points': rp.builder_points + rp.validator_points,
                'rank': rank,
            })

        response_data = {
            'total_referrers': totals['total_referrers'] or 0,
            'total_builder_points': totals['total_builder'] or 0,
            'total_validator_points': totals['total_validator'] or 0,
            'count': totals['total_referrers'] or 0,
            'results': results,
        }

        if user_address:
            response_data['user_rank'] = user_rank
            response_data['user_total_points'] = user_total_points

        return Response(response_data)

    @action(detail=False, methods=['get'], url_path='community-contributors')
    def community_contributors(self, request):
        """Backward-compatible alias for the community points leaderboard."""
        return self.community(request)

    @action(detail=False, methods=['get'])
    def trending(self, request):
        """
        Get users who earned the most points recently.
        Tries last 30 days first; falls back to all-time if no data.
        When category is provided, only that category's point increase is used.
        Otherwise, each contributor includes the recent category where they gained
        the most points so the UI can show the matching badge and delta.
        """
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        limit = min(max(limit, 1), 100)
        category_slug = request.query_params.get('category')
        if category_slug == 'global':
            category_slug = None

        from datetime import timedelta
        from users.models import User

        cutoff = timezone.now() - timedelta(days=30)

        def build_points_query(*, recent_only=True):
            query = Contribution.objects.filter(user__visible=True)
            if recent_only:
                query = query.filter(created_at__gte=cutoff)
            if category_slug:
                query = query.filter(contribution_type__category__slug=category_slug)
            return (
                query
                .values('user_id', 'contribution_type__category__slug')
                .annotate(total_points=Sum('frozen_global_points'))
            )

        def summarize_by_user(rows):
            by_user = {}
            for row in rows:
                user_id = row['user_id']
                category = row['contribution_type__category__slug'] or 'community'
                points = row['total_points'] or 0
                entry = by_user.setdefault(user_id, {
                    'user_id': user_id,
                    'total_recent_points': 0,
                    'category_points': {},
                    'top_category': category_slug or category,
                    'top_category_points': 0,
                })
                entry['total_recent_points'] += points
                entry['category_points'][category] = entry['category_points'].get(category, 0) + points

            for entry in by_user.values():
                if category_slug:
                    entry['top_category'] = category_slug
                    entry['top_category_points'] = entry['category_points'].get(category_slug, 0)
                elif entry['category_points']:
                    top_category, top_points = max(
                        entry['category_points'].items(),
                        key=lambda item: item[1],
                    )
                    entry['top_category'] = top_category
                    entry['top_category_points'] = top_points

            return sorted(
                by_user.values(),
                key=lambda entry: (
                    entry['top_category_points'] if category_slug else entry['total_recent_points'],
                    entry['top_category_points'],
                ),
                reverse=True,
            )[:limit]

        # Aggregate points per user/category from last 30 days
        trending_users = summarize_by_user(build_points_query(recent_only=True))

        # Fall back to all-time if no recent data
        if not trending_users:
            trending_users = summarize_by_user(build_points_query(recent_only=False))

        # Legacy recent fallback for older Contribution rows that cannot join a
        # category; only runs when trending_users is still empty and category_slug
        # was not requested.
        if not trending_users and not category_slug:
            trending_users = list(
                Contribution.objects.filter(
                    created_at__gte=cutoff,
                    user__visible=True,
                )
                .values('user_id')
                .annotate(total_recent_points=Sum('frozen_global_points'))
                .order_by('-total_recent_points')[:limit]
            )

        # Final legacy all-time fallback without cutoff when the recent legacy
        # Contribution aggregation still produced no trending_users.
        if not trending_users and not category_slug:
            trending_users = list(
                Contribution.objects.filter(user__visible=True)
                .values('user_id')
                .annotate(total_recent_points=Sum('frozen_global_points'))
                .order_by('-total_recent_points')[:limit]
            )

        user_ids = [entry['user_id'] for entry in trending_users]
        users = User.objects.filter(id__in=user_ids).select_related(
            'builder', 'validator', 'steward'
        )
        users_by_id = {u.id: u for u in users}

        results = []
        for entry in trending_users:
            user = users_by_id.get(entry['user_id'])
            if not user:
                continue
            top_category = entry.get('top_category') or category_slug or 'community'
            top_category_points = entry.get('top_category_points')
            if top_category_points is None:
                top_category_points = entry.get('total_recent_points') or 0
            results.append({
                'user_id': user.id,
                'user_name': user.name or '',
                'user_address': truncate_address(user.address) or '',
                'profile_image_url': user.profile_image_url or '',
                'total_points': top_category_points,
                'trending_points': top_category_points,
                'total_recent_points': entry.get('total_recent_points') or top_category_points,
                'top_category': top_category,
                'top_category_points': top_category_points,
                'category_points': entry.get('category_points') or {top_category: top_category_points},
                'builder': hasattr(user, 'builder'),
                'validator': hasattr(user, 'validator'),
                'steward': hasattr(user, 'steward'),
            })

        return Response(results)
    
