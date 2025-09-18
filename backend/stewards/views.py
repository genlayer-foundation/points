from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Steward
from users.serializers import StewardSerializer
from .serializers import BannedValidatorSerializer, BannedValidatorListSerializer
from validators.blockchain_service import validator_blockchain_service
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

    @action(detail=False, methods=['get'], url_path='banned-validators')
    def banned_validators(self, request):
        """
        Get all banned validators with their details.
        Only accessible by stewards.
        """
        # Check steward permission
        if not self._check_steward_permission(request):
            return Response(
                {'detail': 'Only stewards can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            logger.info(f"Steward {request.user.address} requesting banned validators list")

            # Get banned validators from blockchain
            result = validator_blockchain_service.get_banned_validators()

            # Serialize the response
            serializer = BannedValidatorListSerializer(result)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching banned validators for steward {request.user.address}: {str(e)}")
            return Response(
                {
                    'banned_validators': [],
                    'total_banned': 0,
                    'error': 'Failed to fetch banned validators from blockchain'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='banned-validators/(?P<address>[^/.]+)')
    def banned_validator_detail(self, request, address=None):
        """
        Get detailed information about a specific banned validator.
        Only accessible by stewards.
        """
        # Check steward permission
        if not self._check_steward_permission(request):
            return Response(
                {'detail': 'Only stewards can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not address:
            return Response(
                {'detail': 'Validator address is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            logger.info(f"Steward {request.user.address} requesting details for banned validator {address}")

            # Check if validator is actually banned
            if not validator_blockchain_service.is_validator_banned(address):
                return Response(
                    {'detail': 'Validator is not banned.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Get validator details
            result = validator_blockchain_service.get_banned_validator_details(address)

            # Serialize the response
            serializer = BannedValidatorSerializer(result)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching banned validator details for {address}: {str(e)}")
            return Response(
                {'error': 'Failed to fetch validator details from blockchain'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='banned-validators/(?P<address>[^/.]+)/unban')
    def unban_validator(self, request, address=None):
        """
        Unban a specific validator.
        Only accessible by stewards.
        Future functionality - currently returns not implemented.
        """
        # Check steward permission
        if not self._check_steward_permission(request):
            return Response(
                {'detail': 'Only stewards can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        if not address:
            return Response(
                {'detail': 'Validator address is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"Steward {request.user.address} attempting to unban validator {address}")

        # For now, return not implemented
        return Response(
            {
                'success': False,
                'error': 'Unban functionality not yet implemented',
                'message': 'This feature will be available in a future update'
            },
            status=status.HTTP_501_NOT_IMPLEMENTED
        )

    @action(detail=False, methods=['post'], url_path='banned-validators/unban-all')
    def unban_all_validators(self, request):
        """
        Unban all validators.
        Only accessible by stewards.
        Future functionality - currently returns not implemented.
        """
        # Check steward permission
        if not self._check_steward_permission(request):
            return Response(
                {'detail': 'Only stewards can access this endpoint.'},
                status=status.HTTP_403_FORBIDDEN
            )

        logger.info(f"Steward {request.user.address} attempting to unban all validators")

        # For now, return not implemented
        return Response(
            {
                'success': False,
                'error': 'Unban all functionality not yet implemented',
                'message': 'This feature will be available in a future update'
            },
            status=status.HTTP_501_NOT_IMPLEMENTED
        )