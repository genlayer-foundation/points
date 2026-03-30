from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.db.models.expressions import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import BooleanFilter, CharFilter, FilterSet, NumberFilter
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from contributions.models import Evidence, SubmissionNote, SubmittedContribution
from stewards.models import ReviewTemplate
from users.models import User

from .permissions import IsAIReviewToken
from .serializers import (
    AIReviewProposeSerializer,
    AIReviewSubmissionSerializer,
    AIReviewTemplateSerializer,
    LightAIReviewSubmissionSerializer,
)

AI_STEWARD_EMAIL = 'genlayer-steward@genlayer.foundation'


class AIReviewPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─── FilterSet ────────────────────────────────────────────────────────────────

class AIReviewFilterSet(FilterSet):
    """Filterset for AI review agent submission queries."""

    contribution_type = NumberFilter(field_name='contribution_type_id')
    category = CharFilter(method='filter_category')
    exclude_category = CharFilter(method='filter_exclude_category')
    exclude_contribution_type = NumberFilter(method='filter_exclude_contribution_type')
    username_search = CharFilter(method='filter_username')
    exclude_username = CharFilter(method='filter_exclude_username')
    include_content = CharFilter(method='filter_include_content')
    exclude_content = CharFilter(method='filter_exclude_content')
    exclude_empty_evidence = BooleanFilter(method='filter_exclude_empty_evidence')
    only_empty_evidence = BooleanFilter(method='filter_only_empty_evidence')
    min_accepted_contributions = NumberFilter(method='filter_min_accepted_contributions')
    has_proposal = BooleanFilter(method='filter_has_proposal')
    exclude_state = CharFilter(method='filter_exclude_state')

    class Meta:
        model = SubmittedContribution
        fields = []

    def filter_category(self, queryset, name, value):
        if value:
            return queryset.filter(contribution_type__category__slug=value)
        return queryset

    def filter_exclude_category(self, queryset, name, value):
        if value:
            return queryset.exclude(contribution_type__category__slug=value)
        return queryset

    def filter_exclude_contribution_type(self, queryset, name, value):
        if value:
            return queryset.exclude(contribution_type_id=value)
        return queryset

    def filter_username(self, queryset, name, value):
        if value:
            return queryset.filter(
                Q(user__name__icontains=value)
                | Q(user__email__icontains=value)
                | Q(user__address__icontains=value)
            )
        return queryset

    def filter_exclude_username(self, queryset, name, value):
        if value:
            return queryset.exclude(
                Q(user__name__icontains=value)
                | Q(user__email__icontains=value)
                | Q(user__address__icontains=value)
            )
        return queryset

    def filter_include_content(self, queryset, name, value):
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    has_matching_evidence = Evidence.objects.filter(
                        submitted_contribution=OuterRef('pk'),
                    ).filter(
                        Q(url__icontains=term) | Q(description__icontains=term)
                    )
                    queryset = queryset.filter(
                        Exists(has_matching_evidence) | Q(notes__icontains=term)
                    )
        return queryset

    def filter_exclude_content(self, queryset, name, value):
        if value:
            for term in value.split(','):
                term = term.strip()
                if term:
                    has_matching_evidence = Evidence.objects.filter(
                        submitted_contribution=OuterRef('pk'),
                    ).filter(
                        Q(url__icontains=term) | Q(description__icontains=term)
                    )
                    queryset = queryset.exclude(
                        Exists(has_matching_evidence) | Q(notes__icontains=term)
                    )
        return queryset

    def filter_exclude_empty_evidence(self, queryset, name, value):
        if value:
            has_url_evidence = Evidence.objects.filter(
                submitted_contribution=OuterRef('pk'),
                url__gt='',
            )
            return queryset.exclude(
                ~Exists(has_url_evidence)
                & ~Q(notes__icontains='http://')
                & ~Q(notes__icontains='https://')
            )
        return queryset

    def filter_only_empty_evidence(self, queryset, name, value):
        if value:
            has_url_evidence = Evidence.objects.filter(
                submitted_contribution=OuterRef('pk'),
                url__gt='',
            )
            return queryset.filter(
                ~Exists(has_url_evidence)
                & ~Q(notes__icontains='http://')
                & ~Q(notes__icontains='https://')
            )
        return queryset

    def filter_min_accepted_contributions(self, queryset, name, value):
        if value and value > 0:
            from django.db.models import Subquery

            accepted_count = (
                SubmittedContribution.objects.filter(
                    user=OuterRef('user'),
                    state='accepted',
                )
                .values('user')
                .annotate(count=Count('id'))
                .values('count')
            )
            return queryset.annotate(
                user_accepted_count=Coalesce(Subquery(accepted_count), 0)
            ).filter(user_accepted_count__gte=value)
        return queryset

    def filter_has_proposal(self, queryset, name, value):
        if value is True:
            return queryset.filter(proposed_action__isnull=False)
        elif value is False:
            return queryset.filter(proposed_action__isnull=True)
        return queryset

    def filter_exclude_state(self, queryset, name, value):
        if value:
            return queryset.exclude(state=value)
        return queryset


