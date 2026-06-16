from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Count, Q
from .models import Steward, WorkingGroup, WorkingGroupParticipant
from users.serializers import StewardSerializer
from users.models import User
from .serializers import (
    WorkingGroupListSerializer,
    WorkingGroupDetailSerializer,
    WorkingGroupCreateSerializer,
    WorkingGroupUpdateSerializer,
)
from contributions.permissions import IsSteward
import logging

logger = logging.getLogger(__name__)


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

