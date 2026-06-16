import uuid

from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, BooleanFilter, NumberFilter
from django.utils import timezone
from django.conf import settings
from django.db import transaction
from django.db.models import (
    Count,
    DecimalField,
    Exists,
    F,
    IntegerField,
    Max,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
)
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth
from django.db.models.functions import Coalesce, Greatest
from django.shortcuts import get_object_or_404
from .models import (
    ContributionType, Contribution, Evidence, SubmittedContribution,
    SubmissionNote, ContributionHighlight, Mission, StartupRequest,
    FeaturedContent, Alert, ContributionDiscordXPState,
    DiscordXPDistributionEvent, ProjectMilestoneReview,
    sync_discord_xp_state_for_contribution,
)
from .rubric_review import rubric_summary_text, uses_project_rubric
from .serializers import (ContributionTypeSerializer, ContributionSerializer,
                         EvidenceSerializer, SubmittedContributionSerializer,
                         SubmittedEvidenceSerializer, ContributionHighlightSerializer,
                         StewardSubmissionSerializer, StewardSubmissionReviewSerializer,
                         StewardAcceptedSubmissionUpdateSerializer,
                         SubmissionNoteSerializer, SubmissionProposeSerializer,
                         MissionSerializer, StartupRequestListSerializer, StartupRequestDetailSerializer,
                         FeaturedContentSerializer, AlertSerializer,
                         ContributionDiscordXPStateSerializer)
from .permissions import IsSteward, steward_has_permission, steward_permitted_type_ids
from .project_milestones import (
    accepted_project_contributions_for_user,
    is_milestone_contribution_type,
    next_milestone_version,
    project_contribution_display_title,
    project_contribution_github_url,
)
from .url_utils import normalize_url
from leaderboard.models import GlobalLeaderboardMultiplier
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from ethereum_auth.authentication import EthereumAuthentication
import requests

METRICS_POINTS_EXCLUDED_TYPE_SLUGS = [
    'builder-welcome',
    'builder',
    'validator-waitlist',
    'validator',
    'community-link-x',
    'community-link-discord',
]

AI_STEWARD_EMAIL = 'genlayer-steward@genlayer.foundation'


class ContributionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contribution types to be viewed.
    """
    queryset = ContributionType.objects.all()
    serializer_class = ContributionTypeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_queryset(self):
        active_submissions = SubmittedContribution.objects.exclude(
            state__in=['rejected', 'canceled']
        )
        submission_count = active_submissions.filter(
            contribution_type_id=OuterRef('pk')
        ).values('contribution_type_id').annotate(
            count=Count('pk')
        ).values('count')
        multiplier_field = DecimalField(max_digits=10, decimal_places=2)
        current_multiplier = GlobalLeaderboardMultiplier.objects.filter(
            contribution_type_id=OuterRef('pk')
        ).order_by('-valid_from').values('multiplier_value')[:1]

        queryset = ContributionType.objects.select_related('category').annotate(
            submission_count=Coalesce(
                Subquery(submission_count, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            current_multiplier_value=Coalesce(
                Subquery(current_multiplier, output_field=multiplier_field),
                Value(1.0, output_field=multiplier_field),
                output_field=multiplier_field,
            ),
        )

        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
            # Exclude Builder Welcome when filtering for builder category
            if category == 'builder':
                queryset = queryset.exclude(slug='builder-welcome')

        # Filter by is_submittable if provided (for user submission forms)
        is_submittable = self.request.query_params.get('is_submittable')
        if is_submittable is not None:
            queryset = queryset.filter(is_submittable=is_submittable.lower() == 'true')

        return queryset.prefetch_related(
            'accepted_evidence_url_types',
            'required_evidence_url_types',
            'required_discord_roles',
        ).order_by('category__name', 'name', 'id')

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def statistics(self, request):
        """
        Get aggregated statistics for each contribution type.
        Returns:
            - count of each contribution type
            - current points multiplier
            - number of participants with each type
            - last date someone earned each type
            - total points given for each type
        """
        # Start with all contribution types
        queryset = ContributionType.objects.all()

        # Filter by category if provided
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
            # Exclude Builder Welcome when filtering for builder category
            if category == 'builder':
                queryset = queryset.exclude(slug='builder-welcome')
        
        multiplier_field = DecimalField(max_digits=10, decimal_places=2)
        current_multiplier = GlobalLeaderboardMultiplier.objects.filter(
            contribution_type_id=OuterRef('pk')
        ).order_by('-valid_from').values('multiplier_value')[:1]

        types_with_stats = queryset.annotate(
            category_slug=F('category__slug'),
            count=Count('contributions'),
            participants_count=Count('contributions__user', distinct=True),
            last_earned=Coalesce(Max('contributions__contribution_date'), timezone.now()),
            total_points_given=Coalesce(Sum('contributions__frozen_global_points'), 0),
            current_multiplier=Coalesce(
                Subquery(current_multiplier, output_field=multiplier_field),
                Value(1.0, output_field=multiplier_field),
                output_field=multiplier_field,
            ),
        ).values(
            'id', 'name', 'description', 'min_points', 'max_points', 'count',
            'participants_count', 'last_earned', 'total_points_given',
            'is_submittable', 'show_in_contributions', 'current_multiplier',
            'category_slug',
        )
            
        return Response(list(types_with_stats))
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def top_contributors(self, request, pk=None):
        """
        Get top 10 contributors for a specific contribution type.
        Returns users with the most points for this contribution type.
        """
        from django.db.models import Sum
        from users.serializers import LightUserSerializer

        contribution_type = self.get_object()

        # Get top contributors by summing their frozen global points for this type
        top_contributors = Contribution.objects.filter(
            contribution_type=contribution_type
        ).values('user').annotate(
            total_points=Sum('frozen_global_points'),
            contribution_count=Count('id')
        ).order_by('-total_points')[:10]

        # Fetch users directly with optimization
        user_ids = [c['user'] for c in top_contributors]
        from users.models import User
        users_dict = {
            user.id: user
            for user in User.objects.filter(id__in=user_ids).select_related('validator', 'builder')
        }

        # Build result with lightweight serializer
        result = []
        for contributor in top_contributors:
            user = users_dict.get(contributor['user'])
            if user:
                user_data = LightUserSerializer(user).data
                user_data['total_points'] = contributor['total_points']
                user_data['contribution_count'] = contributor['contribution_count']
                result.append(user_data)

        return Response(result)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def recent_contributions(self, request, pk=None):
        """
        Get the last 10 contributions for a specific contribution type.
        Uses lightweight serializers to avoid N+1 queries.
        """
        contribution_type = self.get_object()

        recent_contributions = Contribution.objects.filter(
            contribution_type=contribution_type
        ).select_related(
            'user',
            'user__validator',
            'user__builder',
            'contribution_type',
            'contribution_type__category'
        ).order_by('-contribution_date')[:10]

        # Use light serializers for list view
        context = {
            'use_light_serializers': True,
            'include_referral_details': False,
            'request': request
        }
        serializer = ContributionSerializer(recent_contributions, many=True, context=context)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def highlights(self, request, pk=None):
        """
        Get active highlights for a specific contribution type.
        """
        contribution_type = self.get_object()
        limit = int(request.query_params.get('limit', 5))

        highlights = ContributionHighlight.get_active_highlights(
            contribution_type=contribution_type,
            limit=limit
        )

        # Prefetch evidence items to avoid N+1 queries and enable evidence display
        highlights = highlights.select_related(
            'contribution__user',
            'contribution__contribution_type'
        ).prefetch_related(
            'contribution__evidence_items'
        )

        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)
    


class ContributionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contributions to be viewed.
    """
    queryset = Contribution.objects.all().order_by('-contribution_date')
    serializer_class = ContributionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'contribution_type', 'mission']
    search_fields = ['notes', 'user__name', 'user__address', 'contribution_type__name']
    ordering_fields = ['contribution_date', 'created_at', 'points', 'frozen_global_points']
    ordering = ['-contribution_date']
    
    def get_queryset(self):
        queryset = Contribution.objects.all().order_by('-contribution_date')

        # Comprehensive prefetch to avoid N+1 queries
        # Only prefetch what we need based on whether we're using light serializers
        queryset = queryset.select_related(
            'user',
            'user__validator',  # For validator info in user details
            'user__builder',    # For builder info in user details
            'contribution_type',
            'contribution_type__category',
            'mission',  # Avoid N+1 queries when accessing mission details
            'project_contribution',
        ).prefetch_related(
            'evidence_items',  # Only queried in detail view (light serializers skip this)
            'highlights',      # Only queried in detail view (light serializers skip this)
            'project_contribution__evidence_items',  # Milestone repo link
        )

        # Filter by user address if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(user__address__iexact=user_address)

        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(contribution_type__category__slug=category)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date or end_date:
            from django.utils.dateparse import parse_date

            parsed_start = parse_date(start_date) if start_date else None
            parsed_end = parse_date(end_date) if end_date else None
            if parsed_start:
                queryset = queryset.filter(contribution_date__date__gte=parsed_start)
            if parsed_end:
                queryset = queryset.filter(contribution_date__date__lte=parsed_end)

        # Exclude onboarding contributions (builder-welcome and validator-waitlist)
        # EXCEPT when viewing a specific user's profile (user_address is present)
        if not user_address:
            queryset = queryset.exclude(
                contribution_type__slug__in=['builder-welcome', 'validator-waitlist']
            )

        # Optionally remove journey/social-link onboarding records so dashboard
        # contribution lists match member metrics.
        exclude_onboarding = self.request.query_params.get('exclude_onboarding')
        if exclude_onboarding and exclude_onboarding.lower() == 'true':
            queryset = queryset.exclude(
                contribution_type__slug__in=METRICS_POINTS_EXCLUDED_TYPE_SLUGS
            )

        submittable_only = self.request.query_params.get('submittable_only')
        if submittable_only and submittable_only.lower() == 'true':
            queryset = queryset.filter(contribution_type__is_submittable=True)

        public_explorer_only = self.request.query_params.get('public_explorer_only')
        if public_explorer_only and public_explorer_only.lower() == 'true':
            queryset = queryset.filter(
                Q(contribution_type__is_submittable=True) |
                Q(contribution_type__show_in_contributions=True)
            )

        return queryset

    def get_serializer_context(self):
        """
        Add context flags to control serializer behavior.
        Use lightweight serializers for list views to improve performance.
        """
        context = super().get_serializer_context()
        # Use light serializers for list views (action='list')
        # Use full serializers for detail views (action='retrieve')
        context['use_light_serializers'] = self.action == 'list'
        return context
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def highlights(self, request):
        """
        Get all active highlights across all contribution types.
        Optionally filter by category or waitlist users.
        """
        from contributions.models import Category, ContributionType
        from django.db.models import Q
        
        limit_param = request.query_params.get('limit')
        limit = 10
        if limit_param is not None:
            try:
                limit = int(limit_param)
            except (TypeError, ValueError):
                return Response(
                    {'detail': 'limit must be an integer.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if limit < 0:
                return Response(
                    {'detail': 'limit must be greater than or equal to 0.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        category_slug = request.query_params.get('category')
        waitlist_only = request.query_params.get('waitlist_only', 'false').lower() == 'true'
        
        # Start with all highlights
        queryset = ContributionHighlight.objects.all()
        
        # Filter by category if provided
        if category_slug and category_slug != 'global':
            try:
                category = Category.objects.get(slug=category_slug)
                queryset = queryset.filter(contribution__contribution_type__category=category)
            except Category.DoesNotExist:
                # If category doesn't exist, return empty list
                return Response([])
        
        if waitlist_only:
            # Get all users with waitlist badge
            waitlist_type = ContributionType.objects.filter(
                slug='validator-waitlist'
            ).first()
            
            if not waitlist_type:
                return Response([])
            
            waitlist_users = Contribution.objects.filter(
                contribution_type=waitlist_type
            ).values_list('user_id', flat=True).distinct()
            
            # Build complex query for graduated users
            validator_type = ContributionType.objects.filter(
                slug='validator'
            ).first()
            
            if validator_type:
                # Get graduation dates for each user
                graduation_dates = {}
                validator_contribs = Contribution.objects.filter(
                    contribution_type=validator_type,
                    user_id__in=waitlist_users
                ).values('user_id', 'contribution_date').order_by('user_id', 'contribution_date')
                
                for vc in validator_contribs:
                    if vc['user_id'] not in graduation_dates:
                        graduation_dates[vc['user_id']] = vc['contribution_date']
                
                # Build Q objects for filtering
                q_filters = Q()
                for user_id in waitlist_users:
                    if user_id in graduation_dates:
                        # Graduated - only show pre-graduation highlights
                        q_filters |= Q(
                            contribution__user_id=user_id,
                            contribution__contribution_date__lt=graduation_dates[user_id]
                        )
                    else:
                        # Still on waitlist - show all highlights
                        q_filters |= Q(contribution__user_id=user_id)
                
                queryset = queryset.filter(q_filters)
            else:
                # No validator type, just filter by waitlist users
                queryset = queryset.filter(contribution__user_id__in=waitlist_users)
        
        # Order by featured date descending. `limit=0` is used by the
        # all-contributions explorer so local filters can search every highlight.
        highlights = queryset.select_related(
            'contribution__user',
            'contribution__user__validator',
            'contribution__user__builder',
            'contribution__user__steward',
            'contribution__contribution_type',
            'contribution__contribution_type__category'
        ).prefetch_related(
            'contribution__evidence_items'
        ).order_by('-created_at', '-contribution__contribution_date')

        if limit > 0:
            highlights = highlights[:limit]
        
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows evidence to be viewed.
    """
    queryset = Evidence.objects.all().order_by('-created_at')
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['contribution', 'contribution__user']
    search_fields = ['description', 'url']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        """
        Evidence attached to accepted contributions is public review material;
        evidence on pending/rejected submissions is only visible to its owner,
        to staff, and to stewards holding a permission on the submission's
        contribution type (mirroring StewardSubmissionViewSet visibility).
        """
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_staff:
            return queryset
        visible = Q(contribution__isnull=False) | Q(submitted_contribution__user=user)
        if hasattr(user, 'steward'):
            permitted_type_ids = steward_permitted_type_ids(
                user,
                actions=['accept', 'reject', 'request_more_info', 'propose'],
            )
            visible |= Q(submitted_contribution__contribution_type_id__in=permitted_type_ids)
        return queryset.filter(visible)


# API ViewSets for user submissions
class SubmittedContributionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for users to submit and view their contributions.
    """
    serializer_class = SubmittedContributionSerializer
    authentication_classes = [EthereumAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        """Users can only see their own submissions."""
        return SubmittedContribution.objects.filter(
            user=self.request.user
        ).select_related(
            'contribution_type',
            'contribution_type__category',
            'reviewed_by',
            'converted_contribution',
            'user',  # Optimize user access
            'mission',  # Avoid N+1 queries when accessing mission details
            'project_contribution',
        ).prefetch_related(
            'evidence_items',
            'evidence_items__url_type',
            'project_contribution__evidence_items',  # Milestone repo link
        ).order_by('-created_at')

    def get_serializer_context(self):
        """
        Add context flags to control serializer behavior.
        Use lightweight serializers for list views to improve performance.
        """
        context = super().get_serializer_context()
        # Use light serializers for list views only
        # my_submissions needs full data including evidence
        context['use_light_serializers'] = self.action == 'list'
        return context

    def _validate_required_discord_roles(self, user, contribution_type):
        """Ensure the user has at least one role required by this type."""
        required_roles = list(
            contribution_type.required_discord_roles.filter(
                deleted_at__isnull=True,
            ).exclude(
                role_id=F('guild_id'),
            )
        )
        if not required_roles:
            return None

        try:
            connection = user.discordconnection
        except Exception:
            return Response(
                {'error': 'You must link your Discord account to submit this type of contribution.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        recently_synced = (
            connection.roles_synced_at
            and (timezone.now() - connection.roles_synced_at).total_seconds()
            <= int(getattr(settings, 'DISCORD_ROLE_SUBMISSION_SYNC_GRACE_SECONDS', 30))
        )

        if not recently_synced:
            try:
                from social_connections.discord_roles import (
                    DiscordRoleSyncConfigurationError,
                    DiscordRoleSyncError,
                    DiscordRoleSyncService,
                    DiscordRoleSyncUnavailable,
                )

                result = DiscordRoleSyncService().sync_member_roles(connection)
                connection = result.connection
            except DiscordRoleSyncConfigurationError:
                return Response(
                    {'error': 'Discord role verification is not configured. Please try again later.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except DiscordRoleSyncUnavailable:
                return Response(
                    {'error': 'Discord role verification is temporarily unavailable. Please try again later.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            except DiscordRoleSyncError:
                return Response(
                    {'error': 'Discord role verification failed. Please try again later.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

        if not connection.guild_member:
            return Response(
                {'error': 'You must be a member of the GenLayer Discord server to submit this type of contribution.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_role_ids = set(
            connection.current_roles.filter(
                deleted_at__isnull=True,
            ).values_list('role_id', flat=True)
        )
        required_role_ids = {role.role_id for role in required_roles}
        if user_role_ids.isdisjoint(required_role_ids):
            role_names = ', '.join(role.name for role in required_roles)
            return Response(
                {'error': f'You need one of these Discord roles to submit this contribution: {role_names}.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        return None

    def _validate_submission_contribution_type(
        self,
        user,
        contribution_type,
        mission=None,
        skip_capacity_check=False,
    ):
        """Validate role, category, and requirement gates for submissions."""
        if mission and contribution_type.id != mission.contribution_type_id:
            return Response(
                {'error': 'Mission submissions must use the mission contribution type.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not contribution_type.is_submittable and mission is None:
            return Response(
                {'error': 'This contribution type cannot be submitted directly. Submit through one of its active missions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not skip_capacity_check and contribution_type.is_full():
            return Response(
                {'error': 'This contribution type has reached its submission limit.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if contribution_type.category:
            if contribution_type.category.slug == 'builder' and not hasattr(user, 'builder'):
                return Response(
                    {'error': 'You must complete the Builder Welcome journey before submitting builder contributions.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            if contribution_type.category.slug == 'validator' and not hasattr(user, 'validator'):
                return Response(
                    {'error': 'Only validators can submit validator contributions. Join the Validator Waitlist to be considered for selection.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        if contribution_type.required_social_accounts:
            connection_map = {
                'twitter': ('twitterconnection', 'X (Twitter)'),
                'discord': ('discordconnection', 'Discord'),
                'github': ('githubconnection', 'GitHub'),
            }
            missing = []
            for account in contribution_type.required_social_accounts:
                relation, label = connection_map.get(account, (None, account))
                if relation and not hasattr(user, relation):
                    missing.append(label)
            if missing:
                return Response(
                    {'error': f'You must link your {", ".join(missing)} account(s) to submit this type of contribution.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        discord_role_error = self._validate_required_discord_roles(user, contribution_type)
        if discord_role_error is not None:
            return discord_role_error

        return None

    def _project_link_error(self, user, contribution_type, project_contribution_id):
        """Validate project-contribution linking rules for Milestones submissions."""
        if is_milestone_contribution_type(contribution_type):
            if not project_contribution_id:
                return None, Response(
                    {'error': 'Milestones must be linked to one of your accepted projects.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                project_contribution = accepted_project_contributions_for_user(user).get(
                    id=project_contribution_id,
                )
            except (Contribution.DoesNotExist, ValueError, TypeError):
                # ValueError/TypeError cover malformed ids (e.g. 'abc') that
                # would otherwise raise during pk conversion before DRF's
                # PrimaryKeyRelatedField validation runs.
                return None, Response(
                    {'error': 'Select one of your accepted projects before submitting a milestone.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return project_contribution, None

        if project_contribution_id:
            return None, Response(
                {'error': 'Projects can only be linked to Milestones submissions.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None, None

    def _milestone_notes_error(self, contribution_type, notes):
        """Milestones are reviewed from the linked project's repository, so the
        written explanation of what changed is the required content."""
        if is_milestone_contribution_type(contribution_type) and not (notes or '').strip():
            return Response(
                {'error': 'Please describe the changes and improvements in this milestone.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def create(self, request, *args, **kwargs):
        """Create a new submission with optional mission tracking."""
        # Block banned users from submitting
        if request.user.is_banned:
            return Response(
                {'error': 'Your account has been suspended due to repeated '
                          'policy violations. You may submit one appeal from '
                          'your profile page.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        mission_id = request.data.get('mission')
        mission = None
        data = request.data.copy()  # Create mutable copy for modifications

        # Validate mission if provided
        if mission_id:
            try:
                mission = Mission.objects.get(id=mission_id)
                # Validate mission timing with specific error messages
                now = timezone.now()
                if mission.start_date and now < mission.start_date:
                    return Response(
                        {'error': 'This mission has not started yet.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if mission.end_date and now > mission.end_date:
                    return Response(
                        {'error': 'This mission has ended.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if mission.is_full():
                    return Response(
                        {'error': 'This mission has reached its submission limit.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                if mission.is_full_for_user(request.user):
                    return Response(
                        {'error': 'You have reached your submission limit for this mission.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Always enforce contribution_type consistency with mission
                data['contribution_type'] = mission.contribution_type_id
            except Mission.DoesNotExist:
                return Response(
                    {'error': 'Invalid mission ID.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Validate category restrictions based on user role
        contribution_type_id = data.get('contribution_type')
        if contribution_type_id:
            try:
                contribution_type = (
                    ContributionType.objects
                    .select_related('category')
                    .prefetch_related('required_discord_roles')
                    .get(id=contribution_type_id)
                )
                contribution_type_error = self._validate_submission_contribution_type(
                    request.user,
                    contribution_type,
                    mission,
                )
                if contribution_type_error is not None:
                    return contribution_type_error

                project_contribution_id = data.get('project_contribution')
                milestone_project_contribution, project_error = self._project_link_error(
                    request.user,
                    contribution_type,
                    project_contribution_id,
                )
                if project_error is not None:
                    return project_error

                notes_error = self._milestone_notes_error(
                    contribution_type,
                    data.get('notes'),
                )
                if notes_error is not None:
                    return notes_error
            except ContributionType.DoesNotExist:
                pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        if mission_id or contribution_type_id:
            with transaction.atomic():
                locked_type = ContributionType.objects.select_for_update().get(
                    id=serializer.validated_data['contribution_type'].id
                )
                if locked_type.is_full():
                    return Response(
                        {'error': 'This contribution type has reached its submission limit.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                serializer.validated_data['contribution_type'] = locked_type

                if mission_id:
                    locked_mission = Mission.objects.select_for_update().get(
                        id=mission.id
                    )
                    if locked_mission.is_full():
                        return Response(
                            {'error': 'This mission has reached its submission limit.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    if locked_mission.is_full_for_user(request.user):
                        return Response(
                            {'error': 'You have reached your submission limit for this mission.'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    serializer.validated_data['mission'] = locked_mission

                if is_milestone_contribution_type(locked_type):
                    locked_project_contribution = Contribution.objects.select_for_update().get(
                        id=milestone_project_contribution.id
                    )
                    if not accepted_project_contributions_for_user(request.user).filter(
                        id=locked_project_contribution.id,
                    ).exists():
                        return Response(
                            {'error': 'Select one of your accepted projects before submitting a milestone.'},
                            status=status.HTTP_403_FORBIDDEN,
                        )
                    serializer.validated_data['project_contribution'] = locked_project_contribution
                    serializer.validated_data['milestone_version'] = next_milestone_version(
                        locked_project_contribution,
                    )
                else:
                    serializer.validated_data['project_contribution'] = None
                    serializer.validated_data['milestone_version'] = None

                self.perform_create(serializer)
        else:
            self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Update submission (only allowed if state is 'pending' or 'more_info_needed')."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Check if update is allowed
        if instance.state not in ['pending', 'more_info_needed']:
            return Response(
                {'error': 'Submission can only be edited when pending or when more information is requested.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Appealed submissions are locked while awaiting re-review so the
        # submitter can't edit-around the appeal. Once a steward explicitly
        # asks for more info, edits are allowed again so the submitter can
        # respond.
        if instance.has_appeal and instance.state == 'pending':
            return Response(
                {'error': 'Appealed submissions cannot be edited while awaiting re-review.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if 'mission' in request.data:
            requested_mission = request.data.get('mission')
            current_mission = str(instance.mission_id) if instance.mission_id else None
            if requested_mission in ('', None):
                requested_mission = None
            else:
                requested_mission = str(requested_mission)
            if requested_mission != current_mission:
                return Response(
                    {'error': 'Mission cannot be changed after submission.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Update the submission
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        contribution_type = (
            serializer.validated_data.get('contribution_type')
            or instance.contribution_type
        )
        mission = serializer.validated_data.get('mission', instance.mission)
        contribution_type = (
            ContributionType.objects
            .select_related('category')
            .prefetch_related('required_discord_roles')
            .get(id=contribution_type.id)
        )
        keeps_same_contribution_type = contribution_type.id == instance.contribution_type_id
        contribution_type_error = self._validate_submission_contribution_type(
            request.user,
            contribution_type,
            mission,
            skip_capacity_check=keeps_same_contribution_type,
        )
        if contribution_type_error is not None:
            return contribution_type_error

        project_contribution_id = (
            request.data.get('project_contribution')
            if 'project_contribution' in request.data
            else (instance.project_contribution_id if instance.project_contribution_id else None)
        )
        milestone_project_contribution, project_error = self._project_link_error(
            request.user,
            contribution_type,
            project_contribution_id,
        )
        if project_error is not None:
            return project_error

        notes_error = self._milestone_notes_error(
            contribution_type,
            serializer.validated_data.get('notes', instance.notes),
        )
        if notes_error is not None:
            return notes_error

        with transaction.atomic():
            if is_milestone_contribution_type(contribution_type):
                # Lock the project contribution row (as create does) so
                # concurrent edits pointing at the same project cannot be
                # assigned the same milestone version.
                locked_project_contribution = Contribution.objects.select_for_update().get(
                    id=milestone_project_contribution.id
                )
                if not accepted_project_contributions_for_user(request.user).filter(
                    id=locked_project_contribution.id,
                ).exists():
                    return Response(
                        {'error': 'Select one of your accepted projects before submitting a milestone.'},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                serializer.validated_data['project_contribution'] = locked_project_contribution
                needs_new_version = (
                    instance.contribution_type_id != contribution_type.id
                    or instance.project_contribution_id != locked_project_contribution.id
                    or not instance.milestone_version
                )
                if needs_new_version:
                    serializer.validated_data['milestone_version'] = next_milestone_version(
                        locked_project_contribution,
                        exclude_submission_id=instance.id,
                    )
            else:
                serializer.validated_data['project_contribution'] = None
                serializer.validated_data['milestone_version'] = None

            # Update state back to pending and track edit time
            instance.state = 'pending'
            instance.last_edited_at = timezone.now()
            instance.staff_reply = ''  # Clear previous staff reply

            self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """
        Soft delete submission by marking as canceled.

        Only pending or more_info_needed submissions can be canceled.
        """
        instance = self.get_object()

        # Check if cancellation is allowed
        if instance.state not in ['pending', 'more_info_needed']:
            return Response(
                {'error': 'Only pending or unreviewed submissions can be canceled.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Soft delete - mark as canceled with cancellation note
        instance.state = 'canceled'
        # Preserve the original rejection reason if this submission was appealed;
        # otherwise record the cancellation in staff_reply.
        if not instance.has_appeal:
            instance.staff_reply = 'Canceled by user'
        instance.reviewed_at = timezone.now()
        instance.save()

        return Response(
            {'message': 'Submission canceled successfully'},
            status=status.HTTP_200_OK,
        )
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_submissions(self, request):
        """Get all submissions for the authenticated user."""
        queryset = self.get_queryset()

        # Optional deep-link filter used by submission review links. Keeping this
        # owner-scoped through get_queryset() prevents leaking other users'
        # submission IDs while making highlighted submission landings reliable
        # across pagination.
        submission_id = request.query_params.get('submission')
        if submission_id:
            try:
                queryset = queryset.filter(id=uuid.UUID(str(submission_id)))
            except ValueError:
                queryset = queryset.none()
        else:
            # Filter by state if provided. When a specific submission id is
            # requested, ignore state because notification links freeze the
            # decision state at send time and the submission may have moved on.
            state = request.query_params.get('state')
            if state:
                queryset = queryset.filter(state=state)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='accepted-projects')
    def accepted_projects(self, request):
        """Return the user's accepted Projects contributions milestones can link to."""
        project_contributions = (
            accepted_project_contributions_for_user(request.user)
            .prefetch_related('evidence_items')
            .order_by('-contribution_date', '-id')
        )
        data = [
            {
                'id': contribution.id,
                'title': project_contribution_display_title(contribution),
                'link': f'/contribution/{contribution.id}',
                'github_url': project_contribution_github_url(contribution),
                'contribution_date': contribution.contribution_date,
                'next_milestone_version': next_milestone_version(contribution),
            }
            for contribution in project_contributions
        ]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='appeal')
    def appeal(self, request, pk=None):
        """Submitter appeals a rejected submission. Allowed once per submission."""
        if request.user.is_banned:
            return Response(
                {'error': 'Your account has been suspended due to repeated '
                          'policy violations. You may submit one appeal from '
                          'your profile page.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        submission = self.get_object()

        if submission.state != 'rejected':
            return Response(
                {'error': 'Only rejected submissions can be appealed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission.has_appeal:
            return Response(
                {'error': 'This submission has already been appealed.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = (request.data.get('reason') or '').strip()
        if not reason:
            return Response(
                {'error': 'An appeal reason is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(reason) > 5000:
            return Response(
                {'error': 'Appeal reason must be 5000 characters or fewer.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            submission.has_appeal = True
            submission.appeal_reason = reason
            submission.state = 'pending'
            submission.reviewed_by = None
            submission.reviewed_at = None
            submission.save(update_fields=[
                'has_appeal', 'appeal_reason', 'state',
                'reviewed_by', 'reviewed_at', 'updated_at',
            ])

            SubmissionNote.objects.create(
                submitted_contribution=submission,
                user=request.user,
                message=f'APPEAL: {reason}',
                is_proposal=False,
                data={'kind': 'appeal'},
            )

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='add-evidence')
    def add_evidence(self, request, pk=None):
        """Add evidence to a submission."""
        submission = self.get_object()

        # Check if evidence can be added
        if submission.state not in ['pending', 'more_info_needed']:
            return Response(
                {'error': 'Evidence can only be added to pending submissions or when more information is requested.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Appealed submissions are locked while awaiting re-review; once a
        # steward asks for more info, the submitter can attach new evidence.
        if submission.has_appeal and submission.state == 'pending':
            return Response(
                {'error': 'Appealed submissions cannot be edited while awaiting re-review.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Reject file uploads
        if 'file' in request.data or request.FILES:
            return Response(
                {'error': 'File uploads are not currently supported. Please provide a URL instead.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = SubmittedEvidenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create evidence linked to this submission
        evidence = Evidence.objects.create(
            submitted_contribution=submission,
            **serializer.validated_data
        )

        return Response(
            SubmittedEvidenceSerializer(evidence).data,
            status=status.HTTP_201_CREATED
        )


class StewardSubmissionFilterSet(FilterSet):
    """Custom filterset for steward submission filtering."""
    username_search = CharFilter(method='filter_username')
    exclude_username = CharFilter(method='filter_exclude_username')
    assigned_to = CharFilter(method='filter_assigned_to')
    exclude_assigned_to = CharFilter(method='filter_exclude_assigned_to')
    reviewed_by = CharFilter(method='filter_reviewed_by')
    exclude_reviewed_by = CharFilter(method='filter_exclude_reviewed_by')
    proposed_by = CharFilter(method='filter_proposed_by')
    exclude_proposed_by = CharFilter(method='filter_exclude_proposed_by')
    exclude_contribution_type = NumberFilter(method='filter_exclude_contribution_type')
    exclude_content = CharFilter(method='filter_exclude_content')
    include_content = CharFilter(method='filter_include_content')
    exclude_empty_evidence = BooleanFilter(method='filter_exclude_empty_evidence')
    only_empty_evidence = BooleanFilter(method='filter_only_empty_evidence')
    exclude_state = CharFilter(method='filter_exclude_state')
    min_accepted_contributions = NumberFilter(method='filter_min_accepted_contributions')
    has_proposal = BooleanFilter(method='filter_has_proposal')
    proposed_action = CharFilter(method='filter_proposed_action')
    proposed_confidence = CharFilter(method='filter_proposed_confidence')
    proposed_template = NumberFilter(method='filter_proposed_template')
    is_interesting = BooleanFilter(field_name='is_interesting')
    search = CharFilter(method='filter_search')
    category = CharFilter(method='filter_category')
    exclude_category = CharFilter(method='filter_exclude_category')
    mission = CharFilter(method='filter_mission')
    exclude_mission = CharFilter(method='filter_exclude_mission')
    has_appeal = BooleanFilter(field_name='has_appeal')
    resubmitted_more_info = BooleanFilter(method='filter_resubmitted_more_info')

    def _split_filter_values(self, value):
        return [
            item.strip()
            for item in str(value).split(',')
            if item and item.strip()
        ]

    def _parse_id_filter_value(self, value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _normalized_url_query(self, term):
        if '://' not in term and not term.lower().startswith('www.'):
            return Q()
        normalized = normalize_url(term)
        if not normalized:
            return Q()
        return Q(normalized_url=normalized)

    def _evidence_content_query(self, term):
        return (
            Q(url__icontains=term) |
            Q(description__icontains=term) |
            self._normalized_url_query(term)
        )

    def _content_query(self, term):
        submitted_evidence = Evidence.objects.filter(
            submitted_contribution=OuterRef('pk')
        ).filter(self._evidence_content_query(term))
        converted_evidence = Evidence.objects.filter(
            contribution_id=OuterRef('converted_contribution_id')
        ).filter(self._evidence_content_query(term))
        return (
            Q(title__icontains=term) |
            Q(notes__icontains=term) |
            Q(converted_contribution__title__icontains=term) |
            Q(converted_contribution__notes__icontains=term) |
            Exists(submitted_evidence) |
            Exists(converted_evidence)
        )

    def filter_search(self, queryset, name, value):
        """General search across submitter, title, notes, and evidence."""
        if value:
            return queryset.filter(
                Q(user__name__icontains=value) |
                Q(user__address__icontains=value) |
                self._content_query(value)
            )
        return queryset

    def filter_category(self, queryset, name, value):
        """Filter by contribution type category slug."""
        if value:
            return queryset.filter(contribution_type__category__slug=value)
        return queryset

    def filter_exclude_category(self, queryset, name, value):
        """Exclude submissions from a specific category."""
        if value:
            return queryset.exclude(contribution_type__category__slug=value)
        return queryset

    def filter_username(self, queryset, name, value):
        """Filter by submitter name or address (case-insensitive partial match)."""
        if value:
            return queryset.filter(
                Q(user__name__icontains=value) |
                Q(user__address__icontains=value)
            )
        return queryset

    def filter_exclude_username(self, queryset, name, value):
        """Exclude submissions from users matching the search."""
        if value:
            return queryset.exclude(
                Q(user__name__icontains=value) |
                Q(user__address__icontains=value)
            )
        return queryset

    def filter_assigned_to(self, queryset, name, value):
        """Filter by assigned steward or unassigned."""
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                if item == 'null' or item == 'unassigned':
                    query |= Q(assigned_to__isnull=True)
                else:
                    parsed_id = self._parse_id_filter_value(item)
                    if parsed_id is not None:
                        query |= Q(assigned_to_id=parsed_id)
            return queryset.filter(query) if query else queryset.none()
        return queryset

    def filter_exclude_assigned_to(self, queryset, name, value):
        """Exclude submissions assigned to a specific steward."""
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                if item == 'null' or item == 'unassigned':
                    query |= Q(assigned_to__isnull=True)
                else:
                    parsed_id = self._parse_id_filter_value(item)
                    if parsed_id is not None:
                        query |= Q(assigned_to_id=parsed_id)
            return queryset.exclude(query) if query else queryset
        return queryset

    def filter_reviewed_by(self, queryset, name, value):
        """Filter by steward who took the review action."""
        values = self._split_filter_values(value)
        if values:
            parsed_ids = [
                parsed_id for parsed_id in
                (self._parse_id_filter_value(item) for item in values)
                if parsed_id is not None
            ]
            return queryset.filter(reviewed_by_id__in=parsed_ids) if parsed_ids else queryset.none()
        return queryset

    def filter_exclude_reviewed_by(self, queryset, name, value):
        """Exclude submissions reviewed by a specific steward."""
        values = self._split_filter_values(value)
        if values:
            parsed_ids = [
                parsed_id for parsed_id in
                (self._parse_id_filter_value(item) for item in values)
                if parsed_id is not None
            ]
            return queryset.exclude(reviewed_by_id__in=parsed_ids) if parsed_ids else queryset
        return queryset

    def _proposed_by_condition(self, value):
        if value in ('none', 'null', 'unproposed'):
            return Q(proposed_by__isnull=True)
        if value == 'ai':
            return Q(proposed_by__email=AI_STEWARD_EMAIL)
        parsed_id = self._parse_id_filter_value(value)
        if parsed_id is None:
            return None
        return Q(proposed_by_id=parsed_id)

    def filter_proposed_by(self, queryset, name, value):
        """Filter by steward or agent who created the active proposal."""
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                condition = self._proposed_by_condition(item)
                if condition is not None:
                    query |= condition
            return queryset.filter(query) if query else queryset.none()
        return queryset

    def filter_exclude_proposed_by(self, queryset, name, value):
        """Exclude active proposals created by a specific steward or agent."""
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                condition = self._proposed_by_condition(item)
                if condition is not None:
                    query |= condition
            return queryset.exclude(query) if query else queryset
        return queryset

    def filter_exclude_contribution_type(self, queryset, name, value):
        """Exclude submissions of a specific contribution type."""
        if value:
            return queryset.exclude(contribution_type_id=value)
        return queryset

    def filter_exclude_state(self, queryset, name, value):
        """Exclude submissions with specific state."""
        if value:
            return queryset.exclude(state=value)
        return queryset

    def filter_exclude_content(self, queryset, name, value):
        """Exclude submissions containing text in title, notes, or evidence."""
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    queryset = queryset.exclude(self._content_query(term))
        return queryset

    def filter_include_content(self, queryset, name, value):
        """Include ONLY submissions containing text in title, notes, or evidence."""
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    queryset = queryset.filter(self._content_query(term))
        return queryset

    def filter_exclude_empty_evidence(self, queryset, name, value):
        """Exclude submissions that have no evidence URL AND no URL in notes."""
        if value:
            # Subquery: check if submission has at least one evidence item with URL
            has_url_evidence = Evidence.objects.filter(
                submitted_contribution=OuterRef('pk'),
                url__gt=''
            )
            # Exclude submissions where:
            # - No evidence item has a URL AND
            # - Notes don't contain a URL (http:// or https://)
            return queryset.exclude(
                ~Exists(has_url_evidence) &
                ~Q(notes__icontains='http://') &
                ~Q(notes__icontains='https://')
            )
        return queryset

    def filter_only_empty_evidence(self, queryset, name, value):
        """Include ONLY submissions without URL evidence (inverse of exclude_empty_evidence)."""
        if value:
            has_url_evidence = Evidence.objects.filter(
                submitted_contribution=OuterRef('pk'),
                url__gt=''
            )
            return queryset.filter(
                ~Exists(has_url_evidence) &
                ~Q(notes__icontains='http://') &
                ~Q(notes__icontains='https://')
            )
        return queryset

    def filter_min_accepted_contributions(self, queryset, name, value):
        """Exclude submissions from users with less than N accepted contributions."""
        if value and value > 0:
            # Subquery: count accepted submissions for each user
            accepted_count = SubmittedContribution.objects.filter(
                user=OuterRef('user'),
                state='accepted'
            ).values('user').annotate(count=Count('id')).values('count')
            # Annotate queryset with accepted count and filter
            return queryset.annotate(
                user_accepted_count=Coalesce(Subquery(accepted_count), 0)
            ).filter(user_accepted_count__gte=value)
        return queryset

    def filter_has_proposal(self, queryset, name, value):
        """Filter submissions that have/don't have an active proposal."""
        if value is True:
            return queryset.filter(proposed_action__isnull=False)
        elif value is False:
            return queryset.filter(proposed_action__isnull=True)
        return queryset

    def filter_proposed_action(self, queryset, name, value):
        """Filter by proposed action type (accept, reject, more_info)."""
        if value:
            return queryset.filter(proposed_action=value.lower())
        return queryset

    def filter_proposed_confidence(self, queryset, name, value):
        """Filter by proposal confidence level (high, medium, low)."""
        if value:
            return queryset.filter(proposed_confidence=value.lower())
        return queryset

    def filter_proposed_template(self, queryset, name, value):
        """Filter by proposal template ID."""
        if value:
            return queryset.filter(proposed_template_id=value)
        return queryset

    def filter_mission(self, queryset, name, value):
        """Filter by mission ID, or 'none' for submissions without a mission."""
        if value == 'none' or value == 'null':
            return queryset.filter(mission__isnull=True)
        elif value:
            return queryset.filter(mission_id=value)
        return queryset

    def filter_exclude_mission(self, queryset, name, value):
        """Exclude submissions from a mission ID, or exclude missionless submissions."""
        if value == 'none' or value == 'null':
            return queryset.exclude(mission__isnull=True)
        elif value:
            return queryset.exclude(mission_id=value)
        return queryset

    def filter_resubmitted_more_info(self, queryset, name, value):
        """Filter submissions resubmitted after a steward requested more information."""
        condition = Q(
            state='pending',
            reviewed_at__isnull=False,
            last_edited_at__isnull=False,
            last_edited_at__gt=F('reviewed_at'),
        )
        if value is True:
            return queryset.filter(condition)
        elif value is False:
            return queryset.exclude(condition)
        return queryset

    class Meta:
        model = SubmittedContribution
        fields = ['state', 'contribution_type', 'user']


class StewardDiscordXPFilterSet(FilterSet):
    """Server-side filtering for steward Discord XP tracking."""
    status = CharFilter(method='filter_status')
    contribution_type = NumberFilter(method='filter_contribution_type')
    exclude_contribution_type = NumberFilter(method='filter_exclude_contribution_type')
    username_search = CharFilter(method='filter_username')
    search = CharFilter(method='filter_search')
    include_content = CharFilter(method='filter_include_content')
    exclude_content = CharFilter(method='filter_exclude_content')

    def _normalize_status(self, value):
        status_value = (value or '').strip().lower().replace('-', '_')
        allowed = {
            ContributionDiscordXPState.STATUS_PENDING,
            ContributionDiscordXPState.STATUS_DISTRIBUTED,
            ContributionDiscordXPState.STATUS_NEEDS_REVIEW,
        }
        return status_value if status_value in allowed else None

    def _content_query(self, term):
        has_matching_evidence = Evidence.objects.filter(
            contribution_id=OuterRef('contribution_id')
        ).filter(
            Q(url__icontains=term) | Q(description__icontains=term)
        )
        return (
            Q(contribution__title__icontains=term) |
            Q(contribution__notes__icontains=term) |
            Q(contribution__contribution_type__name__icontains=term) |
            Q(contribution__contribution_type__slug__icontains=term) |
            Q(social_task_completion__task__name__icontains=term) |
            Q(social_task_completion__task__slug__icontains=term) |
            Q(social_task_completion__task__description__icontains=term) |
            Exists(has_matching_evidence)
        )

    def _user_query(self, value):
        query = Q()
        for source in ('contribution__user', 'social_task_completion__user'):
            query |= (
                Q(**{f'{source}__name__icontains': value}) |
                Q(**{f'{source}__address__icontains': value}) |
                Q(**{f'{source}__discord_handle__icontains': value}) |
                Q(**{f'{source}__discordconnection__platform_username__icontains': value}) |
                Q(**{f'{source}__discordconnection__guild_nick__icontains': value})
            )
        return query

    def filter_status(self, queryset, name, value):
        status_value = self._normalize_status(value)
        if status_value:
            return queryset.filter(status=status_value)
        return queryset

    def filter_contribution_type(self, queryset, name, value):
        if value:
            return queryset.filter(contribution__contribution_type_id=value)
        return queryset

    def filter_exclude_contribution_type(self, queryset, name, value):
        if value:
            return queryset.exclude(contribution__contribution_type_id=value)
        return queryset

    def filter_username(self, queryset, name, value):
        if value:
            return queryset.filter(self._user_query(value))
        return queryset

    def filter_search(self, queryset, name, value):
        if value:
            return queryset.filter(self._content_query(value) | self._user_query(value))
        return queryset

    def filter_include_content(self, queryset, name, value):
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    queryset = queryset.filter(self._content_query(term))
        return queryset

    def filter_exclude_content(self, queryset, name, value):
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    queryset = queryset.exclude(self._content_query(term))
        return queryset

    class Meta:
        model = ContributionDiscordXPState
        fields = ['status', 'contribution_type']


class StewardDiscordXPViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Steward endpoint for community Discord XP tracking and awards, covering
    community contributions and community social task completions.
    """
    serializer_class = ContributionDiscordXPStateSerializer
    authentication_classes = [EthereumAuthentication]
    permission_classes = [IsSteward]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StewardDiscordXPFilterSet
    # Detail routes take the numeric state id; non-numeric ids must 404 at the
    # URL level instead of raising during ORM pk coercion.
    lookup_value_regex = '[0-9]+'
    ordering_fields = [
        'entry_created_at',
        'entry_date',
        'target_points',
        'pending_xp',
        'distributed_at',
    ]
    ordering = ['-entry_created_at']

    SELECT_RELATED = (
        'contribution',
        'contribution__user',
        'contribution__user__discordconnection',
        'contribution__contribution_type',
        'contribution__contribution_type__category',
        'social_task_completion',
        'social_task_completion__user',
        'social_task_completion__user__discordconnection',
        'social_task_completion__task',
        'social_task_completion__task__category',
        'distributed_by',
        'last_copied_by',
    )

    def _can_manage_social_task_xp(self):
        permitted_ids = steward_permitted_type_ids(self.request.user, actions=['accept'])
        if not permitted_ids:
            return False
        return ContributionType.objects.filter(
            id__in=permitted_ids,
            category__slug='community',
        ).exists()

    def get_queryset(self):
        queryset = ContributionDiscordXPState.objects.filter(
            Q(contribution__contribution_type__category__slug='community') |
            Q(social_task_completion__task__category__slug='community')
        ).annotate(
            target_points=Coalesce(
                'contribution__frozen_global_points',
                'social_task_completion__points_awarded',
                output_field=IntegerField(),
            ),
            entry_created_at=Coalesce(
                'contribution__created_at',
                'social_task_completion__created_at',
            ),
            entry_date=Coalesce(
                'contribution__contribution_date',
                'social_task_completion__completed_at',
            ),
        ).filter(
            Q(target_points__gt=0) |
            Q(awarded_amount__gt=0)
        ).filter(
            Q(contribution__user__discordconnection__guild_member=True) |
            Q(social_task_completion__user__discordconnection__guild_member=True) |
            Q(awarded_amount__gt=0)
        )

        if self.request.user and self.request.user.is_authenticated and hasattr(self.request.user, 'steward'):
            permitted_ids = steward_permitted_type_ids(self.request.user, actions=['accept'])
            if permitted_ids:
                permitted = Q(contribution__contribution_type_id__in=permitted_ids)
                # Social tasks have no contribution type; any steward who can
                # accept a community contribution type can manage their XP.
                if self._can_manage_social_task_xp():
                    permitted |= Q(social_task_completion__isnull=False)
                queryset = queryset.filter(permitted)
            else:
                queryset = queryset.none()

        latest_events = DiscordXPDistributionEvent.objects.select_related(
            'actor',
        ).order_by('-created_at')

        return queryset.select_related(
            *self.SELECT_RELATED,
        ).prefetch_related(
            Prefetch('events', queryset=latest_events[:1], to_attr='latest_events'),
        ).annotate(
            pending_xp=Greatest(
                F('target_points') - F('awarded_amount'),
                Value(0),
                output_field=IntegerField(),
            )
        )

    def _get_locked_state(self, pk):
        state = self.get_queryset().select_for_update(of=('self',)).get(pk=pk)

        if state.contribution_id:
            permitted = steward_has_permission(
                self.request.user, state.contribution.contribution_type_id, 'accept',
            )
        else:
            permitted = self._can_manage_social_task_xp()
        if not permitted:
            return None, Response(
                {'detail': 'You do not have permission to manage XP for this entry.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if state.contribution_id:
            sync_discord_xp_state_for_contribution(state.contribution)
        state = ContributionDiscordXPState.objects.select_for_update(of=('self',)).select_related(
            *self.SELECT_RELATED,
        ).get(pk=state.pk)
        state.refresh_status_from_contribution(save=True)
        return state, None

    def _record_event(self, state, action, amount):
        return DiscordXPDistributionEvent.objects.create(
            state=state,
            actor=self.request.user,
            amount=max(int(amount or 0), 0),
            action=action,
        )

    def _refresh_discord_connection(self, connection):
        from social_connections.oauth_service import DiscordOAuthService

        try:
            refreshed_connection, _ = DiscordOAuthService().refresh_connection_username(connection)
        except ValueError as e:
            error_code = str(e)
            if error_code == 'account_mismatch':
                return None, Response(
                    {'detail': 'Discord account mismatch. The contributor must reconnect Discord before XP can be copied.'},
                    status=status.HTTP_409_CONFLICT,
                )
            if error_code in (
                'missing_access_token',
                'invalid_access_token',
                'missing_refresh_token',
                'invalid_refresh_token',
                'refresh_not_supported',
                'no_access_token',
            ):
                return None, Response(
                    {'detail': 'Discord authorization is no longer valid. The contributor must reconnect Discord before XP can be copied.'},
                    status=status.HTTP_409_CONFLICT,
                )
            return None, Response(
                {'detail': 'Failed to refresh Discord username before copying XP.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except requests.RequestException:
            return None, Response(
                {'detail': 'Failed to reach Discord while refreshing the contributor username. Please try again.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return refreshed_connection, None

    @action(detail=True, methods=['post'], url_path='record-copy')
    def record_copy(self, request, pk=None):
        try:
            with transaction.atomic():
                state, response = self._get_locked_state(pk)
                if response:
                    return response

                if state.status == ContributionDiscordXPState.STATUS_NEEDS_REVIEW:
                    return Response(
                        {
                            'detail': 'This entry has more XP marked distributed than its current community points.',
                            'state': self.get_serializer(state).data,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                discord_connection = getattr(state.recipient, 'discordconnection', None)
                if not discord_connection:
                    return Response(
                        {'detail': 'This contributor does not have a linked Discord account.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if state.pending_amount <= 0:
                    return Response(
                        {'detail': 'This entry has no pending XP to copy.', 'state': self.get_serializer(state).data},
                        status=status.HTTP_409_CONFLICT,
                    )

                discord_connection, response = self._refresh_discord_connection(discord_connection)
                if response:
                    return response
                state.recipient._state.fields_cache.pop('discordconnection', None)

                now = timezone.now()
                state.last_copied_at = now
                state.last_copied_by = request.user
                state.save(update_fields=[
                    'last_copied_at',
                    'last_copied_by',
                    'updated_at',
                ])
                self._record_event(
                    state,
                    DiscordXPDistributionEvent.ACTION_COPIED,
                    state.pending_amount,
                )
                return Response(self.get_serializer(state).data)
        except ContributionDiscordXPState.DoesNotExist:
            return self._not_found()

    @action(detail=True, methods=['post'], url_path='mark-distributed')
    def mark_distributed(self, request, pk=None):
        try:
            with transaction.atomic():
                state, response = self._get_locked_state(pk)
                if response:
                    return response

                if state.status == ContributionDiscordXPState.STATUS_NEEDS_REVIEW:
                    return Response(
                        {
                            'detail': 'Unset this entry before marking it distributed again.',
                            'state': self.get_serializer(state).data,
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                pending_amount = state.pending_amount
                if pending_amount <= 0:
                    return Response(self.get_serializer(state).data)

                now = timezone.now()
                state.awarded_amount = int(state.awarded_amount or 0) + pending_amount
                state.distributed_at = now
                state.distributed_by = request.user
                state.refresh_status_from_contribution(save=False)
                state.save(update_fields=[
                    'awarded_amount',
                    'distributed_at',
                    'distributed_by',
                    'status',
                    'updated_at',
                ])
                self._record_event(
                    state,
                    DiscordXPDistributionEvent.ACTION_DISTRIBUTED,
                    pending_amount,
                )
                return Response(self.get_serializer(state).data)
        except ContributionDiscordXPState.DoesNotExist:
            return self._not_found()

    @action(detail=True, methods=['post'], url_path='unset-distributed')
    def unset_distributed(self, request, pk=None):
        try:
            with transaction.atomic():
                state, response = self._get_locked_state(pk)
                if response:
                    return response

                previous_amount = int(state.awarded_amount or 0)
                state.awarded_amount = 0
                state.status = ContributionDiscordXPState.STATUS_PENDING
                state.distributed_at = None
                state.distributed_by = None
                state.save(update_fields=[
                    'awarded_amount',
                    'status',
                    'distributed_at',
                    'distributed_by',
                    'updated_at',
                ])
                self._record_event(
                    state,
                    DiscordXPDistributionEvent.ACTION_UNSET,
                    previous_amount,
                )
                return Response(self.get_serializer(state).data)
        except ContributionDiscordXPState.DoesNotExist:
            return self._not_found()

    def _not_found(self):
        return Response(
            {'detail': 'Community Discord XP state not found.'},
            status=status.HTTP_404_NOT_FOUND,
        )


class StewardSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for stewards to review submissions.

    Read-only at the router level: all writes go through the explicit custom
    actions below (review, propose, update-accepted, etc.), each of which
    enforces per-contribution-type steward permissions. The default
    POST/PUT/PATCH/DELETE routes are intentionally not exposed so submissions
    cannot be mutated or deleted outside the audited review flows.
    """
    serializer_class = StewardSubmissionSerializer
    authentication_classes = [EthereumAuthentication]
    permission_classes = [IsSteward]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StewardSubmissionFilterSet
    ordering_fields = [
        'created_at',
        'contribution_date',
        'reviewed_at',
        'converted_contribution__frozen_global_points',
    ]
    ordering = ['-created_at']

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Steward review data, including aggregate stats, requires steward permission.
        """
        return super().get_permissions()

    def _visible_submission_queryset(self, queryset=None):
        # Filter by the steward's permitted contribution types and actions.
        # Proposal-only stewards can inspect pending submissions they can
        # propose on, but cannot browse completed/reworked review history.
        if queryset is None:
            queryset = SubmittedContribution.objects.all()
        if self.request.user and self.request.user.is_authenticated and hasattr(self.request.user, 'steward'):
            review_action_type_ids = steward_permitted_type_ids(
                self.request.user,
                actions=['accept', 'reject', 'request_more_info'],
            )
            propose_type_ids = steward_permitted_type_ids(
                self.request.user,
                actions=['propose'],
            )
            visibility_filter = Q()
            if review_action_type_ids:
                visibility_filter |= Q(contribution_type_id__in=review_action_type_ids)
            if propose_type_ids:
                visibility_filter |= Q(
                    state='pending',
                    contribution_type_id__in=propose_type_ids,
                )
            if visibility_filter:
                queryset = queryset.filter(visibility_filter)
            else:
                queryset = queryset.none()
        else:
            queryset = queryset.none()

        return queryset

    def get_queryset(self):
        """Get submissions for steward review, filtered by steward permissions."""
        queryset = self._visible_submission_queryset()

        notes_count = SubmissionNote.objects.filter(
            submitted_contribution_id=OuterRef('pk')
        ).values('submitted_contribution_id').annotate(
            count=Count('pk')
        ).values('count')

        # Comprehensive prefetch for optimization
        queryset = queryset.select_related(
            'user',
            'user__validator',
            'user__builder',
            'user__githubconnection',
            'user__twitterconnection',
            'user__discordconnection',
            'contribution_type',
            'contribution_type__category',
            'reviewed_by',
            'assigned_to',
            'converted_contribution',
            'converted_contribution__user',
            'converted_contribution__contribution_type',
            'converted_contribution__contribution_type__category',
            'converted_contribution__mission',
            'converted_contribution__project_contribution',
            'mission',
            'project_contribution',
            'proposed_by',
            'proposed_contribution_type',
            'proposed_user',
            'proposed_template',
            'project_milestone_review',
            'project_milestone_review__proposer',
        ).prefetch_related(
            'evidence_items',
            'converted_contribution__highlights',
            'project_contribution__evidence_items',
            'converted_contribution__project_contribution__evidence_items',
        ).annotate(
            internal_notes_count=Coalesce(
                Subquery(notes_count, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            )
        )

        return queryset

    def get_serializer_context(self):
        """
        Add context flags to control serializer behavior.
        Use lightweight serializers for list views to improve performance.
        """
        context = super().get_serializer_context()
        # Use light serializers for list views
        # Use full serializers for detail views (single submission review)
        context['use_light_serializers'] = self.action == 'list'
        return context

    @action(detail=True, methods=['post'], url_path='review')
    @transaction.atomic
    def review(self, request, pk=None):
        """Review and take action on a submission."""
        submission = get_object_or_404(
            self._visible_submission_queryset(
                SubmittedContribution.objects.select_for_update(of=('self',))
            ).select_related(
                'user',
                'contribution_type',
                'contribution_type__category',
                'mission',
            ).prefetch_related('evidence_items'),
            pk=pk,
        )
        self.check_object_permissions(request, submission)

        if submission.state not in ['pending', 'more_info_needed']:
            return Response(
                {'detail': 'Only pending submissions or submissions awaiting more information can be reviewed.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = StewardSubmissionReviewSerializer(
            data=request.data,
            context={'submission': submission, 'request': request},
        )
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data['action']
        final_contribution_type = serializer.validated_data.get(
            'contribution_type',
            submission.contribution_type,
        )

        # Per-action permission checks
        permission_map = {
            'accept': 'accept',
            'reject': 'reject',
            'more_info': 'request_more_info',
        }
        required_permission = permission_map.get(action_name)
        permission_contribution_type_id = (
            final_contribution_type.id
            if action_name == 'accept'
            else submission.contribution_type_id
        )
        if required_permission and not steward_has_permission(request.user, permission_contribution_type_id, required_permission):
            return Response(
                {'detail': f'You do not have permission to {action_name} submissions of this contribution type.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Update submission fields
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()

        if action_name == 'accept':
            # Get the contribution type (use provided or keep original)
            contribution_type = final_contribution_type

            # Get the user for the contribution (use provided or keep original submitter)
            contribution_user = serializer.validated_data.get('user', submission.user)

            project_contribution = serializer.validated_data.get(
                'project_contribution',
                submission.project_contribution,
            )
            milestone_version = submission.milestone_version
            if is_milestone_contribution_type(contribution_type):
                if not project_contribution:
                    return Response(
                        {'detail': 'Milestones must be linked to an accepted project before acceptance.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                project_contribution = Contribution.objects.select_for_update().get(
                    id=project_contribution.id,
                )
                # Validate against the user the contribution will belong to
                # (stewards can reassign it), not the original submitter.
                if not accepted_project_contributions_for_user(contribution_user).filter(
                    id=project_contribution.id,
                ).exists():
                    return Response(
                        {'detail': 'Milestones can only be accepted for a project contribution owned by the selected user.'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if project_contribution != submission.project_contribution:
                    milestone_version = None
                if not milestone_version:
                    milestone_version = next_milestone_version(
                        project_contribution,
                        exclude_submission_id=submission.id,
                    )
                submission.project_contribution = project_contribution
                submission.milestone_version = milestone_version
            else:
                submission.project_contribution = None
                submission.milestone_version = None

            # Update submission contribution type if changed
            if contribution_type != submission.contribution_type:
                submission.contribution_type = contribution_type

            # Create the actual contribution with the selected user
            contribution = Contribution.objects.create(
                user=contribution_user,
                contribution_type=contribution_type,
                points=serializer.validated_data['points'],
                contribution_date=submission.contribution_date,
                notes=submission.notes,
                title=submission.title,
                mission=submission.mission,
                project_contribution=project_contribution if is_milestone_contribution_type(contribution_type) else None,
                milestone_version=milestone_version if is_milestone_contribution_type(contribution_type) else None,
            )

            # Auto-grant builder status if accepting builder contribution for non-builder
            if (contribution_type.category and contribution_type.category.slug == 'builder'
                and not hasattr(contribution_user, 'builder')):
                from leaderboard.models import ensure_builder_status, update_user_leaderboard_entries
                ensure_builder_status(contribution_user, submission.contribution_date)
                # Re-fetch user to avoid stale reverse-relation cache from the hasattr check above
                fresh_user = type(contribution_user).objects.get(pk=contribution_user.pk)
                update_user_leaderboard_entries(fresh_user)

            # Copy evidence items using bulk_create for better performance.
            # Preserve url_type so the allow_duplicate exemption applies to
            # the copied accepted-contribution evidence as well.
            Evidence.objects.bulk_create([
                Evidence(
                    contribution=contribution,
                    description=evidence.description,
                    url=evidence.url,
                    file=evidence.file,
                    url_type=evidence.url_type,
                    normalized_url=normalize_url(evidence.url) if evidence.url else '',
                )
                for evidence in submission.evidence_items.all()
            ])

            # Create highlight if requested
            if serializer.validated_data.get('create_highlight'):
                ContributionHighlight.objects.create(
                    contribution=contribution,
                    title=serializer.validated_data['highlight_title'],
                    description=serializer.validated_data['highlight_description']
                )

            submission.state = 'accepted'
            submission.converted_contribution = contribution
            submission.staff_reply = serializer.validated_data.get('staff_reply', '')

        elif action_name == 'reject':
            submission.state = 'rejected'
            submission.staff_reply = serializer.validated_data['staff_reply']

        elif action_name == 'more_info':
            submission.state = 'more_info_needed'
            submission.staff_reply = serializer.validated_data['staff_reply']

        # Clear all proposal fields after review
        submission.proposed_action = None
        submission.proposed_points = None
        submission.proposed_contribution_type = None
        submission.proposed_user = None
        submission.proposed_staff_reply = ''
        submission.proposed_create_highlight = False
        submission.proposed_highlight_title = ''
        submission.proposed_highlight_description = ''
        submission.proposed_by = None
        submission.proposed_at = None
        submission.proposed_confidence = None
        submission.proposed_template = None

        submission.save()

        requires_project_rubric = uses_project_rubric(
            final_contribution_type if action_name == 'accept' else submission.contribution_type
        )
        rubric_review = serializer.validated_data.get('rubric_review')
        rubric_record = None
        if rubric_review and requires_project_rubric:
            rubric_record, _ = ProjectMilestoneReview.objects.update_or_create(
                submitted_contribution=submission,
                defaults={
                    'proposer': request.user,
                    'review_flow': (
                        final_contribution_type
                        if action_name == 'accept'
                        else submission.contribution_type
                    ).review_flow,
                    'action': action_name,
                    'confidence': None,
                    'gate_failures': rubric_review['gate_failures'],
                    'sections': rubric_review['sections'],
                    'extras': rubric_review['extras'],
                    'overall_reason': rubric_review['overall_reason'],
                },
            )
        else:
            ProjectMilestoneReview.objects.filter(submitted_contribution=submission).delete()

        # Create CRM note recording the final decision
        from .models import SubmissionNote
        reviewer_name = request.user.name or request.user.address[:10] + '...'
        pts_str = f" with **{serializer.validated_data.get('points', '')} points**" if action_name == 'accept' else ''
        reply_text = serializer.validated_data.get('staff_reply', '') or ''
        reply_str = f"\n\n> {reply_text}" if reply_text and action_name in ('reject', 'more_info') else ''
        rubric_str = f"\n\n{rubric_summary_text(rubric_review)}" if rubric_review else ''
        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=request.user,
            message=f"Reviewed: **{action_name}**{pts_str} by {reviewer_name}{reply_str}{rubric_str}",
            is_proposal=False,
            data={
                'action': action_name,
                'points': serializer.validated_data.get('points'),
                'staff_reply': reply_text,
                'template_id': serializer.validated_data['template_id'].id if serializer.validated_data.get('template_id') else None,
                'rubric_review_id': rubric_record.id if rubric_record else None,
            },
        )

        # Notify the submitter about the decision
        from notifications.services import notify_submission_review
        notify_submission_review(submission, actor=request.user)

        return Response(
            self.get_serializer(submission).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='update-accepted')
    @transaction.atomic
    def update_accepted(self, request, pk=None):
        """Correct points or add/update/remove a highlight for an accepted submission."""
        submission = self.get_object()
        contribution = submission.converted_contribution

        if submission.state != 'accepted' or not contribution:
            return Response(
                {'detail': 'Only accepted submissions with a created contribution can be updated.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not steward_has_permission(request.user, submission.contribution_type_id, 'accept'):
            return Response(
                {'detail': 'You do not have permission to update accepted submissions of this contribution type.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = StewardAcceptedSubmissionUpdateSerializer(
            data=request.data,
            context={'contribution_type': contribution.contribution_type}
        )
        serializer.is_valid(raise_exception=True)

        points = serializer.validated_data['points']
        contribution.points = points
        multiplier = float(contribution.multiplier_at_creation or 1)
        contribution.frozen_global_points = round(points * multiplier)
        contribution.save(update_fields=['points', 'frozen_global_points', 'updated_at'])

        if serializer.validated_data.get('create_highlight'):
            highlight = ContributionHighlight.objects.filter(contribution=contribution).first()
            if highlight:
                highlight.title = serializer.validated_data['highlight_title']
                highlight.description = serializer.validated_data['highlight_description']
                highlight.save(update_fields=['title', 'description', 'updated_at'])
            else:
                ContributionHighlight.objects.create(
                    contribution=contribution,
                    title=serializer.validated_data['highlight_title'],
                    description=serializer.validated_data['highlight_description']
                )
        elif serializer.validated_data.get('remove_highlight'):
            ContributionHighlight.objects.filter(contribution=contribution).delete()

        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=request.user,
            message=f"Updated accepted contribution: **{points} points**",
            is_proposal=False,
            data={
                'action': 'update_accepted',
                'points': points,
                'create_highlight': serializer.validated_data.get('create_highlight', False),
                'remove_highlight': serializer.validated_data.get('remove_highlight', False),
            },
        )

        from notifications.services import notify_submission_review
        notify_submission_review(submission, actor=request.user)

        return Response(
            self.get_serializer(submission).data,
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Get statistics for steward dashboard."""
        visible_qs = self._visible_submission_queryset()
        total_pending = visible_qs.filter(state='pending').count()

        reviewed_qs = visible_qs.filter(reviewed_by=request.user).exclude(state='canceled')
        total_reviewed = reviewed_qs.count()

        # Get last review time
        last_review = reviewed_qs.order_by('-reviewed_at').first()

        last_review_time = last_review.reviewed_at if last_review else None

        # Get acceptance rate
        user_reviews = reviewed_qs.exclude(state='pending')

        total_decisions = user_reviews.count()
        accepted = user_reviews.filter(state='accepted').count()
        total_rejected = user_reviews.filter(state='rejected').count()
        total_info_requested = user_reviews.filter(state='more_info_needed').count()
        acceptance_rate = (accepted / total_decisions * 100) if total_decisions > 0 else 0
        
        return Response({
            'pending_count': total_pending,
            'total_reviewed': total_reviewed,
            'last_review': last_review_time,
            'acceptance_rate': round(acceptance_rate, 1),
            'total_accepted': accepted,
            'total_rejected': total_rejected,
            'total_info_requested': total_info_requested
        })

    @action(detail=False, methods=['get'], url_path='daily-metrics')
    def daily_metrics(self, request):
        """
        Get time-series metrics for submissions.

        Query parameters:
        - start_date: Start date (YYYY-MM-DD), defaults to first submission date
        - end_date: End date (YYYY-MM-DD), defaults to today
        - group_by: Grouping period - 'day', 'week', or 'month' (default: 'week')
        - category: Filter by category slug (validator, builder, steward, creator)
        - contribution_type: Filter by contribution type ID

        Returns counts grouped by period for:
        - ingress: New submissions created
        - accepted: Submissions accepted
        - rejected: Submissions rejected
        - more_info_requested: Submissions requesting more info
        - points_awarded: Total points from accepted contributions, excluding
          onboarding and social-linking awards

        The `totals` block also includes `pending_review`: submissions created
        in the date range that are still in the pending state, respecting the
        category and contribution_type filters.
        """
        from datetime import datetime, timedelta
        from django.db.models import Min, Max
        # Build base queryset with steward visibility and optional filters first
        # (needed for date detection).
        base_qs = self._visible_submission_queryset()

        category = request.query_params.get('category')
        if category:
            base_qs = base_qs.filter(contribution_type__category__slug=category)

        contribution_type_id = request.query_params.get('contribution_type')
        if contribution_type_id:
            base_qs = base_qs.filter(contribution_type_id=contribution_type_id)

        # Get grouping parameter (default to week)
        group_by = request.query_params.get('group_by', 'week')
        if group_by not in ['day', 'week', 'month']:
            group_by = 'week'

        # Select truncation function based on grouping
        trunc_func = {
            'day': TruncDate,
            'week': TruncWeek,
            'month': TruncMonth
        }[group_by]

        # Parse date range from query params, or auto-detect from data
        end_date = None
        start_date = None

        if request.query_params.get('start_date'):
            try:
                start_date = datetime.strptime(
                    request.query_params['start_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass

        if request.query_params.get('end_date'):
            try:
                end_date = datetime.strptime(
                    request.query_params['end_date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                pass

        # Auto-detect date range from data if not provided
        if start_date is None or end_date is None:
            date_range = base_qs.aggregate(
                min_date=Min('created_at'),
                max_date=Max('created_at')
            )
            if start_date is None:
                start_date = date_range['min_date'].date() if date_range['min_date'] else timezone.now().date()
            if end_date is None:
                end_date = timezone.now().date()

        # Get ingress (new submissions by created_at)
        ingress = (
            base_qs
            .filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            .annotate(period=trunc_func('created_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        # Get reviews by outcome (by reviewed_at date)
        reviews_base = base_qs.filter(
            reviewed_at__date__gte=start_date,
            reviewed_at__date__lte=end_date
        )

        accepted = (
            reviews_base
            .filter(state='accepted')
            .annotate(period=trunc_func('reviewed_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        rejected = (
            reviews_base
            .filter(state='rejected')
            .annotate(period=trunc_func('reviewed_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        more_info = (
            reviews_base
            .filter(state='more_info_needed')
            .annotate(period=trunc_func('reviewed_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        canceled = (
            reviews_base
            .filter(state='canceled')
            .annotate(period=trunc_func('reviewed_at'))
            .values('period')
            .annotate(count=Count('id'))
            .order_by('period')
        )

        # Get points awarded (from converted contributions)
        points_qs = Contribution.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            source_submission__in=base_qs,
        ).exclude(
            contribution_type__slug__in=METRICS_POINTS_EXCLUDED_TYPE_SLUGS
        )

        # Apply category/type filters to points query if specified
        if category:
            points_qs = points_qs.filter(contribution_type__category__slug=category)
        if contribution_type_id:
            points_qs = points_qs.filter(contribution_type_id=contribution_type_id)

        points = (
            points_qs
            .annotate(period=trunc_func('created_at'))
            .values('period')
            .annotate(total_points=Sum('frozen_global_points'))
            .order_by('period')
        )

        # Convert querysets to dict for easier lookup (handle both date and datetime)
        def to_date(val):
            if hasattr(val, 'date'):
                return val.date()
            return val

        ingress_dict = {to_date(item['period']): item['count'] for item in ingress}
        accepted_dict = {to_date(item['period']): item['count'] for item in accepted}
        rejected_dict = {to_date(item['period']): item['count'] for item in rejected}
        more_info_dict = {to_date(item['period']): item['count'] for item in more_info}
        canceled_dict = {to_date(item['period']): item['count'] for item in canceled}
        points_dict = {to_date(item['period']): item['total_points'] for item in points}

        # Build response with all periods in range
        data = []
        current_date = start_date

        # Align to period start
        if group_by == 'week':
            # Align to Monday
            current_date = current_date - timedelta(days=current_date.weekday())
        elif group_by == 'month':
            # Align to first of month
            current_date = current_date.replace(day=1)

        while current_date <= end_date:
            data.append({
                'period': current_date.isoformat(),
                'ingress': ingress_dict.get(current_date, 0),
                'accepted': accepted_dict.get(current_date, 0),
                'rejected': rejected_dict.get(current_date, 0),
                'more_info_requested': more_info_dict.get(current_date, 0),
                'canceled': canceled_dict.get(current_date, 0),
                'points_awarded': points_dict.get(current_date, 0) or 0
            })

            # Advance to next period
            if group_by == 'day':
                current_date += timedelta(days=1)
            elif group_by == 'week':
                current_date += timedelta(weeks=1)
            else:  # month
                # Add one month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)

        # Pending review counts submissions created in the range that are still
        # in pending state. We can't derive it from `ingress - reviewed` because
        # ingress is bucketed by created_at while review outcomes are bucketed
        # by reviewed_at, so the two measure disjoint cohorts and the
        # subtraction produces nonsense (often clamped to 0) under filters.
        pending_review = base_qs.filter(
            state='pending',
            created_at__date__gte=start_date,
            created_at__date__lte=end_date
        ).count()

        # Calculate totals for the period
        totals = {
            'ingress': sum(d['ingress'] for d in data),
            'accepted': sum(d['accepted'] for d in data),
            'rejected': sum(d['rejected'] for d in data),
            'more_info_requested': sum(d['more_info_requested'] for d in data),
            'canceled': sum(d['canceled'] for d in data),
            'points_awarded': sum(d['points_awarded'] for d in data),
            'pending_review': pending_review
        }

        return Response({
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'group_by': group_by,
            'totals': totals,
            'data': data
        })

    @action(detail=False, methods=['get'], url_path='users')
    def users(self, request):
        """Get all users sorted alphabetically by name for steward dropdown."""
        from users.models import User
        
        users = User.objects.all().order_by('name', 'address')
        
        # Create simplified user data for the dropdown
        user_data = []
        for user in users:
            display_name = user.name if user.name else f"{user.address[:6]}...{user.address[-4:]}"
            user_data.append({
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'display_name': display_name
            })
        
        return Response(user_data)

    @action(detail=False, methods=['get'], url_path='accepted-projects')
    def accepted_projects(self, request):
        """Get accepted Projects contributions for a user during steward review."""
        from users.models import User

        user_id = request.query_params.get('user')
        submission_id = request.query_params.get('submission')
        if not user_id:
            return Response(
                {'detail': 'A user query parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        submission = None
        if submission_id:
            submission = get_object_or_404(
                self._visible_submission_queryset(),
                pk=submission_id,
            )

        try:
            user = User.objects.get(pk=user_id)
        except (TypeError, ValueError, User.DoesNotExist):
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        project_contributions = (
            accepted_project_contributions_for_user(user)
            .prefetch_related('evidence_items')
            .order_by('-created_at')
        )
        data = [
            {
                'id': contribution.id,
                'title': project_contribution_display_title(contribution),
                'created_at': contribution.created_at,
                'github_url': project_contribution_github_url(contribution),
                'next_milestone_version': next_milestone_version(
                    contribution,
                    exclude_submission_id=submission.id if submission else None,
                ),
            }
            for contribution in project_contributions
        ]
        return Response(data)

    def _check_type_permission(self, request, submission):
        """
        Require the steward to hold at least one permission (review or propose)
        on the submission's contribution type. Returns a 403 response when the
        check fails, or None when the steward is permitted.
        """
        permitted_type_ids = steward_permitted_type_ids(
            request.user,
            actions=['accept', 'reject', 'request_more_info', 'propose'],
        )
        if submission.contribution_type_id not in permitted_type_ids:
            return Response(
                {'detail': 'You do not have permission to manage submissions of this contribution type.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return None

    @action(detail=True, methods=['post'], permission_classes=[IsSteward])
    def assign(self, request, pk=None):
        """Assign submission to a steward."""
        from users.models import User

        submission = self.get_object()
        permission_response = self._check_type_permission(request, submission)
        if permission_response is not None:
            return permission_response
        steward_id = request.data.get('steward_id')

        if steward_id is None:
            # Unassign
            submission.assigned_to = None
            submission.save()
            return Response({'status': 'unassigned'})

        # Validate steward exists and has steward profile
        try:
            steward_user = User.objects.get(id=steward_id)
            if not hasattr(steward_user, 'steward'):
                return Response(
                    {'error': 'User is not a steward'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except User.DoesNotExist:
            return Response(
                {'error': 'Steward not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        submission.assigned_to = steward_user
        submission.save()

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='toggle-interesting', permission_classes=[IsSteward])
    def toggle_interesting(self, request, pk=None):
        """Toggle (or set) the internal `is_interesting` flag on a submission."""
        submission = self.get_object()
        permission_response = self._check_type_permission(request, submission)
        if permission_response is not None:
            return permission_response

        if 'is_interesting' in request.data:
            field = serializers.BooleanField()
            try:
                submission.is_interesting = field.run_validation(request.data.get('is_interesting'))
            except serializers.ValidationError as exc:
                return Response(
                    {'is_interesting': exc.detail},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            submission.is_interesting = not submission.is_interesting

        submission.save(update_fields=['is_interesting', 'updated_at'])

        serializer = self.get_serializer(submission)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='bulk-reject')
    def bulk_reject(self, request):
        """Bulk reject multiple submissions with a single rejection message."""
        submission_ids = request.data.get('submission_ids', [])
        staff_reply = request.data.get('staff_reply', '')

        if not submission_ids:
            return Response(
                {'error': 'No submission IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not staff_reply:
            return Response(
                {'error': 'Rejection reason is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        submissions = SubmittedContribution.objects.filter(
            id__in=submission_ids,
            state__in=['pending', 'more_info_needed']
        )

        # Filter by steward's reject permission on each submission's contribution type
        permitted_reject_ids = steward_permitted_type_ids(request.user, actions=['reject'])
        permitted = submissions.filter(contribution_type_id__in=permitted_reject_ids)
        skipped_count = submissions.count() - permitted.count()

        rejected_ids = list(permitted.values_list('id', flat=True))
        rejected_count = len(rejected_ids)
        if rejected_count == 0:
            return Response(
                {'error': 'No valid submissions found to reject (you may lack reject permission on these types)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        permitted.update(
            state='rejected',
            staff_reply=staff_reply,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )

        from notifications.services import notify_submission_review
        reviewed_submissions = SubmittedContribution.objects.filter(
            id__in=rejected_ids
        ).select_related('user', 'contribution_type', 'reviewed_by')
        for submission in reviewed_submissions:
            notify_submission_review(submission, actor=request.user)

        return Response({
            'status': 'success',
            'rejected_count': rejected_count,
            'skipped_count': skipped_count,
            'rejected_ids': rejected_ids,
        })

    @action(detail=False, methods=['get'], url_path='my-permissions')
    def my_permissions(self, request):
        """Get current steward's permissions map: { contribution_type_id: [actions] }."""
        from stewards.models import StewardPermission
        if not hasattr(request.user, 'steward'):
            return Response({})

        perms = StewardPermission.objects.filter(
            steward=request.user.steward
        ).values_list('contribution_type_id', 'action')

        result = {}
        for ct_id, action_name in perms:
            result.setdefault(str(ct_id), []).append(action_name)

        return Response(result)

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """Get all review templates, optionally filtered by action."""
        from stewards.models import ReviewTemplate
        templates = ReviewTemplate.objects.all()
        action_filter = request.query_params.get('action')
        if action_filter in ('accept', 'reject', 'more_info'):
            templates = templates.filter(action=action_filter)
        data = [{'id': t.id, 'label': t.label, 'text': t.text, 'action': t.action} for t in templates]
        return Response(data)

    @action(detail=True, methods=['post'], url_path='propose')
    def propose(self, request, pk=None):
        """Submit a proposal for a submission."""
        submission = self.get_object()

        # Check propose permission
        if not steward_has_permission(request.user, submission.contribution_type_id, 'propose'):
            return Response(
                {'detail': 'You do not have permission to propose on submissions of this contribution type.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SubmissionProposeSerializer(
            data=request.data,
            context={'submission': submission},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        effective_contribution_type = (
            data.get('proposed_contribution_type')
            or submission.contribution_type
        )
        requires_project_rubric = uses_project_rubric(effective_contribution_type)

        # Set proposed_* fields on the submission
        submission.proposed_action = data['proposed_action']
        submission.proposed_points = data.get('proposed_points')
        submission.proposed_contribution_type = data.get('proposed_contribution_type')
        submission.proposed_user = data.get('proposed_user')
        submission.proposed_staff_reply = data.get('proposed_staff_reply', '')
        submission.proposed_create_highlight = data.get('proposed_create_highlight', False)
        submission.proposed_highlight_title = data.get('proposed_highlight_title', '')
        submission.proposed_highlight_description = data.get('proposed_highlight_description', '')
        submission.proposed_by = request.user
        submission.proposed_at = timezone.now()
        submission.proposed_confidence = data.get('confidence')

        # Resolve template FK (PrimaryKeyRelatedField returns instance or None)
        template = data.get('template_id')
        submission.proposed_template = template

        submission.save()

        rubric_review = data.get('rubric_review')
        rubric_record = None
        if rubric_review and requires_project_rubric:
            rubric_record, _ = ProjectMilestoneReview.objects.update_or_create(
                submitted_contribution=submission,
                defaults={
                    'proposer': request.user,
                    'review_flow': effective_contribution_type.review_flow,
                    'action': data['proposed_action'],
                    'confidence': data.get('confidence'),
                    'gate_failures': rubric_review['gate_failures'],
                    'sections': rubric_review['sections'],
                    'extras': rubric_review['extras'],
                    'overall_reason': rubric_review['overall_reason'],
                },
            )
        elif not requires_project_rubric:
            ProjectMilestoneReview.objects.filter(submitted_contribution=submission).delete()

        # Create CRM note recording the proposal
        from .models import SubmissionNote
        proposer_name = request.user.name or request.user.address[:10] + '...'
        action_str = data['proposed_action']
        proposed_points = data.get('proposed_points')
        pts_str = f" with **{proposed_points} points**" if action_str == 'accept' and proposed_points is not None else ''
        ct_name = data.get('proposed_contribution_type')
        ct_str = f" ({ct_name.name})" if ct_name else ''
        user_obj = data.get('proposed_user')
        user_str = f", assigned to {user_obj.name or user_obj.address[:10]}" if user_obj else ''
        reply_str = f". Reply: '{data.get('proposed_staff_reply', '')[:100]}'" if data.get('proposed_staff_reply') else ''
        rubric_str = ''
        if rubric_review:
            rubric_str = f"\n\n{rubric_summary_text(rubric_review)}"

        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=request.user,
            message=f"Proposed: **{action_str}**{pts_str}{ct_str}{user_str}{reply_str} by {proposer_name}{rubric_str}",
            is_proposal=True,
            data={
                'action': data['proposed_action'],
                'points': data.get('proposed_points'),
                'staff_reply': data.get('proposed_staff_reply', ''),
                'template_id': template.id if template else None,
                'confidence': data.get('confidence'),
                'rubric_review_id': rubric_record.id if rubric_record else None,
            },
        )

        return Response(
            self.get_serializer(submission).data,
            status=status.HTTP_200_OK
        )

    def _validate_proposal_note_update(self, request, submission, note):
        if not note.is_proposal:
            return Response(
                {'detail': 'Only generated proposal notes can be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if submission.state != 'pending' or not submission.proposed_action:
            return Response(
                {'detail': 'Proposal notes can only be edited while the proposal is pending.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if note.user_id != request.user.id or submission.proposed_by_id != request.user.id:
            return Response(
                {'detail': 'You can only edit your own active proposal note.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not steward_has_permission(request.user, submission.contribution_type_id, 'propose'):
            return Response(
                {'detail': 'You do not have permission to edit proposal notes for this contribution type.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        latest_proposal_note = (
            submission.internal_notes
            .filter(is_proposal=True)
            .order_by('-created_at', '-id')
            .first()
        )
        if not latest_proposal_note or latest_proposal_note.id != note.id:
            return Response(
                {'detail': 'Only the active generated proposal note can be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    @action(detail=True, methods=['get', 'post'], url_path='notes')
    def notes(self, request, pk=None):
        """List or create CRM notes on a submission."""
        submission = self.get_object()
        permission_response = self._check_type_permission(request, submission)
        if permission_response is not None:
            return permission_response

        if request.method == 'GET':
            notes = submission.internal_notes.select_related('user').all()
            serializer = SubmissionNoteSerializer(notes, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            message = request.data.get('message', '').strip()
            if not message:
                return Response(
                    {'error': 'Message is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from .models import SubmissionNote
            note = SubmissionNote.objects.create(
                submitted_contribution=submission,
                user=request.user,
                message=message,
                is_proposal=False,
            )
            return Response(
                SubmissionNoteSerializer(note).data,
                status=status.HTTP_201_CREATED
            )

    @action(detail=True, methods=['patch'], url_path=r'notes/(?P<note_id>[^/.]+)')
    def update_note(self, request, pk=None, note_id=None):
        """Edit the active generated proposal note for a pending proposal."""
        submission = self.get_object()
        note = get_object_or_404(
            SubmissionNote,
            pk=note_id,
            submitted_contribution=submission,
        )

        validation_response = self._validate_proposal_note_update(request, submission, note)
        if validation_response is not None:
            return validation_response

        message = request.data.get('message', '').strip()
        if not message:
            return Response(
                {'error': 'Message is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        note.message = message
        note.save(update_fields=['message', 'updated_at'])
        return Response(SubmissionNoteSerializer(note).data)

    @action(detail=False, methods=['get'], url_path='ban-appeals',
            permission_classes=[permissions.IsAdminUser])
    def ban_appeals(self, request):
        """List ban appeals, optionally filtered by status. Staff only."""
        from users.models import BanAppeal
        from users.serializers import BanAppealSerializer

        status_filter = request.query_params.get('status')
        qs = BanAppeal.objects.select_related(
            'user', 'reviewed_by',
        ).order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)

        serializer = BanAppealSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'],
            url_path='ban-appeals/(?P<appeal_id>[^/.]+)/review',
            permission_classes=[permissions.IsAdminUser])
    def review_ban_appeal(self, request, appeal_id=None):
        """Approve or deny a ban appeal. Staff only: approving unbans the user,
        which is account-level moderation power beyond steward review scope."""
        from users.models import BanAppeal
        from users.serializers import BanAppealReviewSerializer, BanAppealSerializer

        appeal = get_object_or_404(BanAppeal, id=appeal_id)

        if appeal.status != 'pending':
            return Response(
                {'error': f'Appeal has already been {appeal.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = BanAppealReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_taken = serializer.validated_data['action']
        review_notes = serializer.validated_data.get('review_notes', '')

        appeal.reviewed_by = request.user
        appeal.reviewed_at = timezone.now()
        appeal.review_notes = review_notes

        if action_taken == 'approve':
            appeal.status = 'approved'
            appeal.save()
            # Unban the user
            user = appeal.user
            user.is_banned = False
            user.ban_reason = ''
            user.banned_at = None
            user.banned_by = None
            user.save()
        else:
            appeal.status = 'denied'
            appeal.save()

        return Response(BanAppealSerializer(appeal).data)


class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving missions.
    Only missions are returned by default.
    """
    serializer_class = MissionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Return active missions by default.
        Supports filtering by contribution_type and category.
        """
        active_submissions = SubmittedContribution.objects.exclude(
            state__in=['rejected', 'canceled']
        )
        mission_submission_count = active_submissions.filter(
            mission_id=OuterRef('pk')
        ).values('mission_id').annotate(
            count=Count('pk')
        ).values('count')
        contribution_type_submission_count = active_submissions.filter(
            contribution_type_id=OuterRef('contribution_type_id')
        ).values('contribution_type_id').annotate(
            count=Count('pk')
        ).values('count')
        multiplier_field = DecimalField(max_digits=10, decimal_places=2)
        current_multiplier = GlobalLeaderboardMultiplier.objects.filter(
            contribution_type_id=OuterRef('contribution_type_id')
        ).order_by('-valid_from').values('multiplier_value')[:1]

        annotations = {
            'submission_count': Coalesce(
                Subquery(mission_submission_count, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            ),
            'contribution_type_submission_count': Coalesce(
                Subquery(
                    contribution_type_submission_count,
                    output_field=IntegerField(),
                ),
                Value(0),
                output_field=IntegerField(),
            ),
            'contribution_type_current_multiplier_value': Coalesce(
                Subquery(current_multiplier, output_field=multiplier_field),
                Value(1.0, output_field=multiplier_field),
                output_field=multiplier_field,
            ),
            'contributions_count': Count('contributions', distinct=True),
            'unique_users': Count('contributions__user', distinct=True),
            'points_earned': Coalesce(
                Sum('contributions__frozen_global_points'),
                Value(0),
                output_field=IntegerField(),
            ),
        }

        user = getattr(self.request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            user_submission_count = active_submissions.filter(
                mission_id=OuterRef('pk'),
                user_id=user.id,
            ).values('mission_id').annotate(
                count=Count('pk')
            ).values('count')
            annotations['user_submission_count'] = Coalesce(
                Subquery(user_submission_count, output_field=IntegerField()),
                Value(0),
                output_field=IntegerField(),
            )

        queryset = Mission.objects.all().select_related(
            'contribution_type',
            'contribution_type__category',
        ).annotate(**annotations).order_by('-created_at', '-id')

        include_inactive = (
            self.request.query_params.get('include_inactive', '').lower()
            in ['1', 'true', 'yes']
        )
        is_active = self.request.query_params.get('is_active')

        # Detail lookups must be able to resolve expired missions so historical
        # submissions/contributions can keep their mission identity.
        if self.action != 'retrieve':
            active_q = self._active_mission_q()
            if is_active is not None:
                if is_active.lower() in ['1', 'true', 'yes']:
                    queryset = queryset.filter(active_q)
                elif is_active.lower() in ['0', 'false', 'no']:
                    queryset = queryset.exclude(active_q)
            elif not include_inactive:
                queryset = queryset.filter(active_q)

        # Unstarted missions are unannounced content: public callers may see
        # expired missions (needed for historical filters and detail pages),
        # but only stewards/staff can see missions that have not started yet.
        # This applies to every action, including retrieve.
        if not self._is_privileged_user():
            queryset = queryset.exclude(start_date__gt=timezone.now())

        # Filter by contribution type if specified
        contribution_type = self.request.query_params.get('contribution_type', None)
        if contribution_type:
            queryset = queryset.filter(contribution_type_id=contribution_type)

        # Filter by category if specified
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(contribution_type__category__slug=category)

        return queryset

    def _is_privileged_user(self):
        """Stewards and staff may see unstarted (unannounced) missions."""
        user = self.request.user
        return user.is_authenticated and (user.is_staff or hasattr(user, 'steward'))

    @staticmethod
    def _active_mission_q():
        from django.utils import timezone
        from django.db import models

        now = timezone.now()
        return (
            (models.Q(start_date__isnull=True) | models.Q(start_date__lte=now))
            & (models.Q(end_date__isnull=True) | models.Q(end_date__gt=now))
        )

    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def stats(self, request, pk=None):
        # Stats must remain available for expired missions; get_queryset()
        # intentionally filters them out for list views. Unstarted missions,
        # however, stay hidden from non-steward/non-staff callers.
        mission_qs = Mission.objects.all()
        if not self._is_privileged_user():
            mission_qs = mission_qs.exclude(start_date__gt=timezone.now())
        mission = get_object_or_404(mission_qs, pk=pk)
        stats = Contribution.objects.filter(mission=mission).aggregate(
            unique_users=Count('user', distinct=True),
            contributions_count=Count('id'),
            points_earned=Coalesce(Sum('frozen_global_points'), 0),
        )
        return Response({
            'unique_users': stats['unique_users'] or 0,
            'contributions_count': stats['contributions_count'] or 0,
            'points_earned': stats['points_earned'] or 0,
        })


class StartupRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet for startup requests.
    Management is done through Django admin.
    """
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Return active startup requests ordered by display order.
        """
        return StartupRequest.get_active_requests()

    def get_serializer_class(self):
        """
        Use appropriate serializer based on action.
        """
        if self.action == 'retrieve':
            return StartupRequestDetailSerializer
        return StartupRequestListSerializer


class FeaturedContentViewSet(viewsets.ReadOnlyModelViewSet):
    """Featured content for the portal home page."""
    serializer_class = FeaturedContentSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        placement = request.query_params.get('placement')

        if placement:
            valid_placements = {choice[0] for choice in FeaturedContent.HERO_PLACEMENT_CHOICES}
            if placement not in valid_placements - {FeaturedContent.HERO_PLACEMENT_ALL}:
                return Response(
                    {'detail': f"Invalid placement '{placement}'."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = [
                item for item in queryset
                if item.shows_in_placement(placement)
            ]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        include_inactive = (
            self.request.query_params.get('include_inactive', '').lower()
            in ('1', 'true', 'yes')
        )
        queryset = FeaturedContent.objects.select_related(
            'user', 'contribution', 'contribution__contribution_type'
        ).order_by('order', '-created_at')
        if not include_inactive:
            queryset = queryset.filter(status='active')
        content_type = self.request.query_params.get('type')
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        return queryset


class AlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Public endpoint for active system alerts."""
    serializer_class = AlertSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        return Alert.get_active_alerts()
