from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Max, F
from django.db.models.functions import Coalesce
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.generic import ListView
from django.utils.decorators import method_decorator
from .models import ContributionType, Contribution, Evidence, SubmittedContribution, ContributionHighlight
from .serializers import (ContributionTypeSerializer, ContributionSerializer, 
                         EvidenceSerializer, SubmittedContributionSerializer,
                         SubmittedEvidenceSerializer, ContributionHighlightSerializer)
from .forms import SubmissionReviewForm
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
        
        types_with_stats = ContributionType.objects.annotate(
            count=Count('contributions'),
            participants_count=Count('contributions__user', distinct=True),
            last_earned=Coalesce(Max('contributions__contribution_date'), timezone.now()),
            total_points_given=Coalesce(Sum('contributions__frozen_global_points'), 0)
        ).values('id', 'name', 'description', 'min_points', 'max_points', 'count', 'participants_count', 'last_earned', 'total_points_given')
        
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
        from users.serializers import UserSerializer
        
        contribution_type = self.get_object()
        
        # Get top contributors by summing their frozen global points for this type
        top_contributors = Contribution.objects.filter(
            contribution_type=contribution_type
        ).values('user').annotate(
            total_points=Sum('frozen_global_points'),
            contribution_count=Count('id')
        ).order_by('-total_points')[:10]
        
        # Get user objects and add the aggregated data
        result = []
        for contributor in top_contributors:
            user = contribution_type.contributions.filter(
                user_id=contributor['user']
            ).first().user
            
            user_data = UserSerializer(user).data
            user_data['total_points'] = contributor['total_points']
            user_data['contribution_count'] = contributor['contribution_count']
            result.append(user_data)
        
        return Response(result)
    
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def recent_contributions(self, request, pk=None):
        """
        Get the last 10 contributions for a specific contribution type.
        """
        contribution_type = self.get_object()
        
        recent_contributions = Contribution.objects.filter(
            contribution_type=contribution_type
        ).order_by('-contribution_date')[:10]
        
        serializer = ContributionSerializer(recent_contributions, many=True)
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
        
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def all_highlights(self, request):
        """
        Get all active highlights across all contribution types.
        """
        limit = int(request.query_params.get('limit', 5))
        
        highlights = ContributionHighlight.get_active_highlights(limit=limit)
        
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
    filterset_fields = ['user', 'contribution_type']
    search_fields = ['notes', 'user__email', 'user__name', 'contribution_type__name']
    ordering_fields = ['contribution_date', 'created_at', 'points', 'frozen_global_points']
    ordering = ['-contribution_date']
    
    def get_queryset(self):
        queryset = Contribution.objects.all().order_by('-contribution_date')
        
        # Filter by user address if provided
        user_address = self.request.query_params.get('user_address')
        if user_address:
            queryset = queryset.filter(user__address__iexact=user_address)
            
        return queryset


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
        return queryset.select_related('user', 'contribution_type', 'reviewed_by').prefetch_related('evidence_items').order_by('-created_at')
    
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
        ).order_by('-created_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new submission."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """Update submission (only allowed if state is 'more_info_needed')."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if update is allowed
        if instance.state != 'more_info_needed':
            return Response(
                {'error': 'Submission can only be edited when more information is requested.'},
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
