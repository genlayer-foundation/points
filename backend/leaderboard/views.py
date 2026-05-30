from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from .models import GlobalLeaderboardMultiplier, LeaderboardEntry, update_all_ranks, recalculate_all_leaderboards, LEADERBOARD_CONFIG
from .serializers import GlobalLeaderboardMultiplierSerializer, LeaderboardEntrySerializer
from contributions.models import Category, Contribution

ONBOARDING_CONTRIBUTION_TYPE_SLUGS = [
    'builder-welcome',
    'builder',
    'validator-waitlist',
    'validator',
    'community-link-x',
    'community-link-discord',
]
JOURNEY_AUTO_AWARD_SLUGS = ONBOARDING_CONTRIBUTION_TYPE_SLUGS


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
    Filter by type to get specific leaderboards:
    - ?type=validator - Active validators
    - ?type=builder - Builders
    - ?type=steward - Stewards
    - ?type=validator-waitlist - Waitlisted users (not yet validators)
    """
    queryset = LeaderboardEntry.objects.filter(user__visible=True)
    serializer_class = LeaderboardEntrySerializer
    permission_classes = [permissions.AllowAny]  # Allow access without authentication
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['user__name', 'user__address']
    ordering_fields = ['rank', 'total_points', 'updated_at']
    ordering = ['rank']
    pagination_class = None  # Disable pagination to return all entries

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

        # Filter by user address if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(user__address__iexact=user_address)
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

            if leaderboard_type == 'builder':
                eligible_builder_contributions = Contribution.objects.filter(
                    user_id=OuterRef('user_id'),
                    contribution_type__category__slug='builder',
                ).exclude(
                    contribution_type__slug__in=['builder-welcome', 'builder'],
                )
                queryset = queryset.filter(Exists(eligible_builder_contributions))

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
        Get top contributors for the current month, starting on day 1.
        """
        from users.models import User
        from users.serializers import LightUserSerializer

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

        now = timezone.localtime(timezone.now())
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_query = Contribution.objects.filter(
            user__visible=True,
            contribution_type__category__slug=leaderboard_type,
            contribution_date__gte=month_start,
        )
        if leaderboard_type != 'community':
            monthly_query = monthly_query.filter(user__leaderboard_entries__type=leaderboard_type)

        monthly_totals = (
            monthly_query
            .exclude(contribution_type__slug__in=JOURNEY_AUTO_AWARD_SLUGS)
            .values('user_id')
            .annotate(total_points=Sum('frozen_global_points'))
            .order_by('-total_points', 'user__name')[:limit]
        )

        user_ids = [entry['user_id'] for entry in monthly_totals]
        users_by_id = {
            user.id: user
            for user in User.objects.filter(id__in=user_ids)
        }

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
                'total_points': entry['total_points'] or 0,
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
                # Raw contribution counts stay audit/activity metrics. Community
                # displayed score is MEE6 baseline + pending portal XP state.
                if leaderboard_type == 'community':
                    community_summary = get_effective_community_summary()
                    total_points = community_summary['total_points']
                    participant_count = community_summary['member_count']
                elif leaderboard_type == 'validator':
                    total_points = category_contributions.aggregate(
                        total=Sum('frozen_global_points')
                    )['total'] or 0
                    participant_count = get_validators().count()
                else:
                    total_points = category_contributions.aggregate(
                        total=Sum('frozen_global_points')
                    )['total'] or 0
                    participant_count = category_contributions.values('user_id').distinct().count()

                new_points_count = category_contributions.filter(
                    created_at__gte=last_month
                ).aggregate(total=Sum('frozen_global_points'))['total'] or 0
            else:
                contribution_count = 0
                new_contributions_count = 0
                new_points_count = 0
                total_points = leaderboard_entries.aggregate(
                    total=Sum('total_points')
                )['total'] or 0
                participant_count = leaderboard_entries.count()

            # New participants in the last 30 days for the specific leaderboard type
            if leaderboard_type == 'builder':
                new_builders_count = LeaderboardEntry.objects.filter(
                    type='builder', user__created_at__gte=last_month
                ).count()
                new_validators_count = 0
            elif leaderboard_type == 'validator':
                new_builders_count = 0
                new_validators_count = get_validators().filter(
                    created_at__gte=last_month
                ).count()
            else:
                new_builders_count = 0
                new_validators_count = 0
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
            ) + community_summary['total_points']

            new_points_count = all_contributions.filter(
                created_at__gte=last_month
            ).aggregate(total=Sum('frozen_global_points'))['total'] or 0

            new_builders_count = LeaderboardEntry.objects.filter(
                type='builder', user__created_at__gte=last_month
            ).count()
            new_validators_count = LeaderboardEntry.objects.filter(
                type='validator', user__created_at__gte=last_month
            ).count()

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
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        
        # Get user's contributions
        contributions = Contribution.objects.filter(user=user)
        
        # Filter by category if provided
        if category:
            contributions = contributions.filter(contribution_type__category__slug=category)
        
        # Get user's raw portal contribution points. For community, these remain
        # the audit trail while displayed points use MEE6 as the weekly baseline.
        raw_total_points = contributions.aggregate(
            total=Sum('frozen_global_points')
        )['total'] or 0
        total_points = raw_total_points

        community_xp_breakdown = None
        if category == 'community':
            from community_xp.utils import get_effective_community_points
            community_xp_breakdown = get_effective_community_points(user)
            total_points = community_xp_breakdown['total_points']
        
        # Get user's contribution count
        contribution_count = contributions.count()
        
        # Get average points per contribution
        avg_points = total_points / contribution_count if contribution_count > 0 else 0
        
        # Get contribution breakdown by type
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
            percentage_base = raw_total_points if category == 'community' else total_points
            percentage = (type_data['total_points'] / percentage_base * 100) if percentage_base > 0 else 0
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
            'totalContributions': contribution_count,
            'totalPoints': total_points,
            'averagePoints': avg_points,
            'contributionTypes': contribution_types,
        }

        if community_xp_breakdown:
            result.update({
                'discord_xp': community_xp_breakdown['discord_xp'],
                'discord_xp_synced_at': community_xp_breakdown['discord_xp_synced_at'],
                'pending_portal_points': community_xp_breakdown['pending_portal_points'],
                'tracked_portal_points_all_time': community_xp_breakdown['tracked_portal_points_all_time'],
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
            user = User.objects.get(address__iexact=address)
        except User.DoesNotExist:
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
        Get community statistics and paginated community members.
        Returns users sorted by effective community points.
        Supports limit/offset pagination and user_address lookup.
        """
        from users.serializers import LightUserSerializer
        from community_xp.utils import effective_community_ranking_queryset

        try:
            limit = int(request.query_params.get('limit', 20))
        except (ValueError, TypeError):
            limit = 20
        limit = min(max(limit, 1), 100)

        try:
            offset = int(request.query_params.get('offset', 0))
        except (ValueError, TypeError):
            offset = 0

        entries = effective_community_ranking_queryset(visible_only=True)

        search = request.query_params.get('search', '').strip().lower()
        if search:
            entries = entries.filter(
                Q(name__icontains=search) |
                Q(address__icontains=search)
            )

        count = entries.count()
        user_address = request.query_params.get('user_address')
        user_rank = None
        user_total_points = None

        def serialize_community_user(user, rank):
            user_data = LightUserSerializer(user).data
            total_points = user.total_points or 0
            return {
                **user_data,
                'user_details': user_data,
                'user_address': user.address,
                'user_name': user.name,
                'community_points': total_points,
                'total_points': total_points,
                'contribution_count': user.community_contribution_count or 0,
                'discord_xp': user.discord_xp,
                'discord_xp_synced_at': user.discord_xp_synced_at,
                'pending_portal_points': user.pending_portal_points,
                'tracked_portal_points_all_time': user.tracked_portal_points_all_time,
                'has_discord_xp_snapshot': user.has_discord_xp_snapshot,
                'latest_applied_sync_completed_at': user.latest_applied_sync_completed_at,
                'latest_applied_at': user.latest_applied_at,
                'rank': rank,
            }

        if user_address:
            user_entry = entries.filter(address__iexact=user_address).first()
            if user_entry:
                user_total_points = user_entry.total_points or 0
                user_sort_name = user_entry.community_sort_name or ''
                user_rank = entries.filter(
                    Q(total_points__gt=user_total_points) |
                    Q(
                        total_points=user_total_points,
                        community_sort_name__lt=user_sort_name,
                    ) |
                    Q(
                        total_points=user_total_points,
                        community_sort_name=user_sort_name,
                        id__lt=user_entry.id,
                    )
                ).count() + 1

        if request.query_params.get('profile_context') in ('1', 'true', 'True', 'yes'):
            top_user = entries.first()
            top_entry = serialize_community_user(top_user, 1) if top_user else None
            context_results = []

            if user_rank:
                context_offset = max(user_rank - 2, 0)
                context_page = entries[context_offset:context_offset + 3]
                context_results = [
                    serialize_community_user(user, rank)
                    for rank, user in enumerate(context_page, start=context_offset + 1)
                ]

            return Response({
                'total_community': count,
                'count': count,
                'top_entry': top_entry,
                'context_results': context_results,
                'user_rank': user_rank,
                'user_total_points': user_total_points,
            })

        page = entries[offset:offset + limit]

        results = []
        for index, user in enumerate(page, start=offset + 1):
            results.append(serialize_community_user(user, index))

        response_data = {
            'total_community': count,
            'count': count,
            'results': results,
        }

        if user_address:
            response_data['user_rank'] = user_rank
            response_data['user_total_points'] = user_total_points

        return Response(response_data)

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
            referral_qs = referral_qs.filter(
                Q(user__name__icontains=search) |
                Q(user__address__icontains=search)
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
                user_rp = referral_qs.get(user__address__iexact=user_address)
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
        """
        try:
            limit = int(request.query_params.get('limit', 10))
        except (ValueError, TypeError):
            limit = 10
        limit = min(max(limit, 1), 100)

        from datetime import timedelta
        from users.models import User

        cutoff = timezone.now() - timedelta(days=30)

        # Aggregate points per user from last 30 days
        trending_users = list(
            Contribution.objects.filter(
                created_at__gte=cutoff,
                user__visible=True,
            )
            .values('user_id')
            .annotate(total_points=Sum('frozen_global_points'))
            .order_by('-total_points')[:limit]
        )

        # Fall back to all-time if no recent data
        if not trending_users:
            trending_users = list(
                Contribution.objects.filter(user__visible=True)
                .values('user_id')
                .annotate(total_points=Sum('frozen_global_points'))
                .order_by('-total_points')[:limit]
            )

        user_ids = [entry['user_id'] for entry in trending_users]
        points_map = {entry['user_id']: entry['total_points'] for entry in trending_users}

        users = User.objects.filter(id__in=user_ids).select_related(
            'builder', 'validator', 'steward'
        )
        users_by_id = {u.id: u for u in users}

        results = []
        for user_id in user_ids:
            user = users_by_id.get(user_id)
            if not user:
                continue
            results.append({
                'user_name': user.name or '',
                'user_address': user.address or '',
                'profile_image_url': user.profile_image_url or '',
                'total_points': points_map[user_id] or 0,
                'builder': hasattr(user, 'builder'),
                'validator': hasattr(user, 'validator'),
                'steward': hasattr(user, 'steward'),
            })

        return Response(results)
    
