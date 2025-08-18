from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, UserProfileUpdateSerializer
from web3 import Web3


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows users to be viewed.
    Users with visible=False are excluded from the queryset,
    except for the authenticated user viewing their own profile.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]  # Allow read-only access without authentication
    lookup_field = 'address'  # Change default lookup field from 'pk' to 'address'
    
    def get_object(self):
        """
        Override to allow users to access their own profile
        even if they're marked as not visible.
        """
        obj = super().get_object()
        # If the user is accessing their own profile, allow it
        if self.request.user.is_authenticated and obj.id == self.request.user.id:
            return obj
        return obj
        
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)')
    def by_address(self, request, address=None):
        """
        Get a user by their Ethereum wallet address
        """
        user = get_object_or_404(User, address__iexact=address)
        serializer = self.get_serializer(user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='by-address/(?P<address>[^/.]+)/highlights')
    def user_highlights(self, request, address=None):
        """
        Get highlights for a specific user by their address
        """
        from contributions.models import ContributionHighlight
        from contributions.serializers import ContributionHighlightSerializer
        
        user = get_object_or_404(User, address__iexact=address)
        limit = int(request.query_params.get('limit', 5))
        
        highlights = ContributionHighlight.get_active_highlights(user=user, limit=limit)
        serializer = ContributionHighlightSerializer(highlights, many=True)
        return Response(serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'create' and 'visible' in self.request.data:
            context['visible'] = self.request.data.get('visible')
        return context
    
    @action(detail=False, methods=['get', 'patch'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """
        Get or update the authenticated user's profile.
        Users can always see their own profile regardless of visibility setting.
        For PATCH requests, only the name field can be updated.
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            serializer = UserProfileUpdateSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Return the full user data after update
                full_serializer = self.get_serializer(request.user)
                return Response(full_serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Registration will be handled by MetaMask authentication
    
    def _get_web3_contract(self):
        """
        Helper method to create a Web3 contract instance
        """
        # Connect to the blockchain using environment variables
        w3 = Web3(Web3.HTTPProvider(settings.VALIDATOR_RPC_URL))
        
        # Contract address from environment variables
        contract_address = settings.VALIDATOR_CONTRACT_ADDRESS
        
        # Minimal ABI for the validators functions
        abi = [
            {
                'inputs': [],
                'name': 'getValidatorsAtCurrentEpoch',
                'outputs': [{'type': 'address[]', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [],
                'name': 'getAllBannedValidators',
                'outputs': [{'type': 'address[]', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [],
                'name': 'getValidatorBansCount',
                'outputs': [{'type': 'uint256', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            },
            {
                'inputs': [{'type': 'uint256', 'name': 'index'}],
                'name': 'validatorsBanned',
                'outputs': [{'type': 'address', 'name': ''}],
                'stateMutability': 'view',
                'type': 'function'
            }
        ]
        
        # Create contract instance
        return w3.eth.contract(address=contract_address, abi=abi)
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_validator_journey(self, request):
        """
        Award the validator waitlist badge to the user.
        This should be called after the user completes the validator journey requirements.
        """
        from contributions.models import Contribution, ContributionType
        from leaderboard.models import GlobalLeaderboardMultiplier
        from django.utils import timezone
        
        user = request.user
        
        # Check if user already has the badge
        try:
            waitlist_type = ContributionType.objects.get(slug='validator-waitlist')
        except ContributionType.DoesNotExist:
            return Response(
                {'error': 'Validator waitlist contribution type not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if Contribution.objects.filter(user=user, contribution_type=waitlist_type).exists():
            return Response(
                {'message': 'You already have the validator waitlist badge'},
                status=status.HTTP_200_OK
            )
        
        # Create the contribution to award the badge
        try:
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=waitlist_type,
                points=20,
                contribution_date=timezone.now(),
                notes='Completed validator journey and joined the waitlist'
            )
            
            serializer = self.get_serializer(user)
            return Response({
                'message': 'Validator waitlist badge awarded successfully!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to award badge: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def complete_builder_journey(self, request):
        """
        Award the builder initiate badge to the user.
        This should be called after the user completes the builder journey requirements.
        """
        from contributions.models import Contribution, ContributionType
        from django.utils import timezone
        
        user = request.user
        
        # Check if user already has the badge
        try:
            welcome_type = ContributionType.objects.get(slug='builder-welcome')
        except ContributionType.DoesNotExist:
            return Response(
                {'error': 'Builder welcome contribution type not configured'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if Contribution.objects.filter(user=user, contribution_type=welcome_type).exists():
            return Response(
                {'message': 'You already have the builder welcome badge'},
                status=status.HTTP_200_OK
            )
        
        # Create the contribution to award the badge
        try:
            contribution = Contribution.objects.create(
                user=user,
                contribution_type=welcome_type,
                points=20,
                contribution_date=timezone.now(),
                notes='Completed builder journey - welcome to the builder community!'
            )
            
            serializer = self.get_serializer(user)
            return Response({
                'message': 'Builder welcome badge awarded successfully!',
                'user': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to award badge: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def validators(self, request):
        """
        Get the list of active validators from the GenLayer contract
        """
        try:
            # Create contract instance
            contract = self._get_web3_contract()
            
            # Call getValidatorsAtCurrentEpoch function
            validators = contract.functions.getValidatorsAtCurrentEpoch().call()
            
            # Just return the list of addresses without case conversion
            return Response(validators, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
