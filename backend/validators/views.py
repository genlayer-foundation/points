from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db.models import Min, Q
from django.conf import settings
from .models import Validator
from users.models import User
from users.serializers import ValidatorSerializer, UserSerializer
from contributions.models import Contribution, ContributionType


class ValidatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Validator profiles.
    """
    queryset = Validator.objects.all()
    serializer_class = ValidatorSerializer
    
    def get_permissions(self):
        """
        Allow read-only access without authentication for public endpoints.
        """
        if self.action in ['newest_validators']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    @action(detail=False, methods=['get', 'patch'], url_path='me')
    def my_profile(self, request):
        """
        Get or update current user's validator profile.
        """
        if request.method == 'GET':
            try:
                validator = Validator.objects.get(user=request.user)
                serializer = self.get_serializer(validator)
                return Response(serializer.data)
            except Validator.DoesNotExist:
                return Response(
                    {'detail': 'Validator profile not found for current user.'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        elif request.method == 'PATCH':
            validator, created = Validator.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(validator, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='newest')
    def newest_validators(self, request):
        """
        Get validators sorted by their first uptime contribution date (newest first).
        Returns the 5 most recent validators to join.
        Uses lightweight serializers to avoid N+1 queries.
        """
        from django.db.models.functions import TruncDate
        from utils.serializers import LightUserSerializer

        limit = int(request.GET.get('limit', 5))

        # Get the Uptime contribution type
        try:
            uptime_type = ContributionType.objects.get(name__iexact='uptime')
        except ContributionType.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

        # Get all validators with their first uptime contribution
        # Similar to ActiveValidatorsView query
        validators_with_first_uptime = (
            Contribution.objects
            .filter(contribution_type=uptime_type)
            .values('user', 'user__address', 'user__name')
            .annotate(
                first_uptime_date=Min('contribution_date')
            )
            .order_by('-first_uptime_date')[:limit]
        )

        # Get user IDs and fetch users with optimization
        user_ids = [v['user'] for v in validators_with_first_uptime]
        users_dict = {
            user.id: user
            for user in User.objects.filter(id__in=user_ids).select_related('validator', 'builder')
        }

        # Build result with lightweight serializer
        result = []
        for validator in validators_with_first_uptime:
            user = users_dict.get(validator['user'])
            if user:
                user_data = LightUserSerializer(user).data
                user_data['first_uptime_date'] = validator['first_uptime_date']
                result.append(user_data)
            else:
                # Fallback to simple data if user not found
                result.append({
                    'address': validator['user__address'],
                    'name': validator['user__name'],
                    'first_uptime_date': validator['first_uptime_date']
                })

        return Response(result)
