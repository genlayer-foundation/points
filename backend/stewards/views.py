from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Steward
from users.serializers import StewardSerializer
import logging

logger = logging.getLogger(__name__)


class StewardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Steward profiles.
    """
    queryset = Steward.objects.all()
    serializer_class = StewardSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """
        List all stewards with user details.
        Allow public access to view steward list.
        """
        stewards = self.get_queryset().select_related('user')
        data = []
        for steward in stewards:
            steward_data = {
                'id': steward.id,
                'user_id': steward.user.id,
                'name': steward.user.name,
                'address': steward.user.address,
                'created_at': steward.created_at,
                'user_details': {
                    'name': steward.user.name,
                    'address': steward.user.address,
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
            steward, created = Steward.objects.get_or_create(user=request.user)
            serializer = self.get_serializer(steward, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _check_steward_permission(self, request):
        """
        Helper method to check if the current user is a steward.
        """
        if not request.user.is_authenticated:
            return False

        try:
            steward = Steward.objects.get(user=request.user)
            return True
        except Steward.DoesNotExist:
            return False