# ─── ViewSet ──────────────────────────────────────────────────────────────────


class AIReviewViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """
    API endpoints for the external AI review agent.

    Provides read access to pending submissions and the ability to propose
    review actions. All proposals require human steward approval.
    """

    authentication_classes = []  # Pure token auth via permission class
    permission_classes = [IsAIReviewToken]
    pagination_class = AIReviewPagination
    filter_backends = [filters.OrderingFilter]
    filterset_class = AIReviewFilterSet
    ordering_fields = ['created_at']
    ordering = ['created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return LightAIReviewSubmissionSerializer
        return AIReviewSubmissionSerializer

    def get_queryset(self):
        return (
            SubmittedContribution.objects.filter(
                state='pending',
                proposed_action__isnull=True,
                reviewed_by__isnull=True,
            )
            .select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
                'proposed_by',
            )
            .prefetch_related('evidence_items')
        )

    def filter_queryset(self, queryset):
        """Apply django-filter filterset manually since we use OrderingFilter as the only backend."""
        filterset = self.filterset_class(
            data=self.request.query_params,
            queryset=queryset,
            request=self.request,
        )
        if filterset.is_valid():
            queryset = filterset.qs
        return super().filter_queryset(queryset)

    @action(detail=True, methods=['post'], url_path='propose')
    def propose(self, request, pk=None):
        """Submit a review proposal for a submission."""
        submission = get_object_or_404(
            SubmittedContribution.objects.select_related(
                'contribution_type', 'contribution_type__category', 'user',
            ),
            pk=pk,
            state='pending',
        )

        # Check if already proposed
        if submission.proposed_action is not None:
            return Response(
                {'error': 'This submission already has an active proposal.'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = AIReviewProposeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate points within contribution type range for accept
        if data['proposed_action'] == 'accept' and data.get('proposed_points'):
            ct = submission.contribution_type
            points = data['proposed_points']
            if points < ct.min_points or points > ct.max_points:
                return Response(
                    {
                        'error': f'Points must be between {ct.min_points} and {ct.max_points} '
                        f'for {ct.name}.'
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Get AI steward user
        try:
            ai_user = User.objects.get(email=AI_STEWARD_EMAIL)
        except User.DoesNotExist:
            return Response(
                {'error': 'AI steward user not found. Run migrations.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Set proposal fields
        submission.proposed_action = data['proposed_action']
        submission.proposed_points = data.get('proposed_points')
        submission.proposed_staff_reply = data.get('proposed_staff_reply', '')
        submission.proposed_by = ai_user
        submission.proposed_at = timezone.now()
        submission.save()

        # Create CRM note
        action_str = data['proposed_action']
        confidence = data.get('confidence', 'medium')
        reasoning = data.get('reasoning', '')
        pts_str = (
            f' with **{data.get("proposed_points")} points**'
            if action_str == 'accept'
            else ''
        )
        message = (
            f'[AI Review] Proposed: **{action_str}**{pts_str} '
            f'(confidence: {confidence})'
        )
        if reasoning:
            message += f'\nReasoning: {reasoning}'

        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message=message,
            is_proposal=True,
        )

        return Response(
            AIReviewSubmissionSerializer(submission).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """List all available review templates."""
        templates = ReviewTemplate.objects.all()
        serializer = AIReviewTemplateSerializer(templates, many=True)
        return Response(serializer.data)
