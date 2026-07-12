from django.db.models import Count, Q
from django.db.models.functions import Coalesce
from django.db.models.expressions import Exists, OuterRef
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters import (
    BooleanFilter,
    CharFilter,
    DateTimeFilter,
    FilterSet,
    NumberFilter,
    UUIDFilter,
)
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from contributions.ai_attribution import AI_STEWARD_EMAIL, get_ai_steward
from contributions.models import (
    AIReviewFeedback,
    Evidence,
    ProjectMilestoneReview,
    ReviewProposal,
    SubmissionNote,
    SubmittedContribution,
)
from contributions.proposal_filters import ProposalReviewStatusFilterMixin
from contributions.rubric_review import rubric_summary_text, uses_project_rubric
from service_accounts.authentication import ServiceAccountAuthentication
from service_accounts.permissions import HasServiceAccountScope
from service_accounts.scopes import AI_REVIEW_PROPOSE_SCOPE, AI_REVIEW_READ_SCOPE
from stewards.models import ReviewTemplate

from .serializers import (
    AIReviewFeedbackRecordSerializer,
    AIReviewProposeSerializer,
    AIReviewReviewedSubmissionSerializer,
    AIReviewSubmissionSerializer,
    AIReviewTemplateSerializer,
    LightAIReviewSubmissionSerializer,
)


class AIReviewPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─── FilterSet ────────────────────────────────────────────────────────────────

class AIReviewFilterSet(ProposalReviewStatusFilterMixin, FilterSet):
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
    proposal_review_status = CharFilter(method='filter_proposal_review_status')
    proposed_confidence = CharFilter(method='filter_proposed_confidence')
    proposed_template = NumberFilter(method='filter_proposed_template')
    is_interesting = BooleanFilter(field_name='is_interesting')
    gate_reviewed = BooleanFilter(field_name='gate_reviewed')
    has_appeal = BooleanFilter(field_name='has_appeal')
    search = CharFilter(method='filter_search')
    mission = CharFilter(method='filter_mission')
    exclude_mission = CharFilter(method='filter_exclude_mission')

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


class AIReviewFeedbackFilterSet(FilterSet):
    """Incremental benchmark filters for structured feedback records."""

    updated_after = DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    submission = UUIDFilter(field_name='submitted_contribution_id')

    class Meta:
        model = AIReviewFeedback
        fields = []


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

    authentication_classes = [ServiceAccountAuthentication]
    permission_classes = [HasServiceAccountScope]
    required_scopes = {
        'propose': AI_REVIEW_PROPOSE_SCOPE,
        '*': AI_REVIEW_READ_SCOPE,
    }
    pagination_class = AIReviewPagination
    filter_backends = [filters.OrderingFilter]
    filterset_class = AIReviewFilterSet
    # No default `ordering` here: each action's queryset carries its own
    # order_by, which OrderingFilter preserves unless ?ordering= overrides it.
    ordering_fields = ['created_at', 'contribution_date']
    proposal_query_params = {
        'has_proposal',
        'proposed_by',
        'exclude_proposed_by',
        'proposed_action',
        'proposal_review_status',
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
                'proposal_questioned_by',
                'project_milestone_review',
                'project_milestone_review__proposer',
            )
            .prefetch_related(*prefetches)
            .order_by('created_at')
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

    def _validate_and_apply_proposal(self, submission, data, ai_user, service_account_name, is_update=False):
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
        submission.proposal_review_status = SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW
        submission.proposal_review_feedback = ''
        submission.proposal_questioned_by = None
        submission.proposal_questioned_at = None
        if 'gate_reviewed' in data:
            submission.gate_reviewed = data['gate_reviewed']

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
            review_proposal = ReviewProposal.objects.create(
                submitted_contribution=submission,
                proposer=ai_user,
                source=ReviewProposal.SOURCE_AI,
                service_account_name=service_account_name,
                action=data['proposed_action'],
                points=data.get('proposed_points'),
                staff_reply=data.get('proposed_staff_reply', ''),
                confidence=data.get('confidence', 'medium'),
                gate_failures=rubric_review['gate_failures'],
                sections=rubric_review['sections'],
                extras=rubric_review['extras'],
                overall_reason=rubric_review['overall_reason'],
                synthesis=data.get('synthesis', ''),
            )
        else:
            review_proposal = None

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
                'review_proposal_id': review_proposal.id if review_proposal else None,
                'synthesis': data.get('synthesis', ''),
                # Audit trail: which service account authenticated the proposal
                'service_account': service_account_name,
            },
        )

        return Response(
            AIReviewSubmissionSerializer(submission).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post', 'put'], url_path='propose')
    @transaction.atomic
    def propose(self, request, pk=None):
        """
        Submit or update a review proposal for a submission.

        POST: Create a new proposal (fails if one already exists).
        PUT: Update an existing proposal (fails if none exists).
        """
        submission = get_object_or_404(
            SubmittedContribution.objects.select_for_update(of=('self',)).select_related(
                'contribution_type',
                'contribution_type__category',
                'user',
                'proposed_by',
                'proposal_questioned_by',
                'project_milestone_review',
                'project_milestone_review__proposer',
            ),
            pk=pk,
            state='pending',
        )

        is_update = request.method == 'PUT'
        ai_user = get_ai_steward()

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
            submission, serializer.validated_data, ai_user,
            # HasServiceAccountScope guarantees a token principal here
            service_account_name=request.auth.service_account.name,
            is_update=is_update,
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
                'proposal_questioned_by',
                'project_milestone_review',
                'project_milestone_review__proposer',
            )
            .prefetch_related('evidence_items')
            .order_by('-proposed_at')
        )
        if 'proposal_review_status' not in request.query_params:
            queryset = queryset.filter(
                Q(proposal_review_status=SubmittedContribution.PROPOSAL_STATUS_PENDING_REVIEW)
                | Q(proposal_review_status__isnull=True)
            )

        queryset = self.filter_queryset(queryset)

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

        queryset = self.filter_queryset(queryset)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AIReviewReviewedSubmissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AIReviewReviewedSubmissionSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='feedback')
    def feedback(self, request):
        """Export structured steward feedback for benchmark ingestion."""
        queryset = (
            AIReviewFeedback.objects
            .select_related('reviewer')
            .order_by('updated_at', 'id')
        )
        filterset = AIReviewFeedbackFilterSet(
            data=request.query_params,
            queryset=queryset,
            request=request,
        )
        if not filterset.is_valid():
            return Response(filterset.errors, status=status.HTTP_400_BAD_REQUEST)
        queryset = filterset.qs

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = AIReviewFeedbackRecordSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AIReviewFeedbackRecordSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='templates')
    def templates(self, request):
        """List all available review templates."""
        templates = ReviewTemplate.objects.all()
        serializer = AIReviewTemplateSerializer(templates, many=True)
        return Response(serializer.data)
