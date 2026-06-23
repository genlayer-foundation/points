from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from contributions.models import Evidence, SubmittedContribution
from .models import FeatureCandidateScore, Steward, WorkingGroup, WorkingGroupParticipant
from users.serializers import StewardSerializer
from users.models import User
from .serializers import (
    FeatureCandidateAdminSerializer,
    FeatureCandidateSubmissionSerializer,
    WorkingGroupListSerializer,
    WorkingGroupDetailSerializer,
    WorkingGroupCreateSerializer,
    WorkingGroupUpdateSerializer,
    feature_score_summary,
)
from contributions.permissions import IsSteward
import logging

logger = logging.getLogger(__name__)


def user_can_review_feature_candidates(user):
    return bool(
        user
        and user.is_authenticated
        and hasattr(user, 'steward')
        and user.steward.can_review_feature_candidates
    )


def user_can_admin_feature_candidates(user):
    return bool(
        user
        and user.is_authenticated
        and (user.is_staff or user.is_superuser)
    )


class FeatureCandidateReviewViewSet(viewsets.ViewSet):
    """
    Blind scoring view for interesting submissions.
    Reviewers see only their own scores. Staff can access aggregate decisions.
    """
    permission_classes = [IsAuthenticated]

    def _interesting_queryset(self, include_scores=False):
        queryset = SubmittedContribution.objects.filter(
            is_interesting=True,
            state='accepted',
            contribution_type__slug='projects',
        ).select_related(
            'user',
            'user__githubconnection',
            'user__twitterconnection',
            'user__discordconnection',
            'contribution_type',
            'contribution_type__category',
        ).prefetch_related(
            Prefetch(
                'evidence_items',
                queryset=Evidence.objects.select_related('url_type').order_by('-created_at'),
            ),
        ).order_by('-created_at')
        if include_scores:
            queryset = queryset.prefetch_related('feature_candidate_scores')
        return queryset

    def _own_score_map(self, request):
        if not hasattr(request.user, 'steward'):
            return {}
        return dict(
            FeatureCandidateScore.objects.filter(
                steward=request.user.steward,
                submission__is_interesting=True,
                submission__state='accepted',
                submission__contribution_type__slug='projects',
            ).values_list('submission_id', 'score')
        )

    def _summary_map(self, submissions):
        result = {}
        for submission in submissions:
            scores = [
                score.score
                for score in getattr(submission, 'feature_candidate_scores').all()
            ]
            result[submission.id] = feature_score_summary(scores)
        return result

    @action(detail=False, methods=['get'], url_path='access')
    def access(self, request):
        return Response({
            'can_review': user_can_review_feature_candidates(request.user),
            'can_admin': user_can_admin_feature_candidates(request.user),
        })

    def list(self, request):
        if not user_can_review_feature_candidates(request.user):
            return Response(
                {'detail': 'You do not have access to feature candidate scoring.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        submissions = list(self._interesting_queryset())
        own_score_map = self._own_score_map(request)
        serializer = FeatureCandidateSubmissionSerializer(
            submissions,
            many=True,
            context={'own_score_map': own_score_map},
        )
        scored_count = sum(1 for submission in submissions if submission.id in own_score_map)
        return Response({
            'results': serializer.data,
            'progress': {
                'scored': scored_count,
                'total': len(submissions),
            },
        })

    @action(detail=True, methods=['post'], url_path='score')
    def score(self, request, pk=None):
        if not user_can_review_feature_candidates(request.user):
            return Response(
                {'detail': 'You do not have access to feature candidate scoring.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            score = serializers.IntegerField(min_value=0, max_value=3).run_validation(
                request.data.get('score')
            )
        except serializers.ValidationError as exc:
            return Response({'score': exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        submission = get_object_or_404(self._interesting_queryset(), pk=pk)
        FeatureCandidateScore.objects.update_or_create(
            submission=submission,
            steward=request.user.steward,
            defaults={'score': score},
        )

        return Response({'submission': str(submission.id), 'score': score})

    @action(detail=False, methods=['get'], url_path='admin')
    def admin(self, request):
        if not user_can_admin_feature_candidates(request.user):
            return Response(
                {'detail': 'Only staff users can access feature candidate aggregates.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        submissions = list(self._interesting_queryset(include_scores=True))
        own_score_map = self._own_score_map(request)
        summary_map = self._summary_map(submissions)
        submissions.sort(
            key=lambda submission: (
                not summary_map[submission.id]['manual_review'],
                not summary_map[submission.id]['is_borderline'],
                summary_map[submission.id]['decision'] != 'pending',
                -1 * (summary_map[submission.id]['median_score'] or 0),
                submission.created_at,
            )
        )
        serializer = FeatureCandidateAdminSerializer(
            submissions,
            many=True,
            context={'own_score_map': own_score_map, 'summary_map': summary_map},
        )
        return Response({'results': serializer.data})


class StewardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Steward profiles.
    """
    queryset = Steward.objects.all()
    serializer_class = StewardSerializer
    permission_classes = [IsAuthenticated]

    def _is_staff_mutation(self, request):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_superuser)
        )

    def _deny_non_staff_mutation(self, request):
        if self._is_staff_mutation(request):
            return None
        return Response(
            {'detail': 'Only staff users can mutate steward profiles.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    def create(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        denied = self._deny_non_staff_mutation(request)
        if denied is not None:
            return denied
        return super().destroy(request, *args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        """
        List all stewards with user details, role, and permitted categories.
        Allow public access to view steward list.
        """
        stewards = self.get_queryset().select_related('user').prefetch_related(
            'permissions__contribution_type'
        )
        data = []
        for steward in stewards:
            # Compute role based on permissions
            actions = set(steward.permissions.values_list('action', flat=True))
            if 'accept' in actions:
                role = 'Steward'
            elif actions:
                role = 'Reviewer'
            else:
                role = 'Steward'  # Default for stewards with no explicit permissions yet

            # Compute permitted categories
            categories = set(
                steward.permissions.values_list(
                    'contribution_type__category', flat=True
                )
            )
            categories.discard(None)

            steward_data = {
                'id': steward.id,
                'user_id': steward.user.id,
                'name': steward.user.name,
                'address': steward.user.address,
                'profile_image_url': steward.user.profile_image_url,
                'created_at': steward.created_at,
                'role': role,
                'permitted_categories': sorted(categories),
                'user_details': {
                    'name': steward.user.name,
                    'address': steward.user.address,
                    'profile_image_url': steward.user.profile_image_url,
                }
            }
            data.append(steward_data)
        return Response(data)
    
    def get_permissions(self):
        """
        Allow public access to list action, require auth for others.
        """
        if self.action == 'list':
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        Get or update current user's steward profile.
        """
        if request.method == 'GET':
            try:
                steward = Steward.objects.get(user=request.user)
                serializer = self.get_serializer(steward)
                return Response(serializer.data)
            except Steward.DoesNotExist:
                return Response(
                    {'detail': 'Steward profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method == 'PATCH':
            try:
                steward = Steward.objects.get(user=request.user)
            except Steward.DoesNotExist:
                return Response(
                    {'detail': 'Steward profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )
            serializer = self.get_serializer(steward, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkingGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Working Groups.
    - list/retrieve: AllowAny
    - create/destroy: IsSteward only
    """
    queryset = WorkingGroup.objects.all()

    def get_permissions(self):
        """Set permissions based on action."""
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsSteward()]

    def get_serializer_class(self):
        """Use different serializers for list vs detail vs update."""
        if self.action == 'list':
            return WorkingGroupListSerializer
        if self.action == 'create':
            return WorkingGroupCreateSerializer
        if self.action in ['update', 'partial_update']:
            return WorkingGroupUpdateSerializer
        return WorkingGroupDetailSerializer

    def get_queryset(self):
        """Annotate with participant count for list view."""
        queryset = WorkingGroup.objects.all()
        if self.action == 'list':
            queryset = queryset.annotate(participant_count=Count('participants'))
        return queryset

    @action(detail=True, methods=['post'], permission_classes=[IsSteward])
    def add_participant(self, request, pk=None):
        """Add a participant to the working group."""
        working_group = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        participant, created = WorkingGroupParticipant.objects.get_or_create(
            working_group=working_group,
            user=user
        )

        if not created:
            return Response(
                {'error': 'User is already a participant'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'message': f'{user.name or user.address} added to {working_group.name}'},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'], permission_classes=[IsSteward])
    def remove_participant(self, request, pk=None):
        """Remove a participant from the working group."""
        working_group = self.get_object()
        user_id = request.data.get('user_id')

        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            participant = WorkingGroupParticipant.objects.get(
                working_group=working_group,
                user_id=user_id
            )
            participant.delete()
            return Response(
                {'message': 'Participant removed'},
                status=status.HTTP_200_OK
            )
        except WorkingGroupParticipant.DoesNotExist:
            return Response(
                {'error': 'Participant not found'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], permission_classes=[IsSteward])
    def search_users(self, request):
        """Search users by name or address for autocomplete."""
        query = request.query_params.get('q', '').strip()

        if len(query) < 2:
            return Response([])

        users = User.objects.filter(
            Q(name__icontains=query) | Q(address__icontains=query)
        )[:10]

        results = [
            {
                'id': user.id,
                'name': user.name,
                'address': user.address,
                'profile_image_url': user.profile_image_url
            }
            for user in users
        ]

        return Response(results)
