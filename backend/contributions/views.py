from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import FilterSet, CharFilter, BooleanFilter
from django.utils import timezone
from django.db.models import Count, Max, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from .models import ContributionType, Contribution, Evidence, SubmittedContribution, ContributionHighlight, Mission
from .serializers import (ContributionTypeSerializer, ContributionSerializer,
                         EvidenceSerializer, SubmittedContributionSerializer,
                         SubmittedEvidenceSerializer, ContributionHighlightSerializer,
                         StewardSubmissionSerializer, StewardSubmissionReviewSerializer,
                         MissionSerializer)
from .forms import SubmissionReviewForm
from .permissions import IsSteward
from leaderboard.models import GlobalLeaderboardMultiplier
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from ethereum_auth.authentication import EthereumAuthentication


class ContributionTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows contribution types to be viewed.
    """
    queryset = ContributionType.objects.all()
    serializer_class = ContributionTypeSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    
    def get_queryset(self):
        queryset = ContributionType.objects.all()

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

        return queryset
        
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
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
        from django.db.models import Sum
        
        # Start with all contribution types
        queryset = ContributionType.objects.all()

        # Filter by category if provided
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
            # Exclude Builder Welcome when filtering for builder category
            if category == 'builder':
                queryset = queryset.exclude(slug='builder-welcome')
        
        types_with_stats = queryset.annotate(
            count=Count('contributions'),
            participants_count=Count('contributions__user', distinct=True),
            last_earned=Coalesce(Max('contributions__contribution_date'), timezone.now()),
            total_points_given=Coalesce(Sum('contributions__frozen_global_points'), 0)
        ).values('id', 'name', 'description', 'min_points', 'max_points', 'count', 'participants_count', 'last_earned', 'total_points_given', 'is_submittable')
        
        # Add current multiplier for each type
        result = []
        for type_data in types_with_stats:
            try:
                contribution_type = ContributionType.objects.get(id=type_data['id'])
                multiplier_value = GlobalLeaderboardMultiplier.get_current_multiplier_value(contribution_type)
                type_data['current_multiplier'] = multiplier_value
            except Exception:
                type_data['current_multiplier'] = 1.0
            
            result.append(type_data)
            
        return Response(result)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
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
            contribution_type=contribution_type,
            state='accepted'
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
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
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
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
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
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['user', 'contribution_type', 'mission']
    search_fields = ['notes', 'user__email', 'user__name', 'contribution_type__name']
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
            'mission'  # Avoid N+1 queries when accessing mission details
        ).prefetch_related(
            'evidence_items',  # Only queried in detail view (light serializers skip this)
            'highlights'       # Only queried in detail view (light serializers skip this)
        )

        # Filter by user address if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(user__address__iexact=user_address)

        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(contribution_type__category__slug=category)

        # Exclude onboarding contributions (builder-welcome and validator-waitlist)
        # EXCEPT when viewing a specific user's profile (user_address is present)
        if not user_address:
            queryset = queryset.exclude(
                contribution_type__slug__in=['builder-welcome', 'validator-waitlist']
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
    
    def list(self, request, *args, **kwargs):
        """
        Override list to optionally group consecutive contributions of the same type.
        """
        # Check if grouping is requested
        group_consecutive = request.query_params.get('group_consecutive', 'false').lower() == 'true'

        if not group_consecutive:
            # Default behavior - no grouping
            return super().list(request, *args, **kwargs)
        
        # Get the queryset and apply pagination before grouping
        queryset = self.filter_queryset(self.get_queryset())
        
        # Get the total count of actual contributions (not groups)
        total_contributions_count = queryset.count()
        
        # Get pagination parameters
        page_size = int(request.query_params.get('page_size') or request.query_params.get('limit', 10))
        page_number = int(request.query_params.get('page', 1))

        # For grouped pagination, we use limit/offset on the RAW contributions
        # then group them, then slice the result
        # This is simpler but less efficient - acceptable for reasonable dataset sizes
        limit_for_fetch = min(page_size * page_number * 5, 500)  # Fetch enough to cover requested page

        all_contributions = list(queryset[:limit_for_fetch])
        
        # Group consecutive contributions
        grouped = []
        current_group = None
        total_grouped_count = 0
        
        for contrib in all_contributions:
            serialized = ContributionSerializer(contrib).data
            type_id = contrib.contribution_type.id
            has_evidence = bool(serialized.get('evidence_url'))

            # Check if we should add to current group or start new one
            # Only group if same type and NO evidence
            if (current_group and
                current_group['contribution_type']['id'] == type_id and
                not has_evidence and
                not current_group.get('has_evidence')):
                # Add to existing group
                current_group['grouped_contributions'].append(serialized)
                current_group['frozen_global_points'] += (serialized.get('frozen_global_points') or 0)
                current_group['end_date'] = serialized['contribution_date']

                # Add unique user to the set
                user_details = serialized.get('user_details')
                if user_details:
                    user_key = f"{user_details.get('address', '')}|{user_details.get('name', '')}"
                    if user_key not in current_group['unique_users']:
                        current_group['unique_users'][user_key] = user_details
            else:
                # Start new group
                if current_group:
                    # Save previous group
                    current_group['count'] = len(current_group['grouped_contributions'])
                    current_group['users'] = list(current_group['unique_users'].values())
                    del current_group['unique_users']  # Remove the temporary set
                    current_group.pop('has_evidence', None)  # Remove internal tracking field
                    grouped.append(current_group)
                    total_grouped_count += 1

                # Create new group
                contribution_type_details = ContributionTypeSerializer(contrib.contribution_type).data
                current_group = {
                    'id': f"group_{contrib.id}",  # Use first contribution's ID as group ID
                    'contribution_type': {
                        'id': type_id,
                        'name': contrib.contribution_type.name,
                        'slug': contrib.contribution_type.slug,
                    },
                    'contribution_type_details': contribution_type_details,  # Full type details including category
                    'contribution_type_name': contrib.contribution_type.name,
                    'grouped_contributions': [serialized],
                    'frozen_global_points': serialized.get('frozen_global_points') or 0,
                    'contribution_date': serialized['contribution_date'],  # First date
                    'end_date': serialized['contribution_date'],  # Will be updated
                    'unique_users': {},
                    'user_details': serialized.get('user_details'),  # Primary user (for single-user groups)
                    'has_evidence': has_evidence,  # Track if this group has evidence
                }
                
                # Add first user
                user_details = serialized.get('user_details')
                if user_details:
                    user_key = f"{user_details.get('address', '')}|{user_details.get('name', '')}"
                    current_group['unique_users'][user_key] = user_details
        
        # Add the last group if exists
        if current_group:
            current_group['count'] = len(current_group['grouped_contributions'])
            # Check if unique_users exists before accessing it
            if 'unique_users' in current_group:
                current_group['users'] = list(current_group['unique_users'].values())
                del current_group['unique_users']
            else:
                # Fallback: extract users from grouped contributions
                current_group['users'] = []
            # Remove internal tracking field
            current_group.pop('has_evidence', None)
            grouped.append(current_group)
        
        # Paginate the grouped results
        start_idx = (page_number - 1) * page_size
        end_idx = start_idx + page_size
        paginated_groups = grouped[start_idx:end_idx]

        # Calculate if there's more data
        # We don't know the total grouped count without fetching everything,
        # so we check if we got a full page (suggests there might be more)
        has_next = len(grouped) > end_idx or len(all_contributions) >= limit_for_fetch
        has_previous = page_number > 1

        # Return paginated response
        return Response({
            'count': total_contributions_count,  # Total raw contribution count
            'next': f"?page={page_number + 1}&limit={page_size}&group_consecutive=true" if has_next else None,
            'previous': f"?page={page_number - 1}&limit={page_size}&group_consecutive=true" if has_previous else None,
            'results': paginated_groups
        })
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def highlights(self, request):
        """
        Get all active highlights across all contribution types.
        Optionally filter by category or waitlist users.
        """
        from contributions.models import Category, ContributionType
        from django.db.models import Q
        
        limit = int(request.query_params.get('limit', 10))
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
        
        # Order by contribution date descending and apply limit
        highlights = queryset.select_related(
            'contribution__user',
            'contribution__user__validator',
            'contribution__user__builder',
            'contribution__user__steward',
            'contribution__contribution_type',
            'contribution__contribution_type__category'
        ).prefetch_related(
            'contribution__evidence_items'
        ).order_by('-contribution__contribution_date')[:limit]
        
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)


class EvidenceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows evidence to be viewed.
    """
    queryset = Evidence.objects.all().order_by('-created_at')
    serializer_class = EvidenceSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['contribution', 'contribution__user']
    search_fields = ['description', 'url']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    parser_classes = [MultiPartParser, FormParser]


# Staff-only Django views for managing submissions
def is_staff(user):
    """Check if user is staff."""
    return user.is_authenticated and user.is_staff


@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_staff), name='dispatch')
class SubmissionListView(ListView):
    """List view for staff to see all submissions."""
    model = SubmittedContribution
    template_name = 'contributions/staff/submission_list.html'
    context_object_name = 'submissions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by state if provided
        state_filter = self.request.GET.get('state')
        if state_filter:
            queryset = queryset.filter(state=state_filter)
        
        # Order by creation date, newest first
        return queryset.select_related('user', 'contribution_type', 'reviewed_by', 'mission').prefetch_related('evidence_items').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['state_filter'] = self.request.GET.get('state', '')
        context['state_choices'] = SubmittedContribution.STATE_CHOICES
        context['pending_count'] = SubmittedContribution.objects.filter(state='pending').count()
        return context


@login_required
@user_passes_test(is_staff)
def submission_review_view(request, pk):
    """Single view for staff to review and take action on a submission."""
    submission = get_object_or_404(SubmittedContribution, pk=pk)
    
    if request.method == 'POST':
        form = SubmissionReviewForm(request.POST, instance=submission, user=request.user)
        if form.is_valid():
            form.save()
            
            # Show success message based on action
            if submission.state == 'accepted':
                messages.success(request, f'Submission accepted and contribution created with {form.cleaned_data["points"]} points.')
            elif submission.state == 'rejected':
                messages.warning(request, 'Submission rejected.')
            elif submission.state == 'more_info_needed':
                messages.info(request, 'More information requested from user.')
            
            # Redirect back to list or next submission
            next_submission = SubmittedContribution.objects.filter(
                state='pending',
                created_at__gt=submission.created_at
            ).first()
            
            if next_submission and 'review_next' in request.POST:
                return redirect('contributions:submission-review', pk=next_submission.pk)
            else:
                return redirect('contributions:submission-list')
    else:
        form = SubmissionReviewForm(instance=submission)
    
    # Get evidence items
    evidence_items = submission.evidence_items.all()
    
    # Get next pending submission for quick navigation
    next_submission = SubmittedContribution.objects.filter(
        state='pending',
        created_at__gt=submission.created_at
    ).first()
    
    # Get all contribution types with their current multipliers
    global_multipliers = []
    for ct in ContributionType.objects.all():
        try:
            multiplier = GlobalLeaderboardMultiplier.get_current_multiplier_value(ct)
        except:
            multiplier = 1.0
        
        global_multipliers.append({
            'contribution_type_id': ct.id,
            'contribution_type_name': ct.name,
            'min_points': ct.min_points,
            'max_points': ct.max_points,
            'multiplier': float(multiplier),  # Convert Decimal to float for JSON serialization
            'description': ct.description
        })
    
    import json
    context = {
        'submission': submission,
        'form': form,
        'evidence_items': evidence_items,
        'next_submission': next_submission,
        'global_multipliers': global_multipliers,  # For the table
        'global_multipliers_json': json.dumps(global_multipliers),  # For JavaScript
    }
    
    return render(request, 'contributions/staff/submission_review.html', context)


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
            'mission'  # Avoid N+1 queries when accessing mission details
        ).prefetch_related(
            'evidence_items'
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
    
    def create(self, request, *args, **kwargs):
        """Create a new submission with optional mission tracking."""
        mission_id = request.data.get('mission')
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
                contribution_type = ContributionType.objects.select_related('category').get(id=contribution_type_id)
                if contribution_type.category:
                    if contribution_type.category.slug == 'builder' and not hasattr(request.user, 'builder'):
                        return Response(
                            {'error': 'You must complete the Builder Welcome journey before submitting builder contributions.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    if contribution_type.category.slug == 'validator' and not hasattr(request.user, 'validator'):
                        return Response(
                            {'error': 'You must complete the Validator Waitlist journey before submitting validator contributions.'},
                            status=status.HTTP_403_FORBIDDEN
                        )
            except ContributionType.DoesNotExist:
                pass

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
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

        # Update the submission
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Update state back to pending and track edit time
        instance.state = 'pending'
        instance.last_edited_at = timezone.now()
        instance.staff_reply = ''  # Clear previous staff reply

        self.perform_update(serializer)

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Soft delete submission by marking as rejected (only allowed for pending or more_info_needed states)."""
        instance = self.get_object()

        # Check if cancellation is allowed
        if instance.state not in ['pending', 'more_info_needed']:
            return Response(
                {'error': 'Only pending or unreviewed submissions can be cancelled.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Soft delete - mark as rejected with cancellation note
        instance.state = 'rejected'
        instance.staff_reply = 'Cancelled by user'
        instance.reviewed_at = timezone.now()
        instance.save()

        return Response({'message': 'Submission cancelled successfully'}, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'], url_path='my')
    def my_submissions(self, request):
        """Get all submissions for the authenticated user."""
        queryset = self.get_queryset()
        
        # Filter by state if provided
        state = request.query_params.get('state')
        if state:
            queryset = queryset.filter(state=state)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
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

        # Reject file uploads
        if 'file' in request.data or request.FILES:
            return Response(
                {'error': 'File uploads are not currently supported. Please provide a URL or description instead.'},
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
    assigned_to = CharFilter(method='filter_assigned_to')

    def filter_username(self, queryset, name, value):
        """Filter by submitter name, email, or address (case-insensitive partial match)."""
        if value:
            return queryset.filter(
                Q(user__name__icontains=value) |
                Q(user__email__icontains=value) |
                Q(user__address__icontains=value)
            )
        return queryset

    def filter_assigned_to(self, queryset, name, value):
        """Filter by assigned steward or unassigned."""
        if value == 'null' or value == 'unassigned':
            return queryset.filter(assigned_to__isnull=True)
        elif value:
            return queryset.filter(assigned_to_id=value)
        return queryset

    class Meta:
        model = SubmittedContribution
        fields = ['state', 'contribution_type', 'user']


class StewardSubmissionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for stewards to review submissions.
    """
    serializer_class = StewardSubmissionSerializer
    authentication_classes = [EthereumAuthentication]
    permission_classes = [IsSteward]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = StewardSubmissionFilterSet
    ordering_fields = ['created_at', 'contribution_date']
    ordering = ['-created_at']

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Stats endpoint is public, all others require steward permission.
        """
        if self.action == 'stats':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        """Get all submissions for steward review."""
        queryset = SubmittedContribution.objects.all()

        # Comprehensive prefetch for optimization
        queryset = queryset.select_related(
            'user',
            'user__validator',
            'user__builder',
            'contribution_type',
            'contribution_type__category',
            'reviewed_by',
            'assigned_to',
            'converted_contribution',
            'mission'  # Avoid N+1 queries when accessing mission details
        ).prefetch_related('evidence_items')

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
    def review(self, request, pk=None):
        """Review and take action on a submission."""
        submission = self.get_object()
        
        serializer = StewardSubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action = serializer.validated_data['action']
        
        # Update submission fields
        submission.reviewed_by = request.user
        submission.reviewed_at = timezone.now()
        
        if action == 'accept':
            # Get the contribution type (use provided or keep original)
            contribution_type = serializer.validated_data.get('contribution_type', submission.contribution_type)
            
            # Get the user for the contribution (use provided or keep original submitter)
            contribution_user = serializer.validated_data.get('user', submission.user)
            
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
                mission=submission.mission
            )

            # Auto-grant builder status if accepting builder contribution for non-builder
            if (contribution_type.category and contribution_type.category.slug == 'builder'
                and not hasattr(contribution_user, 'builder')):
                from leaderboard.models import ensure_builder_status, update_user_leaderboard_entries
                ensure_builder_status(contribution_user, submission.contribution_date)
                # Manually update leaderboard since ensure_builder_status uses bulk_create (no signals)
                update_user_leaderboard_entries(contribution_user)

            # Copy evidence items
            for evidence in submission.evidence_items.all():
                Evidence.objects.create(
                    contribution=contribution,
                    description=evidence.description,
                    url=evidence.url,
                    file=evidence.file
                )
            
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
            
        elif action == 'reject':
            submission.state = 'rejected'
            submission.staff_reply = serializer.validated_data['staff_reply']
            
        elif action == 'more_info':
            submission.state = 'more_info_needed'
            submission.staff_reply = serializer.validated_data['staff_reply']
        
        submission.save()
        
        return Response(
            self.get_serializer(submission).data,
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """Get statistics for steward dashboard."""
        total_pending = SubmittedContribution.objects.filter(state='pending').count()
        
        # Stats specific to authenticated steward (if logged in)
        if request.user and request.user.is_authenticated:
            total_reviewed = SubmittedContribution.objects.filter(
                reviewed_by=request.user
            ).count()
            
            # Get last review time
            last_review = SubmittedContribution.objects.filter(
                reviewed_by=request.user
            ).order_by('-reviewed_at').first()
            
            last_review_time = last_review.reviewed_at if last_review else None
            
            # Get acceptance rate
            user_reviews = SubmittedContribution.objects.filter(
                reviewed_by=request.user
            ).exclude(state='pending')
            
            total_decisions = user_reviews.count()
            accepted = user_reviews.filter(state='accepted').count()
            total_rejected = user_reviews.filter(state='rejected').count()
            total_info_requested = user_reviews.filter(state='more_info_needed').count()
            acceptance_rate = (accepted / total_decisions * 100) if total_decisions > 0 else 0
        else:
            # Public stats - show overall system stats
            total_reviewed = SubmittedContribution.objects.exclude(state='pending').count()
            
            # Get last review time (system-wide)
            last_review = SubmittedContribution.objects.exclude(
                reviewed_at__isnull=True
            ).order_by('-reviewed_at').first()
            
            last_review_time = last_review.reviewed_at if last_review else None
            
            # Get overall acceptance rate
            all_reviews = SubmittedContribution.objects.exclude(state='pending')
            total_decisions = all_reviews.count()
            accepted = all_reviews.filter(state='accepted').count()
            total_rejected = all_reviews.filter(state='rejected').count()
            total_info_requested = all_reviews.filter(state='more_info_needed').count()
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

    @action(detail=True, methods=['post'], permission_classes=[IsSteward])
    def assign(self, request, pk=None):
        """Assign submission to a steward."""
        from users.models import User

        submission = self.get_object()
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

        rejected_count = submissions.count()
        if rejected_count == 0:
            return Response(
                {'error': 'No valid submissions found to reject'},
                status=status.HTTP_400_BAD_REQUEST
            )

        submissions.update(
            state='rejected',
            staff_reply=staff_reply,
            reviewed_by=request.user,
            reviewed_at=timezone.now()
        )

        return Response({
            'status': 'success',
            'rejected_count': rejected_count
        })


class MissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for retrieving missions.
    Only missions are returned by default.
    """
    serializer_class = MissionSerializer

    def get_queryset(self):
        """
        Return active highlights by default.
        Supports filtering by contribution_type and category.
        """
        from django.utils import timezone
        from django.db import models

        now = timezone.now()

        # Get base queryset of active highlights (without slicing)
        queryset = Mission.objects.filter(
            models.Q(start_date__isnull=True) | models.Q(start_date__lte=now)
        ).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gt=now)
        ).select_related('contribution_type', 'contribution_type__category')

        # Filter by contribution type if specified
        contribution_type = self.request.query_params.get('contribution_type', None)
        if contribution_type:
            queryset = queryset.filter(contribution_type_id=contribution_type)

        # Filter by category if specified
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(contribution_type__category__slug=category)

        return queryset
