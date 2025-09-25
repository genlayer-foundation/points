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
from .blockchain_service import validator_blockchain_service, VALIDATOR_CONTRACT_ABI


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
        if self.action in ['newest_validators', 'contract_info']:
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
        Uses the same query pattern as ActiveValidatorsView.
        """
        from django.db.models.functions import TruncDate
        
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
        
        # Build result with full user details including role indicators
        from users.models import User
        from users.serializers import UserSerializer
        
        result = []
        for validator in validators_with_first_uptime:
            try:
                user = User.objects.get(id=validator['user'])
                user_data = UserSerializer(user).data
                user_data['first_uptime_date'] = validator['first_uptime_date']
                result.append(user_data)
            except User.DoesNotExist:
                # Fallback to simple data if user not found
                result.append({
                    'address': validator['user__address'],
                    'name': validator['user__name'],
                    'first_uptime_date': validator['first_uptime_date']
                })
        
        return Response(result)

    @action(detail=False, methods=['get'], url_path='contract-info')
    def contract_info(self, request):
        """
        Get validator contract information for frontend wallet integration.
        Returns contract address, ABI, and RPC URL.
        This endpoint is public as the ABI is not sensitive information.
        """
        try:
            contract_info = {
                'contract_address': settings.VALIDATOR_CONTRACT_ADDRESS,
                'abi': VALIDATOR_CONTRACT_ABI,
                'rpc_url': settings.VALIDATOR_RPC_URL
            }

            return Response(contract_info, status=status.HTTP_200_OK)

        except AttributeError as e:
            # Handle missing settings
            missing_setting = str(e).split("'")[1]
            return Response(
                {
                    'error': f'Contract configuration incomplete: {missing_setting} not configured',
                    'detail': 'Please check your environment configuration'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            return Response(
                {
                    'error': 'Failed to retrieve contract information',
                    'detail': str(e)
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )