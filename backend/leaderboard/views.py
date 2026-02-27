from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Count, Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
from .models import GlobalLeaderboardMultiplier, LeaderboardEntry, update_all_ranks, recalculate_all_leaderboards, LEADERBOARD_CONFIG
from .serializers import GlobalLeaderboardMultiplierSerializer, LeaderboardEntrySerializer
from contributions.models import Category, Contribution


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
    search_fields = ['user__email', 'user__name', 'user__address']
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
            'user__creator'
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

        # Handle rank ordering
        order = self.request.query_params.get('order', 'asc')
        if order == 'desc':
            queryset = queryset.order_by('-rank')
        else:
            queryset = queryset.order_by('rank')

        return queryset

    def list(self, request, *args, **kwargs):
        """
        Override to apply limit after filtering/ordering.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Apply limit after filtering and ordering
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass

        serializer = self.get_serializer(queryset, many=True)
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
    def stats(self, request):
        """
        Get statistics for the dashboard.
        Supports optional 'type' parameter for category-specific stats.
        """
        from django.db.models import Sum, Count
        from contributions.models import Contribution
        from users.models import User

        leaderboard_type = request.query_params.get('type')

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if leaderboard_type:
            # Category-specific stats
            leaderboard_entries = LeaderboardEntry.objects.filter(
                type=leaderboard_type,
                user__visible=True
            )

            participant_count = leaderboard_entries.count()
            total_points = leaderboard_entries.aggregate(
                total=Sum('total_points')
            )['total'] or 0

            # Get contribution count for this category
            category_map = {
                'validator': 'validator',
                'builder': 'builder',
                'steward': 'steward'
            }
            category = category_map.get(leaderboard_type)

            if category:
                category_contributions = Contribution.objects.filter(
                    contribution_type__category__slug=category
                ).exclude(
                    contribution_type__slug__in=['builder-welcome', 'validator-waitlist']
                )
                contribution_count = category_contributions.count()
                new_contributions_count = category_contributions.filter(
                    created_at__gte=month_start
                ).count()
                new_points_count = category_contributions.filter(
                    created_at__gte=month_start
                ).aggregate(total=Sum('frozen_global_points'))['total'] or 0
            else:
                contribution_count = 0
                new_contributions_count = 0
                new_points_count = 0

            # New participants this month for the specific leaderboard type
            if leaderboard_type == 'builder':
                new_builders_count = LeaderboardEntry.objects.filter(
                    type='builder', user__created_at__gte=month_start
                ).count()
                new_validators_count = 0
            elif leaderboard_type == 'validator':
                new_builders_count = 0
                new_validators_count = LeaderboardEntry.objects.filter(
                    type='validator', user__created_at__gte=month_start
                ).count()
            else:
                new_builders_count = 0
                new_validators_count = 0
        else:
            # Global stats
            participant_count = User.objects.filter(
                contributions__isnull=False,
                visible=True
            ).distinct().count()

            all_contributions = Contribution.objects.exclude(
                contribution_type__slug__in=['builder-welcome', 'validator-waitlist']
            )
            contribution_count = all_contributions.count()
            new_contributions_count = all_contributions.filter(
                created_at__gte=month_start
            ).count()

            total_points = Contribution.objects.aggregate(
                total=Sum('frozen_global_points')
            )['total'] or 0

            new_points_count = Contribution.objects.filter(
                created_at__gte=month_start
            ).aggregate(total=Sum('frozen_global_points'))['total'] or 0

            new_builders_count = LeaderboardEntry.objects.filter(
                type='builder', user__created_at__gte=month_start
            ).count()
            new_validators_count = LeaderboardEntry.objects.filter(
                type='validator', user__created_at__gte=month_start
            ).count()

        # Category-specific counts (always included)
        builder_count = LeaderboardEntry.objects.filter(
            type='builder', user__visible=True
        ).count()
        validator_count = LeaderboardEntry.objects.filter(
            type='validator', user__visible=True
        ).count()

        from .models import ReferralPoints
        from django.db.models import F
        creator_count = ReferralPoints.objects.filter(
            user__visible=True
        ).annotate(
            total_pts=F('builder_points') + F('validator_points')
        ).filter(total_pts__gt=0).count()

        return Response({
            'participant_count': participant_count,
            'contribution_count': contribution_count,
            'total_points': total_points,
            'builder_count': builder_count,
            'validator_count': validator_count,
            'creator_count': creator_count,
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
            'contribution_type__id',
            'contribution_type__category__slug',
            'contribution_type__category__name'
        ).annotate(
            count=Count('id'),
            total_points=Sum('frozen_global_points')
        ).order_by('-total_points')
        
        for type_data in types_data:
            percentage = (type_data['total_points'] / total_points * 100) if total_points > 0 else 0
            contribution_types.append({
                'id': type_data['contribution_type__id'],
                'name': type_data['contribution_type__name'],
                'category_slug': type_data['contribution_type__category__slug'],
                'category_name': type_data['contribution_type__category__name'],
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
        Get community statistics and all community members with referral points.
        Returns users with referrals sorted by total referral points.
        """
        from .models import ReferralPoints
        from users.serializers import UserSerializer
        from django.db.models import F

        # Get all referral points ordered by total points (builder + validator)
        referral_points = ReferralPoints.objects.select_related('user').annotate(
            total_points=F('builder_points') + F('validator_points')
        ).filter(user__visible=True, total_points__gt=0).order_by('-total_points')

        # Calculate aggregate stats
        total_community = referral_points.count()
        total_builder_points = sum(rp.builder_points for rp in referral_points)
        total_validator_points = sum(rp.validator_points for rp in referral_points)

        # Get all community members
        top_community = []
        for rp in referral_points:
            user_data = UserSerializer(rp.user).data
            top_community.append({
                **user_data,
                'builder_points': rp.builder_points,
                'validator_points': rp.validator_points,
                'total_points': rp.builder_points + rp.validator_points
            })

        return Response({
            'total_community': total_community,
            'total_builder_points': total_builder_points,
            'total_validator_points': total_validator_points,
            'top_community': top_community
        })

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
    
