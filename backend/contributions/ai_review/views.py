from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.db.models.expressions import Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import BooleanFilter, CharFilter, FilterSet, NumberFilter
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from contributions.models import (
    Evidence,
    ProjectMilestoneReview,
    SubmissionNote,
    SubmittedContribution,
)
from contributions.rubric_review import rubric_summary_text, uses_project_rubric
from stewards.models import ReviewTemplate
from users.models import User

from .permissions import IsAIReviewToken
from .serializers import (
    AIReviewProposeSerializer,
    AIReviewReviewedSubmissionSerializer,
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
    state = CharFilter(field_name='state')
    category = CharFilter(method='filter_category')
    exclude_category = CharFilter(method='filter_exclude_category')
    exclude_contribution_type = NumberFilter(method='filter_exclude_contribution_type')
    username_search = CharFilter(method='filter_username')
    exclude_username = CharFilter(method='filter_exclude_username')
    assigned_to = CharFilter(method='filter_assigned_to')
    exclude_assigned_to = CharFilter(method='filter_exclude_assigned_to')
    proposed_by = CharFilter(method='filter_proposed_by')
    exclude_proposed_by = CharFilter(method='filter_exclude_proposed_by')
    include_content = CharFilter(method='filter_include_content')
    exclude_content = CharFilter(method='filter_exclude_content')
    exclude_empty_evidence = BooleanFilter(method='filter_exclude_empty_evidence')
    only_empty_evidence = BooleanFilter(method='filter_only_empty_evidence')
    min_accepted_contributions = NumberFilter(method='filter_min_accepted_contributions')
    has_proposal = BooleanFilter(method='filter_has_proposal')
    exclude_state = CharFilter(method='filter_exclude_state')
    proposed_action = CharFilter(method='filter_proposed_action')
    proposed_confidence = CharFilter(method='filter_proposed_confidence')
    proposed_template = NumberFilter(method='filter_proposed_template')
    is_interesting = BooleanFilter(field_name='is_interesting')
    has_appeal = BooleanFilter(field_name='has_appeal')
    search = CharFilter(method='filter_search')
    mission = CharFilter(method='filter_mission')
    exclude_mission = CharFilter(method='filter_exclude_mission')
    resubmitted_more_info = BooleanFilter(method='filter_resubmitted_more_info')

    class Meta:
        model = SubmittedContribution
        fields = []

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

    def filter_assigned_to(self, queryset, name, value):
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                if item in ('null', 'unassigned'):
                    query |= Q(assigned_to__isnull=True)
                else:
                    parsed_id = self._parse_id_filter_value(item)
                    if parsed_id is not None:
                        query |= Q(assigned_to_id=parsed_id)
            return queryset.filter(query) if query else queryset.none()
        return queryset

    def filter_exclude_assigned_to(self, queryset, name, value):
        values = self._split_filter_values(value)
        if values:
            query = Q()
            for item in values:
                if item in ('null', 'unassigned'):
                    query |= Q(assigned_to__isnull=True)
                else:
                    parsed_id = self._parse_id_filter_value(item)
                    if parsed_id is not None:
                        query |= Q(assigned_to_id=parsed_id)
            return queryset.exclude(query) if query else queryset
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

    def _is_reviewed_history_request(self):
        parser_context = getattr(self.request, 'parser_context', {}) if self.request else {}
        view = parser_context.get('view')
        return getattr(view, 'action', None) == 'reviewed'

    def _historical_proposal_note_exists(self, value):
        notes = SubmissionNote.objects.filter(
            submitted_contribution=OuterRef('pk'),
            is_proposal=True,
        )
        if value == 'ai':
            notes = notes.filter(user__email=AI_STEWARD_EMAIL)
        else:
            parsed_id = self._parse_id_filter_value(value)
            if parsed_id is None:
                return None
            notes = notes.filter(user_id=parsed_id)
        return Exists(notes)

    def _historical_proposal_note_exists_for_values(self, values):
        notes = SubmissionNote.objects.filter(
            submitted_contribution=OuterRef('pk'),
            is_proposal=True,
        )
        user_filter = Q()
        for item in values:
            if item == 'ai':
                user_filter |= Q(user__email=AI_STEWARD_EMAIL)
            elif item not in ('none', 'null', 'unproposed'):
                parsed_id = self._parse_id_filter_value(item)
                if parsed_id is not None:
                    user_filter |= Q(user_id=parsed_id)
        if not user_filter:
            return None
        return Exists(notes.filter(user_filter))

    def filter_proposed_by(self, queryset, name, value):
        values = self._split_filter_values(value)
        if values:
            if self._is_reviewed_history_request():
                querysets = []
                if any(item in ('none', 'null', 'unproposed') for item in values):
                    notes = SubmissionNote.objects.filter(
                        submitted_contribution=OuterRef('pk'),
                        is_proposal=True,
                    )
                    querysets.append(queryset.filter(~Exists(notes)))
                historical_exists = self._historical_proposal_note_exists_for_values(values)
                if historical_exists is not None:
                    querysets.append(queryset.filter(historical_exists))
                if not querysets:
                    return queryset.none()
                result = querysets[0]
                for extra_queryset in querysets[1:]:
                    result = result | extra_queryset
                return result
            query = Q()
            for item in values:
                condition = self._proposed_by_condition(item)
                if condition is not None:
                    query |= condition
            return queryset.filter(query) if query else queryset.none()
        return queryset

    def filter_exclude_proposed_by(self, queryset, name, value):
        values = self._split_filter_values(value)
        if values:
            if self._is_reviewed_history_request():
                querysets = []
                if any(item in ('none', 'null', 'unproposed') for item in values):
                    notes = SubmissionNote.objects.filter(
                        submitted_contribution=OuterRef('pk'),
                        is_proposal=True,
                    )
                    querysets.append(queryset.filter(~Exists(notes)))
                historical_exists = self._historical_proposal_note_exists_for_values(values)
                if historical_exists is not None:
                    querysets.append(queryset.filter(historical_exists))
                if not querysets:
                    return queryset
                excluded = querysets[0]
                for extra_queryset in querysets[1:]:
                    excluded = excluded | extra_queryset
                return queryset.exclude(pk__in=excluded.values('pk'))
            query = Q()
            for item in values:
                condition = self._proposed_by_condition(item)
                if condition is not None:
                    query |= condition
            return queryset.exclude(query) if query else queryset
        return queryset

    def filter_search(self, queryset, name, value):
        if value:
            has_matching_evidence = Evidence.objects.filter(
                submitted_contribution=OuterRef('pk'),
            ).filter(
                Q(url__icontains=value) | Q(description__icontains=value)
            )
            return queryset.filter(
                Q(user__name__icontains=value)
                | Q(user__email__icontains=value)
                | Q(user__address__icontains=value)
                | Q(notes__icontains=value)
                | Exists(has_matching_evidence)
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

    def filter_proposed_action(self, queryset, name, value):
        if value:
            return queryset.filter(proposed_action=value.lower())
        return queryset

    def filter_proposed_confidence(self, queryset, name, value):
        if value:
            return queryset.filter(proposed_confidence=value.lower())
        return queryset

    def filter_proposed_template(self, queryset, name, value):
        if value:
            return queryset.filter(proposed_template_id=value)
        return queryset

    def filter_mission(self, queryset, name, value):
        if value in ('none', 'null'):
            return queryset.filter(mission__isnull=True)
        if value:
            return queryset.filter(mission_id=value)
        return queryset

    def filter_exclude_mission(self, queryset, name, value):
        if value in ('none', 'null'):
            return queryset.exclude(mission__isnull=True)
        if value:
            return queryset.exclude(mission_id=value)
        return queryset

    def filter_resubmitted_more_info(self, queryset, name, value):
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
    ordering_fields = ['created_at', 'contribution_date']
    ordering = ['created_at']
    proposal_query_params = {
        'has_proposal',
        'proposed_by',
        'exclude_proposed_by',
        'proposed_action',
        'proposed_confidence',
        'proposed_template',
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return LightAIReviewSubmissionSerializer
        return AIReviewSubmissionSerializer

    def get_queryset(self):
        qs = SubmittedContribution.objects.filter(state='pending')
        # Appealed submissions are reserved for human stewards by default, but
        # keep them queryable when the caller explicitly asks for has_appeal.
        if 'has_appeal' not in self.request.query_params:
            qs = qs.filter(has_appeal=False)
        # The default list endpoint returns unproposed submissions. If the
        # caller uses proposal-specific filters, leave proposals queryable.
        if self.action == 'list' and self.proposal_query_params.isdisjoint(self.request.query_params):
            qs = qs.filter(proposed_action__isnull=True)
        prefetches = ['evidence_items']
        if self.action != 'list':
            prefetches.append('internal_notes')

        return (
            qs.select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
                'mission',
                'assigned_to',
                'proposed_by',
                'proposed_contribution_type',
                'proposed_user',
                'proposed_template',
                'project_milestone_review',
                'project_milestone_review__proposer',
            )
            .prefetch_related(*prefetches)
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

    def _apply_search_ordering(self, request, queryset):
        ordering = request.query_params.get('ordering')
        allowed = {'created_at', '-created_at', 'contribution_date', '-contribution_date'}
        if ordering in allowed:
            return queryset.order_by(ordering)
        return queryset

    def _validate_and_apply_proposal(self, submission, data, ai_user, is_update=False):
        """Validate proposal data and apply it to the submission."""
        # Validate points within contribution type range for accept
        if data['proposed_action'] == 'accept' and data.get('proposed_points') is not None:
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

        # Set proposal fields
        submission.proposed_action = data['proposed_action']
        submission.proposed_points = data.get('proposed_points')
        submission.proposed_staff_reply = data.get('proposed_staff_reply', '')
        submission.proposed_by = ai_user
        submission.proposed_at = timezone.now()
        submission.proposed_confidence = data.get('confidence', 'medium')

        # Resolve template FK (PrimaryKeyRelatedField returns instance or None)
        template = data.get('template_id')
        submission.proposed_template = template

        submission.save()

        rubric_review = data.get('rubric_review')
        rubric_record = None
        if rubric_review and uses_project_rubric(submission.contribution_type):
            rubric_record, _ = ProjectMilestoneReview.objects.update_or_create(
                submitted_contribution=submission,
                defaults={
                    'proposer': ai_user,
                    'review_flow': submission.contribution_type.review_flow,
                    'action': data['proposed_action'],
                    'confidence': data.get('confidence', 'medium'),
                    'gate_failures': rubric_review['gate_failures'],
                    'sections': rubric_review['sections'],
                    'extras': rubric_review['extras'],
                    'overall_reason': rubric_review['overall_reason'],
                },
            )

        # Create CRM note
        action_str = data['proposed_action']
        confidence = data.get('confidence', 'medium')
        reasoning = data.get('reasoning', '')
        proposed_points = data.get('proposed_points')
        pts_str = (
            f' with **{proposed_points} points**'
            if action_str == 'accept' and proposed_points is not None
            else ''
        )
        prefix = '[AI Review] Updated proposal' if is_update else '[AI Review] Proposed'
        message = (
            f'{prefix}: **{action_str}**{pts_str} '
            f'(confidence: {confidence})'
        )
        if reasoning:
            message += f'\nReasoning: {reasoning}'
        if rubric_review:
            message += f'\n{rubric_summary_text(rubric_review)}'

        SubmissionNote.objects.create(
            submitted_contribution=submission,
            user=ai_user,
            message=message,
            is_proposal=True,
            data={
                'action': data['proposed_action'],
                'points': data.get('proposed_points'),
                'staff_reply': data.get('proposed_staff_reply', ''),
                'template_id': template.id if template else None,
                'confidence': confidence,
                'reasoning': reasoning,
                'rubric_review_id': rubric_record.id if rubric_record else None,
            },
        )

        return Response(
            AIReviewSubmissionSerializer(submission).data,
            status=status.HTTP_200_OK,
        )

    def _get_ai_user(self):
        """Get the AI steward user or return an error response."""
        try:
            return User.objects.get(email=AI_STEWARD_EMAIL)
        except User.DoesNotExist:
            return None

    @action(detail=True, methods=['post', 'put'], url_path='propose')
    def propose(self, request, pk=None):
        """
        Submit or update a review proposal for a submission.

        POST: Create a new proposal (fails if one already exists).
        PUT: Update an existing proposal (fails if none exists).
        """
        submission = get_object_or_404(
            SubmittedContribution.objects.select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
                'project_milestone_review',
                'project_milestone_review__proposer',
            ),
            pk=pk,
            state='pending',
        )

        is_update = request.method == 'PUT'
        ai_user = self._get_ai_user()
        if ai_user is None:
            return Response(
                {'error': 'AI steward user not found. Run migrations.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if is_update and submission.proposed_action is None:
            return Response(
                {'error': 'This submission has no proposal to update.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        if is_update and submission.proposed_by_id != ai_user.id:
            return Response(
                {'error': 'Only AI-created proposals can be updated through this endpoint.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not is_update and submission.proposed_action is not None:
            return Response(
                {'error': 'This submission already has an active proposal.'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = AIReviewProposeSerializer(
            data=request.data,
            context={'submission': submission},
        )
        serializer.is_valid(raise_exception=True)

        return self._validate_and_apply_proposal(
            submission, serializer.validated_data, ai_user, is_update=is_update,
        )

    @action(detail=False, methods=['get'], url_path='proposed')
    def proposed(self, request):
        """
        List pending submissions that have a proposal awaiting steward review.

        Returns submissions where state='pending' and proposed_action is set.
        Filter with proposed_by=ai to restrict the list to AI-created proposals,
        or proposed_by=<user_id> for proposals from a specific steward.
        Use GET /ai-review/{id}/ to retrieve full proposal details for any
        submission returned here.
        """
        queryset = (
            SubmittedContribution.objects.filter(
                state='pending',
                proposed_action__isnull=False,
            )
            .select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
                'mission',
                'assigned_to',
                'proposed_by',
                'proposed_contribution_type',
                'proposed_user',
                'proposed_template',
                'project_milestone_review',
                'project_milestone_review__proposer',
            )
            .prefetch_related('evidence_items')
            .order_by('-proposed_at')
        )

        # Apply the same filterset as the main list endpoint
        filterset = self.filterset_class(
            data=request.query_params,
            queryset=queryset,
            request=request,
        )
        if filterset.is_valid():
            queryset = filterset.qs
        queryset = self._apply_search_ordering(request, queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = LightAIReviewSubmissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = LightAIReviewSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='reviewed')
    def reviewed(self, request):
        """
        List reviewed submissions that had AI proposals.

        Returns submissions with state in (accepted, rejected, more_info_needed)
        that have at least one AI-created SubmissionNote with is_proposal=True.
        Includes evidence, review outcome (state, staff_reply), and all internal notes.
        """
        ai_proposal_notes = SubmissionNote.objects.filter(
            submitted_contribution=OuterRef('pk'),
            is_proposal=True,
            user__email=AI_STEWARD_EMAIL,
        )

        queryset = (
            SubmittedContribution.objects
            .filter(
                state__in=['accepted', 'rejected', 'more_info_needed'],
            )
            .filter(Exists(ai_proposal_notes))
            .select_related(
                'contribution_type',
                'contribution_type__category',
                'mission',
                'project_milestone_review',
                'project_milestone_review__proposer',
            )
            .prefetch_related('evidence_items', 'internal_notes')
            .order_by('-reviewed_at')
        )

        filterset = self.filterset_class(
            data=request.query_params,
            queryset=queryset,
            request=request,
        )
        if filterset.is_valid():
            queryset = filterset.qs
        queryset = self._apply_search_ordering(request, queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AIReviewReviewedSubmissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AIReviewReviewedSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """List all available review templates."""
        templates = ReviewTemplate.objects.all()
        serializer = AIReviewTemplateSerializer(templates, many=True)
        return Response(serializer.data)
