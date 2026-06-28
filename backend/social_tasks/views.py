import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from .eligibility import evaluate_task_eligibility
from .models import SocialTask, SocialTaskCompletion
from .serializers import SocialTaskSerializer
from .verifiers import verify

logger = logging.getLogger(__name__)


class CompleteThrottle(UserRateThrottle):
    """30 requests per minute per user on the complete endpoint."""
    scope = 'social_task_complete'
    rate = '30/min'


class SocialTaskViewSet(viewsets.GenericViewSet):
    """Public list + per-user complete for social tasks."""

    serializer_class = SocialTaskSerializer
    queryset = SocialTask.objects.select_related('category')
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        status_filter = request.query_params.get('status')
        category_slug = request.query_params.get('category')

        qs = self.get_queryset()
        if category_slug:
            qs = qs.filter(category__slug=category_slug)

        user = request.user if request.user.is_authenticated else None
        completions_by_task_id = {}
        if user is not None:
            # The audit JSON is never read here; skip loading it.
            completions_by_task_id = {
                c.task_id: c
                for c in SocialTaskCompletion.objects.filter(
                    user=user, task__in=qs
                ).defer('verification_data')
            }

        now = timezone.now()
        active_tasks = []
        completed_tasks = []
        for task in qs:
            completion = completions_by_task_id.get(task.id)
            task._user_completion = completion if completion else False
            task._eligibility_result = evaluate_task_eligibility(task, user)
            if completion:
                completed_tasks.append(task)
            elif task.is_currently_active(now):
                active_tasks.append(task)

        if status_filter == 'active':
            tasks = active_tasks
        elif status_filter == 'completed':
            tasks = completed_tasks
        else:
            tasks = active_tasks + completed_tasks

        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        permission_classes=[permissions.IsAuthenticated],
        throttle_classes=[CompleteThrottle],
    )
    def complete(self, request, slug=None):
        user = request.user

        if getattr(user, 'is_banned', False):
            return Response(
                {
                    'error': 'account_banned',
                    'message': 'Your account is banned and cannot complete social tasks.',
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            task = SocialTask.objects.select_related('category').get(slug=slug)
        except SocialTask.DoesNotExist:
            return Response({'error': 'task_not_found'}, status=status.HTTP_404_NOT_FOUND)

        # Existing completion first: a retry on an already-completed task must
        # stay idempotent (200 already_completed) even after the task expires
        # or is deactivated — matching the list endpoint, which keeps completed
        # tasks visible regardless of lifecycle, and the in-transaction order.
        existing = SocialTaskCompletion.objects.filter(user=user, task=task).first()
        if existing:
            return self._already_completed_response(task, existing)

        if not task.is_currently_active():
            return Response(
                {'error': 'task_unavailable', 'message': 'This task is not currently active.'},
                status=status.HTTP_410_GONE,
            )

        eligibility = evaluate_task_eligibility(task, user)
        if not eligibility.eligible:
            return self._eligibility_error_response(eligibility)

        # Snapshot the type that is actually verified: an admin could edit the
        # task during the (possibly slow) external verification, and the
        # completion row must record what ran, not the new config.
        verified_type = task.verification_type
        result = verify(task, user)
        if not result.ok:
            return self._verification_error_response(result.error_code, result.audit)

        try:
            with transaction.atomic():
                get_user_model().objects.select_for_update().get(pk=user.pk)
                existing = SocialTaskCompletion.objects.filter(user=user, task=task).first()
                if existing:
                    return self._already_completed_response(task, existing)

                # Verification can take seconds (external API call); re-check
                # the task inside the transaction so one that expired or was
                # deactivated in the meantime does not award. The refresh also
                # snapshots the current points value.
                task.refresh_from_db()
                if not task.is_currently_active():
                    return Response(
                        {'error': 'task_unavailable', 'message': 'This task is not currently active.'},
                        status=status.HTTP_410_GONE,
                    )

                eligibility = evaluate_task_eligibility(task, user)
                if not eligibility.eligible:
                    return self._eligibility_error_response(eligibility)

                completion = SocialTaskCompletion.objects.create(
                    user=user,
                    task=task,
                    points_awarded=task.points,
                    verification_type=verified_type,
                    verification_data=result.audit,
                )
        except Exception as exc:
            logger.exception('Failed to record social task completion: %s', exc)
            return Response(
                {'error': 'completion_failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        task._user_completion = completion
        return Response(
            {
                'status': 'completed',
                'points_awarded': completion.points_awarded,
                'completed_at': completion.completed_at,
                'task': SocialTaskSerializer(task, context={'request': request}).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def _already_completed_response(self, task, completion):
        task._user_completion = completion
        return Response(
            {
                'status': 'already_completed',
                'points_awarded': completion.points_awarded,
                'completed_at': completion.completed_at,
                'task': SocialTaskSerializer(task, context={'request': self.request}).data,
            },
            status=status.HTTP_200_OK,
        )

    def _verification_error_response(self, error_code, audit):
        if error_code == 'social_account_not_linked':
            return Response(
                {
                    'error': error_code,
                    'platform': audit.get('platform'),
                    'message': 'Link your social account first, then try again.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if error_code == 'token_invalid_relink_required':
            return Response(
                {
                    'error': error_code,
                    'platform': audit.get('platform'),
                    'message': 'Your authorization expired. Please reconnect your account.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if error_code == 'verification_failed':
            return Response(
                {
                    'error': error_code,
                    'message': 'We did not see the action yet. Try again in a moment.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if error_code == 'verification_unavailable':
            return Response(
                {
                    'error': error_code,
                    'message': 'Verification service is temporarily unavailable. Try again shortly.',
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if error_code == 'unsupported_verification_type':
            return Response(
                {'error': error_code},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {'error': error_code or 'verification_failed'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    def _eligibility_error_response(self, eligibility):
        return Response(
            {
                'error': 'eligibility_failed',
                'message': eligibility.message or 'Meet this task requirement first.',
                'eligibility': {
                    'eligible': eligibility.eligible,
                    'message': eligibility.message,
                    **(eligibility.details or {}),
                },
            },
            status=status.HTTP_403_FORBIDDEN,
        )
